"""
Vista previa de conjunto del mini álbum completo.
Renderiza un mockup visual del estuche mini CD transparente con portada,
lomo, contraportada y disco CD ensamblados.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QImage, QPixmap, QFont, QPaintEvent
)
from PIL import Image

from nfcito.models.project import Project
from nfcito.models.profile import CaseProfile
from nfcito.core.image_ops import render_piece_image

class CompositeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.profile: Optional[CaseProfile] = None
        self._cache_pixmaps: dict = {}

    def set_data(self, project: Optional[Project], profile: Optional[CaseProfile]):
        self.project = project
        self.profile = profile
        self._cache_pixmaps.clear()
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo
        painter.fillRect(self.rect(), QColor("#EDF0F5"))

        if not self.project or not self.profile:
            painter.setFont(QFont("Segoe UI", 12))
            painter.setPen(QColor("#64748B"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sin datos de proyecto para mostrar.")
            return

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        # Título
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.setPen(QColor("#1E293B"))
        painter.drawText(20, 30, f"Maqueta de Conjunto: {self.project.name}")

        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#64748B"))
        painter.drawText(20, 50, f"Estuche Acrílico Transparente ({self.profile.exterior_width_mm} × {self.profile.exterior_height_mm} mm)")

        # Dibujar dos secciones principales:
        # 1. Estuche cerrado / desplegado (Portada + Lomo + Contraportada)
        # 2. Mini CD saliendo o al lado

        # Escala de renderizado
        scale = min((self.width() - 80) / 220.0, (self.height() - 120) / 100.0)
        scale = max(1.2, min(2.5, scale))

        # Medidas en pixels
        front_w = self.profile.portada.width_mm * scale
        front_h = self.profile.portada.height_mm * scale
        spine_w = self.profile.lomo.width_mm * scale
        back_w = self.profile.contraportada.width_mm * scale
        cd_d = self.profile.cd.outer_diameter_mm * scale

        total_inlay_w = back_w + spine_w + front_w
        start_x = cx - (total_inlay_w + cd_d * 0.7) / 2.0
        y_pos = cy - (front_h / 2.0)

        # 1. Contraportada
        back_rect = QRectF(start_x, y_pos, back_w, front_h)
        self._render_piece_mockup(painter, "contraportada", back_rect, "Contraportada")

        # 2. Lomo
        spine_rect = QRectF(start_x + back_w, y_pos, spine_w, front_h)
        self._render_piece_mockup(painter, "lomo", spine_rect, "Lomo")

        # 3. Portada Frontal
        front_rect = QRectF(start_x + back_w + spine_w, y_pos, front_w, front_h)
        self._render_piece_mockup(painter, "portada", front_rect, "Portada")

        # Efecto estuche acrílico desplegado alrededor del inlay
        case_margin = 2.0 * scale
        case_rect = QRectF(
            start_x - case_margin,
            y_pos - case_margin,
            total_inlay_w + 2 * case_margin,
            front_h + 2 * case_margin
        )
        # Marco acrílico transparente brillante
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(QColor(255, 255, 255, 25))
        painter.drawRoundedRect(case_rect, 6, 6)
        painter.setPen(QPen(QColor(180, 200, 220, 120), 1))
        painter.drawRoundedRect(case_rect, 6, 6)

        # 4. Mini CD (a la derecha, superpuesto o al lado)
        cd_x = start_x + total_inlay_w + (15 * scale)
        cd_y = cy - (cd_d / 2.0)
        cd_rect = QRectF(cd_x, cd_y, cd_d, cd_d)

        # Sombra del CD
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cd_rect.adjusted(3, 3, 3, 3))

        # Base plateada / brillo de CD
        painter.setBrush(QColor("#E2E8F0"))
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.drawEllipse(cd_rect)

        # Mockup de imagen de CD
        self._render_cd_mockup(painter, cd_rect, scale)

        # 5. Libreto Interior (si está habilitado o tiene imagen)
        int_piece = self.project.get_piece("interior")
        if int_piece and (int_piece.image_path or int_piece.enabled_for_print):
            int_dim = self.profile.get_piece_dimension("interior")
            int_w_mm = int_piece.custom_width_mm or (int_dim.width_mm if int_dim else max(5.0, self.profile.portada.width_mm - 1.5))
            int_h_mm = int_piece.custom_height_mm or (int_dim.height_mm if int_dim else max(5.0, self.profile.portada.height_mm - 1.5))
            if not int_piece.custom_width_mm and int_w_mm >= self.profile.portada.width_mm:
                int_w_mm = max(5.0, round(self.profile.portada.width_mm - 1.5, 1))
                int_h_mm = max(5.0, round(self.profile.portada.height_mm - 1.5, 1))

            int_w = int_w_mm * scale
            int_h = int_h_mm * scale
            int_x = cd_x + cd_d + (20 * scale)

            if int_x + int_w <= self.width() - 20:
                int_y = cy - (int_h / 2.0)
            else:
                int_x = start_x + (back_w + spine_w)
                int_y = y_pos + front_h + (20 * scale)

            int_rect = QRectF(int_x, int_y, int_w, int_h)
            # Sombra suave
            painter.setBrush(QColor(0, 0, 0, 25))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int_rect.adjusted(3, 3, 3, 3))
            self._render_piece_mockup(painter, "interior", int_rect, f"Libreto Interior\n({int_w_mm:.1f} × {int_h_mm:.1f} mm)")

    def _render_piece_mockup(self, painter: QPainter, piece_key: str, rect: QRectF, label: str):
        painter.save()
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawRect(rect)

        piece = self.project.get_piece(piece_key) if self.project else None
        if piece and piece.image_path:
            if piece_key not in self._cache_pixmaps:
                dim = self.profile.get_piece_dimension(piece_key)
                w_mm = piece.custom_width_mm or (dim.width_mm if dim else 48.0)
                h_mm = piece.custom_height_mm or (dim.height_mm if dim else 48.0)
                try:
                    pil_img = render_piece_image(
                        image_path=piece.image_path,
                        width_mm=w_mm,
                        height_mm=h_mm,
                        crop=piece.crop,
                        text_config=piece.text_overlay,
                        is_circular=False,
                        dpi=120
                    )
                    data = pil_img.tobytes("raw", "RGBA")
                    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
                    self._cache_pixmaps[piece_key] = QPixmap.fromImage(qimg)
                except Exception:
                    self._cache_pixmaps[piece_key] = None

            pix = self._cache_pixmaps.get(piece_key)
            if pix and not pix.isNull():
                painter.drawPixmap(rect.toRect(), pix)
        else:
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        painter.restore()

    def _render_cd_mockup(self, painter: QPainter, rect: QRectF, scale: float):
        painter.save()
        cd_piece = self.project.get_piece("cd") if self.project else None
        d_mm = self.profile.cd.outer_diameter_mm if self.profile else 40.0
        hole_d_mm = self.profile.cd.inner_hole_diameter_mm if self.profile else 10.0

        if cd_piece and cd_piece.image_path:
            if "cd" not in self._cache_pixmaps:
                try:
                    pil_img = render_piece_image(
                        image_path=cd_piece.image_path,
                        width_mm=d_mm,
                        height_mm=d_mm,
                        crop=cd_piece.crop,
                        is_circular=True,
                        inner_hole_mm=hole_d_mm,
                        has_inner_hole=self.profile.cd.has_inner_hole if self.profile else True,
                        dpi=120
                    )
                    data = pil_img.tobytes("raw", "RGBA")
                    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
                    self._cache_pixmaps["cd"] = QPixmap.fromImage(qimg)
                except Exception:
                    self._cache_pixmaps["cd"] = None

            pix = self._cache_pixmaps.get("cd")
            if pix and not pix.isNull():
                painter.drawPixmap(rect.toRect(), pix)
        else:
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#64748B"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "CD Disc")

        # Agujero central
        if self.profile and self.profile.cd.has_inner_hole:
            hole_px = hole_d_mm * scale
            cx = rect.center().x()
            cy = rect.center().y()
            hole_rect = QRectF(cx - hole_px / 2.0, cy - hole_px / 2.0, hole_px, hole_px)
            painter.setBrush(QColor("#EDF0F5"))
            painter.setPen(QPen(QColor("#94A3B8"), 1))
            painter.drawEllipse(hole_rect)

        painter.restore()
