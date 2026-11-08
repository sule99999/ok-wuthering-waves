const fs = require("fs");
const path = require("path");

// Runtime files the launcher executes. PyAppify otherwise checks out a git tag,
// which would drop this fork's gui_title and task fixes.
const SOURCE_PATHS = [
    "src",
    "config.py",
    "main.py",
    "main_debug.py",
    "main_web.py",
    "assets",
    "icons",
    "i18n",
    "requirements.txt",
    "README.md",
    "readme",
    "pyappify.yml",
    // inline_ok_requirements vendors these and deletes their requirement lines.
    "ok",
    "pyappify",
];

const VENDORED_REQUIREMENTS = [
    ["ok-script", "ok"],
    ["pyappify", "pyappify"],
];

function requirementIsPresent(requirementsText, packageName) {
    const pattern = new RegExp(`^\\s*${packageName}\\b`, "im");
    return pattern.test(requirementsText);
}

function overlayForkSource(appDistDir, appName, workspace = process.env.GITHUB_WORKSPACE) {
    if (!workspace) {
        throw new Error("GITHUB_WORKSPACE is required to overlay this fork into the package");
    }
    const working = path.join(appDistDir, "data", "apps", appName, "working");
    if (!fs.existsSync(working)) {
        throw new Error(`Packaged working directory does not exist yet: ${working}`);
    }
    for (const relativePath of SOURCE_PATHS) {
        const source = path.join(workspace, relativePath);
        if (!fs.existsSync(source)) {
            continue;
        }
        const destination = path.join(working, relativePath);
        fs.cpSync(source, destination, {
            recursive: true,
            force: true,
            filter: (sourcePath) => !sourcePath.split(path.sep).includes("__pycache__"),
        });
    }
    const configText = fs.readFileSync(path.join(working, "config.py"), "utf8");
    if (!configText.includes("'gui_title': 'MC_L4'")) {
        throw new Error("Packaged config.py does not contain this fork's MC_L4 window title");
    }
    const packagedConfig = fs.readFileSync(path.join(working, "pyappify.yml"), "utf8");
    if (packagedConfig.includes("ok-oldking/ok-ww-update") || packagedConfig.includes("ok-ww-update2")) {
        throw new Error("Packaged pyappify.yml still downloads an upstream update repository");
    }
    const requirementsPath = path.join(working, "requirements.txt");
    if (fs.existsSync(requirementsPath)) {
        const requirementsText = fs.readFileSync(requirementsPath, "utf8");
        for (const [packageName, folder] of VENDORED_REQUIREMENTS) {
            if (requirementIsPresent(requirementsText, packageName)) {
                continue;
            }
            const initFile = path.join(working, folder, "__init__.py");
            if (!fs.existsSync(initFile)) {
                throw new Error(
                    `requirements.txt no longer installs ${packageName}, but ${folder}/__init__.py was not packaged`,
                );
            }
        }
    }
}

module.exports = {
    SOURCE_PATHS,
    VENDORED_REQUIREMENTS,
    overlayForkSource,
};
