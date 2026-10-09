# usaturn/resoloop Issue #13: capture の早期停止と写真フォルダのマウント 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- 文書管理: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/resoloop/issues/13
- 状態: approved（2026-10-09 にユーザーが「お勧めで進めてください」で承認。承認した版: `68c61d8`。実行方法: Native（このセッションで実装し、最後にブランチ全体をレビュー））
- Spec: `../specs/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir-design.md`（approved、承認した版 `04a74fd`）
- 計画時の HEAD: resoloop `9cf7178f02a696cd91ae5fb092b9078e98f25beb`、create-reso-world `156a8e2`
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-13-screenshots`（ブランチ `feat/resoloop-13-screenshot-mount`）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-13-capture-export-dir`（ブランチ `fix/issue-13-capture-export-dir`）

**Goal:** 写真の保存先を読めない構成では capture を接続前にすぐ止め、Dev Container では任意のリンクでエージェントが撮影できるようにする。

**Architecture:** resoloop では、既定の保存先の解決で Pictures が取れないときに相対パスを作らず `CAPTURE_EXPORT_DIR_UNREACHABLE` を投げる。capture の失敗には、監視先・指定元・撮影前の状態を `context` で返す。create-reso-world では、WSL 側のリンクを読み取り専用でマウントし、リンクがあるときだけ `initialize.bash` が env ファイル経由で `RESOLOOP_SCREENSHOTS_DIR` を渡す。

**Tech Stack:** C#（.NET 10、xUnit）、bash、Dev Container（`devcontainer.json`）

## Global Constraints

- 新しいエラー: `CAPTURE_EXPORT_DIR_UNREACHABLE`、終了コード 3（`ExitCodes.ConfigurationError`）。context のキーは `picturesFolder`・`candidates`・`oneDriveCandidatesChecked`
- `CAPTURE_EXPORT_TIMEOUT`（終了コード 8）の context のキーは `directory`・`directorySource`・`directoryExistedBeforeCapture`・`imagesBeforeCapture`・`waitSeconds`
- `CAPTURE_DIRECTORY_NOT_FOUND`（終了コード 6）の context のキーは `directory`・`directorySource`
- 既存のエラーのメッセージの文言は変えない。`context` と `suggestions` だけを足す
- `directorySource` の値は `ConfigResolution.Sources["screenshotsDirectory"]` の値（`cli`・`environment:RESOLOOP_SCREENSHOTS_DIR`・設定ファイルのパス）、既定の解決なら `default`
- `ScreenshotDirectoryResolver.ResolveDefault` の戻り値の型（`string`）は変えない
- マウント: ソース `${localEnv:HOME}/.local/share/create-reso-world/resonite-screenshots`、ターゲット `/home/vscode/.local/share/create-reso-world/resonite-screenshots`、`type=bind,readonly`
- env ファイル: `.devcontainer/resonite-screenshots.env`（git の追跡外）。リンクがあるときの内容は `RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots` の 1 行、無いときは空
- テストは AGENTS.md の「テストの採用基準」に従う。文書・SKILL.md の文面にはテストを書かない
- rm / rmdir の対象にシェル変数を使うときは `${VAR:?}` で空値を防ぎ、パス全体を引用する
- 日本語の文書は AGENTS.md の「日本語表現」に従う（「正本」「契約」「着地」などを使わない）
- コミットメッセージの末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける
- push・PR の作成・マージはしない（ユーザーの明示指示があるまで「公開未実施」）

## Review Focus

1. 設定した保存先の親が無い（消したマウント先など）: すぐに `CAPTURE_DIRECTORY_NOT_FOUND` になり、context に監視先と指定元が入る → Task 2 のテスト
2. 既定の保存先がまだ無い（`~/Pictures` はあるが `Resonite` が無い Linux、初回撮影前の Windows）: タイムアウトの context が「撮影前に無かった・画像 0・指定元 default」を示す → Task 2 のテスト
3. 保存先を明示したときは、Pictures が取れない環境でも既定の解決を通らず、`CAPTURE_EXPORT_DIR_UNREACHABLE` にならない → Task 4 の手順 5
4. リンクを消して `initialize.bash` を再実行したとき、古い環境変数が env ファイルに残らない → Task 5 のテスト
5. `initialize.bash` を別の cwd から実行しても、env ファイルは cwd ではなくスクリプトの隣に書かれる → Task 5 のテスト

---

### Task 1: 既定の保存先が無いときの早期停止（resoloop）

テスト: 要。Pictures が取れない環境で相対パスを返していた不具合の再発を防ぐ。

**Files:**
- Modify: `src/RLoop.Core/ScreenshotDirectoryResolver.cs`（`ResolveDefault` と、新しい `ExportFolderSuggestions`・`Unreachable`・`ScreenshotDirectoryCandidate`）
- Test: `tests/RLoop.Tests/CaptureTests.cs`

**Interfaces:**
- Produces: `internal static readonly string[] ScreenshotDirectoryResolver.ExportFolderSuggestions`（Task 2 が使う）
- Produces: `public sealed record ScreenshotDirectoryCandidate(string Path, bool Exists)`（`namespace RLoop.Core`）

- [x] **Step 1: ベースラインを確かめる**

Run（CODE_ROOT で）: `dotnet test tests/RLoop.Tests --filter FullyQualifiedName~CaptureTests`
Expected: PASS（全件成功）。失敗があれば作業を止めて報告する

- [x] **Step 2: 失敗するテストを書く**

`tests/RLoop.Tests/CaptureTests.cs` の `ScreenshotDirectoryFindsActiveLocalizedOneDrivePicturesFolder` の後に追加する。

