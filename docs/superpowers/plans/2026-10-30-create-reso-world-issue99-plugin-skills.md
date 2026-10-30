# Issue #99 プラグインのスキル配布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 照合済みプラグインが宣言するスキルを、利用者のファイルを守りながら `init`・`skills sync` の Core API で `.agents/skills/` へ配り、別記録 `.agents/skills/.resoloop-plugins.json` に残す。

**Architecture:** `RLoop.Core.Plugins.PluginSkillManager` が、対象ディレクトリそのものを明示のプロジェクトとして `PluginRegistry.OpenVerified()` の lease を開き、配布先ごとの状態を計画し（書き込みなし）、適用時にファイル→記録の順に書く。`BundledSkillManager.Sync` と `ProjectInitializer.Initialize` に版と予約名を受け取るオーバーロードを足し、同梱と全プラグインの競合をまとめて確かめてから書く。既存の引数の API は変えない。

**Tech Stack:** C# / .NET（`global.json` の 10.0.201 系）、System.Text.Json、xUnit。

**Spec:** `docs/superpowers/specs/2026-10-30-create-reso-world-issue99-plugin-skills-design.md`（`usaturn/create-reso-world`）

- 状態: **draft**（issue-to-pr の実行許可。内容の承認なし）
- `CODE_ROOT`: `/workspaces/reso-world/external/resoloop/.worktrees/create-reso-world-issue-99-plugin-skills`（`feat/create-reso-world-issue-99-plugin-skills`、base `feat/plugin-v2` `dd0b40fb216b0c9fbd82da44903195a885104015`）
- `DOC_ROOT`: `/workspaces/reso-world/.worktrees/create-reso-world-issue-99-plugin-skills`（`docs/create-reso-world-issue-99-plugin-skills`、base main `acd288c3e81a6c108136e37815e718a0fe088195`）
- セッション: `/workspaces/reso-world/tmp/agents/issue-99.5tiljy56`（予算の ledger `budget.jsonl`、作業領域 `sdd/2026-10-30-create-reso-world-issue99-plugin-skills/`）

## Global Constraints

- 変えてよいのは `src/RLoop.Core/Plugins/PluginSkillManager.cs`（新設）、`src/RLoop.Core/BundledSkillManager.cs`、`src/RLoop.Core/ProjectInitializer.cs`、`tests/RLoop.Tests/PluginSkillSyncTests.cs`（新設）、`tests/fixtures/plugins/skills/` だけ。`Program.cs`・`CommandLine.cs`・F の `Plugins/*.cs`・#98 の所有ファイル・`.claude/` は変えない
- 既存の `BundledSkillManager.Sync(string, bool)` と `ProjectInitializer.Initialize(string)` の挙動・生成物・例外・結果は変えない。既存のテストは変更しない
- 記録のパス `.agents/skills/.resoloop-plugins.json`、`schemaVersion` 1、項目 `{ "plugin", "sha256" }`、ハッシュは raw bytes の小文字 16 進 SHA-256、最大 8 MiB
- 状態の文字列: `current`・`missing`・`record-update-required`・`update-available`・`untracked-conflict`・`owner-conflict`・`modified-conflict`・`unsafe-path-conflict`
- エラーコード: `SKILL_SYNC_CONFLICT`・`INIT_FILE_EXISTS`（既存）、`PLUGIN_SKILL_RECORD_INVALID`（新設、`ValidationFailed`）、`PLUGIN_SKILL_WRITE_FAILED`（新設、`OperationFailed`）、`PLUGIN_MODIFIED`・`PLUGIN_NAME_CONFLICT`・`PLUGIN_PATH_UNSAFE`（F の `PluginErrors.Create` を呼ぶだけ）
- テストは S の代表例だけ（Spec 6 章の 5 件）。F・L・D のテストは足さない
- 結果・context のパスはプロジェクトのルートからの相対（`.agents/skills/…`）。記録のキーだけ `.agents/skills/` からの相対
- プラグインのファイルと記録は、同じディレクトリの一時ファイルに書いて rename で置き換える（ハードリンクを共有する外部のファイルを変えない）

