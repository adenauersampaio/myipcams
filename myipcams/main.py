import sys
import argparse
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
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


    window = MainWindow(config_path=args.config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
