# History

## 0.3.0 — October 27, 2026

- User-friendly installer with detection of Debian/Ubuntu, Fedora, Arch, and openSUSE.
- Dependencies managed by the distribution manager; installation of the program without root privileges.
- Fixed folder, shortcut, versioned update, rollback, and reversible uninstallation.
- Optional Linux `.tar.gz` and `.deb` packages with checksums and Ed25519 signatures.
- Diagnosis of dependencies and connections before the interface is opened.
- Creator: David o Baiano Maligno. Co-author: Nexo.
- Identity and documentation reorganized around DroidDesk.
- Android app development has been removed from the scope.

## 0.2.2 — October 26, 2026

- Automatic workaround for the error `only root can delete system app for a particular user`, applicable only to system apps.
- The built-in helper uses `IPackageManager.deletePackageAsUser` with an explicit user; it preserves the option to keep data and does not use global update removal.
- Double verification: the helper reports removal and the Linux backend checks the package list independently.
- Handling invalid responses, incorrect users, and clearing the temporary buffer.
- 17 automated tests passed. Removal and restoration of the Easter Egg verified on the SM-X520/Android 16, with no changes to the final list of apps.
- Validation of the original error on the SM-F766B is still pending: the device was disconnected during testing.

## 0.2.1 — October 26, 2026

- Dark theme by default, light/dark toggle, and persistent settings.
- Explicit palettes for details, controls, menus, tables, and confirmations.
- Fix: Updating the catalog or changing filters no longer overrides the selected action.
- Direct uninstall button and single confirmation for destination, packages, data, and backup.
- Cancellations and results by package recorded in the console/log.
- Number of entries outside the specified filter.
- Physical validation of the Qt workflow, including copying, removing, reinstalling, and maintaining data.
- Nine automatic regressions approved. The user confirmed that the system was working properly after the fix.

## 0.2.0 — October 26, 2026

- Replacing the Tkinter interface with the Qt interface.
- APK names, icons, versions, and sizes via our own collector.
- Profiles, package statuses, presets, the details panel, and batch actions.
- Installation/export of the database + splits, permissions, console, and tools.
- Fixed the issue with reading states when factory records are hidden.
- Testing with a disposable app, including permissions and reinstalling the copy.

## Previous Prototype — History
