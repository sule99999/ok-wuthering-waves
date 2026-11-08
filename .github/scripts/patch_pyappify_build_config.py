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


def patch_action_index(text):
    """Copy this checkout into each profile after PyAppify clones its git tag."""
    newline = "\r\n" if "\r\n" in text else "\n"
    normalized = text.replace("\r\n", "\n")
    if OVERLAY_CALL in normalized:
        return text
    lines = normalized.split("\n")
    for index, line in enumerate(lines):
        if line.strip() != SETUP_CALL:
            continue
        indent = line[: len(line) - len(line.lstrip(" "))]
        lines.insert(index + 1, f"{indent}{OVERLAY_CALL}")
        patched = "\n".join(lines)
        if newline == "\r\n":
            patched = patched.replace("\n", "\r\n")
        return patched
    raise ValueError(
        "pyappify-action index.js no longer calls setupProfile where fork source can be overlaid"
    )


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
