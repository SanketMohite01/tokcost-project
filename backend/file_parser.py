import fitz  # this is pymupdf's import name
from docx import Document
from PIL import Image


def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text


def extract_text_from_code(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text


def extract_text_from_file(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx"):
        return extract_text_from_docx(file_path)
    elif file_path.endswith((".py", ".java", ".js", ".cpp", ".c", ".html", ".css", ".txt")):
        return extract_text_from_code(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")

def get_image_dimensions(file_path: str):
    with Image.open(file_path) as img:
        return img.width, img.height

def claude_image_tokens(width: int, height: int) -> int:
    # Claude's published approximation: tokens ≈ (width × height) / 750
    return int((width * height) / 750)


def gpt_image_tokens(width: int, height: int) -> int:
    # Simplified tile-based formula (OpenAI high-detail mode)
    tiles_x = -(-width // 512)   # ceiling division
    tiles_y = -(-height // 512)
    num_tiles = tiles_x * tiles_y
    return 85 + (170 * num_tiles)


def gemini_image_tokens(width: int, height: int) -> int:
    # Simplified resolution-bucket approximation
    if width <= 384 and height <= 384:
        return 258
    else:
        return 258 * 2

def count_image_tokens(file_path: str) -> dict:
    width, height = get_image_dimensions(file_path)
    return {
        "chatgpt": gpt_image_tokens(width, height),
        "claude": claude_image_tokens(width, height),
        "gemini": gemini_image_tokens(width, height),
    }