"""
Modelo de datos para proyectos de álbumes en NFCito Studio (.nfcito).
Conserva imágenes, recortes, textos de contraportada, perfil activo y datos NFC.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
import time

@dataclass
class CropConfig:
    zoom: float = 1.0          # Factor de zoom (>= 1.0)
    pan_x: float = 0.0         # Desplazamiento horizontal relativo (-1.0 a 1.0)
    pan_y: float = 0.0         # Desplazamiento vertical relativo (-1.0 a 1.0)
    rotation: int = 0          # 0, 90, 180, 270 grados
    fit_mode: str = "cover"    # "cover" (llenar sin deformar), "contain" (encajar)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CropConfig":
        return cls(
            zoom=float(data.get("zoom", 1.0)),
            pan_x=float(data.get("pan_x", 0.0)),
            pan_y=float(data.get("pan_y", 0.0)),
            rotation=int(data.get("rotation", 0)),
            fit_mode=str(data.get("fit_mode", "cover")),
        )

@dataclass
class TextConfig:
    enabled: bool = False
    title: str = ""
    artist: str = ""
    tracks: str = ""           # Lista de canciones / créditos (multilínea)
    full_body_text: str = ""   # Texto completo libre tipo documento / Word
    font_family: str = "Arial"
    font_size: int = 8
    title_font_size: int = 10
    is_bold: bool = False
    is_italic: bool = False
    is_underline: bool = False
    text_color: str = "#000000"
    bg_color: Optional[str] = None  # Color de fondo opcional (ej. "#000000")
    bg_opacity: float = 0.0         # 0.0 (transparente) a 1.0 (sólido)
    alignment: str = "left"         # "left", "center", "right"
    vertical_align: str = "top"     # "top", "middle", "bottom"
    line_spacing: float = 1.2       # Factor de interlineado
    padding_mm: float = 2.0         # Margen interior

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextConfig":
        return cls(
            enabled=bool(data.get("enabled", False)),
            title=str(data.get("title", "")),
            artist=str(data.get("artist", "")),
            tracks=str(data.get("tracks", "")),
            full_body_text=str(data.get("full_body_text", "")),
            font_family=str(data.get("font_family", "Arial")),
            font_size=int(data.get("font_size", 8)),
            title_font_size=int(data.get("title_font_size", 10)),
            is_bold=bool(data.get("is_bold", False)),
            is_italic=bool(data.get("is_italic", False)),
            is_underline=bool(data.get("is_underline", False)),
            text_color=str(data.get("text_color", "#000000")),
            bg_color=data.get("bg_color"),
            bg_opacity=float(data.get("bg_opacity", 0.0)),
            alignment=str(data.get("alignment", "left")),
            vertical_align=str(data.get("vertical_align", "top")),
            line_spacing=float(data.get("line_spacing", 1.2)),
            padding_mm=float(data.get("padding_mm", 2.0)),
        )

@dataclass
class NFCConfig:
    album_title: str = ""
    artist: str = ""
    song_name: str = ""
    nfc_target_url: str = ""
    nfc_tag_type: str = "NTAG213"  # NTAG213, NTAG215, NTAG216
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NFCConfig":
        return cls(
            album_title=str(data.get("album_title", "")),
            artist=str(data.get("artist", "")),
            song_name=str(data.get("song_name", "")),
            nfc_target_url=str(data.get("nfc_target_url", "")),
            nfc_tag_type=str(data.get("nfc_tag_type", "NTAG213")),
            notes=str(data.get("notes", "")),
        )

@dataclass
class PieceDesign:
    piece_key: str             # "portada", "contraportada", "lomo", "cd", "interior"
    enabled_for_print: bool = True
    image_path: Optional[str] = None
    crop: CropConfig = field(default_factory=CropConfig)
    text_overlay: TextConfig = field(default_factory=TextConfig)
    custom_width_mm: Optional[float] = None
    custom_height_mm: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "piece_key": self.piece_key,
            "enabled_for_print": self.enabled_for_print,
            "image_path": self.image_path,
            "crop": self.crop.to_dict(),
            "text_overlay": self.text_overlay.to_dict(),
            "custom_width_mm": self.custom_width_mm,
            "custom_height_mm": self.custom_height_mm,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PieceDesign":
        return cls(
            piece_key=data.get("piece_key", "portada"),
            enabled_for_print=bool(data.get("enabled_for_print", True)),
            image_path=data.get("image_path"),
            crop=CropConfig.from_dict(data.get("crop", {})),
            text_overlay=TextConfig.from_dict(data.get("text_overlay", {})),
            custom_width_mm=data.get("custom_width_mm"),
            custom_height_mm=data.get("custom_height_mm"),
        )

@dataclass
class PrintLayoutConfig:
    paper_size: str = "A4"
    orientation: str = "portrait"     # "portrait" o "landscape"
    margin_mm: float = 8.0            # Margen exterior de la hoja
    spacing_mm: float = 4.0           # Espacio entre piezas
    show_cut_lines: bool = True
    include_calibration: bool = True  # Incluir página de calibración 50x50mm
    quantities: Dict[str, int] = field(default_factory=lambda: {
        "portada": 1,
        "contraportada": 1,
        "lomo": 1,
        "cd": 1,
        "interior": 1,
        "interior_contraportada": 0,
        "lomo_secundario": 0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrintLayoutConfig":
        default_q = {
            "portada": 1, "contraportada": 1, "lomo": 1,
            "cd": 1, "interior": 1, "interior_contraportada": 0, "lomo_secundario": 0
        }
        user_q = data.get("quantities", {})
        merged_q = {**default_q, **user_q}
        return cls(
            paper_size=data.get("paper_size", "A4"),
            orientation=data.get("orientation", "portrait"),
            margin_mm=float(data.get("margin_mm", 8.0)),
            spacing_mm=float(data.get("spacing_mm", 4.0)),
            show_cut_lines=bool(data.get("show_cut_lines", True)),
            include_calibration=bool(data.get("include_calibration", True)),
            quantities=merged_q,
        )

@dataclass
class Project:
    name: str = "Nuevo Álbum"
    profile_id: str = "default_mini_cd_50"
    pieces: Dict[str, PieceDesign] = field(default_factory=dict)
    nfc: NFCConfig = field(default_factory=NFCConfig)
    print_layout: PrintLayoutConfig = field(default_factory=PrintLayoutConfig)
    file_path: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def __post_init__(self):
        # Garantizar que existan las piezas base
        base_keys = [
            "portada", "contraportada", "lomo", "cd", "interior",
            "interior_contraportada", "lomo_secundario"
        ]
        for key in base_keys:
            if key not in self.pieces:
                # El fondo de bandeja y el lomo secundario son adicionales opcionales
                is_enabled = (key not in ["lomo_secundario", "interior_contraportada"])
                self.pieces[key] = PieceDesign(piece_key=key, enabled_for_print=is_enabled)

    def get_piece(self, key: str) -> PieceDesign:
        if key not in self.pieces:
            self.pieces[key] = PieceDesign(piece_key=key)
        return self.pieces[key]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "profile_id": self.profile_id,
            "pieces": {k: v.to_dict() for k, v in self.pieces.items()},
            "nfc": self.nfc.to_dict(),
            "print_layout": self.print_layout.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], file_path: Optional[str] = None) -> "Project":
        pieces_dict = {}
        for k, v in data.get("pieces", {}).items():
            pieces_dict[k] = PieceDesign.from_dict(v)

        return cls(
            name=data.get("name", "Nuevo Álbum"),
            profile_id=data.get("profile_id", "default_mini_cd_50"),
            pieces=pieces_dict,
            nfc=NFCConfig.from_dict(data.get("nfc", {})),
            print_layout=PrintLayoutConfig.from_dict(data.get("print_layout", {})),
            file_path=file_path,
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