```csharp
    [Fact]
    public void ScreenshotDirectoryFailsFastWhenPicturesFolderIsUnavailable()
    {
        // Breaks caught: on Linux without ~/Pictures the resolver returned the relative path "Resonite", so capture
        // watched <cwd>/Resonite until CAPTURE_EXPORT_TIMEOUT while Resonite saved photos elsewhere (usaturn/resoloop#13).
        var error = Assert.Throws<RLoopException>(() => ScreenshotDirectoryResolver.ResolveDefault("", _root, _ => null));

        Assert.Equal("CAPTURE_EXPORT_DIR_UNREACHABLE", error.Code);
        Assert.Equal(ExitCodes.ConfigurationError, error.ExitCode);
        Assert.Equal("", error.Context["picturesFolder"]);
        Assert.Empty(Assert.IsAssignableFrom<IReadOnlyList<ScreenshotDirectoryCandidate>>(error.Context["candidates"]));
        Assert.Equal(OperatingSystem.IsWindows(), error.Context["oneDriveCandidatesChecked"]);
        Assert.NotEmpty(error.Suggestions);
    }
```

- [x] **Step 3: 失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests --filter FullyQualifiedName~ScreenshotDirectoryFailsFast`
Expected: ビルドエラー（`ScreenshotDirectoryCandidate` が無い）

- [x] **Step 4: 実装する**

`src/RLoop.Core/ScreenshotDirectoryResolver.cs` の `ResolveDefault` を次に置き換える（OneDrive の候補を足す `if (OperatingSystem.IsWindows())` のブロックと、`active` を選ぶ式は今のまま）。

```csharp
    public static string ResolveDefault(
        string? picturesDirectory = null,
        string? userProfile = null,
        Func<string, string?>? getEnvironment = null)
    {
        getEnvironment ??= Environment.GetEnvironmentVariable;
        picturesDirectory ??= Environment.GetFolderPath(Environment.SpecialFolder.MyPictures);
        userProfile ??= Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

        var candidates = new HashSet<string>(PathComparer);
        // GetFolderPath returns "" when the known folder is missing (Linux without ~/Pictures). Combining it would
        // yield the relative path "Resonite" under the working directory, which Resonite never writes to.
        string? primary = null;
        if (!string.IsNullOrWhiteSpace(picturesDirectory))
        {
            primary = Path.GetFullPath(Path.Combine(picturesDirectory, PlatformDirectory));
            candidates.Add(primary);
        }

        if (OperatingSystem.IsWindows())
        {
            AddOneDriveCandidates(candidates, getEnvironment("OneDriveConsumer"));
            AddOneDriveCandidates(candidates, getEnvironment("OneDrive"));

            if (Directory.Exists(userProfile))
            {
                try
                {
                    foreach (var root in Directory.EnumerateDirectories(userProfile, "OneDrive*", SearchOption.TopDirectoryOnly))
                        AddOneDriveCandidates(candidates, root);
                }
                catch (UnauthorizedAccessException) { }
                catch (IOException) { }
            }
        }

        // Resonite creates the primary path on first export. Prefer an existing candidate
        // with the newest exported image so stale known-folder redirection does not win.
        var active = candidates
            .Select(path => (Path: path, Latest: LatestImageWriteTime(path)))
            .Where(candidate => candidate.Latest is not null)
            .OrderByDescending(candidate => candidate.Latest)
            .FirstOrDefault();
        return active.Path ?? primary ?? throw Unreachable(picturesDirectory, candidates);
    }

    // Shared with ScreenshotExport so every failure about the export folder gives the same next steps.
    internal static readonly string[] ExportFolderSuggestions =
    [
        "Set --screenshots-dir, RESOLOOP_SCREENSHOTS_DIR or screenshotsDirectory to a folder this CLI can read.",
        "If Resonite runs on another machine or outside this container (for example a Windows host with a Linux dev container), mount its Pictures/Resonite folder and point the setting at the mount."
    ];

    private static RLoopException Unreachable(string picturesDirectory, IEnumerable<string> candidates) => new(
        "CAPTURE_EXPORT_DIR_UNREACHABLE",
        "No screenshot export folder is readable from this CLI: the Pictures known folder is unavailable and no screenshot directory is configured.",
        ExitCodes.ConfigurationError,
        new Dictionary<string, object?>
        {
            ["picturesFolder"] = picturesDirectory,
            ["candidates"] = candidates.Select(path => new ScreenshotDirectoryCandidate(path, Directory.Exists(path))).ToArray(),
            ["oneDriveCandidatesChecked"] = OperatingSystem.IsWindows()
        },
        ExportFolderSuggestions);
```

ファイルの末尾（クラスの閉じ括弧の後）に追加する。

```csharp

/// <summary>A screenshot folder the default resolver considered, reported when none is usable.</summary>
public sealed record ScreenshotDirectoryCandidate(string Path, bool Exists);
```

- [x] **Step 5: テストが通ることを確かめる**

Run: `dotnet test tests/RLoop.Tests --filter FullyQualifiedName~CaptureTests`
Expected: PASS（新しいテストと既存の `ScreenshotDirectoryMatchesResoniteKnownFolderConvention`・`ScreenshotDirectoryFindsActiveLocalizedOneDrivePicturesFolder` を含む全件）

- [x] **Step 6: コミットする**

```bash
git add src/RLoop.Core/ScreenshotDirectoryResolver.cs tests/RLoop.Tests/CaptureTests.cs
git commit -m "fix: stop capture when no screenshot export folder is readable

Linux without ~/Pictures made the default resolver return the relative
path Resonite, so capture watched the working directory until timeout.

Refs #13

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: 書き出し待ちの失敗に監視先と指定元を入れる（resoloop）

テスト: 要。タイムアウトなどの context は実行して確かめる出力であり、Review Focus 1・2 を固定する。

**Files:**
- Modify: `src/RLoop.Core/ScreenshotExport.cs`（コンストラクタ・`Arm`・タイムアウトの throw）
- Modify: `src/RLoop.Core/LiveCaptureService.cs`（`CaptureAsync` の引数と `ScreenshotExport` の生成）
- Modify: `src/RLoop.Cli/Program.cs:207,219-220`
- Test: `tests/RLoop.Tests/CaptureTests.cs`

