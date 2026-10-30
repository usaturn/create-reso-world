# create-reso-world#98 プラグインのコマンドと doctor 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**状態:** `draft`（issue-to-pr の実行許可による。内容の承認ではない）

**Goal:** `resoloop [--project DIR] <plugin-command> ...` の生 argv の分離・解決・起動・終了と、doctor のツール確認、組み込み名 catalog を、I #298 が結線できる API として `usaturn/resoloop:feat/plugin-v2` に入れる。

**Architecture:** CLI 層（`RLoop.Cli`）が生 argv の分類・プロジェクトとプラグインの解決・lease の保持・シグナルを受け持ち、Core 層（`RLoop.Core.Plugins`）が argv と環境の組み立て、プロセスの閉じ込め（Linux のプロセスグループ、Windows の Job）、ツール確認を受け持つ。`Program.cs` は変えない。

**Tech Stack:** C# / .NET 10.0.201（`global.json`）、xUnit、P/Invoke（libc・kernel32）

**Spec:** `docs/superpowers/specs/2026-10-30-create-reso-world-issue98-plugin-commands-design.md`（create-reso-world、この Plan と同じブランチ）

## Global Constraints

- 変えてよいファイルは Spec 1 章の表の 9 つ（とそのディレクトリ）だけ。F の所有ファイル・`Program.cs`・`CommandLine.cs`・csproj・#99/#100 のコードは変えない。変更が要ると分かったら止まり、親 #95 の調整役の裁定を求める
- 作業ルート: `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-98-plugin-commands`（branch `feat/create-reso-world-issue-98-plugin-commands`、base `dd0b40fb216b0c9fbd82da44903195a885104015`）
- 環境変数の名前: `RESOLOOP_PLUGIN_NAME`・`RESOLOOP_PLUGIN_COMMAND`・`RESOLOOP_PLUGIN_ROOT`・`RESOLOOP_PLUGIN_DATA`・`RESOLOOP_PLUGIN_PROJECT_ROOT`・`RESOLOOP_PLUGIN_HOST_ARGV`（JSON 配列）・`RESOLOOP_PLUGIN_HOST_VERSION`、`PYTHONPYCACHEPREFIX=<data>/.cache/python`、`UV_PROJECT_ENVIRONMENT=<data>/.venv`。親の `RESOLOOP_PLUGIN_*` はすべて除く
- エラーコードと終了コード: `INVALID_ARGUMENT` 2、`UNKNOWN_COMMAND` 2、`PLUGIN_COMMAND_START_FAILED` 9、`PLUGIN_COMMAND_TIMEOUT` 8、`PLUGIN_COMMAND_CANCELLED` 7、`PLUGIN_COMMAND_STOP_FAILED` 7。context の鍵は `plugin`・`command`・`program`・`timeoutSeconds`・`processGroup`
- 停止の確認は 5 秒、ツール確認の期限は 1 回 30 秒、ツール確認の出力は stdout・stderr それぞれ最大 64 KiB、版の文字列は最大 200 文字
- Windows は `.exe` だけを起動する（PATH で探す名前は `.exe` で終わらなければ付ける。`./相対パス` は付けず、書かれたとおりのパスが `.exe` で終わることを求める）。PATH は絶対パスの要素だけ。シェルを通さない
- テストは AGENTS.md の S だけ（Spec 5 章の表の 7 件）。文言・一覧・存在だけの照合、同じ守りの重複を足さない
- コメントの密度・命名・書き方は `src/RLoop.Core/Plugins/PluginGit.cs` に合わせる（英語のコメント、必要な箇所だけ）

## 受け入れ基準

### 動作環境

Linux（この Dev Container、.NET 10.0.201）で `dotnet build ResoLoop.slnx --nologo` と `dotnet test ResoLoop.slnx --no-build --nologo` が通る。Windows は PR の公開 CI（`windows-latest`、`.github/workflows/ci.yml`）の Build・Test・Pack・smoke が通る。Windows の手動の実機確認はしない。Resonite・Blender・認証情報は使わない。

### 実入力

