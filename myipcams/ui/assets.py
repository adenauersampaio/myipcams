import os
import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


_SVG_EYE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
  <circle cx="12" cy="12" r="3"/>
</svg>"""

_SVG_EYE_OFF = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
  <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/>
  <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/>
  <line x1="2" y1="2" x2="22" y2="22"/>
</svg>"""


def get_project_root() -> Path:
    """Retorna o diretório raiz do projeto myipcams."""
    return Path(__file__).resolve().parent.parent.parent


def get_asset_path(filename: str) -> Optional[Path]:
    """
    Busca o caminho absoluto de um arquivo de asset procurando em múltiplos locais comuns:
    1. Raiz do projeto / assets
    2. Pacote myipcams / assets (caso empacotado)
    3. Diretório padrão XDG do usuário (~/.local/share/myipcams/assets)
    4. Diretório compartilhado do sistema (/usr/share/myipcams/assets)
    5. Diretório de dados no Windows (%LOCALAPPDATA%/myipcams/assets)
    6. Diretório de dados no macOS (~/Library/Application Support/myipcams/assets)
    """
    candidates = [
        get_project_root() / "assets" / filename,
        Path(__file__).resolve().parent.parent / "assets" / filename,
        Path.home() / ".local" / "share" / "myipcams" / "assets" / filename,
        Path("/usr/share/myipcams/assets") / filename,
    ]

    # Windows AppData
    if sys.platform.startswith("win"):
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            candidates.append(Path(local_appdata) / "myipcams" / "assets" / filename)

    # macOS Application Support
    if sys.platform == "darwin":
        candidates.append(Path.home() / "Library" / "Application Support" / "myipcams" / "assets" / filename)

    candidates.append(Path("assets") / filename)

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None



def get_app_icon() -> QIcon:
    """
    Retorna o QIcon do aplicativo MyIPCams com múltiplas resoluções
    para renderização nítida em qualquer DPI/resolução de tela.
    """
    icon = QIcon()

    # Tenta carregar ícones PNG gerados em várias resoluções
    sizes = [16, 24, 32, 48, 64, 128, 256, 512]
    loaded_any = False
    for sz in sizes:
        p = get_asset_path(f"icon_{sz}.png")
        if p and p.is_file():
            icon.addFile(str(p))
            loaded_any = True

    # Imagem principal PNG ou JPG
    for main_name in ["myipcams.png", "App_icon_for_MyIPCams_2K_20260927120318.jpg"]:
        p = get_asset_path(main_name)
        if p and p.is_file():
            icon.addFile(str(p))
            loaded_any = True

    return icon


def get_camera_animation_path() -> Optional[str]:
    """Retorna o caminho do GIF animado da câmera de segurança."""
    p = get_asset_path("Security_camera_pans_left_right_20260927120805.gif")
    return str(p) if p else None


def get_camera_video_path() -> Optional[str]:
    """Retorna o caminho do vídeo MP4 da câmera de segurança."""
    p = get_asset_path("Security_camera_pans_left_right_20260927120723.mp4")
    return str(p) if p else None


def get_eye_icon(visible: bool = False) -> QIcon:
    """
    Retorna o QIcon vetorial para alternar a exibição da senha.
    - visible=False: Ícone de olho aberto (ação: 'Mostrar senha').
    - visible=True: Ícone de olho com barra (ação: 'Ocultar senha').
    Gera múltiplas resoluções (16, 20, 24, 32px) com estados Normal (#94A3B8)
    e Active/Hover (#38BDF8) para nitidez total em telas HiDPI/Retina.
    """
    template = _SVG_EYE_OFF if visible else _SVG_EYE
    icon = QIcon()

    modes = [
        (QIcon.Mode.Normal, "#94A3B8"),
        (QIcon.Mode.Active, "#38BDF8"),
        (QIcon.Mode.Selected, "#FFFFFF"),
    ]

    for mode, color in modes:
        svg_bytes = template.format(color=color).encode("utf-8")
        renderer = QSvgRenderer(QByteArray(svg_bytes))
        for size in [16, 20, 24, 32]:
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pm, mode)

    return icon