**Interfaces:**
- Consumes: `ScreenshotDirectoryResolver.ExportFolderSuggestions`（Task 1）
- Produces: `public ScreenshotExport(string directory, string directorySource = "default")`
- Produces: `LiveCaptureService.CaptureAsync(..., CancellationToken cancellationToken = default, string screenshotDirectorySource = "default")`（既存の引数の後ろに足す。統合テストが `cancellationToken` を位置で渡しているため）

- [ ] **Step 1: 失敗するテストを書く**（ユーザー指示で省略。実施結果を参照）

`tests/RLoop.Tests/CaptureTests.cs` の `TimesOutInsteadOfReturningOldImageAndHonorsCancellation` の後に追加する。

```csharp
    [Fact]
    public async Task TimeoutReportsWatchedFolderAndItsSource()
    {
        // Breaks caught: CAPTURE_EXPORT_TIMEOUT had an empty context, so watching an unmounted or wrong folder looked
        // the same as a stopped renderer (usaturn/resoloop#13).
        await File.WriteAllBytesAsync(Path.Combine(_root, "old.png"), Png);
        using var export = new ScreenshotExport(_root, "environment:RESOLOOP_SCREENSHOTS_DIR");
        export.Arm();

        var error = await Assert.ThrowsAsync<RLoopException>(() => export.WaitAndCopyAsync(Path.Combine(_root, "out.png"), 1, 1, TimeSpan.FromMilliseconds(100)));

        Assert.Equal("CAPTURE_EXPORT_TIMEOUT", error.Code);
        Assert.Equal(Path.TrimEndingDirectorySeparator(Path.GetFullPath(_root)), error.Context["directory"]);
        Assert.Equal("environment:RESOLOOP_SCREENSHOTS_DIR", error.Context["directorySource"]);
        Assert.Equal(true, error.Context["directoryExistedBeforeCapture"]);
        Assert.Equal(1, error.Context["imagesBeforeCapture"]);
        Assert.Equal(0.1, (double)error.Context["waitSeconds"]!, 3);
        Assert.NotEmpty(error.Suggestions);
    }

    [Fact]
    public async Task TimeoutReportsDefaultFolderThatNeverAppeared()
    {
        // Breaks caught: a default folder that Resonite never creates (Linux ~/Pictures without Resonite) must be
        // distinguishable from an existing folder that simply received no photo.
        using var export = new ScreenshotExport(Path.Combine(_root, "Resonite"));
        export.Arm();

        var error = await Assert.ThrowsAsync<RLoopException>(() => export.WaitAndCopyAsync(Path.Combine(_root, "out.png"), 1, 1, TimeSpan.FromMilliseconds(100)));

        Assert.Equal("default", error.Context["directorySource"]);
        Assert.Equal(false, error.Context["directoryExistedBeforeCapture"]);
        Assert.Equal(0, error.Context["imagesBeforeCapture"]);
    }

    [Fact]
    public void MissingParentReportsFolderAndItsSource()
    {
        // Breaks caught: a configured folder whose parent is gone (for example a removed mount) gave no hint where the
        // setting came from.
        var missing = Path.Combine(_root, "missing", "Resonite");

        var error = Assert.Throws<RLoopException>(() => new ScreenshotExport(missing, "cli"));

        Assert.Equal("CAPTURE_DIRECTORY_NOT_FOUND", error.Code);
        Assert.Equal(Path.GetFullPath(missing), error.Context["directory"]);
        Assert.Equal("cli", error.Context["directorySource"]);
    }
```

- [ ] **Step 2: 失敗を確かめる**（ユーザー指示で省略）

Run: `dotnet test tests/RLoop.Tests --filter "FullyQualifiedName~TimeoutReports|FullyQualifiedName~MissingParentReports"`
Expected: ビルドエラー（`ScreenshotExport` に 2 引数のコンストラクタが無い）

- [x] **Step 3: `ScreenshotExport` を実装する**

フィールドとコンストラクタの先頭を次にする。

```csharp
    private readonly string _directory;
    private readonly string _directorySource;
    private readonly FileStream _lease;
    private HashSet<string>? _before;
    private bool _existedBeforeCapture;

    public ScreenshotExport(string directory, string directorySource = "default")
    {
        _directory = Path.TrimEndingDirectorySeparator(Path.GetFullPath(directory));
        _directorySource = directorySource;
        if (!Directory.Exists(_directory) && !Directory.Exists(Path.GetDirectoryName(_directory)))
            throw new RLoopException("CAPTURE_DIRECTORY_NOT_FOUND", $"Screenshot directory parent does not exist: {_directory}", ExitCodes.ValidationFailed,
                new Dictionary<string, object?> { ["directory"] = _directory, ["directorySource"] = directorySource });
```

（`var key = ...` 以降のリース取得は今のまま）

`Arm` を次にする。

```csharp
    public void Arm()
    {
        _existedBeforeCapture = Directory.Exists(_directory);
        _before = Files();
    }
```

`WaitAndCopyAsync` の最後の throw を次にする（メッセージの文言は今のまま）。

```csharp
        throw new RLoopException("CAPTURE_EXPORT_TIMEOUT", $"No complete screenshot arrived in '{_directory}' within {timeout.TotalSeconds:0.#} seconds. Check --screenshots-dir, local Resonite export settings and renderer availability.", ExitCodes.Timeout,
            new Dictionary<string, object?>
            {
                ["directory"] = _directory,
                ["directorySource"] = _directorySource,
                ["directoryExistedBeforeCapture"] = _existedBeforeCapture,
                ["imagesBeforeCapture"] = _before.Count,
                ["waitSeconds"] = timeout.TotalSeconds
            },
            ["Check that the target world is focused and the renderer is running.", .. ScreenshotDirectoryResolver.ExportFolderSuggestions]);
```

