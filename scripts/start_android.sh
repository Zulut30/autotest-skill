#!/usr/bin/env bash
set -eu
source "$(dirname "$0")/android_env.sh"
cd "$AUTOTEST_REPO_ROOT"
for tool in "$ANDROID_HOME/emulator/emulator" "$ANDROID_HOME/platform-tools/adb" "$AUTOTEST_TOOLS_DIR/appium/node_modules/.bin/appium"; do
 test -x "$tool" || { echo "Required tool is missing: $tool" >&2; exit 2; }
done
test -f "$ANDROID_HOME/system-images/android-26/default/x86/system.img" || { echo 'Install the verified API26 default x86 image first.' >&2; exit 2; }
mkdir -p "$ANDROID_AVD_HOME/autotest-api26.avd" "$ANDROID_USER_HOME" "$AUTOTEST_TOOLS_DIR/java-home" .autotest/native-logs
if [ ! -f "$ANDROID_AVD_HOME/autotest-api26.avd/config.ini" ]; then
 cat > "$ANDROID_AVD_HOME/autotest-api26.avd/config.ini" <<AVD
AvdId=autotest-api26
PlayStore.enabled=no
abi.type=x86
avd.ini.encoding=UTF-8
hw.cpu.arch=x86
hw.cpu.ncore=2
hw.ramSize=1536
image.sysdir.1=$ANDROID_HOME/system-images/android-26/default/x86/
tag.id=default
hw.lcd.width=480
hw.lcd.height=800
hw.lcd.density=160
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader
hw.keyboard=yes
hw.sdCard=no
skin.name=480x800
fastboot.forceColdBoot=yes
showDeviceFrame=no
disk.dataPartition.size=2G
AVD
 cat > "$ANDROID_AVD_HOME/autotest-api26.ini" <<AVD
avd.ini.encoding=UTF-8
path=$ANDROID_AVD_HOME/autotest-api26.avd
target=android-26
AVD
fi
if ! adb -s emulator-5554 get-state >/dev/null 2>&1; then
 acceleration=off
 [ ! -r /dev/kvm ] || acceleration=auto
 nohup emulator -avd autotest-api26 -port 5554 -accel "$acceleration" -gpu swiftshader -no-window -no-audio -no-boot-anim -no-snapshot -no-metrics -memory 1536 -cores 2 -netfast > .autotest/native-logs/emulator.log 2>&1 &
 echo "$!" > .autotest/native-logs/emulator.pid
fi
.venv/bin/python - <<'PY'
import subprocess,time
for attempt in range(120):
 try:
  r=subprocess.run(['adb','-s','emulator-5554','shell','getprop','sys.boot_completed'],capture_output=True,text=True,timeout=5,check=False)
  if r.returncode==0 and r.stdout.strip()=='1':break
 except subprocess.TimeoutExpired:pass
 time.sleep(3)
else:raise SystemExit('Android did not boot; inspect .autotest/native-logs/emulator.log')
print('Android boot completed; semantic app readiness still requires a native scenario.')
PY
if ! .venv/bin/python - <<'PY'
import httpx,sys
try:
 response=httpx.get('http://127.0.0.1:4723/status',timeout=3)
 sys.exit(0 if response.status_code==200 and response.json().get('value',{}).get('ready') else 2)
except (httpx.HTTPError,ValueError):sys.exit(2)
PY
then
 nohup appium --address 127.0.0.1 --port 4723 --log-level warn --log-no-colors > .autotest/native-logs/appium.log 2>&1 &
 echo "$!" > .autotest/native-logs/appium.pid
fi
