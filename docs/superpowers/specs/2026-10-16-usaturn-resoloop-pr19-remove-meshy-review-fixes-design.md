# usaturn/resoloop PR #19: Meshy の同梱を外す変更のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（文書用ブランチ `docs/resoloop-18-remove-meshy`。同じテーマの文書 PR #108 はマージ済みで、open の文書専用 PR は無い）
- 対象リポジトリ・PR: https://github.com/usaturn/resoloop/pull/19（`chore/issue-18-remove-meshy` → `main`）
- 関連 Issue: usaturn/resoloop#18（PR 本文の `Closes #18`。`closingIssuesReferences` に含まれる）。本文で参照しているだけの Issue: usaturn/resoloop#14、usaturn/create-reso-world#95・#104
- 関連文書: `docs/superpowers/plans/2026-10-16-usaturn-resoloop-issue-18-remove-meshy.md`（Spec は無い。範囲は Issue #18 の本文で決めてある）
- 検証したコード HEAD: `a35a7406e32c2a1edb2297e7d1e90380af1444b9`（base `main` = `84c7932190edcbd37b88a8b490b4d5454855b651` は head の祖先）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/19` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う。Plan が「利用者の指示を待つ」としたマージ後の `bash scripts/resoloop-fork.sh install main` と Plan の `completed` への更新は、この許可に含めない
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/resoloop-18-remove-meshy-docs`（同じテーマの既存の文書用ブランチの worktree を、clean の条件で再利用。マージ済みの先端 `c17d790` から `origin/main` の `1129cb3` へ早送りしてからコミット）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-18-remove-meshy`（PR head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`external/resoloop/reviews/#19-chore-issue-18-remove-meshy/` の 5 ファイル。対象 HEAD はすべて `a35a7406e32c` で、`pull/19/head` の取得結果と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `SWE-2-High.md` | Approve | Info 2（どちらも PR 本文で既出と明記） |
| `claude-opus-5-5.md` | Approve | なし |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | なし |
| `gpt-6.1-sol.md` | Approve | なし |
| `openai-codex-gpt-6.1-sol.md` | Approve | なし |

Opus と DeepSeek は、SWE-2-High の 2 件と同じ内容を「PR 本文で既出」として指摘に数えていない。

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | SWE-2-High I-1 | 新テスト `SkillSyncKeepsFilesOfSkillsNoLongerBundled` が、lock に同梱外の項目（`meshy-resoloop/`）が残ったままの `--check` を synchronized とする既存の挙動まで固定している（`tests/RLoop.Tests/ProjectInitializerTests.cs:208`） | 対応しない。現行 HEAD で記載どおりと確認した。`Sync` は `Files` だけから entries を作り（`src/RLoop.Core/BundledSkillManager.cs:35-47`）、lock の余分な項目は状態の判定にも書き込み先にも使わない（`:21` のコメント、`:62-80`）。check が synchronized を返しても書き込みは起きず、update は lock だけを `Files` から作り直す。利用者のファイルは変わらないので、致命的な結果は起こらない。将来 check が古い項目を検出するように変えたときにテストの直しが要るという保守上の論点で、PR 本文の Validation に既出 |
| R2 | SWE-2-High I-2 | revert で、Meshy のテストと一緒に汎用の保証 2 つ（check は何も書かない、競合で止まったとき lock の内容・mtime が変わらない）のテストも消えた | 対応しない。消えたことを差分で確認した（`MeshySyncPreservesUserDataAndCheckIsReadOnly`・`MeshySyncRefusesEditedScriptBeforeRestoringMissingFile`）。どちらも同梱の `meshy-resoloop` のファイルを前提にしたテストで、同梱をやめると成り立たないので、理由のある削除である。守っていた挙動はコードに残っている: check は書き込みより前に戻り（`BundledSkillManager.cs:58-60`）、競合はファイルと lock を書く前に `SKILL_SYNC_CONFLICT` で止まる（`:49-55`）。競合時にほかのファイルを書かないことは、残るテスト（`SkillSyncRefusesUserModifiedContentBeforeUpdatingAnything`、`ReferenceFilesAreInstalledRestoredAndProtectedBeforeAnyUpdate`）が確かめている。テストの範囲が #11 の前に戻っただけで、マージしても実在の使い方で誤った結果は起こらない。PR 本文に既出（汎用テストとしての移植は別 Issue） |

