"""
Procesamiento de imágenes de alta precisión para mini álbumes con Pillow.
Asegura proporciones originales (sin deformación), recorte proporcional,
máscaras circulares con agujero central para CD, y renderizado de texto.
"""
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import math

from nfcito.models.project import CropConfig, TextConfig
from nfcito.core.units import mm_to_px

def render_piece_image(
    image_path: Optional[str],
    width_mm: float,
    height_mm: float,
    crop: Optional[CropConfig] = None,
    text_config: Optional[TextConfig] = None,
    is_circular: bool = False,
    inner_hole_mm: float = 0.0,
    has_inner_hole: bool = False,
    bleed_mm: float = 0.0,
    dpi: int = 300,
    background_color: Tuple[int, int, int, int] = (255, 255, 255, 0),
) -> Image.Image:
    """
    Renderiza una pieza gráfica con dimensiones físicas exactas en milímetros a alta resolución.
    Retorna una imagen PIL en modo RGBA.
    """
    crop = crop or CropConfig()
    total_w_mm = width_mm + (2 * bleed_mm)
    total_h_mm = height_mm + (2 * bleed_mm)
    
    out_w = mm_to_px(total_w_mm, dpi)
    out_h = mm_to_px(total_h_mm, dpi)

    # Base transparente
    canvas = Image.new("RGBA", (out_w, out_h), background_color)

    # Cargar y ajustar imagen de usuario si existe
    if image_path:
        try:
            with Image.open(image_path) as src_raw:
                # Corregir orientación EXIF si existe
                src = ImageOps.exif_transpose(src_raw)
                src = src.convert("RGBA")

                # Aplicar rotación
                if crop.rotation != 0:
                    src = src.rotate(-crop.rotation, expand=True, resample=Image.Resampling.BICUBIC)

                # Calcular escalado sin deformación (mantener ratio de aspecto)
                src_w, src_h = src.size
                src_ratio = src_w / max(1, src_h)
                target_ratio = out_w / max(1, out_h)

                # Modo "cover" con zoom proporcional
                if crop.fit_mode == "contain":
                    if src_ratio > target_ratio:
                        scale = out_w / src_w
                    else:
                        scale = out_h / src_h
                else:  # "cover" por defecto
                    if src_ratio > target_ratio:
                        scale = out_h / src_h
                    else:
                        scale = out_w / src_w

                # Aplicar zoom del usuario
                scale *= max(0.1, crop.zoom)

                new_w = max(1, int(round(src_w * scale)))
                new_h = max(1, int(round(src_h * scale)))

                resized_src = src.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Posicionamiento con pan_x y pan_y (-1.0 a 1.0)
                # Centro base
                base_x = (out_w - new_w) / 2
                base_y = (out_h - new_h) / 2

                # Desplazamiento máximo permitido para recorrer la imagen
                max_shift_x = max(0, (new_w - out_w) / 2)
                max_shift_y = max(0, (new_h - out_h) / 2)

                pos_x = int(round(base_x + (crop.pan_x * max_shift_x)))
                pos_y = int(round(base_y + (crop.pan_y * max_shift_y)))

                # Pegar sobre el canvas
                canvas.paste(resized_src, (pos_x, pos_y), resized_src)
        except Exception as e:
            # Si falla cargar la imagen, se continúa con el fondo y texto
            print(f"Error al procesar imagen '{image_path}': {e}")

    # Renderizar textos si están activos (ej. contraportada con tracklist)
    if text_config and text_config.enabled:
        draw_text_overlay(canvas, text_config, total_w_mm, total_h_mm, dpi)

    # Si es circular (Etiqueta CD)
    if is_circular:
        canvas = apply_circular_mask(
            canvas,
            outer_diameter_px=min(out_w, out_h),
            inner_hole_px=mm_to_px(inner_hole_mm, dpi) if has_inner_hole else 0
        )

    return canvas

