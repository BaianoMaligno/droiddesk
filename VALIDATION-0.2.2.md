# Validation 0.2.2 — Removal of System Apps

## Observed Failure

The user-submitted screenshot and the local log show that `pm uninstall --user 0` was rejected with the error `Failure [only root can delete system app for a particular user]`. The log identifies a Samsung SM-F766B. At the time of testing this version, only the SM-X520 was connected. We were unable to confirm the Android version or reproduce the error on the SM-F766B.


## Independent Implementation

The standard procedure remains `pm uninstall [-k] --user ID PACOTE`. Only when the response includes that restriction and the catalog identifies a system app does DroidDesk run its `DroidDeskPackages` helper via `app_process`, under the shell identity already authorized by ADB.

The helper checks the package for the specified user, confirms that it is a system app, and calls `IPackageManager.deletePackageAsUser` with `DELETE_SYSTEM_APP`, adding `DELETE_KEEP_DATA` when selected. It does not use `DELETE_ALL_USERS`, fixed Binder transaction numbers, root privileges, proprietary components, or the userless approach that can remove updates globally.

The call is asynchronous. The helper waits up to 15 seconds for the packet to arrive, returns the packet/user in JSON, and Linux checks the installed list again before reporting success. The API may change or be discontinued by the manufacturer; in such cases, the result remains a failure, without replacing removal with deactivation.

References: [AOSP IPackageManager interface](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/content/pm/IPackageManager.aidl), [legacy observer wrapper](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/main/core/java/android/content/pm/PackageManager.java) and [package service](https://github.com/aosp-mirror/platform_frameworks_base/blob/main/services/core/java/com/android/server/pm/IPackageManagerBase.java). The interface allows for a null legacy observer; the service wraps it before dispatching the operation. The result is checked via a query, not through an assumed callback.

## Physical Test Conducted

[JSON Evidence](docs/evidence/validation-0.2.2.json), without a serial identifier or personal name.

- Samsung SM-X520, Android 16/API 36, user 0.
- Non-essential system package: `com.android.egg`, the Android Easter Egg.
- APK copy completed before the operation; data preserved.
- The action was executed directly, with the actual removal confirmed in the user's list.
- Restored using `install-existing`; original state `DEFAULT (0)` restored.
- The initial list of 556 packages and the final list were identical. During the removal process, the only difference was the Easter Egg.
- The root restriction **could not be reproduced** on this tablet. The test confirms the issue on Android 16, not the result on the disconnected phone.

The test can be manually rerun using `tests/validate_system_removal.py --serial SERIAL --user ID --output PASTA --run-physical-test`. It only accepts `com.android.egg`, requires that it be already installed as a system app, saves the APK, and performs the restore in the `finally` block. A connection interruption may prevent immediate restoration; check the report and reconnect the same device before retrying.

## Automatic Regression

`QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v`: **17 tests passed**.

New coverage: accurate fault detection, preservation of device/user/data, other errors without undue attempts, normal path preserved, still-installed package treated as a fault, helper response validated, temporary cleanup, and global user rejection. The six interface regressions and the three package reader regressions remain approved.

## Limits and the Next Test

On the SM-F766B, reconnect, refresh the list, and repeat the removal as intended by the user. Check both the result and the “Removed” list. Do not announce Android 17 compatibility or a final resolution for this device before this test. Additional profiles and system removal without preserving data were not physically tested in this round.
