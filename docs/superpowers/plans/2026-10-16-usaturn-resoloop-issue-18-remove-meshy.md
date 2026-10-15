# usaturn/resoloop Issue #18 Meshy の同梱を外す Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR #11（マージ `9cf7178`）で同梱した Meshy の実行基盤（スキル `meshy-resoloop`）を、resoloop の配布物からすべて外す。

**Architecture:** PR #11 のマージを `git revert -m 1 9cf7178` で戻し、Meshy に限らない設定（配布物から `__pycache__`・`.pyc` を外す指定）だけを入れ直す。配置済みのプロジェクトで `skills sync --update` を実行しても、同梱をやめた `meshy-resoloop` のファイルが消えず、中身も変わらないことをテストで確かめる。

**Tech Stack:** .NET 10（C#）、xUnit、GitHub Actions（fork の公開 CI）

**Spec:** なし（範囲・受け入れ条件は Issue https://github.com/usaturn/resoloop/issues/18 の本文で決めてあるため、Issue の指示どおり Plan だけを作る）

- 文書管理リポジトリ: usaturn/create-reso-world（DOC_ROOT `/workspaces/reso-world/.worktrees/resoloop-18-remove-meshy-docs`、ブランチ `docs/resoloop-18-remove-meshy`）
- 対象: usaturn/resoloop#18（親ボード usaturn/create-reso-world#95、子のキー `meshy-unbundle`）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-18-remove-meshy`（ブランチ `chore/issue-18-remove-meshy`、起点は fork の `origin/main` = `84c7932`）
- 検証したコードの HEAD: `84c7932`（2026-10-16 に fetch し、`84c7932` から進んでいないことを確認。PR #11 の後のコミットは #15・#16 の 8 件で、`git diff 8bcef8a 9cf7178 | git apply -R --check` は成功）
- 状態: approved（利用者の着手指示「途中で止めずに推奨案で PR まで作成して」（2026-10-16）による事前の許可。実行方法は利用者の選択が無いため、推奨の Native（このセッションで実装）とする。Task が少なく、同じブランチに順に積み重なるため）
- 導入済みの ResoLoop（検証の後に戻す版）: `0.1.0-preview.17.fork.20261009.g84c7932`
- 予約: create-reso-world の `refs/heads/agent-claims/resoloop-issue-18`（claim のコミット `3880d8f`）
- 関連: PR #11（戻す対象）、PR #10（preproduction の「Meshy 併用」の経路。範囲外）、#14、#17、usaturn/create-reso-world#56・#103・#104

## Global Constraints

- コードの起点は fork の `origin/main`（上流の `upstream/main` ではない。PR #11 は fork にしか無い）
- 上流（orange3134/resoloop）へ PR を出さない
- 範囲外: preproduction の「Meshy 併用」の経路（PR #10 の時点の「非同梱の `meshy-resoloop`」を指す文に戻すだけで、書き換えない）、exporter の Normal Map の UV 名の検査（#14）、各プロジェクトに配置済みの `.agents/skills/meshy-resoloop/`、create-reso-world の Meshy の道具
- 実在のワールドでは `skills sync --update` を実行しない（配置済みのファイルは残すと利用者が決めた）
- 古い worktree `external/resoloop/.worktrees/issue-56-meshy`（ブランチ `feat/meshy-distribution`）は消さない
- dotnet test は CI で Windows でも動く。テストのパスは `Path.GetTempPath()` から作る（`ProjectInitializerTests` の `_root` が既にそうなっている）
- テストの採用基準（create-reso-world の `AGENTS.md`）: 書くのは利用者のデータを守る条件（Task 2）だけ。一覧・文面の照合のテストは作らない

## Review Focus

