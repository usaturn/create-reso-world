# Dev Container texture transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dev Container のテクスチャ転送の生成設定と案内を `data` に切り替える。

**Architecture:** ホストの initializer が既存の生成 env に設定を書き、既存の `--env-file` でコンテナへ渡す。公開版 installer と fork の明示導入は分離したままにする。

**Tech Stack:** Bash、Dev Container JSONC、Markdown。

**Spec:** `docs/superpowers/specs/2026-10-26-create-reso-world-issue-277-texture-transfer-data-design.md`

**管理:** `usaturn/create-reso-world` #277、状態 `draft`。利用者の `issue-to-pr #277 --merge --max-cycles 3` による実行許可。内容の承認ではない。

## Global Constraints

- `initialize.bash` は WSL の有無・checkout の場所によらず、生成する `.devcontainer/resonite-screenshots.env` に `RESOLOOP_TEXTURE_TRANSFER=data` を書く。`RESOLOOP_HOST_PATH_MAP` の生成と UNC パス計算は削除する。
- 同ファイルは従来どおり毎回作り直す。前回の自動生成値は残さず、写真フォルダのリンクがあるときの `RESOLOOP_SCREENSHOTS_DIR` は維持する。
- mount の一覧・env-file の場所・権限・写真リンクの検証、利用者所有の `~/.config/create-reso-world/env` は変えない。生成 env の実物やワールドは編集しない。
- 公開版の自動導入・版固定なしの方針は変えない。機能が公開版に入るまでは rebuild 後に `bash scripts/resoloop-fork.sh install origin/main` が必要で、次の rebuild・公開版の再導入で戻ることを明記する。
- 実機の apply・rebuild は本変更では実行しない。PR は `Refs #277` とする。

## Review Focus

1. 非 WSL と `/mnt` 配下でも `data` を生成する（一時動作検証、L のため常設テストなし）。
2. 再実行で旧自動生成値を残さず、写真リンクの設定を維持する（一時動作検証と既存 initializer テスト）。
3. 利用者 env を保持する（既存の安全範囲は変更せず、一時 sentinel と既存 S テストで検証）。
4. 公開版に未搭載の機能を、環境変数だけで利用可能と誤認させない（README シナリオ確認、F のため常設テストなし）。
5. `data` の優先順位・明示 override・形式と audio の制限を読み取れる（README と fork の仕様を照合、F のため常設テストなし）。

## 要件・担当・証拠の対応

| Spec 条件 | 担当 | 観測結果と検証 |
| --- | --- | --- |
| 1–3 | Task 1 | コピーした initializer の出力、再実行、リンクと sentinel。既存安全テスト。 |
| 4–6 | Task 1 | README と生成値・CLI の実装済み仕様の照合。installer は差分なし。 |
| 7 | 調整役 | 実ワールド未操作。PR/Issue にマージ後の確認を記載。 |
| 共通前提 | 調整役 | initializer の出力先と devcontainer.json の `--env-file` の一致、公開版と fork の違いを実装前・統合時に確認。 |

## 実行予算

- 全体 240 分（準備・調査 30、実装・Task/branch レビュー 35、全検証・公開 25、レビュー修正ループ最大 3 × 50）。調査開始は約 17:31 UTC。ledger 開始前の準備は約 10 分として完了時に併記する。
- worker の目安: 実装 20 分、Task/branch レビュー各 15 分（保存用 3 分、無進捗 5 分を目安）。pi の同期 role API に停止手段は無いので、期限で kill せず戻るまで待つ。runner レビュアーの期限は既定 45 分、修正担当は既定 90 分。
- 同じ信頼性失敗の再試行は 1 回まで。安全の失敗は即停止。予算 100% で停止。phase 境界、50%/100%、worker 失敗直後を checkpoint とする。
- 新規機能追加をせず、問題が広がれば未確認を保持して報告する。上流コード変更・fork 自動導入へ広げない。別の Issue 作成は許可なく行わない。
- 作業領域: `/workspaces/reso-world/tmp/agents/issue-277.h3wm65x_/`。SDD はその `sdd/2026-10-26-create-reso-world-issue-277-texture-transfer-data/`。final branch review clean 後に SDD 作業領域を削除するが、検証ログ・checks はループへ渡すので保持する。

## 実行方式

`subagent-driven-development`。1 Task のため並列 wave は 1 件のみ。設定と説明は同じ納品物としてまとめ、子は feature worktree を 1 件だけ使用する。独立しない手順を分割して並列化しない。実装・Task レビュー・branch レビューはそれぞれ別の担当へ同期委譲する。モデル指定は role 設定に任せる。

### Task 1: 生成設定と利用案内の切り替え

