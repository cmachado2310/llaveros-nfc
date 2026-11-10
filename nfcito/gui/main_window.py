"""
Ventana Principal de NFCito Studio.
Integra el modo manual (diseñador de piezas), modo automático (asistente rápido),
administrador de perfiles de medidas, lienzo interactivo, vista de conjunto y exportación.
"""
from typing import Optional
from pathlib import Path
import os
import subprocess

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QToolBar, QStatusBar, QStackedWidget, QFileDialog,
    QMessageBox, QSplitter, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QFont, QColor

from nfcito.models.project import Project, PieceDesign
from nfcito.models.profile import CaseProfile
from nfcito.storage.profile_repo import ProfileRepository
from nfcito.storage.project_repo import ProjectRepository
from nfcito.gui.canvas_view import CanvasView
from nfcito.gui.composite_view import CompositeView
from nfcito.gui.properties_dock import PropertiesDock
from nfcito.gui.dialogs.profile_manager import ProfileManagerDialog
from nfcito.gui.dialogs.quick_generator import QuickGeneratorDialog
from nfcito.gui.dialogs.print_layout import PrintLayoutDialog
from nfcito.gui.dialogs.calibration import CalibrationDialog
from nfcito.gui.dialogs.quick_export import QuickExportDialog
from nfcito.core.layout_engine import LayoutEngine
from nfcito.core.pdf_exporter import PDFExporter

