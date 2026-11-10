"""
Modelos para la distribución de piezas en hojas de impresión.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Any

@dataclass
class PlacedItem:
    piece_key: str
    display_name: str
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    is_circular: bool = False
    inner_hole_mm: float = 0.0
    has_inner_hole: bool = False
    rotation: int = 0
    copy_index: int = 0
    source_project: Optional[Any] = None
    project_name: str = ""

@dataclass
class PrintPage:
    page_number: int
    paper_size_name: str
    paper_width_mm: float
    paper_height_mm: float
    items: List[PlacedItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class LayoutResult:
    pages: List[PrintPage]
    total_items_placed: int
    unplaced_items: List[str]
    warnings: List[str]
