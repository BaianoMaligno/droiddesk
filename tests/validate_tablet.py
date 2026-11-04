"""Explicit opt-in physical test; only org.droiddesk.validation is changed.

Build/sign the two manifests in tests/android with the same temporary key first.
Example: python3 tests/validate_tablet.py --serial SERIAL --apk test.apk --split config.test.apk
"""
import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adb_backend import Adb,Package,parse_package_states


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial",required=True)
    parser.add_argument("--user",type=int,default=0)
    parser.add_argument("--apk",required=True)
    parser.add_argument("--split",required=True)
    args=parser.parse_args()
    name="org.droiddesk.validation"
    for path in (args.apk,args.split):
        with zipfile.ZipFile(path) as apk: manifest=apk.read("AndroidManifest.xml")
        if name.encode() not in manifest and name.encode("utf-16-le") not in manifest:
            raise SystemExit('The provided APK does not contain the validation package ID.')
    a=Adb()
    if name in a.package_set(args.serial,args.user,"-u"):
        raise SystemExit('The test package already exists; no action will be taken.')
    package=Package(name,label="DroidDesk Validation")
    def notify(*_):pass
    def check(title,results):
        if not all(x.status=="ok" for x in results):raise AssertionError(results)
        print(title+": OK",flush=True)
    try:
        check("APK simples",a.install(args.serial,args.user,[args.apk],False,notify))
        check('Deactivation',[a.action(args.serial,args.user,package,"disable")])
        state=parse_package_states(a.run("shell","dumpsys","package",name,serial=args.serial),args.user)[name]["state"]
        assert state==3
        package.disabled,package.state=True,3
        check('Reactivation',[a.action(args.serial,args.user,package,"enable")])
        package.disabled,package.state=False,1
        a.set_permission(args.serial,args.user,name,"android.permission.POST_NOTIFICATIONS",True)
        a.set_permission(args.serial,args.user,name,"android.permission.POST_NOTIFICATIONS",False)
        print('Grant/revoke permission: OK',flush=True)
        check("Clear test data",[a.action(args.serial,args.user,package,"clear")])
        check('Uninstallation',[a.action(args.serial,args.user,package,"uninstall")])
        check("Base + split",a.install(args.serial,args.user,[args.apk,args.split],True,notify))
        with tempfile.TemporaryDirectory(prefix="droiddesk-validation-") as folder:
            check('Basic Export + Split',a.export(args.serial,args.user,[package],folder,notify))
            dest=Path(folder)/name
            manifest=json.loads((dest/"manifest.json").read_text())
            assert len(manifest["files"])==2
            for entry in manifest["files"]:
                assert hashlib.sha256((dest/entry["file"]).read_bytes()).hexdigest()==entry["sha256"]
            check('Removal to Test Backup',[a.action(args.serial,args.user,package,"uninstall")])
            check('Reinstalling the Exported APKs',a.install(args.serial,args.user,[str(dest/e["file"]) for e in manifest["files"]],True,notify))
    finally:
        if name in a.package_set(args.serial,args.user):a.run("uninstall",name,serial=args.serial)
        assert name not in a.package_set(args.serial,args.user,"-u")
        print('Final cleanup: validation package removed.',flush=True)


if __name__=="__main__":main()
