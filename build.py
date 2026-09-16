# build.py
"""Interactive/CI build front-end for Tailscale & Headscale Client Pro.

Wraps the curated PyInstaller specs (which own the hidden imports, bundled data
and icons) instead of re-deriving their flags, so a local build cannot drift
from what CI produces.

    python build.py                 # interactive menu
    python build.py --target onedir # scriptable
    python build.py --target both --dist build_out --yes

Steps for each target: preflight (interpreter, PyInstaller, runtime imports),
clean that flavour's output folder, run PyInstaller against its spec, then
run the frozen executable's --self-test unless --no-verify is given.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIST = os.path.join(ROOT, "dist")

#: Runtime imports the frozen app needs; a missing one produces a broken bundle.
REQUIRED_IMPORTS = ("PySide6", "qt_material", "keyring", "psutil", "markdown", "pygments", "bs4")

#: spec -> (flavour folder, --distpath relative to the output root, artefact
#: relative to that distpath).
#: The onefile specs name only the executable, so its flavour folder must come
#: from --distpath; the one-dir/mac specs name their COLLECT/BUNDLE, and on
#: Windows/Linux that name *is* the flavour folder, so their distpath is the
#: root (".") and the payload lands directly in dist/OneDir/.
SPECS = {
    "win32": {
        "onefile": ("TailscaleClient_OneFile.spec", "OneFile", "OneFile", "Tailscale VPN Client Pro.exe"),
        "onedir": ("TailscaleClient_OneDir.spec", "OneDir", ".", os.path.join("OneDir", "Tailscale VPN Client Pro.exe")),
    },
    "darwin": {
        "onefile": ("TailscaleClient_OneFile.spec", "OneFile", "OneFile", "Tailscale VPN Client Pro"),
        "onedir": ("TailscaleClient_Mac.spec", "OneDir", "OneDir", "TailscaleClientPro.app"),
    },
    "linux": {
        "onefile": ("TailscaleClient_OneFile.spec", "OneFile", "OneFile", "Tailscale VPN Client Pro"),
        "onedir": ("TailscaleClient_OneDir.spec", "OneDir", ".", os.path.join("OneDir", "Tailscale VPN Client Pro")),
    },
}


def platform_key():
    if sys.platform == "win32":
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    return "linux"


def targets():
    return SPECS[platform_key()]


def flavour_dir(dist_root, target):
    """The folder this flavour owns under the output root; also the clean scope."""
    return os.path.join(dist_root, targets()[target][1])


def pyinstaller_distpath(dist_root, target):
    """--distpath for this flavour (see SPECS for why it is not always the flavour)."""
    return os.path.abspath(os.path.join(dist_root, targets()[target][2]))


def artefact_path(dist_root, target):
    _, _, distpath, relative = targets()[target]
    return os.path.abspath(os.path.join(dist_root, distpath, relative))


def human(size: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def describe_artefact(path):
    if not os.path.exists(path):
        return "MISSING"
    if os.path.isdir(path):
        total = sum(os.path.getsize(os.path.join(r, f))
                    for r, _, files in os.walk(path) for f in files)
        count = sum(len(files) for _, _, files in os.walk(path))
        return f"{count} files, {human(total)}"
    return human(os.path.getsize(path))


# --------------------------------------------------------------------------- #
# Preflight
# --------------------------------------------------------------------------- #

def preflight(distro, target, force=False):
    """Returns a list of problems; an empty list means the build can proceed."""
    problems = []
    spec = targets()[target][0]

    if sys.version_info[:2] != (3, 12):
        print(f"  [warn] running on Python {sys.version_info.major}.{sys.version_info.minor}; the specs target 3.12")
    if not os.path.exists(os.path.join(ROOT, spec)):
        problems.append(f"spec file not found: {spec}")
    if target == "onedir" and platform_key() == "darwin" and sys.platform != "darwin":
        problems.append("the macOS .app bundle can only be built on macOS")

    try:
        version = subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                                 capture_output=True, text=True, timeout=60, check=False)
        if version.returncode != 0:
            problems.append("PyInstaller is not installed (python -m pip install -r requirements.txt)")
        else:
            print(f"  [ok] PyInstaller {version.stdout.strip()}")
    except (OSError, subprocess.SubprocessError) as e:
        problems.append(f"could not run PyInstaller: {e}")

    missing = []
    for module in REQUIRED_IMPORTS:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        problems.append(f"missing runtime dependencies: {', '.join(missing)} "
                        f"(python -m pip install -r requirements.txt)")
    else:
        print(f"  [ok] runtime dependencies: {', '.join(REQUIRED_IMPORTS)}")

    try:
        os.makedirs(distro, exist_ok=True)
        probe = os.path.join(distro, ".write_test")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        print(f"  [ok] output directory writable: {distro}")
    except OSError as e:
        problems.append(f"output directory not writable ({distro}): {e}")

    if problems and force:
        print("  [warn] --force given: continuing despite the problems above")
        return []
    return problems


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #

def clean_target(dist_root, target, dry_run=False):
    """Removes only this flavour's folder: the other flavour and dist/installer survive."""
    path = flavour_dir(dist_root, target)
    if not os.path.isdir(path):
        print(f"  [skip] nothing to clean at {path}")
        return
    if dry_run:
        print(f"  [dry-run] would delete {path}")
        return
    shutil.rmtree(path, ignore_errors=True)
    print(f"  [ok] removed previous build: {path}")