- プロジェクト `作業 ワールド`（空白と日本語）、導入元 `導入 元/<plugin>`
- 利用者の引数: `""`、`日本語 引数`、`a\nb`、`--help`、`--version`、`--json`、`--`、`;`、`$(echo injected)`、`"quoted" \back\`、`end\`
- manifest の args に `${pluginRoot}`・`${pluginData}`
- 親の環境の古い `RESOLOOP_PLUGIN_PROJECT_ROOT=/elsewhere`

### 防御範囲

| 守り | テスト（Task） | 通る例 | 対象外の反例 |
| --- | --- | --- | --- |
| 組み込みの乗っ取り | `BuiltinNamesNeverReachPlugins`（1） | 別名は `Parse` がプラグインの呼び出しとして返す | — |
| 先頭の終了後に子孫が残る、子の失敗の終了コードを成功にする | `NormalExitStopsLeftoverDescendants`（2） | 戻り値 7 | 自分でグループを抜けた子孫（対象外） |
| 期限切れを成功にする、子孫が残る | `TimedOutCommandsFailAndStopTheirProcessTree`（2）。期限 5 秒（Windows CI の dotnet の起動で孫の PID の記録より先に切れないため） | — | 本体の SIGKILL（対象外） |
| cwd・プロジェクトの同名プログラム、Windows の `.cmd` | `ProgramsResolveOnlyFromAbsolutePathOrThePackage`（2） | `./probe/CommandProbe`（package）と `dotnet`（絶対 PATH） | — |
| 生 argv の変形・シェル解釈、cwd・プロジェクト・data の取り違え、古い環境変数 | `RawArgumentsReachTheChildUnchanged`（3） | 同じテスト | — |
| キャンセルを成功にする、実行中に package が消される | `CommandsHoldTheLeaseAndCancellationNeverSucceeds`（3） | 終わった後の remove | — |
| required のツールの不足・失敗を pass にする | `RequiredToolProblemsAreNeverPassing`（4） | `dotnet --version` の pass | optional の不足は warning |

## Review Focus

1. Windows の命令行の引用: 末尾の `\`、`"` の前の `\` の連続、空文字 — `RawArgumentsReachTheChildUnchanged` の入力に `"quoted" \back\` と `end\` を入れる（Task 3）
2. data が消されていた（利用者が削除）: 起動前に作り直す — Task 2 の `NormalExitStopsLeftoverDescendants` の前に data を消しておき、`pids.json` が書けることで確かめる
3. stdin がパイプ・ファイルのときは子に届き、端末のときは EOF — テストの host の stdin を制御できないので、I の結線後に `echo x | resoloop <cmd>` で確かめる項目として handoff に書く
4. 同じプロジェクトでプラグインのコマンドを 2 つ同時に実行: 2 つ目は `PLUGIN_PROJECT_BUSY`（F の lease）— `CommandsHoldTheLeaseAndCancellationNeverSucceeds` の実行中の remove で同じ lock を確かめる（Task 3）
5. manifest に `timeoutSeconds` が無いときのプロジェクト設定の `commandTimeoutSeconds` — Task 5 の一時の確認で、`.resoloop.json` の `commandTimeoutSeconds: 2` が効くことを見る

---

### Task 1: 組み込み名 catalog と生 argv の分類

**テスト:** 要（S: 組み込みの乗っ取り）。`BuiltinNamesNeverReachPlugins` だけ。

**Files:**
- Create: `src/RLoop.Cli/BuiltinCommandCatalog.cs`
- Create: `src/RLoop.Cli/PluginCommandDispatch.cs`（この Task では `PluginInvocation` と `Parse` だけ）
- Create: `tests/RLoop.Tests/PluginCommandTests.cs`

**Interfaces:**
- Consumes: `RLoop.Core.Plugins.PluginNameReservations`、`BundledSkillManager.Names`、`UixRecipes.Catalog`
- Produces:
  - `public static class BuiltinCommandCatalog { IReadOnlySet<string> Commands; bool IsBuiltin(string name); PluginNameReservations Reservations; }`（`Commands` は Spec 3.2 の 33 名、`StringComparer.OrdinalIgnoreCase` の `FrozenSet`）
  - `public sealed record PluginInvocation(string? Project, string Command, IReadOnlyList<string> Arguments);`
  - `public static PluginInvocation? PluginCommandDispatch.Parse(IReadOnlyList<string> args)`（Spec 3.1。`--project` の値の空・重複は `RLoopException("INVALID_ARGUMENT", ..., ExitCodes.InvalidArguments)`）
  - テストの helper（Task 2〜3 も使う）: `PluginCommandTests` の `_root`（一時ディレクトリ、`Dispose` で `PluginPathPolicy.DeleteTree`）、`string CreateProject(string name = "作業 ワールド")`（`.resoloop.json` に `{}`）、`InstalledPlugin InstallPlugin(string project, string name, string commandsJson, PluginNameReservations? reservations = null, bool withProbe = false)`（`導入 元/<name>/resoloop-plugin.json` を書き、`withProbe` なら probe の出力を `probe/` に写し、`new PluginInstaller(new PluginRegistry(project, "0.2.0", reservations ?? BuiltinCommandCatalog.Reservations)).Install(source)`）

- [ ] **Step 1: 失敗するテストを書く**

