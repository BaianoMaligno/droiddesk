import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install_linux as installer


class InstallerRegression(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='droiddesk-installer-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data with spaces'
        self.source = self.root / 'source'
        for name in installer.FILES:
            p = self.source / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('fixture ' + name)

    def test_install_update_rollback_and_uninstall_preserve_user_files(self):
        apps = self.data / 'applications'
        apps.mkdir(parents=True)
        old_launcher = 'Exec=old-downloads-copy\n'
        (apps / 'droiddesk.desktop').write_text(old_launcher)
        unrelated = self.data / 'other.txt'
        unrelated.write_text('keep')
        first = installer.install(self.data, self.source)
        self.assertEqual((self.data / 'droiddesk/current').resolve(), first)
        self.assertEqual(installer.install(self.data, self.source), first)
        (self.source / 'qt_app.py').write_text('updated')
        second = installer.install(self.data, self.source)
        self.assertNotEqual(first, second)
        self.assertEqual(installer.rollback(self.data), first)
        archive = installer.uninstall(self.data)
        self.assertFalse((apps / 'droiddesk.desktop').exists())
        self.assertEqual(unrelated.read_text(), 'keep')
        self.assertEqual(len(list((archive / 'releases').iterdir())), 2)
        self.assertEqual(next((archive / 'launcher-backups').iterdir()).read_text(), old_launcher)

    def test_incomplete_update_does_not_change_current_or_launcher(self):
        first = installer.install(self.data, self.source)
        launcher = (self.data / 'applications/droiddesk.desktop').read_bytes()
        (self.source / 'bridge/bin/droiddesk-packages.jar').unlink()
        with self.assertRaises(RuntimeError): installer.install(self.data, self.source)
        self.assertEqual((self.data / 'droiddesk/current').resolve(), first)
        self.assertEqual((self.data / 'applications/droiddesk.desktop').read_bytes(), launcher)

    def test_launcher_failure_leaves_previous_release_active(self):
        first = installer.install(self.data, self.source)
        (self.source / 'qt_app.py').write_text('updated')
        original = installer.atomic_text
        def failing(path, content):
            if path.name == 'droiddesk.desktop': raise OSError('disk full')
            return original(path, content)
        with patch.object(installer, 'atomic_text', side_effect=failing):
            with self.assertRaises(OSError): installer.install(self.data, self.source)
        self.assertEqual((self.data / 'droiddesk/current').resolve(), first)

    def test_uninstall_preserves_launcher_replaced_by_another_installation(self):
        installer.install(self.data, self.source)
        launcher = self.data / 'applications/droiddesk.desktop'
        launcher.write_text('Exec=/usr/bin/droiddesk\n')
        installer.uninstall(self.data)
        self.assertTrue(launcher.exists())

    def test_refuses_symlink_source_and_unmanaged_destination(self):
        (self.source / 'qt_app.py').unlink()
        (self.source / 'qt_app.py').symlink_to(self.source / 'themes.py')
        with self.assertRaises(RuntimeError): installer.install(self.data, self.source)
        (self.source / 'qt_app.py').unlink()
        (self.source / 'qt_app.py').write_text('regular')
        (self.data / 'droiddesk/current').mkdir(parents=True)
        with self.assertRaises(RuntimeError): installer.install(self.data, self.source)

    def test_modified_installed_release_is_not_silently_reused(self):
        target = installer.install(self.data, self.source)
        (target / 'adb_backend.py').write_text('corrupt')
        with self.assertRaises(RuntimeError): installer.install(self.data, self.source)

    def test_desktop_entry_validates_with_spaces_and_special_characters(self):
        import shutil
        if not shutil.which('desktop-file-validate'): self.skipTest('desktop-file-validate unavailable')
        entry = self.root / 'test.desktop'
        entry.write_text(installer.desktop_entry(self.root / 'space $ cash % back\\slash "quote"'))
        subprocess.run(['desktop-file-validate', str(entry)], check=True, capture_output=True)


if __name__ == '__main__': unittest.main()
