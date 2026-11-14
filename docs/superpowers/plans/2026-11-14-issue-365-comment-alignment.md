# Issue #365 残作業: agent-runner.toml コメント文面揃え 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans（この run は issue-to-pr 委任で inline 実行に確定）。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR #432 後に残った `.devcontainer/agent-runner.toml` のコメント文面差を AW 現行に揃え、個人設定の旧名参照が無いことを確認する（値・並びは不変）。

**Architecture:** コメント行と README の説明だけを編集する。agent / role / workflow の値・並び・`schema_version` は一切変えない。AW 原文を基本に、CRW の実ファイル名・参照規約・#337 経緯・codex 拒否注記・install_beforehand 説明を保持し、AW 固有の出自記述（inspect の #616 節）は CRW の事実に合わせて削除する。Ollama / alibaba / piaq の CRW 固有コメントと `agy_*` agent の不在は揃えない差分として理由を残す。

**Tech Stack:** TOML（agent-runner 雛形）、Markdown（README）、uv / Python（tools.agent_runner の check/list）、pytest。

**Spec:** `docs/superpowers/specs/2026-11-14-issue-365-comment-alignment-design.md`（commit `3c3e9854`）

- 状態: `completed`
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-365-comment-alignment`
- branch: `feat/issue-365-comment-alignment`、base `bcff80ed97c70b31cb30afd3dfb6f9264594efb2`
- 実行方式: `superpowers:executing-plans`（inline、self）。理由: implement は既定の self、同じファイルの逐次コメント編集で 1–2 Task の小変更（issue-to-pr 4 章の表）。
- 実行許可: 利用者の 2026-11-14「残作業を実行してください」（issue-to-pr 委任）。`--merge` 無し。PR 作成で終え、マージしない。
- 比較元 AW: main `36c321cb`、blob `69e841dd229f1ca3cfcf0ba5d092b58bd45b5945`（SESSION の `aw-agent-runner.toml`）。

## Global Constraints（Spec から逐語）

- 実個人設定・key・ログイン・履歴・#408 の値（Ollama 定義・exec・key 導出）を変更しない。alias と自動移行は対象外。
- `check` の成功を認証や実サービス起動の成功と表示しない。
- `[workflows.issue.assignments.implement]` の `self`・`after_run` の `--project .`・`env` の `OPENCODE_API_KEY` を変えない。
- 過去の Spec・Plan・レビュー記録の agent 名を書き換えない。agent / role / workflow の値・並び・`schema_version` を変えない。
- 新しい agent・alias・自動移行・CI・恒久テストを追加しない（`agy_*` 6 agent は追加しない）。
- AW の Issue 参照は `usaturn/agent-workspace#N` と書く。実 API・実モデルは起動しない。

## Review Focus（コメントOnly変更で人が踏みやすい失敗モード。新規テストは F/L のため追加せず、実行検証で確かめる）

1. コメント編集のつもりで agent / role / workflow の値・並び・`schema_version` を壊す → Task 1 の `git diff` 目視 + AW との parse 比較 + check/list で確かめる。
2. AW 固有の事実を CRW にそのまま写し、もっともらしいが誤ったコメントを残す（inspect の #616 出自節）→ D9 で削除済み。Task 2 の差分レビューで確認。
3. TOML 構文を壊す（引用符・行継続）→ check/list の parse が拒否する。
4. CRW 固有の文書（Ollama / alibaba / piaq の key 導出・tier・duplicate_model、codex 拒否注記）を失う → Task 1 の diff が保持対象行に触れないことを確認。
5. README の移行記述が実個人設定と矛盾する → 着手時に旧名参照なしを確認済み。Task 1 の実効 check/list で裏付け。

## 受け入れ基準（Spec と同一。実装担当・レビュー担当双方に渡す）

