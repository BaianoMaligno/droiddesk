# DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
"""Independent ADB backend. Every device operation has an explicit serial and user."""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache" / "droiddesk"
STATE_NAMES = {0: "Ativo", 1: "Ativo", 2: "Desativado pelo sistema", 3: 'Disabled by the user', 4: 'Deep suspension'}
PROTECTED = {"android", "com.android.systemui", "com.android.settings", "com.android.shell", "com.google.android.permissioncontroller", "com.android.permissioncontroller"}


class AdbError(RuntimeError):
    pass


@dataclass
class Device:
    serial: str
    state: str
    model: str


@dataclass
class Package:
    name: str
    label: str = ""
    system: bool = False
    installed: bool = True
    disabled: bool = False
    state: int = -1
    caller: str = ""
    version: str = ""
    uid: int = 0
    target_sdk: int = 0
    source: str = ""
    icon: str = ""
    protected: bool = False
    apk_bytes: int = 0

    @property
    def status(self) -> str:
        if not self.installed:
            return 'Removed from this user'
        if not self.disabled:
            return "Ativo"
        return STATE_NAMES.get(self.state, "Desativado")

    @property
    def title(self) -> str:
        return self.label or self.name

    @property
    def apk_size(self) -> str:
        size = self.apk_bytes
        if not size: return "—"
        for unit in ("B","KB","MB","GB"):
            if size < 1024 or unit=="GB": return f"{size:.1f} {unit}" if unit!="B" else f"{size} B"
            size /= 1024


@dataclass
class Snapshot:
    packages: list[Package]
    info: dict
    users: list[tuple[int, str]]


@dataclass
class Outcome:
    package: str
    status: str
    message: str


def parse_package_states(output: str, user: int) -> dict[str, dict]:
    """Ignore hidden factory versions; their default user records are not current."""
    values: dict[str, dict] = {}
    current = None
    hidden = False
    for line in output.splitlines():
        if line.strip() in {"Hidden system packages:", "Disabled system packages:"}:
            hidden, current = True, None
        elif line == "Packages:":
            hidden = False
        if hidden:
            continue
        match = re.match(r"\s*Package \[([^\]]+)\]", line)
        if match:
            current = match.group(1)
            continue
        if current is None:
            continue
        match = re.match(r"\s*User (\d+):.*?\benabled=(\d+)", line)
        if match:
            if int(match[1]) == user:
                values.setdefault(current, {"state": int(match[2]), "caller": ""})
            continue
        if "lastDisabledCaller:" in line and current in values:
            values[current]["caller"] = line.split("lastDisabledCaller:", 1)[1].strip()
    return values


