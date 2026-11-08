"""Keep the PyAppify product name while satisfying Tauri's bundle identifier rule.

PyAppify copies ``pyappify.yml`` ``name`` into ``productName``, ``mainBinaryName``,
and ``identifier``. Tauri rejects ``_`` in the identifier, so a name such as
``MC_L4`` would fail the Windows build. The executable and product name stay
exactly as configured; only the identifier swaps ``_`` for ``-``.
"""

import sys
from pathlib import Path


IDENTIFIER_LINE = "config.identifier = String(appName).replaceAll('_', '-');"
ANCHOR = "config.mainBinaryName = getMainBinaryName(appName);"
SETUP_CALL = (
    "await setupProfile(exec.exec, exeDestPath, profile.name, appName, appDistDir, setupVersion);"
)
OVERLAY_CALL = (
    "require('./overlay_packaged_source').overlayForkSource(appDistDir, appName);"
)
STARTUP_ANCHOR = "await setupPnpm();"
STARTUP_CALL = "require('./patch_launcher_startup').patchLauncherStartup(buildDir);"


def patch_build_config(text):
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n")
    if IDENTIFIER_LINE in normalized:
        return text

    lines = normalized.split("\n")
    for index, line in enumerate(lines):
        if line.strip() != ANCHOR:
            continue
        indent = line[: len(line) - len(line.lstrip(" "))]
        lines.insert(index + 1, f"{indent}{IDENTIFIER_LINE}")
        patched = "\n".join(lines)
        if newline == "\r\n":
            patched = patched.replace("\n", "\r\n")
        return patched

    raise ValueError(
        "pyappify-action build-config.js no longer assigns mainBinaryName "
        "where the bundle identifier can be corrected"
    )


def _insert_after(lines, anchor, insertion):
    for index, line in enumerate(lines):
        if line.strip() != anchor:
            continue
        indent = line[: len(line) - len(line.lstrip(" "))]
        lines.insert(index + 1, f"{indent}{insertion}")
        return True
    return False


def _insert_before(lines, anchor, insertion):
    for index, line in enumerate(lines):
        if line.strip() != anchor:
            continue
        indent = line[: len(line) - len(line.lstrip(" "))]
        lines.insert(index, f"{indent}{insertion}")
        return True
    return False


def patch_action_index(text):
    """Copy this checkout into each profile and show the launcher before git fetch."""
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    if OVERLAY_CALL not in normalized:
        if not _insert_after(lines, SETUP_CALL, OVERLAY_CALL):
            raise ValueError(
                "pyappify-action index.js no longer calls setupProfile where fork source can be overlaid"
            )
    if STARTUP_CALL not in "\n".join(lines) and STARTUP_ANCHOR in normalized:
        if not _insert_before(lines, STARTUP_ANCHOR, STARTUP_CALL):
            raise ValueError(
                "pyappify-action index.js no longer prepares pyappify where launcher startup can be patched"
            )
    patched = "\n".join(lines)
    if newline == "\r\n":
        patched = patched.replace("\n", "\r\n")
    return patched


def main(argv):
    if len(argv) != 3:
        raise SystemExit(f"usage: {Path(argv[0]).name} build-config|index FILE")
    kind, path_text = argv[1], argv[2]
    path = Path(path_text)
    source = path.read_text(encoding="utf-8")
    if kind == "build-config":
        updated = patch_build_config(source)
    elif kind == "index":
        updated = patch_action_index(source)
    else:
        raise SystemExit(f"unknown patch target {kind}")
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv)
