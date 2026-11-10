# Issue #359 Cleanup Symlink Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 導入した ~/bin/cleanup-workspace.bash が既存の helper 解決と安全な退役を使えるようにする。

**Architecture:** cleanup の配置だけをコピーから絶対 symlink に変える。既存配置関数を抽出して偽 HOME に適用し、導入先から実 helper のローカル fixture を処理する。

**Tech Stack:** Bash、GNU coreutils、git、uv、既存 pr-review helper。

**Spec:** `docs/superpowers/specs/2026-11-10-issue-359-cleanup-symlink-design.md`（draft、実行許可は issue-to-pr の明示指示）。

## Global Constraints

- コード変更は `.devcontainer/install_beforehand.bash` の cleanup 配置と `.devcontainer/test-install-beforehand.bash` だけ。
- 他の Herdr helper の配置は変更しない。
- `.devcontainer/zshrc.txt`、cleanup 本体の helper 探索規則、`.devcontainer/test-cleanup-workspace.bash` の既存ケースは変更しない。
- cwd・HOME・掃除対象データから helper を推測しない。実 PR、実セッション、実 HOME の掃除・再導入はしない。
- #347 と `run-tests.bash` を同時実行しない。実行直前に既知の実行を確認する。
- rebuild・実環境の定期起動は自動実行しない。マージ後の利用者確認として残し、PR は `Refs #359` にする。

## 受け入れ基準

- **動作環境:** Ubuntu Dev Container、Bash・GNU coreutils・git・uv。リポジトリの絶対パスには空白を含めてもよい。検証は一意の一時 HOME / git repo / TMP_ROOT の中だけで行う。
- **実入力:** 偽 HOME の `bin/cleanup-workspace.bash` に旧コピーを置き、実際の配置関数で置換後、その導入先を直接実行する。実 helper が作成した保存済み review（複数行・日本語を含む本文）と未保存 draft を使い、helper env の明示なしで保存済みだけが退役し、未保存本文と保存先の review は残ること、git worktree 登録も退役分だけ外れることを観測する。再配置・再実行も成立する。
- **防御範囲:** helper が見つからない場合は削除せず理由を報告する（既存 cleanup テスト）。実 HOME・実 PR・既存の /tmp セッションには触れない。postCreate 全体の実行、他 helper の配置変更、壊れたスクリプト symlink 自体の実行成功は保証対象外である。

## Review Focus

- 旧コピーを置換でき、二度目の配置でリンク先を壊さないか: Task 1 の動的導入テスト。
- 導入先を直接実行でき、helper env に依存していないか: Task 1 の実 helper 経路。
- 退役で保存先の本文や未保存 draft を失わないか: Task 1 の正負の観測（S）。
- 空白を含む絶対パスの引用: Task 1 の fixture パスに空白を含める。全パターン網羅はしない。
- helper 不在で保持する既存の守り: 変更せず既存 cleanup テストを実行し、重複テストは追加しない。

## 実行方式・担当

`implement_task.py check` の self=false に従い、SDD 形式の Task を runner の `pi_opencode-go_deepseek4-flash_max`（利用者指定、fallback=[]）に 1 件ずつ依頼する。controller は実装を引き取らない。Task のレビューと最後の全体レビューは読み取り専用の sp-review。実装担当・レビュー担当には同じ受け入れ基準と Task brief を渡す。PR 後のループ inspect / implement は利用者の指定を維持する。

## 実行予算

全体 360 分（準備 15、Task 実装・レビュー 55、統合検証・PR 50、ループ 3 サイクル × 80 分）。実装 runner は役割の既定期限 90 分。同期 foreground、ツール timeout なし。取り消せない操作や検証コマンドに打ち切り watcher は使わない。予約枠・無進捗の追加打ち切りは設けず、runner の期限・停止確認を使う。PR レビュアーの期限は各 45 分、ループ設定の max_cycles=3 を使う。

同じ信頼性失敗の再試行は 1 回まで（runner の failed は停止）。安全失敗・捕捉後 base 移動は即停止。checkpoint は各 phase 境界、50%・100%、失敗直後。ledger は `/workspaces/reso-world/tmp/agents/issue-359.k1wihru_/budget.jsonl`、SDD は同セッションの `sdd/2026-11-10-issue-359-cleanup-symlink/`。ログはループの検証再利用に必要な間保持する。

## contingency（代替策）

最初の RED が fixture / helper API の差なら意味を保つ最小修正を ledger に残す。symlink 方式・所有範囲・保持境界を変える必要があれば停止する。テストの干渉があれば #347 の検証終了まで待ち、並行実行しない。指定担当の失敗は self に切り替えず報告。検証の既存不具合は systematic-debugging で切り分け、解消できないものを成功扱いしない。

## 要件照合（統合担当: controller）

