import sys
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from myipcams.ui.main_window import MainWindow
from myipcams.ui.assets import get_app_icon


def main():
    parser = argparse.ArgumentParser(description="MyIPCams - Visualizador de Câmeras IP com Rastreamento Dinâmico de IP")
    parser.add_argument("--config", help="Caminho personalizado para o arquivo de configuração cameras.json", default=None)
    args = parser.parse_args()

    # Otimizações de renderização no Qt6
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # No Windows, define o AppUserModelID para exibir o ícone correto na barra de tarefas
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("myipcams.app.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("MyIPCams")
    app.setOrganizationName("MyIPCams")
    app.setDesktopFileName("myipcams")
    app.setWindowIcon(get_app_icon())

    # Define família de fontes padrão estável para evitar falhas do fontconfig no Linux
    font = QFont()
    font.setFamilies(["DejaVu Sans", "Segoe UI", "SF Pro Text", "Ubuntu", "Noto Sans", "Arial", "sans-serif"])
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow(config_path=args.config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
