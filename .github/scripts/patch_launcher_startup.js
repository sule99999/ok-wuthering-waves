const fs = require("fs");
const path = require("path");

// load_app emits the installed app before its git fetch, but the page only
// applies that event. The listener is registered asynchronously and the fetch
// can run for minutes, so a missed event leaves the window on its initial
// blank/loading view. Register the listener first and also apply the command
// result when the fetch later returns.
//
// Start App is also disabled while current_version is empty. This fork has no
// published tags, so the packaged commit is not a version tag and the launcher
// clears current_version after fetch. start_app runs the installed working
// tree; it does not check out a tag. An installed app can therefore start.
const START_BUTTON = 'disabled={disableRowActions || !app.current_version}>{t("Start App")}';
const START_BUTTON_FIXED = 'disabled={disableRowActions}>{t("Start App")}';
const OLD_START = `        (async () => {
            await invokeTauriCommandWrapper<App>("load_app", undefined, () => {},`;
const NEW_START = `        void (async () => {
            await Promise.all(unlistenPromises);
            await invokeTauriCommandWrapper<App>("load_app", undefined, (loadedApp) => {
                if (loadedApp) {
                    setApp(loadedApp);
                    updateStatus({loading: false});
                }
            },`;

function writePatched(file, patched, newline) {
    if (newline === "\r\n") {
        patched = patched.replace(/\n/g, "\r\n");
    }
    fs.writeFileSync(file, patched);
}

function patchLauncherStartup(buildDir) {
    const file = path.join(buildDir, "src", "App.tsx");
    const original = fs.readFileSync(file, "utf8");
    const newline = original.includes("\r\n") ? "\r\n" : "\n";
    const text = original.replace(/\r\n/g, "\n");
    if (!text.includes("await Promise.all(unlistenPromises);")) {
        if (!text.includes(OLD_START)) {
            throw new Error(
                "App.tsx no longer starts load_app where the window can render before git fetch",
            );
        }
        writePatched(file, text.replace(OLD_START, NEW_START), newline);
    }

    const buttonText = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
    if (buttonText.includes(START_BUTTON)) {
        writePatched(file, buttonText.replace(START_BUTTON, START_BUTTON_FIXED), newline);
    } else if (!buttonText.includes(START_BUTTON_FIXED)) {
        throw new Error("App.tsx no longer disables Start App when current_version is empty");
    }

    const htmlPath = path.join(buildDir, "index.html");
    const htmlOriginal = fs.readFileSync(htmlPath, "utf8");
    const htmlNewline = htmlOriginal.includes("\r\n") ? "\r\n" : "\n";
    const html = htmlOriginal.replace(/\r\n/g, "\n");
    if (!html.includes('id="boot"')) {
        const boot = [
            '    <div id="boot" style="position:fixed;inset:0;background:#1b1b1b;color:#f5f5f5;font:20px sans-serif;padding:32px;z-index:1">',
            "      MC_L4 is opening…",
            "    </div>",
            '    <div id="root"></div>',
        ].join("\n");
        if (!html.includes('<div id="root"></div>')) {
            throw new Error("index.html no longer has the React root");
        }
        writePatched(htmlPath, html.replace('<div id="root"></div>', boot), htmlNewline);
    }

    const appText = fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n");
    if (!appText.includes('getElementById("boot")')) {
        const marker = "function App() {";
        if (!appText.includes(marker)) {
            throw new Error("App.tsx no longer declares function App");
        }
        const removal = `${marker}\n    if (typeof document !== "undefined") {\n        document.getElementById("boot")?.remove();\n    }`;
        writePatched(file, appText.replace(marker, removal), newline);
    }

    const configPath = path.join(buildDir, "src-tauri", "tauri.conf.json");
    const configOriginal = fs.readFileSync(configPath, "utf8");
    if (configOriginal.includes('"visible": false')) {
        fs.writeFileSync(configPath, configOriginal.replace('"visible": false', '"visible": true'));
    }
}

module.exports = {
    patchLauncherStartup,
    OLD_START,
    NEW_START,
    START_BUTTON,
    START_BUTTON_FIXED,
};
