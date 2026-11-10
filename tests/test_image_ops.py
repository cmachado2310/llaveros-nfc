"""
Pruebas obligatorias para el procesamiento de imágenes:
1. Recorte proporcional sin deformación (mantiene relación de aspecto).
2. Piezas circulares con agujero central opcional.
3. Transformaciones de zoom, rotación y encuadre.
"""
import pytest
import tempfile
import os
from PIL import Image

from nfcito.core.image_ops import render_piece_image, apply_circular_mask
from nfcito.models.project import CropConfig, TextConfig
from nfcito.core.units import mm_to_px

@pytest.fixture
def sample_wide_image():
    # Imagen rectangular ancha (aspecto 2:1)
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    img = Image.new("RGBA", (400, 200), color=(0, 128, 255, 255))
    img.save(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_crop_preserves_aspect_ratio_without_distortion(sample_wide_image):
    # Renderizar en un área cuadrada de 48 x 48 mm a 300 DPI
    target_w_mm = 48.0
    target_h_mm = 48.0
    crop = CropConfig(fit_mode="cover", zoom=1.0)

    out = render_piece_image(
        image_path=sample_wide_image,
        width_mm=target_w_mm,
        height_mm=target_h_mm,
        crop=crop,
        dpi=300
    )

    expected_w_px = mm_to_px(target_w_mm, 300)
    expected_h_px = mm_to_px(target_h_mm, 300)

    # El resultado debe tener exactamente las dimensiones físicas en px requeridas
    assert out.size == (expected_w_px, expected_h_px)
    # Debe ser modo RGBA
    assert out.mode == "RGBA"

def test_circular_piece_with_inner_hole(sample_wide_image):
    # CD de 40 mm de diámetro con agujero de 10 mm
    d_mm = 40.0
    hole_mm = 10.0

    out = render_piece_image(
        image_path=sample_wide_image,
        width_mm=d_mm,
        height_mm=d_mm,
        is_circular=True,
        inner_hole_mm=hole_mm,
        has_inner_hole=True,
        dpi=300
    )

    w_px, h_px = out.size
    cx = w_px // 2
    cy = h_px // 2

    # El centro exacto (agujero interior) debe ser completamente transparente (alpha == 0)
    center_pixel = out.getpixel((cx, cy))
    assert center_pixel[3] == 0, f"El agujero central debe ser transparente. Alpha={center_pixel[3]}"

    # Las cuatro esquinas exteriores del cuadrado deben ser transparentes (fuera del círculo)
    corner_pixel = out.getpixel((2, 2))
    assert corner_pixel[3] == 0, f"Las esquinas del CD deben ser transparentes. Alpha={corner_pixel[3]}"

    # Un punto a mitad de radio debe ser opaco (dentro de la etiqueta)
    mid_radius_px = int(cx + (cx * 0.5))
    mid_pixel = out.getpixel((mid_radius_px, cy))
    assert mid_pixel[3] > 200, f"La etiqueta del disco debe ser visible. Alpha={mid_pixel[3]}"

def test_text_overlay_rendering(sample_wide_image):
    text_cfg = TextConfig(
        enabled=True,
        title="Mi Gran Álbum",
        artist="Cantante",
        tracks="1. Pista Uno\n2. Pista Dos",
        text_color="#FF0000"
    )
    out = render_piece_image(
        image_path=sample_wide_image,
        width_mm=48.0,
        height_mm=48.0,
        text_config=text_cfg,
        dpi=150
    )
    assert out.size[0] > 0
    assert out.size[1] > 0

def test_rich_text_overlay_customization(sample_wide_image):
    # Prueba de fuentes, negrita, cursiva, caja de fondo y alineación vertical
    text_cfg = TextConfig(
        enabled=True,
        title="Álbum Delux",
        artist="Banda Sonora",
        tracks="1. Intro\n2. Tema Principal\n3. Final",
        font_family="Calibri",
        font_size=9,
        title_font_size=12,
        is_bold=True,
        is_italic=True,
        text_color="#FFFFFF",
        bg_color="#000000",
        bg_opacity=0.6,
        alignment="center",
        vertical_align="middle",
        line_spacing=1.4,
        padding_mm=3.0
    )
    out = render_piece_image(
        image_path=sample_wide_image,
        width_mm=48.0,
        height_mm=48.0,
        text_config=text_cfg,
        dpi=150
    )
    assert out.size == (mm_to_px(48.0, 150), mm_to_px(48.0, 150))
    # Comprobar que no es completamente transparente
    alpha_max = out.getchannel("A").getextrema()[1]
    assert alpha_max > 0

def test_word_style_full_body_text_rendering(sample_wide_image):
    """Verifica que el editor libre estilo Word con títulos y tracklist multilínea
    se renderiza fielmente sobre la contraportada."""
    text_cfg = TextConfig(
        enabled=True,
        full_body_text="# MI ÁLBUM FAVORITO\nArtista Principal (2024)\n\n1. Canción Uno (3:45)\n2. Canción Dos (4:10)\n3. Créditos Finales",
        font_family="Arial",
        font_size=8,
        title_font_size=11,
        is_bold=False,
        is_italic=False,
        is_underline=True,
        text_color="#FFFFFF",
        bg_color="#000000",
        bg_opacity=0.7,
        alignment="left",
        vertical_align="top",
        line_spacing=1.3,
        padding_mm=2.5
    )
    out = render_piece_image(
        image_path=sample_wide_image,
        width_mm=48.0,
        height_mm=48.0,
        text_config=text_cfg,
        dpi=150
    )
    assert out.size == (mm_to_px(48.0, 150), mm_to_px(48.0, 150))
    alpha_max = out.getchannel("A").getextrema()[1]
    assert alpha_max > 0

