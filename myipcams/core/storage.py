import json
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional
from .camera import Camera


def get_default_config_dir() -> Path:
    """
    Retorna o diretório padrão de configurações conforme as convenções do sistema operacional:
    - Windows: %APPDATA%/myipcams ou ~/AppData/Roaming/myipcams
    - macOS: ~/Library/Application Support/myipcams
    - Linux/Unix: $XDG_CONFIG_HOME/myipcams ou ~/.config/myipcams
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        return Path(base) / "myipcams" if base else Path.home() / "AppData" / "Roaming" / "myipcams"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "myipcams"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        return Path(xdg) / "myipcams" if xdg else Path.home() / ".config" / "myipcams"



class CameraStorage:
    """Gerencia a persistência das câmeras em arquivo JSON de forma segura e atômica."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path:
            self.file_path = Path(config_path)
        else:
            config_dir = get_default_config_dir()
            config_dir.mkdir(parents=True, exist_ok=True)
            self.file_path = config_dir / "cameras.json"


    def load_cameras(self) -> List[Camera]:
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Camera.from_dict(item) for item in data.get("cameras", [])]
        except Exception as e:
            print(f"[Storage] Erro ao carregar câmeras: {e}")
            return []

    def save_cameras(self, cameras: List[Camera]) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"cameras": [cam.to_dict() for cam in cameras]}
            
            # Escrita atômica usando arquivo temporário no mesmo diretório
            dir_path = self.file_path.parent
            with tempfile.NamedTemporaryFile("w", dir=dir_path, delete=False, encoding="utf-8") as tf:
                json.dump(data, tf, indent=2, ensure_ascii=False)
                temp_name = tf.name
            
            os.replace(temp_name, self.file_path)
            return True
        except Exception as e:
            print(f"[Storage] Erro ao salvar câmeras: {e}")
            return False