- [x] **Step 4: 指定元を `LiveCaptureService` と `Program.cs` から渡す**

`src/RLoop.Core/LiveCaptureService.cs` の `CaptureAsync` の引数の末尾と、`ScreenshotExport` の生成を次にする。

```csharp
    public async Task<CaptureArtifact> CaptureAsync(ApplyDocument document, string cameraName, string output,
        string screenshotDirectory, int? width = null, int? height = null, int waitSeconds = 60,
        CancellationToken cancellationToken = default, string screenshotDirectorySource = "default")
```

```csharp
        using var export = new ScreenshotExport(directory, screenshotDirectorySource);
```

`src/RLoop.Cli/Program.cs` の 207 行の後に指定元を取り出し、219-220 行の呼び出しに渡す。

```csharp
                    var screenshots = resolution.Config.ScreenshotsDirectory ?? ScreenshotDirectoryResolver.ResolveDefault();
                    var screenshotsSource = resolution.Sources.GetValueOrDefault("screenshotsDirectory") ?? "default";
```

```csharp
                    result = await new LiveCaptureService(captureClient).CaptureAsync(document, camera, captureOutput,
                        screenshots, width, height, parsed.IntOption("capture-timeout", 60, 1, 600), commandToken, screenshotsSource);
```

保存先の解決（207 行）が接続（`ConnectAsync`）より前にある順序は変えない。

- [x] **Step 5: テストが通ることを確かめる**

Run: `dotnet test tests/RLoop.Tests --filter FullyQualifiedName~CaptureTests`
Expected: PASS（全件）

- [x] **Step 6: 統合テストのプロジェクトがビルドできることを確かめる**

Run: `dotnet build ResoLoop.slnx`
Expected: 警告 0・エラー 0（統合テストの `CaptureAsync` の呼び出しが変更なしでビルドできる）

- [x] **Step 7: コミットする**

```bash
git add src/RLoop.Core/ScreenshotExport.cs src/RLoop.Core/LiveCaptureService.cs src/RLoop.Cli/Program.cs tests/RLoop.Tests/CaptureTests.cs
git commit -m "feat: report watched screenshot folder and its source on capture failures

Refs #13

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: 文書と同梱スキル（resoloop）

テスト: 不要。文書と SKILL.md の文面だけの変更。`git diff` の確認で代える。

**Files:**
- Modify: `README-DETAILS.md`（In-game screenshots の節）
- Modify: `skills/codex/resonite-build/SKILL.md`（手順 9 の capture の文）

- [x] **Step 1: `README-DETAILS.md` に段落を足す**

「OneDriveなどで保存先が異なる環境は、環境変数 `RESOLOOP_SCREENSHOTS_DIR` または…最小例です。」の段落の後に、空行をはさんで次の段落を追加する。

```markdown
Resoniteを別のPCやコンテナの外（例: WindowsのResoniteとLinuxのDev Container）で動かす場合、CLIはその写真フォルダを直接読めません。写真フォルダをCLIから読める場所にマウントし、`--screenshots-dir`・`RESOLOOP_SCREENSHOTS_DIR`・`screenshotsDirectory` のどれかでマウント先を指定してください。指定が無く、Pictures既知フォルダも取得できない環境（`~/Pictures` が無いLinuxなど）では、接続や撮影の前に `CAPTURE_EXPORT_DIR_UNREACHABLE`（exit 3）で停止し、調べた候補を `context` に返します。`CAPTURE_EXPORT_TIMEOUT` の `context` には、監視したフォルダ（`directory`）、その指定元（`directorySource`）、撮影前のフォルダの有無と画像の数が入ります。
```

- [x] **Step 2: `SKILL.md` の capture の文を差し替える**

`skills/codex/resonite-build/SKILL.md` の次の文を探す。

```text
On CAPTURE_EXPORT_TIMEOUT check the active world, renderer and export folder; on CAPTURE_FORMAT_MISMATCH use .jpg or enable Keep Original Screenshot Format.
```

次に置き換える。

```text
On CAPTURE_EXPORT_DIR_UNREACHABLE do not retry: this CLI cannot read Resonite's photo folder (for example from a container), so ask the user to configure a readable folder or leave the visual check to the user. On CAPTURE_EXPORT_TIMEOUT check the active world, renderer, and the folder and its source in the error context; on CAPTURE_FORMAT_MISMATCH use .jpg or enable Keep Original Screenshot Format.
```

- [x] **Step 3: 差分を確かめる**

Run: `git diff --stat && git diff -- README-DETAILS.md skills/codex/resonite-build/SKILL.md`
Expected: 2 ファイルだけが変わり、上の 2 か所以外に差分が無い

- [x] **Step 4: コミットする**

```bash
git add README-DETAILS.md skills/codex/resonite-build/SKILL.md
git commit -m "docs: explain unreachable screenshot export folders

Refs #13

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: resoloop の全体テストとコンテナでの再現確認

テスト: 新規のテストは書かない。Task 1〜3 の全体の回帰と、実際のコンテナでの挙動を、コマンドの実行で確かめる。

**Files:** なし（検証だけ）

- [x] **Step 1: 全体のテストを実行する**

Run（CODE_ROOT で）: `dotnet build ResoLoop.slnx && dotnet test ResoLoop.slnx --no-build`
Expected: すべて成功（実機の統合テストは環境変数が無いので実行されない）。件数を記録する

- [x] **Step 2: 修正版を導入する**

Run:

```bash
sha="$(git -C /workspaces/reso-world/external/resoloop/.worktrees/issue-13-capture-export-dir rev-parse HEAD)"
cd /workspaces/reso-world && bash scripts/resoloop-fork.sh install "${sha:?}"
resoloop --version
```

