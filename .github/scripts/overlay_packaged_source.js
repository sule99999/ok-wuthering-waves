const { execFileSync } = require("child_process");
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
    slimProfileClone(appDistDir, appName);
    removeNonRuntimeWorkingFiles(working);
    sanitizePackagedAppMetadata(appDistDir, appName);
}

// The profile checkout copies the whole repository into working/. These paths are
// not imported by the app. Measured in the 1.15 GiB Global installer from
// fe3ec5d: ok_templates 880 MB and tests 130 MB, mostly images. Upstream
// v3.7.19's Global installer does not contain either directory.
const NON_RUNTIME_WORKING_PATHS = [
    "ok_templates",
    "tests",
    ".github",
    ".agents",
    ".codex",
    "docs",
    "mkdocs.yml",
    "setup.py",
];

function removeNonRuntimeWorkingFiles(working) {
    for (const relativePath of NON_RUNTIME_WORKING_PATHS) {
        fs.rmSync(path.join(working, relativePath), { recursive: true, force: true });
    }
}

const PROFILE_GIT_URL = process.env.MC_L4_PROFILE_GIT_URL
    || "https://github.com/sule99999/ok-wuthering-waves.git";

function removeEmptyDirectories(directory) {
    if (!fs.existsSync(directory)) {
        return;
    }
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
        if (!entry.isDirectory()) {
            continue;
        }
        const child = path.join(directory, entry.name);
        removeEmptyDirectories(child);
        if (fs.readdirSync(child).length === 0) {
            fs.rmdirSync(child);
        }
    }
}

function replaceProfileRepository(repo, gitUrl = PROFILE_GIT_URL) {
    // `git init` leaves objects/ and refs/ empty. NSIS omits empty directories,
    // and the installed folder then fails `git`/`libgit2` open. Startup deletes
    // it and clones the whole fork before the launcher can finish loading.
    // A depth-1 clone has real objects and refs, so that open succeeds.
    fs.rmSync(repo, { recursive: true, force: true });
    const git = process.platform === "win32" ? "git.exe" : "git";
    execFileSync(git, [
        "clone", "--depth", "1", "--filter=blob:none", "--sparse", gitUrl, repo,
    ], { stdio: "inherit" });
    execFileSync(git, [
        "sparse-checkout", "set", "--no-cone", "/*", "!/ok_templates/", "!/tests/",
    ], { cwd: repo, stdio: "inherit" });
    removeEmptyDirectories(path.join(repo, ".git"));
    execFileSync(git, ["status", "-sb"], { cwd: repo, stdio: "inherit" });
}

function slimProfileClone(appDistDir, appName) {
    const repo = path.join(appDistDir, "data", "apps", appName, "repo");
    if (!fs.existsSync(repo)) {
        return;
    }
    replaceProfileRepository(repo);
}

function sanitizePackagedAppMetadata(appDistDir, appName) {
    // Setup saves app.json before this overlay. That copy can still list the
    // upstream update repositories and their version tags. The launcher reads
    // it before the working pyappify.yml.
    const configPath = path.join(appDistDir, "data", "apps", appName, "app.json");
    if (!fs.existsSync(configPath)) {
        return;
    }
    const app = JSON.parse(fs.readFileSync(configPath, "utf8"));
    const globalProfile = (app.profiles || []).find((profile) => profile.name === "Global")
        || (app.profiles || [])[0]
        || {};
    app.profiles = [{
        ...globalProfile,
        name: "Global",
        git_url: PROFILE_GIT_URL,
        main_script: globalProfile.main_script || "main.py",
        requirements: globalProfile.requirements || "requirements.txt",
        requires_python: globalProfile.requires_python || "3.12",
        pip_args: globalProfile.pip_args || "--no-deps",
    }];
    app.current_profile = "Global";
    app.available_versions = [];
    app.current_version = null;
    app.current_version_missing = false;
    app.update_target_version = null;
    app.update_error = null;
    if (app.update_state && app.update_state !== "Idle") {
        app.update_state = "Idle";
    }
    fs.writeFileSync(configPath, JSON.stringify(app, null, 2));
}

module.exports = {
    SOURCE_PATHS,
    VENDORED_REQUIREMENTS,
    overlayForkSource,
    slimProfileClone,
    replaceProfileRepository,
    sanitizePackagedAppMetadata,
    removeEmptyDirectories,
    PROFILE_GIT_URL,
    NON_RUNTIME_WORKING_PATHS,
};