## 受け入れ基準

Spec 5 章の本文をそのまま実装担当・レビュー担当に渡す。

- **動作環境**: Linux の本 Dev Container、`global.json` の .NET（10.0.201 系）、xUnit。一時ディレクトリと一時プロジェクトだけで確かめる。Windows も利用対象（公開 CI は windows-latest）だが、Windows で実行していない状態を確認済みと報告しない。Resonite・Blender・認証情報・グローバル導入は不要。
- **実入力**: 空白と日本語を含むプロジェクト `作業 ワールド`、日本語のファイル名を含むスキル（`references/手順.md`）、`SKILL.md` と参照文書を持つ 2 版のプラグイン、利用者が編集した配布済みファイル、記録の無い同名のスキル、外部ディレクトリへのリンクになった `.agents/skills/<name>`、remove 後に残ったスキル、読み取り専用で書けない配布先。
- **防御範囲**: 利用者の編集・記録の無い既存ファイル・リンク先を上書きしない。全競合を確かめる前に何も書かない（同梱を含む）。書けなかったファイルを配布済みと記録しない。remove 後も配ったファイルと記録を残し、再導入でも編集を守る。プラグイン無しのプロジェクトでは、新しい API でも記録を作らず、既存と同じ生成物にする。各拒否には正しく通る例を残す（編集の無いファイルは更新される、編集を戻せば更新できる、記録の無い別名のスキルには触れない）。
- **対象外の反例**: 悪意ある同一ユーザの差し替え、署名、CLI の結線（I）、Windows 実機。改行だけの違いを同じとみなすこと（制限として残す）。

## Review Focus

- `.agents` か `.agents/skills` そのものがリンク（利用者が共有ディレクトリへ向けた場合）: 書き込みも読み取りもせず `unsafe-path-conflict` で止まる（Task 1 の計画で、プロジェクトのルートから配布先までの全階層を確かめる）
- manifest の `skills[].path` と実ファイルの大小文字が違う（Windows で通った manifest）: `files` を大小文字を無視した接頭辞で選び、配るファイルが 0 件にならない（Task 1 の Step 3 の規則）
- 記録ファイルが壊れている・リンク・ディレクトリ: 空として扱わず、何も書かずに止まる（Task 1 の Step 3。不正な記録が例外になるだけの経路は L なのでテストしない）
- 照合に失敗したプラグイン（`PLUGIN_MODIFIED`）がある: 同梱を含めて何も書かない（F の `OpenVerified` の例外を計画の前にそのまま返す）
- check の後に別プロセスが install/remove する: lease を書き込みの終わりまで保持し、BUSY にする

---

### Task 1: プラグインのスキル配布と skills sync の統合

**Files:**
- Create: `src/RLoop.Core/Plugins/PluginSkillManager.cs`
- Modify: `src/RLoop.Core/BundledSkillManager.cs`
- Test: `tests/RLoop.Tests/PluginSkillSyncTests.cs`

**テストの要否:** 要る。利用者の編集・記録の無いファイル・リンク先の上書き、全競合の確認前の書き込み、書けなかったファイルの記録、remove 後の記録の消失は、壊れてもエラーにならない S。

