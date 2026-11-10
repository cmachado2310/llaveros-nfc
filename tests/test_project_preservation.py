"""
Pruebas obligatorias para proyectos e integridad de datos:
1. Cambiar de perfil no destruye las imágenes ni los recortes asignados.
2. Modificar una medida actualiza ambos modos sin borrar el trabajo.
3. Guardar y cargar conserva textos de contraportada y metadatos NFC.
4. Comunicación clara de imágenes no disponibles.
"""
import pytest
from pathlib import Path
import tempfile
import os
from PIL import Image

from nfcito.models.project import Project, PieceDesign, CropConfig, TextConfig, NFCConfig
from nfcito.models.profile import CaseProfile, PieceDimension, CDDimension
from nfcito.storage.project_repo import ProjectRepository

@pytest.fixture
def sample_image():
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img = Image.new("RGB", (200, 200), color=(255, 100, 50))
    img.save(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_change_profile_preserves_images(sample_image):
    project = Project(name="Mi Álbum de Prueba")
    project.get_piece("portada").image_path = sample_image
    project.get_piece("portada").crop.zoom = 1.35
    project.get_piece("portada").crop.pan_x = 0.25

    # Simular cambio de perfil
    profile_a = CaseProfile(id="prof_a", name="Perfil A", portada=PieceDimension(width_mm=45.0, height_mm=45.0))
    profile_b = CaseProfile(id="prof_b", name="Perfil B", portada=PieceDimension(width_mm=50.0, height_mm=50.0))

    project.profile_id = profile_b.id

    # La imagen y los ajustes deben preservarse intactos
    piece = project.get_piece("portada")
    assert piece.image_path == sample_image
    assert piece.crop.zoom == 1.35
    assert piece.crop.pan_x == 0.25
    assert project.profile_id == "prof_b"

def test_project_save_and_load(sample_image):
    fd, proj_path = tempfile.mkstemp(suffix=".nfcito")
    os.close(fd)

    project = Project(name="Álbum Completo")
    project.nfc = NFCConfig(
        album_title="Álbum Completo",
        artist="Artista Indie",
        nfc_target_url="https://open.spotify.com/album/123456",
        nfc_tag_type="NTAG213"
    )

    p_front = project.get_piece("portada")
    p_front.image_path = sample_image
    p_front.crop.zoom = 1.5

    p_back = project.get_piece("contraportada")
    p_back.text_overlay = TextConfig(
        enabled=True,
        title="Canciones",
        tracks="1. Intro\n2. Éxito\n3. Outro",
        font_size=9,
        text_color="#112233"
    )

    # Guardar
    saved_file = ProjectRepository.save_project(project, proj_path, bundle_assets=False)
    assert os.path.exists(saved_file)

    # Cargar
    loaded, warnings = ProjectRepository.load_project(saved_file)
    assert len(warnings) == 0
    assert loaded.name == "Álbum Completo"
    assert loaded.nfc.nfc_target_url == "https://open.spotify.com/album/123456"
    assert loaded.get_piece("portada").crop.zoom == 1.5
    assert loaded.get_piece("contraportada").text_overlay.enabled is True
    assert "2. Éxito" in loaded.get_piece("contraportada").text_overlay.tracks

    if os.path.exists(proj_path):
        os.remove(proj_path)

def test_missing_image_warning_communication():
    fd, proj_path = tempfile.mkstemp(suffix=".nfcito")
    os.close(fd)

    project = Project(name="Proyecto con Imagen Borrada")
    fake_path = "C:/ruta/inexistente/foto_borrada.jpg"
    project.get_piece("portada").image_path = fake_path

    ProjectRepository.save_project(project, proj_path, bundle_assets=False)

    loaded, warnings = ProjectRepository.load_project(proj_path)
    assert len(warnings) >= 1
    assert "foto_borrada.jpg" in warnings[0]

    if os.path.exists(proj_path):
        os.remove(proj_path)


def test_load_project_with_bundled_assets(sample_image):
    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_file = os.path.join(tmp_dir, "proyecto_test.nfcito")
        project = Project(name="Proyecto con Assets")
        project.get_piece("portada").image_path = sample_image

        # Guardar con bundle_assets=True
        saved_path = ProjectRepository.save_project(project, proj_file, bundle_assets=True)
        assert os.path.exists(saved_path)

        # Cargar el proyecto desde el archivo .nfcito
        loaded, warnings = ProjectRepository.load_project(saved_path)
        assert len(warnings) == 0
        loaded_portada = loaded.get_piece("portada")
        assert loaded_portada.image_path is not None
        assert os.path.exists(loaded_portada.image_path)

