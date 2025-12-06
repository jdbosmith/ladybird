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
import sys


def build_vcpkg():
    script_dir = pathlib.Path(__file__).parent.resolve()

    with open(script_dir.parent / "vcpkg.json", "r") as vcpkg_json_file:
        vcpkg_json = json.load(vcpkg_json_file)

    git_repo = "https://github.com/microsoft/vcpkg.git"
    git_rev = vcpkg_json["builtin-baseline"]

    build_dir = script_dir.parent / "Build"
    build_dir.mkdir(parents=True, exist_ok=True)
    vcpkg_checkout = build_dir / "vcpkg"

    # Ensure a fresh checkout to avoid stale/partial repos causing git errors
    if vcpkg_checkout.is_dir():
        print(f"Removing existing {vcpkg_checkout} to ensure fresh clone")
        shutil.rmtree(vcpkg_checkout)

    # Try a shallow clone and a targeted fetch for the requested revision (fast path).
    # If that fails, fall back to a full clone so all git objects are available.
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", git_repo, str(vcpkg_checkout)], cwd=build_dir)
        try:
            subprocess.check_call(["git", "fetch", "--depth", "1", "origin", git_rev], cwd=vcpkg_checkout)
        except subprocess.CalledProcessError:
            print(f"Warning: targeted shallow fetch of {git_rev} failed; attempting to unshallow/fetch full history")
            # Unshallow and fetch full history
            try:
                subprocess.check_call(["git", "fetch", "--unshallow", "origin"], cwd=vcpkg_checkout)
            except subprocess.CalledProcessError:
                # If unshallow isn't supported, just fetch origin
                subprocess.check_call(["git", "fetch", "origin"], cwd=vcpkg_checkout)
    except subprocess.CalledProcessError:
        # If shallow clone failed for any reason, do a full clone
        if vcpkg_checkout.is_dir():
            shutil.rmtree(vcpkg_checkout)
        print("Shallow clone failed; performing full clone of vcpkg")
        subprocess.check_call(["git", "clone", git_repo, str(vcpkg_checkout)], cwd=build_dir)

    # Ensure the working tree is clean before attempting checkout
    subprocess.check_call(["git", "reset", "--hard"], cwd=vcpkg_checkout)
    subprocess.check_call(["git", "clean", "-fdx"], cwd=vcpkg_checkout)

    # Try to checkout the exact requested revision. If it fails, fetch all refs and retry.
    try:
        subprocess.check_call(["git", "checkout", git_rev], cwd=vcpkg_checkout)
    except subprocess.CalledProcessError:
        print(f"Warning: checkout of {git_rev} failed; fetching all refs and retrying")
        subprocess.check_call(["git", "fetch", "origin"], cwd=vcpkg_checkout)
        try:
            subprocess.check_call(["git", "checkout", git_rev], cwd=vcpkg_checkout)
        except subprocess.CalledProcessError:
            # Check whether the commit exists on upstream; if not, bail with a clear message
            try:
                ls_remote = subprocess.check_output(["git", "ls-remote", git_repo, git_rev]).strip()
            except subprocess.CalledProcessError:
                ls_remote = b""

            if not ls_remote:
                print(f"ERROR: requested vcpkg revision {git_rev} not found on remote {git_repo}.")
                print("Please update vcpkg.json builtin-baseline to a commit present on the vcpkg upstream or use a vcpkg fork that contains this commit.")
                sys.exit(1)
            else:
                # If it is present upstream but checkout still failed, re-clone full repo and retry once
                print("Commit exists on remote; re-cloning full repository and retrying checkout")
                if vcpkg_checkout.is_dir():
                    shutil.rmtree(vcpkg_checkout)
                subprocess.check_call(["git", "clone", git_repo, str(vcpkg_checkout)], cwd=build_dir)
                subprocess.check_call(["git", "fetch", "origin"], cwd=vcpkg_checkout)
                subprocess.check_call(["git", "checkout", git_rev], cwd=vcpkg_checkout)

    bootstrap_script = "bootstrap-vcpkg.bat" if os.name == "nt" else "bootstrap-vcpkg.sh"
    subprocess.check_call([str(vcpkg_checkout / bootstrap_script), "-disableMetrics"], cwd=vcpkg_checkout)


def main():
    build_vcpkg()


if __name__ == "__main__":
    main()