**Interfaces:**
- Consumes（F、変えない）: `PluginRegistry(string projectRoot, string resoloopVersion, PluginNameReservations reservations)`、`PluginRegistry.ProjectRoot`、`PluginRegistry.OpenVerified() -> PluginReadLease`、`PluginReadLease.Plugins: IReadOnlyList<InstalledPlugin>`、`InstalledPlugin(Name, InstallDirectory, PackageDirectory, DataDirectory, Manifest, Record)`、`PluginManifest.Skills: IReadOnlyList<PluginSkill(Name, Path)>`、`PluginInstallRecord.Files: IReadOnlyDictionary<string,string>`（序数順）、`PluginNameReservations(commands, skills, recipes)` と `Commands`/`Skills`/`Recipes`、`PluginPathPolicy.EnsureNoLinks(path, code, allowMissing)`・`ValidateRelativePath(relative, code)`・`Combine(root, relative, code)`、`PluginJson.Read(path, maximumBytes, code)`・`PluginJson.FindDuplicateProperties(element, path, errors)`、`PluginNames.IsValid(name)`、`PluginErrors.Create(code, message, ...)`
- Produces（Spec 3 章の公開 API）:
  - `public sealed record PluginSkillFileStatus(string Plugin, string Skill, string Path, string Status, string PackageHash, string? InstalledHash, string? RecordedHash, string? RecordedPlugin)`（`Path` は `.agents/skills/` からの相対、`/` 区切り）
  - `public sealed record PluginSkillRetainedFile(string Plugin, string Path, string RecordedHash)`
  - `public sealed record PluginSkillSyncResult(string Mode, bool Synchronized, IReadOnlyList<string> Updated, IReadOnlyList<PluginSkillFileStatus> Files, IReadOnlyList<PluginSkillRetainedFile> Retained)`
  - `public static class PluginSkillManager { public const string RecordRelativePath = ".agents/skills/.resoloop-plugins.json"; internal static PluginSkillPlan? Open(string targetDirectory, string resoloopVersion, PluginNameReservations reservations); }`
  - `internal sealed class PluginSkillPlan : IDisposable { IReadOnlyList<PluginSkillFileStatus> Conflicts(bool init); bool Synchronized { get; } IReadOnlyList<string> Apply(bool init); PluginSkillSyncResult? Result(string mode, IReadOnlyList<string> updated, bool applied); }`（Task 2 が `Conflicts(true)`・`Apply(true)`・`Result("init", …, true)` を使う）
  - `SkillSyncResult` の最後に `PluginSkillSyncResult? Plugins = null`
  - `public static SkillSyncResult BundledSkillManager.Sync(string targetDirectory, bool update, string resoloopVersion, PluginNameReservations reservations)`

- [ ] **Step 1: 失敗するテストを書く**

`tests/RLoop.Tests/PluginSkillSyncTests.cs`（`IDisposable`）。補助:
- プロジェクト `_project = Path.Combine(Path.GetTempPath(), "resoloop-plugin-skill-" + Guid.NewGuid().ToString("N"), "作業 ワールド")`、パッケージは `Directory.CreateTempSubdirectory("resoloop-plugin-skill-src-")`（Git の外）の下。`Dispose` は両方を `PluginPathPolicy.DeleteTree(..., "PLUGIN_REMOVE_REFUSED")` で消す（リンクを辿らない）
- `Install(string plugin, string? skill, IReadOnlyDictionary<string,string> files, string version = "1.0.0")`: 新しいディレクトリに `resoloop-plugin.json`（`schemaVersion` 1、`name`、`version`、`resoloop.minVersion` `"0.2.0"`、`skill` があれば `skills: [{ name: skill, path: "skills/" + skill }]`）と `skills/<skill>/<相対>` を UTF-8 で書き、`new PluginInstaller(Registry()).Install(dir)`
- `Registry()` = `new PluginRegistry(_project, "0.2.0", new PluginNameReservations([], [], []))`、`Sync(bool update)` = `BundledSkillManager.Sync(_project, update, "0.2.0", 同じ予約名)`、`Skill(string relative)` = `.agents/skills/<relative>` の絶対パス、`RecordPath` = `.agents/skills/.resoloop-plugins.json`

テスト（各テストに守る損害を 1 行のコメントで書く）:

