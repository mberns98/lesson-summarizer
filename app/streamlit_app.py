from __future__ import annotations

import uuid  # Generate unique run IDs (used for naming outputs and tracking a generation run)
import streamlit as st
import re
from dataclasses import dataclass
from lesson_summarizer.core import summarize_long_text_to_markdown

from lesson_summarizer.pdf_export import markdown_to_pdf_bytes

import tempfile
from lesson_summarizer.transcription.youtube import get_youtube_text
from lesson_summarizer.transcription.audio import transcribe_audio_file

from dotenv import load_dotenv
load_dotenv()  # Load .env file if present to set GEMINI_API_KEY, etc.


# -----------------------------
# Presets (UI contract)
# -----------------------------
ROLE_PRESETS = {
    "philosophy_expert": "Filosofía (experto)",
    "history_professor": "Historia (profesor)",
    "data_engineer": "Data Engineer",
    "data_scientist": "Data Scientist (DL)",
    "ai_engineer": "AI Engineer",
}

OUTPUT_PRESETS = {
    "apunte_detallado": "Apunte detallado",
    "resumen": "Resumen",
    "lista_de_conceptos": "Lista de conceptos",
    "preguntas_de_revision": "Preguntas de revisión",
}

LANG_OPTIONS = ["es", "en", "pt", "fr"]


@dataclass
class UIState:
    """
    Container for all user-selected UI settings.

    This object represents the "contract" between the Streamlit UI and the backend.
    It is stored in st.session_state to persist values across Streamlit reruns.
    """
    input_type: str = "text"  # Input source type selected by the user (text / youtube / audio)
    input_language: str = "auto"   # Input language of the source (for transcription); "auto" means auto-detect
    output_language: str = "es"    # Output language for the generated document (passed to the prompt)
    topic: str = "Clase"  # Subject or course context provided by the user (used as prompt context)
    title: str = ""  # Optional document title (used for markdown header and file naming)
    role_key: str = "philosophy_expert"  # Selected role preset key (mapped to prompt instructions later)
    role_custom: str = ""  # Optional free-text role description; overrides the preset if provided
    output_key: str = "apunte_detallado"  # Selected output format preset key
    output_custom: str = ""  # Optional custom output instructions; overrides the preset if provided


def _init_state() -> None:
    """
    Initialize Streamlit session state.

    Streamlit reruns the script on every user interaction.
    This function ensures that required state objects exist
    so user inputs are not lost across reruns.
    """

    if "ui" not in st.session_state:
        st.session_state.ui = UIState()
        # Create the UIState object only on the first run,
        # and keep it persistent across Streamlit reruns
    if "input_text" not in st.session_state:
        st.session_state.input_text = ""
        # Store the raw text input separately to avoid coupling large text blobs
        # directly to the UIState configuration object 

