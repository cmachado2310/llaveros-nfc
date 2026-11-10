"""
Modelos de perfiles de medidas para estuches de mini CD / llaveros.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

@dataclass
class PieceDimension:
    width_mm: float
    height_mm: float
    enabled: bool = True
    is_circular: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PieceDimension":
        return cls(
            width_mm=float(data.get("width_mm", 48.0)),
            height_mm=float(data.get("height_mm", 48.0)),
            enabled=bool(data.get("enabled", True)),
            is_circular=bool(data.get("is_circular", False))
        )

@dataclass
class CDDimension:
    outer_diameter_mm: float
    inner_hole_diameter_mm: float = 10.0
    has_inner_hole: bool = True
    enabled: bool = True
    
    @property
    def width_mm(self) -> float:
        return self.outer_diameter_mm
        
    @property
    def height_mm(self) -> float:
        return self.outer_diameter_mm

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CDDimension":
        return cls(
            outer_diameter_mm=float(data.get("outer_diameter_mm", 40.0)),
            inner_hole_diameter_mm=float(data.get("inner_hole_diameter_mm", 10.0)),
            has_inner_hole=bool(data.get("has_inner_hole", True)),
            enabled=bool(data.get("enabled", True))
        )

@dataclass
class CaseProfile:
    id: str
    name: str
    description: str = ""
    # Dimensiones exteriores del estuche físico (solo referencia para el usuario)
    exterior_width_mm: float = 53.0
    exterior_height_mm: float = 53.0
    exterior_depth_mm: float = 8.0
    
    # Dimensiones de piezas individuales de impresión
    portada: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=48.0, height_mm=48.0))
    contraportada: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=48.0, height_mm=48.0))
    interior_contraportada: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True))
    lomo: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=5.0, height_mm=48.0))
    lomo_secundario: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=5.0, height_mm=48.0, enabled=False))
    cd: CDDimension = field(default_factory=lambda: CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0))
    interior: PieceDimension = field(default_factory=lambda: PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True))
    
    # Opción para imprimir lomo y contraportada (o portada + lomo + contraportada) en una pieza continua
    continuous_tray: bool = False  # Si es True, contraportada + lomo o portada+lomo+contra se unen
    
    # Parámetros de precisión y corte
    safe_margin_mm: float = 1.5
    bleed_mm: float = 1.5
    separation_mm: float = 3.0
    preferred_paper: str = "A4"
    show_cut_lines: bool = True
    
    # Marca si es un perfil de fábrica provisional
    is_provisional: bool = False

    def get_piece_dimension(self, piece_key: str) -> Optional[PieceDimension]:
        if piece_key == "portada":
            return self.portada
        elif piece_key == "contraportada":
            return self.contraportada
        elif piece_key == "interior_contraportada":
            return self.interior_contraportada
        elif piece_key == "lomo":
            return self.lomo
        elif piece_key == "lomo_secundario":
            return self.lomo_secundario
        elif piece_key == "cd":
            return PieceDimension(
                width_mm=self.cd.outer_diameter_mm,
                height_mm=self.cd.outer_diameter_mm,
                enabled=self.cd.enabled,
                is_circular=True
            )
        elif piece_key == "interior":
            return self.interior
        elif piece_key == "bandeja_continua":
            # Ancho total = portada + lomo + contraportada (o lomo + contraportada)
            total_w = self.portada.width_mm + self.lomo.width_mm + self.contraportada.width_mm
            return PieceDimension(
                width_mm=total_w,
                height_mm=max(self.portada.height_mm, self.contraportada.height_mm),
                enabled=self.continuous_tray
            )
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "exterior_width_mm": self.exterior_width_mm,
            "exterior_height_mm": self.exterior_height_mm,
            "exterior_depth_mm": self.exterior_depth_mm,
            "portada": self.portada.to_dict(),
            "contraportada": self.contraportada.to_dict(),
            "interior_contraportada": self.interior_contraportada.to_dict(),
            "lomo": self.lomo.to_dict(),
            "lomo_secundario": self.lomo_secundario.to_dict(),
            "cd": self.cd.to_dict(),
            "interior": self.interior.to_dict(),
            "continuous_tray": self.continuous_tray,
            "safe_margin_mm": self.safe_margin_mm,
            "bleed_mm": self.bleed_mm,
            "separation_mm": self.separation_mm,
            "preferred_paper": self.preferred_paper,
            "show_cut_lines": self.show_cut_lines,
            "is_provisional": self.is_provisional,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CaseProfile":
        portada_dim = PieceDimension.from_dict(data.get("portada", {}))
        contra_dim = PieceDimension.from_dict(data.get("contraportada", {}))
        lomo_dim = PieceDimension.from_dict(data.get("lomo", {}))
        
        # Interior de contraportada (fondo de bandeja): por defecto mismas dimensiones que contraportada
        if "interior_contraportada" in data:
            interior_contra_dim = PieceDimension.from_dict(data["interior_contraportada"])
        else:
            interior_contra_dim = PieceDimension(
                width_mm=contra_dim.width_mm,
                height_mm=contra_dim.height_mm,
                enabled=True
            )

        # Lomo secundario (borde opcional): por defecto mismas dimensiones que el lomo pero deshabilitado
        if "lomo_secundario" in data:
            lomo_sec_dim = PieceDimension.from_dict(data["lomo_secundario"])
        else:
            lomo_sec_dim = PieceDimension(
                width_mm=lomo_dim.width_mm,
                height_mm=lomo_dim.height_mm,
                enabled=False
            )
        
        # El libreto interior es un poco más pequeño (1.5mm) que la portada para deslizarse sin trabas
        interior_raw = data.get("interior")
        if interior_raw:
            interior_dim = PieceDimension.from_dict(interior_raw)
            # Si el interior tenía la misma medida que la portada o venía de un perfil antiguo
            if interior_dim.width_mm >= portada_dim.width_mm:
                interior_dim.width_mm = max(5.0, round(portada_dim.width_mm - 1.5, 1))
            if interior_dim.height_mm >= portada_dim.height_mm:
                interior_dim.height_mm = max(5.0, round(portada_dim.height_mm - 1.5, 1))
        else:
            interior_dim = PieceDimension(
                width_mm=max(5.0, round(portada_dim.width_mm - 1.5, 1)),
                height_mm=max(5.0, round(portada_dim.height_mm - 1.5, 1)),
                enabled=True
            )

        return cls(
            id=data.get("id", "custom"),
            name=data.get("name", "Perfil Personalizado"),
            description=data.get("description", ""),
            exterior_width_mm=float(data.get("exterior_width_mm", 53.0)),
            exterior_height_mm=float(data.get("exterior_height_mm", 53.0)),
            exterior_depth_mm=float(data.get("exterior_depth_mm", 8.0)),
            portada=portada_dim,
            contraportada=contra_dim,
            interior_contraportada=interior_contra_dim,
            lomo=lomo_dim,
            lomo_secundario=lomo_sec_dim,
            cd=CDDimension.from_dict(data.get("cd", {})),
            interior=interior_dim,
            continuous_tray=bool(data.get("continuous_tray", False)),
            safe_margin_mm=float(data.get("safe_margin_mm", 1.5)),
            bleed_mm=float(data.get("bleed_mm", 1.5)),
            separation_mm=float(data.get("separation_mm", 3.0)),
            preferred_paper=data.get("preferred_paper", "A4"),
            show_cut_lines=bool(data.get("show_cut_lines", True)),
            is_provisional=bool(data.get("is_provisional", False)),
        )