class Adb:
    def __init__(self, log: Callable[[str], None] | None = None):
        self.executable = shutil.which("adb")
        if not self.executable:
            raise AdbError('ADB not found. Install the android-tools-adb package.')
        self.log = log or (lambda _: None)

    def run(self, *args: str, serial: str | None = None, timeout: int = 60, binary: bool = False, check: bool = True, quiet: bool = False):
        cmd = [self.executable] + (["-s", serial] if serial else []) + [str(x) for x in args]
        self.log("$ " + shlex.join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"The command exceeded {timeout}s. Check the USB connection.") from exc
        stdout = result.stdout.decode("utf-8", "replace")
        stderr = result.stderr.decode("utf-8", "replace")
        detail = (stdout + "\n" + stderr).strip()
        failed = result.returncode != 0 or re.search(r"(?im)^(Failure\b|Error:|Exception occurred|java\.lang\.|adb: error:)", detail)
        if check and failed:
            self.log(detail[:5000])
            raise AdbError((stderr or stdout)[-5000:].strip() or f"ADB exited with code {result.returncode}")
        if not binary and not quiet and detail:
            self.log(detail[:1500])
        return result.stdout if binary else stdout.strip()

    def devices(self) -> list[Device]:
        rows = []
        for line in self.run("devices", "-l").splitlines()[1:]:
            bits = line.split()
            if len(bits) >= 2:
                model = next((x[6:].replace("_", " ") for x in bits[2:] if x.startswith("model:")), bits[0])
                rows.append(Device(bits[0], bits[1], model))
        return rows

    def package_set(self, serial: str, user: int, *flags: str) -> set[str]:
        result = self.run("shell", "pm", "list", "packages", *flags, "--user", str(user), serial=serial, quiet=True)
        packages = {line[8:].strip() for line in result.splitlines() if line.startswith("package:")}
        self.log(f"  {len(packages)} package(s), user {user}")
        return packages

    def info(self, serial: str) -> dict:
        output = self.run("shell", "getprop", serial=serial, quiet=True)
        props = dict(re.findall(r"^\[([^]]+)\]: \[([^]]*)\]", output, re.M))
        return {"model": props.get("ro.product.model", serial), "brand": props.get("ro.product.manufacturer", "Android"),
                "android": props.get("ro.build.version.release", "?"), "api": props.get("ro.build.version.sdk", "?"), "serial": serial}

    def users(self, serial: str) -> list[tuple[int, str]]:
        result = self.run("shell", "pm", "list", "users", serial=serial)
        return [(int(uid), name) for uid, name in re.findall(r"UserInfo\{(\d+):([^:}]+):", result)] or [(0, 'Owner')]

    @staticmethod
    def cache_file(serial: str, user: int) -> Path:
        return CACHE / (hashlib.sha256(serial.encode()).hexdigest()[:16] + f"-{user}.json")

    def metadata(self, serial: str, user: int, progress: Callable | None = None) -> dict:
        helper = ROOT / "bridge" / "bin" / "droiddesk-metadata.jar"
        if not helper.exists():
            raise AdbError('Metadata collector not found in the bridge/bin folder.')
        if progress:
            progress(0, 0, 'Reading names, icons, and versions on Android…')
        remote = "/data/local/tmp/droiddesk-metadata-v2.jar"
        self.run("push", str(helper), remote, serial=serial)
        try:
            result = self.run("shell", f"CLASSPATH={remote}", "app_process", "/system/bin", "DroidDeskMetadata", str(user), serial=serial, timeout=180, quiet=True)
        finally:
            self.run("shell","rm","-f",remote,serial=serial,check=False)
        rows = {}
        for line in result.splitlines():
            if line.startswith("{"):
                try:
                    record = json.loads(line)
                    if record.get("package"):
                        rows[record["package"]] = record
                except (ValueError, KeyError):
                    continue
        if not rows:
            raise AdbError('Android did not return the metadata. The list of packages is still available in the console.')
        CACHE.mkdir(parents=True, exist_ok=True)
        target = self.cache_file(serial, user)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        temp.replace(target)
        return rows

    def snapshot(self, serial: str, user: int, progress: Callable | None = None, names: bool = False) -> Snapshot:
        notify = progress or (lambda *_: None)
        notify(0, 7, "Reading installed apps…")
        installed = self.package_set(serial, user)
        notify(1, 7, "Finding removed apps…")
        known = self.package_set(serial, user, "-u")
        system = self.package_set(serial, user, "-u", "-s")
        disabled = self.package_set(serial, user, "-d")
        notify(3, 7, 'Reading user statuses and information…')
        states = parse_package_states(self.run("shell", "dumpsys", "package", serial=serial, timeout=120, quiet=True), user)
        info, users = self.info(serial), self.users(serial)
        protected = set(PROTECTED)
        try:
            launcher = self.run("shell", "cmd", "package", "resolve-activity", "--brief", "--user", str(user), "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME", serial=serial)
            keyboard = self.run("shell", "settings", "--user", str(user), "get", "secure", "default_input_method", serial=serial)
            for component in (launcher.splitlines()[-1], keyboard):
                if "/" in component:
                    protected.add(component.split("/", 1)[0])
        except (AdbError, IndexError):
            pass
        notify(5, 7, 'Loading names and icons…')
        meta = {}
        cache = self.cache_file(serial, user)
        if cache.exists():
            try:
                meta = json.loads(cache.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
        if names or not meta or installed.difference(meta):
            try:
                meta = self.metadata(serial, user, notify)
            except AdbError as exc:
                self.log(str(exc))
        packages = []
        for name in sorted(known | installed):
            # Only system packages can be restored after per-user removal.
            if name not in installed and name not in system:
                continue
            m = meta.get(name, {})
            p = Package(name, label=m.get("label", ""), system=name in system, installed=name in installed,
                        disabled=name in disabled, state=states.get(name, {}).get("state", -1), caller=states.get(name, {}).get("caller", ""),
                        version=m.get("version", ""), uid=m.get("uid", 0), target_sdk=m.get("target_sdk", 0), source=m.get("source", ""), icon=m.get("icon", ""), protected=name in protected, apk_bytes=m.get("apk_bytes",0))
            packages.append(p)
        notify(7, 7, f"{len(packages)} apps loaded")
        return Snapshot(packages, info, users)

    @staticmethod
    def validate_name(name: str):
        if not re.fullmatch(r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*", name):
            raise AdbError('Invalid package name.')

    def action(self, serial: str, user: int, p: Package, operation: str, keep_data: bool = False) -> Outcome:
        self.validate_name(p.name)
        try:
            if type(user) is not int or user < 0:
                raise AdbError('Select a valid Android user.')
            if operation in {"disable", "uninstall", "clear"} and p.protected:
                return Outcome(p.name, "blocked", 'Essential app or launcher/keyboard in use; action blocked.')
            if operation == "enable":
                if not p.installed:
                    return Outcome(p.name, "skipped", "This package was removed. Use Restore.")
                if not p.disabled:
                    return Outcome(p.name, "skipped", "It's already active.")
                if p.state in {2, 4}:
                    return Outcome(p.name, "manual", 'Android blocks reactivation via the shell. Open the details on Android and tap "Enable."')
                output = self.run("shell", "pm", "enable", "--user", str(user), p.name, serial=serial)
                if p.name not in self.package_set(serial, user, "-e"):
                    raise AdbError('Android has not confirmed that the app is active. ' + output)
            elif operation == "disable":
                if not p.installed or p.disabled:
                    return Outcome(p.name, "skipped", 'Package has already been disabled or removed.')
                self.run("shell", "am", "force-stop", "--user", str(user), p.name, serial=serial)
                self.run("shell", "pm", "disable-user", "--user", str(user), p.name, serial=serial)
                if p.name not in self.package_set(serial, user, "-d"):
                    raise AdbError('Android has not confirmed the deactivation.')
            elif operation == "uninstall":
                if not p.installed:
                    return Outcome(p.name, "skipped", 'Already removed from this user.')
                args = ["shell", "pm", "uninstall"] + (["-k"] if keep_data else []) + ["--user", str(user), p.name]
                try:
                    self.run(*args, serial=serial)
                except AdbError as exc:
                    if not p.system or "only root can delete system app for a particular user" not in str(exc).lower():
                        raise
                    self.log('The standard command was rejected; attempting to uninstall the app via the Android API for the same user.')
                    self.remove_system_package(serial, user, p.name, keep_data)
                if p.name in self.package_set(serial, user):
                    raise AdbError('The package remains installed for this user.')
            elif operation == "restore":
                if p.installed or not p.system:
                    return Outcome(p.name, "skipped", "Restore applies to a system app that has been removed from this user's device.")
                self.run("shell", "cmd", "package", "install-existing", "--user", str(user), p.name, serial=serial)
                if p.name not in self.package_set(serial, user):
                    raise AdbError('Android has not confirmed the restore.')
            elif operation == "clear":
                self.run("shell", "pm", "clear", "--user", str(user), p.name, serial=serial)
            elif operation == "stop":
                self.run("shell", "am", "force-stop", "--user", str(user), p.name, serial=serial)
            else:
                raise AdbError('Unknown operation: ' + operation)
            return Outcome(p.name, "ok", 'Completed and verified.' if operation in {"enable", "disable", "restore", "uninstall"} else 'Done.')
        except AdbError as exc:
            detail = str(exc)
            if "SecurityException" in detail:
                detail = 'Android denied this action for the package. ' + detail.splitlines()[0]
            return Outcome(p.name, "error", detail[:1500])

    def remove_system_package(self, serial: str, user: int, package: str, keep_data: bool):
        """Compatibility path; never drops the user or uninstalls system updates globally."""
        self.validate_name(package)
        if type(user) is not int or user < 0:
            raise AdbError('Select a valid Android user.')
        helper = ROOT / "bridge" / "bin" / "droiddesk-packages.jar"
        if not helper.is_file():
            raise AdbError('Incomplete update: removal helper missing in bridge/bin.')
        remote = "/data/local/tmp/droiddesk-packages-" + uuid.uuid4().hex + ".jar"
        try:
            self.run("push", str(helper), remote, serial=serial)
            output = self.run("shell", "CLASSPATH=" + remote, "app_process", "/system/bin",
                              "DroidDeskPackages", "uninstall", str(user), package,
                              "keep" if keep_data else "clear", serial=serial, timeout=30)
            try:
                result = json.loads(output)
            except (ValueError, TypeError) as exc:
                raise AdbError('Android did not return a valid confirmation of the removal.') from exc
            if (not isinstance(result, dict) or result.get("protocol") != 1
                    or result.get("removed") is not True or result.get("user") != user
                    or result.get("package") != package):
                raise AdbError('Android has not confirmed the removal of the package for the selected user.')
        except AdbError as exc:
            raise AdbError('User-initiated removal was also denied or could not be confirmed by the Android API. ' + str(exc)) from exc
        finally:
            try:
                self.run("shell", "rm", "-f", remote, serial=serial, check=False)
            except AdbError as exc:
                self.log('The temporary helper could not be cleared: ' + str(exc))

    def batch(self, serial: str, user: int, packages: list[Package], operation: str, progress: Callable, keep_data: bool = False) -> list[Outcome]:
        outcomes = []
        for i, package in enumerate(packages):
            progress(i, len(packages), package.title)
            outcomes.append(self.action(serial, user, package, operation, keep_data))
        progress(len(packages), len(packages), 'Operation completed')
        return outcomes

    def details(self, serial: str, user: int, package: str):
        self.validate_name(package)
        return self.run("shell", "am", "start", "--user", str(user), "-a", "android.settings.APPLICATION_DETAILS_SETTINGS", "-d", "package:" + package, serial=serial)

    def launch(self, serial: str, user: int, package: str):
        self.validate_name(package)
        output = self.run("shell", "cmd", "package", "resolve-activity", "--brief", "--user", str(user), "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", package, serial=serial)
        component = output.splitlines()[-1]
        if "/" not in component:
            raise AdbError('This app does not have a splash screen. Use "Details" on Android.')
        return self.run("shell", "am", "start", "--user", str(user), "-n", component, serial=serial)

    def export(self, serial: str, user: int, packages: list[Package], folder: str, progress: Callable) -> list[Outcome]:
        results = []
        for i, p in enumerate(packages):
            progress(i, len(packages), "Exportando " + p.title)
            try:
                paths = self.run("shell", "pm", "path", "--user", str(user), p.name, serial=serial)
                paths = [x[8:] for x in paths.splitlines() if x.startswith("package:")]
                if not paths:
                    raise AdbError("No APK found for this package.")
                dest = Path(folder) / p.name
                dest.mkdir(parents=True, exist_ok=True)
                files = []
                for remote in paths:
                    target = dest / Path(remote).name
                    self.run("pull", remote, str(target), serial=serial, timeout=180)
                    files.append({"file": target.name, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
                (dest / "manifest.json").write_text(json.dumps({"package":p.name,"label":p.title,"version":p.version,"files":files,"includes_app_data":False},indent=2,ensure_ascii=False),encoding="utf-8")
                results.append(Outcome(p.name, "ok", f"{len(files)} APK(s) saved to {dest}"))
            except (AdbError, OSError) as exc:
                results.append(Outcome(p.name,"error",str(exc)))
        return results

    def install(self, serial: str, user: int, files: list[str], split: bool, progress: Callable) -> list[Outcome]:
        groups = [files] if split else [[x] for x in files]
        results = []
        for i, group in enumerate(groups):
            progress(i, len(groups), "Instalando " + Path(group[0]).name)
            try:
                command = "install-multiple" if split else "install"
                out = self.run(command, "-r", "--user", str(user), *group, serial=serial, timeout=240)
                if "Success" not in out:
                    raise AdbError(out or 'Android did not confirm the installation.')
                self.cache_file(serial,user).unlink(missing_ok=True)
                results.append(Outcome(Path(group[0]).name,"ok","Installed."))
            except AdbError as exc:
                results.append(Outcome(Path(group[0]).name,"error",str(exc)))
        return results

    def permissions(self, serial: str, user: int, package: str) -> list[tuple[str, bool, str]]:
        output = self.run("shell","dumpsys","package",package,serial=serial,quiet=True)
        active_user = False
        rows = {}
        requested = set()
        in_package = False
        in_requested = False
        for line in output.splitlines():
            if re.match(r"\s*Package \[",line):
                if in_package: break
                in_package = True
            if not in_package: continue
            if line.strip()=="requested permissions:":
                in_requested = True
                continue
            if in_requested:
                stripped=line.strip()
                if re.fullmatch(r"[\w.]+",stripped): requested.add(stripped)
                else: in_requested=False
            m = re.match(r"\s*User (\d+):",line)
            if m:
                active_user = int(m[1]) == user
            if line.strip() == "Hidden system packages:":
                break
            m = re.match(r"\s*(\S+): granted=(true|false), flags=\[([^]]*)\]",line)
            if m and active_user:
                rows[m[1]] = (m[2] == "true", m[3])
            elif not m and not active_user:
                m = re.match(r"\s*(\S+): granted=(true|false)$",line)
                if m: rows[m[1]]=(m[2]=="true",'Installation/System Permission')
        for name in requested: rows.setdefault(name,(False,"Declared by the app"))
        return [(name,*value) for name,value in sorted(rows.items())]

    def set_permission(self, serial: str, user: int, package: str, permission: str, grant: bool):
        self.validate_name(package)
        self.validate_name(permission)
        self.run("shell","pm","grant" if grant else "revoke","--user",str(user),package,permission,serial=serial)
        for attempt in range(5):
            rows = self.permissions(serial,user,package)
            if any(name==permission and granted==grant for name,granted,_ in rows):
                return rows
            if attempt < 4: time.sleep(0.15)
        raise AdbError('Android has not confirmed the permission change. Refresh the list to see the current status.')


def read_preset(path: str) -> set[str]:
    text = Path(path).read_text(encoding="utf-8-sig")
    return {line.strip() for line in text.splitlines() if re.fullmatch(r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+",line.strip())}
