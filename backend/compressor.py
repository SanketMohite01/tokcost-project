import re
import logging
from typing import Dict, Any, Tuple
from functools import lru_cache
import tiktoken
import torch
from llmlingua import PromptCompressor as LLMCompressor

logger = logging.getLogger("TokCost.Compressor")

class ProductionPromptCompressor:
    """
    Enterprise-grade Prompt Compressor for TokCost.
    Combines AST/Regex Tensor Masking with LLMLingua-2 Extractive Token Pruning.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ProductionPromptCompressor, cls).__new__(cls)
            cls._instance._initialize_models()
        return cls._instance

    def _initialize_models(self) -> None:
        """Lazy-loads heavy neural models into host memory once (Singleton)."""
        # Detect whether CUDA GPU acceleration is available; fallback to CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing Microsoft LLMLingua-2 model pipeline on device: {device}...")

        try:
            self.lingua = LLMCompressor(
                model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                use_llmlingua2=True,
                device_map=device  # Explicitly set device targeting
            )
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.info("Compressor models loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load LLMLingua model: {e}")
            self.lingua = None
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _mask_protected_elements(self, text: str) -> Tuple[str, list]:
        """Protects code blocks, JSON schemas, Markdown tables, and logical constraints."""
        protected_blocks = []
        patterns = [
            r"```[\s\S]*?```",                          # Code fences
            r"\{[^{}]*\}",                              # JSON structures
            r"\|[^\n]+\|[^\n]+\|",                     # Markdown tables
            r"\b(IF|THEN|ELSE|REQUIRE|ALWAYS|NEVER)\b" # Strict logic rules
        ]
        combined_pattern = "|".join(patterns)

        def replace_fn(match):
            idx = len(protected_blocks)
            protected_blocks.append(match.group(0))
            return f" __PROTECTED_SLOT_{idx}__ "

        masked_text = re.sub(combined_pattern, replace_fn, text)
        return masked_text, protected_blocks

    def _unmask_elements(self, text: str, protected_blocks: list) -> str:
        """Restores protected structural elements back into the compressed text stream."""
        for idx, block in enumerate(protected_blocks):
            text = text.replace(f"__PROTECTED_SLOT_{idx}__", block)
        return text

    def compress(self, raw_prompt: str, target_rate: float = 0.5) -> Dict[str, Any]:
        """
        Compresses input prompt to target rate while maintaining complete context integrity.
        """
        if not raw_prompt or not raw_prompt.strip():
            return self._empty_response()

        raw_token_count = len(self.tokenizer.encode(raw_prompt))
        
        # Circuit Breaker 1: Short prompts skip compression overhead
        if raw_token_count < 30 or self.lingua is None:
            return self._build_response(raw_prompt, raw_prompt, raw_token_count, raw_token_count)

        try:
            # Step 1: Isolate logic and AST primitives
            masked_text, protected_blocks = self._mask_protected_elements(raw_prompt)

            # Step 2: Information Entropy Token Pruning via LLMLingua-2
            compression_results = self.lingua.compress_prompt(
                masked_text,
                rate=target_rate,
                drop_consecutive=True
            )
            compressed_masked_text = compression_results.get("compressed_prompt", masked_text)

            # Step 3: Reconstruct protected tensors
            final_compressed_prompt = self._unmask_elements(compressed_masked_text, protected_blocks)
            comp_token_count = len(self.tokenizer.encode(final_compressed_prompt))

            # Circuit Breaker 2: Safeguard against unexpected token inflation
            if comp_token_count >= raw_token_count:
                return self._build_response(raw_prompt, raw_prompt, raw_token_count, raw_token_count)

            return self._build_response(raw_prompt, final_compressed_prompt, raw_token_count, comp_token_count)

        except Exception as e:
            logger.error(f"Compression fallback triggered due to error: {e}")
            return self._build_response(raw_prompt, raw_prompt, raw_token_count, raw_token_count)

    def _build_response(self, original: str, compressed: str, raw_cnt: int, comp_cnt: int) -> Dict[str, Any]:
        saved = max(0, raw_cnt - comp_cnt)
        pct = round((saved / raw_cnt * 100), 2) if raw_cnt > 0 else 0.0
        return {
            "original_prompt": original,
            "compressed_prompt": compressed,
            "metrics": {
                "raw_tokens": raw_cnt,
                "compressed_tokens": comp_cnt,
                "tokens_saved": saved,
                "percent_reduction": pct
            }
        }

    def _empty_response(self) -> Dict[str, Any]:
        return self._build_response("", "", 0, 0)