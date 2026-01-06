from __future__ import annotations

import html
import re


def clean_subtitles(raw: str) -> str:
    """
    Basic cleanup for transcripts/subtitles (SRT/VTT-ish):
    - remove timestamps
    - remove arrow separators
    - remove numeric index lines
    - unescape HTML entities
    - normalize whitespace
    """
    text = raw or ""

    text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}", "", text)   # timestamps
    text = re.sub(r"\s*-->\s*", " ", text)                  # arrows
    text = re.sub(r"^\d+\s*$", "", text, flags=re.MULTILINE) # SRT indices
    text = html.unescape(text)                               # HTML entities
    text = re.sub(r"\s+", " ", text)                         # whitespace

    return text.strip()
