#!/usr/bin/env python3

# Copyright (c) 2024, pheonixfirewingz <luke.a.shore@proton.me>
# Copyright (c) 2024-2025, Tim Flynn <trflynn89@ladybird.org>
#
# SPDX-License-Identifier: BSD-2-Clause

import json
import os
import pathlib
import subprocess
import shutil


def build_vcpkg():
    script_dir = pathlib.Path(__file__).parent.resolve()

    with open(script_dir.parent / "vcpkg.json", "r") as vcpkg_json_file:
        vcpkg_json = json.load(vcpkg_json_file)

    git_repo = "https://github.com/microsoft/vcpkg.git"
    git_rev = vcpkg_json["builtin-baseline"]

    build_dir = script_dir.parent / "Build"
    build_dir.mkdir(parents=True, exist_ok=True)
    vcpkg_checkout = build_dir / "vcpkg"

    if not vcpkg_checkout.is_dir():
        subprocess.check_call(args=["git", "clone", git_repo], cwd=build_dir)
    else:
        bootstrapped_vcpkg_version = (
            subprocess.check_output(["git", "-C", vcpkg_checkout, "rev-parse", "HEAD"]).strip().decode()
        )

        if bootstrapped_vcpkg_version == git_rev:
            return

    print(f"Building vcpkg@{git_rev}")

    # Try to fetch only the requested revision first (faster)
    try:
        subprocess.check_call(args=["git", "fetch", "--depth", "1", "origin", git_rev], cwd=vcpkg_checkout)
    except subprocess.CalledProcessError:
        # If that fails, fallback to a full fetch so the commit can be found
        print(f"Warning: shallow fetch of {git_rev} failed; fetching full origin")
        subprocess.check_call(args=["git", "fetch", "origin"], cwd=vcpkg_checkout)

    # Try to checkout the requested revision. If it's still not available, fall back to origin/master (or origin/main).
    try:
        subprocess.check_call(args=["git", "checkout", git_rev], cwd=vcpkg_checkout)
    except subprocess.CalledProcessError:
        print(f"Warning: requested vcpkg revision {git_rev} not found after fetch; falling back to origin/master")
        # Try common default branches to maximise chance of success
        for branch in ("origin/master", "origin/main"):
            try:
                subprocess.check_call(args=["git", "checkout", branch], cwd=vcpkg_checkout)
                break
            except subprocess.CalledProcessError:
                continue
        else:
            # If no fallback branch worked, propagate the original error
            raise

    bootstrap_script = "bootstrap-vcpkg.bat" if os.name == "nt" else "bootstrap-vcpkg.sh"
    subprocess.check_call(args=[vcpkg_checkout / bootstrap_script, "-disableMetrics"], cwd=vcpkg_checkout)


def main():
    build_vcpkg()


if __name__ == "__main__":
    main()
