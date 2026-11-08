# 贡献指南 / Contributing Guide

感谢你愿意为 `ok-ww` 做贡献。本项目是基于图像识别的《鸣潮》自动化工具，使用 [ok-script](https://ok-script.com) 开发，仅供个人学习与交流使用。提交贡献前，请先阅读[简体中文文档](../zh-CN/index.md)中的免责声明、开发者专区和社区信息。

Thank you for contributing to `ok-ww`. This project is an image-recognition-based automation tool for Wuthering Waves, developed with [ok-script](https://ok-script.com), and is intended only for personal learning and communication. Before contributing, please read the disclaimer, developer section, and community information in the [English documentation](../en/index.md).

## 提交 PR 前 / Before Opening a PR

请先确认你的修改范围：

Please check the scope of your change first:

- Bug 修复、文档修正、翻译修正、小型兼容性修复：可以直接提交 PR。
- 新功能、重构、架构调整、角色逻辑大改、任务行为大改、会显著改变现有功能体验的修改：请在提交 PR 前先联系作者或在社区中讨论，确认方向后再开始或提交。
- 不确定是否属于“大改”的修改：请先联系作者。

- Bug fixes, documentation fixes, translation fixes, and small compatibility fixes: you may open a PR directly.
- New features, refactors, architecture changes, major character logic changes, major task behavior changes, or changes that significantly alter existing behavior: please contact the author or discuss with the community before opening a PR.
- If you are unsure whether a change is major, please contact the author first.

## 联系方式 / Contact

- Discord: [https://discord.gg/vVyCatEBgA](https://discord.gg/vVyCatEBgA)

## 开发环境 / Development Environment

本项目仅支持 Python 3.12。建议使用仓库内的本地虚拟环境运行命令。

This project only supports Python 3.12. Prefer using the repository-local virtual environment when running commands.

```powershell
# 安装或更新依赖 / Install or update dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --upgrade

# 如需开发测试依赖 / For development test dependencies
.\.venv\Scripts\python.exe -m pip install ".[dev]" --upgrade

# 仅进行 Web 测试时需要 / Only for web testing
.\.venv\Scripts\python.exe -m pip install ".[dev,web-test]" --upgrade

# 运行 Release 版本 / Run release version
.\.venv\Scripts\python.exe main.py

# 运行 Debug 版本 / Run debug version
.\.venv\Scripts\python.exe main_debug.py
```

如果没有 `.venv`，可以使用 `python` 代替上面的解释器路径。

If `.venv` does not exist, use `python` instead of the interpreter path above.

## 运行此 PR / Run this pull request

本项目只在 Windows 上运行。贡献指南要求 Python 3.12。`pyproject.toml` 写了 `>=3.11`，但发布配置和 China 打包配置都是 3.12。下面的命令取出合并前的 PR 分支，不创建 tag，也不发布安装包。

This project runs on Windows. The supported Python is 3.12. `pyproject.toml` allows `>=3.11`, but the release workflow and the China package profile both use 3.12. These commands check out this pull request before it is merged. They do not create a tag or publish an installer.

```powershell
git clone https://github.com/sule99999/ok-wuthering-waves.git
cd ok-wuthering-waves
git fetch origin pull/1/head:pr-1
git checkout pr-1
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --upgrade
.\.venv\Scripts\python.exe main.py
```

`main_debug.py` 打开调试界面。`main_web.py` 需要再安装 `".[web-test]"`。任务参数见 README：`main.py -t 1 -e`。

`main_debug.py` opens the debug UI. `main_web.py` also needs `".[web-test]"`. Task arguments are in the README: `main.py -t 1 -e`.

这样启动时，窗口标题来自 `config.py` 的 `gui_title`（`MC_L4`）。ok-script 还会在系统标题后加上版本和渠道，源码运行时大约是 `MC_L4 dev`。任务管理器里的进程名仍是 `python.exe`。只有重新打出来的启动器才是 `MC_L4.exe`。

This launch uses `gui_title` from `config.py` (`MC_L4`). ok-script appends the version and channel to the operating-system caption, so a source launch looks like `MC_L4 dev`. Task Manager still shows `python.exe`. Only a rebuilt launcher is `MC_L4.exe`.

### 打包 / Packaging

仓库里的正式发布入口是 `.github/workflows/build.yml`，只在推送 `v*` tag 时运行，运行环境是 `windows-latest` 和 Python 3.12。那个 workflow 会创建 GitHub Release，稳定版还会请求 SignPath。

The release entry point is `.github/workflows/build.yml`. It runs only on a `v*` tag, on `windows-latest` with Python 3.12. That workflow creates a GitHub Release, and a stable tag also requests SignPath.

这个 PR 另有 `.github/workflows/windows-artifact.yml`。它在本分支相关文件被推送时，用同一套打包脚本打未签名的 Windows 安装包，并上传为 Actions artifact `MC_L4-windows-unsigned`。它不创建 tag、Release，不签名，也不上传 MirrorChyan。

This pull request also has `.github/workflows/windows-artifact.yml`. A push of the relevant files on this branch builds unsigned Windows installers with the same packaging scripts and uploads the Actions artifact `MC_L4-windows-unsigned`. It does not create a tag or a Release, and it does not sign or upload to MirrorChyan.

已成功的构建是 https://github.com/sule99999/ok-wuthering-waves/actions/runs/42457584257 ，源码 `fe3ec5d180a49b6be17a9a93cd95afe4464f6326`。Artifact 下载页：https://github.com/sule99999/ok-wuthering-waves/actions/runs/42457584257/artifacts/13609253276 。保留 14 天。文件没有签名，Windows SmartScreen 可能拦截。

The successful build is https://github.com/sule99999/ok-wuthering-waves/actions/runs/42457584257 from `fe3ec5d180a49b6be17a9a93cd95afe4464f6326`. The artifact page is https://github.com/sule99999/ok-wuthering-waves/actions/runs/42457584257/artifacts/13609253276. It is kept for 14 days. The files are unsigned, so Windows SmartScreen may block them.

请安装 `MC_L4-win32-China-setup.exe`（约 1.12 GiB）或 `MC_L4-win32-Global-setup.exe`（约 1.12 GiB）。这两个安装包里已经有 Python 3.12：`data\apps\MC_L4\python\python.exe` 和 `pythonw.exe`，以及已安装的依赖。不需要另装 Python 或 Git 才能编译。约 4 MB 的 `MC_L4-win32-online-setup.exe` 不带这些运行库，第一次运行还要下载。启动器进程名是 `MC_L4.exe`。China 的界面进程是随包的 `pythonw.exe`，Global 是 `python.exe`。

Install `MC_L4-win32-China-setup.exe` (about 1.12 GiB) or `MC_L4-win32-Global-setup.exe` (about 1.12 GiB). Both already contain Python 3.12 at `data\apps\MC_L4\python\python.exe` and `pythonw.exe`, plus the installed dependencies. A separate Python or Git install is not required to compile. The 4 MB `MC_L4-win32-online-setup.exe` does not contain that runtime and still downloads it on first launch. The launcher process is `MC_L4.exe`. China's UI process is the bundled `pythonw.exe`; Global uses `python.exe`.

安装包里的 Git 仓库只有一个空的标记，完整历史和 `ok_templates` 没有打进去，否则 NSIS 会失败。第一次打开程序时，PyAppify 可能联网拉取仓库。这个 fork 没有版本 tag，所以这次拉取不应把已经打进安装包的 `MC_L4` 源码换回 master。

The installer contains only a tiny Git marker. The full history and `ok_templates` are omitted because NSIS could not pack them. On first launch PyAppify may download the repository. This fork has no version tags, so that download should not replace the `MC_L4` source already in the installer.

稳定版 tag（`v1.2.3` 这种）还会走 SignPath 签名。签名使用 workflow 里 ok-oldking 的 organization、project slug 和 `SIGNPATH_API_TOKEN`。这个 fork 没有这些 secret，不能替上游签名。预发布 tag 会跳过签名并继续打包。

A stable tag such as `v1.2.3` also requests SignPath signing. The workflow uses ok-oldking's organization, project slug, and `SIGNPATH_API_TOKEN`. This fork does not have those secrets, so it cannot sign for upstream. A prerelease tag skips signing and continues packaging.

打包脚本会把当前检出的源码覆盖进 `data/apps/MC_L4/working`，包括 `inline_ok_requirements` 写进去的 `ok/` 和 `pyappify/`。China profile 仍使用原来的 `pip_args: "--no-deps"`，Global 沿用第一组 profile 的安装参数。两个 profile 的 `git_url` 都是 `https://github.com/sule99999/ok-wuthering-waves.git`，不再拉取 `ok-oldking/ok-ww-update` 或 `ok-ww-update2`。

The packaging script copies the checked-out source into `data/apps/MC_L4/working`, including the `ok/` and `pyappify/` directories written by `inline_ok_requirements`. The China profile still has the original `pip_args: "--no-deps"`, and Global inherits that profile's install arguments. Both `git_url` values are `https://github.com/sule99999/ok-wuthering-waves.git`. They do not fetch `ok-oldking/ok-ww-update` or `ok-ww-update2`.

`.github/workflows/build.yml` 里，同步到 ok-oldking 更新仓库的 job 只在 `github.repository == 'ok-oldking/ok-wuthering-waves'` 时运行。这个 fork 没有 `CNB_TOKEN` / `OK_GH`，所以不会推上游；打包 job 在同步被跳过时仍会继续。发布说明里的上游 changelog 只有同步成功时才有内容。MirrorChyan 上传文件名已改为 `MC_L4-win32-China-setup-*.exe`，但本 PR 没有执行上传，也没有 MirrorChyan token。

In `.github/workflows/build.yml`, the job that pushes to ok-oldking update repositories runs only when `github.repository == 'ok-oldking/ok-wuthering-waves'`. This fork does not have `CNB_TOKEN` or `OK_GH`, so it does not push upstream, and the package job still continues when that sync is skipped. The upstream changelog in the release notes is present only after a successful sync. The MirrorChyan filename is now `MC_L4-win32-China-setup-*.exe`. This pull request did not run that upload and does not add a MirrorChyan token.

副本出口是否在所有支持的副本里都显示 `illusive_realm_exit`，以及按 Esc 后该图标是否会先消失而队伍名仍在，没有在游戏里验证。若图标先消失，代码会把当前画面当成已经离开副本。这不是已确认的行为。

Whether every supported domain shows `illusive_realm_exit`, and whether that icon disappears after Esc while the team names remain, was not verified in the game. If the icon disappears first, the code treats the screen as already outside the domain. That outcome is not confirmed.

离开副本的等待和打开主界面的等待不是同一个预算。原来的 `esc_world_confirm` 在点确认后最多等 120 秒；`DomainTask` 用自己的 `teleport_timeout`（100 秒）。Tacet/Daily 的 180 秒和梦魇的 30 秒只用于还没进副本时的 `ensure_main`。已经在副本里时，不会把 30 秒当成读条上限。

The domain-load wait and the main-screen wait are different budgets. Original `esc_world_confirm` waited up to 120 seconds after the confirm click. `DomainTask` uses its own `teleport_timeout` (100 seconds). Tacet and Daily's 180 seconds, and Nightmare's 30 seconds, apply only to `ensure_main` before a domain is entered. A task already inside a domain does not use 30 seconds as the load limit.

MirrorChyan 只有在上游同步 job 成功并且它报告稳定版时才会被触发。Fork 跳过同步时不会上传。发布说明在没有同步结果时使用 `github.ref_name`，而不是空白的上游 changelog。

MirrorChyan is triggered only when the upstream sync job succeeds and reports a stable release. A fork run that skips sync does not upload. The release note uses `github.ref_name` when there is no sync result, instead of a blank upstream changelog.

本地或 workflow 成功打包后，`pyappify_dist` 里会有：

A successful package, locally or in the workflow, writes these files under `pyappify_dist`:

- `MC_L4-win32.zip`（内含 `MC_L4/MC_L4.exe`）
- `MC_L4-win32-China-setup-<version>.exe`
- `MC_L4-win32-Global-setup-<version>.exe`
- `MC_L4-win32-online-setup-<version>.exe`

`<version>` 是去掉开头 `v` 的 tag。启动器进程名是 `MC_L4.exe`。China 配置再用 `pythonw.exe` 跑界面，Global 默认用 `python.exe`。这两种 Python 进程名都不会变成 `MC_L4`。

`<version>` is the tag without a leading `v`. The launcher process name is `MC_L4.exe`. The China profile then runs the UI with `pythonw.exe`; Global uses `python.exe` by default. Those Python process names do not become `MC_L4`.

在 Windows 上手动打这个 PR 的包，还需要 Git、Node.js、pnpm、Rust stable，以及能克隆 `ok-oldking/pyappify` 和 `ok-oldking/pyappify-action`。workflow 里的 `.github/scripts/run_pyappify_action.sh` 依赖 `GITHUB_WORKSPACE` 和 `RUNNER_TEMP`，它不是一条已经验证过的本机安装命令。这里没有生成安装包。

Building this pull request by hand on Windows also requires Git, Node.js, pnpm, Rust stable, and clones of `ok-oldking/pyappify` and `ok-oldking/pyappify-action`. `.github/scripts/run_pyappify_action.sh` depends on `GITHUB_WORKSPACE` and `RUNNER_TEMP`; it is not a verified local install command. No installer was produced here.

## 测试 / Testing

提交 PR 前，请尽量运行相关测试，并在 PR 描述中说明测试结果。

Before opening a PR, please run the relevant tests when possible and include the results in the PR description.

```powershell
.\run_tests.ps1
```

也可以直接运行指定测试：

You can also run a specific test directly:

```powershell
.\.venv\Scripts\python.exe -m unittest tests\TestChar.py
```

## PR 要求 / PR Requirements

- 提交 PR 前，必须使用 AI 审查最终修改，处理审查发现的有效问题，并在 PR 描述中简要说明审查工具、结果及处理情况。
- 保持修改范围清晰，避免把无关格式化、重构和功能修改混在同一个 PR 中。
- 说明改动目的、主要实现方式、影响范围和测试结果。
- 修改用户可见行为时，请补充截图、录屏或清晰的复现说明。
- 修改配置、任务、角色逻辑或识别逻辑时，请说明适用场景和可能影响。
- 不要提交日志、缓存、临时文件、个人配置或无关生成文件。

- Before submitting a PR, have AI review the final changes, address valid findings, and briefly describe the review tool, results, and resolutions in the PR description.
- Keep the PR focused. Avoid mixing unrelated formatting, refactoring, and feature changes in one PR.
- Describe the purpose, implementation, impact, and test results.
- For user-visible behavior changes, include screenshots, recordings, or clear reproduction notes.
- For configuration, task, character logic, or recognition logic changes, describe the applicable scenarios and possible impact.
- Do not commit logs, caches, temporary files, personal settings, or unrelated generated files.

## 添加识别素材 / Adding Recognition Assets

`ok_templates/` 中的源图片和标注直接保存在本仓库中。

Source images and annotations in `ok_templates/` are tracked directly in this repository.

1. 如需添加识别素材，在 ok-ww 的「模板」标签页中添加图片并完成标注。
2. 点击「保存」，保存标注并生成识别素材。
3. 检查生成的修改，将相关的 `ok_templates/` 源图片、标注和 `assets/` 识别素材一起提交。

1. To add recognition assets, add the images and markup in ok-ww's Template tab.
2. Click Save to save the annotations and generate the recognition assets.
3. Review the generated changes and include the relevant `ok_templates/` source images, annotations, and `assets/` recognition assets in the same PR.

## 提交流程 / Submission Flow

1. Fork 本仓库并创建你的功能分支。
2. 完成修改并运行相关测试。
3. 确认是否需要先联系作者，尤其是新功能或大幅修改现有功能。
4. 使用 AI 审查最终修改，处理有效问题并记录结果。
5. 提交 PR，并填写 PR 模板中的所有相关内容，包括 AI 审查结果。
6. 根据维护者反馈调整修改。

1. Fork this repository and create your feature branch.
2. Make the changes and run relevant tests.
3. Confirm whether author contact is needed, especially for new features or major changes to existing behavior.
4. Have AI review the final changes, address valid findings, and record the results.
5. Open a PR and fill in all relevant sections of the PR template, including the AI review results.
6. Update the PR based on maintainer feedback.
