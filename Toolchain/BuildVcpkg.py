#!/usr/bin/env python3

# Copyright (c) 2024, pheonixfirewingz <luke.a.shore@proton.me>
# Copyright (c) 2024-2025, Tim Flynn <trflynn89@ladybird.org>
#
# SPDX-License-Identifier: BSD-2-Clause

import json
import os
import pathlib
import subprocess



def build_vcpkg():
    script_dir = pathlib.Path(__file__).parent.resolve()

    with open(script_dir.parent / "vcpkg.json", "r") as vcpkg_json_file:
        vcpkg_json = json.load(vcpkg_json_file)

    git_repo = "https://github.com/microsoft/vcpkg.git"
    git_rev = vcpkg_json["builtin-baseline"]

    build_dir = script_dir.parent / "Build"
    build_dir.mkdir(parents=True, exist_ok=True)
    vcpkg_checkout = build_dir / "vcpkg"

 # Always start with a fresh checkout to avoid stale/partial repos causing git errors
if vcpkg_checkout.is_dir():
    print(f"Removing existing {vcpkg_checkout} to ensure fresh clone")
    shutil.rmtree(vcpkg_checkout)

# Attempt a shallow clone and a targeted fetch for the requested revision (fast path).
# If any step fails, fall back to a full clone so all git objects are available.
try:
    subprocess.check_call(args=["git", "clone", "--depth", "1", git_repo, str(vcpkg_checkout)], cwd=build_dir)
    try:
        subprocess.check_call(args=["git", "fetch", "--depth", "1", "origin", git_rev], cwd=vcpkg_checkout)
    except subprocess.CalledProcessError:
        print(f"Warning: targeted shallow fetch of {git_rev} failed; attempting to unshallow/fetch full history")
        subprocess.check_call(args=["git", "fetch", "--unshallow", "origin"], cwd=vcpkg_checkout)
        subprocess.check_call(args=["git", "fetch", "origin"], cwd=vcpkg_checkout)
except subprocess.CalledProcessError:
    # If shallow clone failed for any reason, do a full clone
    if vcpkg_checkout.is_dir():
        shutil.rmtree(vcpkg_checkout)
    print("Shallow clone failed; performing full clone of vcpkg")
    subprocess.check_call(args=["git", "clone", git_repo, str(vcpkg_checkout)], cwd=build_dir)

# Ensure the working tree is clean before attempting checkout
subprocess.check_call(args=["git", "reset", "--hard"], cwd=vcpkg_checkout)
subprocess.check_call(args=["git", "clean", "-fdx"], cwd=vcpkg_checkout)

# Try to checkout the exact requested revision. If it fails, fetch all refs and retry.
try:
    subprocess.check_call(args=["git", "checkout", git_rev], cwd=vcpkg_checkout)
except subprocess.CalledProcessError:
    print(f"Warning: checkout of {git_rev} failed; fetching all refs and retrying")
    subprocess.check_call(args=["git", "fetch", "origin"], cwd=vcpkg_checkout)
    subprocess.check_call(args=["git", "checkout", git_rev], cwd=vcpkg_checkout)

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
