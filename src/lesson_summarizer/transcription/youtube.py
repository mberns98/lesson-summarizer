from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yt_dlp

from .audio import transcribe_audio_file


def _clean_vtt_to_text(vtt: str) -> str:
    # Saca timestamps, headers, cues y tags básicos
    lines = []
    for raw in vtt.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("WEBVTT"):
            continue
        if "-->" in s:
            continue
        if re.fullmatch(r"\d+", s):  # cue index
            continue
        s = re.sub(r"<[^>]+>", "", s)  # remove HTML tags
        lines.append(s)
    return " ".join(lines).strip()


def _download_subtitles(url: str, *, prefer_manual: bool, lang: str | None) -> str | None:
    """
    Tries to download subtitles as .vtt and returns transcript text if found.
    prefer_manual=True: writesubtitles
    prefer_manual=False: writeautomaticsub
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = str(Path(tmpdir) / "subs.%(ext)s")

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "outtmpl": outtmpl,
            "writesubtitles": bool(prefer_manual),
            "writeautomaticsub": (not prefer_manual),
            "subtitlesformat": "vtt",
        }

        # Si lang es None: dejamos que yt-dlp agarre lo que haya.
        # Si querés forzar español, pasá lang="es".
        if lang:
            ydl_opts["subtitleslangs"] = [lang, f"{lang}-ES", f"{lang}-419", f"{lang}-US"]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # yt-dlp crea archivos tipo subs.es.vtt / subs.en.vtt, etc.
        vtt_files = sorted(Path(tmpdir).glob("subs*.vtt"))
        if not vtt_files:
            return None

        # Elegimos el primero (si querés, mejoramos: priorizar exact match de idioma)
        vtt_path = vtt_files[0]
        vtt_text = vtt_path.read_text(encoding="utf-8", errors="ignore")
        return _clean_vtt_to_text(vtt_text) or None


def _download_audio_for_whisper(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        outtmpl = os.path.join(tmpdir, "audio.%(ext)s")
        wav_path = os.path.join(tmpdir, "audio.wav")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # devolvemos un path fuera del context? no; así que copiamos a un NamedTemporaryFile persistente
        import shutil
        import tempfile as tf

        fd, persistent_path = tf.mkstemp(suffix=".wav")
        os.close(fd)
        shutil.copyfile(wav_path, persistent_path)
        return persistent_path


def get_youtube_text(
    url: str,
    *,
    subtitles_lang: str | None = None,
    whisper_lang: str | None = None,
) -> str:
    url = (url or "").strip()
    if not url:
        raise ValueError("URL de YouTube vacía.")

    # 1) Manual subtitles
    txt = _download_subtitles(url, prefer_manual=True, lang=subtitles_lang)
    if txt:
        return txt

    # 2) Auto subtitles
    txt = _download_subtitles(url, prefer_manual=False, lang=subtitles_lang)
    if txt:
        return txt

    # 3) Fallback: Whisper
    wav_path = _download_audio_for_whisper(url)
    try:
        return transcribe_audio_file(wav_path, language=whisper_lang)
    finally:
        try:
            os.remove(wav_path)
        except OSError:
            pass
