#!/bin/sh
# One entry point across distro families. The app itself runs without root.
set -eu
cd -- "$(dirname -- "$0")"
distro_id=unknown
distro_like=
if [ -r /etc/os-release ]; then
    . /etc/os-release
    distro_id=${ID:-unknown}
    distro_like=${ID_LIKE:-}
fi
case " $distro_id $distro_like " in
    *' debian '*|*' ubuntu '*) family=debian ;;
    *' fedora '*|*' rhel '*) family=fedora ;;
    *' arch '*) family=arch ;;
    *' opensuse '*|*' opensuse-tumbleweed '*|*' opensuse-leap '*|*' suse '*) family=suse ;;
    *) family=unknown ;;
esac
install_dependencies() {
    case "$family" in
        debian) set -- apt-get install -y python3 python3-pyqt6 adb ;;
        fedora) set -- dnf install -y python3 python3-pyqt6 android-tools ;;
        arch) set -- pacman -S --needed --noconfirm python python-pyqt6 android-tools ;;
        suse) set -- zypper --non-interactive install python3 'python3dist(pyqt6)' android-tools ;;
        *) echo 'Unknown distribution. Install Python 3.10+, PyQt6 6.4+, and ADB, then try again.' >&2; return 2 ;;
    esac
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Package manager unavailable: $1. Immutable systems require manual setup." >&2
        return 2
    fi
    echo "Dependencies from the distribution package manager: $*"
    if [ -t 0 ] && command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    elif command -v pkexec >/dev/null 2>&1; then
        package_executable=$(command -v "$1")
        shift
        pkexec "$package_executable" "$@"
    else
        echo "Run as an administrator: $*" >&2
        return 2
    fi
}
if [ "${1:-}" = --system-info ]; then
    printf 'Distribution: %s\nFamily: %s\n' "$distro_id" "$family"
    exit 0
fi
if [ "$(id -u)" = 0 ]; then
    echo 'Run without sudo: sh Install.sh. Only dependency installation requires administrator approval.' >&2
    exit 1
fi
python_bin=$(command -v python3 || true)
if [ "$#" -gt 0 ]; then
    if [ -z "$python_bin" ]; then echo 'Python 3 not found.' >&2; exit 2; fi
    exec "$python_bin" -B install_linux.py "$@"
fi
if [ -z "$python_bin" ] || ! "$python_bin" -B install_linux.py --check; then
    install_dependencies
    python_bin=$(command -v python3)
fi
exec "$python_bin" -B install_linux.py