- **動作環境**: Ubuntu Dev Container、uv / Python の既存 locked 環境。リポジトリルート（worktree）から検証コマンドを実行できること。実 API・実モデルは起動しない。
- **実入力**: `.devcontainer/agent-runner.toml` の日本語複数行 TOML コメント、AW 現行ファイル（blob `69e841dd`）、旧名参照の無い実個人設定（`schema_version = 1` とコメント例のみ）、SESSION の空の一時 config。
- **防御範囲**: 実個人設定・key・ログイン・履歴・#408 の値（Ollama 定義・exec・key 導出）を変更しない。alias と自動移行は対象外。`check` の成功を認証や実サービス起動の成功と表示しない。`[workflows.issue.assignments.implement]` の `self`・`after_run` の `--project .`・`env` の `OPENCODE_API_KEY` を変えない。過去の Spec・Plan・レビュー記録の agent 名を書き換えない。agent / role / workflow の値・並び・`schema_version` を変えない。
- TOML のコメントが AW 原文を基本に揃い、CRW の差異（実ファイル名・参照規約・#337 経緯・codex 拒否注記・install_beforehand 説明・AW 固有の出自記述の削除）には理由がある。Ollama / alibaba / piaq のコメントと値は base から変わらない。
- `agy_*` agent は追加されず、README に追加しない理由がある。
- README の移行節の環境記述が現行の個人設定（旧名参照なし）と一致する。命名表・既定割当・Ollama 節は変わらない。
- 雛形単独（空 config）と実効（実個人設定）の `check`・`list` が成功し、既定割当に `duplicate_model` が無い。旧 Opus 名への現行参照が履歴・移行説明以外に無い。
- Issue 指定の検証コマンドが成功する。新規固定値テストは追加しない。
- ボードの子なので PR は `Refs #365` とし、マージ後に完了状態を記録する（この run はマージしない）。

## Task 1: TOML コメントの文面揃えと README 更新

**Files:**
- Modify: `.devcontainer/agent-runner.toml`（コメント行のみ）
- Modify: `.devcontainer/README.md`（移行節の環境記述 1 行 + 命名節に agy 注記 1 段落）

**Interfaces:**
- Consumes: AW 現行コメント原文（SESSION の `aw-agent-runner.toml`）、Spec の設計節 1–9 と D9。
- Produces: 値・並び不変でコメントだけ AW に揃った TOML と、現行個人設定に一致する README。Task 2 の検証がこの成果物を対象にする。

**テストの要否: 不要。** コメント文面は F（固定値）。値・並びは変えず、S の duplicate_model・env 境界は既存テストが守る。代わりの検証: 雛形単独・実効の check/list、AW との diff 比較、既存 pytest（Task 2）。