Expected: `installed: ResoLoop <版>.fork.<日付>.g<短い SHA>`、`resoloop --version` が同じ版を表示する。`external/resoloop` の checkout はこの SHA で detached になる（既定の運用どおり）

- [x] **Step 3: リンクの無い今のコンテナで、すぐに止まることを確かめる**

Run:

```bash
out="/tmp/claude-1000/-workspaces-reso-world-worlds-slum04/d7b8b65a-104b-4585-919c-a2f873cb7248/scratchpad/capture-check"
mkdir -p "${out:?}"
cd /workspaces/reso-world/worlds/slum04
start=$SECONDS
resoloop capture content/main.json --camera main --output "${out:?}/main.jpg" --url ws://localhost:1/ --json; echo "exit=$? elapsed=$((SECONDS - start))s"
```

Expected: 標準エラーに `"code":"CAPTURE_EXPORT_DIR_UNREACHABLE"`、`"picturesFolder":""`、`"candidates":[]`。`exit=3`、経過は 2 秒以内。`ws://localhost:1/` には何も待ち受けていないので、接続を試みていれば接続のエラーになる。この結果で、接続より前に止まったことが分かる

- [x] **Step 4: 作業ディレクトリに `Resonite` を作っていないことを確かめる**

Run: `test ! -e /workspaces/reso-world/worlds/slum04/Resonite && echo 'no Resonite under cwd'`
Expected: `no Resonite under cwd`

- [ ] **Step 5: 保存先を明示したときは既定の解決を通らないことを確かめる（Review Focus 3）**（ユーザー指示で省略。最終レビューで確認済み）

Step 3 で設定した `out` を使う（別のシェルで実行するときは、同じ値を設定し直す）。

Run:

```bash
cd /workspaces/reso-world/worlds/slum04
RESOLOOP_SCREENSHOTS_DIR="${out:?}" resoloop capture content/main.json --camera main --output "${out:?}/main.jpg" --url ws://localhost:1/ --json; echo "exit=$?"
```

Expected: `CAPTURE_EXPORT_DIR_UNREACHABLE` ではなく、接続のエラー（終了コード 4）

- [x] **Step 6: 結果を記録する**

Step 1〜5 の出力の要点（テストの件数、導入した版、エラーの JSON、終了コード、経過秒数）を作業報告に残す。導入した修正版は戻さない（次の rebuild で公開版に戻る）

### Task 5: Dev Container の写真フォルダのマウント（create-reso-world）

テスト: 要。`initialize.bash` の分岐（空のディレクトリ・リンク・リンク先が無いリンク）と env ファイルの生成は、実行して確かめる挙動である。マウントの固定一覧は、ホストの永続領域の増減を守る既存の固定値なので更新する。README の文面にはテストを書かない（表は既存の `test-readme.bash` が実装と突き合わせる）。

**Files:**
- Modify: `.devcontainer/test-initialize-mounts.bash`
- Modify: `.devcontainer/initialize.bash`
- Modify: `.devcontainer/devcontainer.json`（`mounts` と `runArgs`）
- Modify: `.devcontainer/README.md`（ツール表と「Resonite ワールド開発ツール」の節）
- Modify: `.gitignore`

**Interfaces:**
- Produces: `.devcontainer/resonite-screenshots.env`（`initialize.bash` が毎回書き直す。`devcontainer.json` の `runArgs` が読む）

- [x] **Step 1: テストを変える（失敗するテスト）**

DOC_ROOT の `.devcontainer/test-initialize-mounts.bash` を次のように変える。

(a) 検査 2 の注釈と固定一覧を次にする。

```bash
# 2. mounts は仕様 7.1 の表の 14 個（既存 13 ＋秘密情報）から、撤去した dsh と Grok Build の ~/.dsh・~/.grok を除いた 12 個に、
#    任意の Resonite の写真フォルダ（読み取り専用、usaturn/resoloop#13）を足した 13 個。
#    mount の増減はホストの永続領域と秘密情報の露出に関わるため、固定値で守る。1 の相互比較だけでは、
#    devcontainer.json と initialize.bash を同時に誤って変えたときに検出できない（Issue #36 C1）
expected='.claude
.claude.json
.codex
.config/create-reso-world
.config/devin
.config/gcloud
.config/gh
.config/glab-cli
.cursor
.local/share/create-reso-world/resonite-screenshots
.local/share/cursor-agent
.local/share/devin
.pi'
```

(b) 検査 3 の前に、`initialize.bash` のコピーを用意する。

```bash
# initialize.bash は自分の隣に resonite-screenshots.env を書くので、リポジトリの .devcontainer を書き換えないようにコピーを実行する
mkdir -p "$tmp/devcontainer"
cp "$init" "$tmp/devcontainer/initialize.bash"
run_init="$tmp/devcontainer/initialize.bash"
env_file="$tmp/devcontainer/resonite-screenshots.env"
```

(c) 検査 3 と 3b で `bash "$init"` を実行している 3 か所を `bash "$run_init"` に変える（`mounts_compare` に渡す `"$init"` は変えない）。

(d) 検査 3b の後に、検査 3c を足す。

