#!/usr/bin/env bash
# Source this in bash before running Android tools.
AUTOTEST_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOTEST_TOOLS_DIR="${AUTOTEST_TOOLS_DIR:-$AUTOTEST_REPO_ROOT/.autotest/tools}"
export ANDROID_HOME="${ANDROID_HOME:-$AUTOTEST_TOOLS_DIR/android}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export ANDROID_USER_HOME="$AUTOTEST_TOOLS_DIR/android-user"
export ANDROID_EMULATOR_HOME="$ANDROID_USER_HOME"
export ANDROID_AVD_HOME="$AUTOTEST_TOOLS_DIR/avd"
export APPIUM_HOME="$AUTOTEST_TOOLS_DIR/appium-home"
export JAVA_TOOL_OPTIONS="-Duser.home=$AUTOTEST_TOOLS_DIR/java-home"
export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$AUTOTEST_TOOLS_DIR/appium/node_modules/.bin:$PATH"