```csharp
// S: a plugin installed by an older ResoLoop must never take over a built-in name.
[Fact]
public void BuiltinNamesNeverReachPlugins()
{
    var project = CreateProject();
    InstallPlugin(project, "legacy-plugin",
        """[{"name":"import","description":"old","program":"dotnet"},{"name":"legacy-run","description":"run","program":"dotnet"}]""",
        new PluginNameReservations([], [], []));
    Assert.Null(PluginCommandDispatch.Parse(["--project", project, "import", "x"]));
    Assert.Null(PluginCommandDispatch.Parse(["--project=" + project, "IMPORT"]));
    var invocation = PluginCommandDispatch.Parse(["--project", project, "legacy-run", "--json"]);
    Assert.NotNull(invocation);
    Assert.Equal(("legacy-run", project), (invocation!.Command, invocation.Project));
    Assert.Equal(["--json"], invocation.Arguments);
}
```

- [ ] **Step 2: 実行して失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter FullyQualifiedName~PluginCommandTests.BuiltinNamesNeverReachPlugins`
Expected: コンパイルエラー（`PluginCommandDispatch`・`BuiltinCommandCatalog` が無い）

- [ ] **Step 3: `BuiltinCommandCatalog` と `PluginCommandDispatch.Parse` を実装する**

`Reservations` は `new PluginNameReservations(Commands, BundledSkillManager.Names, UixRecipes.Catalog.Select(r => r.Name))`。`Parse` は先頭の `--project`/`--project=` を読み、候補が無い・`-` で始まる・`IsBuiltin` なら `null`。

- [ ] **Step 4: テストが通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS（1 件）

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Cli/BuiltinCommandCatalog.cs src/RLoop.Cli/PluginCommandDispatch.cs tests/RLoop.Tests/PluginCommandTests.cs
git commit -m "feat: add the built-in command catalog and raw plugin argv split (create-reso-world#98)"
```

### Task 2: Core の起動・閉じ込め・停止

**テスト:** 要（S: 子孫の残り、期限切れ・失敗の成功扱い、別のプログラムの実行）。3 件。

**Files:**
- Create: `src/RLoop.Core/Plugins/PluginRuntimeEnvironment.cs`
- Create: `src/RLoop.Core/Plugins/PluginCommandRunner.cs`
- Create: `tests/fixtures/plugins/commands/command-probe/CommandProbe.csproj`（`git-probe` と同じ形。RLoop.Core を参照しない）
- Create: `tests/fixtures/plugins/commands/command-probe/Program.cs`
- Modify: `tests/RLoop.Tests/PluginCommandTests.cs`

**Interfaces:**
- Consumes: Task 1 のテストの helper、F の `InstalledPlugin`・`PluginCommand`・`PluginPathPolicy`
- Produces:
  - `public sealed record PluginCommandRequest(InstalledPlugin Plugin, PluginCommand Command, string ProjectRoot, IReadOnlyList<string> Arguments, IReadOnlyList<string> HostArgv, string HostVersion, TimeSpan Timeout, IReadOnlyDictionary<string, string?> BaseEnvironment);`
  - `public static Task<int> PluginCommandRunner.RunAsync(PluginCommandRequest request, CancellationToken cancellationToken)`（Spec 3.4・3.5。`HostArgv` が空なら `PLUGIN_COMMAND_START_FAILED`）
  - `public static class PluginRuntimeEnvironment`: 7 つの変数名の `const string`（`NameVariable`・`CommandVariable`・`RootVariable`・`DataVariable`・`ProjectRootVariable`・`HostArgvVariable`・`HostVersionVariable`）と `Prefix`、`IReadOnlyList<string> ExpandArguments(InstalledPlugin plugin, PluginCommand command, IReadOnlyList<string> userArguments)`、`IReadOnlyDictionary<string, string> Create(PluginCommandRequest request)`（Windows は大小文字を区別しない辞書）
  - internal（Task 4 が使う）: `PluginExecutable.Find(string name, IReadOnlyDictionary<string, string?> environment) : string?`（区切りの無い名前を PATH の絶対パスの要素から。Windows は `.exe`）、`PluginProcess.Start(string executable, IReadOnlyList<string> arguments, string workingDirectory, IReadOnlyDictionary<string, string> environment, bool captureOutput) : PluginProcess`、`PluginProcess.Output`/`ErrorOutput`（`captureOutput` のときのパイプ）、`PluginProcess.Exited : Task`、`PluginProcess.StopAsync() : Task<int>`（グループ・Job を止めて 5 秒以内に確かめ、先頭の終了コードを返す。確かめられなければ `PLUGIN_COMMAND_STOP_FAILED`）
