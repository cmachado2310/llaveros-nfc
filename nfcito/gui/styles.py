"""
Estilos visuales modernos y limpios para NFCito Studio en Qt / PySide6.
"""

MODERN_STYLE = """
/* Estilo global moderno */
QMainWindow, QDialog {
    background-color: #F4F5F7;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif;
    color: #1E293B;
}

QWidget {
    font-size: 13px;
}

/* Barra de herramientas */
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    padding: 6px 12px;
    spacing: 8px;
}

QToolButton {
    background-color: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    color: #1E293B;
}

QToolButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}

QToolButton:pressed, QToolButton:checked {
    background-color: #E2E8F0;
    border-color: #64748B;
}

/* Botones principales */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    color: #1E293B;
}

QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #94A3B8;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1.5px solid #1D4ED8;
    font-weight: 600;
}

QPushButton:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border-color: #E2E8F0;
}

/* Botón de acción primaria / exportación */
QPushButton#primaryButton, QToolButton#primaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 600;
}

QPushButton#primaryButton:hover, QToolButton#primaryButton:hover {
    background-color: #1D4ED8;
}

QPushButton#primaryButton:pressed, QToolButton#primaryButton:pressed {
    background-color: #1E40AF;
}

/* Botón de modo o acento */
QPushButton#accentButton {
    background-color: #0D9488;
    color: #FFFFFF;
    border: 1px solid #0F766E;
    font-weight: 600;
}

QPushButton#accentButton:hover {
    background-color: #0F766E;
}

/* Grupos y paneles */
QGroupBox {
    font-weight: 600;
    color: #334155;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 14px;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #2563EB;
}

/* Campos de texto y spinboxes con señalización visual de selección */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 8px;
    color: #1E293B;
    font-size: 13px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QTextEdit:hover, QPlainTextEdit:hover {
    border-color: #94A3B8;
}

/* ESTADO SELECCIONADO / FOCO ACTIVO: Borde azul vibrante de 2px y fondo suave */
QLineEdit:focus,
QSpinBox:focus,
QSpinBox:focus-within,
QSpinBox QLineEdit:focus,
QDoubleSpinBox:focus,
QDoubleSpinBox:focus-within,
QDoubleSpinBox QLineEdit:focus,
QComboBox:focus,
QTextEdit:focus,
QPlainTextEdit:focus {
    border: 2px solid #2563EB;
    background-color: #F0F7FF;
    color: #0F172A;
}

/* Botones de incremento y decremento de spinboxes */
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #F1F5F9;
    border: 1px solid #CBD5E1;
    width: 18px;
    border-radius: 3px;
    margin: 1px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #DBEAFE;
    border-color: #2563EB;
}

/* Casillas de verificación (Checkboxes) con señalización clara */
QCheckBox {
    spacing: 8px;
    color: #1E293B;
    font-weight: 500;
}

QCheckBox:focus {
    color: #1D4ED8;
    font-weight: 600;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #94A3B8;
    border-radius: 4px;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #2563EB;
    background-color: #EFF6FF;
}

QCheckBox::indicator:focus {
    border: 2px solid #2563EB;
    background-color: #EFF6FF;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #1D4ED8;
}

/* Botones conmutables (Checked / Seleccionados) */
QPushButton:checked, QToolButton:checked {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 2px solid #1D4ED8;
    font-weight: bold;
}

QPushButton:focus, QToolButton:focus {
    border: 2px solid #2563EB;
}

/* Listas y árboles */
QListWidget, QTreeWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
    margin-bottom: 2px;
}

QListWidget::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
    font-weight: 600;
    border: 1px solid #BFDBFE;
}

QListWidget::item:hover {
    background-color: #F8FAFC;
}

/* Pestañas */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 500;
    color: #64748B;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    font-weight: 600;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #CBD5E1;
    height: 6px;
    background: #E2E8F0;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #3B82F6;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #2563EB;
    border: 2px solid #FFFFFF;
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}

/* Barra de estado */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 12px;
}
"""
