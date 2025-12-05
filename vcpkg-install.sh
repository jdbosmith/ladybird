#!/usr/bin/env bash
set -euo pipefail

# Defaults (override by setting environment variables in CI or the shell)
TRIPLET=${TRIPLET:-x64-linux}
VCPKG_BIN=${VCPKG_BIN:-./Build/vcpkg/vcpkg}

if [ ! -x "${VCPKG_BIN}" ]; then
  echo "vcpkg binary not found at ${VCPKG_BIN}; aborting"
  ls -la "$(dirname "${VCPKG_BIN}")" || true
  exit 1
fi

echo "vcpkg version:"
${VCPKG_BIN} --version

# If a manifest is present, prefer manifest install so pins in vcpkg.json are respected.
if [ -f vcpkg.json ]; then
  echo "Installing vcpkg manifest dependencies (vcpkg.json) for triplet ${TRIPLET}"
  if ! ${VCPKG_BIN} install --triplet ${TRIPLET}; then
    echo "vcpkg manifest install failed — trying explicit Qt6 port install as a fallback"
    echo "Diagnostic: available qt ports (search):"
    ${VCPKG_BIN} search qt6 || true
    echo "Diagnostic: vcpkg list:"
    ${VCPKG_BIN} list || true

    # Fallback: explicitly install Qt6 ports that LibWeb (and other targets) require.
    # Adjust these ports if your project requires additional Qt ports.
    ${VCPKG_BIN} install qt6-base:${TRIPLET} qt6-webengine:${TRIPLET} || ( echo "vcpkg explicit install of Qt6 ports failed"; ${VCPKG_BIN} list; exit 1 )
  fi
else
  # Fallback: explicitly install Qt6 ports that LibWeb (and other targets) require.
  # Adjust the list below if your project requires additional Qt ports.
  echo "No vcpkg.json found; installing Qt6 ports explicitly into vcpkg for triplet ${TRIPLET}"
  ${VCPKG_BIN} install qt6-base:${TRIPLET} qt6-webengine:${TRIPLET} || ( echo "vcpkg install of Qt6 ports failed"; ${VCPKG_BIN} list; exit 1 )
fi

# Basic diagnostics to ensure Qt6 CMake config files are present for CMake
echo "vcpkg installed ports:"
${VCPKG_BIN} list || true
echo "Installed cmake config dirs:"
ls -la Build/vcpkg/installed/${TRIPLET}/lib/cmake || true
find Build/vcpkg/installed/${TRIPLET} -name "Qt6CoreConfig.cmake" -print || true