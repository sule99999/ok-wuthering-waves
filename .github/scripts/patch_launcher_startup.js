const fs = require("fs");
const path = require("path");

// load_app emits the installed app before its git fetch, but the page only
// applies that event. The listener is registered asynchronously and the fetch
// can run for minutes, so a missed event leaves the window on its initial
// blank/loading view. Register the listener first and also apply the command
// result when the fetch later returns.
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

function patchLauncherStartup(buildDir) {
    const file = path.join(buildDir, "src", "App.tsx");
    const original = fs.readFileSync(file, "utf8");
    const newline = original.includes("\r\n") ? "\r\n" : "\n";
    const text = original.replace(/\r\n/g, "\n");
    if (text.includes("await Promise.all(unlistenPromises);")) {
        return;
    }
    if (!text.includes(OLD_START)) {
        throw new Error(
            "App.tsx no longer starts load_app where the window can render before git fetch",
        );
    }
    let patched = text.replace(OLD_START, NEW_START);
    if (newline === "\r\n") {
        patched = patched.replace(/\n/g, "\r\n");
    }
    fs.writeFileSync(file, patched);
}

module.exports = { patchLauncherStartup, OLD_START, NEW_START };
