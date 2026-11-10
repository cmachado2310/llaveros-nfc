"""
Diálogo de calibración física e instrucciones de impresión para NFCito Studio.
Permite exportar una hoja con un recuadro de prueba de 50.0 x 50.0 mm.
"""
from pathlib import Path
import os
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
)
from reportlab.pdfgen import canvas
from nfcito.core.pdf_exporter import PDFExporter
from nfcito.core.units import mm_to_pt

class CalibrationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Guía de Calibración de Impresión (50 × 50 mm) — NFCito Studio")
        self.setFixedSize(580, 420)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("📐 Calibración de Escala 100% para Mini Estuches")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1E293B;")
        layout.addWidget(title)

        info = QLabel(
            "Los mini estuches de acrílico para llaveros tienen tolerancias muy ajustadas: "
            "una desviación de solo 1 mm puede hacer que la portada no entre en la ranura o quede suelta.<br><br>"
            "Muchos visores de PDF e impresoras vienen configurados por defecto con '<b>Ajustar a página</b>' "
            "o '<b>Reducir para ajustar</b>', lo que reduce el tamaño un 3% a 6% y arruina las medidas físicas.<br><br>"
            "<b>Pasos para calibrar:</b><br>"
            "1. Haga clic en <i>'Generar Hoja de Calibración PDF'</i>.<br>"
            "2. En su programa de impresión, seleccione obligatoriamente <b>Tamaño Real (100%)</b>.<br>"
            "3. Con una regla o calibre físico, mida el recuadro impreso.<br>"
            "4. Debe medir <b>exactamente 50.0 × 50.0 mm</b>. Si es así, su impresora está lista."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #334155; line-height: 140%;")
        layout.addWidget(info)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.accept)

        self.btn_export_calib = QPushButton("Generar Hoja de Calibración PDF...")
        self.btn_export_calib.setObjectName("primaryButton")
        self.btn_export_calib.clicked.connect(self._on_export_calib)

        btn_box.addWidget(self.btn_close)
        btn_box.addWidget(self.btn_export_calib)
        layout.addLayout(btn_box)

    def _on_export_calib(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Hoja de Calibración",
            "NFCito_Calibracion_50x50mm.pdf",
            "Archivos PDF (*.pdf)"
        )
        if not file_path:
            return

        try:
            pw_pt = mm_to_pt(210.0)
            ph_pt = mm_to_pt(297.0)
            pdf_doc = canvas.Canvas(file_path, pagesize=(pw_pt, ph_pt))
            pdf_doc.setTitle("NFCito Studio - Hoja de Calibracion 50x50mm")
            PDFExporter._render_calibration_page(pdf_doc, pw_pt, ph_pt)
            pdf_doc.showPage()
            pdf_doc.save()

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Hoja de Calibración Generada")
            msg.setText(f"La hoja de calibración se guardó con éxito en:\n{file_path}")
            btn_open = msg.addButton("Abrir PDF", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            if msg.clickedButton() == btn_open:
                os.startfile(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar la hoja de calibración:\n{e}")
