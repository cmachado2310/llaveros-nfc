"""
Lienzo interactivo de edición gráfica para NFCito Studio.
Previsualización del corte automático con máscara exterior translúcida,
movimiento y encuadre fluido en tiempo real, zoom con rueda y drag & drop.
"""
from typing import Optional
import os
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPoint, QRectF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QImage, QPixmap, QFont, QPaintEvent,
    QMouseEvent, QWheelEvent, QDragEnterEvent, QDropEvent, QPainterPath, QTransform
)
from PIL import Image, ImageOps

from nfcito.models.project import PieceDesign, CropConfig
from nfcito.models.profile import CaseProfile
from nfcito.core.image_ops import render_piece_image
from nfcito.core.units import mm_to_px

class CanvasView(QWidget):
    cropChanged = Signal(float, float, float)  # zoom, pan_x, pan_y
    imageDropped = Signal(str)                 # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.current_piece: Optional[PieceDesign] = None
        self.current_profile: Optional[CaseProfile] = None
        self.piece_key: str = "portada"

        # Interacción de arrastre en tiempo real
        self._is_dragging: bool = False
        self._last_mouse_pos: QPoint = QPoint()

        # Cache de la imagen original cargada para arrastre fluido a 60 FPS
        self._loaded_image_path: Optional[str] = None
        self._loaded_rotation: int = 0
        self._source_pixmap: Optional[QPixmap] = None

        # Opciones visuales
        self.show_safe_margin: bool = True
        self.show_bleed: bool = True
        self.show_overflow_preview: bool = True
        self.is_preview_mode: bool = False  # Modo vista previa limpia sin guías

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    def set_preview_mode(self, enabled: bool):
        self.is_preview_mode = enabled
        self.update()

    def set_data(self, piece: Optional[PieceDesign], profile: Optional[CaseProfile], piece_key: str = "portada"):
        self.current_piece = piece
        self.current_profile = profile
        self.piece_key = piece_key
        self._sync_source_pixmap()
        self.update()

    def _sync_source_pixmap(self):
        """Carga o actualiza en caché la imagen fuente para transformación rápida."""
        if not self.current_piece or not self.current_piece.image_path:
            self._source_pixmap = None
            self._loaded_image_path = None
            return

        img_path = self.current_piece.image_path
        rot = self.current_piece.crop.rotation

        if img_path != self._loaded_image_path or rot != self._loaded_rotation or self._source_pixmap is None:
            if os.path.exists(img_path):
                try:
                    with Image.open(img_path) as raw:
                        img = ImageOps.exif_transpose(raw)
                        img = img.convert("RGBA")
                        if rot != 0:
                            img = img.rotate(-rot, expand=True, resample=Image.Resampling.BICUBIC)

                        # Limitar tamaño máximo para visualización fluida
                        max_dim = 1800
                        if max(img.size) > max_dim:
                            img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)

                        data = img.tobytes("raw", "RGBA")
                        qimg = QImage(data, img.size[0], img.size[1], QImage.Format.Format_RGBA8888)
                        self._source_pixmap = QPixmap.fromImage(qimg)
                        self._loaded_image_path = img_path
                        self._loaded_rotation = rot
                except Exception as e:
                    print(f"Error cargando imagen en lienzo: {e}")
                    self._source_pixmap = None
            else:
                self._source_pixmap = None

    def refresh_preview(self):
        """Refresca la vista garantizando sincronización con el modelo."""
        self._sync_source_pixmap()
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fondo del lienzo
        if self.is_preview_mode:
            painter.fillRect(self.rect(), QColor("#F8FAFC"))
        else:
            painter.fillRect(self.rect(), QColor("#E9EDF2"))
            self._draw_grid(painter)

        if not self.current_piece or not self.current_profile:
            self._draw_empty_message(painter, "Seleccione una pieza del álbum a la izquierda.")
            return

        dim = self.current_profile.get_piece_dimension(self.piece_key)
        if not dim:
            self._draw_empty_message(painter, "Pieza no disponible en el perfil actual.")
            return

        w_mm = self.current_piece.custom_width_mm or dim.width_mm
        h_mm = self.current_piece.custom_height_mm or dim.height_mm
        is_circ = dim.is_circular

        # Escala estable de la pieza en pantalla (evita que editar la altura encoja visualmente el ancho)
        view_w = self.width() - 100
        view_h = self.height() - 100
        if view_w <= 20 or view_h <= 20:
            return

        ref_dim = max(55.0, max(self.current_profile.portada.width_mm, self.current_profile.portada.height_mm))
        scale = min(view_w, view_h) / (ref_dim * 1.15)
        piece_pw = w_mm * scale
        piece_ph = h_mm * scale

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        piece_rect = QRectF(center_x - piece_pw / 2.0, center_y - piece_ph / 2.0, piece_pw, piece_ph)

        # Sombra de la pieza
        shadow_rect = piece_rect.adjusted(4, 4, 4, 4)
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        if is_circ:
            painter.drawEllipse(shadow_rect)
        else:
            painter.drawRoundedRect(shadow_rect, 6, 6)

        # Base blanca de la pieza
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        if is_circ:
            painter.drawEllipse(piece_rect)
        else:
            painter.drawRect(piece_rect)

        # Si hay imagen asignada, dibujar previsualización con encuadre
        if self._source_pixmap and not self._source_pixmap.isNull():
            self._draw_image_with_cut_preview(painter, piece_rect, scale, is_circ, dim)
        else:
            self._draw_placeholder(painter, piece_rect, is_circ)

        # Textos de contraportada en tiempo real (si está vacía o con imagen)
        if self.piece_key == "contraportada":
            t_cfg = self.current_piece.text_overlay
            has_text = bool(t_cfg.full_body_text or t_cfg.title or t_cfg.tracks or t_cfg.artist)
            if t_cfg.enabled or has_text:
                self._draw_canvas_text_overlay(painter, piece_rect, scale)

        # Guías de corte, seguridad y sangrado
        self._draw_guides(painter, piece_rect, scale, is_circ)

        # Barra de ayuda e información inferior
        self._draw_bottom_info(painter, w_mm, h_mm, is_circ)

    def _draw_image_with_cut_preview(self, painter: QPainter, piece_rect: QRectF, scale: float, is_circ: bool, dim):
        """
        Dibuja la imagen completa mostrando la parte exterior atenuada (máscara translúcida)
        y la parte interna recortada al 100% de brillo, permitiendo ver el corte exacto en tiempo real.
        """
        src_w = self._source_pixmap.width()
        src_h = self._source_pixmap.height()
        if src_w <= 0 or src_h <= 0:
            return

        crop = self.current_piece.crop
        piece_pw = piece_rect.width()
        piece_ph = piece_rect.height()

        # Calcular escalado según modo
        src_ratio = src_w / max(1.0, src_h)
        target_ratio = piece_pw / max(1.0, piece_ph)

        if crop.fit_mode == "contain":
            base_scale = min(piece_pw / src_w, piece_ph / src_h)
        else:  # "cover" proporcional (por defecto)
            base_scale = max(piece_pw / src_w, piece_ph / src_h)

        final_scale = base_scale * max(0.2, crop.zoom)
        img_w = src_w * final_scale
        img_h = src_h * final_scale

        max_shift_x = max(0.0, (img_w - piece_pw) / 2.0)
        max_shift_y = max(0.0, (img_h - piece_ph) / 2.0)

        # Coordenadas de la imagen en pantalla
        base_x = piece_rect.x() + (piece_pw - img_w) / 2.0
        base_y = piece_rect.y() + (piece_ph - img_h) / 2.0

        pos_x = base_x + (crop.pan_x * max_shift_x)
        pos_y = base_y + (crop.pan_y * max_shift_y)
        img_rect = QRectF(pos_x, pos_y, img_w, img_h)

        # 1. Dibujar imagen completa fuera del área de corte con opacidad reducida (para ver qué se recorta)
        if not self.is_preview_mode and self.show_overflow_preview and (img_w > piece_pw or img_h > piece_ph):
            painter.save()
            painter.setOpacity(0.35)  # Atenuado para visualizar el encuadre
            painter.drawPixmap(img_rect.toRect(), self._source_pixmap)
            # Tinte oscuro sobre el sobrante
            painter.setBrush(QColor(0, 0, 0, 80))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(img_rect)
            painter.restore()

        # 2. Dibujar área interior de corte al 100% de nitidez (usando clip path)
        painter.save()
        clip_path = QPainterPath()
        if is_circ:
            clip_path.addEllipse(piece_rect)
            # Si tiene agujero central, excluirlo del clip
            if self.current_profile and self.current_profile.cd.has_inner_hole:
                hole_d_px = self.current_profile.cd.inner_hole_diameter_mm * scale
                cx = piece_rect.center().x()
                cy = piece_rect.center().y()
                hole_rect = QRectF(cx - hole_d_px / 2.0, cy - hole_d_px / 2.0, hole_d_px, hole_d_px)
                hole_path = QPainterPath()
                hole_path.addEllipse(hole_rect)
                clip_path = clip_path.subtracted(hole_path)
        else:
            clip_path.addRect(piece_rect)

        painter.setClipPath(clip_path)

        # Fondo blanco previo en el área de corte
        painter.fillRect(piece_rect, QColor("#FFFFFF"))
        # Imagen nítida adentro
        painter.drawPixmap(img_rect.toRect(), self._source_pixmap)

        painter.restore()

    def _draw_canvas_text_overlay(self, painter: QPainter, rect: QRectF, scale: float):
        """Renderiza texto de contraportada en tiempo real directamente sobre el lienzo (Estilo Word)."""
        t_cfg = self.current_piece.text_overlay
        pad = t_cfg.padding_mm * scale
        inner_rect = rect.adjusted(pad, pad, -pad, -pad)

        if inner_rect.width() <= 10 or inner_rect.height() <= 10:
            return

        # Fondo del bloque si tiene opacidad
        if t_cfg.bg_color and t_cfg.bg_opacity > 0:
            c = QColor(t_cfg.bg_color)
            c.setAlphaF(t_cfg.bg_opacity)
            painter.setBrush(c)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(inner_rect.adjusted(-2, -2, 2, 2), 4, 4)

        painter.setPen(QColor(t_cfg.text_color))

        # Configuración tipográfica alineación
        align_flag = Qt.AlignmentFlag.AlignLeft
        if t_cfg.alignment == "center":
            align_flag = Qt.AlignmentFlag.AlignHCenter
        elif t_cfg.alignment == "right":
            align_flag = Qt.AlignmentFlag.AlignRight

        flags = align_flag | Qt.TextFlag.TextWordWrap

        # 1. Si hay texto libre tipo Documento Word
        if t_cfg.full_body_text and t_cfg.full_body_text.strip():
            font_body = QFont(t_cfg.font_family, max(6, int(t_cfg.font_size * scale * 0.35)))
            font_body.setBold(t_cfg.is_bold)
            font_body.setItalic(t_cfg.is_italic)
            font_body.setUnderline(t_cfg.is_underline)

            font_heading = QFont(t_cfg.font_family, max(8, int(t_cfg.title_font_size * scale * 0.38)))
            font_heading.setBold(True)
            font_heading.setItalic(t_cfg.is_italic)
            font_heading.setUnderline(t_cfg.is_underline)

            curr_y = inner_rect.y()
            line_h = max(12.0, font_body.pointSize() * 1.5 * t_cfg.line_spacing)

            for line in t_cfg.full_body_text.splitlines():
                if curr_y > inner_rect.bottom():
                    break
                line_str = line.strip()
                if not line_str:
                    curr_y += line_h * 0.6
                    continue
                if line_str.startswith("#"):
                    clean = line_str.lstrip("#").strip()
                    painter.setFont(font_heading)
                    head_h = max(16.0, font_heading.pointSize() * 1.6)
                    painter.drawText(QRectF(inner_rect.x(), curr_y, inner_rect.width(), head_h), flags, clean)
                    curr_y += head_h + 3
                else:
                    painter.setFont(font_body)
                    painter.drawText(QRectF(inner_rect.x(), curr_y, inner_rect.width(), line_h), flags, line_str)
                    curr_y += line_h
            return

        # 2. Modo clásico (Título, Artista, Canciones)
        curr_y = inner_rect.y()
        # Título
        if t_cfg.title:
            font_title = QFont(t_cfg.font_family, max(8, int(t_cfg.title_font_size * scale * 0.35)))
            font_title.setBold(True)
            font_title.setItalic(t_cfg.is_italic)
            font_title.setUnderline(t_cfg.is_underline)
            painter.setFont(font_title)
            h_title = 24 * scale * 0.35 + 4
            painter.drawText(QRectF(inner_rect.x(), curr_y, inner_rect.width(), h_title), flags, t_cfg.title)
            curr_y += h_title

        # Artista
        if t_cfg.artist:
            font_art = QFont(t_cfg.font_family, max(7, int(t_cfg.font_size * scale * 0.35)))
            font_art.setBold(t_cfg.is_bold)
            font_art.setItalic(True)
            font_art.setUnderline(t_cfg.is_underline)
            painter.setFont(font_art)
            h_art = 18 * scale * 0.35 + 4
            painter.drawText(QRectF(inner_rect.x(), curr_y, inner_rect.width(), h_art), flags, t_cfg.artist)
            curr_y += h_art

        # Tracklist
        if t_cfg.tracks:
            font_tracks = QFont(t_cfg.font_family, max(6, int(t_cfg.font_size * scale * 0.32)))
            font_tracks.setBold(t_cfg.is_bold)
            font_tracks.setItalic(t_cfg.is_italic)
            font_tracks.setUnderline(t_cfg.is_underline)
            painter.setFont(font_tracks)
            h_rem = inner_rect.bottom() - curr_y
            if h_rem > 10:
                painter.drawText(QRectF(inner_rect.x(), curr_y, inner_rect.width(), h_rem), flags, t_cfg.tracks)

    def _draw_bottom_info(self, painter: QPainter, w_mm: float, h_mm: float, is_circ: bool):
        # Cartel informativo en la base
        info_rect = QRectF(20, self.height() - 36, self.width() - 40, 26)
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRoundedRect(info_rect, 6, 6)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        painter.setPen(QColor("#334155"))

        zoom_pct = int(round(self.current_piece.crop.zoom * 100)) if self.current_piece else 100
        dim_str = f"{w_mm:.1f} × {h_mm:.1f} mm" if not is_circ else f"Ø {w_mm:.1f} mm"

        if self.is_preview_mode:
            painter.setPen(QColor("#1D4ED8"))
            hint = f"👁️ VISTA PREVIA REAL ({dim_str}) — Así lucirá la pieza cortada e impresa en el mini estuche"
        else:
            hint = f"📐 Medida: {dim_str}  |  🔍 Zoom: {zoom_pct}%  |  🖱️ Arrastre para encuadrar en vivo  |  🔄 Rueda: Zoom"

        painter.drawText(info_rect, Qt.AlignmentFlag.AlignCenter, hint)

    def _draw_grid(self, painter: QPainter):
        pen = QPen(QColor("#DFE4EA"), 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        grid_step = 25
        for x in range(0, self.width(), grid_step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), grid_step):
            painter.drawLine(0, y, self.width(), y)

    def _draw_empty_message(self, painter: QPainter, msg: str):
        painter.setFont(QFont("Segoe UI", 12))
        painter.setPen(QColor("#64748B"))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, msg)

    def _draw_placeholder(self, painter: QPainter, rect: QRectF, is_circ: bool):
        painter.save()
        painter.setFont(QFont("Segoe UI", 11))
        painter.setPen(QColor("#94A3B8"))
        msg = "📁 Haga clic en 'Cargar Imagen'\no arrastre un archivo aquí"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, msg)
        painter.restore()

    def _draw_guides(self, painter: QPainter, rect: QRectF, scale: float, is_circ: bool):
        # Si está en modo vista previa limpia, solo dibujar borde exterior sutil realista
        if self.is_preview_mode:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if is_circ:
                painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
                painter.drawEllipse(rect)
                if self.current_profile and self.current_profile.cd.has_inner_hole:
                    hole_d_px = self.current_profile.cd.inner_hole_diameter_mm * scale
                    cx = rect.center().x()
                    cy = rect.center().y()
                    hole_rect = QRectF(cx - hole_d_px / 2.0, cy - hole_d_px / 2.0, hole_d_px, hole_d_px)
                    painter.setPen(QPen(QColor("#94A3B8"), 1))
                    painter.drawEllipse(hole_rect)
            else:
                painter.setPen(QPen(QColor("#CBD5E1"), 1.2))
                painter.drawRect(rect)
            return

        # 1. Borde de corte de la pieza (línea continua azul)
        pen_cut = QPen(QColor("#2563EB"), 1.8, Qt.PenStyle.SolidLine)
        painter.setPen(pen_cut)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if is_circ:
            painter.drawEllipse(rect)
        else:
            painter.drawRect(rect)

        # 2. Margen de seguridad (1.5mm hacia adentro, línea discontinua verde)
        if self.show_safe_margin and self.current_profile:
            safe_px = self.current_profile.safe_margin_mm * scale
            safe_rect = rect.adjusted(safe_px, safe_px, -safe_px, -safe_px)
            if safe_rect.width() > 0 and safe_rect.height() > 0:
                pen_safe = QPen(QColor("#10B981"), 1.2, Qt.PenStyle.DashLine)
                painter.setPen(pen_safe)
                if is_circ:
                    painter.drawEllipse(safe_rect)
                else:
                    painter.drawRect(safe_rect)

        # 3. Sangrado (1.5mm hacia afuera, línea punteada roja)
        if self.show_bleed and self.current_profile:
            bleed_px = self.current_profile.bleed_mm * scale
            bleed_rect = rect.adjusted(-bleed_px, -bleed_px, bleed_px, bleed_px)
            pen_bleed = QPen(QColor("#EF4444"), 1, Qt.PenStyle.DotLine)
            painter.setPen(pen_bleed)
            if is_circ:
                painter.drawEllipse(bleed_rect)
            else:
                painter.drawRect(bleed_rect)

        # 4. Agujero central si es CD
        if is_circ and self.current_profile and self.current_profile.cd.has_inner_hole:
            hole_d_px = self.current_profile.cd.inner_hole_diameter_mm * scale
            cx = rect.center().x()
            cy = rect.center().y()
            hole_rect = QRectF(cx - hole_d_px / 2.0, cy - hole_d_px / 2.0, hole_d_px, hole_d_px)
            pen_hole = QPen(QColor("#DC2626"), 1.5, Qt.PenStyle.SolidLine)
            painter.setPen(pen_hole)
            painter.drawEllipse(hole_rect)

            # Cruz central
            painter.drawLine(int(cx - 8), int(cy), int(cx + 8), int(cy))
            painter.drawLine(int(cx), int(cy - 8), int(cx), int(cy + 8))

    # Eventos de ratón y teclado para encuadre interactivo ultra-fluido (Pan & Zoom)
    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and self.current_piece and self.current_piece.image_path:
            delta = event.pos() - self._last_mouse_pos
            self._last_mouse_pos = event.pos()

            # Sensibilidad proporcional para movimiento natural y suave
            view_w = max(100, self.width() - 100)
            sens = 2.5 / (view_w * max(0.5, self.current_piece.crop.zoom))

            new_pan_x = max(-1.0, min(1.0, self.current_piece.crop.pan_x + delta.x() * sens))
            new_pan_y = max(-1.0, min(1.0, self.current_piece.crop.pan_y + delta.y() * sens))

            self.current_piece.crop.pan_x = new_pan_x
            self.current_piece.crop.pan_y = new_pan_y

            self.cropChanged.emit(self.current_piece.crop.zoom, new_pan_x, new_pan_y)
            # Repintado instantáneo en tiempo real a 60 FPS
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event: QWheelEvent):
        if self.current_piece and self.current_piece.image_path:
            delta = event.angleDelta().y()
            step = 0.08 if delta > 0 else -0.08
            new_zoom = max(1.0, min(5.0, self.current_piece.crop.zoom + step))
            self.current_piece.crop.zoom = round(new_zoom, 2)
            self.cropChanged.emit(self.current_piece.crop.zoom, self.current_piece.crop.pan_x, self.current_piece.crop.pan_y)
            self.update()

    def keyPressEvent(self, event):
        """Permite mover el zoom y el encuadre usando las flechas del teclado."""
        if not self.current_piece or not self.current_piece.image_path:
            super().keyPressEvent(event)
            return

        k = event.key()
        if k in (Qt.Key.Key_Up, Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            # Flecha Arriba o tecla + para acercar zoom
            new_zoom = min(5.0, round(self.current_piece.crop.zoom + 0.08, 2))
            self.current_piece.crop.zoom = new_zoom
            self.cropChanged.emit(self.current_piece.crop.zoom, self.current_piece.crop.pan_x, self.current_piece.crop.pan_y)
            self.update()
            event.accept()
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_Minus):
            # Flecha Abajo o tecla - para alejar zoom
            new_zoom = max(1.0, round(self.current_piece.crop.zoom - 0.08, 2))
            self.current_piece.crop.zoom = new_zoom
            self.cropChanged.emit(self.current_piece.crop.zoom, self.current_piece.crop.pan_x, self.current_piece.crop.pan_y)
            self.update()
            event.accept()
        elif k == Qt.Key.Key_Left:
            # Flecha Izquierda para desplazar horizontalmente
            new_pan_x = max(-1.0, round(self.current_piece.crop.pan_x - 0.04, 3))
            self.current_piece.crop.pan_x = new_pan_x
            self.cropChanged.emit(self.current_piece.crop.zoom, new_pan_x, self.current_piece.crop.pan_y)
            self.update()
            event.accept()
        elif k == Qt.Key.Key_Right:
            # Flecha Derecha para desplazar horizontalmente
            new_pan_x = min(1.0, round(self.current_piece.crop.pan_x + 0.04, 3))
            self.current_piece.crop.pan_x = new_pan_x
            self.cropChanged.emit(self.current_piece.crop.zoom, new_pan_x, self.current_piece.crop.pan_y)
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)

    # Drag & Drop de archivos de imagen directamente al lienzo
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
                    event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.exists(path):
                self.imageDropped.emit(path)
                event.acceptProposedAction()