```bash
# 3c. 写真フォルダ（usaturn/resoloop#13）: 空のディレクトリなら環境変数を渡さず、リンクなら渡す。リンクを消して再実行すると
#     空に戻る。リンク先が無ければ止まる。env ファイルは cwd ではなくスクリプトの隣に書く
shots='.local/share/create-reso-world/resonite-screenshots'
{ [ -d "$home/$shots" ] && [ ! -L "$home/$shots" ]; } || fail "initialize.bash did not create the placeholder ~/$shots"
{ [ -f "$env_file" ] && [ ! -s "$env_file" ]; } || fail "the env file must be empty without the link: $(cat "$env_file" 2>/dev/null)"
linkhome="$tmp/linkhome"
mkdir -p "$linkhome/.local/share/create-reso-world" "$tmp/windows-pictures/Resonite"
ln -s "$tmp/windows-pictures/Resonite" "$linkhome/$shots"
(cd "$tmp" && HOME="$linkhome" bash "$run_init")
[ "$(cat "$env_file")" = 'RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots' ] \
  || fail "the env file lacks the screenshots variable: $(cat "$env_file")"
[ -L "$linkhome/$shots" ] || fail 'initialize.bash replaced the link'
rm -- "${linkhome:?}/${shots:?}"
HOME="$linkhome" bash "$run_init"
[ ! -s "$env_file" ] || fail "the env file kept the variable after the link was removed: $(cat "$env_file")"
rmdir -- "${linkhome:?}/${shots:?}"
ln -s "$tmp/missing/Resonite" "$linkhome/$shots"
if out="$(HOME="$linkhome" bash "$run_init" 2>&1)"; then fail "initialize.bash succeeded with a dangling link: $out"; fi
grep -qF 'links to a missing folder' <<<"$out" || fail "initialize.bash did not report the dangling link: $out"
```

(e) 検査 4 のループを次にする。

```bash
# 4. postCreate はディレクトリの mount をすべて書き込み可能にする。ファイルの ~/.claude.json と、読み取り専用の写真フォルダは除く
#    （読み取り専用の mount を chown しようとすると postCreate が失敗する）
writable="$(sed -n '/^step "Ensuring user-writable directories under ~"$/,/; do$/p' "$installer")"
while IFS= read -r rel; do
  case "$rel" in
    .claude.json) continue ;;
    .local/share/create-reso-world/resonite-screenshots)
      ! grep -qF "\"\${HOME}/$rel\"" <<<"$writable" || fail "install_beforehand.bash must not chown the read-only mount ~/$rel"
      continue ;;
  esac
  grep -qF "\"\${HOME}/$rel\"" <<<"$writable" || fail "install_beforehand.bash does not make ~/$rel writable"
done <<<"$expected"
```

- [x] **Step 2: 失敗を確かめる**

Run（DOC_ROOT で）: `bash .devcontainer/test-initialize-mounts.bash`
Expected: FAIL（`unexpected mounts`。写真フォルダの mount がまだ無い）

- [x] **Step 3: `initialize.bash` を実装する**

`set -e` の後、`mkdir -p` の前に追加する。

```bash
# Resonite の写真フォルダ（任意、usaturn/resoloop#13）。WSL で Windows の Pictures/Resonite へのリンクにすると、
# コンテナから読み取り専用で読める。リンク先が無いと Docker の mount が分かりにくいエラーで失敗するので、先に止める
screenshots="${HOME}/.local/share/create-reso-world/resonite-screenshots"
if [ -L "$screenshots" ] && [ ! -d "$screenshots" ]; then
  echo "initialize: ${screenshots} links to a missing folder ($(readlink "$screenshots")); check that the Windows drive is visible (ls /mnt/c) and that Resonite has saved a photo, or remove the link" >&2
  exit 1
fi
```

`mkdir -p` の一覧の最後の `"${HOME}/.config/create-reso-world"` の行に ` \` を足し、次の行を加える。

```bash
  "${HOME}/.local/share/create-reso-world/resonite-screenshots"
```

ファイルの末尾に追加する。

```bash

# リンクがあるときだけ、写真フォルダの場所をコンテナの環境変数で渡す（devcontainer.json の runArgs の --env-file が読む）。
# mount と同じくコンテナの作成時に決まるので、リンクを作った・消した後は rebuild が要る
env_file="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/resonite-screenshots.env"
if [ -L "$screenshots" ]; then
  printf 'RESOLOOP_SCREENSHOTS_DIR=/home/vscode/.local/share/create-reso-world/resonite-screenshots\n' > "$env_file"
else
  : > "$env_file"
fi
```

- [x] **Step 4: `devcontainer.json` を変える**

`mounts` の `// 秘密情報（API トークンなど）…` のコメント行の前に追加する。

```jsonc
		// Resonite の写真フォルダ（任意）。WSL で Windows の Pictures/Resonite へのリンクにする。読み取り専用（usaturn/resoloop#13）
		"source=${localEnv:HOME}/.local/share/create-reso-world/resonite-screenshots,target=/home/vscode/.local/share/create-reso-world/resonite-screenshots,type=bind,readonly",
```

`runArgs` の `"--network=host"` に `,` を足し、その後に追加する。

```jsonc
		// initialize.bash が書く。写真フォルダがリンクのときだけ RESOLOOP_SCREENSHOTS_DIR を渡す
		"--env-file",
		"${localWorkspaceFolder}/.devcontainer/resonite-screenshots.env"
```

- [x] **Step 5: `.gitignore` に足す**

`## 個人設定・秘密情報` の一覧の最後（`.secrets/` の後）に追加する。

```gitignore
# initialize.bash が書く、コンテナに渡す環境変数（Resonite の写真フォルダ）
/.devcontainer/resonite-screenshots.env
```

- [x] **Step 6: README のツール表に行を足す**

`.devcontainer/README.md` のツール表で、`| 秘密情報 |` の行の前に追加する。

```markdown
| Resonite の写真フォルダ（任意） | WSL で Windows の Pictures/Resonite へのリンクを 1 回作る（「Resonite ワールド開発ツール」の節） | `~/.local/share/create-reso-world/resonite-screenshots`（読み取り専用） | `~/.local/share/create-reso-world/resonite-screenshots` | — | — |
```

- [x] **Step 7: README に手順の節を足す**

「Resonite ワールド開発ツール」の節の最後（「ResoLoop の公式要件には…成功扱いにはしない。」の段落の後、`## Meshy CLI と生成物の受け渡し` の前）に追加する。

````markdown
### Resonite の写真フォルダ（任意）

