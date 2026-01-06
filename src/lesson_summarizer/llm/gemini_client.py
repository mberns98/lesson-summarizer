from __future__ import annotations

import os
import streamlit as st
from google import genai


@st.cache_resource
def get_client() -> genai.Client:
    """
    Create a GenAI client using an API key from the environment.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY (or GOOGLE_API_KEY) in environment/.env")

    return genai.Client(api_key=api_key)


def generate_text(prompt: str, *, model: str = "gemini-2.5-flash") -> str:
    """
    Minimal wrapper: prompt -> text output.
    """
    client = get_client()
    resp = client.models.generate_content(model=model, contents=prompt)
    # SDK returns a structured response; .text is the convenient plain string view
    return (resp.text or "").strip()
