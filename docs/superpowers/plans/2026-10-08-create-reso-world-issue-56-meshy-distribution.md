# Meshy 実行基盤の ResoLoop 同梱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 任意機能の Meshy 実行基盤を ResoLoop の init / skills sync で自己完結して配布する。

**Architecture:** 既存の埋め込みリソースと許可リスト型ハッシュ同期を拡張し、skill 配下に全モジュール・手順を隣接配置する。既存 wrapper の安全条件を維持し、ローカル doctor と Linux platform gate を追加する。依存導入・認証は利用者の明示手順に分離する。

**Tech Stack:** .NET 10 / C#、Python >=3.12 / uv / pytest、Node.js >=22.12.0、meshy-cli 0.4.0、Blender / NumPy、ResoLoop exporter。

**Spec:** `../specs/2026-10-08-create-reso-world-issue-56-meshy-distribution-design.md`（内容コミット `0bacce7b1a9d89c930917bf83d18abda9617e7fe`）

- 文書管理: `usaturn/create-reso-world`、Issue #56
- 実装対象: `usaturn/resoloop`、基準 HEAD `8bcef8a14e4b36167058df3f5c4af95ee895f9cf`
- 状態: draft
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-56-meshy-docs`
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-56-meshy`
- 実行方式: 推奨の subagent-driven。Task は直列、レビューは読み取り専用。
- 実行許可: ユーザーの「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」により、内容の承認待ちは省略する。内容が個別レビュー済みという意味ではない。Plan の内容 SHA を後で記録する。

## Global Constraints

- wrapper の生成・変換は Linux のみ。Windows native / macOS は未対応。Windows の init / sync と bundle 適用は別。
- Python >=3.12、Node.js >=22.12.0、Meshy CLI 0.4.0。通常 ResoLoop は最新の NuGet 公開版（prerelease を含む）。
- init / sync で依存インストール・認証・API を呼ばない。doctor はローカル・短 timeout・無書込み・sanitized env。
- API キーは環境変数のみ。有無だけ確認し値を表示/保存しない。credentials fallback しない。
- 全同期競合を更新前に検出する。operation / journal / 生成物 / blend / state を管理範囲へ入れない。
- Build Handoff 承認と paid / image送信 / live適用の承認を分け、`not-authorized-at-preproduction-stage` を実行許可にしない。
- submitting / unknown は再送禁止。素材の拒否と source culling の個別承認を維持する。
- source create-reso-world を変更しない。Spec/Plan は create-reso-world にのみ保存する。
- 有料・画像外部送信・認証・live 操作、マージ、上流 PR、NuGet 公開を行わない。

## Review Focus

1. 空白のあるプロジェクト/配置先でも兄弟 import と Node guard の preload が動くこと（Task 1/2 の再配置テスト）。
2. 別ファイルの欠落と script の手編集が同時に起きても sync が一つも変更しないこと（Task 1 の snapshot）。
3. dependency probe の出力/timeout に secret が混入しても doctor が漏らさず、送信前に版違いを止めること（Task 2）。
4. Meshy / Node がなくても offline plan が動き、Windows help は POSIX import で落ちないこと（Task 2）。
5. pack/install の配布 ENTRY と移設した bundle で実変換/validate が成立し、fixture が skip で通過しないこと（Task 2/3）。

---

### Task 1: 自己完結配置と同期の挙動

**Files (CODE_ROOT relative):**
- Create: `skills/codex/meshy-resoloop/{SKILL.md,references/runbook.md,references/licenses.md,scripts/meshy.py,scripts/meshy_workflow.py,scripts/meshy_conversion.py,scripts/meshy_blender.py,scripts/meshy_cli_guard.mjs}`。
- Modify: `src/RLoop.Core/BundledSkillManager.cs`, `src/RLoop.Core/RLoop.Core.csproj`。
- Test: `tests/RLoop.Tests/ProjectInitializerTests.cs`。
- Create: `tests/meshy/test_meshy.py`, `tests/meshy/test_meshy_conversion.py`, `tests/fixtures/meshy/create_fixture.py`（移植元の実行可能テスト・fixture）。
- Create: `pyproject.toml`（任意の test dependency group、通常 init に無関係）。