- 閉じ込めは F の `PluginGit` の `ContainedProcess`・`LinuxProcess`・`WindowsProcess`・`UnixNative`・`WindowsNative`・`Utf8Vector`・`WindowsAttributes` を出発点に写し、次だけを変える: 実行ファイルは呼出元が解決した絶対パス（`posix_spawn`）、出力を引き継ぐ形（`captureOutput=false`）では 1・2 を dup2 せずに引き継ぎ、stdin は `Console.IsInputRedirected` が false なら `/dev/null`（`posix_spawn_file_actions_addopen`）・Windows は `NUL`、Windows は `CREATE_NO_WINDOW` を使わず標準出力・エラーの handle も複製して handle list に入れる、エラーは `PLUGIN_COMMAND_*`

probe（`Program.cs`）の動き（`args[0]` で分ける）:
- `record <exit>`: `{"argv": args, "cwd": 現在のディレクトリ, "env": RESOLOOP_PLUGIN_* の全部}` を `$RESOLOOP_PLUGIN_DATA/received.json` に UTF-8 で書き、`<exit>` で終わる
- `spawn <exit|hang>`: 自分を `sleep` で起動した孫（`Environment.ProcessPath` が dotnet なら `[自分の dll, "sleep"]`）を作り、`{"child": 自分の PID, "grandchild": 孫の PID}` を `$RESOLOOP_PLUGIN_DATA/pids.json` に書いてから、`hang` なら止まらず、数値ならその値で終わる
- `sleep`: 240 秒待つ
- `marker <path>`: `<path>` に `ran` を書いて 0 で終わる（実行されてはいけないプログラムの目印）

テストの helper を足す: `CommandProbeFixture`（`IClassFixture`。`dotnet build <fixtures/plugins/commands/command-probe/CommandProbe.csproj> --nologo --artifacts-path <一時>` を 1 回だけ実行し、出力ディレクトリ `<一時>/bin/CommandProbe/debug` を持つ）、`static bool IsRunning(int pid)`（Linux は `/proc/<pid>/stat` が無いか `) Z ` なら false、Windows は `Process.GetProcessById` と `HasExited`）、`finally` で残った PID を止める前に `/proc/<pid>/cmdline` が `CommandProbe` を含むことを確かめる（F の `GitFailuresAndTimeoutNeverBecomeSuccessfulCopies` と同じ慎重さ）、`PluginCommandRequest Request(InstalledPlugin plugin, string command, IReadOnlyList<string> args, TimeSpan timeout, IReadOnlyDictionary<string, string?>? environment = null)`（`HostArgv = ["/host/resoloop"]`、`HostVersion = "0.2.0"`、環境の既定はプロセスの環境の写し）

- [ ] **Step 1: 失敗するテストを書く**

```csharp
// S: descendants left by a finished command must not keep using the package after the lease is released;
// a failing child exit code must never become success.
[Fact]
public async Task NormalExitStopsLeftoverDescendants()
{
    var project = CreateProject();
    var plugin = InstallPlugin(project, "probe-plugin",
        """[{"name":"probe-spawn","description":"spawn","program":"dotnet","args":["${pluginRoot}/probe/CommandProbe.dll","spawn","7"]}]""", withProbe: true);
    PluginPathPolicy.DeleteTree(plugin.DataDirectory, "PLUGIN_REMOVE_REFUSED");   // Review Focus 2
    var exit = await PluginCommandRunner.RunAsync(Request(plugin, "probe-spawn", [], TimeSpan.FromSeconds(60)), CancellationToken.None);
    Assert.Equal(7, exit);
    var pids = ReadPids(plugin);
    Assert.False(IsRunning(pids.Child)); Assert.False(IsRunning(pids.Grandchild));
}

// S: a deadline must never report success and must stop the whole tree.
[Fact]
public async Task TimedOutCommandsFailAndStopTheirProcessTree()
{
    var project = CreateProject();
    var plugin = InstallPlugin(project, "probe-plugin",
        """[{"name":"probe-hang","description":"hang","program":"dotnet","args":["${pluginRoot}/probe/CommandProbe.dll","spawn","hang"]}]""", withProbe: true);
    var watch = Stopwatch.StartNew();
    var error = await Assert.ThrowsAsync<RLoopException>(() =>
        PluginCommandRunner.RunAsync(Request(plugin, "probe-hang", [], TimeSpan.FromSeconds(5)), CancellationToken.None));
    Assert.Equal(("PLUGIN_COMMAND_TIMEOUT", ExitCodes.Timeout), (error.Code, error.ExitCode));
    Assert.InRange(watch.Elapsed.TotalSeconds, 5, 40);
    var pids = ReadPids(plugin);
    Assert.False(IsRunning(pids.Child)); Assert.False(IsRunning(pids.Grandchild));
}

// S: only the package or absolute PATH entries may supply the program; never cwd/project files or Windows batch files.
[Fact]
public async Task ProgramsResolveOnlyFromAbsolutePathOrThePackage()
{
    var project = CreateProject();
    var marker = Path.Combine(_root, "marker-ran");
    var tools = Path.Combine(project, "tools");   // relative PATH entry "tools" with project as cwd
    Directory.CreateDirectory(tools);
    // Linux: tools/evil is an executable sh script writing the marker. Windows: tools/evil.cmd and an absolute dir with evil.cmd.
    WriteMarkerProgram(tools, "evil", marker);
    var environment = CopyEnvironment();
    environment["PATH"] = OperatingSystem.IsWindows()
        ? tools + Path.PathSeparator + environment["PATH"]      // absolute, but only evil.cmd exists there
        : "tools" + Path.PathSeparator + environment["PATH"];   // relative entry is ignored
    var plugin = InstallPlugin(project, "probe-plugin",
        $$"""[{"name":"probe-evil","description":"evil","program":"evil"},
              {"name":"probe-local","description":"local","program":"./probe/{{ApphostName()}}","args":["record","0"]}]""", withProbe: true);
    var error = await Assert.ThrowsAsync<RLoopException>(() =>
        PluginCommandRunner.RunAsync(Request(plugin, "probe-evil", [], TimeSpan.FromSeconds(30), environment), CancellationToken.None));
    Assert.Equal("PLUGIN_COMMAND_START_FAILED", error.Code);
    Assert.False(File.Exists(marker));
    Assert.Equal(0, await PluginCommandRunner.RunAsync(Request(plugin, "probe-local", [], TimeSpan.FromSeconds(60), environment), CancellationToken.None));
}
```

