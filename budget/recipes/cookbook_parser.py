import re
from typing import List, Tuple, Dict


# ----------------------------
# Text cleanup helpers
# ----------------------------

# Postgres TEXT cannot contain NUL bytes. Some PDFs produce \x00 characters.
_CTRL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

def clean_extracted_text(s: str) -> str:
    """
    Clean extracted PDF text so it can be safely stored in Postgres and parsed.
    - Removes NUL and other control chars (except \n and \t)
    - Normalizes newlines
    """
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _CTRL_RE.sub("", s)
    return s


# ----------------------------
# PDF extraction (Render-safe)
# ----------------------------

def extract_text_from_pdf(file_path: str, max_pages: int = 60, min_chars_to_accept: int = 1500) -> str:
    """
    Fast + Render-safe extraction.
    1) Try pypdf first (lighter, less likely to crash on fonts)
    2) If it extracts almost nothing, try pdfplumber as fallback
    3) Hard cap pages to avoid timeouts/OOM
    4) Cleans control characters (esp. NUL \x00) that break Postgres
    """
    parts: list[str] = []
    last_err = None
    text = ""

    # 1) pypdf first
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path, strict=False)
        for page in reader.pages[:max_pages]:
            try:
                page_text = page.extract_text() or ""
            except Exception:
                page_text = ""
            page_text = clean_extracted_text(page_text)
            if page_text.strip():
                parts.append(page_text)

        text = "\n\n".join(parts).strip()
        if len(text) >= min_chars_to_accept:
            return text

    except Exception as e_pypdf:
        last_err = e_pypdf
        text = ""

    # 2) pdfplumber fallback (only if needed)
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:max_pages]:
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                page_text = clean_extracted_text(page_text)
                if page_text.strip():
                    parts.append(page_text)

        text2 = "\n\n".join(parts).strip()
        if text2:
            return text2

    except Exception as e_plumber:
        if last_err:
            raise Exception(f"Both pypdf and pdfplumber failed: {last_err}, {e_plumber}")
        raise Exception(f"pdfplumber failed: {e_plumber}")

    # If both succeeded but produced nothing
    if text:
        return text

    raise Exception("Could not extract any text from this PDF (might be scanned images/OCR needed).")


# ----------------------------
# Chunking + parsing
# ----------------------------

def split_into_recipe_chunks(text: str) -> List[Dict]:
    """
    Split PDF text into recipe chunks by detecting 'Ingredients' headings.
    Include ~300-500 chars above as title context.
    """
    text = clean_extracted_text(text)

    ingredients_pattern = re.compile(r"(ingredients?)\s*[:\n]", re.IGNORECASE)
    matches = list(ingredients_pattern.finditer(text))

    if not matches:
        # If no Ingredients heading found, treat entire text as one chunk
        return [{
            "title_guess": "",
            "raw_text": text.strip(),
        }]

    chunks = []

    for i, match in enumerate(matches):
        start_pos = match.start()

        # Get context before (300-500 chars for title)
        context_start = max(0, start_pos - 500)
        title_context = text[context_start:start_pos]

        # Content until next Ingredients heading or end
        if i + 1 < len(matches):
            # NOTE: do NOT subtract 500 here; you already capture title context separately
            end_pos = matches[i + 1].start()
            end_pos = max(match.end(), end_pos)
        else:
            end_pos = len(text)

        recipe_content = text[start_pos:end_pos]
        raw = (title_context + recipe_content).strip()

        # Clean again before storing (extra safety)
        raw = clean_extracted_text(raw)

        chunks.append({
            "title_guess": extract_title_from_context(title_context),
            "raw_text": raw,
        })

    return chunks


def extract_title_from_context(context: str) -> str:
    """Extract title from the context before Ingredients heading."""
    context = clean_extracted_text(context)
    lines = context.strip().split("\n")

    # Work backwards to find a non-empty line that looks like a title
    for line in reversed(lines):
        line = line.strip()

        # Skip empty lines, page numbers, very short lines
        if len(line) < 3:
            continue
        if line.isdigit():
            continue

        # Skip lines that look like measurements or ingredient-like
        if re.match(r"^[\d½¼¾⅓⅔⅛]+\s*(cup|tbsp|tsp|oz|lb|g|ml|kg)", line, re.IGNORECASE):
            continue

        # Clean up potential title
        title = re.sub(r"^(recipe|chapter|\d+[\.\):]?)\s*", "", line, flags=re.IGNORECASE).strip()

        if len(title) > 2:
            return title[:200]  # Limit title length

    return "Untitled Recipe"


