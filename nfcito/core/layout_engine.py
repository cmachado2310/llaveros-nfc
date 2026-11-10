"""
Motor de diagramación y distribución de piezas en hojas de impresión.
Evita superposiciones, respeta márgenes de impresora y genera múltiples páginas si es necesario.
"""
from typing import List, Dict, Optional, Tuple
from nfcito.models.project import Project
from nfcito.models.profile import CaseProfile
from nfcito.models.sheet import PlacedItem, PrintPage, LayoutResult
from nfcito.core.units import PAPER_SIZES_MM

PIECE_NAMES_ES = {
    "portada": "Portada Frontal",
    "contraportada": "Contraportada",
    "interior_contraportada": "Fondo Bandeja (Interior Contraportada)",
    "lomo": "Lomo / Lateral",
    "lomo_secundario": "Lomo Secundario (Borde Opcional)",
    "cd": "Etiqueta CD",
    "interior": "Interior / Libreto",
    "bandeja_continua": "Inlay Continuo (Portada + Lomo + Contra)",
}

class LayoutEngine:
    @staticmethod
    def compute_layout(
        project: Project,
        profile: CaseProfile,
        paper_size_name: str = "A4",
        orientation: str = "portrait",
        margin_mm: float = 6.0,
        spacing_mm: float = 2.5,
        quantities: Optional[Dict[str, int]] = None,
        only_selected: bool = False,
        unprintable_margin_mm: float = 5.0,
    ) -> LayoutResult:
        """
        Calcula la distribución óptima de piezas sin escalarlas (escala 100% física).
        Agrega páginas adicionales si no caben en una sola hoja.
        """
        base_w, base_h = PAPER_SIZES_MM.get(paper_size_name, (210.0, 297.0))
        if orientation == "landscape":
            paper_w, paper_h = max(base_w, base_h), min(base_w, base_h)
        else:
            paper_w, paper_h = min(base_w, base_h), max(base_w, base_h)

        quantities = quantities or project.print_layout.quantities

        # Lista de elementos a colocar: (key, width, height, is_circular, inner_hole, has_inner, source_project)
        items_to_place: List[Tuple[str, float, float, bool, float, bool, Optional[Project]]] = []

        if profile.continuous_tray:
            # Caso bandeja continua
            cont_w = profile.portada.width_mm + profile.lomo.width_mm + profile.contraportada.width_mm
            cont_h = max(profile.portada.height_mm, profile.contraportada.height_mm, profile.lomo.height_mm)
            qty = quantities.get("bandeja_continua", quantities.get("portada", 1))
            for i in range(qty):
                items_to_place.append(("bandeja_continua", cont_w, cont_h, False, 0.0, False, project))

            # Añadir CD e interior si están habilitados en el proyecto
            if project.get_piece("cd").enabled_for_print and quantities.get("cd", 1) > 0:
                for i in range(quantities.get("cd", 1)):
                    items_to_place.append((
                        "cd",
                        profile.cd.outer_diameter_mm,
                        profile.cd.outer_diameter_mm,
                        True,
                        profile.cd.inner_hole_diameter_mm,
                        profile.cd.has_inner_hole,
                        project
                    ))
            p_int = project.get_piece("interior")
            if p_int.enabled_for_print and quantities.get("interior", 1) > 0:
                dim_int = profile.get_piece_dimension("interior")
                int_w = p_int.custom_width_mm or (dim_int.width_mm if dim_int else max(5.0, profile.portada.width_mm - 1.5))
                int_h = p_int.custom_height_mm or (dim_int.height_mm if dim_int else max(5.0, profile.portada.height_mm - 1.5))
                if not p_int.custom_width_mm and int_w >= profile.portada.width_mm:
                    int_w = max(5.0, profile.portada.width_mm - 1.5)
                if not p_int.custom_height_mm and int_h >= profile.portada.height_mm:
                    int_h = max(5.0, profile.portada.height_mm - 1.5)
                for i in range(quantities.get("interior", 1)):
                    items_to_place.append((
                        "interior",
                        int_w,
                        int_h,
                        False, 0.0, False,
                        project
                    ))
        else:
            # Caso piezas separadas
            # Para aprovechar la hoja al máximo y hacer caber como mínimo 5 mini álbumes completos
            # por hoja A4, agrupamos las piezas álbum por álbum
            piece_keys = [
                "portada", "contraportada", "interior_contraportada",
                "interior", "cd", "lomo", "lomo_secundario"
            ]
            max_copies = max([quantities.get(k, 0) for k in piece_keys] or [0])
            for copy_i in range(max_copies):
                for key in piece_keys:
                    piece_design = project.get_piece(key)
                    if only_selected and not piece_design.enabled_for_print:
                        continue
                    if not piece_design.enabled_for_print:
                        continue
                    if copy_i >= quantities.get(key, 0):
                        continue

                    dim = profile.get_piece_dimension(key)
                    if key == "interior":
                        int_w = piece_design.custom_width_mm or (dim.width_mm if dim else max(5.0, profile.portada.width_mm - 1.5))
                        int_h = piece_design.custom_height_mm or (dim.height_mm if dim else max(5.0, profile.portada.height_mm - 1.5))
                        if not piece_design.custom_width_mm and int_w >= profile.portada.width_mm:
                            int_w = max(5.0, profile.portada.width_mm - 1.5)
                        if not piece_design.custom_height_mm and int_h >= profile.portada.height_mm:
                            int_h = max(5.0, profile.portada.height_mm - 1.5)
                        w, h = int_w, int_h
                        is_circ = False
                        inner_hole = 0.0
                        has_inner = False
                    else:
                        if not dim:
                            continue
                        w = piece_design.custom_width_mm or dim.width_mm
                        h = piece_design.custom_height_mm or dim.height_mm
                        is_circ = dim.is_circular
                        inner_hole = profile.cd.inner_hole_diameter_mm if is_circ else 0.0
                        has_inner = profile.cd.has_inner_hole if is_circ else False

                    items_to_place.append((key, w, h, is_circ, inner_hole, has_inner, project))

        return LayoutEngine._pack_items_on_pages(
            items_to_place=items_to_place,
            paper_w=paper_w,
            paper_h=paper_h,
            paper_size_name=paper_size_name,
            margin_mm=margin_mm,
            spacing_mm=spacing_mm,
            unprintable_margin_mm=unprintable_margin_mm
        )

    @staticmethod
    def _get_piece_item_tuple(
        proj: Project,
        key: str,
        profile: CaseProfile
    ) -> Optional[Tuple[str, float, float, bool, float, bool, Optional[Project]]]:
        """Obtiene la tupla de especificación de pieza para el motor de empaquetado."""
        piece_design = proj.get_piece(key)
        dim = profile.get_piece_dimension(key)
        if key == "interior":
            int_w = piece_design.custom_width_mm or (dim.width_mm if dim else max(5.0, profile.portada.width_mm - 1.5))
            int_h = piece_design.custom_height_mm or (dim.height_mm if dim else max(5.0, profile.portada.height_mm - 1.5))
            if not piece_design.custom_width_mm and int_w >= profile.portada.width_mm:
                int_w = max(5.0, profile.portada.width_mm - 1.5)
            if not piece_design.custom_height_mm and int_h >= profile.portada.height_mm:
                int_h = max(5.0, profile.portada.height_mm - 1.5)
            return (key, int_w, int_h, False, 0.0, False, proj)
        elif key == "cd":
            w = profile.cd.outer_diameter_mm
            h = profile.cd.outer_diameter_mm
            is_circ = True
            inner_hole = profile.cd.inner_hole_diameter_mm
            has_inner = profile.cd.has_inner_hole
            return (key, w, h, is_circ, inner_hole, has_inner, proj)
        else:
            if not dim:
                return None
            w = piece_design.custom_width_mm or dim.width_mm
            h = piece_design.custom_height_mm or dim.height_mm
            is_circ = dim.is_circular
            inner_hole = profile.cd.inner_hole_diameter_mm if is_circ else 0.0
            has_inner = profile.cd.has_inner_hole if is_circ else False
            return (key, w, h, is_circ, inner_hole, has_inner, proj)

    @staticmethod
    def compute_multi_project_layout(
        project_packages: List[Tuple[Project, int]],
        profile: CaseProfile,
        paper_size_name: str = "A4",
        orientation: str = "portrait",
        margin_mm: float = 6.0,
        spacing_mm: float = 2.5,
        unprintable_margin_mm: float = 5.0,
        extra_pieces: Optional[List[Tuple[Project, str, int]]] = None,
    ) -> LayoutResult:
        """
        Calcula la distribución óptima para MÚLTIPLES PROYECTOS y PIEZAS SUELTAS EXTRAS en el mismo documento PDF.
        Recibe una lista de tuplas (Project, cantidad_de_paquetes_completos) y opcionalmente
        piezas individuales adicionales (Project, piece_key, cantidad_suelta).
        Acomoda todo a escala física 100% real (mínimo 5 paquetes completos por hoja A4).
        """
        base_w, base_h = PAPER_SIZES_MM.get(paper_size_name, (210.0, 297.0))
        if orientation == "landscape":
            paper_w, paper_h = max(base_w, base_h), min(base_w, base_h)
        else:
            paper_w, paper_h = min(base_w, base_h), max(base_w, base_h)

        items_to_place: List[Tuple[str, float, float, bool, float, bool, Optional[Project]]] = []

        piece_keys = [
            "portada", "contraportada", "interior_contraportada",
            "interior", "cd", "lomo", "lomo_secundario"
        ]

        # 1. Empaquetar paquetes completos de cada proyecto
        for proj, num_packages in project_packages:
            if num_packages <= 0:
                continue

            if profile.continuous_tray:
                cont_w = profile.portada.width_mm + profile.lomo.width_mm + profile.contraportada.width_mm
                cont_h = max(profile.portada.height_mm, profile.contraportada.height_mm, profile.lomo.height_mm)
                for _ in range(num_packages):
                    items_to_place.append(("bandeja_continua", cont_w, cont_h, False, 0.0, False, proj))
                    if proj.get_piece("cd").enabled_for_print:
                        items_to_place.append((
                            "cd",
                            profile.cd.outer_diameter_mm,
                            profile.cd.outer_diameter_mm,
                            True,
                            profile.cd.inner_hole_diameter_mm,
                            profile.cd.has_inner_hole,
                            proj
                        ))
                    p_int = proj.get_piece("interior")
                    if p_int.enabled_for_print:
                        dim_int = profile.get_piece_dimension("interior")
                        int_w = p_int.custom_width_mm or (dim_int.width_mm if dim_int else max(5.0, profile.portada.width_mm - 1.5))
                        int_h = p_int.custom_height_mm or (dim_int.height_mm if dim_int else max(5.0, profile.portada.height_mm - 1.5))
                        if not p_int.custom_width_mm and int_w >= profile.portada.width_mm:
                            int_w = max(5.0, profile.portada.width_mm - 1.5)
                        if not p_int.custom_height_mm and int_h >= profile.portada.height_mm:
                            int_h = max(5.0, profile.portada.height_mm - 1.5)
                        items_to_place.append(("interior", int_w, int_h, False, 0.0, False, proj))
                    p_inlay = proj.get_piece("interior_contraportada")
                    if p_inlay.enabled_for_print:
                        dim_inlay = profile.get_piece_dimension("interior_contraportada")
                        in_w = p_inlay.custom_width_mm or (dim_inlay.width_mm if dim_inlay else profile.contraportada.width_mm)
                        in_h = p_inlay.custom_height_mm or (dim_inlay.height_mm if dim_inlay else profile.contraportada.height_mm)
                        items_to_place.append(("interior_contraportada", in_w, in_h, False, 0.0, False, proj))
            else:
                for _ in range(num_packages):
                    for key in piece_keys:
                        piece_design = proj.get_piece(key)
                        if not piece_design.enabled_for_print:
                            continue
                        tup = LayoutEngine._get_piece_item_tuple(proj, key, profile)
                        if tup:
                            items_to_place.append(tup)

        # 2. Empaquetar piezas individuales / sueltas extras añadidas por el usuario
        if extra_pieces:
            for extra_proj, extra_key, count in extra_pieces:
                if count <= 0:
                    continue
                tup = LayoutEngine._get_piece_item_tuple(extra_proj, extra_key, profile)
                if tup:
                    for _ in range(count):
                        items_to_place.append(tup)

        return LayoutEngine._pack_items_on_pages(
            items_to_place=items_to_place,
            paper_w=paper_w,
            paper_h=paper_h,
            paper_size_name=paper_size_name,
            margin_mm=margin_mm,
            spacing_mm=spacing_mm,
            unprintable_margin_mm=unprintable_margin_mm
        )

    @staticmethod
    def _pack_items_on_pages(
        items_to_place: List[Tuple[str, float, float, bool, float, bool, Optional[Project]]],
        paper_w: float,
        paper_h: float,
        paper_size_name: str,
        margin_mm: float,
        spacing_mm: float,
        unprintable_margin_mm: float
    ) -> LayoutResult:
        printable_w = paper_w - (2 * margin_mm)
        printable_h = paper_h - (2 * margin_mm)

        pages: List[PrintPage] = []
        warnings: List[str] = []
        unplaced_items: List[str] = []

        if not items_to_place:
            pages.append(PrintPage(page_number=1, paper_size_name=paper_size_name, paper_width_mm=paper_w, paper_height_mm=paper_h))
            return LayoutResult(pages=pages, total_items_placed=0, unplaced_items=[], warnings=["No hay piezas activadas para imprimir."])

        current_page_idx = 1
        current_page = PrintPage(
            page_number=current_page_idx,
            paper_size_name=paper_size_name,
            paper_width_mm=paper_w,
            paper_height_mm=paper_h
        )
        pages.append(current_page)

        cursor_x = margin_mm
        cursor_y = margin_mm
        row_max_h = 0.0
        copy_counters: Dict[str, int] = {}

        for key, item_w, item_h, is_circ, inner_hole, has_inner, source_proj in items_to_place:
            copy_counters[key] = copy_counters.get(key, 0) + 1
            copy_idx = copy_counters[key]

            if item_w > printable_w or item_h > printable_h:
                unplaced_items.append(f"{PIECE_NAMES_ES.get(key, key)} #{copy_idx} ({item_w}x{item_h} mm)")
                warnings.append(
                    f"La pieza {PIECE_NAMES_ES.get(key, key)} ({item_w:.1f} × {item_h:.1f} mm) "
                    f"excede el área imprimible del papel {paper_size_name}."
                )
                continue

            if (cursor_x + item_w) > (paper_w - margin_mm):
                cursor_x = margin_mm
                cursor_y += row_max_h + spacing_mm
                row_max_h = 0.0

            if (cursor_y + item_h) > (paper_h - margin_mm):
                current_page_idx += 1
                current_page = PrintPage(
                    page_number=current_page_idx,
                    paper_size_name=paper_size_name,
                    paper_width_mm=paper_w,
                    paper_height_mm=paper_h
                )
                pages.append(current_page)
                cursor_x = margin_mm
                cursor_y = margin_mm
                row_max_h = 0.0

            if cursor_x < unprintable_margin_mm or (cursor_x + item_w) > (paper_w - unprintable_margin_mm) or \
               cursor_y < unprintable_margin_mm or (cursor_y + item_h) > (paper_h - unprintable_margin_mm):
                msg = f"Pieza {PIECE_NAMES_ES.get(key, key)} #{copy_idx} se encuentra cerca del borde físico de impresión ({unprintable_margin_mm} mm)."
                if msg not in current_page.warnings:
                    current_page.warnings.append(msg)

            placed = PlacedItem(
                piece_key=key,
                display_name=PIECE_NAMES_ES.get(key, key),
                x_mm=cursor_x,
                y_mm=cursor_y,
                width_mm=item_w,
                height_mm=item_h,
                is_circular=is_circ,
                inner_hole_mm=inner_hole,
                has_inner_hole=has_inner,
                rotation=0,
                copy_index=copy_idx,
                source_project=source_proj,
                project_name=source_proj.name if source_proj else ""
            )
            current_page.items.append(placed)

            cursor_x += item_w + spacing_mm
            if item_h > row_max_h:
                row_max_h = item_h

        total_placed = sum(len(p.items) for p in pages)
        return LayoutResult(
            pages=pages,
            total_items_placed=total_placed,
            unplaced_items=unplaced_items,
            warnings=warnings
        )

    @staticmethod
    def check_overlaps(items: List[PlacedItem]) -> List[Tuple[PlacedItem, PlacedItem]]:
        """Verifica si existen superposiciones entre piezas en una misma hoja."""
        overlaps = []
        n = len(items)
        for i in range(n):
            for j in range(i + 1, n):
                a = items[i]
                b = items[j]
                # Bounding box test
                if (a.x_mm < b.x_mm + b.width_mm and
                    a.x_mm + a.width_mm > b.x_mm and
                    a.y_mm < b.y_mm + b.height_mm and
                    a.y_mm + a.height_mm > b.y_mm):
                    overlaps.append((a, b))
        return overlaps
