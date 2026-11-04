# DroidDesk 0.2 Validation

Date: 10/26/2026. Physical device: Samsung SM-X520, Android 16/API 36, user 0, USB connection authorized.

## Catalog and Interface

The independent collector read 565 entries with names and icons during its first full run. In the subsequent interface check, the installed catalog contained 564 apps, all with metadata. The count may change depending on device usage.

The Qt window loaded the catalog in approximately 4 seconds, with 182 interface timer cycles during background reading. We tested filters, name search, Gmail/Messages statuses, tagging, and blocking execution without tags. The previews were rendered using the tablet's actual data.

The rollback of hidden factory records was handled by local tests: the saved state does not override the actual state, and the Android user is respected.

## Physical cycle with disposable package

`org.droiddesk.validation` was created and installed locally, with no app code, no network access, and only the notifications permission declared. The package did not exist on the device prior to the test.

The following passed:

1. Simple APK installation.
2. Deactivation and status confirmation 3.
3. Reactivation and confirmation on the list of assets.
4. Granting and revoking POST_NOTIFICATIONS, with a status check.
5. Clearing the test package data.
6. Uninstallation by the user and verification that the software is no longer present.
7. Basic installation + split system installed using the same key.
8. Export the two APKs with the manifest and SHA-256.
9. Uninstalling and reinstalling using the exported APKs.
10. Final removal of the validation package and confirmation that it is no longer on the `-u` list.

The first round detected that the permissions had not yet been updated; the permissions operation then confirmed the status with limited re-reads. The next full round passed. No user applications were disabled or removed during these tests of version 0.2.

## Limits

No reboots, resolution/density changes, status bar icon changes, Wi-Fi pairing, or Fastboot commands were performed. Restoring a removed system app was not physically tested because there was no package in that state. The complete coverage table is in FEATURES.md.
