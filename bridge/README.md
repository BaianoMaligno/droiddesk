# DroidDesk Android Widgets

The collector reads data via `app_process`, using the shell's UID. The minimum requirement is Android 8/API 26. The compiled JAR file, located at `bin/droiddesk-metadata.jar`, is included with the program.

To recompile, you'll need the JDK and Google's official R8/D8:

```sh
DROIDDESK_R8_JAR=/caminho/r8lib.jar ./build.sh
```

You can also set `DROIDDESK_JAVA` and `DROIDDESK_JAVAC`. See the [official R8 release](https://r8.googlesource.com/r8/+/refs/heads/main/README.md).


`bin/droiddesk-packages.jar` contains the standalone user-removal helper. It is used automatically only for the specific system-removal error that requires root privileges in the standard command. It resolves the Android interface via reflection, uses `DELETE_SYSTEM_APP`, and checks for the absence of the package; it does not use numbered transactions or global uninstallation. Its `probe USER PACOTE keep` operation is read-only. The `uninstall USER PACOTE keep|clear` operation modifies the specified package and must be called by the backend after the interface has been confirmed.

The build compiles both helper functions. In this version, I used JDK 21 and R8 8.3.37. The minimum bytecode requirement is API 26, but the manufacturer may not provide the necessary APIs. See [physical validation and its limitations](../VALIDATION-0.2.2.md).

The collector reads the PackageManager and the apps' static resources, returning one JSON per line. After the query, Linux deletes the temporary JAR and stores the metadata in the local cache.