| 条件 | 担当 | 観測結果 | 証拠 |
| --- | --- | --- | --- |
| 旧コピー置換・再導入 | Task 1 | 配置した導入先が再配置後も動く | 動的配置テストの RED/GREEN |
| helper 解決・保存済み退役 | Task 1、controller 統合 | 明示 env なしで保存済み session と worktree 登録だけ外れる | 同テスト、導入先実行の出力 |
| 保存本文・未保存 draft 保護 | Task 1、controller 統合 | 内容と未保存側の登録が残る | 同テストの独立した入力照合 |
| helper 不在時保持 | controller 統合 | 既存コピー負例で理由表示と保持 | 既存 test-cleanup-workspace |
| rebuild 後の実環境 | 利用者（マージ後） | ~/bin 導入先の定期実行 | 未実施として PR/Issue に残す |

共有前提は配置関数→導入先の実体→helper の保存/退役順序であり、controller が条件単位で証拠を照合する。別の Task の暗黙の入力・状態はない。

### Task 1: cleanup の導入方式と実行経路の回帰検証

**Files:**
- Modify: `.devcontainer/install_beforehand.bash`（`place_herdr_helpers()` の cleanup 配置だけ）
- Test/Modify: `.devcontainer/test-install-beforehand.bash`

**Interfaces:**
- Consumes: `place_herdr_helpers()`、`WORKSPACE_ROOT`（installer が絶対パスを初期化）、HOME、実 helper の create/save/reap-check/cleanup。
- Produces: `~/bin/cleanup-workspace.bash` が repository 実体に届く絶対 symlink。既存コピーの置換と再実行が成立する。既存の失敗伝播を維持。

**テストの要否:** 新しい導入経路からの安全な退役とデータ保持は、実際の気付きにくい不具合の再発防止および誤削除防止（S）のため動的テストを追加する。symlink の有無・パスだけを検査するテスト、文言コピー、既存 helper 不在テストの重複は追加しない。構文・存在・実行権限だけのテストは L のため不要。直接実行がその確認を兼ねる。

- [x] **Step 1: 動的回帰テストを追加する。** 既存 test-install-beforehand の関数抽出・一時領域パターンを使う。偽 HOME の bin に旧コピーを置き、実配置関数を実行する。実 helper でローカル git repo と保存済み/未保存の session を作る（test-cleanup-workspace の API を参照し、同ファイル自体は変えない）。複数行・日本語の保存本文と未保存 draft の独立した期待内容を持ち、空白を含む一時パスを使う。helper env を解除して導入先を直接実行し、保存済みだけの退役、登録解除、保存本文保持、未保存 draft と登録の保持を観測する。再配置・再実行も観測する。テスト内は一時 HOME を env のワンショットで渡し、Python は uv を使う。元 repository のファイルへ chmod しない。
- [x] **Step 2: RED を確認する。** `bash .devcontainer/run-tests.bash .devcontainer/test-install-beforehand.bash`。現行コピー方式で、保存済みが退役されず失敗することを確認し、実際の出力を報告に残す。fixture の import / 構文失敗は目的の RED ではない。
- [x] **Step 3: 最小修正を行う。** cleanup の cp / chmod だけを絶対 symlink の配置に置換する。`WORKSPACE_ROOT` を使い、古い通常ファイルを置換する。既存ディレクトリを宛先と誤認して内部へリンクを作らない。失敗は既存どおり `return 1` で伝える。他の配置は変えない。
- [x] **Step 4: GREEN と回帰を確認する。** 他の run-tests 実行が無いことを確認後、`bash .devcontainer/run-tests.bash .devcontainer/test-cleanup-workspace.bash .devcontainer/test-install-beforehand.bash` と `bash -n .devcontainer/install_beforehand.bash .devcontainer/test-install-beforehand.bash`。全成功、実行前後の git diff と status に許可範囲外の変更が無いこと。
- [x] **Step 5: Commit と報告。** 2 ファイルだけ stage し、`fix: resolve cleanup helper through installed symlink`。結果には RED/GREEN の対象版・argv・終了コード・主な観測結果、所要時間を含める。runner の worktree 外へ成果ファイルを作らない。報告は helper が指定する JSON で返す。

## controller の統合・公開手順

Task の受け取り後に同じ関連テストと bash -n を実行し、読み取り専用 Task review を行う。条件照合を更新して完了を記録する。最後の branch 全体レビューは captured base SHA から行う。レビュー子はテストを実行しない。

README の入口: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。最後のコード/文書 commit 後の clean HEAD で同期実行し、各 argv・終了コード・ログ・捕捉 base SHA を checks-file に記録する。

base / 競合の再確認、Gitleaks、検査 SHA の push、main 向け PR、実 base/head 照合。`Refs #359` と rebuild 後に残る確認を書く。指定の inspect 3 担当と implement 担当で `pr-review-fix-loop` を起動し、finalize 以外でマージしない。Issue は未実施の rebuild 確認を完了扱いしない。
