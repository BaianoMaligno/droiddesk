#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
: "${DROIDDESK_R8_JAR:?Set DROIDDESK_R8_JAR to the path of the official Google r8lib.jar}"
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
mkdir -p bin
for component in Metadata Packages; do
    "${DROIDDESK_JAVAC:-javac}" --release 8 -d "$build_dir" "src/DroidDesk${component}.java"
    name=$(printf '%s' "$component" | tr '[:upper:]' '[:lower:]')
    "${DROIDDESK_JAVA:-java}" -cp "$DROIDDESK_R8_JAR" com.android.tools.r8.D8 --min-api 26 --output "bin/droiddesk-${name}.jar" "$build_dir/DroidDesk${component}.class"
done
