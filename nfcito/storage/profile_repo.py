"""
Repositorio y persistencia de perfiles de medidas en formato JSON.
"""
import json
import uuid
from typing import List, Optional, Dict
from pathlib import Path

from nfcito.models.profile import CaseProfile, PieceDimension, CDDimension
from nfcito.config import PROFILES_FILE, load_settings, save_settings

DEFAULT_PROFILES: List[CaseProfile] = [
    CaseProfile(
        id="default_mini_cd_50",
        name="Mini CD Estuche Estándar 50x50 mm (Provisional)",
        description="Medidas provisionales típicas para llavero mini CD estándar (~53x53 mm exterior). Requiere verificar con calibre o regla.",
        exterior_width_mm=53.0,
        exterior_height_mm=53.0,
        exterior_depth_mm=8.0,
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=False),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0, has_inner_hole=True, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
        continuous_tray=False,
        safe_margin_mm=1.5,
        bleed_mm=1.5,
        separation_mm=3.0,
        preferred_paper="A4",
        show_cut_lines=True,
        is_provisional=True,
    ),
    CaseProfile(
        id="default_mini_cd_compact_45",
        name="Mini CD Estuche Compacto 45x45 mm (Provisional)",
        description="Medidas provisionales para mini estuche compacto (~48x48 mm exterior).",
        exterior_width_mm=48.0,
        exterior_height_mm=48.0,
        exterior_depth_mm=7.0,
        portada=PieceDimension(width_mm=43.0, height_mm=43.0, enabled=True),
        contraportada=PieceDimension(width_mm=43.0, height_mm=43.0, enabled=True),
        interior_contraportada=PieceDimension(width_mm=43.0, height_mm=43.0, enabled=True),
        lomo=PieceDimension(width_mm=4.5, height_mm=43.0, enabled=True),
        lomo_secundario=PieceDimension(width_mm=4.5, height_mm=43.0, enabled=False),
        cd=CDDimension(outer_diameter_mm=36.0, inner_hole_diameter_mm=8.0, has_inner_hole=True, enabled=True),
        interior=PieceDimension(width_mm=41.5, height_mm=41.5, enabled=True),
        continuous_tray=False,
        safe_margin_mm=1.2,
        bleed_mm=1.5,
        separation_mm=3.0,
        preferred_paper="A4",
        show_cut_lines=True,
        is_provisional=True,
    ),
    CaseProfile(
        id="default_mini_cd_unfolded",
        name="Mini CD Inlay Continuo Desplegado (Provisional)",
        description="Plantilla de una sola pieza desplegada (Contraportada + Lomo + Portada) para doblar en el estuche.",
        exterior_width_mm=53.0,
        exterior_height_mm=53.0,
        exterior_depth_mm=8.0,
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=False),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0, has_inner_hole=True, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
        continuous_tray=True,
        safe_margin_mm=1.5,
        bleed_mm=1.5,
        separation_mm=3.0,
        preferred_paper="A4",
        show_cut_lines=True,
        is_provisional=True,
    ),
]

class ProfileRepository:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path or PROFILES_FILE
        self._profiles: Dict[str, CaseProfile] = {}
        self.load_all()

    def load_all(self) -> Dict[str, CaseProfile]:
        """Carga todos los perfiles guardados o inicializa con los perfiles predeterminados."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._profiles = {item["id"]: CaseProfile.from_dict(item) for item in data}
                    # Actualizar perfiles guardados antiguos si tenían medidas viejas de interior
                    needs_save = False
                    for p in self._profiles.values():
                        if p.interior.width_mm >= p.portada.width_mm:
                            p.interior.width_mm = max(5.0, round(p.portada.width_mm - 1.5, 1))
                            p.interior.height_mm = max(5.0, round(p.portada.height_mm - 1.5, 1))
                            needs_save = True
                        if not p.interior.enabled and p.id.startswith("default_"):
                            p.interior.enabled = True
                            needs_save = True
                    if needs_save:
                        self.save_all()
            except Exception as e:
                print(f"Aviso: No se pudo leer {self.file_path}: {e}. Inicializando perfiles base.")
                self._initialize_defaults()
        else:
            self._initialize_defaults()
            self.save_all()
        return self._profiles

    def _initialize_defaults(self):
        self._profiles = {p.id: p for p in DEFAULT_PROFILES}

    def save_all(self) -> None:
        """Guarda todos los perfiles de forma persistente en disco."""
        try:
            data = [p.to_dict() for p in self._profiles.values()]
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar perfiles en {self.file_path}: {e}")
            raise

    def get_all(self) -> List[CaseProfile]:
        return list(self._profiles.values())

    def get_by_id(self, profile_id: str) -> Optional[CaseProfile]:
        return self._profiles.get(profile_id)

    def save_profile(self, profile: CaseProfile) -> None:
        """Agrega o actualiza un perfil y persiste los cambios."""
        self._profiles[profile.id] = profile
        self.save_all()

    def duplicate_profile(self, profile_id: str, new_name: str) -> CaseProfile:
        original = self.get_by_id(profile_id)
        if not original:
            raise ValueError(f"Perfil {profile_id} no encontrado.")
        new_data = original.to_dict()
        new_id = f"custom_{uuid.uuid4().hex[:8]}"
        new_data["id"] = new_id
        new_data["name"] = new_name
        new_data["is_provisional"] = False
        new_profile = CaseProfile.from_dict(new_data)
        self.save_profile(new_profile)
        return new_profile

    def create_profile(self, name: str, description: str = "") -> CaseProfile:
        new_id = f"custom_{uuid.uuid4().hex[:8]}"
        profile = CaseProfile(
            id=new_id,
            name=name,
            description=description,
            is_provisional=False
        )
        self.save_profile(profile)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self.save_all()
            return True
        return False

    def get_active_profile_id(self) -> str:
        settings = load_settings()
        last_id = settings.get("last_profile_id", "default_mini_cd_50")
        if last_id in self._profiles:
            return last_id
        # Retorna el primero si no existe el último
        if self._profiles:
            return next(iter(self._profiles.keys()))
        return "default_mini_cd_50"

    def set_active_profile_id(self, profile_id: str) -> None:
        settings = load_settings()
        settings["last_profile_id"] = profile_id
        save_settings(settings)
