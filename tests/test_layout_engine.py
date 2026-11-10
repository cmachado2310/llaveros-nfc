"""
Pruebas obligatorias para la diagramación de hojas de impresión:
1. Ausencia total de superposiciones entre piezas.
2. Detección y advertencia de piezas que excedan el área imprimible.
3. Generación automática de páginas adicionales.
4. Soporte para plantilla continua desplegada (bandeja completa).
"""
import pytest
from nfcito.models.project import Project, PieceDesign
from nfcito.models.profile import CaseProfile, PieceDimension, CDDimension
from nfcito.core.layout_engine import LayoutEngine

def test_zero_overlaps_in_layout():
    profile = CaseProfile(
        id="test_prof",
        name="Test",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
    )
    project = Project(name="Test Layout", profile_id=profile.id)
    # Pedir 4 copias de portada y 4 de CD
    quantities = {"portada": 4, "contraportada": 2, "lomo": 2, "cd": 4, "interior": 0}

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0,
        quantities=quantities
    )

    assert layout.total_items_placed == 12
    # Verificar cada página
    for page in layout.pages:
        overlaps = LayoutEngine.check_overlaps(page.items)
        assert len(overlaps) == 0, f"Se detectaron superposiciones en página {page.page_number}: {overlaps}"

def test_exceeding_piece_warning():
    profile = CaseProfile(
        id="test_giant",
        name="Pieza Gigante",
        # Pieza más ancha que una hoja A4 (A4 = 210 x 297 mm)
        portada=PieceDimension(width_mm=250.0, height_mm=48.0, enabled=True),
    )
    project = Project(name="Test Exceed", profile_id=profile.id)

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0,
    )

    assert len(layout.warnings) >= 1
    assert len(layout.unplaced_items) >= 1
    assert any("excede el área imprimible" in w for w in layout.warnings)

def test_multi_page_distribution():
    profile = CaseProfile(
        id="test_prof",
        name="Test",
        portada=PieceDimension(width_mm=50.0, height_mm=50.0, enabled=True),
    )
    project = Project(name="Multi Page Test", profile_id=profile.id)
    # Colocar 30 piezas que no caben en una sola página A4
    quantities = {"portada": 30, "contraportada": 0, "lomo": 0, "cd": 0, "interior": 0}

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0,
        quantities=quantities
    )

    assert layout.total_items_placed == 30
    assert len(layout.pages) >= 2
    # En ninguna página debe haber superposiciones
    for page in layout.pages:
        assert len(LayoutEngine.check_overlaps(page.items)) == 0

def test_continuous_tray_layout():
    profile = CaseProfile(
        id="test_continuous",
        name="Bandeja Continua",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0),
        cd=CDDimension(outer_diameter_mm=40.0),
        continuous_tray=True,
    )
    project = Project(name="Continuous Project", profile_id=profile.id)

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
    )

    # Debe colocar la bandeja continua (48 + 5 + 48 = 101 mm) y el CD
    first_page = layout.pages[0]
    keys = [item.piece_key for item in first_page.items]
    assert "bandeja_continua" in keys
    assert "cd" in keys

    item_tray = next(item for item in first_page.items if item.piece_key == "bandeja_continua")
    assert item_tray.width_mm == pytest.approx(101.0, 0.1)
    assert item_tray.height_mm == pytest.approx(48.0, 0.1)

def test_interior_booklet_placed_and_smaller_than_portada():
    profile = CaseProfile(
        id="test_interior_dim",
        name="Test Libreto",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )
    project = Project(name="Project With Booklet", profile_id=profile.id)
    project.get_piece("interior").enabled_for_print = True

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0
    )

    all_items = [item for page in layout.pages for item in page.items]
    booklet = next((item for item in all_items if item.piece_key == "interior"), None)
    assert booklet is not None, "El interior/libreto debe aparecer en la hoja de impresión"
    portada = next(item for item in all_items if item.piece_key == "portada")

    # El libreto interior debe ser estrictamente más pequeño que la portada
    assert booklet.width_mm < portada.width_mm
    assert booklet.height_mm < portada.height_mm
    assert booklet.width_mm == pytest.approx(46.5, 0.1)
    assert booklet.height_mm == pytest.approx(46.5, 0.1)

