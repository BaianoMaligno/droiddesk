"""Opt-in physical test, restricted to Android's Easter Egg system package.

Removes it for the explicit user with KEEP_DATA, then restores installation and
enabled state in finally. Never suitable for an essential or user-selected app.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adb_backend import Adb, Package, parse_package_states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--user", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-physical-test", action="store_true", required=True)
    args = parser.parse_args()
    if args.user < 0:
        parser.error("user must be nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    logs = []
    adb = Adb(logs.append)
    serial, user, name = args.serial, args.user, "com.android.egg"
    installed = adb.package_set(serial, user)
    systems = adb.package_set(serial, user, "-s")
    assert name in installed & systems, "Easter Egg must already be installed and system"
    dump = adb.run("shell", "dumpsys", "package", name, serial=serial, quiet=True)
    state = parse_package_states(dump, user)[name]["state"]
    assert state in {0, 1, 3}, "Refuse to alter a system-managed disabled state"
    package = Package(name, system=True)
    backup = adb.export(serial, user, [package], str(args.output / "backup"), lambda *a: None)
    assert backup[0].status == "ok", backup[0].message
    info = adb.info(serial)
    info.pop("serial", None)
    report = dict(time=datetime.now(timezone.utc).isoformat(), device=info, user=user,
                  package=name, original_enabled_state=state, keep_data=True,
                  original_installed_count=len(installed), helper_removal_verified=False,
                  restoration_verified=False, tested_path="direct IPackageManager helper",
                  shell_root_restriction_reproduced=False)
    try:
        adb.remove_system_package(serial, user, name, True)
        after = adb.package_set(serial, user)
        assert name not in after, "Package remains installed"
        assert after == installed - {name}, "Unexpected change to other package installations"
        report["helper_removal_verified"] = True
    finally:
        try:
            result = adb.action(serial, user, Package(name, system=True, installed=False), "restore")
            assert result.status == "ok", result.message
            command = {0: "default-state", 1: "enable", 3: "disable-user"}[state]
            adb.run("shell", "pm", command, "--user", str(user), name, serial=serial)
            restored = adb.package_set(serial, user)
            final_dump = adb.run("shell", "dumpsys", "package", name, serial=serial, quiet=True)
            assert restored == installed, "Installed package set differs after restoration"
            assert parse_package_states(final_dump, user)[name]["state"] == state
            report["restoration_verified"] = True
        finally:
            (args.output / "validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
            (args.output / "commands.log").write_text("\n".join(logs))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
