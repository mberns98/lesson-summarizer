from __future__ import annotations

from lesson_summarizer.llm.prompts import build_prompt
from lesson_summarizer.llm.gemini_client import generate_text
from lesson_summarizer.chunking import chunk_text


def summarize_text_to_markdown(
    text: str,
    *,
    language: str = "es",
    topic: str = "Clase",
    role_key: str | None = None,
    role_custom: str | None = None,
    output_key: str | None = None,
    output_custom: str | None = None,
    model: str = "gemini-2.5-flash",
) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("Input text is empty.")

    instructions = build_prompt(
        language=language,
        topic=topic,
        role_key=role_key,
        role_custom=role_custom,
        output_key=output_key,
        output_custom=output_custom,
    )

    full_prompt = f"""{instructions}

TEXTO:
\"\"\"{text}\"\"\"

INSTRUCCIONES:
- Generá la salida solicitada en Markdown.
- No agregues saludos ni cierres.
""".strip()

    md = generate_text(full_prompt, model=model)
    return md.strip()


def summarize_long_text_to_markdown(
    text: str,
    *,
    language: str = "es",
    topic: str = "Clase",
    role_key: str | None = None,
    role_custom: str | None = None,
    output_key: str | None = None,
    output_custom: str | None = None,
    model: str = "gemini-2.5-flash",
    chunk_size_chars: int = 10_000,
    overlap_chars: int = 0,
) -> str:
    """
    Resume texto largo por chunks y concatena (SIN reduce final).
    Esto evita que el output se trunque por límites.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Input text is empty.")

    chunks = chunk_text(text, chunk_size=chunk_size_chars, overlap=overlap_chars)
    if not chunks:
        return ""

    parts: list[str] = []
    total = len(chunks)

    for i, ch in enumerate(chunks, start=1):
        # Forzamos output acotado por chunk (si no, igual explota)
        per_chunk_output_custom = (output_custom or "").strip()
        if per_chunk_output_custom:
            per_chunk_output_custom += "\n"
        per_chunk_output_custom += (
            f"\nIMPORTANTE: Esta es la parte {i}/{total}. "
            "Mantené la salida breve y estructurada (máx ~1–2 páginas)."
        )

        md_i = summarize_text_to_markdown(
            text=ch,
            language=language,
            topic=topic,
            role_key=role_key,
            role_custom=role_custom,
            output_key=output_key,
            output_custom=per_chunk_output_custom,
            model=model,
        )

        parts.append(f"## Parte {i}/{total}\n\n{md_i}".strip())

    return "\n\n---\n\n".join(parts).strip()