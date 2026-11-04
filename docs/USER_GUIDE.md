# User Guide

## Device, Filter, and Labeling

Check the device and Android user on the side before taking any action. Switching devices or profiles clears the selections. The **Active**, **System**, and **User** filters show active apps; **Disabled** groups apps by their disabled status; **Removed** shows known system apps that are not installed for that user. **All** displays the entire available catalog.

The search accepts either a name or a package. Clicking on a row opens the details; **the checkboxes define the batch**. Use “Select Visible,” “Clear Selections,” double-click, or the Space bar. Items not included in the filter remain in the batch, and their quantity is shown. The selected action does not change when you refresh the list or change the filter.

## Uninstall

1. Select the apps you want.
2. Click **Uninstall…**.
3. Review all packages, the device, and the user in the confirmation.
4. Choose whether you want to keep the data and save the APKs before removal.
5. Confirm the copy folder and click **Uninstall**.
6. Read the individual result: completed, failed, protected, or ignored.

The option to save APKs includes the base APK and splits. If copying a package fails, it is preserved. The saved manifest contains the file names and SHA-256 values. **This copy does not contain the app's private data.** Keeping data on the device is another option; it does not turn the APK copy into a data backup.

The program uses `pm uninstall --user <id>` and then checks the list of installed apps again. Essential apps protected by the program, the current launcher, and the current keyboard are blocked from destructive operations. This protection is a limited list, not a complete catalog of everything the manufacturer considers essential.

Canceling the confirmation does not send a removal command. The cancellation is displayed and logged.



## Deactivate, Reactivate, and Restore

| Status | Action | Limit |
|---|---|---|
| App installed and active | Disable | Force stop, disable for this profile, and check |
| Disabled by the user (`3`) | Re-enable | Confirm return to the list of active items |
| Disabled by the system (`2`) or deep sleep (`4`) | Details on Android | On the tested Android 16, reactivation via the shell is denied |
| System app removed from profile | Restore | Uses `install-existing`; must remain recognized by the system |
| Third-party app removed | Reinstall APKs or from the store | Does not appear as an automatic system app restore |


## Install APKs and splits

On the Installation tab, add files, a folder, or drag and drop APKs. For standalone apps, leave the "splits" option unchecked. For the base + splits of **the same app**, check the option and keep only the files for that app in the queue. The commands use the selected user and require a successful response from Android.

## Presets and Permissions

Presets are text lists of package names. Loading a preset highlights the names found; it does not perform any actions. Saving saves the current highlights.

The Permissions panel reads the declared permissions and available statuses. Granting or revoking permissions requires Android to authorize the operation. The result is re-read to confirm the change. Common permissions granted during installation and runtime permissions are not interchangeable; any error should be checked in the result.

## Console, Tools, and Appearance

The console sends commands to the selected device. `shell` opens an interactive session; `exit` closes it. Logcat can be started and stopped. Fastboot mode uses self-discovery and depends on the executable and device support.

The tools offer screenshot capture, sending to Downloads, scrcpy integration, viewing/changing resolution and density, status bar icons, and restarting. Refer to the [test matrix](../FEATURES.md) before interpreting a button implemented as a validated resource in your model.

The **Dark Theme / Light Theme** toggle is located at the bottom of the sidebar and saves your preference. The theme applies to lists, details, menus, scrolling, and confirmation messages.

## Where are the files located?

| Content | Default Location |
|---|---|
| Names, icons, and metadata by device/profile | `~/.cache/droiddesk/` |
| Commands and results by day | `~/.cache/droiddesk/logs/` |
| Theme preference | QSettings; usually `~/.config/DroidDesk/DroidDesk.conf` |
| User shortcut | `~/.local/share/applications/droiddesk.desktop` |
| Suggested copies to keep when deleting | `~/Documents/DroidDesk/Backups/<data-hora>/` |
| Export and captures | Folder selected in the interface |

Logs may contain package names, identifiers, and command output. When reporting an error, include the relevant portion of the operation and the result, rather than assuming that a loaded catalog proves the action was executed.

Android versions 2 and 4 may prevent reactivation via the shell. Use the details action to open the app's settings on the device. The message `ComponentName null` does not indicate an empty selection.
