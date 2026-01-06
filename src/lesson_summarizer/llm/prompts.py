from __future__ import annotations

ROLE_PRESETS = {
    "data_scientist": "Actuás como Data Scientist senior en Deep Learning. Priorizás rigor y claridad.",
    "philosophy_expert": "Actuás como experto en filosofía, enfocándote en ética y teorías filosóficas clave.",
    "history_professor": "Actuás como profesor de historia, destacando eventos y contextos históricos importantes.",
    "data_engineer": "Actuás como ingeniero de datos, optimizando flujos y asegurando calidad de datos.",
    "ai_engineer": "Actuás como ingeniero de IA, implementando modelos y soluciones de inteligencia artificial.",
}

OUTPUT_PRESETS = {
    "apunte_detallado": "Apunte bien detallado, con secciones, definiciones, y bullets claros.",
    "resumen": "Resumen conciso del contenido principal, con puntos clave y definiciones esenciales.",
    "lista_de_conceptos": "Lista de conceptos importantes mencionados en la lección, sin explicaciones.",
    "preguntas_de_revision": "Preguntas de revisión para evaluar la comprensión del material cubierto en la lección.",
}

BASE = """\
Sos un asistente académico. Nada de frases de cortesía.
Tu objetivo es producir un documento útil para estudiar.

REGLAS:
- No inventes hechos. Si falta información, indicá incertidumbre.
- Priorizá claridad y estructura.
- Usá Markdown bien formateado (títulos, listas, tablas si aplica).
"""


def build_prompt(
    *,
    language: str,
    topic: str,
    role_key: str | None = None,
    role_custom: str | None = None,
    output_key: str | None = None,
    output_custom: str | None = None,
) -> str:
    role_txt = (
        (role_custom or "").strip()
        or ROLE_PRESETS.get(role_key or "", "").strip()
        or "Actuás como un asistente académico técnico y claro."
    )
    out_txt = (
        (output_custom or "").strip()
        or OUTPUT_PRESETS.get(output_key or "", "").strip()
        or "Generá un apunte detallado, estructurado, sin redundancias."
    )

    return f"""{BASE}

IDIOMA: {language}
TEMA/MATERIA: {topic}

ROL (contexto):
{role_txt}

TIPO DE SALIDA (requisitos):
{out_txt}
""".strip()
