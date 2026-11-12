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
            await invokeTauriCommandWrapper<AppInfo>("load_app", undefined, () => {},`;
const NEW_START = `        void (async () => {
            await Promise.all(unlistenPromises);
            await invokeTauriCommandWrapper<AppInfo>("load_app", undefined, (loadedApp) => {
                if (loadedApp) {
                    setApp(loadedApp);
                    updateStatus({loading: false});
                }
            },`;

const START_GUARDS = [
    "const disableRowActions = isBusy || isActionLoading || app.update_state !== 'idle';",
    "isBusy={currentPage !== 'list' || !!status.messageLoading}",
    'disabled={disableRowActions}>{t("Stop App")}',
    'disabled={disableRowActions}>{t("Install")}',
    'disabled={disableRowActions}>{t("Start App")}',
];

function assertStartRemainsGuarded(cardText, appText) {
    const text = `${cardText}\n${appText}`;
    for (const snippet of START_GUARDS) {
        if (!text.includes(snippet)) {
            throw new Error(
                "Start App patch would drop an installed, loading, or update-state guard",
            );
        }
    }
    const startAt = text.indexOf('{t("Start App")}');
    const installedAt = text.lastIndexOf("app.installed ?", startAt);
    const runningAt = text.lastIndexOf("app.running ?", startAt);
    if (installedAt < 0 || runningAt < installedAt || startAt < runningAt) {
        throw new Error("Start App is no longer limited to an installed app that is not running");
    }
    if (text.includes(START_BUTTON)) {
        throw new Error("Start App is still disabled when the packaged build has no version tag");
    }
}

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

    const cardPath = path.join(buildDir, "src", "AppCard.tsx");
    const cardOriginal = fs.readFileSync(cardPath, "utf8");
    const cardNewline = cardOriginal.includes("\r\n") ? "\r\n" : "\n";
    let cardText = cardOriginal.replace(/\r\n/g, "\n");
    if (cardText.includes(START_BUTTON)) {
        cardText = cardText.replace(START_BUTTON, START_BUTTON_FIXED);
    } else if (!cardText.includes(START_BUTTON_FIXED)) {
        throw new Error("AppCard.tsx no longer disables Start App when current_version is empty");
    }
    const unsafeCompare = "compareVersions(v, app.current_version!)";
    const safeCompare = "app.current_version ? compareVersions(v, app.current_version) : 0";
    if (cardText.includes(unsafeCompare)) {
        cardText = cardText.replaceAll(unsafeCompare, safeCompare);
    } else if (!cardText.includes(safeCompare)) {
        throw new Error("Version menu still assumes current_version is set");
    }
    writePatched(cardPath, cardText, cardNewline);
    assertStartRemainsGuarded(
        cardText,
        fs.readFileSync(file, "utf8").replace(/\r\n/g, "\n"),
    );

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
    patchPackagedFetch(buildDir);
}

// A partial clone fetches in well under a second with git because the blob
// filter stays in place. libgit2 ignores that filter and the same heads-and-tags
// fetch did not finish within 240 seconds on the Windows runner, so load_app
// never returned the final no-tag state. The packaged repository is already
// the reviewed tree. Read its local tags and do not contact the remote.
const FETCH_BLOCK = `                emit_info!(app_name, "Fetching updates for existing repository...");
                let repo_path_for_task = repo_path.clone();
                let app_name_for_task = app_name.clone();

                task::spawn_blocking(move || -> Result<()> {
                    let repo = open_repository(&repo_path_for_task)?;
                    sync_tags(&repo, &app_name_for_task, true, Some("Fetching objects"))
                        .with_context(|| {
                            format!(
                                "Failed to fetch updates for {}",
                                repo_path_for_task.display()
                            )
                        })?;
                    emit_info!(app_name_for_task, "Fetch complete.");
                    Ok(())
                })
                .await
                .context("Task for fetching updates panicked")??;
                return Ok(());`;
const FETCH_SKIPPED = `                emit_info!(
                    app_name,
                    "Packaged repository is ready; skipping startup fetch."
                );
                return Ok(());`;
const TAG_FETCH_BLOCK = `        emit_info!(
            app_name_for_task,
            "Fetching all tags for repository at {}",
            repo_path_for_task.display()
        );

        let repo = open_repository(&repo_path_for_task)?;
        sync_tags(&repo, &app_name_for_task, false, None).with_context(|| {
            format!(
                "Failed to fetch tags for repository {}",
                repo_path_for_task.display()
            )
        })?;`;
const TAG_FETCH_SKIPPED = `        emit_info!(
            app_name_for_task,
            "Reading packaged tags without a startup fetch at {}",
            repo_path_for_task.display()
        );

        let repo = open_repository(&repo_path_for_task)?;`;

function patchPackagedFetch(buildDir) {
    const file = path.join(buildDir, "src-tauri", "src", "git.rs");
    const original = fs.readFileSync(file, "utf8");
    const newline = original.includes("\r\n") ? "\r\n" : "\n";
    let text = original.replace(/\r\n/g, "\n");
    if (!text.includes("skipping startup fetch.")) {
        if (!text.includes(FETCH_BLOCK)) {
            throw new Error("git.rs no longer fetches every head before the launcher can start");
        }
        text = text.replace(FETCH_BLOCK, FETCH_SKIPPED);
    }
    if (!text.includes("Reading packaged tags without a startup fetch")) {
        if (!text.includes(TAG_FETCH_BLOCK)) {
            throw new Error("git.rs no longer fetches tags before resolving current_version");
        }
        text = text.replace(TAG_FETCH_BLOCK, TAG_FETCH_SKIPPED);
    }
    if (text.includes("Fetching updates for existing repository")) {
        throw new Error("Startup still fetches every branch of the packaged repository");
    }
    writePatched(file, text, newline);
}

module.exports = {
    patchLauncherStartup,
    OLD_START,
    NEW_START,
    START_BUTTON,
    START_BUTTON_FIXED,
    assertStartRemainsGuarded,
    patchPackagedFetch,
    FETCH_BLOCK,
    TAG_FETCH_BLOCK,
};