**Files:**
- Modify: `.devcontainer/initialize.bash`（env 生成の末尾）
- Modify: `.devcontainer/README.md`（写真フォルダの env 説明、Windows テクスチャ取り込み）
- Modify: `.devcontainer/devcontainer.json`（`--env-file` のコメントのみ）
- Modify: `.gitignore`（生成 env の説明コメントのみ）

**Interfaces:**
- Consumes: 既存 `runArgs` の `--env-file` と `.devcontainer/resonite-screenshots.env`。
- Produces: 常に `RESOLOOP_TEXTURE_TRANSFER=data`、写真リンク時のみ従来の `RESOLOOP_SCREENSHOTS_DIR`。

**テストの要否:** 新規の常設テストは不要。env の欠落は apply の明示エラーで気付ける L、文言・設定の照合は F。既存の S/F∩S のテストは変更しない。一時動作検証で red/green を記録する。

- [x] **Step 1: 一時検証で変更前の欠落を確認する。** セッションディレクトリ配下に検証スクリプトと一時 HOME を作り、initializer のコピーを実行する。WSL なしで `RESOLOOP_TEXTURE_TRANSFER=data` が無いことを失敗として観測する。リポジトリ内の生成 env を触らない。
- [x] **Step 2: 生成処理を切り替える。** 既存の truncation と写真リンクの分岐を残し、`repo_root`/WSL/UNC のブロックを無条件の `printf 'RESOLOOP_TEXTURE_TRANSFER=data\n' >> "$env_file"` に置換する。コメントを更新する。`.devcontainer/devcontainer.json` と `.gitignore` は関連コメントだけを整える。
- [x] **Step 3: README を更新する。** Spec 条件 4–6 を説明し、fork のマージ済み機能へのリンクを使う。rebuild 後に `printenv RESOLOOP_TEXTURE_TRANSFER` と `resoloop apply --help` で確認する。公開版未対応なら `bash scripts/resoloop-fork.sh install origin/main`、公開版に戻る操作は `bash .devcontainer/install_resoloop.bash`。`--texture-transfer file`、env がプロジェクト設定より優先、audio/形式の制限、旧手動設定は利用者が必要に応じ削除することを記す。実物の生成 env や利用者の env を編集しない。
- [x] **Step 4: 一時検証と既存検証を行う。** WSL 有無、`/mnt` 配下相当のコピー、写真リンク有無、古い env の再生成、2 回目の実行と利用者 sentinel の保持を確認。`/mnt` の検証場所は一意の使い捨て領域に限り、権限不足なら実行不能を報告する。`bash -n .devcontainer/initialize.bash`、`bash .devcontainer/test-initialize-mounts.bash`、`bash .devcontainer/test-readme.bash`、`git diff --check` を実行。ログはセッション配下へ置く。レビュー用 report にコマンド・終了コード・red/green と時間を記録。
- [x] **Step 5: 差分を自己レビューし commit する。** 対象 4 ファイルだけを stage し、`git commit -m "fix: default container texture transfer to pixel data"`。Plan のチェック更新は調整役が行う。公開操作やサブエージェント起動は行わない。

## 統合・公開のチェックリスト（調整役）

- [x] Task review の spec/quality を確認し、Task 1 を完了として記録する。
- [ ] 全検証: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。ワールドは対象外。
- [ ] 全体の branch review と SDD の作業領域 cleanup を行う。
- [ ] 最後の記録 commit 後の HEAD・clean status・全検証 3 コマンドの argv/終了コード/ログを checks とともに保持する。
- [ ] Issue の状態・競合を再確認し、Gitleaks 検査済み SHA を push、main 向け PR を作る。決定・方式・検証・所要時間・残る rebuild/実機確認を記す。
- [ ] 最大 3 サイクルのループを実行する。マージは `finalize.py` のみ。ループ完了後に Issue に PR と残る確認をコメントし、結果を報告する。

## 実行記録

- Task 1: `4ebc121..0da2775`、実装担当の検証は一時 RED→GREEN、WSL 有無×写真リンク有無の 4 ケース・再実行・旧値削除・利用者 sentinel 保持、構文/差分/既存個別チェック、Dev Container 全 23 scripts が成功。Task レビューは spec compliant / quality approved、指摘なし。
- `/mnt` 下の一時領域作成は権限不足で実行できず、再試行・回避なし。パス判定自体を削除した差分と、別の任意パスでの無条件出力を確認したが、`/mnt` で実行済みとはしない。Step 4 の事前指定どおり実行不能として記録。
- 実装担当: 約 6 分 52 秒、Task レビュー: 約 3 分（概算）。rebuild/実機 apply は未実施。ログは `/workspaces/reso-world/tmp/agents/issue-277.h3wm65x_/`。
