"""
Campo de entrada de senha com botão de alternância de visibilidade ('olho').
"""
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QToolButton, QWidget

from myipcams.ui.assets import get_eye_icon


class PasswordLineEdit(QLineEdit):
    """
    Campo de texto customizado para senhas com botão de alternância
    de visibilidade (ícone de olho) integrado na extremidade direita.
    """

    def __init__(self, placeholder: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        if placeholder:
            self.setPlaceholderText(placeholder)

        self._icon_show = get_eye_icon(visible=False)
        self._icon_hide = get_eye_icon(visible=True)

        self._toggle_action = self.addAction(
            self._icon_show,
            QLineEdit.ActionPosition.TrailingPosition,
        )
        self._toggle_action.setToolTip("Mostrar senha")
        self._toggle_action.triggered.connect(self.toggle_password_visibility)

        self._update_tool_button_cursor()

    def _update_tool_button_cursor(self) -> None:
        """Garante que o botão interno de alternância exiba o cursor de mão/clique."""
        tb = self.findChild(QToolButton)
        if tb:
            tb.setCursor(Qt.CursorShape.PointingHandCursor)

    def showEvent(self, event) -> None:
        """Ao exibir o widget, reforça o cursor do botão caso o Qt tenha recriado os filhos."""
        super().showEvent(event)
        self._update_tool_button_cursor()

    def is_password_visible(self) -> bool:
        """Retorna True se a senha estiver sendo exibida em texto claro."""
        return self.echoMode() == QLineEdit.EchoMode.Normal

    def set_password_visible(self, visible: bool) -> None:
        """Define explicitamente se a senha deve estar visível ou oculta."""
        pos = self.cursorPosition()
        if visible:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
            self._toggle_action.setIcon(self._icon_hide)
            self._toggle_action.setToolTip("Ocultar senha")
        else:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            self._toggle_action.setIcon(self._icon_show)
            self._toggle_action.setToolTip("Mostrar senha")
        self.setCursorPosition(pos)

    def toggle_password_visibility(self) -> None:
        """Alterna entre ocultar (dots) e exibir a senha em texto claro."""
        self.set_password_visible(not self.is_password_visible())