1. g84c7932 の版で `init` 済み（`meshy-resoloop` のファイルと lock の項目がある）プロジェクトで `skills sync --update` → `meshy-resoloop` のファイルは消えず、中身も更新時刻も変わらない。書き換わるのは lock だけ。Task 2 のテストで確かめる
2. 配布物（nupkg）に `__pycache__` と `.pyc` が入らない → revert の後も `Exclude` が残る。Task 3 で nupkg の中身を一覧して確かめる
3. 空のディレクトリで `resoloop init` → `.agents/skills/meshy-resoloop/` が作られない。Task 3 で、導入した版で確かめる
4. revert が PR #11 の後のコミット（#15 の capture、#16 の hostPathMap）の変更を巻き戻さない → `README-DETAILS.md`・`docs/BLENDER.md`・`resonite-blender`・`resonite-build` の `84c7932` との差分が Meshy の文だけ。Task 3 で確かめる
5. 文書に消したファイルへのリンクが残らない → `git grep -n 'meshy-resoloop/'` が 0 件、`git grep -n -i meshy` は範囲外の 7 ファイルだけ。Task 3 で確かめる

---

### Task 1: PR #11 を戻し、Python のキャッシュを外す指定を入れ直す

**テスト:** 書かない。同梱をやめる変更で、新しく確かめる挙動が無い（守る挙動は Task 2 のテストで確かめる）。代わりに、build・既存のテスト（`CreatesPortableStarterProject` などは `BundledSkillManager.Files` の件数に合わせて数える）・`git diff` で確かめる。

**Files:**
- Revert: PR #11 の 29 ファイル（`skills/codex/meshy-resoloop/`、`tests/meshy/`、`tests/fixtures/meshy/`、`pyproject.toml`、`docs/MESHY-VALIDATION.md` を削除し、`BundledSkillManager.cs`・`RLoop.Core.csproj`・`ProjectInitializerTests.cs`・`.github/workflows/ci.yml`・README 3 本・`docs/BLENDER.md`・3 スキルの文を戻す）
- Modify: `src/RLoop.Cli/RLoop.Cli.csproj`（`skills/codex` の `<None>`）

- [x] **Step 1: PR #11 のマージを戻す**

```bash
cd /workspaces/reso-world/external/resoloop/.worktrees/issue-18-remove-meshy
git revert -m 1 --no-edit 9cf7178
git show --stat HEAD | tail -3
```

Expected: コンフリクトなし。`29 files changed, 11 insertions(+), 5356 deletions(-)`

- [x] **Step 2: `Exclude` を入れ直す**

`src/RLoop.Cli/RLoop.Cli.csproj` の

```xml
    <None Include="../../skills/codex/**/*" Pack="true" PackagePath="source/skills/codex/" />
```

を、PR #11 と同じ次の行にする。

```xml
    <None Include="../../skills/codex/**/*" Exclude="../../skills/codex/**/__pycache__/**/*;../../skills/codex/**/*.pyc" Pack="true" PackagePath="source/skills/codex/" />
```

- [x] **Step 3: build と既存のテスト**

```bash
dotnet build ResoLoop.slnx && dotnet test ResoLoop.slnx --no-build
```

Expected: build の警告 0 件、テストはすべて成功（PR #11 の Meshy のテスト 5 件の分だけ減る）

- [x] **Step 4: コミット**

```bash
git add src/RLoop.Cli/RLoop.Cli.csproj
git commit -m "build: keep excluding Python caches from packaged skills"
```

### Task 2: 同梱をやめたスキルのファイルを sync が残すことのテスト

**テスト:** 書く。利用者のデータを守る条件（Issue の受け入れ条件 3）で、`BundledSkillManager.Sync` を実行して確かめる挙動がある。revert で消える Meshy のテストの代わりになる。

**Files:**
- Modify: `tests/RLoop.Tests/ProjectInitializerTests.cs`（`SkillSyncUpdateRestoresMissingLockedSkill` の後にテストを、`Dispose` の前に補助のメソッドを足す）

**Interfaces:**
- Consumes: `ProjectInitializer.Initialize(string)`、`BundledSkillManager.Sync(string, bool)`、`BundledSkillManager.LockRelativePath`、`SkillSyncResult.Updated`・`Synchronized`

- [x] **Step 1: テストを書く**

`SkillSyncUpdateRestoresMissingLockedSkill` の後に足す。

