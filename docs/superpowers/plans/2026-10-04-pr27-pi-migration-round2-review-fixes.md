# PR #27 pi 移行の追加修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan. Steps use checkbox syntax for tracking.

**Goal:** 再現済みの5件を回帰テストで固定し、利用者設定と保持対象を失わずに移行する。
**Architecture:** 既存 cleanup の metadata 読込み・npm source 判定・子環境を最小修正し、既存 zsh setup に失敗伝播と限定したパス展開を加える。
**Tech Stack:** Python unittest、zsh、実 npm のオフライン fixture。
**Spec:** `docs/superpowers/specs/2026-10-04-pr27-pi-migration-round2-review-fixes-design.md`

## Global Constraints

- 対象は `.devcontainer/cleanup_pi_mcp.py`、`.devcontainer/setup_pi.zsh`、`.devcontainer/tests/fake_pi_packages.py`、`.devcontainer/tests/test_pi_mcp_cleanup.py` と今回の文書のみ。
- 既存安全策、バックアップ、mode、独自設定・認証・MCP保持を維持する。
- 実認証・ネット接続・利用者の実 agent directory は使用しない。uv で Python を実行する。`.devcontainer/` の既存 bootstrap の python3 は許可された例外として維持する。
- scratch・TMPDIR・ログは controller 指定の一時 root 配下に置く。source/test は隔離 worktree 内のみ変更する。
- サブエージェントは commit/push/Issue更新/他エージェント起動を行わない。controller がレビュー・検証後に1コミットで既存 PR の head に反映する。

## Review Focus

- JS trim が受理する U+FEFF と scoped/pinned source を漏らさず、類似名を削除しない。
- 不正 JSON が4マニフェストのどこにあっても pi 呼出し・バックアップ・状態変更の前に停止する。
- npm の env と prefix `.npmrc` の omit による dev/optional の巻き添え削除を実 npm で防ぐ。
- backup の cp 失敗が成功表示や既存モデル上書きへ進まない。
- `~/space path/agent` は HOME 配下へ書込み、cwd に文字列 `~` を作らない。

### Task 1: 入力処理と失敗伝播の回帰修正

**Files:** Global Constraints の4実装/テストファイルを変更する。新しい helper、テストファイル、依存関係は不要。
**Interfaces:** `matches(source, name)`、`read_object(path)`、`cleanup()` の呼出し方法を維持する。setup は引数を増やさず `PI_CODING_AGENT_DIR` と HOME を使用する。

- [ ] **Step 1:** 既存 fixture を使い R2-1〜R2-5 の失敗テストを追加する。名前と観測する挙動は以下のとおり。既存テストを削除・弱化しない。
  - `test_whitespace_retired_sources_are_removed_without_resurrection`: 5対象、string/object/pinned、JS trim whitespace（U+FEFF を含む）、settings-only、KEPTと類似名保持。cleanup→offline update後も撤去済み。
  - `test_nonstandard_json_constants_stop_before_mutation`: NaN/Infinity/-Infinity を settings と4マニフェストに置き、非ゼロ・pi呼出しなし・全元バイト列不変・cache保持。
  - `test_real_npm_omit_preserves_retained_dependency_types`: 実 npm fixture に declared dev/optional 保持対象と撤去対象を置き、NODE_ENV=production、npm_config_omit、prefix .npmrc の各ケースで保持ファイルのバイト列・宣言を確認し撤去対象だけ消す。ネット接続しない。
  - setup失敗テスト: 破損 models JSON、fake cp、blocked parent mkdir、Python書込み/検証の失敗を再現し、非ゼロと成功表示なしを確認する。cp失敗では元モデルのバイト列不変。
  - setupパステスト: exact `~`、`~/`、空白入りtilde path、絶対パス、デフォルト、`~other` 非展開を隔離cwd/HOMEで確認する。独自provider保持も確認する。
- [ ] **Step 2:** 新テストを修正前に実行し、各項目が期待するバグによって失敗することを確認する。fake identity の正常化は境界仕様に合わせるテストfixture変更として先行可能。
- [ ] **Step 3:** 最小修正を行う。npm payload の trim は実 pi の JS trim に合わせる。非標準定数は共有読込処理で拒否し、書込みでは `allow_nan=False`。pi 子環境の `npm_config_include` は `dev\n\noptional\n\npeer` とし、改行2つが npm の array 区切りである説明を添える。setup は `set -e` と exact `~` / `~/` の HOME 展開だけを追加し eval は使わない。
- [ ] **Step 4:** 新テストと `bash .devcontainer/test-pi-mcp-cleanup.bash` を同期実行し、全件成功を確認する。`git diff --check` と既存 safety/保持テストを確認する。実行・結果・red/green・所要時間を指定 report に記録する。
- [ ] **Step 5:** commit せず controller へ報告する。controller が修正後の独立点検、全体bash・layout・スキルテストを行い、既知失敗を照合する。その後に1コミットで既存 PR へ push する。
