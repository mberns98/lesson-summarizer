from __future__ import annotations

import os
from dataclasses import dataclass

import streamlit as st
from faster_whisper import WhisperModel


@dataclass(frozen=True)
class WhisperConfig:
    model_size: str = "small"
    device: str = "cpu"          # en Docker default CPU
    compute_type: str = "int8"   # rápido en CPU, suficiente para resumen


@st.cache_resource
def _get_whisper_model(cfg: WhisperConfig) -> WhisperModel:
    return WhisperModel(cfg.model_size, device=cfg.device, compute_type=cfg.compute_type)


def transcribe_audio_file(
    file_path: str,
    *,
    language: str | None = None,
    cfg: WhisperConfig = WhisperConfig(),
) -> str:
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"No existe el archivo: {file_path}")

    model = _get_whisper_model(cfg)

    segments, info = model.transcribe(
        file_path,
        language=language,   # None = autodetect
        vad_filter=True,     # reduce silencios/ruido
    )

    text_parts = [seg.text.strip() for seg in segments if seg.text and seg.text.strip()]
    return " ".join(text_parts).strip()