def build(dist_root, target, clean_cache=True, dry_run=False):
    spec, _, _, _ = targets()[target]
    command = [sys.executable, "-m", "PyInstaller", spec, "--noconfirm",
               "--distpath", pyinstaller_distpath(dist_root, target)]
    if clean_cache:
        command.append("--clean")

    print(f"  $ {' '.join(command)}")
    if dry_run:
        return 0
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, check=False)
    print(f"  [{ 'ok' if result.returncode == 0 else 'FAIL' }] PyInstaller finished in {time.monotonic() - started:.1f}s")
    return result.returncode


def verify(artefact, dry_run=False):
    """Runs the frozen executable's --self-test (headless)."""
    if dry_run:
        print(f"  [dry-run] would run: {artefact} --self-test")
        return 0
    if not os.path.exists(artefact):
        fallback = glob.glob(os.path.join(os.path.dirname(artefact), "*"))
        print(f"  [FAIL] expected artefact not found: {artefact}")
        if fallback:
            print(f"         found instead: {', '.join(os.path.basename(p) for p in fallback[:5])}")
        return 1

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    print(f"  $ {artefact} --self-test")
    result = subprocess.run([artefact, "--self-test"], capture_output=True, text=True,
                            timeout=180, env=env, check=False)
    for line in (result.stdout or "").strip().splitlines()[-3:]:
        print(f"         {line}")
    if result.returncode != 0 and result.stderr:
        print(f"         {result.stderr.strip().splitlines()[-1][:160]}")
    print(f"  [{'ok' if result.returncode == 0 else 'FAIL'}] self-test")
    return result.returncode


# --------------------------------------------------------------------------- #
# Interaction
# --------------------------------------------------------------------------- #

def choose_target():
    available = targets()
    labels = {
        "onefile": "One-file  (single executable)",
        "onedir": "One-dir   (folder" + (", .app bundle)" if platform_key() == "darwin" else " / installer input)"),
    }
    while True:
        print("\nWhat do you want to build?")
        for index, key in enumerate(("onefile", "onedir"), start=1):
            print(f"  {index}) {labels[key]}")
        print("  3) Both")
        print("  4) Change output path")
        print("  q) Quit")
        choice = input("> ").strip().lower()

        if choice in ("q", "quit"):
            return None, None
        if choice == "1":
            return "onefile", available["onefile"]
        if choice == "2":
            return "onedir", available["onedir"]
        if choice == "3":
            return "both", None
        if choice == "4":
            return "path", None
        print("  Please choose 1, 2, 3, 4 or q.")


