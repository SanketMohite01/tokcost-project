import fitz  # this is pymupdf's import name

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text


def extract_text_from_code(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text_from_file(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith((".py", ".java", ".js", ".cpp", ".c", ".html", ".css", ".txt")):
        return extract_text_from_code(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")