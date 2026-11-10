"""
Pruebas obligatorias para el sistema de perfiles y persistencia.
Verifica:
1. Guardado y recuperación tras reiniciar.
2. Restauración del último perfil activo.
3. Conservación de perfiles anteriores al crear uno nuevo.
4. Duplicación y renombrado.
5. Medidas compartidas y actualizadas.
"""
import pytest
import json
from pathlib import Path
import tempfile
import os

from nfcito.models.profile import CaseProfile, PieceDimension, CDDimension
from nfcito.storage.profile_repo import ProfileRepository

@pytest.fixture
def temp_profile_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield Path(path)
    if os.path.exists(path):
        os.remove(path)

def test_default_profiles_initialization(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    profiles = repo.get_all()
    assert len(profiles) >= 3
    # Comprobar que los perfiles predeterminados están identificados como provisionales
    assert any(p.is_provisional for p in profiles)

def test_save_and_retrieve_profile(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    profile = repo.create_profile("Estuche Acrílico Personalizado 52mm", "Medidas con calibre")
    profile.portada.width_mm = 51.5
    profile.portada.height_mm = 51.5
    profile.cd.outer_diameter_mm = 42.0
    repo.save_profile(profile)

    # Simular cierre y reapertura de la app con un nuevo repo que lee del mismo archivo
    repo2 = ProfileRepository(file_path=temp_profile_file)
    retrieved = repo2.get_by_id(profile.id)
    assert retrieved is not None
    assert retrieved.name == "Estuche Acrílico Personalizado 52mm"
    assert retrieved.portada.width_mm == 51.5
    assert retrieved.portada.height_mm == 51.5
    assert retrieved.cd.outer_diameter_mm == 42.0

def test_preserve_older_profiles_on_new_creation(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    initial_count = len(repo.get_all())
    p1 = repo.create_profile("Perfil 1")
    p2 = repo.create_profile("Perfil 2")

    repo2 = ProfileRepository(file_path=temp_profile_file)
    assert repo2.get_by_id(p1.id) is not None
    assert repo2.get_by_id(p2.id) is not None
    assert len(repo2.get_all()) == initial_count + 2

def test_duplicate_profile(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    orig = repo.get_all()[0]
    orig.portada.width_mm = 49.2
    repo.save_profile(orig)

    dup = repo.duplicate_profile(orig.id, "Copia de Prueba")
    assert dup.id != orig.id
    assert dup.name == "Copia de Prueba"
    assert dup.portada.width_mm == 49.2
    assert not dup.is_provisional

def test_last_active_profile_persistence(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    p = repo.create_profile("Perfil Activo Recordado")
    repo.set_active_profile_id(p.id)

    # Verificar que el repo recupera este perfil como activo
    assert repo.get_active_profile_id() == p.id

def test_interior_booklet_dimensions_smaller_than_portada(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    default_p = repo.get_by_id("default_mini_cd_50")
    assert default_p is not None
    # El libreto interior debe ser más pequeño que la portada (46.5 vs 48.0)
    assert default_p.interior.width_mm < default_p.portada.width_mm
    assert default_p.interior.height_mm < default_p.portada.height_mm
    assert default_p.interior.width_mm == pytest.approx(46.5, 0.1)
    assert default_p.interior.height_mm == pytest.approx(46.5, 0.1)
    assert default_p.interior.enabled is True


def test_interior_contraportada_and_lomo_secundario_in_profile(temp_profile_file):
    repo = ProfileRepository(file_path=temp_profile_file)
    default_p = repo.get_by_id("default_mini_cd_50")
    assert default_p is not None

    # Fondo de bandeja (interior contraportada) por defecto tiene las mismas dimensiones de contraportada
    assert default_p.interior_contraportada.width_mm == default_p.contraportada.width_mm
    assert default_p.interior_contraportada.height_mm == default_p.contraportada.height_mm
    assert default_p.interior_contraportada.enabled is True

    # Lomo secundario opcional viene desactivado por defecto
    assert default_p.lomo_secundario.width_mm == default_p.lomo.width_mm
    assert default_p.lomo_secundario.height_mm == default_p.lomo.height_mm
    assert default_p.lomo_secundario.enabled is False

    # Modificar y guardar
    default_p.interior_contraportada.width_mm = 47.5
    default_p.lomo_secundario.enabled = True
    default_p.lomo_secundario.width_mm = 6.0
    repo.save_profile(default_p)

    repo2 = ProfileRepository(file_path=temp_profile_file)
    reloaded = repo2.get_by_id("default_mini_cd_50")
    assert reloaded.interior_contraportada.width_mm == 47.5
    assert reloaded.lomo_secundario.enabled is True
    assert reloaded.lomo_secundario.width_mm == 6.0