- [x] **Step 1: TOML のコメント 9 ブロックを AW 原文を基本に置き換える（値・並び・schema_version は触れない）**

  各ブロックの確定文面（AW の Issue 参照は `usaturn/agent-workspace#N`。Ollama / alibaba / piaq のコメントと全 agent / role / workflow の値・並びは変更しない）:

  冒頭（現行 6 行 → 4 行）:
  ```
  # 汎用の非対話エージェント実行ツール。資格情報の値は書かない。
  # agent 名の規則: .devcontainer/README.md「agent の命名と同一モデルの比較」を参照。
  # 個人設定 ~/.config/agent-runner/config.toml はこの雛形に重ねて読む。install_beforehand.bash は、個人設定が無いときに
  # agent-runner-personal.toml を置き、この雛形は写さない。
  ```
  Devin（2 行）:
  ```
  # Devin の SWE-2 は tier（medium・high・max）を --model の UID で選ぶ。tier は effort の軸なので名の effort の段に置く。
  # 2 つは同じ model_key で同じモデルとして扱う（同じ役割に並べられない）。
  ```
  roles 期限（2 行）:
  ```
  # 役割の期限（usaturn/agent-workspace#616）。pr-review の全体予算に合わせて 45 分とし、implement だけ 90 分にする。
  # fix-check は呼び出し側（review-verify の dispatch.py・review-fix-planning の run_roles.py）が 1800 秒に切り詰める。
  ```
  spec-review（3 行）:
  ```
  # issue-to-pr の `--spec-review AGENT` を書いた run だけ、Spec を保存した後・Plan の前に Spec をレビューする役割（usaturn/agent-workspace#848・#853）。ファイルを書かない。
  # 担当は引数で決まり、雛形に割り当ては置かない（個人設定に fallback を書くときは同じ節に agents も書く。agents は引数で置き換わる）。
  # xhigh の reviewer が既存のコードを確かめながら読む時間を見て 30 分とする（期限切れは issue-to-pr の run の停止になる）。
  ```
  design-review（3 行）:
  ```
  # issue-to-pr の `--design-review AGENT` を書いた run だけ、Spec を保存した後・Spec レビューと Plan の前に、設計の妥当性と別案をレビューする役割（usaturn/agent-workspace#861）。ファイルを書かない。
  # 担当は引数で決まり、雛形に割り当ては置かない（個人設定に fallback を書くときは同じ節に agents も書く。agents は引数で置き換わる）。
  # 期限は Spec レビューと同じ 30 分とする（期限切れは issue-to-pr の run の停止になる）。
  ```
  after_run（2 行 → 1 行。`--project .` の値は維持）:
  ```
  # PR レビューの後処理。ランナーの観測値を実行記録へ追記する。
  ```
  inspect（3 行 → 5 行。D9 で AW 4 行目の出自節を削除）:
  ```
  # workflow の割り当て既定値（usaturn/agent-workspace#565）。
  # review の inspect（レビュアー）は固定しない。依頼ごとに --assign inspect=agent-a,agent-b で選ぶ。
  # いつも使う構成は、個人設定のこの節の agents を書き換える。
  # 下の 3 人は指定が無いときの既定値で、性能の順位ではない。
  # Command Code GOAT は契約終了のため既定から外す（#337）。
  ```
  issue.implement（4 行 → 5 行。`self` の値は維持）:
  ```
  # issue-to-pr が Plan の Task を 1 つずつ実装させる担当（usaturn/agent-workspace#679）。レビュー修正の fix.implement とは別に選ぶ。
  # 既定は self。issue-to-pr を実行しているセッション（司令塔）が自分で実装し、runner を起動しない。
  # 外部の担当に任せるときは、個人設定のこの節の agents を書き換え、代わりの候補を fallback に明示する。
  # その回だけ変えるときは /issue-to-pr <Issue> --implement <agent> と書く（fallback は保つ）。
  # agents は 1 つだけ。
  ```
  fix.assignments（2 行保持。参照 `#116` だけ `usaturn/create-reso-world#116` に直す）:
  ```
  # review-fix-planning の run_roles.py が使う担当（usaturn/create-reso-world#116 のボードの D-13）。self は司令塔が自分で実行する。
  # self-review・fix-check には codex の担当を割り当てられない（run_roles.py が起動の前に拒否する）。
  ```

  > 訂正（2026-11-14）: 上の fix.assignments の参照は `usaturn/create-reso-world#116` が正しい。PR #437 の実行時は `usaturn/agent-workspace#116` と記載しており、本訂正で直した。

- [x] **Step 2: README を 2 か所更新する（命名表・既定割当・Ollama 節は変えない）**

  - 移行節の「この環境の既存個人設定は旧名の参照だけを持つため、マージ後に利用者による移行が必要であり、本変更では触らない。」を次に置換:
    「この環境の個人設定は #365 残作業の着手時（2026-11-14）に旧名の参照・定義が無いことを確認済み（agent-runner-personal.toml の例コメントのみ）で、移行は不要。」
  - 命名節の「このほか、Claude Code 用の exec を呼ぶ雛形 agent として…」の段落（「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」にある。で終わる段落）の後に次を追記:
    「usaturn/agent-workspace の雛形には Antigravity CLI（runtime `agy`）の agent があるが、本リポジトリには追加しない。#365 の範囲は新しい agent の追加を含まず、agent_runner に agy adapter が無い（agy CLI 自体は「導入ツール一覧」にある）。」

