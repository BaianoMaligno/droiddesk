#!/usr/bin/env python3
"""Build a dependency-aware .deb and a portable per-user installer archive."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import VERSION, CREATOR, COAUTHOR
from install_linux import FILES


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="droiddesk-deb-") as temp:
        stage = Path(temp)
        app = stage / "usr/lib/droiddesk"
        for name in FILES:
            dest = app / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        for directory in ("DEBIAN", "usr/bin", "usr/share/applications", "usr/share/icons/hicolor/scalable/apps", "usr/share/doc/droiddesk"):
            (stage / directory).mkdir(parents=True, exist_ok=True)
        launcher = stage / "usr/bin/droiddesk"
        launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 -B /usr/lib/droiddesk/launch.py "$@"\n')
        launcher.chmod(0o755)
        desktop = stage / "usr/share/applications/droiddesk.desktop"
        desktop.write_text(f'''[Desktop Entry]
Type=Application
Version=1.0
Name=DroidDesk
Comment=Manage Android apps from Linux
Exec=/usr/bin/droiddesk
Icon=droiddesk
Terminal=false
Categories=Utility;System;
StartupNotify=true
StartupWMClass=droiddesk
X-DroidDesk-Creator={CREATOR}
X-DroidDesk-Coauthor={COAUTHOR}
Actions=Diagnosis;

[Desktop Action Diagnosis]
Name=Diagnosis
Exec=/usr/bin/droiddesk --doctor-dialog
''')
        shutil.copyfile(ROOT / "assets/droiddesk.svg", stage / "usr/share/icons/hicolor/scalable/apps/droiddesk.svg")
        for doc in ("README.md", "CHANGELOG.md", "AUTHORS.md"):
            shutil.copyfile(ROOT / doc, stage / "usr/share/doc/droiddesk" / doc)
        shutil.copyfile(ROOT / "docs/INSTALLATION.md", stage / "usr/share/doc/droiddesk/INSTALLATION.md")
        size = sum(p.stat().st_size for p in stage.rglob('*') if p.is_file()) // 1024 + 1
        (stage / "DEBIAN/control").write_text(f'''Package: droiddesk
Version: {VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: {CREATOR} <droiddesk@localhost>
Depends: python3 (>= 3.10), python3-pyqt6 (>= 6.4), adb
Suggests: scrcpy, fastboot
Installed-Size: {size}
Homepage: https://github.com/BaianoMaligno/droiddesk
Description: Android app manager for Linux
 Qt interface with light and dark themes, APK export, and
 management for an Android user via authorized ADB.
''')
        # Package has no maintainer scripts: apt/dpkg own installation and removal.
        for p in stage.rglob('*'):
            if p.is_dir(): p.chmod(0o755)
            elif p != launcher: p.chmod(0o644)
        if shutil.which("desktop-file-validate"):
            subprocess.run(["desktop-file-validate", str(desktop)], check=True)
        deb = output / f"droiddesk_{VERSION}_all.deb"
        subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(deb)], check=True)
    archive = output / f"droiddesk-{VERSION}-linux.tar.gz"
    allowed_suffixes = {'.py', '.sh', '.md', '.java', '.jar', '.png', '.json', '.txt', '.svg', '.xml', '.yml'}
    with tarfile.open(archive, 'w:gz') as tar:
        for p in sorted(ROOT.rglob('*')):
            relative = p.relative_to(ROOT)
            if any(part in {'.git', '__pycache__', 'build', 'dist', '.venv', 'outputs'} for part in relative.parts): continue
            if not p.is_file() or p.is_symlink(): continue
            if p.name != '.gitignore' and p.suffix not in allowed_suffixes and relative.as_posix() != 'signing/droiddesk-public.pem': continue
            info = tar.gettarinfo(str(p), f'droiddesk-{VERSION}/{relative.as_posix()}')
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            info.mode = 0o755 if p.suffix == '.sh' else 0o644
            with p.open('rb') as content: tar.addfile(info, content)
    artifacts = (deb, archive)
    (output / "SHA256SUMS").write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in artifacts))
    for p in artifacts: print(p)
    return artifacts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output.resolve())
