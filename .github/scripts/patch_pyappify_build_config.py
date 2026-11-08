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


def main(argv):
    if len(argv) != 2:
        raise SystemExit(f"usage: {Path(argv[0]).name} BUILD_CONFIG_JS")
    path = Path(argv[1])
    path.write_text(patch_build_config(path.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv)
