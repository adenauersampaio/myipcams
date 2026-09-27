import os
import time
from typing import Optional
import cv2
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage

# Configuração global de captura de streaming para OpenCV / FFmpeg
# - rtsp_transport;tcp: força TCP para evitar corrupção por perda de pacotes UDP
# - fflags;nobuffer: elimina buffering de vídeo para visualização em tempo real (latência mínima)
# - flags;low_delay: reduz tempo de decodificação interna
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
    "rtsp_transport;tcp|fflags;nobuffer|flags;low_delay|stimeout;3000000"
)


class StreamWorker(QObject):
    """
    Worker que roda a captura RTSP contínua em thread separada com auto-recuperação.
    Emite sinais para a interface com os frames decodificados e status de conexão.
    """
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)   # "online", "reconnecting", "offline", "error"
    stats_updated = pyqtSignal(float, int, int)  # fps, width, height

    def __init__(self, rtsp_url: str):
        super().__init__()
        self._rtsp_url = rtsp_url
        self._running = False
        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame: Optional[cv2.typing.MatLike] = None
        self._snapshot_request: Optional[str] = None
        self._url_changed = False

    def set_url(self, new_url: str):
        """Atualiza a URL RTSP (usado quando o IP é atualizado pelo tracker)."""
        if self._rtsp_url != new_url:
            self._rtsp_url = new_url
            self._url_changed = True

    def request_snapshot(self, filepath: str):
        """Solicita gravação do próximo frame capturado em arquivo de imagem."""
        self._snapshot_request = filepath

    def stop(self):
        """Sinaliza para a thread interromper a execução sem interferir diretamente no objeto de captura."""
        self._running = False

    def run(self):
        self._running = True
        fps_counter = 0
        last_fps_time = time.time()
        current_fps = 0.0

        while self._running:
            if not self._rtsp_url:
                self.status_changed.emit("offline")
                time.sleep(1.0)
                continue

            self.status_changed.emit("reconnecting")
            self._url_changed = False
            
            # Abre o fluxo RTSP com proteção rigorosa e timeout ágil
            try:
                params = []
                if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                    params.extend([cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2500])
                if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                    params.extend([cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2500])

                if params:
                    self._cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG, params)
                else:
                    self._cap = cv2.VideoCapture(self._rtsp_url, cv2.CAP_FFMPEG)

                if self._cap and self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                else:
                    if self._cap:
                        try:
                            self._cap.release()
                        except Exception:
                            pass
                    self._cap = None
            except Exception as e:
                print(f"[StreamWorker] Erro ao abrir VideoCapture: {e}")
                self._cap = None

            if not self._cap or not self._cap.isOpened():
                self.status_changed.emit("offline")
                # Aguarda antes de tentar reconectar
                for _ in range(10):
                    if not self._running or self._url_changed:
                        break
                    time.sleep(0.3)
                continue

            self.status_changed.emit("online")
            last_frame_time = time.time()

            while self._running:
                if self._url_changed:
                    break

                ret, frame = self._cap.read()

                if not ret or frame is None:
                    # Timeout ou queda de conexão do stream
                    if time.time() - last_frame_time > 3.0:
                        print(f"[StreamWorker] Queda no stream ({self._rtsp_url}), reconectando...")
                        self.status_changed.emit("reconnecting")
                        break
                    time.sleep(0.01)
                    continue

                last_frame_time = time.time()
                self._current_frame = frame

                # Tratamento de snapshot se solicitado
                if self._snapshot_request:
                    try:
                        cv2.imwrite(self._snapshot_request, frame)
                        print(f"[StreamWorker] Snapshot salvo em: {self._snapshot_request}")
                    except Exception as e:
                        print(f"[StreamWorker] Erro ao salvar snapshot: {e}")
                    finally:
                        self._snapshot_request = None

                # Cálculo de FPS
                fps_counter += 1
                now = time.time()
                if now - last_fps_time >= 1.0:
                    current_fps = fps_counter / (now - last_fps_time)
                    h, w = frame.shape[:2]
                    self.stats_updated.emit(current_fps, w, h)
                    fps_counter = 0
                    last_fps_time = now

                # Conversão de BGR (OpenCV) para RGB e empacotamento em QImage
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_img = QImage(
                    rgb_frame.data,
                    w,
                    h,
                    bytes_per_line,
                    QImage.Format.Format_RGB888
                ).copy()  # .copy() garante cópia independente de memória para o Qt

                self.frame_ready.emit(q_img)

                # Pequena pausa para cooperar com a CPU mantendo ~30fps
                time.sleep(0.005)

            if self._cap:
                self._cap.release()
                self._cap = None

        self.status_changed.emit("offline")
