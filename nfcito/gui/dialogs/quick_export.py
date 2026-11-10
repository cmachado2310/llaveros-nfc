"""
Diálogo rápido de exportación de PDF listo para imprimir.
Permite especificar la cantidad de paquetes (mini álbumes completos) a producir,
admite incluir múltiples proyectos en un solo PDF y calcula automáticamente
la distribución en hojas manteniendo siempre las dimensiones físicas al 100% real.
"""
from pathlib import Path
import os
from typing import Optional, List, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QComboBox, QCheckBox, QLineEdit, QFileDialog, QMessageBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QFrame, QWidget
)
from PySide6.QtCore import Qt

from nfcito.models.project import Project
from nfcito.models.profile import CaseProfile
from nfcito.core.layout_engine import LayoutEngine, PAPER_SIZES_MM, PIECE_NAMES_ES
from nfcito.core.pdf_exporter import PDFExporter
from nfcito.storage.project_repo import ProjectRepository

class QuickExportDialog(QDialog):
    def __init__(self, project: Project, profile: CaseProfile, parent=None):
        super().__init__(parent)
        self.project = project
        self.profile = profile
        self.setWindowTitle("Exportar PDF Listo para Imprimir — Escala 100% Real")
        self.setMinimumWidth(660)
        self.setMinimumHeight(520)

        # Lista de proyectos incluidos: cada elemento es [Project, packages_count]
        self.included_projects: List[List] = [[self.project, 1]]

        # Lista de piezas sueltas / faltantes extras: cada elemento es [Project, piece_key, quantity]
        self.extra_pieces: List[List] = []

        self._init_ui()
        self._update_table()
        self._update_combo_extra_projects()
        self._update_extras_table()
        self._update_estimate()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(6, 6, 6, 6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        # Encabezado
        lbl_head = QLabel(
            "<b>Adecuar proyectos en PDF de impresión física</b><br>"
            "Especifique cuántos paquetes (juegos completos) desea producir de cada proyecto. "
            "Puede incluir más de un proyecto en el mismo PDF y agregar piezas sueltas que le hagan falta. "
            "La aplicación adecúa todo automáticamente sin alterar las medidas físicas (escala 100% real garantizada)."
        )
        lbl_head.setWordWrap(True)
        lbl_head.setStyleSheet("color: #1E293B; background-color: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 6px; padding: 10px;")
        layout.addWidget(lbl_head)

        # 1. Grupo: Proyectos y Paquetes (Multi-Proyecto)
        grp_projects = QGroupBox("1. Proyectos a Incluir y Cantidad de Paquetes")
        l_proj = QVBoxLayout(grp_projects)

        self.table_projects = QTableWidget()
        self.table_projects.setColumnCount(3)
        self.table_projects.setHorizontalHeaderLabels(["Nombre del Proyecto", "Paquetes a Producir", "Acciones"])
        self.table_projects.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_projects.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_projects.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_projects.setFixedHeight(120)
        l_proj.addWidget(self.table_projects)

        # Botón para añadir más proyectos y control de álbumes a 0
        h_add = QHBoxLayout()
        btn_add_proj = QPushButton("＋ Añadir Otro Proyecto (.nfcito)...")
        btn_add_proj.setStyleSheet("font-weight: 600; color: #1D4ED8; padding: 5px 12px;")
        btn_add_proj.clicked.connect(self._on_add_another_project)
        h_add.addWidget(btn_add_proj)

        btn_zero_pkgs = QPushButton("🎯 Poner Álbumes a 0 (Solo Piezas Sueltas)")
        btn_zero_pkgs.setToolTip("Pone en 0 la cantidad de álbumes completos para imprimir exclusivamente piezas sueltas")
        btn_zero_pkgs.setStyleSheet("color: #0F766E; font-weight: 500;")
        btn_zero_pkgs.clicked.connect(self._on_set_zero_packages)
        h_add.addWidget(btn_zero_pkgs)

        btn_one_pkg = QPushButton("📦 Restaurar 1 Paquete")
        btn_one_pkg.setStyleSheet("color: #475569;")
        btn_one_pkg.clicked.connect(self._on_restore_packages)
        h_add.addWidget(btn_one_pkg)

        h_add.addStretch()
        l_proj.addLayout(h_add)

        layout.addWidget(grp_projects)

        # 2. Grupo: Piezas Sueltas / Extras Opcionales
        grp_extras = QGroupBox("2. Piezas Sueltas o Faltantes Adicionales (Opcional)")
        l_extras = QVBoxLayout(grp_extras)

        self.chk_only_extras = QCheckBox("🎯 Imprimir únicamente piezas sueltas (desactivar álbumes completos)")
        self.chk_only_extras.setStyleSheet("font-weight: bold; color: #0F766E; font-size: 12px;")
        self.chk_only_extras.toggled.connect(self._on_toggle_only_extras)
        l_extras.addWidget(self.chk_only_extras)

        lbl_ext_tip = QLabel(
            "💡 ¿Le hace falta alguna pieza individual (ej. solo el CD de un proyecto o 1 portada extra)? "
            "Seleccione el proyecto y la pieza para añadirla suelta en la hoja sin necesidad de imprimir todo el álbum completo:"
        )
        lbl_ext_tip.setWordWrap(True)
        lbl_ext_tip.setStyleSheet("color: #475569; font-size: 11px; margin-bottom: 2px;")
        l_extras.addWidget(lbl_ext_tip)

        row_load_loose = QHBoxLayout()
        btn_load_loose_proj = QPushButton("📂 Cargar Otro Proyecto (.nfcito) para Piezas Sueltas...")
        btn_load_loose_proj.setStyleSheet("font-weight: 600; color: #0F766E; padding: 4px 10px;")
        btn_load_loose_proj.setToolTip("Carga otro proyecto con 0 paquetes completos para que pueda elegir piezas sueltas de él en Modo Mixto")
        btn_load_loose_proj.clicked.connect(self._on_load_project_for_loose_pieces)
        row_load_loose.addWidget(btn_load_loose_proj)
        row_load_loose.addStretch()
        l_extras.addLayout(row_load_loose)

        row_add_extra = QHBoxLayout()
        row_add_extra.addWidget(QLabel("Proyecto:"))
        self.combo_extra_proj = QComboBox()
        row_add_extra.addWidget(self.combo_extra_proj, 1)

        row_add_extra.addWidget(QLabel("Pieza:"))
        self.combo_extra_piece = QComboBox()
        self.combo_extra_piece.addItem("Portada Frontal", "portada")
        self.combo_extra_piece.addItem("Contraportada Exterior", "contraportada")
        self.combo_extra_piece.addItem("Fondo Bandeja (Interior)", "interior_contraportada")
        self.combo_extra_piece.addItem("Etiqueta CD Circular", "cd")
        self.combo_extra_piece.addItem("Interior / Libreto", "interior")
        self.combo_extra_piece.addItem("Lomo Principal", "lomo")
        self.combo_extra_piece.addItem("Lomo Secundario (Opcional)", "lomo_secundario")
        row_add_extra.addWidget(self.combo_extra_piece, 1)

        row_add_extra.addWidget(QLabel("Cantidad:"))
        self.spin_extra_qty = QSpinBox()
        self.spin_extra_qty.setRange(1, 50)
        self.spin_extra_qty.setValue(1)
        self.spin_extra_qty.setSuffix(" ud(s)")
        row_add_extra.addWidget(self.spin_extra_qty)

        self.btn_add_extra = QPushButton("＋ Agregar Pieza Suelta")
        self.btn_add_extra.setStyleSheet("background-color: #F1F5F9; font-weight: 600; color: #0F766E; padding: 4px 10px;")
        self.btn_add_extra.clicked.connect(self._on_add_extra_piece)
        row_add_extra.addWidget(self.btn_add_extra)

        l_extras.addLayout(row_add_extra)

        # Tabla de piezas sueltas añadidas
        self.table_extras = QTableWidget()
        self.table_extras.setColumnCount(4)
        self.table_extras.setHorizontalHeaderLabels(["Proyecto", "Pieza Suelta", "Cantidad", "Acción"])
        self.table_extras.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_extras.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_extras.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_extras.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_extras.setFixedHeight(95)
        l_extras.addWidget(self.table_extras)

        layout.addWidget(grp_extras)

        # 3. Configuración de Papel y Rendimiento
        grp_config = QGroupBox("3. Formato de Papel y Adecuación Automática")
        l_conf = QVBoxLayout(grp_config)

        row_paper = QHBoxLayout()
        row_paper.addWidget(QLabel("Tamaño de papel:"))
        self.combo_paper = QComboBox()
        for p in PAPER_SIZES_MM.keys():
            self.combo_paper.addItem(p)
        idx = self.combo_paper.findText(self.project.print_layout.paper_size)
        if idx >= 0:
            self.combo_paper.setCurrentIndex(idx)
        self.combo_paper.currentIndexChanged.connect(self._update_estimate)
        row_paper.addWidget(self.combo_paper)
        row_paper.addStretch()
        l_conf.addLayout(row_paper)

        # Indicador dinámico de paquetes y hojas
        self.lbl_estimate = QLabel("")
        self.lbl_estimate.setWordWrap(True)
        self.lbl_estimate.setStyleSheet("color: #15803D; font-weight: 600; font-size: 12px; background-color: #F0FDF4; padding: 8px; border-radius: 4px; border: 1px solid #BBF7D0;")
        l_conf.addWidget(self.lbl_estimate)

        layout.addWidget(grp_config)

        # 4. Opciones de PDF
        grp_opts = QGroupBox("4. Opciones de Impresión")
        l_opts = QVBoxLayout(grp_opts)

        self.chk_cut_lines = QCheckBox("Incluir líneas y marcas de corte discretas")
        self.chk_cut_lines.setChecked(self.project.print_layout.show_cut_lines)
        l_opts.addWidget(self.chk_cut_lines)

        self.chk_include_calib = QCheckBox("Incluir página de calibración inicial (50 × 50 mm)")
        self.chk_include_calib.setChecked(self.project.print_layout.include_calibration)
        l_opts.addWidget(self.chk_include_calib)

        self.chk_auto_open = QCheckBox("Abrir el PDF automáticamente tras generarlo")
        self.chk_auto_open.setChecked(True)
        l_opts.addWidget(self.chk_auto_open)

        layout.addWidget(grp_opts)

        # 5. Ruta de guardado
        grp_dest = QGroupBox("5. Archivo de Salida")
        l_dest = QVBoxLayout(grp_dest)
        h_dest = QHBoxLayout()
        self.txt_dest = QLineEdit()
        suggested = f"{self.project.name.replace(' ', '_')}_Impresion.pdf"
        default_dir = Path.home() / "Documents"
        self.txt_dest.setText(str(default_dir / suggested))
        btn_browse = QPushButton("Examinar...")
        btn_browse.clicked.connect(self._on_browse)
        h_dest.addWidget(self.txt_dest, 1)
        h_dest.addWidget(btn_browse)
        l_dest.addLayout(h_dest)
        layout.addWidget(grp_dest)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

        # Botones de pie (fijos en la parte inferior para accesibilidad total)
        h_btn = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        self.btn_export = QPushButton("🚀 Generar y Abrir PDF Listo para Imprimir")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setFixedHeight(40)
        self.btn_export.setStyleSheet("font-size: 13px; font-weight: bold; background-color: #2563EB; color: white; padding: 8px 16px;")
        self.btn_export.clicked.connect(self._on_export)

        h_btn.addWidget(btn_cancel)
        h_btn.addStretch()
        h_btn.addWidget(self.btn_export)
        outer_layout.addLayout(h_btn)

    def _update_table(self):
        self.table_projects.setRowCount(len(self.included_projects))
        for row, entry in enumerate(self.included_projects):
            proj, pkgs = entry[0], entry[1]

            # Columna 0: Nombre
            label_text = f"🎵 {proj.name}"
            if row == 0:
                label_text += " (Proyecto Actual)"
            item_name = QTableWidgetItem(label_text)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_projects.setItem(row, 0, item_name)

            # Columna 1: SpinBox paquetes
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setValue(pkgs)
            spin.setSpecialValueText("0 (Sin álbum)")
            spin.setSuffix(" paquete(s)")
            spin.setStyleSheet("font-weight: bold;")
            spin.valueChanged.connect(lambda val, ent=entry: self._on_entry_packages_changed(ent, val))
            self.table_projects.setCellWidget(row, 1, spin)

            # Columna 2: Acción Quitar (solo para proyectos adicionales)
            if row > 0:
                btn_del = QPushButton("Quitar")
                btn_del.setStyleSheet("color: #DC2626; font-weight: 500;")
                btn_del.clicked.connect(lambda _, ent=entry: self._on_remove_entry(ent))
                self.table_projects.setCellWidget(row, 2, btn_del)
            else:
                lbl_fixed = QLabel("Principal")
                lbl_fixed.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_fixed.setStyleSheet("color: #64748B; font-size: 11px;")
                self.table_projects.setCellWidget(row, 2, lbl_fixed)

    def _on_set_zero_packages(self):
        """Pone en 0 los paquetes de todos los proyectos para imprimir solo piezas sueltas."""
        for entry in self.included_projects:
            entry[1] = 0
        self.chk_only_extras.blockSignals(True)
        self.chk_only_extras.setChecked(True)
        self.chk_only_extras.blockSignals(False)
        self._update_table()
        self._update_estimate()

    def _on_restore_packages(self):
        """Restaura a 1 paquete el proyecto principal para imprimir el álbum completo."""
        for row, entry in enumerate(self.included_projects):
            if row == 0 or entry[1] == 0:
                entry[1] = 1
        self.chk_only_extras.blockSignals(True)
        self.chk_only_extras.setChecked(False)
        self.chk_only_extras.blockSignals(False)
        self._update_table()
        self._update_estimate()

    def _on_toggle_only_extras(self, checked: bool):
        if checked:
            self._on_set_zero_packages()
        else:
            self._on_restore_packages()

    def _on_entry_packages_changed(self, entry: list, val: int):
        entry[1] = val
        total_pkgs = sum(e[1] for e in self.included_projects)
        self.chk_only_extras.blockSignals(True)
        self.chk_only_extras.setChecked(total_pkgs == 0)
        self.chk_only_extras.blockSignals(False)
        self._update_estimate()

    def _on_remove_entry(self, entry: list):
        if entry in self.included_projects and entry is not self.included_projects[0]:
            removed_proj = entry[0]
            self.included_projects.remove(entry)
            # Limpiar piezas extras de ese proyecto
            self.extra_pieces = [ep for ep in self.extra_pieces if ep[0] != removed_proj]
            self._update_table()
            self._update_combo_extra_projects()
            self._update_extras_table()
            self._update_estimate()

    def _update_combo_extra_projects(self):
        self.combo_extra_proj.blockSignals(True)
        cur_data = self.combo_extra_proj.currentData()
        self.combo_extra_proj.clear()
        selected_idx = 0
        for row, entry in enumerate(self.included_projects):
            proj, pkgs = entry[0], entry[1]
            status_txt = f"{pkgs} paq. completos" if pkgs > 0 else "0 paq. (solo sueltas)"
            label = f"🎵 {proj.name} ({status_txt})"
            if row == 0:
                label = f"🎵 {proj.name} [Actual] ({status_txt})"
            self.combo_extra_proj.addItem(label, proj)
            if cur_data is not None and proj == cur_data:
                selected_idx = row
        if self.combo_extra_proj.count() > 0:
            self.combo_extra_proj.setCurrentIndex(selected_idx)
        self.combo_extra_proj.blockSignals(False)

    def _on_add_extra_piece(self):
        if self.combo_extra_proj.count() == 0:
            return
        proj = self.combo_extra_proj.currentData()
        piece_key = self.combo_extra_piece.currentData()
        qty = self.spin_extra_qty.value()
        if not proj or not piece_key or qty <= 0:
            return

        # Si ya existe en la lista de extras, sumar la cantidad
        found = False
        for item in self.extra_pieces:
            if item[0] == proj and item[1] == piece_key:
                item[2] += qty
                found = True
                break
        if not found:
            self.extra_pieces.append([proj, piece_key, qty])

        self._update_extras_table()
        self._update_estimate()

    def _update_extras_table(self):
        self.table_extras.setRowCount(len(self.extra_pieces))
        for row, item in enumerate(self.extra_pieces):
            proj, piece_key, qty = item[0], item[1], item[2]
            piece_name = PIECE_NAMES_ES.get(piece_key, piece_key)

            # Columna 0: Proyecto
            it_proj = QTableWidgetItem(f"🎵 {proj.name}")
            it_proj.setFlags(it_proj.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_extras.setItem(row, 0, it_proj)

            # Columna 1: Pieza
            it_piece = QTableWidgetItem(f"✂️ {piece_name}")
            it_piece.setFlags(it_piece.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_extras.setItem(row, 1, it_piece)

            # Columna 2: Cantidad
            spin = QSpinBox()
            spin.setRange(1, 50)
            spin.setValue(qty)
            spin.setSuffix(" ud(s)")
            spin.valueChanged.connect(lambda val, it=item: self._on_extra_qty_changed(it, val))
            self.table_extras.setCellWidget(row, 2, spin)

            # Columna 3: Quitar
            btn_del = QPushButton("Quitar")
            btn_del.setStyleSheet("color: #DC2626; font-weight: 500;")
            btn_del.clicked.connect(lambda _, it=item: self._on_remove_extra(it))
            self.table_extras.setCellWidget(row, 3, btn_del)

    def _on_extra_qty_changed(self, item: list, val: int):
        item[2] = val
        self._update_estimate()

    def _on_remove_extra(self, item: list):
        if item in self.extra_pieces:
            self.extra_pieces.remove(item)
            self._update_extras_table()
            self._update_estimate()

    def _on_add_another_project(self):
        self._load_project_file(initial_packages=1)

    def _on_load_project_for_loose_pieces(self):
        self._load_project_file(initial_packages=0)

    def _load_project_file(self, initial_packages: int = 1):
        dialog_title = (
            "Seleccionar Proyecto para Extraer Piezas Sueltas"
            if initial_packages == 0 else
            "Seleccionar Proyecto NFCito para Incluir en el PDF"
        )
        file_path, _ = QFileDialog.getOpenFileName(
            self, dialog_title,
            "", "Proyectos NFCito (*.nfcito *.json);;Todos los archivos (*.*)"
        )
        if file_path:
            try:
                loaded_proj, warnings = ProjectRepository.load_project(file_path)
                target_resolved = str(Path(file_path).resolve())

                # Verificar si el mismo archivo ya está en la lista
                existing_entry = None
                for entry in self.included_projects:
                    p = entry[0]
                    if p.file_path and str(Path(p.file_path).resolve()) == target_resolved:
                        existing_entry = entry
                        break

                if existing_entry:
                    if initial_packages > 0:
                        existing_entry[1] += initial_packages
                    self._update_table()
                    self._update_combo_extra_projects()
                    idx = self.combo_extra_proj.findData(existing_entry[0])
                    if idx >= 0:
                        self.combo_extra_proj.setCurrentIndex(idx)
                    self._update_estimate()
                    msg = f"El proyecto '{existing_entry[0].name}' ya estaba cargado."
                    if initial_packages > 0:
                        msg += f" Se sumó 1 paquete (total: {existing_entry[1]} paquetes)."
                    else:
                        msg += " Ahora está seleccionado en el selector de piezas sueltas."
                    QMessageBox.information(self, "Proyecto Seleccionado", msg)
                    return

                # Si tiene el mismo nombre que otro proyecto, desambiguar con el nombre de archivo
                name_collisions = [e[0].name for e in self.included_projects if e[0].name == loaded_proj.name]
                if name_collisions:
                    loaded_proj.name = f"{loaded_proj.name} ({Path(file_path).stem})"

                self.included_projects.append([loaded_proj, initial_packages])
                self._update_table()
                self._update_combo_extra_projects()

                # Seleccionar automáticamente el proyecto recién cargado en el combo de piezas sueltas
                idx = self.combo_extra_proj.findData(loaded_proj)
                if idx >= 0:
                    self.combo_extra_proj.setCurrentIndex(idx)

                self._update_estimate()

                if initial_packages == 0:
                    QMessageBox.information(
                        self, "Proyecto Añadido para Piezas Sueltas",
                        f"Se cargó '{loaded_proj.name}' con 0 álbumes completos.\n\n"
                        "Está seleccionado en la sección 2. Elija la pieza que necesita (ej. el CD o portada) "
                        "y pulse '＋ Agregar Pieza Suelta' para incluirla en el PDF en Modo Mixto."
                    )

                if warnings:
                    QMessageBox.warning(self, "Aviso de Imágenes", "\n".join(warnings))
            except Exception as e:
                QMessageBox.critical(self, "Error al cargar proyecto", f"No se pudo cargar el archivo:\n{e}")

    def _update_estimate(self):
        paper_size = self.combo_paper.currentText()
        project_packages: List[Tuple[Project, int]] = [(p, count) for p, count in self.included_projects]
        total_packages = sum(count for _, count in project_packages)
        extra_list: List[Tuple[Project, str, int]] = [(p, k, qty) for p, k, qty in self.extra_pieces]
        total_extras = sum(qty for _, _, qty in extra_list)

        try:
            layout_res = LayoutEngine.compute_multi_project_layout(
                project_packages=project_packages,
                profile=self.profile,
                paper_size_name=paper_size,
                orientation=self.project.print_layout.orientation,
                margin_mm=self.project.print_layout.margin_mm,
                spacing_mm=self.project.print_layout.spacing_mm,
                extra_pieces=extra_list
            )
            n_pages = len(layout_res.pages)
            total_items = layout_res.total_items_placed

            if total_packages == 0 and total_extras > 0:
                self.lbl_estimate.setText(
                    f"🎯 <b>Modo Solo Piezas Sueltas Activo:</b> Se imprimirán únicamente <b>{total_extras} pieza(s) suelta(s)</b> "
                    f"({total_items} piezas en total, <b>sin imprimir álbumes completos</b>).<br>"
                    f"📄 La aplicación distribuirá las piezas en <b>{n_pages} hoja(s) de papel {paper_size}</b> "
                    f"a escala 100% física real sin encogimiento."
                )
            elif total_packages > 0 and total_extras > 0:
                pkgs_info = ", ".join([f"{p.name} ({c} paq.)" for p, c in self.included_projects if c > 0])
                extras_info = ", ".join([f"{p.name}: {PIECE_NAMES_ES.get(k, k)} x{qty}" for p, k, qty in self.extra_pieces])
                self.lbl_estimate.setText(
                    f"🔀 <b>Modo Mixto Activo (Álbumes + Piezas Sueltas):</b><br>"
                    f"• <b>Álbumes completos:</b> {total_packages} paquete(s) [{pkgs_info}].<br>"
                    f"• <b>Piezas sueltas extras/incompletas:</b> {total_extras} pieza(s) [{extras_info}].<br>"
                    f"📄 Todo se empaquetará junto (<b>{total_items} piezas en total</b>) en "
                    f"<b>{n_pages} hoja(s) de papel {paper_size}</b> a escala 100% física real sin deformación."
                )
            elif total_packages > 0:
                self.lbl_estimate.setText(
                    f"📦 <b>Adecuación calculada:</b> {total_packages} paquete(s) solicitados "
                    f"({len(self.included_projects)} proyecto(s) diferentes, {total_items} piezas en total).<br>"
                    f"📄 La aplicación distribuirá todo en <b>{n_pages} hoja(s) de papel {paper_size}</b> "
                    f"(capacidad de al menos 5 paquetes por hoja A4) a escala 100% física real sin encogimiento."
                )
            else:
                self.lbl_estimate.setText(
                    "⚠️ <b>Sin piezas seleccionadas:</b> Indique al menos 1 paquete de álbum o agregue piezas sueltas (ej. CD) abajo."
                )
        except Exception:
            pass

    def _on_browse(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF Listo para Imprimir", self.txt_dest.text(), "Archivos PDF (*.pdf)"
        )
        if dest:
            self.txt_dest.setText(dest)

    def _on_export(self):
        file_path = self.txt_dest.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Ruta requerida", "Por favor seleccione una ruta para guardar el archivo PDF.")
            return

        paper_size = self.combo_paper.currentText()
        project_packages: List[Tuple[Project, int]] = [(p, count) for p, count in self.included_projects]
        total_packages = sum(count for _, count in project_packages)
        extra_list: List[Tuple[Project, str, int]] = [(p, k, qty) for p, k, qty in self.extra_pieces]
        total_extras = sum(qty for _, _, qty in extra_list)

        if total_packages <= 0 and total_extras <= 0:
            QMessageBox.warning(
                self, "Aviso",
                "Debe especificar al menos 1 paquete de álbum o agregar alguna pieza suelta para imprimir."
            )
            return

        try:
            # Guardar preferencias en el proyecto principal
            self.project.print_layout.paper_size = paper_size
            self.project.print_layout.show_cut_lines = self.chk_cut_lines.isChecked()
            self.project.print_layout.include_calibration = self.chk_include_calib.isChecked()

            layout_res = LayoutEngine.compute_multi_project_layout(
                project_packages=project_packages,
                profile=self.profile,
                paper_size_name=paper_size,
                orientation=self.project.print_layout.orientation,
                margin_mm=self.project.print_layout.margin_mm,
                spacing_mm=self.project.print_layout.spacing_mm,
                extra_pieces=extra_list
            )

            if layout_res.total_items_placed == 0:
                QMessageBox.warning(self, "Aviso", "No hay piezas activadas para imprimir.")
                return

            out_file = PDFExporter.export_pdf(
                output_path=file_path,
                project=self.project,
                profile=self.profile,
                layout_result=layout_res,
                include_calibration=self.chk_include_calib.isChecked(),
                show_cut_lines=self.chk_cut_lines.isChecked(),
                dpi=300
            )

            if self.chk_auto_open.isChecked():
                os.startfile(out_file)

            n_pages = len(layout_res.pages)
            page_text = f"{n_pages} hoja" if n_pages == 1 else f"{n_pages} hojas (añadidas automáticamente)"
            
            if total_packages == 0 and total_extras > 0:
                proj_summary = f"Solo piezas sueltas ({total_extras} piezas en total, sin álbumes completos)"
            else:
                included_txt = ", ".join([f"{p.name} ({c} paq.)" for p, c in self.included_projects if c > 0])
                extras_txt = f" + {total_extras} piezas sueltas" if total_extras > 0 else ""
                proj_summary = f"{included_txt}{extras_txt}"

            QMessageBox.information(
                self, "PDF Generado con Éxito",
                f"El archivo PDF listo para imprimir se generó en:\n{out_file}\n\n"
                f"• Contenido impreso: {proj_summary}.\n"
                f"• Piezas totales diagramadas: {layout_res.total_items_placed} piezas.\n"
                f"• Hojas generadas: {page_text}.\n"
                f"• Escala física: 100% exacta garantizada (sin deformación).\n\n"
                "¡Abierto en su lector de PDF para imprimir a precisión!"
            )

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error al Exportar PDF", f"No se pudo generar el documento PDF:\n{e}")
