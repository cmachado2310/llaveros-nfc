"""
Generador de documentos PDF de alta precisión milimétrica usando ReportLab.
Garantiza escala 100% real, marcas de corte discretas, resolución de 300 DPI y hoja de calibración.
"""
from pathlib import Path
from typing import List, Optional
import tempfile
import os

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from nfcito.models.project import Project
from nfcito.models.profile import CaseProfile
from nfcito.models.sheet import LayoutResult, PlacedItem
from nfcito.core.units import mm_to_pt, POINTS_PER_MM
from nfcito.core.image_ops import render_piece_image

class PDFExporter:
    @staticmethod
    def export_pdf(
        output_path: str,
        project: Project,
        profile: CaseProfile,
        layout_result: LayoutResult,
        include_calibration: bool = True,
        show_cut_lines: bool = True,
        dpi: int = 300,
    ) -> str:
        """
        Exporta el documento PDF con todas las páginas diagramadas y hoja de calibración opcional.
        """
        out_file = Path(output_path).resolve()
        if out_file.suffix.lower() != ".pdf":
            out_file = out_file.with_suffix(".pdf")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Usar primera página para dimensiones de página base
        first_page = layout_result.pages[0] if layout_result.pages else None
        p_w_pt = mm_to_pt(first_page.paper_width_mm) if first_page else mm_to_pt(210.0)
        p_h_pt = mm_to_pt(first_page.paper_height_mm) if first_page else mm_to_pt(297.0)

        pdf_doc = canvas.Canvas(str(out_file), pagesize=(p_w_pt, p_h_pt))
        pdf_doc.setTitle(f"NFCito Studio - {project.name}")
        pdf_doc.setAuthor("NFCito Studio")
        pdf_doc.setCreator("NFCito Studio v1.0")

        temp_images_to_cleanup: List[str] = []

        try:
            # 1. Hoja de Calibración física de 50 x 50 mm (si está activa)
            if include_calibration:
                PDFExporter._render_calibration_page(pdf_doc, p_w_pt, p_h_pt)
                pdf_doc.showPage()

            # 2. Renderizar cada página del diseño
            for page in layout_result.pages:
                page_w_pt = mm_to_pt(page.paper_width_mm)
                page_h_pt = mm_to_pt(page.paper_height_mm)
                pdf_doc.setPageSize((page_w_pt, page_h_pt))

                # Encabezado informativo de página
                pdf_doc.setFont("Helvetica-Bold", 8)
                pdf_doc.setFillColor(colors.HexColor("#555555"))
                header_text = (
                    f"NFCito Studio | Proyecto: {project.name} | Perfil: {profile.name} | "
                    f"Página {page.page_number}/{len(layout_result.pages)} | ESCALA 100% (NO AJUSTAR A PÁGINA)"
                )
                pdf_doc.drawString(mm_to_pt(8.0), page_h_pt - mm_to_pt(6.0), header_text)

                for item in page.items:
                    PDFExporter._render_placed_item(
                        pdf_doc=pdf_doc,
                        item=item,
                        project=project,
                        profile=profile,
                        page_h_pt=page_h_pt,
                        show_cut_lines=show_cut_lines,
                        dpi=dpi,
                        temp_cleanup_list=temp_images_to_cleanup
                    )

                pdf_doc.showPage()

            pdf_doc.save()
        finally:
            # Eliminar archivos temporales de render
            for tmp in temp_images_to_cleanup:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass

        return str(out_file)

    @staticmethod
    def _render_placed_item(
        pdf_doc: canvas.Canvas,
        item: PlacedItem,
        project: Project,
        profile: CaseProfile,
        page_h_pt: float,
        show_cut_lines: bool,
        dpi: int,
        temp_cleanup_list: List[str]
    ) -> None:
        """Renderiza una pieza individual en el canvas de ReportLab con medidas exactas."""
        # En ReportLab el origen (0,0) está en la esquina inferior izquierda
        x_pt = mm_to_pt(item.x_mm)
        w_pt = mm_to_pt(item.width_mm)
        h_pt = mm_to_pt(item.height_mm)
        # Convertir coordenada Y desde el borde superior
        y_pt = page_h_pt - mm_to_pt(item.y_mm + item.height_mm)

        source_proj = item.source_project if getattr(item, "source_project", None) is not None else project
        piece_design = source_proj.get_piece(item.piece_key) if source_proj else None

        # Generar imagen rasterizada a alta resolución
        img_pil = render_piece_image(
            image_path=piece_design.image_path if piece_design else None,
            width_mm=item.width_mm,
            height_mm=item.height_mm,
            crop=piece_design.crop if piece_design else None,
            text_config=piece_design.text_overlay if piece_design else None,
            is_circular=item.is_circular,
            inner_hole_mm=item.inner_hole_mm,
            has_inner_hole=item.has_inner_hole,
            dpi=dpi
        )

        # Guardar en archivo temporal para ReportLab drawImage
        fd, temp_img_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img_pil.save(temp_img_path, format="PNG", dpi=(dpi, dpi))
        temp_cleanup_list.append(temp_img_path)

        # Dibujar imagen con dimensiones exactas en puntos
        pdf_doc.drawImage(
            temp_img_path,
            x_pt,
            y_pt,
            width=w_pt,
            height=h_pt,
            mask="auto",
            preserveAspectRatio=True
        )

        # Dibujar líneas de corte / marcas de registro
        if show_cut_lines:
            pdf_doc.setStrokeColor(colors.HexColor("#777777"))
            pdf_doc.setLineWidth(0.3)

            if item.is_circular:
                # Contorno circular para corte con tijera/cúter compás
                radius_pt = w_pt / 2.0
                cx_pt = x_pt + radius_pt
                cy_pt = y_pt + radius_pt
                pdf_doc.circle(cx_pt, cy_pt, radius_pt, stroke=1, fill=0)

                # Agujero central
                if item.has_inner_hole and item.inner_hole_mm > 0:
                    inner_r_pt = mm_to_pt(item.inner_hole_mm / 2.0)
                    pdf_doc.circle(cx_pt, cy_pt, inner_r_pt, stroke=1, fill=0)
                    # Pequeña cruz central
                    pdf_doc.line(cx_pt - 4, cy_pt, cx_pt + 4, cy_pt)
                    pdf_doc.line(cx_pt, cy_pt - 4, cx_pt, cy_pt + 4)
            else:
                # Marcas de corte esquineras exteriores (Corner crop marks)
                mark_len = mm_to_pt(2.5)
                # Esquina inferior izquierda
                pdf_doc.line(x_pt, y_pt, x_pt - mark_len, y_pt)
                pdf_doc.line(x_pt, y_pt, x_pt, y_pt - mark_len)
                # Esquina inferior derecha
                pdf_doc.line(x_pt + w_pt, y_pt, x_pt + w_pt + mark_len, y_pt)
                pdf_doc.line(x_pt + w_pt, y_pt, x_pt + w_pt, y_pt - mark_len)
                # Esquina superior izquierda
                pdf_doc.line(x_pt, y_pt + h_pt, x_pt - mark_len, y_pt + h_pt)
                pdf_doc.line(x_pt, y_pt + h_pt, x_pt, y_pt + h_pt + mark_len)
                # Esquina superior derecha
                pdf_doc.line(x_pt + w_pt, y_pt + h_pt, x_pt + w_pt + mark_len, y_pt + h_pt)
                pdf_doc.line(x_pt + w_pt, y_pt + h_pt, x_pt + w_pt, y_pt + h_pt + mark_len)

                # Si es bandeja continua, dibujar líneas guía de plegado para el lomo
                if item.piece_key == "bandeja_continua":
                    pdf_doc.setStrokeColor(colors.HexColor("#999999"))
                    pdf_doc.setDash(2, 2)
                    fold1_x = x_pt + mm_to_pt(profile.contraportada.width_mm)
                    fold2_x = fold1_x + mm_to_pt(profile.lomo.width_mm)
                    pdf_doc.line(fold1_x, y_pt, fold1_x, y_pt + h_pt)
                    pdf_doc.line(fold2_x, y_pt, fold2_x, y_pt + h_pt)
                    pdf_doc.setDash()  # Restaurar línea sólida

        # Etiqueta de la pieza
        pdf_doc.setFont("Helvetica", 6)
        pdf_doc.setFillColor(colors.HexColor("#666666"))
        proj_prefix = f"[{item.project_name}] " if getattr(item, "project_name", None) else ""
        label = f"{proj_prefix}{item.display_name} ({item.width_mm:.1f} × {item.height_mm:.1f} mm)"
        pdf_doc.drawString(x_pt, y_pt - mm_to_pt(2.2), label)

    @staticmethod
    def _render_calibration_page(pdf_doc: canvas.Canvas, page_w_pt: float, page_h_pt: float) -> None:
        """
        Dibuja una página de calibración con un cuadrado exacto de 50.0 × 50.0 mm
        e instrucciones en español para validar la escala de la impresora.
        """
        cx = page_w_pt / 2.0
        cy = page_h_pt / 2.0

        # Título principal
        pdf_doc.setFont("Helvetica-Bold", 16)
        pdf_doc.setFillColor(colors.HexColor("#1A1A24"))
        pdf_doc.drawCentredString(cx, cy + mm_to_pt(75.0), "NFCito Studio — Página de Calibración de Escala")

        # Subtítulo e instrucciones críticas
        pdf_doc.setFont("Helvetica", 10)
        pdf_doc.setFillColor(colors.HexColor("#333333"))
        pdf_doc.drawCentredString(cx, cy + mm_to_pt(65.0), "Comprobación de precisión física antes de imprimir piezas del mini álbum.")

        box_y = cy + mm_to_pt(40.0)
        pdf_doc.setFont("Helvetica-Bold", 10)
        pdf_doc.setFillColor(colors.HexColor("#B22222"))
        pdf_doc.drawCentredString(cx, box_y, "INSTRUCCIONES OBLIGATORIAS DE IMPRESIÓN:")

        pdf_doc.setFont("Helvetica", 9)
        pdf_doc.setFillColor(colors.black)
        instructions = [
            "1. En el diálogo de impresión de su lector de PDF, seleccione 'Tamaño Real' o 'Escala 100%'.",
            "2. DESACTIVE por completo la opción 'Ajustar a página' o 'Reducir páginas excesivas'.",
            "3. Tras imprimir esta página, mida el recuadro inferior con una regla física o calibre.",
            "4. Si mide exactamente 50.0 mm de ancho y 50.0 mm de alto, su configuración es perfecta.",
            "5. Si mide distinto, ajuste la escala porcentual en la configuración del controlador de su impresora."
        ]
        line_offset = mm_to_pt(33.0)
        for inst in instructions:
            pdf_doc.drawCentredString(cx, cy + line_offset, inst)
            line_offset -= mm_to_pt(5.0)

        # Dibujar cuadrado de calibración exacto de 50 × 50 mm
        sq_size_pt = mm_to_pt(50.0)
        sq_x = cx - (sq_size_pt / 2.0)
        sq_y = cy - (sq_size_pt / 2.0) - mm_to_pt(15.0)

        # Fondo suave y borde negro
        pdf_doc.setFillColor(colors.HexColor("#F8F9FA"))
        pdf_doc.rect(sq_x, sq_y, sq_size_pt, sq_size_pt, fill=1, stroke=0)

        pdf_doc.setStrokeColor(colors.black)
        pdf_doc.setLineWidth(0.8)
        pdf_doc.rect(sq_x, sq_y, sq_size_pt, sq_size_pt, fill=0, stroke=1)

        # Texto dentro del recuadro
        pdf_doc.setFont("Helvetica-Bold", 13)
        pdf_doc.setFillColor(colors.black)
        pdf_doc.drawCentredString(cx, sq_y + (sq_size_pt / 2.0) + 6, "50.0 mm × 50.0 mm")
        pdf_doc.setFont("Helvetica", 9)
        pdf_doc.drawCentredString(cx, sq_y + (sq_size_pt / 2.0) - 8, "(5.0 cm exactos)")

        # Dibujar marcas de regla milimétrica en los bordes del recuadro (cada 5 mm y cada 10 mm)
        pdf_doc.setLineWidth(0.5)
        for mm in range(1, 50):
            d_pt = mm_to_pt(mm)
            tick_len = mm_to_pt(2.5) if (mm % 10 == 0) else mm_to_pt(1.5) if (mm % 5 == 0) else mm_to_pt(0.8)
            # Borde superior
            pdf_doc.line(sq_x + d_pt, sq_y + sq_size_pt, sq_x + d_pt, sq_y + sq_size_pt - tick_len)
            # Borde izquierdo
            pdf_doc.line(sq_x, sq_y + d_pt, sq_x + tick_len, sq_y + d_pt)
            # Borde inferior
            pdf_doc.line(sq_x + d_pt, sq_y, sq_x + d_pt, sq_y + tick_len)
            # Borde derecho
            pdf_doc.line(sq_x + sq_size_pt, sq_y + d_pt, sq_x + sq_size_pt - tick_len, sq_y + d_pt)

        # Pie de página de calibración
        pdf_doc.setFont("Helvetica", 8)
        pdf_doc.setFillColor(colors.HexColor("#777777"))
        pdf_doc.drawCentredString(cx, mm_to_pt(12.0), "NFCito Studio — Impresión de Precisión para Mini Álbumes y Llaveros NFC")
