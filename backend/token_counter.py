import os
from dotenv import load_dotenv
import tiktoken
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def count_tokens_gpt(text: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def count_tokens_claude(text: str) -> int:
    # Temporary approximation using tiktoken until Anthropic API access is available
    encoding = tiktoken.encoding_for_model("gpt-4o")
    return len(encoding.encode(text))


def count_tokens_gemini(text: str) -> int:
    model = genai.GenerativeModel("gemini-3.6-flash")
    result = model.count_tokens(text)
    return result.total_tokens


def count_all_platforms(text: str) -> dict:
    return {
        "chatgpt": count_tokens_gpt(text),
        "claude": count_tokens_claude(text),
        "gemini": count_tokens_gemini(text),
    }


if __name__ == "__main__":
    user_text = input("Enter your prompt: ")
    results = count_all_platforms(user_text)
    print(results)