```csharp
    // Catch sync deleting or rewriting files of a skill that an earlier build deployed
    // but this build no longer bundles (meshy-resoloop): projects still load them.
    [Fact]
    public void SkillSyncKeepsFilesOfSkillsNoLongerBundled()
    {
        ProjectInitializer.Initialize(_root);
        var previouslyBundled = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["meshy-resoloop/SKILL.md"] = "---\nname: meshy-resoloop\ndescription: previously bundled\n---\n",
            ["meshy-resoloop/references/runbook.md"] = "# previously bundled runbook\n",
            ["meshy-resoloop/scripts/meshy.py"] = "print('previously bundled')\n"
        };
        var lockPath = Path.Combine(_root, BundledSkillManager.LockRelativePath);
        var locked = System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(lockPath))!;
        foreach (var (file, content) in previouslyBundled)
        {
            var path = Path.Combine(_root, ".agents", "skills", file);
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            File.WriteAllText(path, content);
            locked["files"]![file] = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(
                System.Text.Encoding.UTF8.GetBytes(content)));
        }
        File.WriteAllText(lockPath, locked.ToJsonString());
        var skillDirectory = Path.Combine(_root, ".agents", "skills", "meshy-resoloop");
        var before = SnapshotFiles(skillDirectory);

        Assert.True(BundledSkillManager.Sync(_root, update: false).Synchronized);
        var updated = BundledSkillManager.Sync(_root, update: true);

        Assert.Equal(BundledSkillManager.LockRelativePath, Assert.Single(updated.Updated));
        Assert.Equal(before, SnapshotFiles(skillDirectory));
        var rewritten = System.Text.Json.Nodes.JsonNode.Parse(File.ReadAllText(lockPath))!;
        Assert.DoesNotContain(rewritten["files"]!.AsObject(),
            pair => pair.Key.StartsWith("meshy-resoloop/", StringComparison.Ordinal));
        Assert.True(BundledSkillManager.Sync(_root, update: false).Synchronized);
    }
```

`Dispose` の前に足す。

```csharp
    private static (string Relative, string Hex, DateTime Modified)[] SnapshotFiles(string directory) =>
        Directory.EnumerateFiles(directory, "*", SearchOption.AllDirectories)
            .Order(StringComparer.Ordinal)
            .Select(path => (Path.GetRelativePath(directory, path).Replace('\\', '/'),
                Convert.ToHexString(File.ReadAllBytes(path)), File.GetLastWriteTimeUtc(path))).ToArray();
```

- [x] **Step 2: revert 後のコードで成功することを確かめる**

```bash
dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~SkillSyncKeepsFilesOfSkillsNoLongerBundled"
```

Expected: PASS（1 件）

- [x] **Step 3: コミット**

```bash
git add tests/RLoop.Tests/ProjectInitializerTests.cs
git commit -m "test: keep files of skills that are no longer bundled on skills sync"
```

- [x] **Step 4: revert 前のコードで失敗することを確かめる（テストが条件を検出できることの確認）**

scratchpad に `84c7932` の一時 worktree を作り、テストのコミットだけを cherry-pick して実行する。Meshy を同梱している版では、lock の hash と一致するファイルを「update-available」として同梱の内容で上書きするため、失敗するはず。

```bash
SP=/tmp/claude-1000/-workspaces-reso-world/4e9e5d7d-3aff-4580-b969-8cd7e45e3bb1/scratchpad
git -C /workspaces/reso-world/external/resoloop worktree add --detach "${SP:?}/resoloop-18-red" 84c7932
git -C "${SP:?}/resoloop-18-red" cherry-pick --no-commit <Step 3 のコミット>
(cd "${SP:?}/resoloop-18-red" && dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter "FullyQualifiedName~SkillSyncKeepsFilesOfSkillsNoLongerBundled")
git -C /workspaces/reso-world/external/resoloop worktree remove --force "${SP:?}/resoloop-18-red"
```

Expected: FAIL（`Assert.True(... Synchronized)` が false）。一時 worktree は削除する

