"""
Lanzador principal de NFCito Studio.
Ejecutar con: python run_app.py
"""
import sys
from pathlib import Path

# Agregar directorio raíz al PYTHONPATH
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from nfcito.app import main

if __name__ == "__main__":
    main()