`ApphostName()` は Windows で `CommandProbe.exe`、それ以外で `CommandProbe`。`WriteMarkerProgram` は Linux で `#!/bin/sh` の実行可能ファイル、Windows で `evil.cmd`（`echo ran> "<marker>"`）を書く。

- [ ] **Step 2: 実行して失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~PluginCommandTests"`
Expected: コンパイルエラー（`PluginCommandRunner` が無い）

- [ ] **Step 3: probe、`PluginRuntimeEnvironment`、`PluginCommandRunner` を実装する**

`RunAsync` の順: 実行ファイルの解決（`./` は `PluginPathPolicy.Combine(plugin.PackageDirectory, ..., "PLUGIN_MODIFIED")`、Linux は通常ファイルかつ `euidaccess(X_OK)`、Windows は `.exe`。名前は `PluginExecutable.Find`）→ data の `EnsureNoLinks(allowMissing)`・作成・`EnsureNoLinks` → argv と環境 → `PluginProcess.Start(captureOutput: false)` → `Exited` を「期限」と「呼出元のキャンセル」の linked token で待つ → どの経路でも `StopAsync` → 期限なら TIMEOUT、キャンセルなら CANCELLED（先頭が 0 で終わっていても、`cancellationToken.IsCancellationRequested` なら CANCELLED）、それ以外は終了コード。

