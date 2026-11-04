# Upcoming Deliveries

**Current focus: DroidDesk for Linux.** Android app development has been removed from the scope by decision of the creator.

## Released as version 0.3.0

- A single installer per user for Debian/Ubuntu, Fedora, Arch, and openSUSE families.
- Checking dependencies and installing via the distribution's repositories.
- Fixed folder, menu shortcut, update while preserving the previous version, and rollback.
- Uninstallation that preserves preferences, APK copies, and previous files.
- Optional `.deb` package and Linux package with checksums and a signature.
- Identification of the creator and co-authors in the interface, code, and manifests.
- Isolated tests on the four families and local validation on Kubuntu.

## Upcoming validations

- Graphical and USB integration on real computers running Fedora, Arch, and openSUSE.
- Older versions and derivatives of the supported families.
- Additional Android profiles and wireless connectivity.
- Test the alternative system removal path on the SM-F766B.
- scrcpy/Fastboot integrations in compatible environments.

AppImage, Flatpak, and support for immutable distributions have not been implemented. The current coverage is in [FEATURES.md](../FEATURES.md).
