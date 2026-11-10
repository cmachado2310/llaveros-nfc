"""
Administrador de perfiles de medidas para estuches mini CD de llaveros.
Permite crear, editar, duplicar, renombrar y configurar dimensiones físicas precisas.
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QLineEdit, QTextEdit, QDoubleSpinBox, QCheckBox,
    QGroupBox, QComboBox, QMessageBox, QInputDialog, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, Signal

from nfcito.models.profile import CaseProfile
from nfcito.storage.profile_repo import ProfileRepository

class ProfileManagerDialog(QDialog):
    profileChanged = Signal(str)  # profile_id activo

    def __init__(self, repo: ProfileRepository, active_id: str, parent=None):
        super().__init__(parent)
        self.repo = repo
        self.active_id = active_id
        self.current_profile: Optional[CaseProfile] = None

        self.setWindowTitle("Administrador de Perfiles de Medidas — NFCito Studio")
        self.setMinimumSize(750, 520)
        self._init_ui()
        self._load_profiles()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # Panel izquierdo: Lista de perfiles y botones de gestión
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Perfiles de Estuches:"))

        self.list_profiles = QListWidget()
        self.list_profiles.currentRowChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.list_profiles)

        btn_row1 = QHBoxLayout()
        self.btn_new = QPushButton("Nuevo...")
        self.btn_new.clicked.connect(self._on_new_profile)
        self.btn_dup = QPushButton("Duplicar...")
        self.btn_dup.clicked.connect(self._on_duplicate_profile)
        btn_row1.addWidget(self.btn_new)
        btn_row1.addWidget(self.btn_dup)
        left_layout.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self.btn_rename = QPushButton("Renombrar...")
        self.btn_rename.clicked.connect(self._on_rename_profile)
        self.btn_del = QPushButton("Eliminar")
        self.btn_del.clicked.connect(self._on_delete_profile)
        btn_row2.addWidget(self.btn_rename)
        btn_row2.addWidget(self.btn_del)
        left_layout.addLayout(btn_row2)

        self.btn_set_active = QPushButton("Establecer como Perfil Activo")
        self.btn_set_active.setObjectName("primaryButton")
        self.btn_set_active.clicked.connect(self._on_set_active)
        left_layout.addWidget(self.btn_set_active)

        main_layout.addLayout(left_layout, 1)

        # Panel derecho: Editor de medidas del perfil seleccionado
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Aviso de medidas provisionales
        self.lbl_provisional_badge = QLabel("⚠️ Medidas provisionales de fábrica. Mida su estuche físico para calibrar.")
        self.lbl_provisional_badge.setStyleSheet(
            "background-color: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; "
            "border-radius: 6px; padding: 6px; font-weight: 600;"
        )
        right_layout.addWidget(self.lbl_provisional_badge)

        # 1. Dimensiones exteriores del estuche (solo referencia)
        grp_ext = QGroupBox("Dimensiones Exteriores del Estuche Físico (Referencia)")
        l_ext = QHBoxLayout(grp_ext)
        l_ext.addWidget(QLabel("Ancho (mm):"))
        self.spin_ext_w = QDoubleSpinBox()
        self.spin_ext_w.setRange(10.0, 300.0)
        l_ext.addWidget(self.spin_ext_w)

        l_ext.addWidget(QLabel("Alto (mm):"))
        self.spin_ext_h = QDoubleSpinBox()
        self.spin_ext_h.setRange(10.0, 300.0)
        l_ext.addWidget(self.spin_ext_h)

        l_ext.addWidget(QLabel("Grosor (mm):"))
        self.spin_ext_d = QDoubleSpinBox()
        self.spin_ext_d.setRange(1.0, 50.0)
        l_ext.addWidget(self.spin_ext_d)
        right_layout.addWidget(grp_ext)

        # 2. Medidas de piezas individuales para imprimir
        grp_pieces = QGroupBox("Dimensiones de Impresión de Cada Pieza (Milímetros)")
        l_pieces = QVBoxLayout(grp_pieces)

        # Portada
        row_p = QHBoxLayout()
        self.chk_portada = QCheckBox("Portada:")
        self.chk_portada.setChecked(True)
        self.spin_portada_w = QDoubleSpinBox()
        self.spin_portada_w.setRange(5.0, 300.0)
        self.spin_portada_h = QDoubleSpinBox()
        self.spin_portada_h.setRange(5.0, 300.0)
        row_p.addWidget(self.chk_portada)
        row_p.addWidget(QLabel("Ancho:"))
        row_p.addWidget(self.spin_portada_w)
        row_p.addWidget(QLabel("Alto:"))
        row_p.addWidget(self.spin_portada_h)
        l_pieces.addLayout(row_p)

        # Contraportada
        row_c = QHBoxLayout()
        self.chk_contra = QCheckBox("Contraportada:")
        self.chk_contra.setChecked(True)
        self.spin_contra_w = QDoubleSpinBox()
        self.spin_contra_w.setRange(5.0, 300.0)
        self.spin_contra_h = QDoubleSpinBox()
        self.spin_contra_h.setRange(5.0, 300.0)
        row_c.addWidget(self.chk_contra)
        row_c.addWidget(QLabel("Ancho:"))
        row_c.addWidget(self.spin_contra_w)
        row_c.addWidget(QLabel("Alto:"))
        row_c.addWidget(self.spin_contra_h)
        l_pieces.addLayout(row_c)

        # Fondo bandeja (interior contraportada)
        row_ic = QHBoxLayout()
        self.chk_interior_contra = QCheckBox("Fondo bandeja (Interior contraportada):")
        self.chk_interior_contra.setChecked(True)
        self.spin_interior_contra_w = QDoubleSpinBox()
        self.spin_interior_contra_w.setRange(5.0, 300.0)
        self.spin_interior_contra_h = QDoubleSpinBox()
        self.spin_interior_contra_h.setRange(5.0, 300.0)
        row_ic.addWidget(self.chk_interior_contra)
        row_ic.addWidget(QLabel("Ancho:"))
        row_ic.addWidget(self.spin_interior_contra_w)
        row_ic.addWidget(QLabel("Alto:"))
        row_ic.addWidget(self.spin_interior_contra_h)
        l_pieces.addLayout(row_ic)

        # Lomo
        row_l = QHBoxLayout()
        self.chk_lomo = QCheckBox("Lomo principal / Lateral:")
        self.chk_lomo.setChecked(True)
        self.spin_lomo_w = QDoubleSpinBox()
        self.spin_lomo_w.setRange(1.0, 50.0)
        self.spin_lomo_h = QDoubleSpinBox()
        self.spin_lomo_h.setRange(5.0, 300.0)
        row_l.addWidget(self.chk_lomo)
        row_l.addWidget(QLabel("Ancho:"))
        row_l.addWidget(self.spin_lomo_w)
        row_l.addWidget(QLabel("Alto:"))
        row_l.addWidget(self.spin_lomo_h)
        l_pieces.addLayout(row_l)

        # Lomo secundario (opcional)
        row_l2 = QHBoxLayout()
        self.chk_lomo_sec = QCheckBox("Lomo secundario / Borde opcional:")
        self.chk_lomo_sec.setChecked(False)
        self.spin_lomo_sec_w = QDoubleSpinBox()
        self.spin_lomo_sec_w.setRange(1.0, 50.0)
        self.spin_lomo_sec_h = QDoubleSpinBox()
        self.spin_lomo_sec_h.setRange(5.0, 300.0)
        row_l2.addWidget(self.chk_lomo_sec)
        row_l2.addWidget(QLabel("Ancho:"))
        row_l2.addWidget(self.spin_lomo_sec_w)
        row_l2.addWidget(QLabel("Alto:"))
        row_l2.addWidget(self.spin_lomo_sec_h)
        l_pieces.addLayout(row_l2)

        # CD
        row_cd = QHBoxLayout()
        self.chk_cd = QCheckBox("Etiqueta CD:")
        self.chk_cd.setChecked(True)
        self.spin_cd_outer = QDoubleSpinBox()
        self.spin_cd_outer.setRange(10.0, 200.0)
        self.chk_cd_hole = QCheckBox("Agujero:")
        self.spin_cd_inner = QDoubleSpinBox()
        self.spin_cd_inner.setRange(0.0, 50.0)
        row_cd.addWidget(self.chk_cd)
        row_cd.addWidget(QLabel("Diámetro exterior:"))
        row_cd.addWidget(self.spin_cd_outer)
        row_cd.addWidget(self.chk_cd_hole)
        row_cd.addWidget(self.spin_cd_inner)
        l_pieces.addLayout(row_cd)

        # Interior
        row_int = QHBoxLayout()
        self.chk_interior = QCheckBox("Interior / Libreto:")
        self.spin_int_w = QDoubleSpinBox()
        self.spin_int_w.setRange(5.0, 300.0)
        self.spin_int_h = QDoubleSpinBox()
        self.spin_int_h.setRange(5.0, 300.0)
        row_int.addWidget(self.chk_interior)
        row_int.addWidget(QLabel("Ancho:"))
        row_int.addWidget(self.spin_int_w)
        row_int.addWidget(QLabel("Alto:"))
        row_int.addWidget(self.spin_int_h)
        l_pieces.addLayout(row_int)

        lbl_int_tip = QLabel("💡 El libreto interior es un poco más pequeño que la portada (~1.5 mm menos) para deslizarse suavemente en las pestañas interiores.")
        lbl_int_tip.setStyleSheet("color: #64748B; font-size: 11px; margin-left: 18px; font-style: italic;")
        l_pieces.addWidget(lbl_int_tip)

        # Opción bandeja continua desplegada
        self.chk_continuous = QCheckBox("Unir Contraportada + Lomo + Portada en una sola pieza continua desplegada")
        self.chk_continuous.setStyleSheet("font-weight: 500; color: #2563EB;")
        l_pieces.addWidget(self.chk_continuous)

        right_layout.addWidget(grp_pieces)

        # 3. Márgenes y configuración de impresión
        grp_print = QGroupBox("Márgenes, Sangrado y Papel Preferido")
        l_p = QHBoxLayout(grp_print)

        l_p.addWidget(QLabel("Margen Seguridad:"))
        self.spin_safe = QDoubleSpinBox()
        self.spin_safe.setRange(0.0, 10.0)
        self.spin_safe.setSingleStep(0.2)
        l_p.addWidget(self.spin_safe)

        l_p.addWidget(QLabel("Sangrado:"))
        self.spin_bleed = QDoubleSpinBox()
        self.spin_bleed.setRange(0.0, 10.0)
        self.spin_bleed.setSingleStep(0.2)
        l_p.addWidget(self.spin_bleed)

        l_p.addWidget(QLabel("Separación:"))
        self.spin_sep = QDoubleSpinBox()
        self.spin_sep.setRange(0.0, 20.0)
        self.spin_sep.setSingleStep(0.5)
        l_p.addWidget(self.spin_sep)

        l_p.addWidget(QLabel("Papel:"))
        self.combo_paper = QComboBox()
        self.combo_paper.addItems(["A4", "Carta (Letter)", "Oficio (Legal)", "A5", "4x6 pulgadas (Foto)"])
        l_p.addWidget(self.combo_paper)

        right_layout.addWidget(grp_print)

        # Botón Guardar Medidas
        btn_save_box = QHBoxLayout()
        self.btn_save = QPushButton("Guardar Cambios del Perfil")
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.clicked.connect(self._on_save_profile)
        btn_save_box.addStretch()
        btn_save_box.addWidget(self.btn_save)
        right_layout.addLayout(btn_save_box)

        scroll.setWidget(right_widget)
        main_layout.addWidget(scroll, 2)

    def _load_profiles(self):
        self.list_profiles.clear()
        profiles = self.repo.get_all()
        target_row = 0
        for i, p in enumerate(profiles):
            item_text = f"{p.name} {'(Activo)' if p.id == self.active_id else ''}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.list_profiles.addItem(item)
            if p.id == self.active_id:
                target_row = i

        if self.list_profiles.count() > 0:
            self.list_profiles.setCurrentRow(target_row)

    def _on_profile_selected(self, row: int):
        if row < 0:
            return
        item = self.list_profiles.item(row)
        profile_id = item.data(Qt.ItemDataRole.UserRole)
        profile = self.repo.get_by_id(profile_id)
        if not profile:
            return

        self.current_profile = profile
        self._populate_fields(profile)

    def _populate_fields(self, p: CaseProfile):
        self.lbl_provisional_badge.setVisible(p.is_provisional)

        self.spin_ext_w.setValue(p.exterior_width_mm)
        self.spin_ext_h.setValue(p.exterior_height_mm)
        self.spin_ext_d.setValue(p.exterior_depth_mm)

        self.chk_portada.setChecked(p.portada.enabled)
        self.spin_portada_w.setValue(p.portada.width_mm)
        self.spin_portada_h.setValue(p.portada.height_mm)

        self.chk_contra.setChecked(p.contraportada.enabled)
        self.spin_contra_w.setValue(p.contraportada.width_mm)
        self.spin_contra_h.setValue(p.contraportada.height_mm)

        self.chk_interior_contra.setChecked(p.interior_contraportada.enabled)
        self.spin_interior_contra_w.setValue(p.interior_contraportada.width_mm)
        self.spin_interior_contra_h.setValue(p.interior_contraportada.height_mm)

        self.chk_lomo.setChecked(p.lomo.enabled)
        self.spin_lomo_w.setValue(p.lomo.width_mm)
        self.spin_lomo_h.setValue(p.lomo.height_mm)

        self.chk_lomo_sec.setChecked(p.lomo_secundario.enabled)
        self.spin_lomo_sec_w.setValue(p.lomo_secundario.width_mm)
        self.spin_lomo_sec_h.setValue(p.lomo_secundario.height_mm)

        self.chk_cd.setChecked(p.cd.enabled)
        self.spin_cd_outer.setValue(p.cd.outer_diameter_mm)
        self.chk_cd_hole.setChecked(p.cd.has_inner_hole)
        self.spin_cd_inner.setValue(p.cd.inner_hole_diameter_mm)

        self.chk_interior.setChecked(p.interior.enabled)
        self.spin_int_w.setValue(p.interior.width_mm)
        self.spin_int_h.setValue(p.interior.height_mm)

        self.chk_continuous.setChecked(p.continuous_tray)

        self.spin_safe.setValue(p.safe_margin_mm)
        self.spin_bleed.setValue(p.bleed_mm)
        self.spin_sep.setValue(p.separation_mm)

        idx = self.combo_paper.findText(p.preferred_paper)
        if idx >= 0:
            self.combo_paper.setCurrentIndex(idx)

    def _on_save_profile(self):
        if not self.current_profile:
            return

        self.current_profile.exterior_width_mm = self.spin_ext_w.value()
        self.current_profile.exterior_height_mm = self.spin_ext_h.value()
        self.current_profile.exterior_depth_mm = self.spin_ext_d.value()

        self.current_profile.portada.enabled = self.chk_portada.isChecked()
        self.current_profile.portada.width_mm = self.spin_portada_w.value()
        self.current_profile.portada.height_mm = self.spin_portada_h.value()

        self.current_profile.contraportada.enabled = self.chk_contra.isChecked()
        self.current_profile.contraportada.width_mm = self.spin_contra_w.value()
        self.current_profile.contraportada.height_mm = self.spin_contra_h.value()

        self.current_profile.interior_contraportada.enabled = self.chk_interior_contra.isChecked()
        self.current_profile.interior_contraportada.width_mm = self.spin_interior_contra_w.value()
        self.current_profile.interior_contraportada.height_mm = self.spin_interior_contra_h.value()

        self.current_profile.lomo.enabled = self.chk_lomo.isChecked()
        self.current_profile.lomo.width_mm = self.spin_lomo_w.value()
        self.current_profile.lomo.height_mm = self.spin_lomo_h.value()

        self.current_profile.lomo_secundario.enabled = self.chk_lomo_sec.isChecked()
        self.current_profile.lomo_secundario.width_mm = self.spin_lomo_sec_w.value()
        self.current_profile.lomo_secundario.height_mm = self.spin_lomo_sec_h.value()

        self.current_profile.cd.enabled = self.chk_cd.isChecked()
        self.current_profile.cd.outer_diameter_mm = self.spin_cd_outer.value()
        self.current_profile.cd.has_inner_hole = self.chk_cd_hole.isChecked()
        self.current_profile.cd.inner_hole_diameter_mm = self.spin_cd_inner.value()

        self.current_profile.interior.enabled = self.chk_interior.isChecked()
        self.current_profile.interior.width_mm = self.spin_int_w.value()
        self.current_profile.interior.height_mm = self.spin_int_h.value()

        self.current_profile.continuous_tray = self.chk_continuous.isChecked()

        self.current_profile.safe_margin_mm = self.spin_safe.value()
        self.current_profile.bleed_mm = self.spin_bleed.value()
        self.current_profile.separation_mm = self.spin_sep.value()
        self.current_profile.preferred_paper = self.combo_paper.currentText()

        # Guardar en repositorio
        self.repo.save_profile(self.current_profile)
        QMessageBox.information(self, "Perfil Guardado", f"Las medidas del perfil '{self.current_profile.name}' se han guardado con éxito.")
        self.profileChanged.emit(self.current_profile.id)

    def _on_new_profile(self):
        name, ok = QInputDialog.getText(self, "Nuevo Perfil", "Nombre del nuevo perfil de estuche:")
        if ok and name.strip():
            new_p = self.repo.create_profile(name.strip())
            self.active_id = new_p.id
            self.repo.set_active_profile_id(new_p.id)
            self._load_profiles()
            self.profileChanged.emit(new_p.id)

    def _on_duplicate_profile(self):
        if not self.current_profile:
            return
        name, ok = QInputDialog.getText(
            self, "Duplicar Perfil",
            "Nombre para la copia:",
            text=f"{self.current_profile.name} (Copia)"
        )
        if ok and name.strip():
            dup_p = self.repo.duplicate_profile(self.current_profile.id, name.strip())
            self.active_id = dup_p.id
            self.repo.set_active_profile_id(dup_p.id)
            self._load_profiles()
            self.profileChanged.emit(dup_p.id)

    def _on_rename_profile(self):
        if not self.current_profile:
            return
        name, ok = QInputDialog.getText(
            self, "Renombrar Perfil",
            "Nuevo nombre del perfil:",
            text=self.current_profile.name
        )
        if ok and name.strip():
            self.current_profile.name = name.strip()
            self.repo.save_profile(self.current_profile)
            self._load_profiles()
            self.profileChanged.emit(self.current_profile.id)

    def _on_delete_profile(self):
        if not self.current_profile:
            return
        if len(self.repo.get_all()) <= 1:
            QMessageBox.warning(self, "Aviso", "No se puede eliminar el único perfil disponible.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Desea eliminar el perfil '{self.current_profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.repo.delete_profile(self.current_profile.id)
            self.active_id = self.repo.get_active_profile_id()
            self._load_profiles()
            self.profileChanged.emit(self.active_id)

    def _on_set_active(self):
        if self.current_profile:
            self.active_id = self.current_profile.id
            self.repo.set_active_profile_id(self.current_profile.id)
            self._load_profiles()
            self.profileChanged.emit(self.current_profile.id)
            QMessageBox.information(self, "Perfil Activo", f"'{self.current_profile.name}' ahora es el perfil activo.")