def get_font_file(family: str, is_bold: bool = False, is_italic: bool = False) -> str:
    """Resuelve la ruta al archivo .ttf en Windows según familia y estilos."""
    fonts_dir = Path("C:/Windows/Fonts")
    family_lower = family.lower().strip()

    font_map = {
        "arial": {
            (False, False): "arial.ttf", (True, False): "arialbd.ttf",
            (False, True): "ariali.ttf", (True, True): "arialbi.ttf"
        },
        "calibri": {
            (False, False): "calibri.ttf", (True, False): "calibrib.ttf",
            (False, True): "calibrii.ttf", (True, True): "calibriz.ttf"
        },
        "segoe ui": {
            (False, False): "segoeui.ttf", (True, False): "segoeuib.ttf",
            (False, True): "segoeuii.ttf", (True, True): "segoeuiz.ttf"
        },
        "times new roman": {
            (False, False): "times.ttf", (True, False): "timesbd.ttf",
            (False, True): "timesi.ttf", (True, True): "timesbi.ttf"
        },
        "georgia": {
            (False, False): "georgia.ttf", (True, False): "georgiab.ttf",
            (False, True): "georgiai.ttf", (True, True): "georgiaz.ttf"
        },
        "verdana": {
            (False, False): "verdana.ttf", (True, False): "verdanab.ttf",
            (False, True): "verdanai.ttf", (True, True): "verdanaz.ttf"
        },
        "tahoma": {
            (False, False): "tahoma.ttf", (True, False): "tahomabd.ttf",
            (False, True): "tahoma.ttf", (True, True): "tahomabd.ttf"
        },
        "impact": {
            (False, False): "impact.ttf", (True, False): "impact.ttf",
            (False, True): "impact.ttf", (True, True): "impact.ttf"
        },
        "courier new": {
            (False, False): "cour.ttf", (True, False): "courbd.ttf",
            (False, True): "couri.ttf", (True, True): "courbi.ttf"
        },
        "bahnschrift": {
            (False, False): "bahnschrift.ttf", (True, False): "bahnschrift.ttf",
            (False, True): "bahnschrift.ttf", (True, True): "bahnschrift.ttf"
        },
    }

    sub_map = font_map.get(family_lower)
    if sub_map:
        filename = sub_map.get((is_bold, is_italic), sub_map.get((False, False)))
        path = fonts_dir / filename
        if path.exists():
            return str(path)

    # Búsqueda directa o fallback
    direct = fonts_dir / f"{family_lower}.ttf"
    if direct.exists():
        return str(direct)

    # Fallback Arial
    fallback = fonts_dir / ("arialbd.ttf" if is_bold else "arial.ttf")
    if fallback.exists():
        return str(fallback)

    return "arial.ttf"