### Task 3: 検証

**テスト:** 書かない。受け入れ条件 1・2・4・5 を、静的な確認・build・テスト・導入した版の実行で確かめる。

- [x] **Step 1: `meshy` の出現箇所**

```bash
git grep -n -i meshy
git grep -n 'meshy-resoloop/'
```

Expected: 1 つ目は範囲外の 7 ファイル（`skills/codex/resonite-model-preproduction/SKILL.md` 7 箇所、`.../references/build-handoff.md` 7 箇所、`skills/codex/resonite-build/SKILL.md`・`README.md`・`README_JA.md`・`README-DETAILS.md`・`docs/BLENDER.md` 各 1 箇所）と、Task 2 のテストだけ。2 つ目は Task 2 のテストだけ（文書のリンクは 0 件）

- [x] **Step 2: 後のコミットの変更を巻き戻していない**

```bash
git diff 84c7932 HEAD -- README-DETAILS.md docs/BLENDER.md skills/codex/resonite-blender/SKILL.md skills/codex/resonite-build/SKILL.md
git diff 8bcef8a HEAD --stat
```

Expected: 1 つ目は Meshy の文の差分だけ。2 つ目は #15・#16 の変更に、`RLoop.Cli.csproj` の `Exclude` と Task 2 のテストが加わったものだけ

- [x] **Step 3: build とテスト（Debug・Release）**

```bash
dotnet build ResoLoop.slnx && dotnet test ResoLoop.slnx --no-build
dotnet build ResoLoop.slnx -c Release && dotnet test ResoLoop.slnx -c Release --no-build
```

Expected: 警告 0 件、すべて成功

- [x] **Step 4: 配布物の確認（pack → install → init）**

```bash
cd /workspaces/reso-world
bash scripts/resoloop-fork.sh install <HEAD の SHA>
resoloop --version
unzip -l external/resoloop/artifacts/fork/ResoLoop.<版>.nupkg | grep -i -E 'meshy|__pycache__|\.pyc$'
T="$SP/init-check" && mkdir -p "${T:?}" && resoloop init "${T:?}" && ls -a "${T:?}/.agents/skills"
resoloop skills sync "${T:?}" --check
```

Expected: 版が `...g<HEAD の短い SHA>`。nupkg の grep は 0 件。`.agents/skills/` に `meshy-resoloop` が無い。`--check` は synchronized。実在のワールドでは `skills sync --update` を実行しない

- [x] **Step 5: ResoLoop の版を戻す**

```bash
bash scripts/resoloop-fork.sh install 84c7932
resoloop --version
```

Expected: `0.1.0-preview.17.fork.20261009.g84c7932`

- [x] **Step 6: ブランチ全体のレビュー**

新しいコンテキストのレビュアー 1 名が `84c7932..HEAD` を、この Plan の Review Focus と Issue の受け入れ条件に照らして確認する。致命的な指摘だけを直す

### Task 4: 公開と報告

- [x] **Step 1:** fork のブランチを push し、usaturn/resoloop の `main` へ PR を作る（本文に検証の結果、範囲外、`Closes #18`）。上流へは出さない
- [x] **Step 2:** PR の公開 CI（windows: build・test・pack・導入の smoke test）の結果を確かめる
- [x] **Step 3:** この Plan に実施結果を記録し、create-reso-world の文書専用 PR を作る（コード PR と相互に参照する）
- [ ] **Step 4:** Issue #18 に、結果・検証の根拠・所要時間と主要な Task ごとの内訳をコメントする
- [ ] **Step 5:** 予約 `refs/heads/agent-claims/resoloop-issue-18` を、保存した claim の SHA を lease にして削除し、無くなったことを確かめる

マージ、マージ後の `bash scripts/resoloop-fork.sh install main`、この Plan の `completed` への更新は、利用者の指示を待つ。

## 実施結果（2026-10-16）