分類: **解消済み 0 / 対応する 0 / 対応しない 2**。

仕様の論点として残すもの:

- R1: `skills sync --check` が、lock に残った同梱外の項目を「同期が必要」と報告すべきか（現状は無視し、update で lock から外れる）
- R2: check の読み取り専用と、競合時に lock を変えないことを、同梱スキルに依らない汎用テストとして入れ直すか（別 Issue の候補）

## 確認の範囲

- 変更ファイル（削除以外の 12 件）: `BundledSkillManager.cs` は全文、`RLoop.Core.csproj` は全体、`ProjectInitializerTests.cs` は差分と残る sync のテスト（100〜240 行）、`ci.yml`・README 3 本・`docs/BLENDER.md`・`resonite-blender`・`resonite-build`・`resonite-model-preproduction`（`SKILL.md` と `references/build-handoff.md`）は差分。削除 16 件は、#11 で追加したファイルの削除であることを差分の統計で確かめた
- 呼出元: `BundledSkillManager.Sync` は CLI の `skills sync`（`src/RLoop.Cli/Program.cs:63`）とテストだけ。`Files`・`LoadBundledFile` は `ProjectInitializer.Initialize`（`src/RLoop.Core/ProjectInitializer.cs:115-122`）と `UixRecipes`（`src/RLoop.Core/UixRecipes.cs:69`）。`Files` の各項目は `RLoop.Core.csproj` の埋め込みリソースと対応し、欠けると `LoadBundledFile` が例外を出すので、`Initialize` を通るテストで確かめられる
- 配布物: `RLoop.Cli.csproj` は PR 全体の差分に出ない（revert で消えた `__pycache__`・`*.pyc` の除外を次のコミットで入れ直し、`main` と同じになった）。`skills/codex` の下は `resonite-*` の 7 つだけ
- 残る参照: `git grep` で `pyproject`・`uv.lock`・`tests/meshy`・`fixtures/meshy`・`pytest`・`MESHY-VALIDATION`・`skills/codex/meshy-resoloop` は 0 件。`meshy` を含むのは、PR 本文で範囲外とした preproduction 関連の文書 7 ファイルと新テストだけ。`release.yml` にも参照は無い。`RLoop.IntegrationTests` は skills・init を参照しない
- 既存プロジェクトへの影響: `Sync` は lock に書かれたパスを書き込み先に使わないので、配置済みの `.agents/skills/meshy-resoloop/` は check でも update でも変わらない。#11 の版で init したプロジェクトに `resoloop init` をやり直すと lock の内容の違いで `INIT_FILE_EXISTS` になるが、同梱ファイルが変わる版ではどれも同じで、この PR が持ち込んだ挙動ではない
- 自己確認で、PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

PR head を checkout した専用の worktree（CODE_ROOT。HEAD `a35a740`、未コミットの変更なし）で実行した。ビルド出力（`bin/`・`obj/`）は ignore の対象で、実行後も `git status --porcelain` は空だった。

| コマンド | 結果 |
| --- | --- |
| `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` | 452 passed、skip 0（exit 0、約 70 秒）。新テスト `SkillSyncKeepsFilesOfSkillsNoLongerBundled` を含む |

`RLoop.IntegrationTests` は変更したコードを参照しないので実行していない。公開 CI: run 38790410680 がこの head で `windows`（4 分 15 秒）成功（`gh pr checks 19 --repo usaturn/resoloop`）。base `main` は head の祖先なので、base を merge した一時ツリーでの再検証は不要。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

無い。「対応しない」の R1・R2 は、PR 本文の Validation に既知の軽微な点として書かれており、本文の保証と食い違わない。

## 作業時間

- 着手 2026-10-16T03:33Z 頃、Spec の完成 2026-10-16T03:42Z 頃（約 9 分）。内訳: レビューの読込と PR の状態・境界の確認・worktree の選定（約 2 分）、差分と関連処理の精読（約 2 分）、テスト（約 1 分）、関連 Issue・文書用ブランチの確認と Spec の作成（約 4 分）
