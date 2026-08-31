# tokcost-project
# TokCost Project

Cross-platform token and cost estimation framework for ChatGPT, Claude, and Gemini.

## About
This project helps users estimate token usage and cost across multiple AI platforms 
before submitting a prompt, and recommends the most suitable platform for their task.

## Features

- **Cross-Platform Token Estimation**: Accurate token counting for OpenAI GPT models, Anthropic Claude, and Google Gemini
- **Cost Calculation**: Real-time cost estimation based on current API pricing
- **Prompt Compression**: Intelligent prompt optimization to reduce token usage and costs
- **Platform Recommendations**: Smart suggestions for the most cost-effective platform for your use case

## Prompt Compression Module

The **Prompt Compressor** (`backend/compressor.py`) is an enterprise-grade module that intelligently reduces prompt size while maintaining semantic integrity and protecting critical information.

### Features
- **Hybrid Compression Strategy**: Combines AST/Regex Tensor Masking with LLMLingua-2 Extractive Token Pruning
- **Intelligent Content Protection**: Automatically preserves code blocks, JSON schemas, Markdown tables, and logical constraints
- **Configurable Compression Rate**: Customize target compression ratios (default: 50%)
- **GPU Acceleration**: Automatically detects and utilizes CUDA for faster processing, with CPU fallback
- **Singleton Pattern**: Lazy-loads heavy neural models once to optimize memory usage
- **Comprehensive Metrics**: Returns detailed compression statistics including tokens saved and reduction percentage
- **Error Resilience**: Graceful fallback mechanisms ensure prompt delivery even if compression fails

### Architecture

The `ProductionPromptCompressor` class implements:

1. **Model Initialization**: Lazy-loads Microsoft LLMLingua-2 (bert-base-multilingual-cased-meetingbank) on available device (CUDA/CPU)
2. **Content Protection**: Masks critical elements before compression:
   - Code blocks (```...```)
   - JSON structures ({...})
   - Markdown tables (|...|)
   - Logical constraints (IF, THEN, ELSE, REQUIRE, ALWAYS, NEVER)
3. **Token Pruning**: Applies information entropy-based pruning via LLMLingua-2
4. **Content Restoration**: Unmasks protected elements into the final compressed prompt
5. **Safety Circuits**: 
   - Skips compression for prompts under 30 tokens
   - Validates compression doesn't inflate token count
   - Falls back to original prompt if compression fails

### Usage

```python
from backend.compressor import ProductionPromptCompressor

compressor = ProductionPromptCompressor()

result = compressor.compress(
    raw_prompt="your prompt text here",
    target_rate=0.5  # Target 50% of original tokens
)

print(result)
# Output:
# {
#     "original_prompt": "...",
#     "compressed_prompt": "...",
#     "metrics": {
#         "raw_tokens": 150,
#         "compressed_tokens": 75,
#         "tokens_saved": 75,
#         "percent_reduction": 50.0
#     }
# }
```

### Response Format

```json
{
  "original_prompt": "The complete original prompt text",
  "compressed_prompt": "The intelligently compressed prompt",
  "metrics": {
    "raw_tokens": 150,
    "compressed_tokens": 75,
    "tokens_saved": 75,
    "percent_reduction": 50.0
  }
}
```
### Collaborator: Sarthak Deshmukh (https://github.com/sarthakkkk7)
## Getting Started

Everyone (including you) should now clone the repo locally:
```bash
git clone https://github.com/SanketMohite01/tokcost-project.git
cd tokcost-project
```