"""
Configuración global y rutas de persistencia de NFCito Studio.
"""
from pathlib import Path
import os
import json

APP_NAME = "NFCito Studio"
APP_VERSION = "1.0.0"

# Directorio de datos del usuario
USER_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "NFCitoStudio"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

PROFILES_FILE = USER_DATA_DIR / "profiles.json"
SETTINGS_FILE = USER_DATA_DIR / "settings.json"
PROJECTS_DIR = USER_DATA_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS = {
    "last_profile_id": "default_mini_cd_50",
    "last_paper_size": "A4",
    "export_dpi": 300,
    "show_safe_margin": True,
    "show_bleed_margin": True,
    "show_cut_lines": True,
    "unprintable_margin_mm": 5.0,  # Margen típico no imprimible de impresoras domésticas
}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
        except Exception:
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
