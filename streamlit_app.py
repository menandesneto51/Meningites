# -*- coding: utf-8 -*-
"""Entry point padrão do Streamlit Cloud (main file: streamlit_app.py)."""
from pathlib import Path
import runpy

APP = Path(__file__).resolve().parent / "dashboard_meningites_v22_refinado.py"
runpy.run_path(str(APP), run_name="__main__")
