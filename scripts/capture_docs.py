"""Render the real Qt interface from a fresh, read-only Android snapshot.

Serial/profile labels are masked in the documentation view only. No package
action is executed; the uninstall dialog is opened for illustration and rejected.
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
CONFIG = tempfile.TemporaryDirectory(prefix="droiddesk-doc-capture-")
os.environ["XDG_CONFIG_HOME"] = CONFIG.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qt_app import QApplication, MainWindow, UninstallDialog, Qt, VERSION
from adb_backend import Adb, Device


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial",required=True)
    parser.add_argument("--output",default=str(Path(__file__).resolve().parents[1]/"docs"/"screenshots"))
    args=parser.parse_args()
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    adb=Adb()
    snapshot=adb.snapshot(args.serial,0)
    app=QApplication([])
    app.setStyle("Fusion")
    w=MainWindow(False)
    w.resize(1600,960)
    w.logpath=Path(CONFIG.name)/"capture.log"
    w.devices=[Device(args.serial,"device",snapshot.info['model'])]
    w.device_box.blockSignals(True)
    w.device_box.addItem(snapshot.info['model']+" · USB",args.serial)
    w.device_box.blockSignals(False)
    w.loaded(snapshot)
    w.device_meta.setText(f"{snapshot.info['brand'].title()} · Android {snapshot.info['android']}\nAPI {snapshot.info['api']} · USB authorized")
    w.user_box.setItemText(0,"Primary profile · 0")
    w.show()
    w.filters.setCurrentRow(5)
    w.search.setText("com.google.android")
    chosen=None
    for row in range(w.proxy.rowCount()):
        p=w.proxy.index(row,0).data(Qt.ItemDataRole.UserRole)
        if p.name=="com.google.android.apps.photos" and p.installed:
            w.table.selectRow(row)
            w.table.scrollTo(w.proxy.index(row,1))
            chosen=p
            break
    def save(filename):
        app.processEvents()
        assert w.grab().save(str(out/filename))
    for theme in ("dark","light"):
        w.theme_box.setCurrentIndex(w.theme_box.findData(theme))
        save("apps-"+theme+".png")
    w.theme_box.setCurrentIndex(w.theme_box.findData("dark"))
    if chosen:
        dialog=UninstallDialog(w,[chosen],"USB authorized",0)
        dialog.folder.setText("~/Documents/DroidDesk/Backups/2026-10-26")
        dialog.show()
        app.processEvents()
        assert dialog.grab().save(str(out/"removal-confirmation.png"))
        dialog.reject()
    w.tabs.setCurrentIndex(1)
    save("installation.png")
    w.tabs.setCurrentIndex(3)
    save("tools.png")
    w.tabs.setCurrentIndex(2)
    w.console.clear()
    for args_ in [("shell","wm","size"),("shell","wm","density"),("shell","getprop","ro.build.version.release")]:
        result=adb.run(*args_,serial=args.serial,quiet=True)
        w.console.appendPlainText("$ adb "+" ".join(args_)+"\n"+result+"\n")
    save("console.png")
    metadata=dict(captured_at=datetime.now(timezone.utc).isoformat(),version=VERSION,
                  source='Qt offscreen with real ADB snapshot; connection and profile identifiers hidden in the preview',
                  device_model=snapshot.info['model'],android=snapshot.info['android'],api=snapshot.info['api'],
                  packages=len(snapshot.packages),package_mutations=False)
    (out/"capture.json").write_text(json.dumps(metadata,indent=2,ensure_ascii=False))
    w.close()
    print(json.dumps(metadata,ensure_ascii=False))


if __name__=="__main__":main()
