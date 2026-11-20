#!/bin/zsh
cd -- "${0:A:h}"
# L'environnement Python vit hors du dossier Desktop (synchronisé iCloud, qui bloquait les imports)
VENV="${STUDIO_VENV:-$HOME/.venvs/studio-editorial}"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" || exit 1
fi
if ! "$VENV/bin/python" -c 'import streamlit, defusedxml' 2>/dev/null; then
  "$VENV/bin/python" -m pip install -r requirements.txt || exit 1
fi
(sleep 4 && open http://127.0.0.1:8501) &
"$VENV/bin/python" -m streamlit run app.py --server.address=127.0.0.1 --server.headless=true
