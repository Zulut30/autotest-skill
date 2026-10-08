#!/usr/bin/env python3
"""Install official Android/Appium tools into task-owned paths with verification."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

repo=Path(__file__).resolve().parents[1]
root=Path(os.environ.get('AUTOTEST_TOOLS_DIR',str(repo/'.autotest/tools'))).resolve()
root.mkdir(parents=True,exist_ok=True)
sdk=root/'android';sdk.mkdir(exist_ok=True)
versions=json.loads((repo/'scripts/tool-versions.json').read_text())
artifact=versions['android_command_line_tools'];tools=sdk/'cmdline-tools/latest'
if not tools.is_dir():
 archive=sdk/artifact['filename']
 if not archive.is_file():
  with urllib.request.urlopen('https://dl.google.com/android/repository/'+artifact['filename'],timeout=60) as response,archive.open('wb') as output:
   while chunk:=response.read(1024*1024):output.write(chunk)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=artifact['sha256']:raise SystemExit('Official Android archive checksum mismatch')
 staging=sdk/'unpack';staging.mkdir()
 with zipfile.ZipFile(archive) as source:
  for member in source.infolist():
   destination=(staging/member.filename).resolve()
   if staging.resolve() not in destination.parents:raise SystemExit('Unsafe archive member')
  source.extractall(staging)
 tools.parent.mkdir(exist_ok=True);(staging/'cmdline-tools').rename(tools)
 for path in (tools/'bin').iterdir():path.chmod(path.stat().st_mode|0o111)
for name in ['android-user','java-home','avd','appium-home','npm-cache']:(root/name).mkdir(exist_ok=True)
env={**os.environ,'ANDROID_HOME':str(sdk),'ANDROID_SDK_ROOT':str(sdk),'ANDROID_USER_HOME':str(root/'android-user'),
 'ANDROID_SDK_HOME':str(root),'JAVA_TOOL_OPTIONS':'-Duser.home='+str(root/'java-home'),'APPIUM_HOME':str(root/'appium-home')}
subprocess.run([str(tools/'bin/android'),'--no-metrics','--sdk='+str(sdk),'sdk','install','platform-tools','emulator',
 'platforms;android-30','build-tools;35.0.0','system-images;android-26;default;x86'],check=True,env=env)
subprocess.run(['npm','install','--prefix',str(root/'appium'),'--cache',str(root/'npm-cache'),'--no-audit','--no-fund','appium@'+versions['appium']],check=True,env=env)
appium=root/'appium/node_modules/.bin/appium'
listing=subprocess.run([str(appium),'driver','list','--installed','--json'],capture_output=True,text=True,check=True,env=env)
installed=json.loads(listing.stdout)
if 'uiautomator2' not in installed:
 subprocess.run([str(appium),'driver','install','uiautomator2@'+versions['uiautomator2']],check=True,env=env)
(root/'android-installed.json').write_text(json.dumps({'sdk':str(sdk),'requested_versions':versions,
 'note':'SDK manager uses verified official package metadata. Actual SDK versions are recorded in source.properties; no trust checks disabled.'},indent=2)+'\n')
print('Verified Android tools installed. Export AUTOTEST_TOOLS_DIR='+str(root)+' and run scripts/start_android.sh.')