def parse_recipe_chunk(chunk: Dict) -> Dict:
    """
    Parse a recipe chunk to extract title, ingredients, and steps.
    Returns parsed data with confidence score.
    """
    raw_text = clean_extracted_text(chunk.get("raw_text", ""))
    title_guess = (chunk.get("title_guess", "") or "").strip()

    # Parse ingredients
    ingredients, ing_confidence = parse_ingredients(raw_text)

    # Parse steps/instructions
    steps, steps_confidence = parse_steps(raw_text)

    # Refine title
    parsed_title = title_guess if title_guess else extract_title_fallback(raw_text)

    # Calculate overall confidence
    confidence = calculate_confidence(ingredients, steps, ing_confidence, steps_confidence)

    return {
        "title_guess": title_guess,
        "raw_text": raw_text,
        "parsed_title": parsed_title,
        "parsed_ingredients": ingredients,
        "parsed_steps": steps,
        "confidence": confidence,
    }


def parse_ingredients(text: str) -> Tuple[List[str], float]:
    """Extract ingredients list from text."""
    text = clean_extracted_text(text)
    ingredients: List[str] = []
    confidence = 0.0

    ing_match = re.search(
        r"ingredients?\s*[:\n](.*?)(?=(?:instructions?|directions?|method|steps?|preparation)\s*[:\n]|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if ing_match:
        ing_section = ing_match.group(1)
        confidence = 0.5

        lines = ing_section.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Skip lines that look like section headers
            if re.match(r"^(for the|ingredients?|notes?|tip:)", line, re.IGNORECASE):
                continue

            # Clean up bullet points and numbers
            line = re.sub(r"^[\-•\*\d\.\)]+\s*", "", line).strip()

            if len(line) > 1:
                ingredients.append(line)

        if len(ingredients) >= 3:
            confidence = 0.8
        if len(ingredients) >= 5:
            confidence = 1.0

    return ingredients, confidence


def parse_steps(text: str) -> Tuple[List[str], float]:
    """Extract cooking steps/instructions from text."""
    text = clean_extracted_text(text)
    steps: List[str] = []
    confidence = 0.0

    inst_match = re.search(
        r"(?:instructions?|directions?|method|steps?|preparation)\s*[:\n](.*?)(?=(?:notes?|tips?|serving|nutrition)\s*[:\n]|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if inst_match:
        inst_section = inst_match.group(1)
        confidence = 0.5

        # Try to split by numbered steps first
        numbered_steps = re.findall(
            r"(?:^|\n)\s*\d+[\.\)]\s*(.+?)(?=(?:\n\s*\d+[\.\)]|\Z))",
            inst_section,
            re.DOTALL
        )

        if numbered_steps:
            steps = [step.strip().replace("\n", " ") for step in numbered_steps if step.strip()]
            confidence = 0.9
        else:
            # Fallback to paragraph splitting
            paragraphs = inst_section.strip().split("\n\n")
            for para in paragraphs:
                para = para.strip().replace("\n", " ")
                if len(para) > 10:
                    steps.append(para)

            if steps:
                confidence = 0.6

    if len(steps) >= 3:
        confidence = min(confidence + 0.1, 1.0)

    return steps, confidence


def extract_title_fallback(text: str) -> str:
    """Fallback title extraction from first meaningful line."""
    text = clean_extracted_text(text)
    lines = text.strip().split("\n")
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 5 and not re.match(r"^(ingredients?|instructions?|directions?)", line, re.IGNORECASE):
            return line[:200]
    return "Untitled Recipe"


def calculate_confidence(ingredients: List[str], steps: List[str], ing_conf: float, steps_conf: float) -> float:
    """Calculate overall parsing confidence."""
    if not ingredients and not steps:
        return 0.0

    # Weighted average
    score = (ing_conf * 0.5) + (steps_conf * 0.5)

    # Bonus for having both
    if ingredients and steps:
        score += 0.1

    return min(score, 1.0)