**Interfaces:**
- Consumes: `BundledSkillManager.Sync(string targetDirectory, bool update)`、`ProjectInitializer` の既存 init。
- Produces: 配置済み `scripts/meshy.py --project PROJECT COMMAND`、Task 1 の8ファイル（Task 2 で doctor を加え計9ファイル）の v2 lock。既存の CLI / sync API は不変。
- Python テストは `RESOLOOP_MESHY_ENTRY` で配置済み ENTRY を選択できる。未指定時は target `skills/codex/.../scripts`。テスト内の直接 module import も同じ ENTRY の隣接パスを使う。

**テスト要否:** 必要。同期の安全条件・ファイルの配置・wrapper の実行/入出力を確認する。文書・ライセンス本文や一覧を写した文字列テストは作らない。

- [ ] **Step 1:** C# テスト `MeshySyncPreservesUserDataAndCheckIsReadOnly`、`MeshySyncRefusesEditedScriptBeforeRestoringMissingFile`、`MeshySyncInstallsIntoPreMigrationLock` を追加する。実 init/sync を呼び、配置 script を開けること、check 前後 snapshot 一致、operation/journal/blend/state 保持、欠落＋手編集時の `SKILL_SYNC_CONFLICT` と bytes/lock 不変、解決後の復旧を検査する。
- [ ] **Step 2:** `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj -c Release --filter FullyQualifiedName~MeshySync`。未登録により FAIL を確認する。
- [ ] **Step 3:** source 5 scripts を隣接配置して移植し、skill と runbook の repository root / Dev Container 参照を除去する。ライセンス・外部依存の説明も配置する。Files/Names と explicit EmbeddedResource を登録する。新 installer/sync schema は作らない。
- [ ] **Step 4:** source の wrapper テストと Blender fixture を target へ移し、ROOT/ENTRY/兄弟 module の参照だけ target 用に変更する。API モック・guard 実行・path 保護などの検証内容は維持する。
- [ ] **Step 5:** C# focused tests と `uv run --group dev pytest tests/meshy/test_meshy.py -q` を実行し PASS を確認する。Node guard を空白を含む移設先で実行する回帰も加える。
- [ ] **Step 6:** `git diff --check`、diff を確認しコード側でコミットする。

### Task 2: 任意依存の診断、対応環境、制作導線、配布物テスト

**Files:**
- Create: `skills/codex/meshy-resoloop/scripts/meshy_doctor.py`。
- Modify: 同 `meshy.py`, `meshy_workflow.py`、`BundledSkillManager.cs`, Core csproj（doctor 登録）。
- Test: `tests/meshy/test_meshy_doctor.py`, 既存 `tests/meshy/test_meshy*.py`。
- Modify: 同 `SKILL.md`, `references/runbook.md`、`skills/codex/resonite-model-preproduction/{SKILL.md,references/build-handoff.md}`, `skills/codex/resonite-build/SKILL.md`, `skills/codex/resonite-blender/SKILL.md`, `README.md`, `README_JA.md`, `README-DETAILS.md`, `docs/BLENDER.md` の関連箇所。
- Modify: `.github/workflows/ci.yml`（Linux の非 live Python テスト。Windows pack smoke を維持）。

**Interfaces:**
- Consumes: Task 1 の配置済み ENTRY / `RESOLOOP_MESHY_ENTRY` / wrapper。
- Produces: `meshy_doctor.diagnose(project: Path) -> dict` (`ok`, `checks`, `key_present`) と `meshy_doctor.require_cli_compatibility() -> None`（名前付きエラー）。doctor CLI は `ok` に応じた exit 0/1。help/platform gate を通過するまで POSIX module を import しない。

**テスト要否:** 実ロジックは必要。fake PATH / dependency version / timeout / secret / 無書込み、送信ゼロ、任意依存なし plan、配布 ENTRY を検査する。文書変更には文字列テストを作らず、リンク先・構文・diff を検査する。