class MainWindow(QMainWindow):
    def __init__(self, repo: ProfileRepository):
        super().__init__()
        self.repo = repo
        self.project: Project = Project()
        self.profile: CaseProfile = self.repo.get_by_id(self.repo.get_active_profile_id()) or self.repo.get_all()[0]

        self.current_piece_key: str = "portada"
        self.setWindowTitle("NFCito Studio — Mini Álbumes y Llaveros NFC")
        self.setMinimumSize(780, 500)

        self._init_ui()
        self._init_menus()
        self._init_toolbar()
        self._sync_profile_to_project()
        self._select_piece("portada")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(6, 6, 6, 6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Panel Lateral Izquierdo: Secciones del Álbum
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)

        lbl_sections = QLabel("Secciones del Álbum:")
        lbl_sections.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px;")
        left_layout.addWidget(lbl_sections)

        self.list_sections = QListWidget()
        self.list_sections.currentRowChanged.connect(self._on_section_selected)
        left_layout.addWidget(self.list_sections)

        # Botón directo para Guardar Como solicitado por el usuario
        self.btn_save_as = QPushButton("💾 Guardar Proyecto Como...")
        self.btn_save_as.setObjectName("primaryButton")
        self.btn_save_as.setStyleSheet("font-weight: 600; padding: 8px; font-size: 13px;")
        self.btn_save_as.clicked.connect(self._on_save_project_as)
        left_layout.addWidget(self.btn_save_as)

        splitter.addWidget(left_panel)

        # 2. Área Central con barra de previsualización en el Diseñador Manual
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(6)

        # Barra de modos de visualización para nunca editar a ciegas
        view_bar = QWidget()
        view_bar.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px;")
        view_bar_layout = QHBoxLayout(view_bar)
        view_bar_layout.setContentsMargins(8, 6, 8, 6)
        view_bar_layout.setSpacing(8)

        lbl_v = QLabel("👁️ Modo de Vista:")
        lbl_v.setStyleSheet("font-weight: bold; color: #1E293B;")
        view_bar_layout.addWidget(lbl_v)

        self.btn_view_edit = QPushButton("✂️ Modo Encuadre y Corte")
        self.btn_view_edit.setCheckable(True)
        self.btn_view_edit.setChecked(True)
        self.btn_view_edit.setToolTip("Muestra las guías de corte y permite arrastrar la foto con el ratón en tiempo real")
        self.btn_view_edit.clicked.connect(lambda: self._set_center_view_mode("edit"))
        view_bar_layout.addWidget(self.btn_view_edit)

        self.btn_view_clean = QPushButton("👁️ Previsualizar Pieza Limpia")
        self.btn_view_clean.setCheckable(True)
        self.btn_view_clean.setToolTip("Previsualiza la pieza individual limpia sin líneas de corte, exactamente como saldrá impresa")
        self.btn_view_clean.clicked.connect(lambda: self._set_center_view_mode("clean"))
        view_bar_layout.addWidget(self.btn_view_clean)

        self.btn_view_full = QPushButton("📖 Previsualizar Todo el Mini Álbum")
        self.btn_view_full.setCheckable(True)
        self.btn_view_full.setToolTip("Previsualiza el conjunto completo con portada, lomo, contraportada y CD ensamblados")
        self.btn_view_full.clicked.connect(lambda: self._set_center_view_mode("album"))
        view_bar_layout.addWidget(self.btn_view_full)

        view_bar_layout.addStretch()
        center_layout.addWidget(view_bar)

        self.stack_center = QStackedWidget()
        self.canvas_view = CanvasView()
        self.canvas_view.cropChanged.connect(self._on_canvas_crop_changed)
        self.canvas_view.imageDropped.connect(self._on_image_dropped)
        self.stack_center.addWidget(self.canvas_view)  # index 0

        self.composite_view = CompositeView()
        self.stack_center.addWidget(self.composite_view)  # index 1
        center_layout.addWidget(self.stack_center, 1)

        splitter.addWidget(center_panel)

        # 3. Panel Lateral Derecho: Propiedades
        self.properties_dock = PropertiesDock()
        self.properties_dock.pieceUpdated.connect(self._on_piece_updated)
        self.properties_dock.nfcUpdated.connect(self._on_nfc_updated)
        splitter.addWidget(self.properties_dock)

        left_panel.setMinimumWidth(180)
        center_panel.setMinimumWidth(320)
        self.properties_dock.setMinimumWidth(260)
        splitter.setChildrenCollapsible(False)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        main_layout.addWidget(splitter)

        # Barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _init_menus(self):
        menubar = self.menuBar()

        # Menú Archivo
        menu_file = menubar.addMenu("Archivo")

        act_new = QAction("Nuevo Proyecto", self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._on_new_project)
        menu_file.addAction(act_new)

        act_open = QAction("Abrir Proyecto...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._on_open_project)
        menu_file.addAction(act_open)

        act_save = QAction("Guardar", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._on_save_project)
        menu_file.addAction(act_save)

        act_save_as = QAction("Guardar Como...", self)
        act_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_as.triggered.connect(self._on_save_project_as)
        menu_file.addAction(act_save_as)

        act_dup = QAction("Duplicar Proyecto...", self)
        act_dup.triggered.connect(self._on_duplicate_project)
        menu_file.addAction(act_dup)

        menu_file.addSeparator()

        act_exit = QAction("Salir", self)
        act_exit.setShortcut(QKeySequence("Alt+F4"))
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Menú Perfiles
        menu_profiles = menubar.addMenu("Perfiles")
        act_manage_prof = QAction("Administrador de Perfiles de Medidas...", self)
        act_manage_prof.triggered.connect(self._open_profile_manager)
        menu_profiles.addAction(act_manage_prof)

        # Menú Herramientas
        menu_tools = menubar.addMenu("Herramientas")

        act_quick = QAction("Modo Automático: Generador Rápido...", self)
        act_quick.setShortcut(QKeySequence("Ctrl+G"))
        act_quick.triggered.connect(self._open_quick_generator)
        menu_tools.addAction(act_quick)

        menu_tools.addSeparator()

        act_quick_pdf = QAction("⚡ Exportar PDF Inmediato (Listo para Imprimir)...", self)
        act_quick_pdf.setShortcut(QKeySequence("Ctrl+E"))
        act_quick_pdf.triggered.connect(self._quick_export_pdf)
        menu_tools.addAction(act_quick_pdf)

        act_print_sheet = QAction("Organizar Hoja de Impresión y Exportar PDF...", self)
        act_print_sheet.setShortcut(QKeySequence("Ctrl+P"))
        act_print_sheet.triggered.connect(self._open_print_layout)
        menu_tools.addAction(act_print_sheet)

        act_calib = QAction("Calibración de Escala (50 × 50 mm)...", self)
        act_calib.triggered.connect(self._open_calibration)
        menu_tools.addAction(act_calib)

        # Menú Ayuda
        menu_help = menubar.addMenu("Ayuda")
        act_guide = QAction("Instrucciones de Impresión de Precisión", self)
        act_guide.triggered.connect(self._show_print_guide)
        menu_help.addAction(act_guide)

        act_about = QAction("Acerca de NFCito Studio", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    def _init_toolbar(self):
        toolbar = QToolBar("Barra de Herramientas Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Botones de modo
        self.btn_mode_manual = QPushButton("🎨 Modo Manual (Diseñador)")
        self.btn_mode_manual.setCheckable(True)
        self.btn_mode_manual.setChecked(True)
        self.btn_mode_manual.clicked.connect(self._on_switch_to_manual)
        toolbar.addWidget(self.btn_mode_manual)

        self.btn_mode_auto = QPushButton("⚡ Modo Automático (Generador Rápido)")
        self.btn_mode_auto.clicked.connect(self._open_quick_generator)
        toolbar.addWidget(self.btn_mode_auto)

        self.btn_mode_preview_album = QPushButton("👁️ Previsualizar Álbum")
        self.btn_mode_preview_album.setToolTip("Ver maqueta del mini álbum completo con portada, lomo, contra y disco")
        self.btn_mode_preview_album.clicked.connect(lambda: self._set_center_view_mode("album"))
        toolbar.addWidget(self.btn_mode_preview_album)

        toolbar.addSeparator()

        # Indicador de Perfil Activo
        toolbar.addWidget(QLabel(" Perfil Activo: "))
        self.lbl_active_profile = QLabel(f"<b>{self.profile.name}</b>")
        self.lbl_active_profile.setStyleSheet("color: #2563EB; font-size: 13px;")
        toolbar.addWidget(self.lbl_active_profile)

        self.btn_change_profile = QPushButton("Cambiar Perfil...")
        self.btn_change_profile.clicked.connect(self._open_profile_manager)
        toolbar.addWidget(self.btn_change_profile)

        toolbar.addSeparator()

        # Acciones clave
        btn_calib = QPushButton("📐 Calibrar (50x50mm)")
        btn_calib.clicked.connect(self._open_calibration)
        toolbar.addWidget(btn_calib)

        toolbar.addSeparator()

        btn_print = QPushButton("📄 Organizar Hoja...")
        btn_print.clicked.connect(self._open_print_layout)
        toolbar.addWidget(btn_print)

        btn_quick_pdf = QPushButton("🚀 Exportar PDF Inmediato")
        btn_quick_pdf.setObjectName("primaryButton")
        btn_quick_pdf.setStyleSheet("font-weight: bold; background-color: #2563EB; color: white;")
        btn_quick_pdf.clicked.connect(self._quick_export_pdf)
        toolbar.addWidget(btn_quick_pdf)

    def _sync_profile_to_project(self):
        """Sincroniza las medidas del perfil activo al proyecto sin borrar imágenes."""
        self.lbl_active_profile.setText(f"<b>{self.profile.name}</b>")
        self._update_sections_list()
        self._refresh_active_views()
        self.status_bar.showMessage(f"Perfil activo: {self.profile.name} | Listo.")

    def _update_sections_list(self):
        """Actualiza la lista visual de secciones con sus medidas y estado."""
        self.list_sections.blockSignals(True)
        self.list_sections.clear()

        sections = [
            ("portada", "1. Portada frontal", self.profile.portada),
            ("lomo", "2. Lomo / lateral", self.profile.lomo),
            ("contraportada", "3. Contraportada exterior", self.profile.contraportada),
            ("interior_contraportada", "4. Fondo bandeja (interior)", self.profile.interior_contraportada),
            ("cd", "5. Etiqueta CD circular", self.profile.cd),
            ("interior", "6. Interior / libreto", self.profile.interior),
            ("lomo_secundario", "7. Lomo secundario (opcional)", self.profile.lomo_secundario),
            ("album_completo", "👁️ 8. Previsualizar Mini Álbum", None),
        ]

        for key, name, dim in sections:
            if key == "album_completo":
                text = f"{name}\nMaqueta frontal, lomo, contra y disco"
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setForeground(QColor("#1D4ED8"))
                self.list_sections.addItem(item)
                continue

            piece = self.project.get_piece(key)
            w = piece.custom_width_mm or dim.width_mm
            h = piece.custom_height_mm or dim.height_mm

            img_status = "🖼️ Con foto" if piece.image_path else "⚪ Vacía"
            print_status = "🖨️ Imprime" if piece.enabled_for_print else "❌ No imprime"

            if key == "cd":
                text = f"{name}\nØ {w:.1f} mm | {img_status} | {print_status}"
            else:
                text = f"{name}\n{w:.1f} × {h:.1f} mm | {img_status} | {print_status}"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.list_sections.addItem(item)

        self.list_sections.blockSignals(False)

    def _set_center_view_mode(self, mode: str):
        """Alterna entre modo de ajuste con guías, vista previa limpia o maqueta de conjunto."""
        if mode == "edit":
            self.stack_center.setCurrentIndex(0)
            self.canvas_view.set_preview_mode(False)
            self.btn_view_edit.setChecked(True)
            self.btn_view_clean.setChecked(False)
            self.btn_view_full.setChecked(False)
            self.status_bar.showMessage("Modo Encuadre y Corte — Mueva la foto con el ratón o use la rueda para zoom.", 3500)
        elif mode == "clean":
            self.stack_center.setCurrentIndex(0)
            self.canvas_view.set_preview_mode(True)
            self.btn_view_clean.setChecked(True)
            self.btn_view_edit.setChecked(False)
            self.btn_view_full.setChecked(False)
            self.status_bar.showMessage("Vista Previa Limpia — Visualización fiel de la pieza final cortada e impresa.", 3500)
        elif mode == "album":
            self.stack_center.setCurrentIndex(1)
            self.composite_view.set_data(self.project, self.profile)
            self.btn_view_full.setChecked(True)
            self.btn_view_edit.setChecked(False)
            self.btn_view_clean.setChecked(False)
            self.status_bar.showMessage("Previsualización de Conjunto — Portada, Lomo, Contraportada y Disco CD.", 3500)

    def _select_piece(self, piece_key: str):
        self.current_piece_key = piece_key
        # Si estábamos en vista de conjunto, volver a mostrar la pieza individual
        if self.stack_center.currentIndex() == 1:
            self.stack_center.setCurrentIndex(0)
            if self.btn_view_full.isChecked():
                self.btn_view_edit.setChecked(True)
                self.btn_view_full.setChecked(False)
                self.canvas_view.set_preview_mode(False)

        # Seleccionar en la lista
        for i in range(self.list_sections.count()):
            item = self.list_sections.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == piece_key:
                self.list_sections.blockSignals(True)
                self.list_sections.setCurrentRow(i)
                self.list_sections.blockSignals(False)
                break

        piece = self.project.get_piece(piece_key)
        self.canvas_view.set_data(piece, self.profile, piece_key)
        self.properties_dock.set_data(self.project, self.profile, piece_key)

        dim = self.profile.get_piece_dimension(piece_key)
        if dim:
            w = piece.custom_width_mm or dim.width_mm
            h = piece.custom_height_mm or dim.height_mm
            self.status_bar.showMessage(f"Editando '{piece_key}' — Dimensiones físicas: {w:.1f} × {h:.1f} mm")

    def _on_section_selected(self, row: int):
        if row < 0:
            return
        item = self.list_sections.item(row)
        key = item.data(Qt.ItemDataRole.UserRole)
        if key == "album_completo":
            self._set_center_view_mode("album")
        else:
            if self.stack_center.currentIndex() == 1:
                # Si estábamos en maqueta completa, restaurar la vista individual
                self._set_center_view_mode("clean" if self.btn_view_clean.isChecked() else "edit")
            self._select_piece(key)

    def _show_composite_view(self):
        self._set_center_view_mode("album")

    def _on_switch_to_manual(self):
        self._set_center_view_mode("edit")
        self._select_piece(self.current_piece_key)

    def _on_canvas_crop_changed(self, zoom: float, pan_x: float, pan_y: float):
        self.properties_dock.update_crop_sliders(zoom, pan_x, pan_y)

    def _on_image_dropped(self, file_path: str):
        self.properties_dock.set_image_file(file_path)

    def _on_piece_updated(self):
        self._update_sections_list()
        self.canvas_view.refresh_preview()
        self.composite_view.set_data(self.project, self.profile)

    def _on_nfc_updated(self):
        pass

    def _refresh_active_views(self):
        piece = self.project.get_piece(self.current_piece_key)
        self.canvas_view.set_data(piece, self.profile, self.current_piece_key)
        self.composite_view.set_data(self.project, self.profile)
        self.properties_dock.set_data(self.project, self.profile, self.current_piece_key)

    # Diálogos y Modos
    def _open_profile_manager(self):
        dlg = ProfileManagerDialog(self.repo, self.profile.id, self)
        dlg.profileChanged.connect(self._on_profile_changed_from_dialog)
        dlg.exec()

    def _on_profile_changed_from_dialog(self, profile_id: str):
        p = self.repo.get_by_id(profile_id)
        if p:
            self.profile = p
            self.project.profile_id = profile_id
            self.repo.set_active_profile_id(profile_id)
            self._sync_profile_to_project()

    def _open_quick_generator(self):
        dlg = QuickGeneratorDialog(self.repo, self.project, self)
        dlg.projectGenerated.connect(self._on_project_generated)
        dlg.exec()

    def _on_project_generated(self, generated_proj: Project):
        self.project = generated_proj
        p = self.repo.get_by_id(generated_proj.profile_id)
        if p:
            self.profile = p
            self.repo.set_active_profile_id(p.id)
        self._sync_profile_to_project()
        self._select_piece("portada")
        QMessageBox.information(
            self, "Mini Álbum Generado",
            f"Se ha generado el proyecto '{self.project.name}'.\n"
            "Puede ajustar manualmente los encuadres, textos o dimensiones antes de imprimir."
        )

    def _open_print_layout(self):
        dlg = PrintLayoutDialog(self.project, self.profile, self)
        dlg.exec()

    def _open_calibration(self):
        dlg = CalibrationDialog(self)
        dlg.exec()

    def _quick_export_pdf(self):
        """Abre el diálogo para adecuar cantidad de mini álbumes y exportar PDF multipágina a escala 100%."""
        dlg = QuickExportDialog(self.project, self.profile, self)
        dlg.exec()

    # Gestión de Proyectos
    def _on_new_project(self):
        self.project = Project()
        self.project.profile_id = self.profile.id
        self._sync_profile_to_project()
        self._select_piece("portada")
        self.setWindowTitle("NFCito Studio — Mini Álbumes y Llaveros NFC [Nuevo Álbum]")

    def _on_open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Abrir Proyecto NFCito", "", "Proyectos NFCito (*.nfcito *.json)"
        )
        if not file_path:
            return

        try:
            proj, missing = ProjectRepository.load_project(file_path)
            self.project = proj
            p = self.repo.get_by_id(proj.profile_id)
            if p:
                self.profile = p
                self.repo.set_active_profile_id(p.id)
            self._sync_profile_to_project()
            self._select_piece("portada")
            self.setWindowTitle(f"NFCito Studio — {self.project.name} [{Path(file_path).name}]")

            if missing:
                QMessageBox.warning(
                    self, "Imágenes No Encontradas",
                    "Algunas imágenes del proyecto no se pudieron localizar:\n- " + "\n- ".join(missing)
                )
        except Exception as e:
            QMessageBox.critical(self, "Error al abrir proyecto", f"No se pudo cargar el archivo:\n{e}")

    def _on_save_project(self):
        if self.project.file_path and os.path.exists(self.project.file_path):
            try:
                ProjectRepository.save_project(self.project, self.project.file_path, bundle_assets=True)
                self.status_bar.showMessage(f"Proyecto guardado con éxito en: {self.project.file_path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Error al guardar", str(e))
        else:
            self._on_save_project_as()

    def _on_save_project_as(self):
        suggested = f"{self.project.name.replace(' ', '_')}.nfcito"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Proyecto Como", suggested, "Proyectos NFCito (*.nfcito)"
        )
        if not file_path:
            return

        try:
            target = ProjectRepository.save_project(self.project, file_path, bundle_assets=True)
            self.setWindowTitle(f"NFCito Studio — {self.project.name} [{Path(target).name}]")
            self.status_bar.showMessage(f"Proyecto guardado con éxito en: {target}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _on_duplicate_project(self):
        if not self.project.file_path:
            QMessageBox.warning(self, "Aviso", "Primero guarde el proyecto actual antes de duplicarlo.")
            return

        new_path, _ = QFileDialog.getSaveFileName(
            self, "Duplicar Proyecto En", f"{self.project.name}_Copia.nfcito", "Proyectos NFCito (*.nfcito)"
        )
        if new_path:
            try:
                target = ProjectRepository.duplicate_project(self.project.file_path, f"{self.project.name} (Copia)", new_path)
                QMessageBox.information(self, "Proyecto Duplicado", f"Se creó una copia en:\n{target}")
            except Exception as e:
                QMessageBox.critical(self, "Error al duplicar", str(e))

    def _show_print_guide(self):
        msg = (
            "<h3>Guía de Impresión a Escala Real (100%)</h3>"
            "<p>Para que los mini álbumes encajen con exactitud en los estuches de acrílico:</p>"
            "<ol>"
            "<li><b>Imprima siempre la página de calibración inicial (50 × 50 mm).</b></li>"
            "<li>Verifique con una regla física que el cuadrado mida exactamente 5.0 cm.</li>"
            "<li><b>Desactive</b> las casillas <i>'Ajustar a página'</i> o <i>'Fit to printable area'</i> en su lector PDF.</li>"
            "<li>Utilice papel fotográfico brillante o satinado de 180 a 240 g/m² para las portadas.</li>"
            "<li>Para la etiqueta del CD, use papel fotográfico autoadhesivo (sticker).</li>"
            "</ol>"
        )
        QMessageBox.information(self, "Guía de Impresión — NFCito Studio", msg)

    def _show_about(self):
        msg = (
            "<h3>NFCito Studio v1.0</h3>"
            "<p>Aplicación de precisión para diseño e impresión de mini álbumes personalizados para llaveros con mini estuches de CD y etiquetas NFC.</p>"
            "<p>Desarrollado para Windows con Python, PySide6, Pillow y ReportLab.</p>"
        )
        QMessageBox.about(self, "Acerca de NFCito Studio", msg)
