"""Opt-in Qt click test against a tablet, limited to org.droiddesk.validation.

Build the no-code APK and split from tests/android first. This test refuses an
existing validation package in any Android user, then removes its own fixture.
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
import zipfile
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
CONFIG = tempfile.TemporaryDirectory(prefix="droiddesk-live-ui-")
os.environ["XDG_CONFIG_HOME"] = CONFIG.name
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtTest import QTest
from qt_app import QApplication, MainWindow, UninstallDialog, ResultsDialog, QMessageBox
from adb_backend import Adb, Device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("serial","apk","split","output"):
        parser.add_argument("--"+field,required=True)
    args = parser.parse_args()
    name = "org.droiddesk.validation"
    for path in (args.apk,args.split):
        with zipfile.ZipFile(path) as apk:
            manifest = apk.read("AndroidManifest.xml")
        if name.encode() not in manifest and name.encode("utf-16-le") not in manifest:
            raise SystemExit('APK without the validation package ID.')
    output = Path(args.output)
    output.mkdir(parents=True,exist_ok=True)
    report = {"serial":args.serial,"package":name,"checks":[],"cleanup":False}
    a = Adb()
    for uid,_ in a.users(args.serial):
        if name in a.package_set(args.serial,uid,"-u"):
            raise SystemExit('The validation package already exists. No changes have been made.')
    app = QApplication([])
    app.setStyle("Fusion")
    window = MainWindow(False)
    window.logpath = output/"comandos.log"
    window.devices = [Device(args.serial,"device",'Validation Tablet')]
    window.device_box.blockSignals(True)
    window.device_box.addItem('Validation Tablet',args.serial)
    window.device_box.blockSignals(False)
    window.show()
    def check(title,results):
        assert all(o.status=="ok" for o in results),results
        report["checks"].append(title)
        print(title+": OK",flush=True)
    def load_test():
        window.loaded(a.snapshot(args.serial,0))
        window.filters.setCurrentRow(5)
        window.search.setText(name)
        app.processEvents()
        assert window.proxy.rowCount()==1
        index=window.proxy.index(0,0)
        QTest.mouseClick(window.table.viewport(),Qt.MouseButton.LeftButton,pos=window.table.visualRect(index).center())
        assert window.model.checked == {name}
        return window.proxy.index(0,0).data(Qt.ItemDataRole.UserRole)
    def click_remove(backup,keep,direct):
        outcomes,errors,confirmations = [],[],[]
        def dialogs():
            dialog=app.activeModalWidget()
            if isinstance(dialog,UninstallDialog):
                confirmations.append(True)
                dialog.backup.setChecked(backup)
                dialog.keep_data.setChecked(keep)
                dialog.folder.setText(str(output/"backup"))
                app.processEvents()
                dialog.grab().save(str(output/("confirmation-with-backup.png" if backup else "confirmation-without-backup.png")))
                QTest.mouseClick(dialog.confirm,Qt.MouseButton.LeftButton)
            elif isinstance(dialog,ResultsDialog):
                outcomes.extend(dialog.outcomes)
                dialog.grab().save(str(output/("result-with-backup.png" if backup else "result-without-backup.png")))
                dialog.accept()
            elif isinstance(dialog,QMessageBox):
                errors.append(dialog.text())
                dialog.reject()
        timer=QTimer()
        timer.timeout.connect(dialogs)
        timer.start(30)
        if not direct:
            window.operation.setCurrentIndex(window.operation.findData("uninstall"))
            window.loaded(window.snapshot_data)
            assert window.operation.currentData()=="uninstall"
        QTest.mouseClick(window.uninstall_button if direct else window.execute_button,Qt.MouseButton.LeftButton)
        until=time.monotonic()+120
        while (not outcomes or window.busy) and not errors and time.monotonic()<until:
            QTest.qWait(30)
        timer.stop()
        assert not errors,errors
        assert len(confirmations)==1,confirmations
        assert not window.busy,'The operation is not complete'
        assert name not in a.package_set(args.serial,0)
        return outcomes
    try:
        check("Install base and split test APKs",a.install(args.serial,0,[args.apk,args.split],True,lambda *_:None))
        load_test()
        check('Quick button: copy base + split and uninstall',click_remove(True,False,True))
        dest=output/"backup"/name
        manifest=json.loads((dest/"manifest.json").read_text())
        assert len(manifest["files"])==2
        for entry in manifest["files"]:
            assert hashlib.sha256((dest/entry["file"]).read_bytes()).hexdigest()==entry["sha256"]
        report["checks"].append('Full backup of two APKs using SHA256')
        check('Reinstall Exported Copy',a.install(args.serial,0,[str(dest/e["file"]) for e in manifest["files"]],True,lambda *_:None))
        package=load_test()
        check("Disable only the test app",[a.action(args.serial,0,package,"disable")])
        window.model.mark({name},False)
        package=load_test()
        assert package.disabled and package.state==3
        check('Selected action: Remove disabled app, keep data, no copy',click_remove(False,True,False))
        assert name in a.package_set(args.serial,0,"-u")
        report["checks"].append('Deletion while preserving data confirmed by -u')
        window.search.clear()
        window.filters.setCurrentRow(3)
        window.operation.setCurrentIndex(window.operation.findData("enable"))
        for i in range(window.proxy.rowCount()):
            if window.proxy.index(i,0).data(Qt.ItemDataRole.UserRole).name=="com.microsoft.skydrive":
                window.table.selectRow(i)
                window.table.scrollTo(window.proxy.index(i,1))
                break
        for theme in ("dark","light"):
            window.theme_box.setCurrentIndex(window.theme_box.findData(theme))
            app.processEvents()
            window.grab().save(str(output/("interface-"+theme+".png")))
    finally:
        # This fixture was absent in every user before the test.
        if name in a.package_set(args.serial,0,"-u"):
            a.run("uninstall",name,serial=args.serial)
        report["cleanup"] = name not in a.package_set(args.serial,0,"-u")
        (output/"validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
        window.close()
        assert report["cleanup"]
        print("Limpeza: fixture removida.",flush=True)


if __name__=="__main__":
    main()
