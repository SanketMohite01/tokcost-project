import re
import logging
from typing import Dict, Any, Tuple
import tiktoken
import torch
from llmlingua import PromptCompressor as LLMCompressor

logger = logging.getLogger("TokCost.Compressor")

class ProductionPromptCompressor:
    """
    Enterprise-grade Prompt Compressor for TokCost.
    Combines AST/Balanced Bracket Masking with LLMLingua-2 Extractive Token Pruning.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ProductionPromptCompressor, cls).__new__(cls)
            cls._instance._initialize_models()
        return cls._instance

    def _initialize_models(self) -> None:
        """Lazy-loads heavy neural models into host memory once (Singleton)."""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing Microsoft LLMLingua-2 model pipeline on device: {device}...")

        try:
            self.lingua = LLMCompressor(
                model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                use_llmlingua2=True,
                device_map=device
            )
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.info("Compressor models loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load LLMLingua model: {e}")
            self.lingua = None
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _mask_protected_elements(self, text: str) -> Tuple[str, list[str]]:
        """
        Masks code fences, Markdown tables, and arbitrarily nested JSON blocks
        using a balanced character stack parser.
        """
        protected_blocks: list[str] = []

        # 1. Mask Code Fences & Markdown Tables via Regex
        regex_patterns = [
            r"```[\s\S]*?```",        # Multi-line code fences
            r"\|[^\n]+\|[^\n]+\|"     # Markdown tables
        ]
        
        def replace_fn(match: re.Match) -> str:
            idx = len(protected_blocks)
            protected_blocks.append(match.group(0))
            return f" [BLOCK_{idx}] "

        masked_text = re.sub("|".join(regex_patterns), replace_fn, text)

        # 2. Mask Balanced JSON Structures (Handles arbitrary nested objects)
        output_chars: list[str] = []
        i = 0
        length = len(masked_text)

        while i < length:
            if masked_text[i] == '{':
                start = i
                brace_count = 0
                in_string = False
                escape = False

                while i < length:
                    char = masked_text[i]
                    if not escape and char == '"':
                        in_string = not in_string
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                i += 1
                                break
                    escape = (char == '\\' and not escape)
                    i += 1

                if brace_count == 0:
                    json_block = masked_text[start:i]
                    idx = len(protected_blocks)
                    protected_blocks.append(json_block)
                    output_chars.append(f" [BLOCK_{idx}] ")
                    continue
                else:
                    output_chars.append(masked_text[start])
                    i = start + 1
            else:
                output_chars.append(masked_text[i])
                i += 1

        return "".join(output_chars), protected_blocks

    def _unmask_elements(self, text: str, protected_blocks: list[str]) -> str:
        """Restores protected structural blocks back into the compressed text stream."""
        for idx, block in enumerate(protected_blocks):
            target = f"[BLOCK_{idx}]"
            # Handle spacing alterations introduced by model tokenizers
            text = text.replace(target, block)
            text = text.replace(f"[BLOCK_ {idx}]", block)
            text = text.replace(f"[ BLOCK_{idx} ]", block)
        return text

    def compress(self, raw_prompt: str, target_rate: float = 0.5) -> Dict[str, Any]:
        """
        Compresses input prompt to target rate while maintaining context integrity.
        """
        if not raw_prompt or not raw_prompt.strip():
            return self._empty_response()

        raw_token_count = len(self.tokenizer.encode(raw_prompt))
        
        # Circuit Breaker 1: Short prompts skip compression overhead
        if raw_token_count < 35 or self.lingua is None:
            return self._build_response(raw_prompt, raw_prompt, raw_token_count, raw_token_count)

        try:
            # Step 1: Isolate structural primitives and nested JSON
            masked_text, protected_blocks = self._mask_protected_elements(raw_prompt)

            # Step 2: Build dynamic force_tokens array for placeholders and logic keys
            slot_tokens = [f"[BLOCK_{i}]" for i in range(len(protected_blocks))]
            base_force_keywords = ["IF", "THEN", "ELSE", "REQUIRE", "ALWAYS", "NEVER"]
            dynamic_force_tokens = base_force_keywords + slot_tokens

            # Step 3: LLMLingua-2 Token Pruning
            compression_results = self.lingua.compress_prompt(
                masked_text,
                rate=target_rate,
                drop_consecutive=True,
                force_tokens=dynamic_force_tokens
            )
            compressed_masked_text = compression_results.get("compressed_prompt", masked_text)

            # Step 4: Reconstruct protected structural blocks
            final_compressed_prompt = self._unmask_elements(compressed_masked_text, protected_blocks)
            comp_token_count = len(self.tokenizer.encode(final_compressed_prompt))

            # Circuit Breaker 2: Safeguard against token inflation
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