- 実行方法: Native（このセッションで実装）。作業記録は CODE_ROOT の `.superpowers/sdd/2026-10-16-usaturn-resoloop-issue-18-remove-meshy/progress.md`（git の追跡対象外。要点をこの節に写した後に削除）
- コミット: `1136d73`（Task 1: PR #11 の revert、29 ファイル +11 −5356）、`4719f4a`（Task 1: `Exclude` の入れ直し。csproj は PR #11 の版と同じ blob）、`a35a740`（Task 2: テスト）
- 判断（Ruling）: Task 2 の RED は、revert 前のコード（`84c7932`）にテストのコミットを cherry-pick して確かめた。本変更は機能の削除で、テストが守る挙動は revert で生じるため、revert 後の木では最初から成功する。cherry-pick は `Dispose` 前の helper の位置で衝突したので、一時 worktree の中だけで両方を残して解消した
- テスト:
  - Task 1: revert 後に build の警告 0 件、RLoop.Tests 451 件（PR #11 の Meshy のテスト 5 件の分だけ減った）・RLoop.IntegrationTests 19 件が成功
  - Task 2: 追加したテストは revert 後に成功。`84c7932` では `--check` の検査（`Synchronized` が false）で失敗し、その行を外すと `Assert.Single(updated.Updated)` が 4 件（Meshy の 3 ファイルの上書きと lock）で失敗した
  - Debug・Release とも build の警告 0 件、RLoop.Tests 452 件・RLoop.IntegrationTests 19 件がすべて成功
- 検証（Task 3）:
  - `git grep -i meshy` は範囲外の 7 ファイル（preproduction の `SKILL.md` 7・`build-handoff.md` 7、`resonite-build/SKILL.md`・`README.md`・`README_JA.md`・`README-DETAILS.md`・`docs/BLENDER.md` 各 1）と Task 2 のテストだけ。`meshy-resoloop/` はテストだけで、文書のリンクは 0 件
  - `git diff 8bcef8a HEAD` は #15・#16 の 14 ファイル（`9cf7178..84c7932` と同じ 248+/27-）と csproj・テストだけ。#16 も触った 4 ファイルの Meshy の行は `8bcef8a` と一致
  - `a35a740` を導入（`0.1.0-preview.17.fork.20261015.ga35a740`）。nupkg に `meshy`・`__pycache__`・`.pyc` は 0 件、skills は `resonite-*` の 7 本。空のディレクトリで `init` → `.agents/skills/meshy-resoloop/` は無く、lock にも Meshy の項目なし。`skills sync --check` は `synchronized=True`。実在のワールドでは `skills sync --update` を実行していない
  - 検証の後、`install 84c7932` で `0.1.0-preview.17.fork.20261009.g84c7932` に戻した
- ブランチ全体のレビュー: 新しいコンテキストのレビュアー（opus）が `84c7932..a35a740` を確認し、Critical・Important は 0 件、Review Focus の 1〜5 はすべて成り立つ（Ready to merge: Yes）。レビュアーは、`skills/codex` に `.pyc` を置いて pack して除外が効くこと、`84c7932` の実物の `meshy-resoloop` 9 ファイルと lock の項目を置いたプロジェクトで CLI の `--update` が lock だけを書き換えることも確かめた。Minor 3 件のうち 2 件（テストの `--check` の検査が既存の挙動まで固定している、revert で汎用の sync の検査 2 つも消えた）は致命的でないため対応せず PR 本文に記載。残りの 1 件（受け入れ条件 4 にテストのファイルが出ることの明記）は PR 本文で対応した
- 公開: fork PR https://github.com/usaturn/resoloop/pull/19 を作成（`Closes #18`）。head `a35a740` の公開 CI（run 38790410680）の windows（build・test・pack・導入の smoke test）が成功。文書は create-reso-world の文書専用 PR で公開する
- 残り: マージ（利用者の判断）、マージ後の `bash scripts/resoloop-fork.sh install main`、この Plan の `completed` への更新。Task 4 の Step 4（Issue へのコメント）・Step 5（予約の解放）は文書 PR の作成後に行い、結果は Issue #18 のコメントに記録する