def _safe_filename(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "documento"

    # reemplaza espacios por guiones bajos
    name = re.sub(r"\s+", "_", name)

    # deja solo letras, números, guion, underscore y punto
    name = re.sub(r"[^A-Za-z0-9._-]", "", name)

    # evita nombres vacíos o solo símbolos
    return name or "documento"

def main() -> None:
    """
    Main Streamlit application entry point.

    This function is re-executed on every Streamlit interaction.
    All UI rendering and event handling happens here.
    """
    # Initialize session state and keep a local reference
    # to avoid repeated access to st.session_state
    _init_state()
    ui: UIState = st.session_state.ui

    # Configure Streamlit page settings (must be called before rendering UI)
    st.set_page_config(page_title="Lesson Summarizer", layout="wide")

    # Header
    st.title("📚 Lesson Summarizer")
    st.caption("Input: texto / YouTube / audio · Output: Markdown/PDF (más adelante)")

    # -----------------------------
    # Sidebar: all configuration inputs that define the backend contract
    # -----------------------------
    with st.sidebar:
        st.header("⚙️ Configuración")

        # Use index lookup to preserve the current selection across reruns
        ui.input_type = st.selectbox(
            "Input",
            options=["text", "youtube", "audio"],
            index=["text", "youtube", "audio"].index(ui.input_type),
        )

        ui.input_language = st.selectbox(
            "Idioma del contenido (input)",
            options=["auto", "es", "en", "pt", "fr"],
            index=["auto", "es", "en", "pt", "fr"].index(ui.input_language)
            if ui.input_language in ["auto", "es", "en", "pt", "fr"]
            else 0,
        )

        ui.output_language = st.selectbox(
            "Idioma del resumen (output)",
            options=LANG_OPTIONS,
            index=LANG_OPTIONS.index(ui.output_language)
            if ui.output_language in LANG_OPTIONS
            else 0,
        )
        st.divider()

        # Contextual metadata passed to the prompt (not extracted from the input text)
        ui.topic = st.text_input("Tema / materia", value=ui.topic)
        ui.title = st.text_input("Título del documento", value=ui.title, placeholder="(opcional)")

        st.divider()

        # Role preset + custom
        # If custom role is provided, it will override the preset at prompt-building time
        st.subheader("Rol")
        ui.role_key = st.selectbox(
            "Preset de rol",
            options=list(ROLE_PRESETS.keys()),
            format_func=lambda k: ROLE_PRESETS.get(k, k),
            index=list(ROLE_PRESETS.keys()).index(ui.role_key)
            if ui.role_key in ROLE_PRESETS
            else 0,
        )
        ui.role_custom = st.text_area(
            "Rol custom (opcional)",
            value=ui.role_custom,
            placeholder="Si escribís acá, pisa el preset.\nEj: Actuás como profesor exigente y súper claro…",
            height=90,
        )

        st.divider()

        # Output preset + custom
        st.subheader("Tipo de salida")
        ui.output_key = st.selectbox(
            "Preset de salida",
            options=list(OUTPUT_PRESETS.keys()),
            format_func=lambda k: OUTPUT_PRESETS.get(k, k),
            index=list(OUTPUT_PRESETS.keys()).index(ui.output_key)
            if ui.output_key in OUTPUT_PRESETS
            else 0,
        )
        ui.output_custom = st.text_area(
            "Salida custom (opcional)",
            value=ui.output_custom,
            placeholder="Si escribís acá, pisa el preset.\nEj: hacé un apunte con definiciones + bullets + ejemplo…",
            height=90,
        )

        st.divider()

    # -----------------------------
    # Main layout: input and actions on the left, preview and downloads on the right
    # -----------------------------
    col_left, col_right = st.columns([2, 1], vertical_alignment="top")

    with col_left:
        if ui.input_type == "text":
            st.subheader("📝 Texto")
            st.caption("Pegá tu transcripción acá")
            # Store the input text in session_state to persist across reruns
            st.session_state.input_text = st.text_area(
                "Transcripción",
                value=st.session_state.input_text,
                placeholder="Pegá acá el texto…",
                height=300,
                label_visibility="collapsed",
            )

        elif ui.input_type == "youtube":
            st.subheader("▶️ YouTube")
            # Placeholder UI: extraction/transcription
            st.session_state.youtube_url = st.text_input(
                                                            "URL de YouTube",
                                                            value=st.session_state.get("youtube_url", ""),
                                                            placeholder="https://www.youtube.com/watch?v=...",
                                                        )


        elif ui.input_type == "audio":
            st.subheader("🎧 Audio")
            st.caption("Todavía no está implementada la transcripción. Por ahora solo UI.")
            uploaded_audio = st.file_uploader("Subí un audio", type=["mp3", "wav", "m4a", "flac", "mp4"])
            st.session_state.uploaded_audio = uploaded_audio

        st.write("")

        # Trigger generation on button click
        run = st.button("🚀 Generar", type="primary", use_container_width=True)

        if run:
            try:
                run_id = uuid.uuid4().hex[:10]
                # --- Resolver input -> texto ---
                if ui.input_type == "text":
                    text = st.session_state.input_text

                elif ui.input_type == "youtube":
                    url = (st.session_state.get("youtube_url") or "").strip()
                    if not url:
                        raise ValueError("Falta URL de YouTube.")
                    with st.spinner("Obteniendo transcripción de YouTube..."):
                        text = get_youtube_text(
                        url,
                        subtitles_lang=None if ui.input_language == "auto" else ui.input_language,
                        whisper_lang=None if ui.input_language == "auto" else ui.input_language,
                    )
                    st.session_state.input_text = text  # opcional: para poder verlo si cambiás a 'text'

                elif ui.input_type == "audio":
                    uploaded = st.session_state.get("uploaded_audio")
                    if uploaded is None:
                        raise ValueError("Falta subir un archivo de audio/video.")
                    suffix = "." + uploaded.name.split(".")[-1].lower() if "." in uploaded.name else ".bin"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded.getbuffer())
                        tmp_path = tmp.name
                    try:
                        with st.spinner("Transcribiendo audio..."):
                            text = transcribe_audio_file(
                                tmp_path,
                                language=None if ui.input_language == "auto" else ui.input_language,
                            )
                        st.session_state.input_text = text
                    finally:
                        import os
                        try:
                            os.remove(tmp_path)
                        except OSError:
                            pass

                else:
                    raise ValueError(f"Input type no soportado: {ui.input_type}")
                # --- Fin resolver input ---


                md = summarize_long_text_to_markdown(
                                                    text=text,
                                                    language=ui.output_language,
                                                    topic=ui.topic,
                                                    role_key=ui.role_key,
                                                    role_custom=ui.role_custom,
                                                    output_key=ui.output_key,
                                                    output_custom=ui.output_custom,
                                                    chunk_size_chars=10_000,
                                                    overlap_chars=500,
                                                    )
                
                pdf_bytes = markdown_to_pdf_bytes(md, title=ui.title or "Resumen")
                st.session_state.last_run = {
                    "run_id": run_id,
                    "markdown": md,
                    "pdf_bytes": pdf_bytes,
                    "title": ui.title,
                }
                st.success(f"Listo. Run ID: {run_id}")

            except Exception as e:
                st.error(str(e))



    with col_right:
        st.subheader("👀 Preview")
        # Render preview and downloads only if a generation has already run
        last = st.session_state.get("last_run")
        if not last:
            st.info("Todavía no generaste nada.")
        else:
            st.markdown(last["markdown"])

            st.download_button(
                "⬇️ Descargar Markdown",
                data=last["markdown"].encode("utf-8"),
                file_name=f"{_safe_filename(last.get('title') or last['run_id'])}.md",
                mime="text/markdown",
                use_container_width=True,
            )

            # Placeholder “PDF” para que la UX quede armada
            st.download_button(
                "⬇️ Descargar PDF",
                data=last["pdf_bytes"],
                file_name=f"{_safe_filename(last.get('title') or last['run_id'])}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
