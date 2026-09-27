import logging
from typing import Optional

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

logger = logging.getLogger(__name__)


class CameraAudioPlayer(QObject):
    """
    Player de áudio em tempo real para stream RTSP da câmera.
    
    Utiliza o backend multimídia do Qt6 (QMediaPlayer + QAudioOutput) para decodificar
    apenas a trilha sonora (AAC, G.711, PCM, etc.) sem consumo desnecessário de CPU com vídeo.
    """

    muted_changed = pyqtSignal(bool)         # True se mutado, False se com som ativo
    volume_changed = pyqtSignal(int)          # Volume de 0 a 100
    playback_state_changed = pyqtSignal(str)  # "playing", "stopped", "error"

    def __init__(self, rtsp_url: str = "", parent: Optional[QObject] = None):
        super().__init__(parent)
        self._rtsp_url = rtsp_url
        self._volume = 80          # Padrão: 80%
        self._is_muted = True      # Por padrão inicia mutado
        self._is_playing = False

        self._player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        self._init_player()

    def _init_player(self):
        try:
            self._player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_output)
            self._audio_output.setVolume(self._volume / 100.0)
            self._audio_output.setMuted(self._is_muted)

            self._player.errorOccurred.connect(self._on_player_error)
            self._player.playbackStateChanged.connect(self._on_state_changed)
        except Exception as e:
            logger.warning(f"[CameraAudioPlayer] Falha ao inicializar subsistema de áudio Qt: {e}")
            self._player = None
            self._audio_output = None

    def _on_player_error(self, error, error_string: str):
        logger.warning(f"[CameraAudioPlayer] Erro no player ({self._rtsp_url}): {error_string}")
        self.playback_state_changed.emit("error")

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._is_playing = True
            self.playback_state_changed.emit("playing")
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self._is_playing = False
            self.playback_state_changed.emit("stopped")

    def set_url(self, new_url: str):
        """Atualiza a URL do fluxo de áudio."""
        if self._rtsp_url != new_url:
            self._rtsp_url = new_url
            if self._is_playing and not self._is_muted:
                self.play()

    def is_muted(self) -> bool:
        return self._is_muted

    def is_playing(self) -> bool:
        return self._is_playing

    def get_volume(self) -> int:
        return self._volume

    def set_volume(self, volume: int):
        """Ajusta o volume entre 0 e 100%."""
        vol = max(0, min(100, volume))
        self._volume = vol
        if self._audio_output:
            self._audio_output.setVolume(vol / 100.0)
        self.volume_changed.emit(vol)

    def set_muted(self, muted: bool):
        """Define se o som está mutado."""
        if self._is_muted == muted:
            return

        self._is_muted = muted
        if self._audio_output:
            self._audio_output.setMuted(muted)

        self.muted_changed.emit(self._is_muted)

        if not muted:
            self.play()
        else:
            self.stop()

    def toggle_mute(self) -> bool:
        """Alterna estado de mudo e retorna o novo estado (True = mutado, False = ativo)."""
        self.set_muted(not self._is_muted)
        return self._is_muted

    def play(self):
        """Inicia a reprodução do fluxo sonoro."""
        if not self._player or not self._rtsp_url:
            return

        try:
            if self._is_muted:
                self._is_muted = False
                if self._audio_output:
                    self._audio_output.setMuted(False)
                self.muted_changed.emit(False)

            if self._audio_output:
                self._audio_output.setVolume(self._volume / 100.0)

            url = QUrl(self._rtsp_url)
            self._player.setSource(url)
            self._player.play()
            self._is_playing = True
            self.playback_state_changed.emit("playing")
            logger.info(f"[CameraAudioPlayer] Áudio iniciado para {self._rtsp_url}")
        except Exception as e:
            logger.error(f"[CameraAudioPlayer] Erro ao iniciar áudio: {e}")
            self.playback_state_changed.emit("error")

    def stop(self):
        """Interrompe a reprodução de áudio e libera recursos de rede."""
        if not self._player:
            return

        try:
            self._player.stop()
            self._player.setSource(QUrl())
            self._is_playing = False
            self.playback_state_changed.emit("stopped")
        except Exception as e:
            logger.debug(f"[CameraAudioPlayer] Erro ao parar áudio: {e}")
