"""
Conversiones de unidades de alta precisión: Milímetros (mm), Puntos PDF (pt) y Píxeles (px).
1 pulgada = 25.4 mm = 72 puntos tipográficos (PostScript / PDF).
"""

MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0
POINTS_PER_MM = POINTS_PER_INCH / MM_PER_INCH  # ~2.834645669291339

def mm_to_pt(mm: float) -> float:
    """Convierte milímetros a puntos PDF."""
    return float(mm) * POINTS_PER_MM

def pt_to_mm(pt: float) -> float:
    """Convierte puntos PDF a milímetros."""
    return float(pt) / POINTS_PER_MM

def mm_to_px(mm: float, dpi: int = 300) -> int:
    """Convierte milímetros a píxeles enteros al DPI especificado (por defecto 300 DPI)."""
    return int(round((float(mm) / MM_PER_INCH) * dpi))

def px_to_mm(px: int, dpi: int = 300) -> float:
    """Convierte píxeles a milímetros según el DPI."""
    return (float(px) / dpi) * MM_PER_INCH

# Tamaños de papel comunes en milímetros (ancho x alto)
PAPER_SIZES_MM = {
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "Carta (Letter)": (215.9, 279.4),
    "Oficio (Legal)": (215.9, 355.6),
    "4x6 pulgadas (Foto)": (101.6, 152.4),
    "A6": (105.0, 148.0),
}
