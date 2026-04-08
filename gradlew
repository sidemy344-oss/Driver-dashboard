#!/#!/usr/bin/env sh

# GitHub Build Starter Script
# This is a minimal wrapper to trigger the build engine.

# Find the project root
APP_HOME=$(pwd)
CLASSPATH=$APP_HOME/gradle/wrapper/gradle-wrapper.jar

# Run the build
exec java -classpath "$CLASSPATH" org.gradle.wrapper.GradleWrapperMain "$@"