def draw_text_overlay(
    canvas: Image.Image,
    text_cfg: TextConfig,
    w_mm: float,
    h_mm: float,
    dpi: int = 300
) -> None:
    """Dibuja texto tipográfico editable, estilizado y alineado con precisión sobre la imagen."""
    w_px, h_px = canvas.size

    margin_px = mm_to_px(text_cfg.padding_mm, dpi)

    # Obtener fuentes para título y cuerpo
    title_px = int(round(text_cfg.title_font_size * dpi / 72))
    body_px = int(round(text_cfg.font_size * dpi / 72))

    font_path = get_font_file(text_cfg.font_family, text_cfg.is_bold, text_cfg.is_italic)
    bold_font_path = get_font_file(text_cfg.font_family, is_bold=True, is_italic=text_cfg.is_italic)

    try:
        title_font = ImageFont.truetype(bold_font_path, max(10, title_px))
    except Exception:
        try:
            title_font = ImageFont.truetype("arial.ttf", max(10, title_px))
        except Exception:
            title_font = ImageFont.load_default()

    try:
        body_font = ImageFont.truetype(font_path, max(8, body_px))
    except Exception:
        try:
            body_font = ImageFont.truetype("arial.ttf", max(8, body_px))
        except Exception:
            body_font = ImageFont.load_default()

    # Pre-calcular líneas y alturas para alineación vertical
    items_to_render = []
    line_h_body = int(body_px * text_cfg.line_spacing)
    line_h_title = int(title_px * text_cfg.line_spacing)

    dummy_draw = ImageDraw.Draw(canvas)

    if text_cfg.full_body_text and text_cfg.full_body_text.strip():
        # Modo Documento Word libre
        for line in text_cfg.full_body_text.splitlines():
            line_str = line.strip()
            if not line_str:
                items_to_render.append(("spacer", "", body_font, 0, int(line_h_body * 0.5)))
            elif line_str.startswith("#"):
                clean = line_str.lstrip("#").strip()
                tb = dummy_draw.textbbox((0, 0), clean, font=title_font)
                items_to_render.append(("title", clean, title_font, tb[2] - tb[0], line_h_title))
            else:
                lb = dummy_draw.textbbox((0, 0), line_str, font=body_font)
                items_to_render.append(("body", line_str, body_font, lb[2] - lb[0], line_h_body))
    else:
        # Modo clásico con campos estructurados
        if text_cfg.title:
            tb = dummy_draw.textbbox((0, 0), text_cfg.title, font=title_font)
            items_to_render.append(("title", text_cfg.title, title_font, tb[2] - tb[0], tb[3] - tb[1] + int(margin_px * 0.3)))

        if text_cfg.artist:
            ab = dummy_draw.textbbox((0, 0), text_cfg.artist, font=body_font)
            items_to_render.append(("artist", text_cfg.artist, body_font, ab[2] - ab[0], ab[3] - ab[1] + int(margin_px * 0.4)))

        if text_cfg.tracks:
            for line in text_cfg.tracks.splitlines():
                line_str = line.strip()
                if not line_str:
                    items_to_render.append(("spacer", "", body_font, 0, int(line_h_body * 0.5)))
                else:
                    lb = dummy_draw.textbbox((0, 0), line_str, font=body_font)
                    items_to_render.append(("track", line_str, body_font, lb[2] - lb[0], line_h_body))

    total_text_h = sum(item[4] for item in items_to_render)

    # Calcular posición vertical de inicio
    if text_cfg.vertical_align == "middle":
        start_y = max(margin_px, int((h_px - total_text_h) / 2))
    elif text_cfg.vertical_align == "bottom":
        start_y = max(margin_px, int(h_px - total_text_h - margin_px))
    else:  # top
        start_y = margin_px

    # Dibujar caja de fondo translúcida u opaca detrás del bloque de texto si está configurada
    if text_cfg.bg_color and text_cfg.bg_opacity > 0.0:
        box_top = max(0, start_y - int(margin_px * 0.6))
        box_bottom = min(h_px, start_y + total_text_h + int(margin_px * 0.6))
        box_left = max(0, margin_px // 2)
        box_right = min(w_px, w_px - margin_px // 2)

        # Parsear color hex
        try:
            from PIL import ImageColor
            rgb = ImageColor.getrgb(text_cfg.bg_color)
            alpha = int(max(0.0, min(1.0, text_cfg.bg_opacity)) * 255)
            rgba = (rgb[0], rgb[1], rgb[2], alpha)

            box_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            box_draw = ImageDraw.Draw(box_overlay)
            corner_r = int(mm_to_px(1.5, dpi))
            box_draw.rounded_rectangle([box_left, box_top, box_right, box_bottom], radius=corner_r, fill=rgba)
            canvas.alpha_composite(box_overlay)
        except Exception as e:
            print(f"Aviso al dibujar caja de fondo: {e}")

    # Dibujar textos
    draw = ImageDraw.Draw(canvas)
    curr_y = start_y

    for kind, text, font, tw, th in items_to_render:
        if curr_y > h_px - margin_px:
            break
        if kind == "spacer":
            curr_y += th
            continue

        if text_cfg.alignment == "center":
            x = (w_px - tw) / 2
        elif text_cfg.alignment == "right":
            x = w_px - margin_px - tw
        else:  # left
            x = margin_px

        draw.text((x, curr_y), text, fill=text_cfg.text_color, font=font)
        curr_y += th

def apply_circular_mask(image: Image.Image, outer_diameter_px: int, inner_hole_px: int = 0) -> Image.Image:
    """Aplica recorte circular antialiaseado y remueve agujero central si corresponde."""
    w, h = image.size
    # Generar máscara a resolución 4x para antialiasing de alta calidad
    super_factor = 4
    mask_w, mask_h = w * super_factor, h * super_factor
    mask = Image.new("L", (mask_w, mask_h), 0)
    draw = ImageDraw.Draw(mask)

    center_x = mask_w / 2
    center_y = mask_h / 2
    radius_outer = (outer_diameter_px * super_factor) / 2

    # Círculo exterior
    draw.ellipse(
        [center_x - radius_outer, center_y - radius_outer, center_x + radius_outer, center_y + radius_outer],
        fill=255
    )

    # Agujero interior opcional
    if inner_hole_px > 0:
        radius_inner = (inner_hole_px * super_factor) / 2
        draw.ellipse(
            [center_x - radius_inner, center_y - radius_inner, center_x + radius_inner, center_y + radius_inner],
            fill=0
        )

    # Redimensionar máscara a tamaño final con filtro BOX/LANCZOS para antialiasing suave
    smooth_mask = mask.resize((w, h), Image.Resampling.LANCZOS)

    # Combinar máscara con canal alpha existente
    output = image.copy()
    if output.mode != "RGBA":
        output = output.convert("RGBA")
    
    # Multiplicar alpha existente con la nueva máscara
    orig_r, orig_g, orig_b, orig_a = output.split()
    combined_a = ImageOps.invert(smooth_mask)
    # Nueva máscara alpha
    new_a = ImageOps.invert(ImageOps.invert(orig_a))
    # Aplicar smooth_mask al canal alpha
    output.putalpha(smooth_mask)
    return output
