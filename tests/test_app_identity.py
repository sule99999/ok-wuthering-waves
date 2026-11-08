"""The fork's visible app name and packaged executable name are MC_L4.

These checks read the source files directly so they do not import ok-script.
"""

import ast
import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "MC_L4"
PATCH_SCRIPT = ROOT / ".github" / "scripts" / "patch_pyappify_build_config.py"


def _pyappify_app_name():
    for line in (ROOT / "pyappify.yml").read_text(encoding="utf-8").splitlines():
        if line.startswith("name:"):
            return ast.literal_eval(line.split(":", 1)[1].strip())
    raise AssertionError("pyappify.yml has no top-level name")


def _config_gui_title():
    tree = ast.parse((ROOT / "config.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "gui_title":
                if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                    raise AssertionError("gui_title is not a string constant")
                return value.value
    raise AssertionError("config.py has no gui_title")


class AppIdentityTest(unittest.TestCase):
    def test_window_title_and_packaged_name_are_mc_l4(self):
        self.assertEqual(APP_NAME, _config_gui_title())
        self.assertEqual(APP_NAME, _pyappify_app_name())

    def test_release_installer_glob_follows_the_packaged_name(self):
        workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
        installer = f"pyappify_dist/{APP_NAME}-win32-China-setup-*.exe"
        self.assertIn(installer, workflow)
        self.assertNotIn("pyappify_dist/ok-ww-win32-China-setup-", workflow)

    def test_repository_identity_and_license_stay_in_place(self):
        config_source = (ROOT / "config.py").read_text(encoding="utf-8")
        setup_source = (ROOT / "setup.py").read_text(encoding="utf-8")
        project_source = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        license_source = (ROOT / "LICENSE.txt").read_text(encoding="utf-8")
        pyappify_source = (ROOT / "pyappify.yml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

        self.assertIn("https://github.com/ok-oldking/ok-wuthering-waves", config_source)
        self.assertIn('author="ok-oldking"', setup_source)
        self.assertIn('name = "ok-ww"', project_source)
        self.assertIn("GNU AFFERO GENERAL PUBLIC LICENSE", license_source)
        self.assertIn("https://github.com/ok-oldking/ok-ww-update.git", pyappify_source)
        self.assertIn("https://cnb.cool/ok-oldking/ok-ww-update2.git", pyappify_source)
        self.assertIn("uses: ./.github/actions/package-launcher", workflow)
        self.assertNotIn("uses: ok-oldking/pyappify-action@master", workflow)

    def test_packaged_name_keeps_a_tauri_safe_bundle_identifier(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("patch_pyappify_build_config", PATCH_SCRIPT)
        patcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(patcher)

        upstream = textwrap.dedent(
            """\
            function replaceExactStringValues(value, from, to) {
              if (typeof value === 'string') {
                return value === from ? to : value;
              }
              if (Array.isArray(value)) {
                return value.map(item => replaceExactStringValues(item, from, to));
              }
              if (value && typeof value === 'object') {
                return Object.fromEntries(
                  Object.entries(value).map(([key, item]) => [key, replaceExactStringValues(item, from, to)]),
                );
              }
              return value;
            }

            function getMainBinaryName(appName) {
              return appName;
            }

            function prepareTauriConfig(contents, appName, version) {
              let config = JSON.parse(contents);
              config = replaceExactStringValues(config, 'pyappify', appName);
              config = replaceExactStringValues(config, '0.0.1', version.replace(/^v/, ''));
              config.mainBinaryName = getMainBinaryName(appName);

              return `${JSON.stringify(config, null, 2)}\\n`;
            }

            module.exports = { prepareTauriConfig, getMainBinaryName };
            """
        )
        patched = patcher.patch_build_config(upstream)
        self.assertEqual(patched, patcher.patch_build_config(patched))

        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not installed")

        sample = {
            "productName": "pyappify",
            "mainBinaryName": "pyappify",
            "version": "0.0.1",
            "identifier": "pyappify",
            "app": {"windows": [{"title": "pyappify"}]},
        }
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "build-config.js"
            probe_path = Path(directory) / "probe.js"
            script_path.write_text(patched, encoding="utf-8")
            probe_path.write_text(
                textwrap.dedent(
                    """\
                    const { prepareTauriConfig, getMainBinaryName } = require(process.argv[2]);
                    const config = JSON.parse(prepareTauriConfig(process.argv[3], process.argv[4], 'v1.2.4'));
                    const identifierOk = [...config.identifier].every(
                      (ch) => /[A-Za-z0-9.-]/.test(ch),
                    );
                    process.stdout.write(JSON.stringify({
                      productName: config.productName,
                      mainBinaryName: config.mainBinaryName,
                      binary: `${getMainBinaryName(process.argv[4])}.exe`,
                      windowTitle: config.app.windows[0].title,
                      identifier: config.identifier,
                      identifierOk,
                    }));
                    """
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [node, str(probe_path), str(script_path), json.dumps(sample), APP_NAME],
                check=True,
                capture_output=True,
                text=True,
            )
        result = json.loads(completed.stdout)
        self.assertEqual(APP_NAME, result["productName"])
        self.assertEqual(APP_NAME, result["mainBinaryName"])
        self.assertEqual(f"{APP_NAME}.exe", result["binary"])
        self.assertEqual(APP_NAME, result["windowTitle"])
        self.assertEqual("MC-L4", result["identifier"])
        self.assertTrue(result["identifierOk"])
