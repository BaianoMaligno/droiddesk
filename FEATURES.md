# DroidDesk Features and Coverage

| Feature | DroidDesk 0.3.0 | Validation |
|---|---|---|
| List, names, icons, and versions | Implemented with a custom collector | Real tablet |
| APK and split sizes | Implemented | Actual metadata |
| Light and dark themes | Full palette and saved preferences | Rendering of both themes with a real catalog |
| Search by name/package and filters | Implemented | Qt with actual catalog |
| Explicit Android user and device | Implemented | User 0 on tablet; additional profiles not available |
| Disable and re-enable per user | Implemented and verified after command | Cycle with disposable app |
| States 2/3/4 and deep sleep | Categorized, with rejected states redirected to the Android screen | Actual reading and Zul+ screen |
| Remove and retain data | Implemented; retaining data is an option | Removal via the interface with or without retaining data; disposable app |
| Remove a system app when the standard command requires root | Alternative using the Android API with an explicit user | Tested on SM-X520/Android 16; the original error on SM-F766B still requires physical verification |
| Restore removed system app | Implemented using `install-existing` and verification | Easter Egg removed and restored, including previous state and complete list |
| Base backup + splits | Implemented, with manifest and hashes | Two APKs exported and reinstalled |
| Backup before uninstallation | Implemented; backup failure preserves the package | Button, confirmation, copy, and removal on the tablet; simulated copy failure preserves the package |
| Batch installation / splits | Implemented | Simple APK and base + split |
| Presets | Reading and Writing Text | Parser and Local Tagging |
| Permissions | Declared, installed, and runtime; subsequent verification | Grant/revoke POST_NOTIFICATIONS in a disposable app |
| Clear data / force stop | Implemented | Clears data for the disposable app; stop used in the deactivation cycle |
| Console, shell, and logcat | Implemented in separate processes | Window and read commands; no long-running logcat session |
| Screenshot | Implemented | Tablet control and PNG signature |
| File Upload | Implemented | Not tested in this validation |
| Wi-Fi / Pairing | Implemented | Physical connection validated via USB; wireless pairing not tested |
| Resolution, density, status icons, and reboot | Implemented with confirmation | Query commands; screen changes and reboot not executed |
| Scrcpy / Fastboot | Integration with installed Linux executables | Optional dependencies missing; no physical testing |

The implemented support does not guarantee that a manufacturer will authorize all commands. Android remains responsible for deciding whether to allow, deny, or require on-screen interaction.
