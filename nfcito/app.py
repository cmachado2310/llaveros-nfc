"""
Punto de entrada para la aplicación de escritorio NFCito Studio.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from nfcito.gui.main_window import MainWindow
from nfcito.gui.styles import MODERN_STYLE
from nfcito.storage.profile_repo import ProfileRepository

def main():
    # Habilitar soporte High DPI
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("NFCito Studio")
    app.setOrganizationName("NFCito")
    app.setStyleSheet(MODERN_STYLE)

    # Inicializar persistencia de perfiles
    repo = ProfileRepository()

    window = MainWindow(repo)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