Resonite は写真を Windows の Pictures の `Resonite` フォルダに保存する。そのままではコンテナの `resoloop capture` が写真を読めず、
`CAPTURE_EXPORT_DIR_UNREACHABLE` で止まる。WSL 側にリンクを 1 回作ると、コンテナの
`~/.local/share/create-reso-world/resonite-screenshots` に読み取り専用でマウントされる。あわせて `initialize.bash` が
`.devcontainer/resonite-screenshots.env` に `RESOLOOP_SCREENSHOTS_DIR` を書き、`runArgs` の `--env-file` でコンテナに渡す。

1. Windows の PowerShell で Pictures の場所を調べる。OneDrive にリダイレクトされていれば、その場所が表示される

   ```powershell
   [Environment]::GetFolderPath('MyPictures')
   ```

2. その下に `Resonite` フォルダが無ければ、Resonite で写真を 1 枚撮る
3. WSL のターミナル（コンテナの外）で、`initialize.bash` が作った空のディレクトリをリンクに置き換える。
   `C:\Users\<名前>\Pictures` は `/mnt/c/Users/<名前>/Pictures` になる

   ```bash
   rmdir ~/.local/share/create-reso-world/resonite-screenshots
   ln -s /mnt/c/Users/<名前>/Pictures/Resonite ~/.local/share/create-reso-world/resonite-screenshots
   ```

4. Dev Container を rebuild し、コンテナで確かめる

   ```bash
   echo "$RESOLOOP_SCREENSHOTS_DIR"
   ls "$RESOLOOP_SCREENSHOTS_DIR"
   ```

リンク先が無くなると、`initialize.bash` がリンク先を表示して止まる。`/mnt/c` が見えるか（WSL の automount）とフォルダがあるかを
確かめるか、リンクを消して空のディレクトリに戻す。リンクを作った・消した後は、どちらも rebuild が要る。
````

- [x] **Step 8: テストが通ることを確かめる**

Run（DOC_ROOT で）: `bash .devcontainer/test-initialize-mounts.bash && bash .devcontainer/test-readme.bash && bash scripts/check-layout.sh`
Expected: `PASS: mounts, initialize.bash and postCreate agree`、`PASS: README implementation table and no hard-coded workspace path`、`PASS: check-layout`

- [x] **Step 9: リポジトリの `.devcontainer` に env ファイルができていないことを確かめる**

Run: `test ! -e .devcontainer/resonite-screenshots.env && git status --short`
Expected: env ファイルが無く、`git status` に変更した 6 ファイルだけが出る

- [x] **Step 10: コミットする**

```bash
git add .devcontainer/test-initialize-mounts.bash .devcontainer/initialize.bash .devcontainer/devcontainer.json .devcontainer/README.md .gitignore
git commit -m "feat: mount the Resonite photo folder read-only when linked

The container now gets RESOLOOP_SCREENSHOTS_DIR only when the WSL path
is a link to Windows Pictures/Resonite, so resoloop capture can read
photos; without the link it stops early (usaturn/resoloop#13).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: 全体の確認・記録・引き継ぎ

テスト: 新規のテストは書かない。両リポジトリの全テストとレイアウト検査、ブランチ全体のレビューで確かめる。

**Files:**
- Modify: `docs/superpowers/plans/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir.md`（チェックボックスと結果の記録）
- Modify: `docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir-design.md`（冒頭の `Plan:` の行と実装 HEAD）
- Create: `tmp/docs_draft/claude_handoffs/` の引き継ぎ（PARENT_ROOT、agent-handoff スキルの書式）

- [x] **Step 1: create-reso-world の全テストを実行する**

Run（DOC_ROOT で）: `bash .devcontainer/run-tests.bash && bash scripts/check-layout.sh`
Expected: すべて PASS

- [x] **Step 2: ブランチ全体をレビューする**

resoloop（CODE_ROOT の `origin/main..HEAD`）と create-reso-world（DOC_ROOT の `origin/main..HEAD`）の差分を、新しいレビュー担当に確認させる。致命的な指摘だけを直し、直したらその Task のテストを再実行する

- [x] **Step 3: 文書に結果を記録してコミットする**

Plan のチェックボックスを更新し、末尾に「実施結果」の節を足す（各 Task の検証結果、Task 4 のエラーの JSON と終了コード、テストの件数、両ブランチの HEAD、所要時間と主要 Task 別の内訳、公開未実施）。Spec の `Plan:` の行をこの Plan のパスに、実装 HEAD を追記する。状態は、実機の撮影の確認（Step 4 の引き継ぎ）が終わるまで `completed` にしない

```bash
git add docs/superpowers/plans/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir.md docs/superpowers/specs/2026-10-09-usaturn-resoloop-issue-13-capture-export-dir-design.md
git commit -m "docs: record resoloop issue 13 implementation results

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [x] **Step 4: rebuild 後の実機確認の引き継ぎを書く**

agent-handoff スキルで、次を受け取る側に渡す。ユーザーの作業（README の手順でリンクを作り、rebuild する）が先に要る。

1. コンテナで `echo "$RESOLOOP_SCREENSHOTS_DIR"` と `ls "$RESOLOOP_SCREENSHOTS_DIR"` が Windows の写真を示す
2. `resoloop discover` と `resoloop doctor --json` で接続を確かめる
3. `worlds/slum04` で `resoloop capture content/main.json --camera main --output <scratchpad>/main.jpg --url <URL> --capture-timeout 30 --json` が成功し、画像を Read で開ける。作られるのは `ResoLoop_Test_Capture_*` の一時 Slot だけで、終了時に消えることを確かめる。Windows の写真フォルダに写真が 1 枚増える
4. 読み取り専用の 9p マウントで、書き出しの完了待ち（排他読み込み）が動くこと（3 が成功すれば確認できる）
5. 結果を Plan の「実施結果」に追記し、Spec と Plan を `completed` にする。公開（push・PR）はユーザーの指示を待つ

