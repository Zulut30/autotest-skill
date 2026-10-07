#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
sdk="${ANDROID_HOME:-/workspace/.autotest-tools/android}"
output="$PWD/.autotest/android-build"
mkdir -p "$output/classes" "$output/dex"
chmod 700 "$output"
platform="$sdk/platforms/android-30/android.jar"
tools="$sdk/build-tools/35.0.0"
test -f "$platform" || { echo 'Android API 30 platform is required.' >&2; exit 2; }
java -m jdk.compiler/com.sun.tools.javac.Main -source 8 -target 8 -Xlint:-options -classpath "$platform" -d "$output/classes" fixtures/android/src/com/autotest/demo/*.java
java -m jdk.jartool/sun.tools.jar.Main cf "$output/classes.jar" -C "$output/classes" .
"$tools/d8" --lib "$platform" --min-api 26 --output "$output/dex" "$output/classes.jar"
"$tools/aapt2" link -o "$output/unsigned.apk" -I "$platform" --manifest fixtures/android/AndroidManifest.xml --min-sdk-version 26 --target-sdk-version 30
.venv/bin/python - "$output" <<'PY'
import sys,zipfile,pathlib
root=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(root/'unsigned.apk','a') as archive:archive.write(root/'dex'/'classes.dex','classes.dex')
PY
"$tools/zipalign" -f 4 "$output/unsigned.apk" "$output/aligned.apk"
if [ ! -f "$output/debug.keystore" ]; then
 keytool -genkeypair -keystore "$output/debug.keystore" -storepass android -keypass android -alias androiddebugkey -dname 'CN=Autotest Demo' -keyalg RSA -keysize 2048 -validity 3650 -noprompt
fi
"$tools/apksigner" sign --ks "$output/debug.keystore" --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out "$output/autotest-demo.apk" "$output/aligned.apk"
"$tools/apksigner" verify --verbose "$output/autotest-demo.apk"
.venv/bin/python - "$output/autotest-demo.apk" <<'PY'
import hashlib,sys,pathlib
path=pathlib.Path(sys.argv[1]);print('Built demo APK:',path);print('SHA256:',hashlib.sha256(path.read_bytes()).hexdigest())
PY