- [ ] **Step 4: テストが通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS（4 件）

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Core/Plugins/PluginRuntimeEnvironment.cs src/RLoop.Core/Plugins/PluginCommandRunner.cs tests/fixtures/plugins/commands tests/RLoop.Tests/PluginCommandTests.cs
git commit -m "feat: launch plugin commands in a contained process tree (create-reso-world#98)"
```

### Task 3: CLI の解決・lease・シグナル

**テスト:** 要（S: 生 argv・cwd・環境の取り違え、キャンセルの成功扱い、実行中の削除）。2 件。

**Files:**
- Modify: `src/RLoop.Cli/PluginCommandDispatch.cs`
- Modify: `tests/RLoop.Tests/PluginCommandTests.cs`

**Interfaces:**
- Consumes: Task 1 の `Parse`・`BuiltinCommandCatalog.Reservations`、Task 2 の `PluginCommandRunner.RunAsync`・`PluginCommandRequest`
- Produces:
  - `public sealed record PluginDispatchContext(string ResoloopVersion, string StartDirectory, IReadOnlyDictionary<string, string?> Environment, IReadOnlyList<string> HostArgv) { public static PluginDispatchContext Current(string resoloopVersion); }`（`HostArgv`: `Environment.ProcessPath` の名前が `dotnet` なら `[ProcessPath, Assembly.GetEntryAssembly()!.Location]`、それ以外は `[ProcessPath]`、`ProcessPath` が null なら空）
  - `public static Task<int> PluginCommandDispatch.RunAsync(PluginInvocation invocation, PluginDispatchContext context, CancellationToken cancellationToken)`（Spec 3.3。実行中だけ `PosixSignalRegistration` で SIGINT・SIGTERM・SIGHUP・SIGQUIT を `Cancel = true` にして linked のキャンセルに変える）

- [ ] **Step 1: 失敗するテストを書く**

```csharp
// S: the child must receive exactly the user's tokens (no parsing, no shell), the selected project as cwd,
// and fresh plugin variables even if the parent environment carries stale ones.
[Fact]
public async Task RawArgumentsReachTheChildUnchanged()
{
    var project = CreateProject("作業 ワールド");
    var plugin = InstallPlugin(project, "probe-plugin",
        """[{"name":"probe-record","description":"record","program":"dotnet","args":["${pluginRoot}/probe/CommandProbe.dll","record","3","${pluginData}"]}]""", withProbe: true);
    string[] user = ["", "日本語 引数", "a\nb", "--help", "--version", "--json", "--", ";", "$(echo injected)", "\"quoted\" \\back\\", "end\\"];
    var environment = CopyEnvironment();
    environment[PluginRuntimeEnvironment.ProjectRootVariable] = "/elsewhere";
    var context = new PluginDispatchContext("0.2.0", _root, environment, ["/host/resoloop"]);
    var invocation = PluginCommandDispatch.Parse(["--project", project, "probe-record", .. user])!;
    Assert.Equal(3, await PluginCommandDispatch.RunAsync(invocation, context, CancellationToken.None));
    var received = ReadReceived(plugin);
    Assert.Equal(["record", "3", plugin.DataDirectory, .. user], received.Argv);
    Assert.Equal(project, received.Cwd);
    Assert.Equal(project, received.Env[PluginRuntimeEnvironment.ProjectRootVariable]);
    Assert.Equal(plugin.PackageDirectory, received.Env[PluginRuntimeEnvironment.RootVariable]);
    Assert.Equal("""["/host/resoloop"]""", received.Env[PluginRuntimeEnvironment.HostArgvVariable]);
}

// S: a running command keeps the plugin lease (no concurrent remove) and cancellation never reports success.
[Fact]
public async Task CommandsHoldTheLeaseAndCancellationNeverSucceeds()
{
    var project = CreateProject();
    var plugin = InstallPlugin(project, "probe-plugin",
        """[{"name":"probe-hang","description":"hang","program":"dotnet","args":["${pluginRoot}/probe/CommandProbe.dll","spawn","hang"]}]""", withProbe: true);
    using var cancel = new CancellationTokenSource();
    var context = new PluginDispatchContext("0.2.0", project, CopyEnvironment(), ["/host/resoloop"]);
    var run = PluginCommandDispatch.RunAsync(PluginCommandDispatch.Parse(["probe-hang"])!, context, cancel.Token);
    var pids = await WaitForPids(plugin, TimeSpan.FromSeconds(60));
    var installer = new PluginInstaller(new PluginRegistry(project, "0.2.0", BuiltinCommandCatalog.Reservations));
    Assert.Equal("PLUGIN_PROJECT_BUSY", Assert.Throws<RLoopException>(() => installer.Remove("probe-plugin", true)).Code);
    cancel.Cancel();
    var error = await Assert.ThrowsAsync<RLoopException>(() => run);
    Assert.Equal("PLUGIN_COMMAND_CANCELLED", error.Code);
    Assert.False(IsRunning(pids.Child)); Assert.False(IsRunning(pids.Grandchild));
    installer.Remove("probe-plugin", true);
    Assert.False(Directory.Exists(plugin.InstallDirectory));
}
```

- [ ] **Step 2: 実行して失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~PluginCommandTests"`
Expected: コンパイルエラー（`PluginDispatchContext`・`RunAsync` が無い）

- [ ] **Step 3: `PluginDispatchContext` と `RunAsync` を実装する**

`--project` が無くプロジェクトが無い `PLUGIN_PROJECT_NOT_FOUND` は `UNKNOWN_COMMAND`（suggestion: `Run resoloop help to list commands, or pass --project DIR for a plugin command.`）。期限は `command.TimeoutSeconds ?? ConfigResolver.Resolve(registry.ProjectRoot, 空, key => context.Environment.GetValueOrDefault(key)).Config.CommandTimeoutSeconds`。lease は `RunAsync` の戻りまで `using` で持つ。