```csharp
// S: 利用者の編集を上書きしない・全競合の確認前に同梱も含めて書かない・remove 後もファイルと記録を残す
[Fact] public void UserEditsSurviveRemoveAndReinstall()
//  ProjectInitializer.Initialize(_project); Install("alpha-plugin","alpha-guide",{SKILL.md:"v1 skill", references/手順.md:"v1 手順"})
//  check = Sync(false): Assert.False(check.Synchronized); 全 Plugins!.Files が "missing"; Assert.False(File.Exists(RecordPath))
//  Sync(true): 2 ファイルが v1 のバイト列と一致; Assert.True(Sync(false).Synchronized); recordV1 = File.ReadAllBytes(RecordPath)
//  new PluginInstaller(Registry()).Remove("alpha-plugin", true): 2 ファイルと RecordPath のバイト列が不変
//  retained = Sync(false): Assert.True(retained.Synchronized); Assert.Equal(2, retained.Plugins!.Retained.Count)
//  File.WriteAllText(Skill("alpha-guide/SKILL.md"), "user edit"); File.Delete(Skill("resonite-flux/SKILL.md"))
//  Install(... version "2.0.0", {SKILL.md:"v2 skill", references/手順.md:"v2 手順"})
//  Assert.Equal("SKILL_SYNC_CONFLICT", Assert.Throws<RLoopException>(() => Sync(true)).Code)
//  "user edit"・"v1 手順" のまま、resonite-flux/SKILL.md は無いまま、RecordPath == recordV1
//  File.Delete(Skill("alpha-guide/SKILL.md")); Sync(true): 2 ファイルが v2、resonite-flux/SKILL.md が戻る; Assert.True(Sync(false).Synchronized)

// S: 所有の記録が無い同名ファイルと、リンク先の外部ディレクトリを書き換えない
[Fact] public void UnownedFilesAndLinkedDestinationsAreNeverWritten()
//  Initialize; Skill("beta-guide/SKILL.md") に "user's own skill"; outside = 一時ディレクトリ; Directory.CreateSymbolicLink(Skill("gamma-guide"), outside)
//  Install("beta-plugin","beta-guide",{SKILL.md:"beta"}); Install("gamma-plugin","gamma-guide",{SKILL.md:"gamma"})
//  error = Assert.Throws<RLoopException>(() => Sync(true)); Code == "SKILL_SYNC_CONFLICT"
//  (IReadOnlyList<PluginSkillFileStatus>)error.Context["pluginConflicts"] の Path→Status が
//    {"beta-guide/SKILL.md":"untracked-conflict","gamma-guide/SKILL.md":"unsafe-path-conflict"}
//  "user's own skill" のまま; Assert.Empty(Directory.EnumerateFileSystemEntries(outside))
//  File.Delete(beta の SKILL.md); Directory.Delete(Skill("gamma-guide"))（リンクだけを消す）; Sync(true) 成功、両方が配られ、outside は空のまま

// S: 書けなかったファイルを配布済みと記録しない（失敗を成功として返さない）
[Fact] public void FailedWritesAreNotRecordedAsDistributed()
//  Linux の root は読み取り専用を無視するので `if (!OperatingSystem.IsWindows() && Environment.UserName == "root") return;`
//  Initialize; Install v1 {SKILL.md, references/手順.md}; Sync(true); recordV1; Remove; Install v2（両方変更）
//  File.SetAttributes(Skill("alpha-guide/references/手順.md"), FileAttributes.ReadOnly)
//  Assert.Equal("PLUGIN_SKILL_WRITE_FAILED", Assert.Throws<RLoopException>(() => Sync(true)).Code)
//  RecordPath == recordV1、手順.md は "v1 手順"
//  File.SetAttributes(..., FileAttributes.Normal); Sync(true) で両方 v2; Assert.True(Sync(false).Synchronized)
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run（`CODE_ROOT`）: `dotnet build ResoLoop.slnx --nologo`
Expected: `BundledSkillManager.Sync` の 4 引数のオーバーロード・`PluginSkillSyncResult`・`SkillSyncResult.Plugins` が無いコンパイルエラー

- [ ] **Step 3: `PluginSkillManager.cs` を実装する**

- `Open`: `root = Path.GetFullPath(targetDirectory)`。`root/.resoloop.json` が `File.Exists` で、`root/.resoloop/plugins` が `Directory.Exists` のときだけ、`new PluginRegistry(root, resoloopVersion, new PluginNameReservations(reservations.Commands, reservations.Skills.Concat(BundledSkillManager.Names), reservations.Recipes))` を作り `OpenVerified()`。それ以外は `null`（記録も読まない）。計画の構築で例外が出たら lease を解放して再送出
- 計画のルートは `registry.ProjectRoot`（解決済み）。記録は `ReadRecord`（下）で、大小文字を無視したキーの辞書と「ファイルがあったか」を持つ
- 対象: lease の各プラグイン（名前の序数順）→ manifest の `Skills` の順 → `Record.Files`（序数順）のうち `skill.Path + "/"` で始まるもの（`StringComparison.OrdinalIgnoreCase`）。配布先 `skill.Name + "/" + 残り`。スキル名が `resonite-` で始まるか `BundledSkillManager.Names` に一致（大小文字を無視）したら `PluginErrors.Create("PLUGIN_NAME_CONFLICT", …)` で止まる
- 状態は Spec 4 章の 1〜7 の順。安全でない経路の判定: `full = Path.Combine(root, ".agents", "skills", …)` に `PluginPathPolicy.EnsureNoLinks(full, "PLUGIN_PATH_UNSAFE", allowMissing: true)` が例外、`Directory.Exists(full)`、`root` より下の途中の階層が `File.Exists` のどれか。このときファイルを読まない。`I` は `FileStream` を `SHA256.HashData(stream)` で小文字 16 進に
- 宣言から外れた記録の項目を `Retained`（序数順）に
- `Conflicts(init)`: 状態が `-conflict` で終わるもの。`init` なら `update-available` も含める
- `Synchronized`: 全 `Files` が `current`
- `Apply(init)`: `missing`（と `init` でなければ `update-available`）を順に書く。パッケージのファイルは `PluginPathPolicy.Combine(PackageDirectory, packageRelative, "PLUGIN_MODIFIED")` から `File.ReadAllBytes` し、SHA-256 が `PackageHash` と違えば `PLUGIN_MODIFIED`。`Directory.CreateDirectory(親)`→`File.WriteAllBytes`。`IOException`・`UnauthorizedAccessException` は `new RLoopException("PLUGIN_SKILL_WRITE_FAILED", …, ExitCodes.OperationFailed, context { path, updated }, innerException)` に包む。書けたものと `record-update-required` を記録の写しに反映し（大小文字を無視して同じキーを置き換え）、最後に記録を書く。返り値は書いた `.agents/skills/…` のパス（記録を書いたら `RecordRelativePath` も最後に）
- 記録の書き込み: 項目が 1 つ以上で、直列化したバイト列が既存と違うときだけ。`JsonSerializerOptions { PropertyNamingPolicy = CamelCase, WriteIndented = true, NewLine = "\n" }`、キーは `SortedDictionary<string, …>(StringComparer.Ordinal)`、末尾に `"\n"`、UTF-8（BOM なし）。書く前に `EnsureNoLinks(recordPath, …, allowMissing: true)`
- `ReadRecord`: `EnsureNoLinks(path, "PLUGIN_PATH_UNSAFE", allowMissing: true)`、無ければ空。ディレクトリなら不正。`PluginJson.Read(path, 8 * 1024 * 1024, code)` と `FindDuplicateProperties`。ルートは `schemaVersion`（整数 1）と `files`（オブジェクト）だけ、各値は `plugin`（`PluginNames.IsValid`）と `sha256`（`^[0-9a-f]{64}$`）だけ、キーは `ValidateRelativePath`・2 要素以上・先頭が `PluginNames.IsValid`・大小文字を無視して重複しない。違反・`PluginJson` の例外は `new RLoopException("PLUGIN_SKILL_RECORD_INVALID", …, ExitCodes.ValidationFailed, innerException)`
- `Result(mode, updated, applied)`: `Files` が空で記録ファイルも無ければ `null`。`applied` なら各 `Files` を `current`（`InstalledHash = RecordedHash = PackageHash`、`RecordedPlugin = Plugin`）にした写しを返す

- [ ] **Step 4: `BundledSkillManager.cs` を統合する**

- `SkillSyncResult` の最後に `PluginSkillSyncResult? Plugins = null` を足す
- 既存の `Sync(string, bool)` の本体を `private static SkillSyncResult Sync(string targetDirectory, bool update, PluginSkillPlan? plugins)` に移し、既存の公開関数はそれを `null` で呼ぶ。新設の 4 引数は `using var plugins = PluginSkillManager.Open(...)` で開いて同じ private を呼ぶ
- 競合: 同梱の `conflicts` と `plugins?.Conflicts(false)` を合わせて判定。プラグインの項目が無ければ既存と同じメッセージ・context・suggestion。あれば message を `"Skill sync stopped because one or more bundled or plugin skills are modified, unowned or unsafe."` にし、context に `pluginConflicts` を足す
- check: `Synchronized` = 既存の判定 && `(plugins?.Synchronized ?? true)`、`Plugins = plugins?.Result("check", [], false)`
- update: 既存の同梱の書き込みの後に `plugins?.Apply(false)` を呼び、返ったパスを `Updated` に足す。`Plugins = plugins?.Result("update", pluginUpdated, true)`

- [ ] **Step 5: テストが通ることを確かめる**

Run: `dotnet build ResoLoop.slnx --nologo && dotnet test ResoLoop.slnx --nologo --no-build --filter "FullyQualifiedName~PluginSkillSyncTests|FullyQualifiedName~ProjectInitializerTests|FullyQualifiedName~AgentEfficiencyTests"`
Expected: 警告 0・エラー 0、選んだテストがすべて成功

- [ ] **Step 6: Commit**

```bash
git add src/RLoop.Core/Plugins/PluginSkillManager.cs src/RLoop.Core/BundledSkillManager.cs tests/RLoop.Tests/PluginSkillSyncTests.cs
git commit -m "feat: distribute verified plugin skills through skills sync (#99)"
```

#### Task 1 の追加: builder check の反映

Spec の builder check（Task 1・2 の実装の後に返った）の 3 点を同じ TDD で反映する。

- [ ] **Step 7: テストを変える（RED）**
  - `UnownedFilesAndLinkedDestinationsAreNeverWritten` の期待するパスを `.agents/skills/beta-guide/SKILL.md`・`.agents/skills/gamma-guide/SKILL.md` にする
  - 新設 `UpdatesNeverWriteThroughHardlinks`（S: 更新でハードリンクを共有する外部のファイルの中身を変えない）: v1 を配った後、`alpha-guide/SKILL.md` を外部へ移し、外部のファイルへのハードリンクを元の名前に作る（`PluginManifestTests` と同じ `link`/`CreateHardLinkW`）。remove→v2 を導入して `Sync(true)`。配布先は `"v2 skill"`、外部は `"v1 skill"` のまま
  - `FailedWritesAreNotRecordedAsDistributed` の失敗の注入を、Windows は読み取り専用のファイル、Unix は読み取り専用のディレクトリ（`UserRead | UserExecute`）にし、`finally` で戻す。ディレクトリに `手順.md` 以外が残らないことも確かめる
  - Expected: パスの期待値とハードリンクの 2 件が失敗する
- [ ] **Step 8: 実装する**
  - `PluginSkillFileStatus.Path`・`PluginSkillRetainedFile.Path`・`Updated`・context のパスに `.agents/skills/` を付ける。記録のキーは `Planned.Target`（`.agents/skills/` からの相対）に分ける。`ProjectInitializer` は `conflict.Path` をそのまま `conflicts` に足す
  - ファイルと記録の書き込みを `Replace(path, bytes, modeSource)` にする: 同じディレクトリに `.resoloop-<GUID>.tmp` を `FileMode.CreateNew` で作って書き、Unix では `File.GetUnixFileMode(modeSource)` の rwx ビットを写し、`File.Move(temporary, path, overwrite: true)`。例外では一時ファイルを消して再送出
- [ ] **Step 9: テストが通ることを確かめて commit**
  - Run: Step 5 と同じ。Expected: 警告 0・エラー 0、すべて成功
  - `git commit -m "fix: replace plugin skill files without writing through hardlinks (#99)"`

### Task 2: init でのプラグインのスキル配布

**Files:**
- Modify: `src/RLoop.Core/ProjectInitializer.cs`
- Test: `tests/RLoop.Tests/PluginSkillSyncTests.cs`

**テストの要否:** 要る。init の状態の扱い（どれを conflict にするか）は sync と別の分岐で、壊れると利用者の編集を init が黙って上書きする S。プラグイン無しで記録ファイルを作ると、既存の生成物が黙って変わる S。

**Interfaces:**
- Consumes: Task 1 の `PluginSkillManager.Open`、`PluginSkillPlan.Conflicts(true)`・`Apply(true)`・`Result("init", updated, true)`
- Produces: `ProjectInitResult` の最後に `PluginSkillSyncResult? Plugins = null`、`public static ProjectInitResult ProjectInitializer.Initialize(string targetDirectory, string resoloopVersion, PluginNameReservations reservations)`

- [ ] **Step 1: 失敗するテストを書く**

```csharp
// S: init が利用者の編集を上書きしない・スキルの無いプラグインだけのプロジェクトに記録を作らない
[Fact] public void InitDistributesPluginSkillsButNeverOverwritesEdits()
//  ProjectInitializer.Initialize(_project); Install("tool-plugin", null, {})（スキルなし）
//  synced = Sync(true): Assert.Null(synced.Plugins); Assert.False(File.Exists(RecordPath))
//  Install("alpha-plugin","alpha-guide",{SKILL.md:"v1 skill", references/手順.md:"v1 手順"})
//  init = ProjectInitializer.Initialize(_project, "0.2.0", 予約名): 2 ファイルが v1、Assert.Contains(".agents/skills/alpha-guide/SKILL.md", init.Plugins!.Updated)、Assert.Empty(init.Created)
//  File.WriteAllText(Skill("alpha-guide/SKILL.md"), "user edit")
//  Assert.Equal("INIT_FILE_EXISTS", Assert.Throws<RLoopException>(() => ProjectInitializer.Initialize(_project, "0.2.0", 予約名)).Code)
//  "user edit" のまま
```

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `dotnet build ResoLoop.slnx --nologo`
Expected: 3 引数の `Initialize` が無いコンパイルエラー

- [ ] **Step 3: `ProjectInitializer.cs` を実装する**

- `ProjectInitResult` の最後に `PluginSkillSyncResult? Plugins = null`
- 既存の本体を `private static ProjectInitResult Initialize(string targetDirectory, PluginSkillPlan? plugins)` に移し、既存の公開関数は `null` で呼ぶ。新設の 3 引数は `using var plugins = PluginSkillManager.Open(...)`
- 競合: 既存の `conflicts` に `plugins?.Conflicts(true)` の各 `".agents/skills/" + Path` を足す。プラグインの項目があれば context に `pluginConflicts`。message・suggestion は既存のまま
- 書き込み: 既存の基本ファイルの後に `plugins?.Apply(true)`。`Plugins = plugins?.Result("init", pluginUpdated, true)`。`Created`・`Unchanged` にプラグインの分を混ぜない

- [ ] **Step 4: テストが通ることを確かめる**

Run: `dotnet build ResoLoop.slnx --nologo && dotnet test ResoLoop.slnx --nologo --no-build --filter "FullyQualifiedName~PluginSkillSyncTests|FullyQualifiedName~ProjectInitializerTests"`
Expected: 警告 0・エラー 0、すべて成功

- [ ] **Step 5: Commit**

```bash
git add src/RLoop.Core/ProjectInitializer.cs tests/RLoop.Tests/PluginSkillSyncTests.cs
git commit -m "feat: distribute plugin skills during init without overwriting edits (#99)"
```

### Task 3: 統合確認・全体レビュー・公開

**Files:** なし（検証と記録）

**テストの要否:** 新しいテストは書かない。全体の build/test と差分の確認で代える。

- [ ] **Step 1: 全体の検証**

Run（`CODE_ROOT`）: `dotnet build ResoLoop.slnx --nologo` と `dotnet test ResoLoop.slnx --nologo --no-build`
Expected: 警告 0・エラー 0、unit 573＋新設 5 件・offline integration 22 件が成功、失敗/skip 0。ログはセッションの `verify-*.log`

- [ ] **Step 2: 条件単位の照合**

Spec 5 章の各防御範囲を、テスト名・コードの位置・実行結果に対応づけて ledger に書く。`git diff dd0b40f...HEAD --stat` で許可したファイルだけが変わったことを確かめる

- [ ] **Step 3: ブランチ全体のレビュー**

新しいサブエージェントに、Spec 5 章の受け入れ基準の本文・差分・テストの採用基準を渡し、入力→配布→記録→再実行の流れを通して見てもらう。採否を ledger に記録し、採用したものは原文のまま直す

- [ ] **Step 4: 公開**

issue-to-pr の 5 章の順（検証の記録、diff、scan→push、PR 作成、`--merge` のループ）

## 実行予算

- 全体の能動時間: 360 分（Spec・Plan・実装 2 Task・ループの最大 3 サイクル。#297 は 4 時間超の大きな基盤だったが、本 Issue は 3 ファイルとテスト 1 本）。ledger は 11:25 UTC に開始（初期の確認・予約の約 17 分は含まない）
- phase の目安: Spec・Plan 60 分、Task 1 60 分、Task 2 20 分、Task 3（検証・レビュー・PR）40 分、PR 修正ループ（サイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 30 分））最大 225 分
- worker: build/test は同期実行（全体のテスト約 2 分 30 秒）。期限 15 分、無進捗 10 分で打ち切り。レビューのサブエージェントは 30 分
- 再試行の上限: 同じ失敗は 1 回まで（既定）。安全の失敗は全体停止
- checkpoint: 各 Task の境界、予算の 50%・100%、レビュー・ループのサイクルの直後
- 縮小・切り出し・方法変更の候補: (1) init の統合（Task 2）が既存テストと衝突したら、init は既存のままにして sync だけを配り、init の配布を I へ持ち越す（Spec の決定記録に変更として書く）。(2) 読み取り専用によるテストが Windows CI で不安定なら、失敗の注入方法を変える（同じ守りを保つ）。(3) ループで範囲外の大きな指摘が出たら、持ち越し候補として PR 本文に書く

## contingency（代替策）

- 最初の RED で F の API の前提が違うと分かったら（例: `Record.Files` の順序・大小文字、`OpenVerified` の空の lease）、Spec の意味を保つ最小の修正を ledger に書いて続ける。F の所有ファイルを変える必要が出たら停止して親 #95 の裁定を待つ
- `File.SetAttributes(ReadOnly)` で書き込みが失敗しない環境（root など）では、そのテストは早期 return する。Linux の本 Dev Container（uid 1000）では実行されることを確かめる
- 既存の同梱・init のテストが 1 件でも失敗したら、既存の挙動を変えたものとして直す。既存のテストは書き換えない
- 公開 CI（windows-latest）が失敗したら、ループの `finalize.py` が CI の失敗を致命的な指摘として扱う。Windows 固有の失敗はローカルで再現できないため、ログから原因を特定して直す。直せなければ停止する
