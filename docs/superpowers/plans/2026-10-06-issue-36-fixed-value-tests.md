# Issue #36 固定値テスト見直し Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 文面・モデル設定のコピーを検査するテストを整理し、参照・挙動・安全な範囲を検査するテストを維持する。

**Architecture:** 文面だけを固定する検査は削除する。配置・起動の検査は定義元を独立に読み比較する。安全な操作範囲、利用者所有のペルソナ、凍結した履歴は固定値の必要性を明記して維持する。

**Tech Stack:** Bash、zsh、Python（uv / pytest / unittest）、Git、GitHub CLI。

**Spec:** `docs/superpowers/specs/2026-10-06-issue-36-fixed-value-tests-design.md`

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`、Issue #36、PR #46（マージ未実施）
- 状態: completed
- 基準 HEAD: `ee1421ae3efb274cb5e28c8f3a810fe24ac5a3a6`
- 実行方法: 推奨の subagent-driven-development。各タスクを直列実行し、読み取り専用レビューを挟む。
- 実行許可: 利用者の「途中で止めずに推奨案で Spec、Plan を作成し PR まで実施せよ」。作成後の内容承認とは区別する。マージは実施しない。

## Global Constraints

- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-36-fixed-value-tests`。PARENT_ROOT: `/workspaces/reso-world`。
- 編集対象は表で指定したテスト、Spec・Plan、AGENTS.md の基本方針だけ。SKILL.md・README.md・ペルソナ・ワールド・#41 のロック関連検査・過去 Spec/Plan は編集しない。
- 文面検査を削除するために `SKILL.md`、schema、eval JSON の本文は変えない。
- 削除した語句検査を、別の同義語一覧、別ファイルに移した語句、件数の固定、弱い恒真の検査で置き換えない。
- Python は uv で実行する。`.devcontainer/` 内のブートストラップ用の既存 python3 使用は許可される。
- 同じ worktree に書く実装子は 1 件まで。子は委譲しない。review 子は読み取り専用、テスト実行は実装担当か controller。
- controller だけが文書 metadata、予約 ref、Issue・PR、push を管理する。実装子は担当テストと指定した AGENTS.md のみコミットする。
- テストの整理なので新しい固定値テストを作らず、許容する変更・拒否する誤りを隔離コピーで試して検査の有効性を確かめる。子は必要な検証を同期実行し、終了コードを確認してから報告する。

## Review Focus

1. 見出しの改称後に残った抽出 helper が実行テストを壊さない（Task 3 のスキル見出し変異）。
2. ファイル参照の typo が、文言検査削除と一緒に見逃されない（Task 1 のリンク切れ変異）。
3. 同じ現行設定から実行結果と期待値を作る恒真検査にならない（Task 2 の配置先不一致変異）。
4. 利用者所有のペルソナ変更や移植元名混入を引き続き拒否する（Task 1 の拒否変異）。
5. モデル更新で正常な引数転送テストが失敗せず、引数の脱落・順序誤りは検出する（Task 2 のモデル変更と引数誤り変異）。

---

### Task 1: 文書の参照検査と規則の整理（A、C の維持）

**Files:**
- Modify: `tests/scripts/test-docs.bash`
- Modify: `tests/scripts/test-instructions.bash`
- Modify: `.devcontainer/test-readme.bash`
- Modify: `AGENTS.md` の基本方針のみ
- Keep: `.devcontainer/test-initialize-mounts.bash`、`tests/scripts/test-gitignore.bash`

**Interfaces:**
- Consumes: 現行 Markdown 内のリポジトリ内参照、既存の mounts helper。
- Produces: 文面の言い換えを許容し、存在しない参照・禁止名・ペルソナ変更を拒否する既存のシェルテスト。

- [x] **Step 1: 読み取りと隔離コピーでの基準確認**
  Spec 3 章の A1〜A6・C1〜C3 に対応するブロックを読む。一時コピーで README に新しい見出しを追加し、旧 `test-docs.bash` が sections differ で失敗することを確認する。コピーは worktree の外に置き、共有 checkout は変更しない。
- [x] **Step 2: 文面固定を除去する**
  README のタイトル・見出し一覧、AGENTS のタイトル・文で位置を切り出す検査、現行指示の説明文一致を削除する。`CLAUDE.md` 先頭の `@AGENTS.md`、移植元/撤去ツール/旧 API/無効設定の禁止、ペルソナ SHA は維持する。過去文書と #41 のロック関連の既存 assertions は変更しない。残す文書チェックのコメント・PASS 表示を実際の検査範囲に合わせる。