- [ ] **Step 4: テストが通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS（6 件）

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Cli/PluginCommandDispatch.cs tests/RLoop.Tests/PluginCommandTests.cs
git commit -m "feat: resolve and run plugin commands under the plugin lease (create-reso-world#98)"
```

### Task 4: doctor のツール確認

**テスト:** 要（S: required の不足・失敗を pass にする）。1 件。

**Files:**
- Create: `src/RLoop.Core/Plugins/PluginToolProbe.cs`
- Create: `src/RLoop.Cli/PluginDoctorChecks.cs`
- Create: `tests/RLoop.Tests/PluginToolProbeTests.cs`

**Interfaces:**
- Consumes: Task 2 の `PluginExecutable.Find`・`PluginProcess.Start(captureOutput: true)`・`StopAsync`、Task 1 の `BuiltinCommandCatalog.Reservations`
- Produces:
  - `public sealed record PluginToolProbeResult(string Plugin, PluginTool Tool, string Outcome, string? ExecutablePath, int? ExitCode, string? Version);`（`Outcome` は `available`・`missing`・`failed`・`timed-out`）
  - `public static Task<PluginToolProbeResult> PluginToolProbe.ProbeAsync(string plugin, PluginTool tool, string workingDirectory, IReadOnlyDictionary<string, string?> environment, TimeSpan timeout, CancellationToken cancellationToken)`
  - `public static Task<IReadOnlyList<DoctorCheck>> PluginDoctorChecks.RunAsync(string? explicitProject, string startDirectory, string resoloopVersion, IReadOnlyDictionary<string, string?> environment, CancellationToken cancellationToken)`（Spec 3.6。名前は `plugins`・`plugin:<名前>`・`plugin:<プラグイン>:<ツール>`、期限 30 秒）

- [ ] **Step 1: 失敗するテストを書く**

`PluginToolProbeTests` は自分の一時ディレクトリと `CreateProject`、`InstallPlugin(string project, string name, string toolsJson)`（manifest の `tools` に書く。probe は要らない）、`CopyEnvironment()` を持つ。

```csharp
// S: a missing or failing required tool must never be reported as passing (doctor readiness depends on it).
[Fact]
public async Task RequiredToolProblemsAreNeverPassing()
{
    var project = CreateProject();
    InstallPlugin(project, "tools-plugin", """
        [{"name":"present","executable":"dotnet","versionArgs":["--version"]},
         {"name":"absent","executable":"resoloop-missing-tool-98"},
         {"name":"broken","executable":"dotnet","versionArgs":["--resoloop-invalid-option-98"]},
         {"name":"optional","executable":"resoloop-missing-tool-98","required":false}]
        """);
    var checks = await PluginDoctorChecks.RunAsync(project, _root, "0.2.0", CopyEnvironment(), CancellationToken.None);
    var byName = checks.ToDictionary(check => check.Name);
    Assert.Equal(("pass", true), (byName["plugin:tools-plugin:present"].Status, byName["plugin:tools-plugin:present"].Required));
    Assert.Equal(("fail", true), (byName["plugin:tools-plugin:absent"].Status, byName["plugin:tools-plugin:absent"].Required));
    Assert.Equal(("fail", true), (byName["plugin:tools-plugin:broken"].Status, byName["plugin:tools-plugin:broken"].Required));
    Assert.Equal(("warning", false), (byName["plugin:tools-plugin:optional"].Status, byName["plugin:tools-plugin:optional"].Required));
}
```

- [ ] **Step 2: 実行して失敗を確かめる**

Run: `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --nologo --filter "FullyQualifiedName~PluginToolProbeTests"`
Expected: コンパイルエラー（`PluginDoctorChecks` が無い）

- [ ] **Step 3: `PluginToolProbe` と `PluginDoctorChecks` を実装する**

`PluginDoctorChecks` は `registry.List()` を使い（lease は持たない）、問題のある status は `plugin:<名前>` の fail。stdout・stderr はそれぞれ 64 KiB を超えたら読み捨てて止める（超過は `failed`）。

- [ ] **Step 4: テストが通ることを確かめる**

Run: Step 2 と同じ。Expected: PASS（1 件）

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Core/Plugins/PluginToolProbe.cs src/RLoop.Cli/PluginDoctorChecks.cs tests/RLoop.Tests/PluginToolProbeTests.cs
git commit -m "feat: check plugin tools for doctor with a deadline (create-reso-world#98)"
```

### Task 5: 統合の確認（統合担当: controller）

**テスト:** 新しいテストは足さない（共有条件は Task 1〜4 のテストと一時の確認で見る）。

共有条件（統合担当が条件単位で確かめる）:
- 同じ入力の解釈: `Parse` が残した `Arguments` を runner が置き換えずに渡す（Task 3 のテスト）
- 予約名の判定の共通化: install・dispatch・doctor が同じ `BuiltinCommandCatalog.Reservations` を使う（`git grep` で `new PluginRegistry(` の呼出元をすべて確かめる）
- 停止の順序: lease の解放は `StopAsync` の後（Task 3 のテスト）

- [ ] **Step 1: 全体の build とテスト**

