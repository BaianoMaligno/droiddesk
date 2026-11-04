import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
import json

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adb_backend import parse_package_states, Adb, AdbError, Package

ROOT_ERROR = "Failure [only root can delete system app for a particular user]"


class SystemRemovalRegression(unittest.TestCase):
    def make_adb(self):
        adb = object.__new__(Adb)
        adb.log = Mock()
        adb.run = Mock()
        adb.package_set = Mock(return_value=set())
        return adb

    def test_restricted_system_removal_keeps_serial_user_and_data_choice(self):
        for keep in (True, False):
            adb = self.make_adb()
            adb.run.side_effect = AdbError(ROOT_ERROR)
            adb.remove_system_package = Mock()
            result = adb.action("device-B", 10, Package("org.example.app", system=True), "uninstall", keep)
            self.assertEqual(result.status, "ok")
            adb.remove_system_package.assert_called_once_with("device-B", 10, "org.example.app", keep)
            adb.package_set.assert_called_once_with("device-B", 10)

    def test_other_errors_and_user_apps_never_use_system_fallback(self):
        for system, error in ((False, ROOT_ERROR), (True, "DELETE_FAILED_USER_RESTRICTED")):
            adb = self.make_adb()
            adb.run.side_effect = AdbError(error)
            adb.remove_system_package = Mock()
            self.assertEqual(adb.action("A", 0, Package("org.example.app", system=system), "uninstall").status, "error")
            adb.remove_system_package.assert_not_called()

    def test_success_text_is_not_enough_if_package_remains_installed(self):
        adb = self.make_adb()
        adb.run.side_effect = AdbError(ROOT_ERROR)
        adb.remove_system_package = Mock()
        adb.package_set.return_value = {"org.example.app"}
        self.assertEqual(adb.action("A", 0, Package("org.example.app", system=True), "uninstall").status, "error")

    def test_old_platform_uses_normal_per_user_command(self):
        adb = self.make_adb()
        adb.remove_system_package = Mock()
        self.assertEqual(adb.action("A", 0, Package("org.example.app", system=True), "uninstall", True).status, "ok")
        adb.run.assert_called_once_with("shell", "pm", "uninstall", "-k", "--user", "0", "org.example.app", serial="A")
        adb.remove_system_package.assert_not_called()

    def test_helper_protocol_destination_and_cleanup(self):
        adb = self.make_adb()
        response = json.dumps(dict(protocol=1, removed=True, user=10, package="org.example.app"))
        adb.run.side_effect = ["", response, ""]
        adb.remove_system_package("B", 10, "org.example.app", True)
        calls = adb.run.call_args_list
        remote = calls[0].args[-1]
        self.assertTrue(remote.startswith("/data/local/tmp/droiddesk-packages-"))
        self.assertEqual(calls[1].args, ("shell", "CLASSPATH=" + remote, "app_process", "/system/bin", "DroidDeskPackages", "uninstall", "10", "org.example.app", "keep"))
        self.assertEqual(calls[2].args, ("shell", "rm", "-f", remote))
        self.assertTrue(all(call.kwargs["serial"] == "B" for call in calls))

    def test_invalid_helper_response_never_reports_success_and_always_cleans(self):
        for response in ("Success", "[]", '{"protocol":1,"removed":true,"user":0,"package":"org.other"}'):
            adb = self.make_adb()
            adb.run.side_effect = ["", response, ""]
            with self.assertRaises(AdbError): adb.remove_system_package("A", 10, "org.example.app", False)
            self.assertEqual(adb.run.call_args.args[:3], ("shell", "rm", "-f"))

    def test_cleanup_failure_does_not_hide_operation_error(self):
        adb = self.make_adb()
        adb.run.side_effect = ["", AdbError("operation refused"), AdbError("USB disconnected")]
        with self.assertRaisesRegex(AdbError, "operation refused"):
            adb.remove_system_package("A", 0, "org.example.app", False)
        adb.log.assert_called_once()

    def test_all_users_and_protected_packages_never_dispatch(self):
        adb = self.make_adb()
        for user in (-1, -2, "0", True):
            self.assertEqual(adb.action("A", user, Package("org.example.app"), "uninstall").status, "error")
        self.assertEqual(adb.action("A", 0, Package("android", protected=True), "uninstall").status, "blocked")
        adb.run.assert_not_called()


class PackageStateRegression(unittest.TestCase):
    def test_hidden_factory_record_cannot_override_active_user_record(self):
        dump = """Packages:
  Package [org.example.app] (1):
    User 0: installed=true enabled=3
      lastDisabledCaller: shell:2000
    User 10: installed=true enabled=1
Hidden system packages:
  Package [org.example.app] (2):
    User 0: installed=true enabled=0
    User 10: installed=true enabled=0
"""
        self.assertEqual(parse_package_states(dump,0),{"org.example.app":{"state":3,"caller":"shell:2000"}})
        self.assertEqual(parse_package_states(dump,10)["org.example.app"]["state"],1)

    def test_first_effective_default_wins_over_duplicate_saved_disabled_state(self):
        dump = """Packages:
  Package [org.example.app] (1):
    User 0: installed=true enabled=0
  Package [org.example.app] (2):
    User 0: installed=true enabled=3
"""
        self.assertEqual(parse_package_states(dump,0)["org.example.app"]["state"],0)

    def test_shell_fragments_are_not_package_names(self):
        for value in ("org.example; reboot", "org.example/app", "org.example\nother", "$(id)"):
            with self.assertRaises(AdbError): Adb.validate_name(value)


if __name__=="__main__":unittest.main()
