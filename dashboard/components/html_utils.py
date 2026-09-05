"""
AUREVIX — Safe HTML & CSS Rendering Utility
Strips line indentation from multiline HTML and provides cached CSS injection for instantaneous page transitions.
"""

from pathlib import Path
import streamlit as st

_CSS_CACHE: str = ""


def render_html(html_str: str):
    """Strip line-leading indentation to prevent Markdown code block triggers."""
    cleaned_lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    st.markdown(" ".join(cleaned_lines), unsafe_allow_html=True)


def load_cached_css(css_path: Path):
    """Cache CSS in Python memory to eliminate repetitive disk reads."""
    global _CSS_CACHE
    if not _CSS_CACHE and css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            _CSS_CACHE = f.read()
    if _CSS_CACHE:
        st.markdown(f"<style>{_CSS_CACHE}</style>", unsafe_allow_html=True)