Run: `dotnet build ResoLoop.slnx --nologo` → 警告・エラー 0、`dotnet test ResoLoop.slnx --no-build --nologo` → 失敗 0（base `dd0b40f` の基準は RLoop.Tests 573・RLoop.IntegrationTests 22 がすべて成功。完了時は RLoop.Tests 580）

- [ ] **Step 2: 一時の確認（コミットしない。`/workspaces/reso-world/tmp/agents/issue-98.*/verify/` に置く）**

`PluginCommandDispatch` を呼ぶ一時の console（`git-probe` と同じ形で RLoop.Core・resoloop.dll を参照）で、次を実行して結果を記録する: プロジェクトの外の未知名 → `UNKNOWN_COMMAND`、`--project=` → `INVALID_ARGUMENT`、`commandTimeoutSeconds: 2` のプロジェクトで timeout の無いコマンドが 2 秒で `PLUGIN_COMMAND_TIMEOUT`、子の環境の `PYTHONPYCACHEPREFIX`・`UV_PROJECT_ENVIRONMENT` が data の下、プラグインの無いプロジェクトで `PluginDoctorChecks.RunAsync` が空。

- [ ] **Step 3: ブランチ全体のレビュー**

新しいレビュアー（サブエージェント）に、Spec・Plan の受け入れ基準と `git diff dd0b40f...HEAD` を渡す。指摘の採否は controller が ledger に記録する。

- [ ] **Step 4: Spec・Plan の完了記録を書き、文書をコミットする**

## 実行方式

`implement_task.py check` の `self` が true（雛形の既定）。Task は前の Task の internal なインターフェース（閉じ込め・helper）に順に依存し、F の閉じ込めの詳細を controller が持っているので、子に渡すと文脈が欠ける。**superpowers:executing-plans**（このセッションが実装）で進め、最後に新しいレビュアーがブランチ全体をレビューする（Task 5 Step 3）。作業領域・ledger は `/workspaces/reso-world/tmp/agents/issue-98.0e5r1jqr/sdd/2026-10-30-create-reso-world-issue98-plugin-commands/`。

## 実行予算

- Issue 全体の能動時間: 240 分（根拠: #99 は 47 分だが、#98 は native の起動を Linux・Windows で持ち、F の #297 は Windows CI の修正で長引いた）。ledger は `/workspaces/reso-world/tmp/agents/issue-98.0e5r1jqr/budget.jsonl`
- phase の目安: 準備・Spec・Plan 50 分、Task 1 15 分、Task 2 70 分、Task 3 25 分、Task 4 25 分、Task 5 と PR 35 分、Windows CI の確認と修正 20 分
- worker: 実装の子は使わない。最後のレビュアーは 30 分で打ち切る（完了の通知を待つ）。`dotnet test` 全体は 15 分で打ち切る
- 再試行: 同じ失敗（同じ signature）は 1 回まで。Windows CI の失敗の修正は、別の原因ごとに 1 回まで
- checkpoint: 各 Task の終わり、予算の 50%（120 分）・100%、テストや CI が失敗した直後
- 縮小・切り出し・方法変更の候補: (1) Windows CI で native の起動が直らないとき、Windows だけ `PLUGIN_COMMAND_START_FAILED` にする案は D-4 の Windows 対応を落とすので採らず、停止して報告する (2) doctor（Task 4）は独立しているので、予算が足りなければ Task 1〜3 で PR を作り、Task 4 を持ち越し候補にする (3) probe のビルドが遅すぎる（1 回 120 秒超）ときは、クラスごとの 1 回のビルドを全テストで共有する collection fixture にする

## Contingency（代替策）

- `posix_spawn_file_actions_addopen` が使えない・失敗する: 親で `/dev/null` を `O_RDONLY|O_CLOEXEC` で開き、`adddup2(fd, 0)` に替える（意味は同じ）
- `Console.IsInputRedirected` が端末を正しく判定しない: libc の `isatty(0)` に替える
- Windows で標準出力の handle の複製・handle list で起動が失敗する: 無効な handle は `NUL` に替え、それでも失敗する原因は CI のログで調べる（systematic-debugging）
- 同じプロセスの中で lease と remove が衝突しない: F の `PluginRegistryTests` の BUSY の確認と同じなので起きない想定。起きたら remove を別プロセス（probe）で行う
- 停止の確認の 5 秒が CI で足りない: 実際の時間を記録し、根拠を Plan に書いて 10 秒にする（意味を保つ最小修正として ledger に記録）
- 最初の RED で F の API の前提が違うと分かった: 意味を保つ最小の修正で続け、ledger に記録する。所有範囲の外の変更が要るなら止まる

## 完了

（実装の後に記録する）
