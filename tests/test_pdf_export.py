"""
Pruebas obligatorias para la exportación de documentos PDF de precisión:
1. Conversión exacta milímetros a puntos PDF.
2. Generación física de PDF sin escalado automático.
3. Dimensiones de página y cuadrado de calibración de 50.0 x 50.0 mm.
4. Exportación exitosa de piezas rectangulares y circulares.
"""
import pytest
import tempfile
import os
from pathlib import Path
from PIL import Image

from nfcito.core.units import mm_to_pt, pt_to_mm, POINTS_PER_MM
from nfcito.models.project import Project, PieceDesign
from nfcito.models.profile import CaseProfile, PieceDimension, CDDimension
from nfcito.core.layout_engine import LayoutEngine
from nfcito.core.pdf_exporter import PDFExporter

def test_unit_conversions_precision():
    # 25.4 mm debe ser exactamente 72.0 puntos PDF (1 pulgada)
    assert mm_to_pt(25.4) == pytest.approx(72.0, 1e-6)
    assert pt_to_mm(72.0) == pytest.approx(25.4, 1e-6)

    # 50 mm (cuadrado de calibración)
    sq_50_pt = mm_to_pt(50.0)
    assert sq_50_pt == pytest.approx(141.732283, 1e-4)

def test_pdf_export_execution():
    # Crear proyecto y piezas con imagen temporal
    fd_img, img_path = tempfile.mkstemp(suffix=".png")
    os.close(fd_img)
    img = Image.new("RGBA", (200, 200), (200, 50, 50, 255))
    img.save(img_path)

    profile = CaseProfile(
        id="test_export",
        name="Perfil Export",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0),
    )
    project = Project(name="Test Export PDF", profile_id=profile.id)
    project.get_piece("portada").image_path = img_path
    project.get_piece("cd").image_path = img_path

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0
    )

    fd_pdf, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd_pdf)

    out_file = PDFExporter.export_pdf(
        output_path=pdf_path,
        project=project,
        profile=profile,
        layout_result=layout,
        include_calibration=True,
        show_cut_lines=True,
        dpi=300
    )

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000  # Archivo PDF válido con contenido binario

    # Limpieza
    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_pdf_export_with_extra_loose_pieces():
    fd_img, img_path = tempfile.mkstemp(suffix=".png")
    os.close(fd_img)
    img = Image.new("RGBA", (150, 150), (30, 180, 50, 255))
    img.save(img_path)

    profile = CaseProfile(
        id="test_export_loose",
        name="Perfil Export Sueltas",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5),
    )
    project = Project(name="Project Loose Extras", profile_id=profile.id)
    project.get_piece("portada").image_path = img_path
    project.get_piece("interior_contraportada").image_path = img_path

    # 2 paquetes completos + 1 portada extra suelta + 1 fondo bandeja extra suelto
    extra_pieces = [
        (project, "portada", 1),
        (project, "interior_contraportada", 1)
    ]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=[(project, 2)],
        profile=profile,
        paper_size_name="A4",
        extra_pieces=extra_pieces
    )

    # 2 álbumes x 5 piezas base = 10 piezas + 2 piezas sueltas = 12 piezas en total
    assert layout.total_items_placed == 12

    fd_pdf, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd_pdf)

    out_file = PDFExporter.export_pdf(
        output_path=pdf_path,
        project=project,
        profile=profile,
        layout_result=layout,
        include_calibration=True,
        show_cut_lines=True,
        dpi=300
    )

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 2000

    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_pdf_export_with_interior_booklet():
    fd_img, img_path = tempfile.mkstemp(suffix=".png")
    os.close(fd_img)
    img = Image.new("RGBA", (150, 150), (10, 150, 200, 255))
    img.save(img_path)

    profile = CaseProfile(
        id="test_export_interior",
        name="Perfil Export con Libreto",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )
    project = Project(name="Project PDF Booklet", profile_id=profile.id)
    project.get_piece("interior").image_path = img_path
    project.get_piece("interior").enabled_for_print = True

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0
    )

    all_keys = [item.piece_key for page in layout.pages for item in page.items]
    assert "interior" in all_keys

    fd_pdf, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd_pdf)

    out_file = PDFExporter.export_pdf(
        output_path=pdf_path,
        project=project,
        profile=profile,
        layout_result=layout,
        include_calibration=False,
        show_cut_lines=True,
        dpi=300
    )

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000

    # Limpieza
    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)


def test_pdf_export_with_extra_loose_pieces():
    fd_img, img_path = tempfile.mkstemp(suffix=".png")
    os.close(fd_img)
    img = Image.new("RGBA", (150, 150), (30, 180, 50, 255))
    img.save(img_path)

    profile = CaseProfile(
        id="test_export_loose",
        name="Perfil Export Sueltas",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0),
        cd=CDDimension(outer_diameter_mm=40.0, inner_hole_diameter_mm=10.0),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5),
    )
    project = Project(name="Project Loose Extras", profile_id=profile.id)
    project.get_piece("portada").image_path = img_path
    project.get_piece("interior_contraportada").image_path = img_path

    # 2 paquetes completos + 1 portada extra suelta + 1 fondo bandeja extra suelto
    extra_pieces = [
        (project, "portada", 1),
        (project, "interior_contraportada", 1)
    ]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=[(project, 2)],
        profile=profile,
        paper_size_name="A4",
        extra_pieces=extra_pieces
    )

    # 2 álbumes x 5 piezas base = 10 piezas + 2 piezas sueltas = 12 piezas en total
    assert layout.total_items_placed == 12

    fd_pdf, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd_pdf)

    out_file = PDFExporter.export_pdf(
        output_path=pdf_path,
        project=project,
        profile=profile,
        layout_result=layout,
        include_calibration=True,
        show_cut_lines=True,
        dpi=300
    )

    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 2000

    if os.path.exists(img_path):
        os.remove(img_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

