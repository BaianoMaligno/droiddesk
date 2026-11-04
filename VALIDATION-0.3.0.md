# Validation 0.3.0: Linux distribution

Creator: **David o Baiano Maligno**. Co-author: **Nexo**.

## Automated Testing

`QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`: **24 tests passed**.

The new tests check for repeated installation, updates, rollbacks to previous versions, preservation of user files, rejection of incomplete sources and unexpected links, updates with write failures, and shortcuts containing spaces or special characters. The 17 previous regressions continue to pass.

## Four isolated distributions

[Structured evidence with image identifiers](docs/evidence/installation-0.3.0.json).

| Environment x86_64 | PyQt6 observed | Result |
|---|---|---|
| Ubuntu 24.04 | 6.6.1 | Installation, opening Qt offscreen, and uninstallation verified |
| Fedora 43 | 6.11.0 | Installation, opening Qt offscreen, and uninstallation approved |
| Arch Linux | 6.11.0 | Installation, offscreen Qt launch, and uninstallation verified |
| openSUSE Tumbleweed | 6.12.0 | Installation, Qt offscreen launch, and uninstallation approved |

In each environment, the dependencies were installed by the distribution manager acting as the container administrator. The `Install.sh` script was then run as a regular user, followed by launching the installed program with `--smoke-test` and uninstalling it. The test did not pass USB, credentials, or Android data to the containers. The Fedora test required adding `su` to the minimal test environment; this is not a dependency of DroidDesk.

These results cover the packages available in the images used, not all versions of the four families. Udev rules, USB authorization, integration with each menu, and Wayland/X11 graphical sessions require separate physical testing. PyQt6 6.4 is the stated minimum; the oldest version observed in this matrix was 6.6.1.

## Main Computer and Packages

The user-specific installation is performed in a persistent folder, and the old shortcut is preserved as a backup before being replaced. The program does not rely on the Downloads folder. The `.deb` package is generated with declared dependencies and without maintenance scripts that modify Android or personal files.

The Linux archive contains the installer, Android support files, documentation, and the copyright notice. The packages are provided with SHA-256 checksums and Ed25519 signatures. See [authenticity](docs/AUTHENTICITY.md) for verification and signature limits.

No operations involving Android apps were repeated in this release. The user had already validated the other features; the focus of this version is the Linux distribution.

The installation, extraction, and removal of the `.deb` file also worked in the Ubuntu container. The valid signature was accepted by OpenSSL; a copy of the hash file with altered content was rejected. The copy installed on the computer returned a diagnostic with no missing dependencies and started without error.