def choose_dist(current):
    print(f"\nCurrent output path: {current}")
    answer = input("New output path (empty keeps the current one): ").strip()
    if not answer:
        return current
    return os.path.abspath(os.path.expandvars(os.path.expanduser(answer)))


def confirm(plan):
    print("\nPlan:")
    for line in plan:
        print(f"  - {line}")
    return input("Proceed? [Y/n] ").strip().lower() in ("", "y", "yes")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=("onefile", "onedir", "both"),
                        help="skip the menu and build this directly")
    parser.add_argument("--dist", default=DEFAULT_DIST, help=f"output root (default: {DEFAULT_DIST})")
    parser.add_argument("--no-clean", action="store_true", help="reuse PyInstaller's cache (faster, less safe)")
    parser.add_argument("--no-verify", action="store_true", help="skip the post-build --self-test")
    parser.add_argument("--force", action="store_true", help="continue despite preflight problems")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, build nothing")
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    args = parser.parse_args()

    print("Tailscale & Headscale Client Pro — build")
    print(f"Platform: {platform_key()} | Python {sys.version.split()[0]} | repo {ROOT}")

    dist_root = os.path.abspath(os.path.expandvars(os.path.expanduser(args.dist)))
    interactive = args.target is None and sys.stdin.isatty()

    if interactive:
        while True:
            target, _ = choose_target()
            if target is None:
                print("Aborted.")
                return 1
            if target == "path":
                dist_root = choose_dist(dist_root)
                continue
            break
    elif args.target is None:
        parser.error("--target is required when no interactive terminal is attached")
    else:
        target = args.target

    selected = ("onefile", "onedir") if target == "both" else (target,)

    if dist_root != DEFAULT_DIST:
        print(f"\n  [warn] non-default output path: {dist_root}")
        print("         TailscaleClient_Installer.iss, build_mac_dmg.sh and build_linux_deb.sh")
        print("         read their input from dist/OneDir and dist/OneFile — either build there")
        print("         or adjust those paths.")

    if interactive and not args.yes:
        plan = [f"target(s): {', '.join(selected)}",
                f"output root: {dist_root}",
                "artefacts: " + "; ".join(
                    f"{t} -> {os.path.relpath(artefact_path(dist_root, t), ROOT)}" for t in selected),
                f"clean cache: {'no' if args.no_clean else 'yes'}",
                f"verify with --self-test: {'no' if args.no_verify else 'yes'}"]
        if not confirm(plan):
            print("Aborted.")
            return 1

    failures = []
    for current in selected:
        print(f"\n=== {current} ===")
        problems = preflight(dist_root, current, force=args.force)
        if problems:
            for problem in problems:
                print(f"  [FAIL] {problem}")
            failures.append(current)
            continue

        clean_target(dist_root, current, dry_run=args.dry_run)
        if build(dist_root, current, clean_cache=not args.no_clean, dry_run=args.dry_run) != 0:
            failures.append(current)
            continue

        artefact = artefact_path(dist_root, current)
        print(f"  artefact: {artefact} ({describe_artefact(artefact)})")
        if not args.no_verify and verify(artefact, dry_run=args.dry_run) != 0:
            failures.append(current)

    print("\n" + "=" * 60)
    if failures:
        print(f"Build finished with problems: {', '.join(failures)}")
        return 1
    print("Build finished successfully: " + ", ".join(selected))

    print("\nNext steps")
    if platform_key() == "win32":
        print("  Installer (needs Inno Setup, run in your build environment):")
        print('    iscc TailscaleClient_Installer.iss')
    elif platform_key() == "darwin":
        print("  DMG wrapper: ./build_mac_dmg.sh (expects dist/OneDir/TailscaleClientPro.app)")
    else:
        print("  Debian package: ./build_linux_deb.sh (expects dist/OneDir)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
