import os
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import tempfile
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QMimeData, QPointF
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from myipcams.core.camera import Camera
from myipcams.core.storage import CameraStorage
from myipcams.ui.camera_widget import CameraWidget
from myipcams.ui.camera_grid import CameraGrid

app = QApplication.instance() or QApplication([])


class TestCameraDragReorder(unittest.TestCase):

    def setUp(self):
        self.cam1 = Camera(id="cam-1", name="Garagem", current_ip="192.168.1.101", enabled=False)
        self.cam2 = Camera(id="cam-2", name="Portão", current_ip="192.168.1.102", enabled=False)
        self.cam3 = Camera(id="cam-3", name="Entrada", current_ip="192.168.1.103", enabled=False)

    def test_camera_widget_has_drag_elements(self):
        widget = CameraWidget(self.cam1)

        # Verifica presença da alça de arrasto e aceite de drops
        self.assertTrue(hasattr(widget, "drag_handle"))
        self.assertEqual(widget.drag_handle.text(), "⠿")
        self.assertTrue(widget.acceptDrops())

        # Verifica sinais necessários
        self.assertTrue(hasattr(widget, "reorder_requested"))
        self.assertTrue(hasattr(widget, "move_action_requested"))

        # Oculta alça ao maximizar e restaura ao desmaximizar
        widget.set_maximized_state(True)
        self.assertTrue(widget.drag_handle.isHidden())
        widget.set_maximized_state(False)
        self.assertFalse(widget.drag_handle.isHidden())

        widget.stop_stream()

    def test_camera_widget_drag_drop_events(self):
        widget = CameraWidget(self.cam1)

        mime_other = QMimeData()
        mime_other.setData("application/x-myipcams-camera-id", b"cam-2")

        # Testa dragEnterEvent de outra câmera
        enter_event = QDragEnterEvent(
            QPointF(10.0, 10.0),
            Qt.DropAction.MoveAction,
            mime_other,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.dragEnterEvent(enter_event)
        self.assertTrue(enter_event.isAccepted())
        self.assertTrue(widget.property("dropTarget"))

        # Testa dragLeaveEvent limpando destaque
        widget.dragLeaveEvent(None)
        self.assertFalse(widget.property("dropTarget"))

        # Testa dropEvent emitindo reorder_requested
        reordered_calls = []
        widget.reorder_requested.connect(lambda src, tgt: reordered_calls.append((src, tgt)))

        drop_event = QDropEvent(
            QPointF(10.0, 10.0),
            Qt.DropAction.MoveAction,
            mime_other,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.dropEvent(drop_event)
        self.assertTrue(drop_event.isAccepted())
        self.assertEqual(reordered_calls, [("cam-2", "cam-1")])
        self.assertFalse(widget.property("dropTarget"))

        # Drop de si mesmo deve ser ignorado
        mime_self = QMimeData()
        mime_self.setData("application/x-myipcams-camera-id", b"cam-1")
        drop_self = QDropEvent(
            QPointF(10.0, 10.0),
            Qt.DropAction.MoveAction,
            mime_self,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        widget.dropEvent(drop_self)
        # Nenhuma nova chamada emitida
        self.assertEqual(len(reordered_calls), 1)

        widget.stop_stream()

    def test_camera_grid_reorder_cameras(self):
        grid = CameraGrid()
        cams = [self.cam1, self.cam2, self.cam3]
        grid.set_cameras(cams)

        self.assertEqual([c.id for c in grid.cameras], ["cam-1", "cam-2", "cam-3"])

        emitted_lists = []
        grid.cameras_reordered.connect(lambda clist: emitted_lists.append([c.id for c in clist]))

        # Move cam-3 para a posição da cam-1 (Início)
        grid.reorder_cameras("cam-3", "cam-1")
        self.assertEqual([c.id for c in grid.cameras], ["cam-3", "cam-1", "cam-2"])
        self.assertEqual(emitted_lists[-1], ["cam-3", "cam-1", "cam-2"])

        # Move cam-3 para a posição da cam-2
        grid.reorder_cameras("cam-3", "cam-2")
        self.assertEqual([c.id for c in grid.cameras], ["cam-1", "cam-2", "cam-3"])
        self.assertEqual(emitted_lists[-1], ["cam-1", "cam-2", "cam-3"])

        grid.stop_all()

    def test_camera_grid_move_action(self):
        grid = CameraGrid()
        grid.set_cameras([self.cam1, self.cam2, self.cam3])

        # Ação "last" na cam-1
        grid.move_camera_action("cam-1", "last")
        self.assertEqual([c.id for c in grid.cameras], ["cam-2", "cam-3", "cam-1"])

        # Ação "first" na cam-1
        grid.move_camera_action("cam-1", "first")
        self.assertEqual([c.id for c in grid.cameras], ["cam-1", "cam-2", "cam-3"])

        # Ação "next" na cam-1
        grid.move_camera_action("cam-1", "next")
        self.assertEqual([c.id for c in grid.cameras], ["cam-2", "cam-1", "cam-3"])

        # Ação "prev" na cam-1
        grid.move_camera_action("cam-1", "prev")
        self.assertEqual([c.id for c in grid.cameras], ["cam-1", "cam-2", "cam-3"])

        grid.stop_all()

    def test_storage_persistence_after_reorder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "cameras.json"
            storage = CameraStorage(str(config_file))

            cams = [self.cam1, self.cam2, self.cam3]
            storage.save_cameras(cams)

            loaded = storage.load_cameras()
            self.assertEqual([c.id for c in loaded], ["cam-1", "cam-2", "cam-3"])

            # Simula reordenação
            grid = CameraGrid()
            grid.set_cameras(loaded)
            grid.reorder_cameras("cam-3", "cam-1")

            # Salva lista reordenada
            storage.save_cameras(grid.cameras)

            reloaded = storage.load_cameras()
            self.assertEqual([c.id for c in reloaded], ["cam-3", "cam-1", "cam-2"])

            grid.stop_all()


if __name__ == "__main__":
    unittest.main()