- [x] **Step 3: 案内される実ファイルの存在を検査する**
  固定の `has README "$f"` を、本文中の Markdown リンク・バッククォートに記載したリポジトリ内の実ファイル/スキル参照の実在チェックへ変更する。サンプル・コマンド・glob・外部/ホーム/絶対パスは除外し、未知の `.md`・`.sh`・`.bash`・`.py`・`.json` 等の参照は存在しないと失敗させる。参照の内容をテストへ丸写ししない。小さい inline helper で済ませ、汎用パーサや新しい本文マーカーは作らない。
- [x] **Step 4: 規則を補う**
  AGENTS の既存 TDD 規則を維持して、文書/モデル設定を写しただけのテスト禁止、挙動/定義元比較/参照実在の優先、理由付きの安全境界・schema・凍結履歴・利用者所有部分の例外を基本方針に追記する。ほかの節は変更しない。
- [x] **Step 5: 検証しコミットする**
  正常: `bash tests/scripts/test-docs.bash && bash tests/scripts/test-instructions.bash && bash .devcontainer/test-readme.bash`。隔離コピーで見出し改称/節追加を許容、リンク切れ/移植元名/ペルソナ書換えを拒否することを確認。`git diff --check`。固定値保護の維持を差分で照合し、担当ファイルだけ `test: remove brittle documentation assertions` でコミットする。結果・時間・変異検証のログパスを report に記録する。

### Task 2: モデル設定を定義元との比較へ変える（B、C2 の維持）

**Files:**
- Modify: `.devcontainer/test-pi-superagents.bash`
- Modify: `.devcontainer/test-pi-openai-codex.bash`
- Modify: `.devcontainer/test-herdr-migration.bash` の alias モデル期待値のみ

**Interfaces:**
- Consumes: `.devcontainer/pi-superagents/*.json` の `superagents.modelTiers`、ランチャーの `pi_superagents_exec` 呼出し、`zshrc.txt` の alias 定義。
- Produces: 設定変更をそのまま反映する配置検査と、独立な静的定義に基づく実行 argv 検査。既存の unset 安全一覧はそのまま残る。

- [x] **Step 1: 基準と期待値の読み元を確認する**
  3 ファイルとランチャー/alias の定義を読む。一時コピーで tier の thinking/モデル、alias のモデルを変更し、旧検査が固定値で失敗することを確認する。親モデルは tier の選択と同一であると仮定しない。
- [x] **Step 2: tier の固定表を除去する**
  `test-pi-superagents.bash` の重複 tier 値一覧とその専用 helper を除去し、既存の定義元対配置先比較・構造/provider/モデル実在チェックを残す。`test-pi-openai-codex.bash` では piga/pigs/pigl の配置結果の `superagents.modelTiers` を対応する source JSON と直接比較する。関連するテスト名と説明から現在のモデル世代の固定を除く。
- [x] **Step 3: argv のモデル・thinking を source から読む**
  launcher 定義の唯一の `pi_superagents_exec` 呼出しから `--provider`・`--model`・`--thinking` の定数を解析し、実際の dry-run/installed 実行結果と比較する。起動結果から期待値を作らない。alias は `zshrc.txt` の静的定義を shlex 等で解析して `claude` の prefix を得て、実行 probe の argv と独立比較する。モデル以外の引数転送と C2 の unset 一覧は変えない。
- [x] **Step 4: 検証しコミットする**
  `bash .devcontainer/test-pi-superagents.bash && bash .devcontainer/test-pi-openai-codex.bash && bash .devcontainer/test-herdr-migration.bash`。隔離コピーで tier モデル/thinking・alias モデル更新を許容し、配置先だけの破損と引数脱落を拒否する（比較を適用する fixture を使う）。`git diff --check`。担当ファイルだけ `test: compare launcher settings with their definitions` でコミットする。結果・時間・変異ログを report に残す。

### Task 3: スキルの文面固定を除去する（D）

**Files:**
- Modify: `tests/scripts/test_superpowers_lifecycle.py`
- Modify: `tests/skills/test_skill_packages.py`
- Modify: `.agents/skills/{pr-review,review-fix-planning,agent-handoff,repo-cleanup-after-merge,simplify-in-subagent,rst-writer,planning-parallel-issues,monitoring-long-tasks,pi-model-name,stale-git-lock-recovery,find-docs,herdr-agent-task}/tests/*contract*.py`

