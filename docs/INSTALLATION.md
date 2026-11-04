# Install DroidDesk on Linux

**Creator: David o Baiano Maligno · Co-author: Nexo**

## An installer for multiple distributions

1. Clone the [DroidDesk repository](https://github.com/BaianoMaligno/droiddesk) or use a release archive when one is available.
2. If you downloaded an archive, extract it using the file manager.
3. Open a terminal in the project folder and run the following command **without sudo**:

   ```sh
   sh Install.sh
   ```

4. Open **DroidDesk** from the app menu.

The installer checks for Python, PyQt6, and ADB. If a dependency is missing, it uses the distribution's package manager; this is the only step that requires an administrator password. The program is located in `~/.local/share/droiddesk`, and the downloaded folder can be removed later. The installation does not modify Android apps or automatically enable debugging.

| Family | Manager | Packages installed as needed |
|---|---|---|
| Debian, Ubuntu, Kubuntu, and derivatives identified by `ID_LIKE` | APT | `python3`, `python3-pyqt6`, `adb` |
| Fedora and compatible derivatives | DNF | `python3`, `python3-pyqt6`, `android-tools` |
| Arch and compatible derivatives | Pacman | `python`, `python-pyqt6`, `android-tools` |
| openSUSE Tumbleweed and the SUSE family | Zypper | `python3`, provider of `python3dist(pyqt6)`, `android-tools` |

**Python 3.10+ and PyQt6 6.4+** must be available in the distribution's repositories. Support for a family does not guarantee support for all versions or derivatives. Immutable systems, NixOS, and distributions without these dependencies require custom setup. The installer does not add external repositories, does not change the global Python installation via pip, and does not perform a full distribution update.

The installation and launch of Qt were tested on Ubuntu 24.04, Fedora 43, Arch, and openSUSE Tumbleweed containers. The graphical session and desktop shortcut were verified on Kubuntu 26.04. Containers do not validate USB integration, Wayland/X11, or the udev rules specific to each desktop; see the [report](../VALIDATION-0.3.0.md).

Before installing, you can check:

```sh
sh Install.sh --system-info
sh Install.sh --check
```

## Optional Debian/Ubuntu Package

The `droiddesk_0.3.0_all.deb` file can be opened using the system's package manager. From the terminal:

```sh
sudo apt install ./droiddesk_0.3.0_all.deb
```

APT resolves the dependencies; the application is installed in `/usr/lib/droiddesk`, and the `droiddesk` command becomes available. This format is intended for Debian/Ubuntu distributions, while the `.tar.gz` file contains the installer for various families.

Choose one method per user. If a per-user installation already exists, remove its managed shortcut before migrating to the `.deb`, since personal shortcuts take precedence over system shortcuts. Older, manually created copies are preserved; the per-user installer retains the previous shortcut when it replaces it.

## Update, Go Back, and Remove

**Update:** Extract the new file and run `sh Install.sh` again. The new version is copied and verified before the shortcut's target is updated. Previous versions are preserved.

**Return to the previous managed version:**

```sh
python3 ~/.local/share/droiddesk/current/install_linux.py --rollback
```

**Uninstall the user installation:** Use the **Uninstall DroidDesk** action from the shortcut when the desktop menu offers secondary actions, or run:

```sh
python3 ~/.local/share/droiddesk/current/install_linux.py --uninstall
```

The program's files are moved to a `droiddesk-removed-*` folder next to the installation, allowing for recovery. The managed shortcut is removed. Cache, preferences, APK copies, files from other apps, and Android packages are preserved. The archived folder can be manually deleted when it is no longer needed.

**Update the `.deb`:** Install the new `.deb` using the same method. **Remove the `.deb`:** Use the package manager or run `sudo apt remove droiddesk`.

## Android Diagnostics and Connection

In the menu, the **Diagnostics** option displays the version, the folder, and the connection statuses. Via the terminal, for user-initiated installation:

```sh
python3 ~/.local/share/droiddesk/current/launch.py --doctor
```

Enable USB debugging on Android, connect a data cable, and grant permission on the device's screen. Then, use **Update Connection**. `unauthorized` requires permission on Android; `offline` indicates a connection problem. Udev rules and USB groups are the responsibility of the distribution and are not modified by the installer.

References: [ADB](https://developer.android.com/tools/adb), [physical devices on Linux](https://developer.android.com/studio/run/device), [Fedora packages](https://packages.fedoraproject.org/pkgs/python-pyqt6/python3-pyqt6/), [Arch packages](https://archlinux.org/packages/extra/x86_64/python-pyqt6/).

Scrcpy and Fastboot remain optional. The project is a Linux application that manages Android; developing a custom APK is outside the current scope.
