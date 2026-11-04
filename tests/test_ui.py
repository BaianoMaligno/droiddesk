"""UI regressions. No Android commands or user preferences are changed."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CONFIG = tempfile.TemporaryDirectory(prefix="droiddesk-ui-tests-")
os.environ["XDG_CONFIG_HOME"] = CONFIG.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtTest import QTest
from qt_app import QApplication, MainWindow, UninstallDialog, ResultsDialog, QDialog, QPalette
from adb_backend import Package, Snapshot, Device, Outcome


class InterfaceRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")

    def setUp(self):
        self.window = MainWindow(False)
        self.window.logpath = Path(CONFIG.name)/"test.log"
        self.window.devices = [Device("TEST", "device", "Teste")]
        self.window.device_box.blockSignals(True)
        self.window.device_box.addItem("Teste", "TEST")
        self.window.device_box.blockSignals(False)
        self.packages = [Package("org.test.first", label="Primeiro"), Package("org.test.second", label="Segundo")]
        self.snapshot = Snapshot(self.packages,dict(model="Teste",brand="Teste",android="16",api="36",serial="TEST"),[(0,"Teste")])
        self.window.loaded(self.snapshot)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.pool.waitForDone(5000)
        self.app.processEvents()
        self.window.close()

    def test_refresh_and_filters_preserve_explicit_operation(self):
        w = self.window
        w.operation.setCurrentIndex(w.operation.findData("uninstall"))
        w.loaded(self.snapshot)
        w.filters.setCurrentRow(3)
        self.assertEqual(w.operation.currentData(),"uninstall")

    def test_checkbox_controls_actions_and_hidden_marks_are_visible(self):
        w = self.window
        self.assertFalse(w.uninstall_button.isEnabled())
        rect = w.table.visualRect(w.proxy.index(0,0))
        QTest.mouseClick(w.table.viewport(),Qt.MouseButton.LeftButton,pos=rect.center())
        self.assertEqual(len(w.model.checked),1)
        self.assertTrue(w.uninstall_button.isEnabled())
        w.search.setText("not-present")
        self.assertIn("1 fora do filtro",w.marked_label.text())

    def test_cancel_removal_does_not_send_commands(self):
        w = self.window
        w.model.mark({self.packages[0].name})
        QTimer.singleShot(0,lambda: self.app.activeModalWidget().reject())
        with patch("qt_app.Adb") as adb:
            QTest.mouseClick(w.uninstall_button,Qt.MouseButton.LeftButton)
            adb.assert_not_called()
        self.assertIn("canceled",w.progress_text.text())
        self.assertIn("[Canceled]",w.console.toPlainText())

    def test_empty_backup_folder_keeps_confirmation_open(self):
        dialog = UninstallDialog(self.window,self.packages,"TEST",0)
        dialog.show()
        dialog.folder.clear()
        QTest.mouseClick(dialog.confirm,Qt.MouseButton.LeftButton)
        self.assertTrue(dialog.isVisible())
        self.assertIn("Select a folder",dialog.error.text())
        dialog.reject()

    def test_backup_failure_preserves_only_failed_package_and_reports_results(self):
        w = self.window
        w.model.mark({p.name for p in self.packages})
        removed, reported = [], []
        class Backend:
            def __init__(self, log): pass
            def export(self,serial,user,packages,folder,progress):
                return [Outcome(packages[0].name,"error",'No space'),Outcome(packages[1].name,"ok","Saved")]
            def action(self,serial,user,package,operation,keep):
                removed.append((serial,user,package.name,operation))
                return Outcome(package.name,"ok","Removed and verified")
        def confirm():
            dialog = self.app.activeModalWidget()
            self.assertIsInstance(dialog,UninstallDialog)
            dialog.folder.setText(CONFIG.name)
            QTest.mouseClick(dialog.confirm,Qt.MouseButton.LeftButton)
        def result(dialog):
            reported.extend(dialog.outcomes)
            return QDialog.DialogCode.Accepted
        QTimer.singleShot(0,confirm)
        with patch("qt_app.Adb",Backend), patch.object(ResultsDialog,"exec",result), patch.object(w,"refresh_packages"):
            QTest.mouseClick(w.uninstall_button,Qt.MouseButton.LeftButton)
            until = time.monotonic()+5
            while not reported and time.monotonic()<until:
                QTest.qWait(10)
        self.assertEqual(removed,[("TEST",0,"org.test.second","uninstall")])
        self.assertEqual([o.status for o in reported],["error","ok"])
        self.assertIn("package preserved",reported[0].message)
        self.assertIn("[Resultado]",w.console.toPlainText())

    def test_light_and_dark_palette_define_readable_details_and_remember_choice(self):
        for theme in ("light","dark"):
            self.window.theme_box.setCurrentIndex(self.window.theme_box.findData(theme))
            self.app.processEvents()
            palette = self.window.app_details.palette()
            self.assertNotEqual(palette.color(QPalette.ColorRole.Text),palette.color(QPalette.ColorRole.Base))
            self.assertEqual(self.window.settings.value("theme"),theme)


if __name__ == "__main__":
    unittest.main()
