"""
Organizador de hojas de impresión y exportador de documentos PDF.
Permite seleccionar tamaño de papel, distribuir piezas, configurar cantidades,
previsualizar páginas completas y verificar márgenes y colisiones.
"""
from typing import Optional, List, Dict
import os
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QFileDialog,
    QMessageBox, QFrame, QScrollArea, QWidget, QSplitter
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPaintEvent

from nfcito.models.project import Project
from nfcito.models.profile import CaseProfile
from nfcito.models.sheet import LayoutResult, PlacedItem
from nfcito.core.layout_engine import LayoutEngine
from nfcito.core.pdf_exporter import PDFExporter
from nfcito.core.units import PAPER_SIZES_MM

class SheetPreviewWidget(QWidget):
    """Widget que dibuja la hoja de papel y las piezas colocadas a escala."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout_result: Optional[LayoutResult] = None
        self.page_index: int = 0

    def set_data(self, layout_res: Optional[LayoutResult], page_idx: int = 0):
        self.layout_result = layout_res
        self.page_index = page_idx
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor("#E2E8F0"))

        if not self.layout_result or not self.layout_result.pages or self.page_index >= len(self.layout_result.pages):
            painter.setFont(QFont("Segoe UI", 11))
            painter.setPen(QColor("#64748B"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No hay páginas de impresión para previsualizar.")
            return

        page = self.layout_result.pages[self.page_index]
        pw_mm = page.paper_width_mm
        ph_mm = page.paper_height_mm

        # Calcular factor de escala para que la hoja quepa en el widget con margen
        view_w = self.width() - 40
        view_h = self.height() - 40
        if view_w <= 10 or view_h <= 10:
            return

        scale = min(view_w / max(1.0, pw_mm), view_h / max(1.0, ph_mm))
        sheet_w = pw_mm * scale
        sheet_h = ph_mm * scale

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        sheet_rect = QRectF(cx - sheet_w / 2.0, cy - sheet_h / 2.0, sheet_w, sheet_h)

        # Sombra de la hoja de papel
        painter.setBrush(QColor(0, 0, 0, 30))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(sheet_rect.adjusted(4, 4, 4, 4))

        # Hoja blanca
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(sheet_rect)

        # Margen no imprimible de impresora (5mm, línea discontinua tenue)
        unprintable_px = 5.0 * scale
        unp_rect = sheet_rect.adjusted(unprintable_px, unprintable_px, -unprintable_px, -unprintable_px)
        painter.setPen(QPen(QColor("#FCA5A5"), 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(unp_rect)

        # Dibujar cada pieza en la hoja
        for item in page.items:
            ix = sheet_rect.x() + (item.x_mm * scale)
            iy = sheet_rect.y() + (item.y_mm * scale)
            iw = item.width_mm * scale
            ih = item.height_mm * scale
            i_rect = QRectF(ix, iy, iw, ih)

            # Fondo suave de pieza
            painter.setBrush(QColor("#EFF6FF"))
            painter.setPen(QPen(QColor("#3B82F6"), 1))

            if item.is_circular:
                painter.drawEllipse(i_rect)
                if item.has_inner_hole and item.inner_hole_mm > 0:
                    hole_px = item.inner_hole_mm * scale
                    h_rect = QRectF(i_rect.center().x() - hole_px / 2.0, i_rect.center().y() - hole_px / 2.0, hole_px, hole_px)
                    painter.setBrush(QColor("#FFFFFF"))
                    painter.setPen(QPen(QColor("#EF4444"), 1, Qt.PenStyle.SolidLine))
                    painter.drawEllipse(h_rect)
            else:
                painter.drawRect(i_rect)

            # Etiqueta
            painter.setFont(QFont("Segoe UI", 7))
            painter.setPen(QColor("#1E40AF"))
            txt = f"{item.display_name}\n{item.width_mm:.1f}×{item.height_mm:.1f}mm"
            painter.drawText(i_rect, Qt.AlignmentFlag.AlignCenter, txt)

        # Información inferior de la hoja
        painter.setFont(QFont("Segoe UI", 9))
        painter.setPen(QColor("#64748B"))
        info = f"Página {page.page_number} de {len(self.layout_result.pages)} | Papel: {page.paper_size_name} ({pw_mm:.1f} × {ph_mm:.1f} mm) | {len(page.items)} piezas"
        painter.drawText(10, self.height() - 10, info)

class PrintLayoutDialog(QDialog):
    def __init__(self, project: Project, profile: CaseProfile, parent=None):
        super().__init__(parent)
        self.project = project
        self.profile = profile
        self.setWindowTitle("Organización de Hoja de Impresión y Exportación PDF — NFCito Studio")
        self.setMinimumSize(950, 680)

        self.current_page_idx: int = 0
        self.layout_result: Optional[LayoutResult] = None

        self._init_ui()
        self._recalculate_layout()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel izquierdo: Opciones y controles de hoja (con scroll para pantallas pequeñas)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)

        # 1. Configuración de Papel
        grp_paper = QGroupBox("Formato de Papel")
        l_paper = QVBoxLayout(grp_paper)

        h_p1 = QHBoxLayout()
        h_p1.addWidget(QLabel("Tamaño:"))
        self.combo_paper = QComboBox()
        for name in PAPER_SIZES_MM.keys():
            self.combo_paper.addItem(name)
        idx = self.combo_paper.findText(self.project.print_layout.paper_size)
        if idx >= 0:
            self.combo_paper.setCurrentIndex(idx)
        self.combo_paper.currentIndexChanged.connect(self._recalculate_layout)
        h_p1.addWidget(self.combo_paper)
        l_paper.addLayout(h_p1)

        h_p2 = QHBoxLayout()
        h_p2.addWidget(QLabel("Orientación:"))
        self.combo_orient = QComboBox()
        self.combo_orient.addItem("Vertical (Portrait)", "portrait")
        self.combo_orient.addItem("Horizontal (Landscape)", "landscape")
        if self.project.print_layout.orientation == "landscape":
            self.combo_orient.setCurrentIndex(1)
        self.combo_orient.currentIndexChanged.connect(self._recalculate_layout)
        h_p2.addWidget(self.combo_orient)
        l_paper.addLayout(h_p2)

        # Márgenes y espacio
        h_m = QHBoxLayout()
        h_m.addWidget(QLabel("Margen hoja (mm):"))
        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(2.0, 30.0)
        self.spin_margin.setValue(self.project.print_layout.margin_mm)
        self.spin_margin.valueChanged.connect(self._recalculate_layout)
        h_m.addWidget(self.spin_margin)
        l_paper.addLayout(h_m)

        h_s = QHBoxLayout()
        h_s.addWidget(QLabel("Espacio piezas (mm):"))
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(1.0, 20.0)
        self.spin_spacing.setValue(self.project.print_layout.spacing_mm)
        self.spin_spacing.valueChanged.connect(self._recalculate_layout)
        h_s.addWidget(self.spin_spacing)
        l_paper.addLayout(h_s)

        left_layout.addWidget(grp_paper)

        # 2. Cantidades a Imprimir por Pieza
        grp_qty = QGroupBox("Cantidades a Imprimir (Repetición)")
        l_qty = QVBoxLayout(grp_qty)

        # Multiplicador rápido de juegos completos
        row_all = QHBoxLayout()
        row_all.addWidget(QLabel("<b>Juegos completos de álbum:</b>"))
        self.spin_all_sets = QSpinBox()
        self.spin_all_sets.setRange(1, 100)
        self.spin_all_sets.setValue(self.project.print_layout.quantities.get("portada", 1))
        self.spin_all_sets.setSuffix(" juego(s)")
        self.spin_all_sets.valueChanged.connect(self._on_all_sets_changed)
        row_all.addWidget(self.spin_all_sets)
        l_qty.addLayout(row_all)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #E2E8F0; margin: 4px 0;")
        l_qty.addWidget(sep)

        self.spin_quantities: Dict[str, QSpinBox] = {}
        piece_labels = [
            ("portada", "Portada frontal:"),
            ("contraportada", "Contraportada:"),
            ("interior_contraportada", "Fondo bandeja (interior):"),
            ("lomo", "Lomo principal:"),
            ("lomo_secundario", "Lomo secundario (opcional):"),
            ("cd", "Etiqueta CD:"),
            ("interior", "Interior / libreto:"),
        ]
        for key, lbl in piece_labels:
            row = QHBoxLayout()
            row.addWidget(QLabel(lbl))
            spin = QSpinBox()
            spin.setRange(0, 100)
            spin.setValue(self.project.print_layout.quantities.get(key, 1 if key != "lomo_secundario" else 0))
            spin.valueChanged.connect(self._recalculate_layout)
            self.spin_quantities[key] = spin
            row.addWidget(spin)
            l_qty.addLayout(row)

        lbl_auto_pages = QLabel("💡 Si la cantidad sobrepasa la hoja, se añaden hojas adicionales automáticamente sin encoger ni alterar las medidas reales.")
        lbl_auto_pages.setWordWrap(True)
        lbl_auto_pages.setStyleSheet("color: #2563EB; font-size: 11px; margin-top: 4px; font-style: italic;")
        l_qty.addWidget(lbl_auto_pages)

        left_layout.addWidget(grp_qty)

        # 3. Opciones de PDF y Precisión
        grp_pdf_opts = QGroupBox("Opciones de Impresión y Calibración")
        l_pdf = QVBoxLayout(grp_pdf_opts)

        self.chk_cut_lines = QCheckBox("Incluir líneas y marcas de corte discretas")
        self.chk_cut_lines.setChecked(self.project.print_layout.show_cut_lines)
        l_pdf.addWidget(self.chk_cut_lines)

        self.chk_calib = QCheckBox("Incluir página de calibración inicial (50 × 50 mm)")
        self.chk_calib.setChecked(self.project.print_layout.include_calibration)
        self.chk_calib.setStyleSheet("font-weight: 600; color: #1E293B;")
        l_pdf.addWidget(self.chk_calib)

        left_layout.addWidget(grp_pdf_opts)

        # Advertencias
        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setWordWrap(True)
        self.lbl_warnings.setStyleSheet("color: #DC2626; font-size: 11px; font-weight: 500;")
        left_layout.addWidget(self.lbl_warnings)

        left_layout.addStretch()

        # Botón Exportar PDF
        self.btn_export = QPushButton("Exportar PDF de Precisión...")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setFixedHeight(40)
        self.btn_export.clicked.connect(self._on_export_pdf)
        left_layout.addWidget(self.btn_export)

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # Panel derecho: Vista previa de páginas de impresión
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Controles de navegación de página
        h_nav = QHBoxLayout()
        self.btn_prev_page = QPushButton("◀ Página Anterior")
        self.btn_prev_page.clicked.connect(self._prev_page)
        self.lbl_page_counter = QLabel("Página 1 de 1")
        self.lbl_page_counter.setStyleSheet("font-weight: 600;")
        self.btn_next_page = QPushButton("Página Siguiente ▶")
        self.btn_next_page.clicked.connect(self._next_page)

        h_nav.addWidget(self.btn_prev_page)
        h_nav.addStretch()
        h_nav.addWidget(self.lbl_page_counter)
        h_nav.addStretch()
        h_nav.addWidget(self.btn_next_page)
        right_layout.addLayout(h_nav)

        self.preview_widget = SheetPreviewWidget()
        right_layout.addWidget(self.preview_widget, 1)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)

    def _on_all_sets_changed(self, val: int):
        for k, spin in self.spin_quantities.items():
            spin.blockSignals(True)
            spin.setValue(val)
            spin.blockSignals(False)
        self._recalculate_layout()

    def _recalculate_layout(self):
        # Actualizar configuración del proyecto
        self.project.print_layout.paper_size = self.combo_paper.currentText()
        self.project.print_layout.orientation = self.combo_orient.currentData()
        self.project.print_layout.margin_mm = self.spin_margin.value()
        self.project.print_layout.spacing_mm = self.spin_spacing.value()
        for k, spin in self.spin_quantities.items():
            self.project.print_layout.quantities[k] = spin.value()

        # Calcular distribución con LayoutEngine
        self.layout_result = LayoutEngine.compute_layout(
            project=self.project,
            profile=self.profile,
            paper_size_name=self.project.print_layout.paper_size,
            orientation=self.project.print_layout.orientation,
            margin_mm=self.project.print_layout.margin_mm,
            spacing_mm=self.project.print_layout.spacing_mm,
            quantities=self.project.print_layout.quantities,
        )

        total_pages = max(1, len(self.layout_result.pages))
        if self.current_page_idx >= total_pages:
            self.current_page_idx = total_pages - 1

        self.preview_widget.set_data(self.layout_result, self.current_page_idx)

        # Actualizar navegación con conteo de páginas y piezas totales a escala 100%
        page_suffix = f"({self.layout_result.total_items_placed} piezas a escala 100% real)"
        self.lbl_page_counter.setText(f"Página {self.current_page_idx + 1} de {total_pages} {page_suffix}")
        self.btn_prev_page.setEnabled(self.current_page_idx > 0)
        self.btn_next_page.setEnabled(self.current_page_idx < total_pages - 1)

        # Mostrar advertencias si existen
        all_warnings = self.layout_result.warnings[:]
        if self.layout_result.unplaced_items:
            all_warnings.append(f"Piezas no colocadas por exceder el papel: {', '.join(self.layout_result.unplaced_items)}")
        if all_warnings:
            self.lbl_warnings.setText("⚠️ " + "\n⚠️ ".join(all_warnings))
        else:
            self.lbl_warnings.setText("")

    def _prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.preview_widget.set_data(self.layout_result, self.current_page_idx)
            self.lbl_page_counter.setText(f"Página {self.current_page_idx + 1} de {len(self.layout_result.pages)}")
            self.btn_prev_page.setEnabled(self.current_page_idx > 0)
            self.btn_next_page.setEnabled(True)

    def _next_page(self):
        if self.layout_result and self.current_page_idx < len(self.layout_result.pages) - 1:
            self.current_page_idx += 1
            self.preview_widget.set_data(self.layout_result, self.current_page_idx)
            self.lbl_page_counter.setText(f"Página {self.current_page_idx + 1} de {len(self.layout_result.pages)}")
            self.btn_next_page.setEnabled(self.current_page_idx < len(self.layout_result.pages) - 1)
            self.btn_prev_page.setEnabled(True)

    def _on_export_pdf(self):
        if not self.layout_result or self.layout_result.total_items_placed == 0:
            QMessageBox.warning(self, "Aviso", "No hay piezas seleccionadas para exportar.")
            return

        suggested_name = f"{self.project.name.replace(' ', '_')}_impresion.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF de Impresión",
            suggested_name,
            "Archivos PDF (*.pdf)"
        )
        if not file_path:
            return

        try:
            out_file = PDFExporter.export_pdf(
                output_path=file_path,
                project=self.project,
                profile=self.profile,
                layout_result=self.layout_result,
                include_calibration=self.chk_calib.isChecked(),
                show_cut_lines=self.chk_cut_lines.isChecked(),
                dpi=300
            )

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Exportación Exitosa")
            msg.setText(f"El documento PDF se ha generado con precisión milimétrica en:\n{out_file}")
            btn_open = msg.addButton("Abrir PDF", QMessageBox.ButtonRole.ActionRole)
            btn_folder = msg.addButton("Abrir Carpeta", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)

            msg.exec()

            if msg.clickedButton() == btn_open:
                os.startfile(out_file)
            elif msg.clickedButton() == btn_folder:
                subprocess.Popen(f'explorer /select,"{out_file}"')

        except Exception as e:
            QMessageBox.critical(self, "Error de Exportación", f"No se pudo generar el archivo PDF:\n{e}")