def test_multiple_albums_add_pages_without_changing_dimensions():
    """Verifica que al pedir múltiples álbumes completos, si sobrepasa la hoja, se añade otra hoja
    automáticamente y las dimensiones físicas no se alteran ni se escalan."""
    profile = CaseProfile(
        id="test_multi_albums",
        name="Test Multi Álbumes",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )
    project = Project(name="Project 10 Albums", profile_id=profile.id)

    num_albums = 10
    quantities = {
        "portada": num_albums,
        "contraportada": num_albums,
        "lomo": num_albums,
        "cd": num_albums,
        "interior": num_albums,
    }

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        margin_mm=8.0,
        spacing_mm=4.0,
        quantities=quantities
    )

    # 10 álbumes x 5 piezas = 50 piezas en total
    assert layout.total_items_placed == 50
    # En A4 no caben 50 piezas en 1 sola hoja, debe crear páginas adicionales
    assert len(layout.pages) >= 2

    # Verificar que en cada página generada no existan superposiciones
    for page in layout.pages:
        overlaps = LayoutEngine.check_overlaps(page.items)
        assert len(overlaps) == 0, f"Superposiciones en página {page.page_number}: {overlaps}"

        # Verificar que NINGUNA pieza haya cambiado sus medidas físicas
        for item in page.items:
            if item.piece_key in ("portada", "contraportada"):
                assert item.width_mm == pytest.approx(48.0, 1e-4)
                assert item.height_mm == pytest.approx(48.0, 1e-4)
            elif item.piece_key == "interior":
                assert item.width_mm == pytest.approx(46.5, 1e-4)
                assert item.height_mm == pytest.approx(46.5, 1e-4)
            elif item.piece_key == "cd":
                assert item.width_mm == pytest.approx(40.0, 1e-4)
            elif item.piece_key == "lomo":
                assert item.width_mm == pytest.approx(5.0, 1e-4)
                assert item.height_mm == pytest.approx(48.0, 1e-4)

def test_five_albums_fit_on_single_a4_page():
    """Verifica que el optimizador acomoda como mínimo 5 mini álbumes completos (25 piezas)
    en una sola hoja A4 a escala 100% física real sin superposiciones."""
    profile = CaseProfile(
        id="test_5_albums",
        name="Test 5 Álbumes",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )
    project = Project(name="Project 5 Albums", profile_id=profile.id)

    quantities_5 = {
        "portada": 5,
        "contraportada": 5,
        "lomo": 5,
        "cd": 5,
        "interior": 5,
    }

    # Con los márgenes por defecto optimizados (6mm margen, 2.5mm espaciado)
    layout_5 = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        quantities=quantities_5
    )

    # 5 álbumes completos = 25 piezas
    assert layout_5.total_items_placed == 25
    # Caben exactamente en 1 sola hoja A4
    assert len(layout_5.pages) == 1
    assert len(LayoutEngine.check_overlaps(layout_5.pages[0].items)) == 0

    # Y 10 álbumes completos (50 piezas) caben exactamente en 2 hojas
    quantities_10 = {k: v * 2 for k, v in quantities_5.items()}
    layout_10 = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        quantities=quantities_10
    )
    assert layout_10.total_items_placed == 50
    assert len(layout_10.pages) == 2
    for page in layout_10.pages:
        assert len(LayoutEngine.check_overlaps(page.items)) == 0

def test_multi_project_layout():
    """Verifica que se pueden combinar múltiples proyectos en un mismo PDF,
    adecuando los paquetes correctamente y conservando las referencias a cada proyecto."""
    profile = CaseProfile(
        id="test_prof_multi",
        name="Perfil Multi",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )

    proj_a = Project(name="Album A", profile_id=profile.id)
    proj_b = Project(name="Album B", profile_id=profile.id)

    # 3 paquetes de A + 2 paquetes de B = 5 paquetes (25 piezas)
    project_packages = [(proj_a, 3), (proj_b, 2)]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=project_packages,
        profile=profile,
        paper_size_name="A4"
    )

    assert layout.total_items_placed == 25
    assert len(layout.pages) == 1
    assert len(LayoutEngine.check_overlaps(layout.pages[0].items)) == 0

    # Verificar que las piezas tengan las referencias correctas de sus proyectos de origen
    items_a = [item for item in layout.pages[0].items if item.source_project is proj_a]
    items_b = [item for item in layout.pages[0].items if item.source_project is proj_b]
    assert len(items_a) == 15  # 3 paquetes x 5 piezas
    assert len(items_b) == 10  # 2 paquetes x 5 piezas

    # 4 paquetes de A + 3 paquetes de B = 7 paquetes (35 piezas) -> debe generar 2 páginas
    layout_7 = LayoutEngine.compute_multi_project_layout(
        project_packages=[(proj_a, 4), (proj_b, 3)],
        profile=profile,
        paper_size_name="A4"
    )
    assert layout_7.total_items_placed == 35
    assert len(layout_7.pages) == 2
    for page in layout_7.pages:
        assert len(LayoutEngine.check_overlaps(page.items)) == 0


def test_multi_project_layout_with_extra_loose_pieces():
    """Verifica que se pueden agregar piezas sueltas individuales (ej. 1 portada extra que faltó)
    junto con paquetes completos en el mismo PDF sin deformaciones ni superposiciones."""
    profile = CaseProfile(
        id="test_prof_extras",
        name="Perfil Extras",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )

    proj = Project(name="Mi Álbum", profile_id=profile.id)

    # 4 paquetes completos (20 piezas) + 1 portada suelta adicional = 21 piezas
    project_packages = [(proj, 4)]
    extra_pieces = [(proj, "portada", 1)]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=project_packages,
        profile=profile,
        paper_size_name="A4",
        extra_pieces=extra_pieces
    )

    assert layout.total_items_placed == 21
    # Debe haber 5 portadas en total (4 de los paquetes + 1 suelta)
    portadas = [it for page in layout.pages for it in page.items if it.piece_key == "portada"]
    assert len(portadas) == 5

    for page in layout.pages:
        assert len(LayoutEngine.check_overlaps(page.items)) == 0