**Interfaces:**
- Consumes: Spec 4 章の全ファイルの個別判断、既存の bash/zsh 実行 fixture、schema、frontmatter、links、symlinks。
- Produces: 文面に依存しない構造・参照・実行のテスト。CLI/schema keys と履歴 SHA manifest は維持する。

- [x] **Step 1: 各テストを目的で分ける**
  Spec 4 章を読み、各ファイルで説明文のみの関数は削除候補、実行/構造/参照/安全 guard は維持候補として、変更前の名前を report に記録する。eval 5 を含む期待文の固定は削除し、eval JSON の構造・fixture 実在は残す。固定値の件数を追加しない。
- [x] **Step 2: 文面の検査と不要な helper を削除する**
  SKILL の節/手順/例/説明文の固定 assert を除く。混在する関数は構造部分だけ残す。使われなくなった constants/imports/section helper を削除する。実行テスト、凍結履歴 manifest、意味的な危険操作 guard は削らない。
- [x] **Step 3: 残す検査の見出し依存を除く**
  bash block は `--operation review-workspace` / `--operation review-fix` / status 投稿 CLI 等の一意な実行マーカーで抽出する。schema のフィールド・continuation gate は表の機械キーで探す。参照先は文書全体から列挙する。状態表は enum の列から探す。これらのために本文を変更しない。
- [x] **Step 4: 正常と変異を検証する**
  `uv run pytest tests/skills .agents/skills` と `uv run pytest tests/scripts/test_superpowers_lifecycle.py`。隔離コピーでスキル見出し改称・手順名言い換え・README/AGENTS 見出し変更でも残る検査が成功することを確認する。schema key の脱落/参照切れ/危険操作 guard を既存の代表テストで拒否することを確認する。実行テストの関数名が差分で残っていることを確認する。
- [x] **Step 5: コミットする**
  `git diff --check`。変更 Python の診断が利用できれば LSP probe、利用不可なら compile/pytest で確認する。担当テストだけ `test: stop pinning skill prose and headings` でコミットする。ファイルごとの削除/維持と検証・時間を report に記録する。

## 統合・公開（controller）

- [x] Spec/Plan の自己レビュー、draft コミット、`scripts/superpowers-review-copy.sh` で SHA 付き確認コピー作成。内容承認を偽らず実行許可の対象 SHA を記録する。
- [x] 各タスクの直後に spec 適合とコード品質を fresh review し、重要な指摘を解消する。全タスク後に全差分のレビューを行う。
- [x] 全体検証: `uv run pytest`、指定の `uv run pytest tests/skills .agents/skills`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`git diff --check`。
- [x] Spec A〜D の各行を差分/維持理由と照合。検証ログ、既存警告、実行時間を文書と PR に記録する。文書 metadata のみで、内容の承認を捏造しない。
- [x] 自分の予約 SHA・Issue の OPEN・main の最新状態を確認し、作業ブランチを push、main 向け `Closes #36` の PR を 1 本作成する。マージしない。
- 運用後処理（完了記録は PR/Issue コメント）: Issue に結果と PR を記録し、予約 ref を保存 SHA の lease 付きで削除、削除確認、Herdr を completed にする。

## 実行結果

- 初版内容 SHA: `0601efbb985d21adc535b1b59e5f05654ae2d496`。利用者指示による実行許可で進め、内容レビューによる approved は記録していない。
- Task1〜3、個別レビュー/修正レビュー/全差分レビュー、PR 作成まで完了。公開: https://github.com/usaturn/create-reso-world/pull/46 。マージ未実施。
- 最終コード `b084f43c753fff0bdc02f9962e534fab6ec65230` で controller が root555 passed/1skip、skills487 passed/1skip、shell28 PASS、layout PASS、Python14構文確認、diff check を実行。ログ: `/workspaces/reso-world/tmp/issue-36/final-b084f43/`。
- 最後の safety guard はレビュー済み Git のバイト列へ復元して引用 payload の拒否を確認。残るコメント文字列の誤検出、変更対象外の killed-create race、既存スキル同期警告、裁定・時間内訳は Spec 8章を参照。
- 予約 ref の解放/Issue コメント/Herdr は controller の公開後処理。実施記録は公開コメントに残し、worktree は維持する。
