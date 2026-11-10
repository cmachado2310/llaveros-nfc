"""
Generador Rápido (Modo Automático) para crear diseños de mini álbumes en pocos pasos.
Previsualización del corte automático en tiempo real con arrastre interactivo,
reutilización de portada para CD y exportación inmediata a PDF con selección de ruta.
"""
from typing import Optional, Dict
from pathlib import Path
import os
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QRadioButton, QButtonGroup, QFileDialog, QGroupBox, QLineEdit,
    QMessageBox, QFrame, QCheckBox, QSlider, QWidget, QSplitter, QSpinBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QRectF, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QImage, QPixmap, QFont, QPaintEvent,
    QMouseEvent, QPainterPath
)
from PIL import Image, ImageOps

from nfcito.models.project import Project, PieceDesign, CropConfig
from nfcito.models.profile import CaseProfile
from nfcito.storage.profile_repo import ProfileRepository
from nfcito.core.layout_engine import LayoutEngine
from nfcito.core.pdf_exporter import PDFExporter

class QuickCropPreviewWidget(QWidget):
    """Mini lienzo interactivo para previsualizar el corte y mover la imagen en tiempo real."""
    cropChanged = Signal()

    def __init__(self, title: str, is_circular: bool = False, parent=None):
        super().__init__(parent)
        self.title = title
        self.is_circular = is_circular
        self.image_path: Optional[str] = None
        self.crop = CropConfig()

        self._pixmap: Optional[QPixmap] = None
        self._cached_path: Optional[str] = None
        self._is_dragging: bool = False
        self._last_mouse: QPoint = QPoint()
        self.aspect_ratio: float = 1.0

        self.setMinimumSize(170, 170)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_aspect_ratio(self, ratio: float):
        self.aspect_ratio = max(0.2, min(5.0, ratio))
        self.update()

    def set_image(self, path: Optional[str]):
        self.image_path = path
        if path and os.path.exists(path):
            try:
                with Image.open(path) as raw:
                    img = ImageOps.exif_transpose(raw).convert("RGBA")
                    img.thumbnail((800, 800), Image.Resampling.BILINEAR)
                    data = img.tobytes("raw", "RGBA")
                    qimg = QImage(data, img.size[0], img.size[1], QImage.Format.Format_RGBA8888)
                    self._pixmap = QPixmap.fromImage(qimg)
            except Exception as e:
                print(f"Error en preview rápido: {e}")
                self._pixmap = None
        else:
            self._pixmap = None
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fondo
        painter.fillRect(self.rect(), QColor("#F1F5F9"))

        # Dimensiones de la caja de recorte según aspect ratio real
        pad = 20
        avail_w = self.width() - 2 * pad
        avail_h = self.height() - 2 * pad - 20
        if avail_w <= 10 or avail_h <= 10:
            return

        if self.is_circular:
            box_size = min(avail_w, avail_h)
            crop_w, crop_h = box_size, box_size
        else:
            aspect = getattr(self, "aspect_ratio", 1.0) or 1.0
            if avail_w / avail_h > aspect:
                crop_h = avail_h
                crop_w = avail_h * aspect
            else:
                crop_w = avail_w
                crop_h = avail_w / aspect

        cx = self.width() / 2.0
        cy = (self.height() - 15) / 2.0
        crop_rect = QRectF(cx - crop_w / 2.0, cy - crop_h / 2.0, crop_w, crop_h)

        # Título arriba
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#334155"))
        painter.drawText(0, 16, self.width(), 18, Qt.AlignmentFlag.AlignCenter, self.title)

        if self._pixmap and not self._pixmap.isNull():
            src_w = self._pixmap.width()
            src_h = self._pixmap.height()

            # Escala cover con zoom
            base_scale = max(crop_w / src_w, crop_h / src_h) * max(0.5, self.crop.zoom)
            img_w = src_w * base_scale
            img_h = src_h * base_scale

            max_shift_x = max(0.0, (img_w - crop_w) / 2.0)
            max_shift_y = max(0.0, (img_h - crop_h) / 2.0)

            base_x = crop_rect.x() + (crop_w - img_w) / 2.0
            base_y = crop_rect.y() + (crop_h - img_h) / 2.0

            pos_x = base_x + (self.crop.pan_x * max_shift_x)
            pos_y = base_y + (self.crop.pan_y * max_shift_y)
            img_rect = QRectF(pos_x, pos_y, img_w, img_h)

            # 1. Dibujar imagen exterior con opacidad reducida (para ver qué se recorta)
            painter.save()
            painter.setOpacity(0.3)
            painter.drawPixmap(img_rect.toRect(), self._pixmap)
            painter.restore()

            # 2. Dibujar interior recortado nítido
            painter.save()
            clip_path = QPainterPath()
            if self.is_circular:
                clip_path.addEllipse(crop_rect)
                # Agujero central
                hole_size = box_size * 0.25
                hole_rect = QRectF(cx - hole_size / 2.0, cy - hole_size / 2.0, hole_size, hole_size)
                hole_path = QPainterPath()
                hole_path.addEllipse(hole_rect)
                clip_path = clip_path.subtracted(hole_path)
            else:
                clip_path.addRect(crop_rect)

            painter.setClipPath(clip_path)
            painter.fillRect(crop_rect, QColor("#FFFFFF"))
            painter.drawPixmap(img_rect.toRect(), self._pixmap)
            painter.restore()

            # Guía de corte
            painter.setPen(QPen(QColor("#2563EB"), 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.is_circular:
                painter.drawEllipse(crop_rect)
                hole_size = box_size * 0.25
                painter.setPen(QPen(QColor("#DC2626"), 1.2))
                painter.drawEllipse(QRectF(cx - hole_size / 2.0, cy - hole_size / 2.0, hole_size, hole_size))
            else:
                painter.drawRect(crop_rect)

            # Indicador de arrastre en la base
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor("#64748B"))
            painter.drawText(0, self.height() - 14, self.width(), 14, Qt.AlignmentFlag.AlignCenter, "🖱️ Arrastre | ⬆⬇ Flechas o Rueda: Zoom")
        else:
            # Placeholder vacío
            painter.setPen(QPen(QColor("#CBD5E1"), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor("#FFFFFF"))
            if self.is_circular:
                painter.drawEllipse(crop_rect)
            else:
                painter.drawRect(crop_rect)
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(crop_rect, Qt.AlignmentFlag.AlignCenter, "Sin imagen")

    def zoom_in(self):
        if self._pixmap:
            self.crop.zoom = min(5.0, round(self.crop.zoom + 0.1, 2))
            self.update()
            self.cropChanged.emit()

    def zoom_out(self):
        if self._pixmap:
            self.crop.zoom = max(1.0, round(self.crop.zoom - 0.1, 2))
            self.update()
            self.cropChanged.emit()

    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            self._is_dragging = True
            self._last_mouse = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_dragging and self._pixmap:
            delta = event.pos() - self._last_mouse
            self._last_mouse = event.pos()

            sens = 0.015 / max(0.5, self.crop.zoom)
            self.crop.pan_x = max(-1.0, min(1.0, self.crop.pan_x + delta.x() * sens))
            self.crop.pan_y = max(-1.0, min(1.0, self.crop.pan_y + delta.y() * sens))

            self.update()
            self.cropChanged.emit()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def wheelEvent(self, event):
        if self._pixmap:
            delta = event.angleDelta().y()
            step = 0.08 if delta > 0 else -0.08
            self.crop.zoom = max(1.0, min(5.0, round(self.crop.zoom + step, 2)))
            self.update()
            self.cropChanged.emit()
            event.accept()

    def keyPressEvent(self, event):
        """Permite mover el zoom y el encuadre usando las flechas del teclado."""
        if not self._pixmap:
            super().keyPressEvent(event)
            return

        k = event.key()
        if k in (Qt.Key.Key_Up, Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            # Flecha Arriba o tecla + para acercar zoom
            self.zoom_in()
            event.accept()
        elif k in (Qt.Key.Key_Down, Qt.Key.Key_Minus):
            # Flecha Abajo o tecla - para alejar zoom
            self.zoom_out()
            event.accept()
        elif k == Qt.Key.Key_Left:
            self.crop.pan_x = max(-1.0, round(self.crop.pan_x - 0.04, 3))
            self.update()
            self.cropChanged.emit()
            event.accept()
        elif k == Qt.Key.Key_Right:
            self.crop.pan_x = min(1.0, round(self.crop.pan_x + 0.04, 3))
            self.update()
            self.cropChanged.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class QuickGeneratorDialog(QDialog):
    projectGenerated = Signal(Project)

    def __init__(self, repo: ProfileRepository, active_project: Optional[Project] = None, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.active_project = active_project
        self.setWindowTitle("Generador Rápido de Mini Álbum — Modo Automático")
        self.setMinimumSize(780, 500)

        self.main_image_path: Optional[str] = None
        self.back_image_path: Optional[str] = None
        self.cd_image_path: Optional[str] = None
        self.interior_image_path: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Encabezado explicativo
        header = QLabel(
            "<b>Modo Automático:</b> Cargue sus imágenes y previsualice en tiempo real la adecuación "
            "y el corte de la portada y el CD. Puede mover el encuadre directamente o exportar el PDF listo para imprimir de inmediato."
        )
        header.setWordWrap(True)
        header.setStyleSheet("color: #334155; font-size: 13px; background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 8px;")
        main_layout.addWidget(header)

        # Contenedor dividido en 2 columnas: izquierda opciones, derecha previsualización en tiempo real
        content_box = QHBoxLayout()

        # --- Columna Izquierda: Controles ---
        left_box = QVBoxLayout()
        left_box.setSpacing(10)

        # 1. Selección de Perfil
        grp_profile = QGroupBox("1. Seleccionar Perfil de Estuche")
        l_prof = QHBoxLayout(grp_profile)
        l_prof.addWidget(QLabel("Perfil:"))
        self.combo_profiles = QComboBox()
        for p in self.repo.get_all():
            self.combo_profiles.addItem(p.name, p.id)
        active_id = self.repo.get_active_profile_id()
        idx = self.combo_profiles.findData(active_id)
        if idx >= 0:
            self.combo_profiles.setCurrentIndex(idx)
        self.combo_profiles.currentIndexChanged.connect(self._on_profile_selection_changed)
        l_prof.addWidget(self.combo_profiles, 1)
        left_box.addWidget(grp_profile)

        # 2. Imagen Principal (Portada)
        grp_img = QGroupBox("2. Imagen Principal (Portada)")
        l_img = QVBoxLayout(grp_img)

        h_img_row = QHBoxLayout()
        self.lbl_main_img = QLabel("No se ha seleccionado ninguna foto.")
        self.lbl_main_img.setStyleSheet("color: #64748B;")
        self.btn_select_main = QPushButton("Seleccionar Foto de Portada...")
        self.btn_select_main.setObjectName("primaryButton")
        self.btn_select_main.clicked.connect(self._on_select_main_image)
        h_img_row.addWidget(self.lbl_main_img, 1)
        h_img_row.addWidget(self.btn_select_main)
        l_img.addLayout(h_img_row)
        left_box.addWidget(grp_img)

        # 3. Opciones de Distribución de Fotos
        grp_opts = QGroupBox("3. Distribución y Reutilización de Imágenes")
        l_opts = QVBoxLayout(grp_opts)

        self.btn_grp = QButtonGroup(self)

        self.rad_opt1 = QRadioButton("Reutilizar la foto de portada en el CD (recorte circular automático)")
        self.rad_opt1.setChecked(True)
        self.btn_grp.addButton(self.rad_opt1, 1)
        l_opts.addWidget(self.rad_opt1)

        self.rad_opt2 = QRadioButton("Elegir una foto independiente para el CD")
        self.btn_grp.addButton(self.rad_opt2, 2)
        l_opts.addWidget(self.rad_opt2)

        # Botón para foto de CD
        h_cd = QHBoxLayout()
        h_cd.setContentsMargins(20, 0, 0, 0)
        self.lbl_cd_img = QLabel("Misma que la portada")
        self.lbl_cd_img.setStyleSheet("color: #64748B; font-size: 11px;")
        self.btn_select_cd = QPushButton("Elegir foto de CD...")
        self.btn_select_cd.setEnabled(False)
        self.btn_select_cd.clicked.connect(self._on_select_cd_image)
        h_cd.addWidget(self.lbl_cd_img, 1)
        h_cd.addWidget(self.btn_select_cd)
        l_opts.addLayout(h_cd)

        self.rad_opt3 = QRadioButton("Portada solamente (CD sin foto)")
        self.btn_grp.addButton(self.rad_opt3, 3)
        l_opts.addWidget(self.rad_opt3)

        self.btn_grp.idToggled.connect(self._on_option_toggled)

        # Foto de contraportada
        h_back = QHBoxLayout()
        h_back.addWidget(QLabel("Contraportada:"))
        self.lbl_back_img = QLabel("Vacía / Para texto")
        self.lbl_back_img.setStyleSheet("color: #64748B; font-size: 11px;")
        self.btn_select_back = QPushButton("Elegir foto trasera...")
        self.btn_select_back.clicked.connect(self._on_select_back_image)
        h_back.addWidget(self.lbl_back_img, 1)
        h_back.addWidget(self.btn_select_back)
        l_opts.addLayout(h_back)

        # Foto de libreto / interior (opcional, encaja dentro del estuche)
        h_int = QHBoxLayout()
        h_int.addWidget(QLabel("Libreto interior:"))
        self.lbl_int_img = QLabel("Opcional / Vacía")
        self.lbl_int_img.setStyleSheet("color: #64748B; font-size: 11px;")
        self.btn_select_int = QPushButton("Elegir foto libreto...")
        self.btn_select_int.clicked.connect(self._on_select_int_image)
        h_int.addWidget(self.lbl_int_img, 1)
        h_int.addWidget(self.btn_select_int)
        l_opts.addLayout(h_int)

        left_box.addWidget(grp_opts)

        # 4. Datos del Álbum y NFC
        grp_nfc = QGroupBox("4. Datos del Álbum y Enlace NFC")
        l_nfc = QHBoxLayout(grp_nfc)
        l_nfc.addWidget(QLabel("Nombre:"))
        self.txt_album_name = QLineEdit()
        self.txt_album_name.setPlaceholderText("Ej. Mi Mini Álbum")
        self.txt_album_name.textChanged.connect(self._on_name_changed)
        l_nfc.addWidget(self.txt_album_name)

        l_nfc.addWidget(QLabel("Enlace NFC:"))
        self.txt_nfc_link = QLineEdit()
        self.txt_nfc_link.setPlaceholderText("https://spotify.com/...")
        l_nfc.addWidget(self.txt_nfc_link)
        left_box.addWidget(grp_nfc)

        content_box.addLayout(left_box, 3)

        # --- Columna Derecha: Previsualización en Tiempo Real con Arrastre y Flechas ---
        right_group = QGroupBox("Previsualización y Encuadre (Mueva con ratón o FLECHAS para Zoom)")
        right_layout = QVBoxLayout(right_group)

        self.prev_cover = QuickCropPreviewWidget("Portada Frontal (Corte Rectangular)", is_circular=False)
        self.prev_cd = QuickCropPreviewWidget("Etiqueta de Disco CD (Corte Circular)", is_circular=True)

        # Botones de zoom para portada (compatibles con flechas del teclado)
        row_z_cov = QHBoxLayout()
        row_z_cov.addWidget(QLabel("Zoom Portada:"))
        btn_zout_cov = QPushButton("🔍 − Alejar")
        btn_zout_cov.setToolTip("Alejar zoom (o use Flecha Abajo / Rueda)")
        btn_zout_cov.clicked.connect(self.prev_cover.zoom_out)
        btn_zin_cov = QPushButton("🔍 ＋ Acercar")
        btn_zin_cov.setToolTip("Acercar zoom (o use Flecha Arriba / Rueda)")
        btn_zin_cov.clicked.connect(self.prev_cover.zoom_in)
        row_z_cov.addWidget(btn_zout_cov)
        row_z_cov.addWidget(btn_zin_cov)

        # Botones de zoom para CD (compatibles con flechas del teclado)
        row_z_cd = QHBoxLayout()
        row_z_cd.addWidget(QLabel("Zoom CD:"))
        btn_zout_cd = QPushButton("🔍 − Alejar")
        btn_zout_cd.setToolTip("Alejar zoom (o use Flecha Abajo / Rueda)")
        btn_zout_cd.clicked.connect(self.prev_cd.zoom_out)
        btn_zin_cd = QPushButton("🔍 ＋ Acercar")
        btn_zin_cd.setToolTip("Acercar zoom (o use Flecha Arriba / Rueda)")
        btn_zin_cd.clicked.connect(self.prev_cd.zoom_in)
        row_z_cd.addWidget(btn_zout_cd)
        row_z_cd.addWidget(btn_zin_cd)

        right_layout.addWidget(self.prev_cover)
        right_layout.addLayout(row_z_cov)
        right_layout.addWidget(self.prev_cd)
        right_layout.addLayout(row_z_cd)
        content_box.addWidget(right_group, 2)

        main_layout.addLayout(content_box)

        # 5. Sección de Exportación Inmediata a PDF
        grp_export = QGroupBox("5. Paso Final: Exportar PDF de Precisión Listo para Imprimir")
        grp_export.setStyleSheet("font-weight: 600; color: #1E293B;")
        l_exp = QVBoxLayout(grp_export)

        # Configuración por PAQUETES (mini álbumes completos)
        h_pages = QHBoxLayout()
        lbl_pages = QLabel("<b>¿Cuántos paquetes de mini álbumes completos deseas producir?</b>")
        lbl_pages.setStyleSheet("font-size: 13px; color: #1E293B;")
        self.spin_packages = QSpinBox()
        self.spin_packages.setRange(1, 100)
        self.spin_packages.setValue(1)
        self.spin_packages.setSuffix(" paquete(s)")
        self.spin_packages.setStyleSheet("font-weight: bold; padding: 4px 8px; font-size: 13px;")
        self.spin_packages.valueChanged.connect(self._on_packages_changed)

        h_pages.addWidget(lbl_pages)
        h_pages.addWidget(self.spin_packages)
        h_pages.addStretch()
        l_exp.addLayout(h_pages)

        # Adecuación calculada
        self.lbl_pages_estimate = QLabel("")
        self.lbl_pages_estimate.setStyleSheet("color: #15803D; font-weight: 500; font-size: 11px; background-color: #F0FDF4; padding: 8px; border-radius: 4px; border: 1px solid #BBF7D0;")
        l_exp.addWidget(self.lbl_pages_estimate)
        self._on_packages_changed(1)
        self.lbl_pages_estimate.setStyleSheet("color: #15803D; font-weight: 500; font-size: 11px; background-color: #F0FDF4; padding: 8px; border-radius: 4px; border: 1px solid #BBF7D0;")
        l_exp.addWidget(self.lbl_pages_estimate)

        h_path = QHBoxLayout()
        h_path.addWidget(QLabel("Ruta de guardado del PDF:"))
        self.txt_pdf_dest = QLineEdit()
        default_dir = Path.home() / "Documents"
        default_pdf = str(default_dir / "NFCito_MiniAlbum_Imprimir.pdf")
        self.txt_pdf_dest.setText(default_pdf)
        self.btn_browse_dest = QPushButton("Examinar...")
        self.btn_browse_dest.clicked.connect(self._on_browse_pdf_dest)
        h_path.addWidget(self.txt_pdf_dest, 1)
        h_path.addWidget(self.btn_browse_dest)
        l_exp.addLayout(h_path)

        h_opts_exp = QHBoxLayout()
        self.chk_auto_open = QCheckBox("Abrir el PDF inmediatamente tras crearlo para imprimir")
        self.chk_auto_open.setChecked(True)
        h_opts_exp.addWidget(self.chk_auto_open)

        self.chk_include_calib = QCheckBox("Incluir página de calibración de 50 × 50 mm")
        self.chk_include_calib.setChecked(True)
        h_opts_exp.addWidget(self.chk_include_calib)
        l_exp.addLayout(h_opts_exp)

        main_layout.addWidget(grp_export)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

        # Botones de Acción de Pie (fijos para accesibilidad continua)
        btn_box = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_open_designer = QPushButton("🎨 Personalizar en Diseñador...")
        self.btn_open_designer.clicked.connect(self._on_open_in_designer)

        self.btn_export_direct = QPushButton("🚀 Generar y Exportar PDF Listo para Imprimir Ahora")
        self.btn_export_direct.setObjectName("primaryButton")
        self.btn_export_direct.setFixedHeight(40)
        self.btn_export_direct.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #2563EB; color: white; border-radius: 6px; padding: 8px 16px;")
        self.btn_export_direct.clicked.connect(self._on_export_direct_pdf)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addStretch()
        btn_box.addWidget(self.btn_open_designer)
        btn_box.addWidget(self.btn_export_direct)
        outer_layout.addLayout(btn_box)

    def _on_select_main_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Foto de Portada", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            self.main_image_path = f
            self.lbl_main_img.setText(os.path.basename(f))
            if not self.txt_album_name.text().strip():
                clean_name = os.path.splitext(os.path.basename(f))[0]
                self.txt_album_name.setText(clean_name)
                self._update_suggested_pdf_path(clean_name)

            self.prev_cover.set_image(f)
            if self.btn_grp.checkedId() == 1:
                self.prev_cd.set_image(f)

    def _on_select_cd_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Foto para CD", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            self.cd_image_path = f
            self.lbl_cd_img.setText(os.path.basename(f))
            self.prev_cd.set_image(f)

    def _on_select_back_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Foto para Contraportada", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            self.back_image_path = f
            self.lbl_back_img.setText(os.path.basename(f))

    def _on_select_int_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Foto para Libreto Interior", "", "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)")
        if f:
            self.interior_image_path = f
            self.lbl_int_img.setText(os.path.basename(f))

    def _on_option_toggled(self, opt_id: int, checked: bool):
        if checked:
            self.btn_select_cd.setEnabled(opt_id == 2)
            if opt_id == 1:
                self.lbl_cd_img.setText("Misma que la portada")
                self.prev_cd.set_image(self.main_image_path)
            elif opt_id == 2:
                self.prev_cd.set_image(self.cd_image_path or self.main_image_path)
            else:
                self.lbl_cd_img.setText("Desactivado")
                self.prev_cd.set_image(None)

    def _on_name_changed(self, text: str):
        if text.strip():
            self._update_suggested_pdf_path(text.strip())

    def _update_suggested_pdf_path(self, name: str):
        clean_name = name.replace(" ", "_")
        default_dir = Path.home() / "Documents"
        self.txt_pdf_dest.setText(str(default_dir / f"NFCito_{clean_name}_Imprimir.pdf"))

    def _on_browse_pdf_dest(self):
        suggested = self.txt_pdf_dest.text() or str(Path.home() / "Documents" / "NFCito_Imprimir.pdf")
        f, _ = QFileDialog.getSaveFileName(self, "Guardar PDF de Impresión", suggested, "Archivos PDF (*.pdf)")
        if f:
            self.txt_pdf_dest.setText(f)

    def _build_project(self) -> Project:
        profile_id = self.combo_profiles.currentData()
        name = self.txt_album_name.text().strip() or "Nuevo Mini Álbum"

        proj = Project(name=name, profile_id=profile_id)

        # Portada con los encuadres de la previsualización interactiva
        p_front = proj.get_piece("portada")
        p_front.image_path = self.main_image_path
        p_front.crop.pan_x = self.prev_cover.crop.pan_x
        p_front.crop.pan_y = self.prev_cover.crop.pan_y
        p_front.crop.zoom = self.prev_cover.crop.zoom
        p_front.enabled_for_print = True

        # CD con los encuadres de la previsualización interactiva
        opt = self.btn_grp.checkedId()
        p_cd = proj.get_piece("cd")
        if opt == 1:
            p_cd.image_path = self.main_image_path
            p_cd.crop.pan_x = self.prev_cd.crop.pan_x
            p_cd.crop.pan_y = self.prev_cd.crop.pan_y
            p_cd.crop.zoom = self.prev_cd.crop.zoom
            p_cd.enabled_for_print = True
        elif opt == 2:
            p_cd.image_path = self.cd_image_path or self.main_image_path
            p_cd.crop.pan_x = self.prev_cd.crop.pan_x
            p_cd.crop.pan_y = self.prev_cd.crop.pan_y
            p_cd.crop.zoom = self.prev_cd.crop.zoom
            p_cd.enabled_for_print = True
        else:
            p_cd.enabled_for_print = False

        # Contraportada
        p_back = proj.get_piece("contraportada")
        if self.back_image_path:
            p_back.image_path = self.back_image_path
            p_back.enabled_for_print = True
        else:
            p_back.enabled_for_print = True

        # Lomo
        p_spine = proj.get_piece("lomo")
        p_spine.enabled_for_print = True

        # Libreto interior (un poco más pequeño para encajar en el estuche)
        p_int = proj.get_piece("interior")
        if self.interior_image_path:
            p_int.image_path = self.interior_image_path
        p_int.enabled_for_print = True

        # Fondo de bandeja (interior de contraportada)
        p_inlay = proj.get_piece("interior_contraportada")
        p_inlay.enabled_for_print = True

        # Cantidad de mini álbumes calculada por paquetes
        qty = self.spin_packages.value()
        cd_on = (opt != 3)
        proj.print_layout.quantities = {
            "portada": qty,
            "contraportada": qty,
            "interior_contraportada": qty,
            "lomo": qty,
            "lomo_secundario": 0,
            "cd": qty if cd_on else 0,
            "interior": qty,
            "bandeja_continua": qty,
        }

        # NFC
        if self.txt_nfc_link.text().strip():
            proj.nfc.nfc_target_url = self.txt_nfc_link.text().strip()
            proj.nfc.album_title = name

        return proj

    def _on_profile_selection_changed(self):
        prof_id = self.combo_profiles.currentData()
        p = self.repo.get_by_id(prof_id)
        if p:
            aspect = p.portada.width_mm / max(1.0, p.portada.height_mm)
            self.prev_cover.set_aspect_ratio(aspect)
        self._on_packages_changed(self.spin_packages.value())

    def _on_packages_changed(self, pkgs: int):
        total_pieces = pkgs * 5
        # Capacidad de mínimo 5 paquetes por hoja A4
        pages_needed = max(1, (pkgs + 4) // 5)
        self.lbl_pages_estimate.setText(
            f"📦 <b>Adecuación calculada:</b> {pkgs} paquete(s) completos ({total_pieces} piezas en total). "
            f"La aplicación los acomodará automáticamente en <b>{pages_needed} hoja(s) de impresión</b> "
            f"(con mínimo 5 paquetes por hoja A4) a escala 100% física real sin encogimiento."
        )

    def _on_open_in_designer(self):
        if not self.main_image_path:
            QMessageBox.warning(self, "Foto Requerida", "Por favor seleccione una foto principal para la portada.")
            return

        proj = self._build_project()
        self.projectGenerated.emit(proj)
        self.accept()

    def _on_export_direct_pdf(self):
        if not self.main_image_path:
            QMessageBox.warning(self, "Foto Requerida", "Por favor seleccione una foto principal para la portada.")
            return

        dest_pdf = self.txt_pdf_dest.text().strip()
        if not dest_pdf:
            QMessageBox.warning(self, "Ruta requerida", "Por favor seleccione la ruta de guardado del PDF.")
            return

        proj = self._build_project()
        profile = self.repo.get_by_id(proj.profile_id)
        if not profile:
            profile = self.repo.get_all()[0]

        qty = self.spin_packages.value()
        opt = self.btn_grp.checkedId()
        cd_on = (opt != 3)
        quantities = {
            "portada": qty,
            "contraportada": qty,
            "lomo": qty,
            "cd": qty if cd_on else 0,
            "interior": qty,
            "bandeja_continua": qty,
        }

        try:
            # Calcular distribución multipágina conservando escala física 100%
            layout_res = LayoutEngine.compute_layout(
                project=proj,
                profile=profile,
                paper_size_name=profile.preferred_paper,
                quantities=quantities
            )

            # Generar PDF inmediatamente
            out_file = PDFExporter.export_pdf(
                output_path=dest_pdf,
                project=proj,
                profile=profile,
                layout_result=layout_res,
                include_calibration=self.chk_include_calib.isChecked(),
                show_cut_lines=True,
                dpi=300
            )

            # Abrir inmediatamente si la casilla está marcada
            if self.chk_auto_open.isChecked():
                os.startfile(out_file)

            n_pages = len(layout_res.pages)
            QMessageBox.information(
                self, "PDF Generado con Éxito",
                f"El archivo PDF listo para imprimir se generó en:\n{out_file}\n\n"
                f"• Hojas generadas: {n_pages} página(s).\n"
                f"• Mini álbumes producidos: {qty} juego(s) completos ({layout_res.total_items_placed} piezas).\n"
                f"• Rendimiento: 5 mini álbumes completos por hoja A4 a escala 100% real física.\n\n"
                "¡Abierto en su lector de PDF para imprimir a escala 100% real!"
            )

            self.projectGenerated.emit(proj)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el documento PDF:\n{e}")