- [ ] **Step 1:** fake tools による doctor テストを書く。キーなしでもローカル依存が揃えば成功、node旧版/meshy新版/欠落/timeoutは非0、APIサブコマンド呼出しゼロ、envの key/NODE_OPTIONS 除去、出力の sentinel secret 不在、project snapshot 不変を検査する。非対応 platform は help 成功・操作拒否を検査する。版違い submit は operation を submitting にせず create が0回。
- [ ] **Step 2:** `uv run --group dev pytest tests/meshy/test_meshy_doctor.py -q`、未実装による FAIL を確認する。
- [ ] **Step 3:** doctor と platform/lazy import gate を実装する。probe の出力はそのまま表示しない。Meshy `--no-update-check` を使い、CLI送信経路の child_env 準備より前で版検査する。互換版の fake CLI に version 応答を加える。
- [ ] **Step 4:** source 環境に依存しない手順へ仕上げる。Node/Python/uv/Blender/NumPy/exporter の導入・確認・更新、ResoLoop の非固定最新導入、承認と復旧を記載する。preproduction の Meshy「外部スキル」説明を同梱へ変更し、finishing/build の責務を維持する。
- [ ] **Step 5:** Linux CI で Python/uv/Node を用意し安全条件・doctor テストを実行する。実 Blender が必須のテストを skip で成功扱いしない（ローカル mandatory 実行結果と分離する）。Windows の既存 pack/install smoke はそのまま維持する。
- [ ] **Step 6:** `dotnet test ResoLoop.slnx -c Release` と Python 全テストを同期実行する。Blender/NumPy の不足は一時隔離 launcher で補い、標準環境の未検証を明記する。必要 fixture は skip 0。
- [ ] **Step 7:** pack した CLI を一時 tool-path に install、新規 init、既存プロジェクトへ sync、キー・Meshy/Node 不在の通常 init/sync、配置済み help/plan を検査する。配置 ENTRY で Python 全テストを再実行する。変換 bundle を別パスへコピーして `resoloop validate`、asset の相対解決を確認する。
- [ ] **Step 8:** `git diff --check`、Python 構文、相対リンク、active LSP 診断、変更差分を確認しコミットする。

### Task 3: 最終レビュー、記録、fork PR と文書 PR

**Files:** この Spec / Plan、必要な検証結果を target `docs/MESHY-VALIDATION.md` に記録する。

**Interfaces:** Task 1/2 の変更・実行結果・内容コミット SHA を消費し、相互参照する2 PR を公開する。

**テスト要否:** 文書/PRの本文は不要。代替として main controller が直近のテスト・pack/install を再確認し、読み取り専用 reviewer に全変更とテスト採用基準を確認させる。

- [ ] **Step 1:** 読み取り専用 sp-review で最終ブランチレビュー。paid gate、retry、防漏洩、path保護、競合全件preflight、配布依存閉包、テスト基準を確認する。実装担当/controllerだけがテストを実行する。
- [ ] **Step 2:** 根拠のある指摘を修正し該当テストと全体検証を実行する。既存source/ユーザー作業物には触らない。
- [ ] **Step 3:** Spec/Plan に実行許可と内容SHA、実装HEAD、検証結果/残課題/所要時間を追記する。実施していない live/標準rebuild/Windows 実機は明記する。承認済みと推測しない。
- [ ] **Step 4:** 文書と実装をそれぞれコミット・push する。`usaturn/resoloop` に Meshy の独立 PR、`usaturn/create-reso-world` に Spec/Plan の文書専用 PR を作り相互参照する。`Refs usaturn/create-reso-world#56`、自動closeなし。
- [ ] **Step 5:** 公開 target の CI を確認する。create-reso-world private CI の確認は不要。forkマージ/上流PR/NuGet未公開を明記して、Herdr task を completed にする。

## 実行記録

内容コミットと検証結果は実行後に追記する。未実施のチェックを成功扱いにしない。
