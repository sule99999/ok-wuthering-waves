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
];

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
}

module.exports = {
    SOURCE_PATHS,
    overlayForkSource,
};
