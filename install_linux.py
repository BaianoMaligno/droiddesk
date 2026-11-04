#!/usr/bin/env python3
# DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
"""Per-user, versioned installation. No root, downloads or Android mutations."""
import argparse
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

from version import VERSION, CREATOR, COAUTHOR
from launch import dependencies

ROOT = Path(__file__).resolve().parent
FILES = ("droiddesk.py", "launch.py", "version.py", "qt_app.py", "themes.py", "adb_backend.py",
         "install_linux.py", "DroidDesk.sh", "AUTHORS.md", "assets/droiddesk.svg", "assets/arrow.svg", "assets/check.svg",
         "bridge/bin/droiddesk-metadata.jar", "bridge/bin/droiddesk-packages.jar")
MARKER = "X-DroidDesk-Managed=true"


def quote_exec(value):
    # Exec quoting followed by Desktop Entry string escaping.
    quoted = '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
    return quoted.replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')


def string_value(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r')


def desktop_entry(base):
    current = base / "current"
    return '\n'.join(("[Desktop Entry]", "Type=Application", "Name=DroidDesk",
        "Comment=Manage Android apps from Linux", "Version=1.0",
        "Exec=" + quote_exec(sys.executable) + " -B " + quote_exec(current / "launch.py"),
        "Icon=" + string_value(current / "assets/droiddesk.svg"), "Terminal=false",
        "Categories=Utility;System;", "StartupNotify=true", "StartupWMClass=droiddesk",
        MARKER, "X-DroidDesk-Creator=" + CREATOR, "X-DroidDesk-Coauthor=" + COAUTHOR,
        "Actions=Diagnosis;Uninstall;", "", "[Desktop Action Diagnosis]",
        'Name=Diagnosis', "Exec=" + quote_exec(sys.executable) + " -B " + quote_exec(current / "launch.py") + " --doctor-dialog",
        "", "[Desktop Action Uninstall]", "Name=Uninstall DroidDesk",
        "Exec=" + quote_exec(sys.executable) + " -B " + quote_exec(current / "install_linux.py") + " --uninstall --confirm-dialog --data-home " + quote_exec(base.parent), ""))


def atomic_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        temp.write_text(content, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def switch_link(base, name, target):
    link = base / name
    temp = base / (name + ".tmp-" + uuid.uuid4().hex)
    temp.symlink_to(target)
    try:
        os.replace(temp, link)
    finally:
        temp.unlink(missing_ok=True)


def managed_target(base, name):
    link = base / name
    if not link.is_symlink():
        if link.exists():
            raise RuntimeError('Existing unmanaged destination: ' + str(link))
        return None
    target = link.resolve()
    if target.parent != (base / "releases").resolve() or not (target / "installation.json").is_file():
        raise RuntimeError('Invalid version shortcut: ' + str(link))
    return target


@contextmanager
def locked(data_home):
    data_home.mkdir(parents=True, exist_ok=True)
    with (data_home / ".droiddesk-install.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def install(data_home, source=ROOT):
    data_home = data_home.resolve()
    base = data_home / "droiddesk"
    if base.is_symlink():
        raise RuntimeError('The installation folder cannot be a symbolic link.')
    hashes = {}
    for name in FILES:
        p = source / name
        if not p.is_file() or p.is_symlink():
            raise RuntimeError('Incomplete package or invalid file: ' + name)
        hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    release_id = VERSION + "-" + hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:12]
    releases = base / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    old = managed_target(base, "current")
    target = releases / release_id
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=releases))
    try:
        for name, checksum in hashes.items():
            dest = staging / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, dest)
            if hashlib.sha256(dest.read_bytes()).hexdigest() != checksum:
                raise RuntimeError('Error copying ' + name)
        atomic_text(staging / "installation.json", json.dumps({"version": VERSION, "creator": CREATOR, "coauthor": COAUTHOR, "files": hashes}, indent=2, ensure_ascii=False))
        if target.exists():
            # A repeated install must never trust a corrupt existing release.
            for name, checksum in hashes.items():
                if not (target / name).is_file() or hashlib.sha256((target / name).read_bytes()).hexdigest() != checksum:
                    raise RuntimeError('The installed version has been modified; back it up before reinstalling: ' + str(target))
        else:
            os.replace(staging, target)
        launcher = data_home / "applications/droiddesk.desktop"
        old_launcher = launcher.read_text() if launcher.exists() else None
        if old_launcher is not None and old_launcher != desktop_entry(base):
            backup = base / "launcher-backups" / (hashlib.sha256(old_launcher.encode()).hexdigest()[:12] + ".desktop")
            atomic_text(backup, old_launcher)
        # Prepare the launcher before committing the active-version pointer.
        # The previous current remains usable if launcher creation fails.
        atomic_text(launcher, desktop_entry(base))
        try:
            switch_link(base, "current", target.relative_to(base))
        except Exception:
            if old_launcher is None:
                launcher.unlink(missing_ok=True)
            else:
                atomic_text(launcher, old_launcher)
            raise
        if old is not None and old != target:
            switch_link(base, "previous", old.relative_to(base))
        return target
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def rollback(data_home):
    base = data_home.resolve() / "droiddesk"
    current, previous = managed_target(base, "current"), managed_target(base, "previous")
    if current is None or previous is None:
        raise RuntimeError('There is no previous managed version to restore.')
    switch_link(base, "current", previous.relative_to(base))
    switch_link(base, "previous", current.relative_to(base))
    return previous


def uninstall(data_home):
    data_home = data_home.resolve()
    base = data_home / "droiddesk"
    if base.is_symlink() or managed_target(base, "current") is None:
        raise RuntimeError('User installation not found.')
    archived = data_home / ("droiddesk-removed-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6])
    os.replace(base, archived)
    launcher = data_home / "applications/droiddesk.desktop"
    if launcher.is_file() and MARKER in launcher.read_text() and str(base) in launcher.read_text():
        launcher.unlink()
    # Cache, settings, APK backups, and unmanaged installations are untouched.
    return archived


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--rollback", action="store_true")
    parser.add_argument("--confirm-dialog", action="store_true")
    parser.add_argument("--data-home", type=Path, default=Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))))
    args = parser.parse_args()
    try:
        if not args.uninstall and not args.rollback:
            missing = dependencies()
            if missing:
                print('Missing dependencies: ' + ", ".join(missing), file=sys.stderr)
                return 2
            if args.check:
                print('Required dependencies: Python, PyQt6, and ADB.')
                return 0
        if args.confirm_dialog:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            app = QApplication([])
            if QMessageBox.question(None, "Uninstall DroidDesk", 'Remove DroidDesk for this user? Preferences and APK copies will be preserved.') != QMessageBox.StandardButton.Yes:
                return 0
        with locked(args.data_home):
            if args.uninstall:
                result = uninstall(args.data_home)
                print("DroidDesk removed from the menu. Files preserved at:", result)
            elif args.rollback:
                print('Previous version enabled:', rollback(args.data_home))
            else:
                if os.geteuid() == 0:
                    raise RuntimeError('Run without sudo. To install the system, use the .deb package.')
                print("DroidDesk installed. Open it from the app menu.\nFolder:", install(args.data_home))
        if shutil.which("update-desktop-database"):
            import subprocess
            subprocess.run(["update-desktop-database", str(args.data_home / "applications")], capture_output=True)
        return 0
    except (OSError, RuntimeError) as exc:
        print('Unable to complete: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
