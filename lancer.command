#!/bin/zsh
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || exit 1
fi
if ! .venv/bin/python -c 'import streamlit' 2>/dev/null; then
  .venv/bin/python -m pip install -r requirements.txt || exit 1
fi
(sleep 4 && open http://127.0.0.1:8501) &
.venv/bin/python -m streamlit run app.py --server.address=127.0.0.1 --server.headless=true
