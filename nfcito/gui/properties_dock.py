"""
Panel de propiedades de piezas, encuadre, textos de contraportada y metadatos NFC.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox,
    QDoubleSpinBox, QSpinBox, QSlider, QComboBox, QLineEdit, QTextEdit,
    QGroupBox, QFileDialog, QScrollArea, QFrame, QMessageBox, QColorDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from nfcito.models.project import PieceDesign, Project, TextConfig
from nfcito.models.profile import CaseProfile

class PropertiesDock(QWidget):
    pieceUpdated = Signal()
    nfcUpdated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project: Optional[Project] = None
        self.profile: Optional[CaseProfile] = None
        self.piece: Optional[PieceDesign] = None
        self.piece_key: str = "portada"

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Scroll area para acomodar todos los controles
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(6, 6, 6, 6)

        # 1. Grupo: Estado y Dimensiones
        self.dim_group = QGroupBox("Dimensiones y Estado de Impresión")
        dim_layout = QVBoxLayout(self.dim_group)

        self.chk_print = QCheckBox("Imprimir esta pieza en la hoja")
        self.chk_print.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.chk_print.toggled.connect(self._on_chk_print_toggled)
        dim_layout.addWidget(self.chk_print)

        # Medidas en mm
        grid_dim = QHBoxLayout()
        self.lbl_dim_w = QLabel("Ancho (mm):")
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(5.0, 500.0)
        self.spin_w.setSingleStep(0.5)
        self.spin_w.valueChanged.connect(self._on_custom_w_changed)

        spin_dim_style = (
            "QDoubleSpinBox { border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 3px 6px; background-color: #FFFFFF; font-weight: 600; color: #1E293B; font-size: 13px; } "
            "QDoubleSpinBox:focus, QDoubleSpinBox QLineEdit:focus { border: 2.5px solid #2563EB; background-color: #F0F7FF; color: #1D4ED8; } "
            "QDoubleSpinBox:hover { border-color: #94A3B8; }"
        )
        self.spin_w.setStyleSheet(spin_dim_style)

        self.btn_lock_aspect = QPushButton("🔓")
        self.btn_lock_aspect.setCheckable(True)
        self.btn_lock_aspect.setFixedWidth(28)
        self.btn_lock_aspect.setStyleSheet(
            "QPushButton { border: 1.5px solid #CBD5E1; border-radius: 4px; background: #F8FAFC; font-size: 13px; } "
            "QPushButton:hover { background: #E2E8F0; } "
            "QPushButton:checked { background: #2563EB; color: white; border: 1.5px solid #1D4ED8; }"
        )
        self.btn_lock_aspect.setToolTip("Desbloqueado: Permite editar Alto o Ancho de forma totalmente independiente.\nBloqueado: Mantiene la proporción al modificar.")
        self.btn_lock_aspect.toggled.connect(self._on_lock_aspect_toggled)

        self.lbl_dim_h = QLabel("Alto (mm):")
        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(5.0, 500.0)
        self.spin_h.setSingleStep(0.5)
        self.spin_h.setStyleSheet(spin_dim_style)
        self.spin_h.valueChanged.connect(self._on_custom_h_changed)

        grid_dim.addWidget(self.lbl_dim_w)
        grid_dim.addWidget(self.spin_w)
        grid_dim.addWidget(self.btn_lock_aspect)
        grid_dim.addWidget(self.lbl_dim_h)
        grid_dim.addWidget(self.spin_h)
        dim_layout.addLayout(grid_dim)

        self.btn_reset_dim = QPushButton("Restablecer a medidas del perfil")
        self.btn_reset_dim.clicked.connect(self._on_reset_dim)
        dim_layout.addWidget(self.btn_reset_dim)

        self.lbl_interior_hint = QLabel("💡 Guía de la pieza seleccionada")
        self.lbl_interior_hint.setWordWrap(True)
        self.lbl_interior_hint.setStyleSheet("color: #2563EB; font-size: 11px; font-style: italic; background: #EFF6FF; padding: 4px; border-radius: 4px;")
        self.lbl_interior_hint.setVisible(False)
        dim_layout.addWidget(self.lbl_interior_hint)

        self.layout.addWidget(self.dim_group)

        # 2. Grupo: Gestión de Imagen
        self.img_group = QGroupBox("Imagen de la Pieza")
        img_layout = QVBoxLayout(self.img_group)

        self.lbl_img_path = QLabel("Sin imagen asignada")
        self.lbl_img_path.setWordWrap(True)
        self.lbl_img_path.setStyleSheet("color: #64748B; font-size: 11px;")
        img_layout.addWidget(self.lbl_img_path)

        btn_box = QHBoxLayout()
        self.btn_load_img = QPushButton("Cargar Imagen...")
        self.btn_load_img.setObjectName("primaryButton")
        self.btn_load_img.clicked.connect(self._on_load_image)

        self.btn_clear_img = QPushButton("Eliminar")
        self.btn_clear_img.clicked.connect(self._on_clear_image)

        btn_box.addWidget(self.btn_load_img)
        btn_box.addWidget(self.btn_clear_img)
        img_layout.addLayout(btn_box)

        self.layout.addWidget(self.img_group)

        # 3. Grupo: Encuadre y Recorte Proporcional
        self.crop_group = QGroupBox("Ajuste de Encuadre y Recorte")
        crop_layout = QVBoxLayout(self.crop_group)

        # Modo de ajuste
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Modo:"))
        self.combo_fit = QComboBox()
        self.combo_fit.addItem("Llenar sin deformar (Cover)", "cover")
        self.combo_fit.addItem("Encajar completo (Contain)", "contain")
        self.combo_fit.currentIndexChanged.connect(self._on_fit_mode_changed)
        mode_layout.addWidget(self.combo_fit)
        crop_layout.addLayout(mode_layout)

        # Zoom
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setRange(100, 400)
        self.slider_zoom.setValue(100)
        self.slider_zoom.valueChanged.connect(self._on_zoom_slider)
        self.lbl_zoom_val = QLabel("100%")
        zoom_layout.addWidget(self.slider_zoom)
        zoom_layout.addWidget(self.lbl_zoom_val)
        crop_layout.addLayout(zoom_layout)

        # Desplazamiento X / Y
        pan_x_layout = QHBoxLayout()
        pan_x_layout.addWidget(QLabel("Mover X:"))
        self.slider_pan_x = QSlider(Qt.Orientation.Horizontal)
        self.slider_pan_x.setRange(-100, 100)
        self.slider_pan_x.setValue(0)
        self.slider_pan_x.valueChanged.connect(self._on_pan_slider)
        pan_x_layout.addWidget(self.slider_pan_x)
        crop_layout.addLayout(pan_x_layout)

        pan_y_layout = QHBoxLayout()
        pan_y_layout.addWidget(QLabel("Mover Y:"))
        self.slider_pan_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_pan_y.setRange(-100, 100)
        self.slider_pan_y.setValue(0)
        self.slider_pan_y.valueChanged.connect(self._on_pan_slider)
        pan_y_layout.addWidget(self.slider_pan_y)
        crop_layout.addLayout(pan_y_layout)

        # Rotación
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Rotación:"))
        self.btn_rot_0 = QPushButton("0°")
        self.btn_rot_90 = QPushButton("90°")
        self.btn_rot_180 = QPushButton("180°")
        self.btn_rot_270 = QPushButton("270°")

        self.btn_rot_0.clicked.connect(lambda: self._set_rotation(0))
        self.btn_rot_90.clicked.connect(lambda: self._set_rotation(90))
        self.btn_rot_180.clicked.connect(lambda: self._set_rotation(180))
        self.btn_rot_270.clicked.connect(lambda: self._set_rotation(270))

        rot_layout.addWidget(self.btn_rot_0)
        rot_layout.addWidget(self.btn_rot_90)
        rot_layout.addWidget(self.btn_rot_180)
        rot_layout.addWidget(self.btn_rot_270)
        crop_layout.addLayout(rot_layout)

        self.btn_center_crop = QPushButton("Centrar Encuadre")
        self.btn_center_crop.clicked.connect(self._on_center_crop)
        crop_layout.addWidget(self.btn_center_crop)

        self.layout.addWidget(self.crop_group)

        # 4. Grupo: Editor de Texto Avanzado Tipo Word (Contraportada)
        self.text_group = QGroupBox("Editor de Texto Tipo Word — En Vivo (Contraportada)")
        text_layout = QVBoxLayout(self.text_group)
        text_layout.setSpacing(6)

        # Explicación en vivo
        lbl_word_hint = QLabel("✍️ Escribe libremente como en Word. Los cambios se ven inmediatamente en la pieza en tiempo real.")
        lbl_word_hint.setWordWrap(True)
        lbl_word_hint.setStyleSheet("color: #1E40AF; font-size: 11px; background-color: #EFF6FF; border: 1px solid #BFDBFE; padding: 5px; border-radius: 4px;")
        text_layout.addWidget(lbl_word_hint)

        # 4.1 Barra de herramientas estilo Word
        word_toolbar = QHBoxLayout()

        self.combo_font_family = QComboBox()
        self.combo_font_family.addItems([
            "Arial", "Calibri", "Segoe UI", "Impact", "Times New Roman",
            "Georgia", "Verdana", "Tahoma", "Bahnschrift", "Courier New"
        ])
        self.combo_font_family.currentIndexChanged.connect(self._on_font_settings_changed)
        word_toolbar.addWidget(self.combo_font_family, 2)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(4, 36)
        self.spin_font_size.setValue(8)
        self.spin_font_size.setSuffix(" pt")
        self.spin_font_size.valueChanged.connect(self._on_font_settings_changed)
        word_toolbar.addWidget(self.spin_font_size, 1)

        btn_biu_base = (
            "QPushButton { border: 1.5px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 12px; } "
            "QPushButton:hover { background: #F1F5F9; border-color: #94A3B8; } "
            "QPushButton:checked { background-color: #2563EB; color: #FFFFFF; border: 1.5px solid #1D4ED8; } "
        )

        # Botones B, I, U
        self.btn_bold = QPushButton("B")
        self.btn_bold.setCheckable(True)
        self.btn_bold.setFixedWidth(26)
        self.btn_bold.setStyleSheet(btn_biu_base + "QPushButton { font-weight: bold; }")
        self.btn_bold.toggled.connect(self._on_font_settings_changed)
        word_toolbar.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I")
        self.btn_italic.setCheckable(True)
        self.btn_italic.setFixedWidth(26)
        self.btn_italic.setStyleSheet(btn_biu_base + "QPushButton { font-style: italic; }")
        self.btn_italic.toggled.connect(self._on_font_settings_changed)
        word_toolbar.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("U")
        self.btn_underline.setCheckable(True)
        self.btn_underline.setFixedWidth(26)
        self.btn_underline.setStyleSheet(btn_biu_base + "QPushButton { text-decoration: underline; }")
        self.btn_underline.toggled.connect(self._on_font_settings_changed)
        word_toolbar.addWidget(self.btn_underline)

        text_layout.addLayout(word_toolbar)

        # 4.2 Alineación y Color estilo Word
        align_bar = QHBoxLayout()

        align_btn_style = (
            "QPushButton { border: 1.5px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; font-size: 13px; } "
            "QPushButton:hover { background: #F1F5F9; border-color: #94A3B8; } "
            "QPushButton:checked { background-color: #2563EB; color: #FFFFFF; border: 1.5px solid #1D4ED8; font-weight: bold; } "
        )

        self.btn_align_left = QPushButton("⯬")
        self.btn_align_left.setToolTip("Alinear a la izquierda")
        self.btn_align_left.setCheckable(True)
        self.btn_align_left.setChecked(True)
        self.btn_align_left.setFixedWidth(28)
        self.btn_align_left.setStyleSheet(align_btn_style)
        self.btn_align_left.clicked.connect(lambda: self._set_word_alignment("left"))
        align_bar.addWidget(self.btn_align_left)

        self.btn_align_center = QPushButton("▬")
        self.btn_align_center.setToolTip("Centrar")
        self.btn_align_center.setCheckable(True)
        self.btn_align_center.setFixedWidth(28)
        self.btn_align_center.setStyleSheet(align_btn_style)
        self.btn_align_center.clicked.connect(lambda: self._set_word_alignment("center"))
        align_bar.addWidget(self.btn_align_center)

        self.btn_align_right = QPushButton("⯮")
        self.btn_align_right.setToolTip("Alinear a la derecha")
        self.btn_align_right.setCheckable(True)
        self.btn_align_right.setFixedWidth(28)
        self.btn_align_right.setStyleSheet(align_btn_style)
        self.btn_align_right.clicked.connect(lambda: self._set_word_alignment("right"))
        align_bar.addWidget(self.btn_align_right)

        align_bar.addSpacing(6)

        # Botón Color de Texto
        self.btn_text_color = QPushButton("Color...")
        self.btn_text_color.setFixedHeight(26)
        self.btn_text_color.clicked.connect(self._on_pick_text_color)
        align_bar.addWidget(self.btn_text_color)

        self.btn_color_white = QPushButton("⚪")
        self.btn_color_white.setFixedWidth(24)
        self.btn_color_white.setToolTip("Blanco")
        self.btn_color_white.clicked.connect(lambda: self._set_text_color("#FFFFFF"))
        align_bar.addWidget(self.btn_color_white)

        self.btn_color_black = QPushButton("⚫")
        self.btn_color_black.setFixedWidth(24)
        self.btn_color_black.setToolTip("Negro")
        self.btn_color_black.clicked.connect(lambda: self._set_text_color("#000000"))
        align_bar.addWidget(self.btn_color_black)

        self.btn_color_gold = QPushButton("🟡")
        self.btn_color_gold.setFixedWidth(24)
        self.btn_color_gold.setToolTip("Dorado")
        self.btn_color_gold.clicked.connect(lambda: self._set_text_color("#D4AF37"))
        align_bar.addWidget(self.btn_color_gold)

        text_layout.addLayout(align_bar)

        # 4.3 Hoja de Edición en Tiempo Real (Documento Word)
        text_layout.addWidget(QLabel("Contenido del Álbum (Título, Canciones, Créditos):"))
        self.txt_word_doc = QTextEdit()
        self.txt_word_doc.setPlaceholderText(
            "# TÍTULO DEL ÁLBUM\n"
            "Artista / Año\n\n"
            "1. Primera Canción (3:45)\n"
            "2. Segunda Canción (4:10)\n"
            "3. Tercera Canción (2:55)\n\n"
            "(Tip: Las líneas con '#' al inicio se formatean automáticamente como Título)"
        )
        self.txt_word_doc.setFixedHeight(120)
        self.txt_word_doc.setStyleSheet(
            "QTextEdit { background-color: #FFFFFF; font-family: Segoe UI, sans-serif; font-size: 12px; "
            "border: 1.5px solid #CBD5E1; border-radius: 6px; padding: 6px; color: #0F172A; } "
            "QTextEdit:focus { border: 2.5px solid #2563EB; background-color: #F8FAFF; }"
        )
        self.txt_word_doc.textChanged.connect(self._on_word_doc_changed)
        text_layout.addWidget(self.txt_word_doc)

        # Campos colapsables o adicionales para formato
        more_fmt = QHBoxLayout()
        more_fmt.addWidget(QLabel("Fondo detrás de texto:"))
        self.combo_bg_style = QComboBox()
        self.combo_bg_style.addItem("Sin fondo (Transparente)", "none")
        self.combo_bg_style.addItem("Caja negra translúcida (55%)", "black_trans")
        self.combo_bg_style.addItem("Caja negra sólida (100%)", "black_solid")
        self.combo_bg_style.addItem("Caja blanca translúcida (65%)", "white_trans")
        self.combo_bg_style.addItem("Caja blanca sólida (100%)", "white_solid")
        self.combo_bg_style.currentIndexChanged.connect(self._on_bg_style_changed)
        more_fmt.addWidget(self.combo_bg_style)
        text_layout.addLayout(more_fmt)

        row_sp = QHBoxLayout()
        row_sp.addWidget(QLabel("Interlineado:"))
        self.spin_line_spacing = QDoubleSpinBox()
        self.spin_line_spacing.setRange(0.8, 2.5)
        self.spin_line_spacing.setSingleStep(0.1)
        self.spin_line_spacing.setValue(1.2)
        self.spin_line_spacing.valueChanged.connect(self._on_font_settings_changed)
        row_sp.addWidget(self.spin_line_spacing)

        row_sp.addWidget(QLabel("Margen (mm):"))
        self.spin_padding = QDoubleSpinBox()
        self.spin_padding.setRange(0.5, 10.0)
        self.spin_padding.setSingleStep(0.5)
        self.spin_padding.setValue(2.0)
        self.spin_padding.valueChanged.connect(self._on_font_settings_changed)
        row_sp.addWidget(self.spin_padding)
        text_layout.addLayout(row_sp)

        # Checkbox activar explícito (se activa solo al escribir)
        self.chk_text_enable = QCheckBox("Mostrar texto sobre la contraportada")
        self.chk_text_enable.setStyleSheet("font-weight: 600; color: #1E293B;")
        self.chk_text_enable.toggled.connect(self._on_text_toggled)
        text_layout.addWidget(self.chk_text_enable)

        # Campos legacy ocultos para compatibilidad interna
        self.txt_title = QLineEdit()
        self.txt_artist = QLineEdit()
        self.txt_tracks = QTextEdit()
        self.spin_title_size = QSpinBox()
        self.spin_title_size.setRange(6, 40)
        self.spin_title_size.setValue(10)
        self.combo_align_h = QComboBox()
        self.combo_align_v = QComboBox()

        # 4.3 Alineación Horizontal y Vertical
        align_row = QHBoxLayout()
        align_row.addWidget(QLabel("Alineación H:"))
        self.combo_align_h = QComboBox()
        self.combo_align_h.addItem("Izquierda", "left")
        self.combo_align_h.addItem("Centro", "center")
        self.combo_align_h.addItem("Derecha", "right")
        self.combo_align_h.currentIndexChanged.connect(self._on_font_settings_changed)
        align_row.addWidget(self.combo_align_h)

        align_row.addWidget(QLabel("Vertical:"))
        self.combo_align_v = QComboBox()
        self.combo_align_v.addItem("Arriba", "top")
        self.combo_align_v.addItem("Centro", "middle")
        self.combo_align_v.addItem("Abajo", "bottom")
        self.combo_align_v.currentIndexChanged.connect(self._on_font_settings_changed)
        align_row.addWidget(self.combo_align_v)
        text_layout.addLayout(align_row)

        # 4.4 Color del texto y paleta rápida
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Color Texto:"))
        self.btn_text_color = QPushButton("Color...")
        self.btn_text_color.clicked.connect(self._on_pick_text_color)
        color_row.addWidget(self.btn_text_color)

        # Paleta rápida
        self.btn_color_white = QPushButton("⚪")
        self.btn_color_white.setToolTip("Blanco")
        self.btn_color_white.setFixedWidth(26)
        self.btn_color_white.clicked.connect(lambda: self._set_text_color("#FFFFFF"))
        color_row.addWidget(self.btn_color_white)

        self.btn_color_black = QPushButton("⚫")
        self.btn_color_black.setToolTip("Negro")
        self.btn_color_black.setFixedWidth(26)
        self.btn_color_black.clicked.connect(lambda: self._set_text_color("#000000"))
        color_row.addWidget(self.btn_color_black)

        self.btn_color_gold = QPushButton("🟡")
        self.btn_color_gold.setToolTip("Dorado")
        self.btn_color_gold.setFixedWidth(26)
        self.btn_color_gold.clicked.connect(lambda: self._set_text_color("#D4AF37"))
        color_row.addWidget(self.btn_color_gold)

        text_layout.addLayout(color_row)

        # 4.5 Caja de fondo detrás del texto (para legibilidad sobre fotos)
        bg_row = QHBoxLayout()
        bg_row.addWidget(QLabel("Fondo Texto:"))
        self.combo_bg_style = QComboBox()
        self.combo_bg_style.addItem("Sin fondo (Transparente)", "none")
        self.combo_bg_style.addItem("Caja negra translúcida (55%)", "black_trans")
        self.combo_bg_style.addItem("Caja negra sólida (100%)", "black_solid")
        self.combo_bg_style.addItem("Caja blanca translúcida (65%)", "white_trans")
        self.combo_bg_style.addItem("Caja blanca sólida (100%)", "white_solid")
        self.combo_bg_style.currentIndexChanged.connect(self._on_bg_style_changed)
        bg_row.addWidget(self.combo_bg_style)
        text_layout.addLayout(bg_row)

        # 4.6 Interlineado y Margen interior
        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("Interlineado:"))
        self.spin_line_spacing = QDoubleSpinBox()
        self.spin_line_spacing.setRange(0.8, 2.5)
        self.spin_line_spacing.setSingleStep(0.1)
        self.spin_line_spacing.setValue(1.2)
        self.spin_line_spacing.valueChanged.connect(self._on_font_settings_changed)
        spacing_row.addWidget(self.spin_line_spacing)

        spacing_row.addWidget(QLabel("Margen (mm):"))
        self.spin_padding = QDoubleSpinBox()
        self.spin_padding.setRange(1.0, 10.0)
        self.spin_padding.setSingleStep(0.5)
        self.spin_padding.setValue(2.0)
        self.spin_padding.valueChanged.connect(self._on_font_settings_changed)
        spacing_row.addWidget(self.spin_padding)
        text_layout.addLayout(spacing_row)

        self.layout.addWidget(self.text_group)

        # 5. Grupo: Metadatos NFC
        self.nfc_group = QGroupBox("Datos NFC (Enlace y Canción)")
        nfc_layout = QVBoxLayout(self.nfc_group)

        nfc_layout.addWidget(QLabel("URL de destino NFC (Spotify, Apple, YouTube, etc.):"))
        self.txt_nfc_url = QLineEdit()
        self.txt_nfc_url.setPlaceholderText("https://open.spotify.com/album/...")
        self.txt_nfc_url.textChanged.connect(self._on_nfc_field_changed)
        nfc_layout.addWidget(self.txt_nfc_url)

        nfc_layout.addWidget(QLabel("Tipo de Etiqueta NFC:"))
        self.combo_nfc_type = QComboBox()
        self.combo_nfc_type.addItems(["NTAG213 (144 bytes)", "NTAG215 (504 bytes)", "NTAG216 (888 bytes)"])
        self.combo_nfc_type.currentIndexChanged.connect(self._on_nfc_field_changed)
        nfc_layout.addWidget(self.combo_nfc_type)

        self.layout.addWidget(self.nfc_group)

        self.layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def set_data(self, project: Optional[Project], profile: Optional[CaseProfile], piece_key: str = "portada"):
        self.project = project
        self.profile = profile
        self.piece_key = piece_key
        self.piece = project.get_piece(piece_key) if project else None

        self._update_ui_state()

    def update_crop_sliders(self, zoom: float, pan_x: float, pan_y: float):
        """Sincroniza los sliders con el lienzo interactivo."""
        self.slider_zoom.blockSignals(True)
        self.slider_pan_x.blockSignals(True)
        self.slider_pan_y.blockSignals(True)

        self.slider_zoom.setValue(int(round(zoom * 100)))
        self.lbl_zoom_val.setText(f"{int(round(zoom * 100))}%")
        self.slider_pan_x.setValue(int(round(pan_x * 100)))
        self.slider_pan_y.setValue(int(round(pan_y * 100)))

        self.slider_zoom.blockSignals(False)
        self.slider_pan_x.blockSignals(False)
        self.slider_pan_y.blockSignals(False)

    def _update_ui_state(self):
        if not self.piece or not self.profile:
            self.setEnabled(False)
            return

        self.setEnabled(True)

        # Mostrar/Ocultar paneles y mensajes según la pieza
        self.text_group.setVisible(self.piece_key == "contraportada")
        if self.piece_key == "interior":
            self.lbl_interior_hint.setText("💡 El libreto interior es un poco más pequeño (~1.5 mm menos que la portada) para encajar sin doblarse en las pestañas del estuche.")
            self.lbl_interior_hint.setVisible(True)
        elif self.piece_key == "interior_contraportada":
            self.lbl_interior_hint.setText("💡 Fondo de Bandeja (Interior Contraportada): Se coloca debajo del CD transparente en el interior del estuche. Tiene las mismas medidas de la contraportada.")
            self.lbl_interior_hint.setVisible(True)
        elif self.piece_key == "lomo_secundario":
            self.lbl_interior_hint.setText("💡 Lomo Secundario (Borde Opcional): Útil para estuches con borde derecho o solapa adicional. Actívelo si su modelo de estuche lo requiere.")
            self.lbl_interior_hint.setVisible(True)
        else:
            self.lbl_interior_hint.setVisible(False)

        dim = self.profile.get_piece_dimension(self.piece_key)
        is_circ = dim.is_circular if dim else False

        # Configurar spinboxes de medidas
        self.spin_w.blockSignals(True)
        self.spin_h.blockSignals(True)
        if is_circ:
            self.lbl_dim_w.setText("Diámetro (mm):")
            self.lbl_dim_h.setVisible(False)
            self.spin_h.setVisible(False)
            val = self.piece.custom_width_mm or self.profile.cd.outer_diameter_mm
            self.spin_w.setValue(val)
        else:
            self.lbl_dim_w.setText("Ancho (mm):")
            self.lbl_dim_h.setVisible(True)
            self.spin_h.setVisible(True)
            if self.piece_key == "interior" and not self.piece.custom_width_mm:
                w_val = dim.width_mm if dim else max(5.0, self.profile.portada.width_mm - 1.5)
                h_val = dim.height_mm if dim else max(5.0, self.profile.portada.height_mm - 1.5)
                if w_val >= self.profile.portada.width_mm:
                    w_val = max(5.0, round(self.profile.portada.width_mm - 1.5, 1))
                if h_val >= self.profile.portada.height_mm:
                    h_val = max(5.0, round(self.profile.portada.height_mm - 1.5, 1))
            else:
                w_val = self.piece.custom_width_mm or (dim.width_mm if dim else 48.0)
                h_val = self.piece.custom_height_mm or (dim.height_mm if dim else 48.0)
            self.spin_w.setValue(w_val)
            self.spin_h.setValue(h_val)
        self.spin_w.blockSignals(False)
        self.spin_h.blockSignals(False)

        # Checkbox imprimir
        self.chk_print.blockSignals(True)
        self.chk_print.setChecked(self.piece.enabled_for_print)
        self.chk_print.blockSignals(False)

        # Imagen
        if self.piece.image_path:
            import os
            self.lbl_img_path.setText(f"Archivo: {os.path.basename(self.piece.image_path)}")
            self.btn_clear_img.setEnabled(True)
            self.crop_group.setEnabled(True)
        else:
            self.lbl_img_path.setText("Sin imagen asignada")
            self.btn_clear_img.setEnabled(False)
            self.crop_group.setEnabled(False)

        # Controles de encuadre
        self.update_crop_sliders(self.piece.crop.zoom, self.piece.crop.pan_x, self.piece.crop.pan_y)

        idx = self.combo_fit.findData(self.piece.crop.fit_mode)
        if idx >= 0:
            self.combo_fit.setCurrentIndex(idx)

        # Textos de contraportada
        if self.piece_key == "contraportada":
            t_cfg = self.piece.text_overlay
            self.chk_text_enable.blockSignals(True)
            self.chk_text_enable.setChecked(t_cfg.enabled)
            self.chk_text_enable.blockSignals(False)

            self.txt_title.blockSignals(True)
            self.txt_title.setText(t_cfg.title)
            self.txt_title.blockSignals(False)

            self.txt_artist.blockSignals(True)
            self.txt_artist.setText(t_cfg.artist)
            self.txt_artist.blockSignals(False)

            self.txt_tracks.blockSignals(True)
            self.txt_tracks.setPlainText(t_cfg.tracks)
            self.txt_tracks.blockSignals(False)

            self.spin_font_size.blockSignals(True)
            self.spin_font_size.setValue(t_cfg.font_size)
            self.spin_font_size.blockSignals(False)

            self.spin_title_size.blockSignals(True)
            self.spin_title_size.setValue(t_cfg.title_font_size)
            self.spin_title_size.blockSignals(False)

            idx_f = self.combo_font_family.findText(t_cfg.font_family)
            if idx_f >= 0:
                self.combo_font_family.blockSignals(True)
                self.combo_font_family.setCurrentIndex(idx_f)
                self.combo_font_family.blockSignals(False)

            self.btn_bold.blockSignals(True)
            self.btn_bold.setChecked(t_cfg.is_bold)
            self.btn_bold.blockSignals(False)

            self.btn_italic.blockSignals(True)
            self.btn_italic.setChecked(t_cfg.is_italic)
            self.btn_italic.blockSignals(False)

            idx_ah = self.combo_align_h.findData(t_cfg.alignment)
            if idx_ah >= 0:
                self.combo_align_h.blockSignals(True)
                self.combo_align_h.setCurrentIndex(idx_ah)
                self.combo_align_h.blockSignals(False)

            idx_av = self.combo_align_v.findData(t_cfg.vertical_align)
            if idx_av >= 0:
                self.combo_align_v.blockSignals(True)
                self.combo_align_v.setCurrentIndex(idx_av)
                self.combo_align_v.blockSignals(False)

            self.spin_line_spacing.blockSignals(True)
            self.spin_line_spacing.setValue(t_cfg.line_spacing)
            self.spin_line_spacing.blockSignals(False)

            self.spin_padding.blockSignals(True)
            self.spin_padding.setValue(t_cfg.padding_mm)
            self.spin_padding.blockSignals(False)

            self.btn_text_color.setStyleSheet(f"background-color: {t_cfg.text_color}; color: {'#FFF' if t_cfg.text_color.lower() in ('#000000', '#112233', '#1e293b') else '#000'}; font-weight: bold;")

            # Fondo estilo
            self.combo_bg_style.blockSignals(True)
            if not t_cfg.bg_color or t_cfg.bg_opacity <= 0.05:
                self.combo_bg_style.setCurrentIndex(0)
            elif t_cfg.bg_color.lower() == "#000000" and t_cfg.bg_opacity < 0.9:
                self.combo_bg_style.setCurrentIndex(1)
            elif t_cfg.bg_color.lower() == "#000000":
                self.combo_bg_style.setCurrentIndex(2)
            elif t_cfg.bg_color.lower() == "#ffffff" and t_cfg.bg_opacity < 0.9:
                self.combo_bg_style.setCurrentIndex(3)
            elif t_cfg.bg_color.lower() == "#ffffff":
                self.combo_bg_style.setCurrentIndex(4)
            self.combo_bg_style.blockSignals(False)

            # Sincronizar documento Word en vivo
            self.txt_word_doc.blockSignals(True)
            if t_cfg.full_body_text:
                self.txt_word_doc.setPlainText(t_cfg.full_body_text)
            elif t_cfg.title or t_cfg.tracks:
                assembled = []
                if t_cfg.title: assembled.append(f"# {t_cfg.title}")
                if t_cfg.artist: assembled.append(t_cfg.artist)
                if t_cfg.tracks: assembled.append(t_cfg.tracks)
                self.txt_word_doc.setPlainText("\n".join(assembled))
            else:
                self.txt_word_doc.setPlainText("")
            self.txt_word_doc.blockSignals(False)

            self.btn_align_left.setChecked(t_cfg.alignment == "left")
            self.btn_align_center.setChecked(t_cfg.alignment == "center")
            self.btn_align_right.setChecked(t_cfg.alignment == "right")
            self.btn_underline.setChecked(t_cfg.is_underline)

        # Datos NFC
        if self.project:
            self.txt_nfc_url.blockSignals(True)
            self.txt_nfc_url.setText(self.project.nfc.nfc_target_url)
            self.txt_nfc_url.blockSignals(False)

    def _on_chk_print_toggled(self, checked: bool):
        if self.piece:
            self.piece.enabled_for_print = checked
            self.pieceUpdated.emit()

    def _on_lock_aspect_toggled(self, checked: bool):
        if checked:
            self.btn_lock_aspect.setText("🔒")
            self.btn_lock_aspect.setToolTip("Bloqueado: La proporción se mantiene al modificar ancho o alto.")
        else:
            self.btn_lock_aspect.setText("🔓")
            self.btn_lock_aspect.setToolTip("Desbloqueado: Permite editar Alto o Ancho de forma totalmente independiente.")

    def _on_custom_w_changed(self, val: float):
        if not self.piece or not self.profile:
            return
        dim = self.profile.get_piece_dimension(self.piece_key)
        if dim and dim.is_circular:
            self.piece.custom_width_mm = val
            self.piece.custom_height_mm = val
        else:
            if self.btn_lock_aspect.isChecked():
                old_w = self.piece.custom_width_mm or (dim.width_mm if dim else 48.0)
                old_h = self.piece.custom_height_mm or (dim.height_mm if dim else 48.0)
                if old_w > 0:
                    ratio = old_h / old_w
                    new_h = round(val * ratio, 1)
                    self.piece.custom_height_mm = new_h
                    self.spin_h.blockSignals(True)
                    self.spin_h.setValue(new_h)
                    self.spin_h.blockSignals(False)
            self.piece.custom_width_mm = val
        self.pieceUpdated.emit()

    def _on_custom_h_changed(self, val: float):
        if not self.piece or not self.profile:
            return
        dim = self.profile.get_piece_dimension(self.piece_key)
        if dim and dim.is_circular:
            self.piece.custom_width_mm = val
            self.piece.custom_height_mm = val
        else:
            if self.btn_lock_aspect.isChecked():
                old_w = self.piece.custom_width_mm or (dim.width_mm if dim else 48.0)
                old_h = self.piece.custom_height_mm or (dim.height_mm if dim else 48.0)
                if old_h > 0:
                    ratio = old_w / old_h
                    new_w = round(val * ratio, 1)
                    self.piece.custom_width_mm = new_w
                    self.spin_w.blockSignals(True)
                    self.spin_w.setValue(new_w)
                    self.spin_w.blockSignals(False)
            self.piece.custom_height_mm = val
        self.pieceUpdated.emit()

    def _set_word_alignment(self, align: str):
        if self.piece and self.piece_key == "contraportada":
            self.btn_align_left.setChecked(align == "left")
            self.btn_align_center.setChecked(align == "center")
            self.btn_align_right.setChecked(align == "right")
            self.piece.text_overlay.alignment = align
            self.piece.text_overlay.enabled = True
            self.chk_text_enable.blockSignals(True)
            self.chk_text_enable.setChecked(True)
            self.chk_text_enable.blockSignals(False)
            self.pieceUpdated.emit()

    def _on_word_doc_changed(self):
        if self.piece and self.piece_key == "contraportada":
            doc_text = self.txt_word_doc.toPlainText()
            self.piece.text_overlay.full_body_text = doc_text
            if doc_text.strip():
                self.piece.text_overlay.enabled = True
                self.chk_text_enable.blockSignals(True)
                self.chk_text_enable.setChecked(True)
                self.chk_text_enable.blockSignals(False)
            self.pieceUpdated.emit()

    def _on_reset_dim(self):
        if self.piece:
            self.piece.custom_width_mm = None
            self.piece.custom_height_mm = None
            self._update_ui_state()
            self.pieceUpdated.emit()

    def _on_load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Imagen para " + self.piece_key.capitalize(),
            "",
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            self.set_image_file(file_path)

    def set_image_file(self, file_path: str):
        if self.piece:
            self.piece.image_path = file_path
            # Reset crop
            self.piece.crop.zoom = 1.0
            self.piece.crop.pan_x = 0.0
            self.piece.crop.pan_y = 0.0
            self._update_ui_state()
            self.pieceUpdated.emit()

    def _on_clear_image(self):
        if self.piece:
            self.piece.image_path = None
            self._update_ui_state()
            self.pieceUpdated.emit()

    def _on_fit_mode_changed(self):
        if self.piece:
            mode = self.combo_fit.currentData()
            self.piece.crop.fit_mode = mode
            self.pieceUpdated.emit()

    def _on_zoom_slider(self, val: int):
        if self.piece:
            zoom = val / 100.0
            self.piece.crop.zoom = zoom
            self.lbl_zoom_val.setText(f"{val}%")
            self.pieceUpdated.emit()

    def _on_pan_slider(self):
        if self.piece:
            self.piece.crop.pan_x = self.slider_pan_x.value() / 100.0
            self.piece.crop.pan_y = self.slider_pan_y.value() / 100.0
            self.pieceUpdated.emit()

    def _set_rotation(self, deg: int):
        if self.piece:
            self.piece.crop.rotation = deg
            self.pieceUpdated.emit()

    def _on_center_crop(self):
        if self.piece:
            self.piece.crop.zoom = 1.0
            self.piece.crop.pan_x = 0.0
            self.piece.crop.pan_y = 0.0
            self.update_crop_sliders(1.0, 0.0, 0.0)
            self.pieceUpdated.emit()

    def _on_text_toggled(self, checked: bool):
        if self.piece:
            self.piece.text_overlay.enabled = checked
            self.pieceUpdated.emit()

    def _on_text_content_changed(self):
        if self.piece and self.piece_key == "contraportada":
            self.piece.text_overlay.title = self.txt_title.text()
            self.piece.text_overlay.artist = self.txt_artist.text()
            self.piece.text_overlay.tracks = self.txt_tracks.toPlainText()
            self.piece.text_overlay.font_size = self.spin_font_size.value()
            self.pieceUpdated.emit()

    def _on_font_settings_changed(self):
        if self.piece and self.piece_key == "contraportada":
            t = self.piece.text_overlay
            t.font_family = self.combo_font_family.currentText()
            t.is_bold = self.btn_bold.isChecked()
            t.is_italic = self.btn_italic.isChecked()
            t.is_underline = self.btn_underline.isChecked()
            t.title_font_size = self.spin_title_size.value()
            t.font_size = self.spin_font_size.value()
            t.alignment = self.combo_align_h.currentData()
            t.vertical_align = self.combo_align_v.currentData()
            t.line_spacing = self.spin_line_spacing.value()
            t.padding_mm = self.spin_padding.value()
            self.pieceUpdated.emit()

    def _set_text_color(self, hex_color: str):
        if self.piece and self.piece_key == "contraportada":
            self.piece.text_overlay.text_color = hex_color
            self.btn_text_color.setStyleSheet(f"background-color: {hex_color}; color: {'#FFF' if hex_color.lower() in ('#000000', '#112233', '#1e293b') else '#000'}; font-weight: bold;")
            self.pieceUpdated.emit()

    def _on_pick_text_color(self):
        color = QColorDialog.getColor(QColor(self.piece.text_overlay.text_color if self.piece else "#000000"), self, "Seleccionar Color de Texto")
        if color.isValid() and self.piece:
            self._set_text_color(color.name())

    def _on_bg_style_changed(self):
        if self.piece and self.piece_key == "contraportada":
            t = self.piece.text_overlay
            style = self.combo_bg_style.currentData()
            if style == "none":
                t.bg_color = None
                t.bg_opacity = 0.0
            elif style == "black_trans":
                t.bg_color = "#000000"
                t.bg_opacity = 0.55
            elif style == "black_solid":
                t.bg_color = "#000000"
                t.bg_opacity = 1.0
            elif style == "white_trans":
                t.bg_color = "#FFFFFF"
                t.bg_opacity = 0.65
            elif style == "white_solid":
                t.bg_color = "#FFFFFF"
                t.bg_opacity = 1.0
            self.pieceUpdated.emit()

    def _on_nfc_field_changed(self):
        if self.project:
            self.project.nfc.nfc_target_url = self.txt_nfc_url.text()
            self.project.nfc.nfc_tag_type = self.combo_nfc_type.currentText().split()[0]
            self.nfcUpdated.emit()
