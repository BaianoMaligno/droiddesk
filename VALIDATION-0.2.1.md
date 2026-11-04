# DroidDesk 0.2.1 — Uninstallation via the interface and themes

Date: October 26, 2026. SM-X520 tablet, Android 16, user 0.

## Confirmed diagnosis

The log for the reported attempt did not contain a `pm uninstall` command or an removal failure response. The screenshot showed the “Reactivate” action. It is not possible to attribute a specific Android failure to the user’s apps based on this log.

A regression was reproduced locally: selecting `uninstall` and refreshing the catalog caused `loaded → filter_changed` to override the selection with `disable` (or `enable`, in the "Disabled" filter). The test failed before the fix and passed afterward. Refreshes and filters now preserve the selected action.

The uninstallation process now features a dedicated button and a single confirmation screen that displays the packages, destination, data options, and copy folder. The previous workflow opened a second folder selector and exited silently if canceled. Now, cancellations and results for each package are displayed in the console and in the log.

## Physical Test via the Qt Interface

Run by `tests/validate_removal_ui.py`, with actual Qt clicks on the checkbox, action button, and confirmation button; real ADB backend, without simulation.

Only `org.droiddesk.validation` was used, generated from the local manifests, with no application code and no network access. The test verified that the package did not exist on any user's device before starting.

1. Install the base unit and the test split unit.
2. Select the item in the table, click "Uninstall," and confirm with "Copy" enabled.
3. Verify that it is not listed in user 0's installed list.
4. Verify the two APKs exported using the SHA256 hashes from the manifest.
5. Reinstall the exported APKs.
6. Disable only the test app and confirm status 3.
7. Select "Uninstall" from the list of actions, refresh the catalog, and verify that the action remains selected.
8. Remove via the interface while preserving data, without creating a copy; verify that the item is not present in the installed list but is present in the `-u` query.
9. Remove any remnants of the test app and verify that they are also absent in `-u`.

All steps were completed. No personal apps were removed, disabled, or re-enabled during this validation.

## Automatic regressions and appearance

`python3 -B -m unittest discover -s tests -v`: Nine tests passed, including checkbox selection, action preservation, cancellation without commands, empty folder, package copy failure, and theme preference. The copy failure is simulated: the package whose copy fails is preserved, the other continues, and both receive a result.

The light and dark interfaces were rendered and inspected using the tablet's actual interface, including the OneDrive panel, which appeared illegible in the submitted screenshot. The palette now explicitly defines the background and text for that panel, controls, and dialogs.

Versioned evidence: [structured report](docs/evidence/validation-0.2.1.json), and [current gallery](docs/SCREENSHOTS.md). The raw ADB log and test APKs are stored outside the repository.

## Limits of the Conclusion

The removal flow was validated with a disposable app that was enabled and disabled via ADB. No instances of a specific user app refusing removal were observed, as the log sent did not indicate an attempt to uninstall. After the fix, the user confirmed: “Everything is fine now.” This confirmation complements the tests, though it does not demonstrate full functionality parity. The limitations regarding the reactivation of states 2/4 and the coverage described in FEATURES.md remain applicable.
