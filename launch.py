#!/usr/bin/env python3
# DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
"""Standard-library entry point: diagnose dependencies before importing Qt."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from version import VERSION, CREATOR, COAUTHOR


def dependencies():
    problems = []
    if sys.version_info < (3, 10):
        problems.append("Python 3.10 ou superior")
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR
        if tuple(map(int, PYQT_VERSION_STR.split('.')[:2])) < (6, 4):
            problems.append("PyQt6 6.4 ou superior")
    except ImportError:
        problems.append("PyQt6 (python3-pyqt6 package)")
    if not shutil.which("adb"):
        problems.append("ADB (adb package)")
    return problems


def doctor():
    report = {"version": VERSION, "python": sys.version.split()[0],
              "creator": CREATOR, "coauthor": COAUTHOR,
              "application": str(Path(__file__).resolve().parent),
              "missing": dependencies(), "adb": shutil.which("adb"),
              "display_available": bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))}
    if report["adb"]:
        try:
            result = subprocess.run([report["adb"], "devices"], capture_output=True, text=True, timeout=10)
            # Report authorization states, never serial numbers.
            report["device_states"] = [line.split()[1] for line in result.stdout.splitlines()[1:] if len(line.split()) >= 2]
            report["adb_ok"] = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            report["adb_ok"] = False
            report["adb_error"] = str(exc)
    return report


def main():
    if "--version" in sys.argv:
        print("DroidDesk " + VERSION)
        return 0
    if "--doctor" in sys.argv or "--doctor-dialog" in sys.argv:
        report = doctor()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if "--doctor-dialog" in sys.argv and not report["missing"]:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication([])
            message = ("DroidDesk " + VERSION + '\n\nDependencies: ready\nADB connection: '
                       + (", ".join(report.get("device_states", [])) or "nenhum aparelho conectado")
                       + "\n\nPasta do programa:\n" + report["application"])
            QMessageBox.information(None, 'DroidDesk Diagnosis', message)
        return int(bool(report["missing"]) or report.get("adb_ok") is False)
    missing = dependencies()
    if missing:
        message = "DroidDesk precisa de: " + ", ".join(missing) + '.\nRun the distribution installer again: sh Install.sh'
        print(message, file=sys.stderr)
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            for tool, args in (("kdialog", ["--error", message]), ("zenity", ["--error", "--text=" + message])):
                if shutil.which(tool):
                    subprocess.run([tool] + args, check=False)
                    break
        return 2
    if "--smoke-test" in sys.argv:
        from qt_app import QApplication, MainWindow, QTimer
        app = QApplication([])
        app.setApplicationName("DroidDeskSmokeTest")
        app.setOrganizationName("DroidDeskTests")
        window = MainWindow(False)
        window.show()
        QTimer.singleShot(300, app.quit)
        return app.exec()
    from qt_app import main as gui
    gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
