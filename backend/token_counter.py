import logging
import os
from dotenv import load_dotenv
import tiktoken
import google.generativeai as genai
from file_parser import extract_text_from_file, count_image_tokens

load_dotenv()
logger = logging.getLogger("tokcost.tokens")

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Override in .env if Google renames models (invalid names break count_tokens API).
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def count_tokens_gpt(text: str, model: str = "gpt-4o") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def count_tokens_claude(text: str) -> int:
    encoding = tiktoken.encoding_for_model("gpt-4o")
    return len(encoding.encode(text))


def count_tokens_gemini(text: str) -> int:
    if not os.getenv("GOOGLE_API_KEY", "").strip():
        return None
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        result = model.count_tokens(text)
        return result.total_tokens
    except Exception as e:
        logger.warning("Gemini count_tokens failed (%s), using tiktoken fallback", e)
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def count_all_platforms(text: str) -> dict:
    return {
        "chatgpt": count_tokens_gpt(text),
        "claude": count_tokens_claude(text),
        "gemini": count_tokens_gemini(text),
    }


def count_tokens_for_file(file_path: str) -> dict:
    extracted_text = extract_text_from_file(file_path)
    return count_all_platforms(extracted_text)


def count_tokens_for_image(file_path: str) -> dict:
    return count_image_tokens(file_path)


if __name__ == "__main__":
    choice = input("Type 'text', 'file', or 'image': ")

    if choice == "text":
        user_text = input("Enter your prompt: ")
        results = count_all_platforms(user_text)
    elif choice == "image":
        file_path = input("Enter image path (e.g. sample.jpg): ")
        results = count_tokens_for_image(file_path)
    else:
        file_path = input("Enter file path (e.g. sample.pdf or sample.py): ")
        results = count_tokens_for_file(file_path)

    print(results)
