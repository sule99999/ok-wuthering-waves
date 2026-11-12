#!/usr/bin/env bash
# Run ok-oldking/pyappify-action from source after correcting the Tauri bundle
# identifier. Product name and executable name still come from pyappify.yml.
set -euo pipefail

if [[ -z "${RUNNER_TEMP:-}" || -z "${GITHUB_WORKSPACE:-}" ]]; then
  echo "This script is meant to run inside GitHub Actions." >&2
  exit 1
fi

python_bin="python3"
if ! command -v "$python_bin" >/dev/null 2>&1; then
  python_bin="python"
fi

dest="${RUNNER_TEMP}/pyappify-action"
rm -rf "$dest"
git clone --depth 1 https://github.com/ok-oldking/pyappify-action.git "$dest"
# Same action commit upstream uses for portable 7z releases without setup.exe.
git -C "$dest" fetch --depth 1 origin 69bf7ae364e8c7f0606f34df86d432168a46f4bf
git -C "$dest" checkout --detach 69bf7ae364e8c7f0606f34df86d432168a46f4bf
"$python_bin" "${GITHUB_WORKSPACE}/.github/scripts/patch_pyappify_build_config.py" \
  build-config "${dest}/build-config.js"
cp "${GITHUB_WORKSPACE}/.github/scripts/overlay_packaged_source.js" \
  "${dest}/overlay_packaged_source.js"
cp "${GITHUB_WORKSPACE}/.github/scripts/patch_launcher_startup.js" \
  "${dest}/patch_launcher_startup.js"
"$python_bin" "${GITHUB_WORKSPACE}/.github/scripts/patch_pyappify_build_config.py" \
  index "${dest}/index.js"

(
  cd "$dest"
  npm ci --omit=dev --ignore-scripts
)
# PACKAGE_ROOT lets the profile clone use a short directory. The default
# runner path plus ok_templates filenames exceeds the legacy Windows limit.
cd "${PACKAGE_ROOT:-$GITHUB_WORKSPACE}"
attempt=1
while true; do
  if node "${dest}/index.js"; then
    break
  fi
  if [[ "$attempt" -ge 3 ]]; then
    echo "Packaging failed after ${attempt} attempts." >&2
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "Packaging failed, retrying attempt ${attempt} in 20 seconds." >&2
  sleep 20
done