- [x] **Step 3: 検証（worktree を cwd に。実 API は呼ばない）**

  - 雛形単独: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config "$SESSION/empty-config.toml" check` と `list`。Expected: exit 0、duplicate_model 無し。
  - 実効: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml check` と `list`（実個人設定を重ねる。読み取り専用）。Expected: exit 0。
  - AW 現行との `diff -u "$SESSION/aw-agent-runner.toml"` で、残る差分がすべて Spec の「揃えない差分」であることを確認する。
  - `git diff -- .devcontainer/agent-runner.toml` で、変更がコメント行のみ（値・並び・schema_version 不変）であることを確認する。

- [x] **Step 4: commit（明示パスのみ stage）**

  ```bash
  git add .devcontainer/agent-runner.toml .devcontainer/README.md
  git commit -m "chore: agent-runner.toml のコメントを AW 現行の文面に揃える (#365)

  Co-Authored-By: Claude Code <noreply@anthropic.com>"
  ```

## Task 2: 回帰検証と最終レビュー

**Files:** なし（検証のみ）。

**テストの要否: 不要**（既存テストの実行）。

- [x] **Step 1: 回帰検証（worktree cwd）**

  - `uv run pytest tools/agent_runner/tests` → Expected: 305 passed / exit 0。
  - `bash .devcontainer/test-install-beforehand.bash` → Expected: PASS / exit 0。
  - `bash scripts/check-layout.sh` → Expected: PASS / exit 0。
  - `git diff --check` → Expected: exit 0。
  - `git grep -n -E 'claude-code_opus_default|pi_openai-codex_gpt6-sol_max' -- .devcontainer/agent-runner.toml .agents/skills/review-fix-planning/` → Expected: 空（README の履歴・移行節は許可）。

- [x] **Step 2: 最終のブランチ全体レビュー（別 context。`--merge` が無いので省かない）**

  受け入れ基準・防御範囲を渡し、値・並び・schema_version 不変、コメントの AW 整合、揃えない差分の理由、README 更新、agy 不在を確認させる。追加実行は具体的な不具合の疑いに対する絞った確認に限る。

- [x] **Step 3: 検証の記録**

  最終検証の HEAD・clean 状態・各コマンドの argv と終了コード・ログの完全パスを SESSION に記録する。

## 実行予算

- Issue 全体の能動時間: 0.5〜1.5 時間（小変更）。phase 目安: Spec/Plan 0.3h、Task 1 実装 0.3h、Task 2 検証・レビュー 0.4h、PR 0.2h。
- worker 期限: inline 実装のため runner 期限は使わない。検証コマンドは同期実行し完了を待つ。
- 再試行の上限: 検証失敗の調査・修正は 2 回まで。解消できなければ systematic-debugging で調べ、止まる。
- checkpoint: Task 1 commit 後、Task 2 検証後、PR 作成前。
- 縮小・切り出し・方法変更: 範囲はコメントのみで縮小余地は小さい。AW との差分に予期しない値の差が見つかった場合は、値を変えず Spec の「揃えない差分」に理由を記録するか、意味が変わるなら停止して利用者裁定を待つ。

## contingency（代替策）

- AW 現行と差分表が食い違う（新しい agent・値の差）場合: 仕様の意味（除外範囲）を保つ最小修正で進め、判断と根拠を Spec・ledger に記録する。意味が変わる場合は利用者の裁定を待つ（Issue「エージェントに任せる事項」）。
- check/list が失敗した場合: systematic-debugging で原因を調べる。コメント編集が値を壊していないか `git diff` で確認する。実個人設定起因なら実個人設定は変更せず、原因を報告して止まる。
- 検証が解消できない場合: 止まって報告する（成功扱いにしない）。
- 既存の停止条件・安全境界（防御範囲）は維持する。