- [ ] **Step 5: ユーザーに報告する**

両ブランチの HEAD、検証結果、公開未実施であること、rebuild 前にユーザーがする作業（README の手順）を報告する

## 実施結果

実行方法は Native（このセッションで実装し、最後にブランチ全体をレビュー）。2026-10-09 07:39Z（Plan の承認）〜 08:10Z ごろ。公開: 2026-10-09 にユーザーの指示「2」で push し、fork PR https://github.com/usaturn/resoloop/pull/15 と create-reso-world の PR を作成した（マージはしていない）。

### 実行中の変更（ユーザー指示）

Task 1 の途中で、ユーザーが「AGENTS.md を読んでテストは書かなくても良い場合があることをよく考えてね」「設定をされていることを確認する必要はないですよ」と指示した。AGENTS.md のテストの採用基準に照らし、値や設定が入っていることを確かめるだけのテストと確認をやめた。

- 残した: Task 1 の回帰テスト（実際に起きた不具合の再発防止）。確かめるのはエラーコードだけにした
- やめた: Task 1 のテストの context の各値の確認、Task 2 の 3 本、Task 4 の Step 5、Task 5 の検査 3c と postCreate の「chown しない」の確認、README と引き継ぎの `echo "$RESOLOOP_SCREENSHOTS_DIR"` の確認
- 既存のテストに合わせる変更（マウントの固定一覧、検査 4 の除外、`initialize.bash` をコピーして実行）は行った

### 各 Task

| Task | コミット | 結果 |
| --- | --- | --- |
| 1 | resoloop `901c3b8` | RED「No exception was thrown」（相対パスを返す今の挙動）→ GREEN。`CaptureTests` 23/23 |
| 2 | resoloop `443c836` | テストなし（ユーザー指示）。`dotnet build ResoLoop.slnx` 警告 0・エラー 0（統合テストの呼び出しは変更なしでビルド可）、`CaptureTests` 23/23 |
| 3 | resoloop `9e43c95` | 文書のみ。`git diff` で 2 か所だけの変更を確認 |
| 4 | なし | `dotnet test ResoLoop.slnx` で RLoop.Tests 454/454、RLoop.IntegrationTests 19/19（実機のテストは無効）。`scripts/resoloop-fork.sh install 9e43c95` で `0.1.0-preview.17.fork.20261009.g9e43c95` を導入。slum04 で `resoloop capture content/main.json --camera main --url ws://localhost:1/ --json` が `CAPTURE_EXPORT_DIR_UNREACHABLE`（`picturesFolder: ""`、`candidates: []`）、exit 3、0 秒、作業ディレクトリに `Resonite` を作らない |
| 5 | create-reso-world `fd2eb94` | テストの変更で RED（unexpected mounts）→ GREEN。`test-initialize-mounts`・`test-readme`・`check-layout` PASS。コピーした `initialize.bash` の一時的な実行で、リンクあり → 変数 1 行、リンク先なし → exit 1 とメッセージを確認 |
| 6 | create-reso-world `d3050ed` ほか | 最終レビューの修正 1 件。`run-tests.bash` 29 本 PASS、`check-layout` PASS |

### 最終レビュー（opus、読み取り専用）

Critical 0、Important 0、Minor 4。マージしてよいとの判断。Review Focus 1〜5 はコードの読解と実行で確認済み（Focus 3 はレビュー担当が修正版で実行し、明示した保存先では既定の解決を通らず接続のエラー（exit 4）になることを確認）。

- 修正した: Minor 1。`CDPATH` に `.` を含む値が export されていると、`initialize.bash` の `cd` がパスを出力して env ファイルの書き出しに失敗し、リンクの有無に関係なくコンテナの作成が止まる。影響から致命的と判断し、`cd` を使わない形にした（`d3050ed`）。修正前に `CDPATH=.:` で exit 1、修正後に exit 0 を一時的な実行で確認した（テストは追加していない）
- 直さない: Minor 2（`install_beforehand.bash` の注釈に、読み取り専用のマウントが例外であることが書かれていない）、Minor 3（`--url auto` では discovery（最大 12 秒）の後に止まる。接続も一時 Slot の作成もしない）
- 実機確認で見る: Minor 4（drvfs が EACCES を返すと、排他読み込みの `UnauthorizedAccessException` を捕まえずに capture が想定外の例外で失敗しうる。一時 Slot は消える）
- 範囲外として受け入れた主な点: NuGet の公開版には修正が入っていないため、rebuild 後のリンク無しの状態では従来どおりタイムアウトまで待つ（README の「止まる」は修正版が公開されるまで当てはまらない）。リンクがあれば公開版でも環境変数で撮影できる

### 所要時間（UTC）

| 区分 | 時間 |
| --- | --- |
| Task 1（ベースライン、RED 2 回、実装、テストの絞り込み） | 07:40〜07:43（約 3 分） |
| Task 2・3 | 07:43〜07:44（約 1 分） |
| Task 4（全テスト 93 秒、fork 版の導入、再現確認） | 07:44〜07:46（約 2 分） |
| Task 5 | 07:46〜07:48（約 2 分） |
| 最終レビュー（レビュー担当 約 9 分） | 07:49〜07:58 |
| 指摘の修正・全テスト・記録・引き継ぎ | 07:59〜08:10 |

### 次の作業

- ユーザー: `.devcontainer/README.md` の「Resonite の写真フォルダ（任意）」の手順でリンクを作り、rebuild する
- rebuild 後: 引き継ぎ `tmp/docs_draft/claude_handoffs/20261009T081000Z-resoloop-issue13-live-capture.handoff.md` の手順で実機の撮影を確かめ、この節に追記して Spec と Plan を `completed` にする
- マージは、ユーザーの指示を待つ