def test_interior_contraportada_and_lomo_secundario_layout():
    """Verifica que el fondo de bandeja (interior contraportada) y el lomo secundario
    se diagraman con precisión si el usuario los activa."""
    profile = CaseProfile(
        id="test_prof_inlay",
        name="Perfil Inlay",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )

    project = Project(name="Proyecto con Inlay", profile_id=profile.id)
    # Habilitar las dos nuevas piezas
    project.get_piece("interior_contraportada").enabled_for_print = True
    project.get_piece("lomo_secundario").enabled_for_print = True

    quantities = {
        "portada": 1,
        "contraportada": 1,
        "interior_contraportada": 1,
        "lomo": 1,
        "lomo_secundario": 1,
        "cd": 1,
        "interior": 1,
    }

    layout = LayoutEngine.compute_layout(
        project=project,
        profile=profile,
        paper_size_name="A4",
        quantities=quantities
    )

    assert layout.total_items_placed == 7
    placed_keys = [it.piece_key for it in layout.pages[0].items]
    assert "interior_contraportada" in placed_keys
    assert "lomo_secundario" in placed_keys
    assert len(LayoutEngine.check_overlaps(layout.pages[0].items)) == 0


def test_loose_piece_only_without_full_album():
    """Verifica que si el usuario solo necesita reimprimir una pieza faltante (ej. solo el CD),
    se puede poner la cantidad de álbumes en 0 y colocar ÚNICAMENTE esa pieza suelta."""
    profile = CaseProfile(
        id="test_cd_only",
        name="Perfil CD Only",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
    )

    proj = Project(name="Proyecto Solo CD", profile_id=profile.id)

    # 0 paquetes completos + 1 etiqueta CD suelta
    project_packages = [(proj, 0)]
    extra_pieces = [(proj, "cd", 1)]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=project_packages,
        profile=profile,
        paper_size_name="A4",
        extra_pieces=extra_pieces
    )

    # Debe contener EXACTAMENTE 1 pieza (el CD) y ninguna otra
    assert layout.total_items_placed == 1
    assert len(layout.pages[0].items) == 1
    item = layout.pages[0].items[0]
    assert item.piece_key == "cd"
    assert item.is_circular is True
    assert item.width_mm == 40.0
    assert item.height_mm == 40.0


def test_mixed_mode_layout():
    """Valida el Modo Mixto:
    Imprimir varios paquetes completos de un Proyecto A (p. ej. 2 paquetes)
    Y simultáneamente piezas sueltas de un Proyecto B incompleto (0 paquetes completos, solo 1 CD y 1 portada).
    """
    profile = CaseProfile(
        id="test_mixed",
        name="Perfil Mixto",
        portada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=True),
        cd=CDDimension(outer_diameter_mm=40.0, enabled=True),
        interior=PieceDimension(width_mm=46.5, height_mm=46.5, enabled=True),
        interior_contraportada=PieceDimension(width_mm=48.0, height_mm=48.0, enabled=True),
        lomo_secundario=PieceDimension(width_mm=5.0, height_mm=48.0, enabled=False),
    )
    # Piezas habilitadas por paquete: portada, contraportada, lomo, cd, interior, interior_contraportada = 6 piezas

    proj_a = Project(name="Album Completo A", profile_id=profile.id)
    # Habilitar también interior_contraportada en el Proyecto A para que tenga 6 piezas por paquete
    proj_a.get_piece("interior_contraportada").enabled_for_print = True
    proj_b = Project(name="Album Incompleto B", profile_id=profile.id)

    # Proyecto A: 2 paquetes completos = 2 * 6 = 12 piezas
    # Proyecto B: 0 paquetes completos = 0 piezas de paquete
    project_packages = [
        (proj_a, 2),
        (proj_b, 0),
    ]

    # Piezas sueltas: 1 CD y 1 Portada del Proyecto B
    extra_pieces = [
        (proj_b, "cd", 1),
        (proj_b, "portada", 1),
    ]

    layout = LayoutEngine.compute_multi_project_layout(
        project_packages=project_packages,
        profile=profile,
        paper_size_name="A4",
        extra_pieces=extra_pieces
    )

    # Total esperado: 12 (de A) + 2 (de B) = 14 piezas
    assert layout.total_items_placed == 14

    # Verificar que los items de B son exactamente los sueltos
    items_b = [
        item for page in layout.pages for item in page.items
        if item.project_name == "Album Incompleto B"
    ]
    assert len(items_b) == 2
    keys_b = sorted([item.piece_key for item in items_b])
    assert keys_b == ["cd", "portada"]

    # Verificar que los items de A corresponden a los 2 paquetes completos (2 de cada una de las 6 piezas)
    items_a = [
        item for page in layout.pages for item in page.items
        if item.project_name == "Album Completo A"
    ]
    assert len(items_a) == 12






