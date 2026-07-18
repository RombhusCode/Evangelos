# Evangelos

Local-first AI communications assistant.

## Setup

```bash
.venv/bin/python -m pip install -r requirements.txt
PLAYWRIGHT_BROWSERS_PATH="$PWD/.playwright-browsers" .venv/bin/python -m playwright install chromium
```

## Run

```bash
.venv/bin/python -m streamlit run app.py
```

## Verify

```bash
.venv/bin/python -m pytest
```
