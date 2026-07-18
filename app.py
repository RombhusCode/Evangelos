"""Streamlit dashboard entry point for Evangelos."""

from __future__ import annotations

import streamlit as st

from database.session import initialize_database


def main() -> None:
    """Render the initial Evangelos dashboard shell."""
    initialize_database()

    st.set_page_config(page_title="Evangelos", page_icon="E", layout="wide")
    st.title("Evangelos")
    st.caption("Local-first communications intelligence")

    st.subheader("Today")
    st.info("Project scaffold is ready. Data collection and summaries come next.")


if __name__ == "__main__":
    main()
