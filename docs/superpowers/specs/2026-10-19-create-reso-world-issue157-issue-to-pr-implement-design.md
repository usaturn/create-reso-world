# Issue #157: issue-to-pr に `--implement`（Plan の Task を runner の担当に依頼する）を入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/157（親 #116、ボード `review-automation-board`、子のキー `issue-to-pr-implement`）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-19-create-reso-world-issue157-issue-to-pr-implement.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-157-issue-to-pr-implement`（branch `feat/issue-157-issue-to-pr-implement`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可:
  1. 2026-10-19（JST）、利用者が `/issue-to-pr #157` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #157`）まで行う
  2. 同じ日の作業中（この Spec を書く前）に、利用者が「`/issue-to-pr #157 --merge` 相当で進めて」と指示した。D-157-13 のとおり、PR の作成後のレビュー修正のサイクルと、修正不要と確かめられたときのマージ・関連 Issue の更新までを許可された範囲とする
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 予約: `refs/heads/agent-claims/issue-157`（SHA `36c163d4419705386e0d96850889112f0be6b541`、セッション `272e7149-b69e-4212-9317-8709431161da`、2026-10-19T10:51:19Z）。記録: https://github.com/usaturn/create-reso-world/issues/157#issuecomment-6265511121
- 基準: 移植先 `origin/main` の `8083a85`、移植元 usaturn/agent-workspace の `a47b2065`（#116 の基準）。基準の後に移植元で `implement_task.py`・そのテスト・`resolve_issue.py`・`SKILL.md` を変えたコミットは無い（2026-10-19 に GitHub の API で確認）
- 方針: #116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」に従う。この子に関係するのは、`tools/workspace`・`projects.toml` を入れず、`resolve_issue.py` は #114 の版を土台にすること。D-157-13 のサイクルでは、移植先の review-fix-planning の判断基準（現行 HEAD で到達できる致命的な指摘だけを直す）、三択の結論、修正後の自己レビューは最大 1 回を保つ
- builder check（brainstorming の読み合わせ、2026-10-19、model sonnet）の 5 点は、どれも既存の規則と移植元から決められたので、エージェントの判断として書き込んだ。実機の確認が通らないとき → D-157-11・D-157-13 の停止条件、レビュアーの起動と一部の失敗 → D-157-13 のサイクルの細部、修正の後の検証・`origin/main` が進んだとき・マージの方法 → 同、外部のリポジトリ → D-157-14、予算の総量 → Plan の「実行予算」（600 分）。利用者に確かめる必要のある点は無かった

## 意図

`/issue-to-pr <Issue> --implement <agent>` で、Plan の Task を agent-runner の担当（別のモデル）に 1 つずつ依頼し、feature worktree に取り込めるようにする。担当は agent-runner の `workflows.issue` の `implement` で決まり（雛形 < 個人設定 < `--implement`）、雛形の既定は `self`（今までどおり、このセッションが自分で実装する）。移植元の `implement_task.py`（agent-workspace #679・#696・#702）と SKILL.md の節を、移植先の構成（`PARENT_ROOT`、`.worktrees/`、`AGENTS.md` の「リポジトリ境界」）に合わせて取り入れる。`--merge` は #158 が入れる。

## 確認した事実（2026-10-19）

- 先行 #150 は `completed` で close、PR #173（`1335f41`）は `main` に含まれる。#157 に open PR・予約・worktree・branch は無かった
- 移植先の `tools/agent_runner` の、`implement_task.py` が使う API（`Config`・`ConfigError`・`RunnerError`・`Workflow`・`load_config`・`resolve_config_path`・`run_workflow`、`adapters.Adapter`・`load_adapter`、`config.validate_config`、`environ.literal_environ`、`models`、`workspace.CheckoutAuditError`・`require_auditable_checkouts`）は移植元と同じ。違いは、runner の DSH の扱い（書き込みの例外の文、DSH の agent が設定にあるときは出力先が正規化したパスであること）と `grok-build` の除外だけ
- 雛形 `.devcontainer/agent-runner.toml` には `[roles.implement]`（`writes = true`、5400 秒、`json`）があり、`[workflows.issue]` は無い。個人設定 `~/.config/agent-runner/config.toml` は、雛形のレビュアーに `pixg` を足したもので、`[workflows.issue]` は無い
- `tools/test_support` に `outside_runner`（`plugin.py`）と `FINDING_CONTENT`（`texts.py`）がある。テストは `pytest_plugins = ("tools.test_support.plugin",)` で読み込む
- 現行の `resolve_issue.py` は `FUTURE_OPTIONS` に `--implement` を含め、どのオプションも終了コード 2 で止める。`uv run --no-project` で動き、pydantic を使わない
- runner は起動の前に、対象のリポジトリに登録された全 worktree を監査する（`require_auditable_checkouts`）。2026-10-19 の時点で、親の checkout には消えた worktree の登録（`/tmp/pr-review-182-177dc8a7/worktree`、prunable）が 1 件あり、親の checkout を対象にした `implement_task.py run` は `checkout_audit` で起動の前に止まる
- DSH の隔離（`dsh_sandbox.py`）は `/tmp` を tmpfs に差し替え、ルートを読み取り専用にして、依頼の worktree などだけを書けるようにする。linked worktree の git の管理領域（共通の `.git`）は書けない側にあり、codex の `-s workspace-write` でも同じことが起きうる。移植元は、担当が commit できないときに helper が commit する経路を持つ
- 既存のテストのうち、fixture の git が `GIT_*` を引き継ぐものは #166（open）が扱う。`.agents/skills/issue-to-pr/tests/test_resolve_issue.py` も候補に入っている

## 設計

### 担当の決定と入口

1. `resolve_issue.py` が利用者の引数から `--implement` の値を取り出し、出力の JSON の `implement`（値か `null`）に入れる
2. issue-to-pr は、`--implement` の有無に関係なく、worktree を作る前に `implement_task.py check [--implement <値>]` を実行する。`check` は雛形 < 個人設定 < `--implement` で設定を読み、`workflows.issue` の `implement` だけを残して検査し、`assignment`（`agents`・`fallback`）と `self` を返す。worktree・runner・GitHub には触れない
3. `self` が true なら、今までどおり 4 章の 4 の表で実行方式を選ぶ。false なら、各 Task の実装を runner の担当に依頼する

### Task の依頼・判定・取り込み・後片付け（`implement_task.py`）

| サブコマンド | 役割 |
| --- | --- |
| `check` | 設定の検査だけ。終了コード 0 か 2（`status: error`、`reason`） |
| `run` | 依頼の JSON（`TaskRequest`）の Task 1 つを、runner の workflow `issue` の `implement` で依頼する（concurrency 1）。停止の確認の後、成功した試行の worktree を git で読み、取り込めるかを判定する（`verdict`）。取り込みはしない。記録は `RUN_DIR/task.json` |
| `accept` | `task.json` から判定を今の状態でやり直し、`importable` なら（担当が commit していなければ helper が `commit_message` で commit してから）feature worktree に `--ff-only` で取り込む。確認に反したら終了コード 1（`status: refused`）で、feature worktree を動かさない |
| `cleanup` | 停止を確認した試行の worktree の登録を外し（force しない）、何も残らなければ `RUN_DIR` を消す。残したものがあれば終了コード 1（`retained`） |

- `TaskRequest` は 6 項目（`repository`・`revision`・`task`・`allowed_files`・`commit_message`・`prompt`）。`repository` は feature worktree（linked worktree）の root で、HEAD が `revision`、未 commit の変更が無いこと
- 担当が返す `TaskResult` は 7 項目（`status`・`commit`・`changed_files`・`commands`・`concerns`・`incomplete`・`retained_paths`）。形に合わない結果は runner の `payload_check` で `invalid_result` になり、`fallback` の次の候補を試す
- `verdict` は `importable`・`no_changes`・`retry`（`BLOCKED`・`NEEDS_CONTEXT`）・`rejected`・`failed`。報告を信用せず、worktree の HEAD・未 commit の変更・`revision` からの範囲のどの commit が触ったパスかを git で読み、担当ファイル（`allowed_files`）の外、merge commit、`revision` の子孫でない commit、`outside_changes` を拒む
- `RUN_DIR` は `PARENT_ROOT/tmp/agents/` の下に置く。DSH の隔離（bubblewrap）は `/tmp` を差し替えて起動するので、`/tmp` の下では失敗する（#157 の本文、移植元の SKILL.md）
- 失敗を理由に、このセッションが `self` で引き取らない。止まった Task の後の Task・最後の全体レビュー・PR には進まない

### `resolve_issue.py`

- `--implement AGENT`・`--implement=AGENT` を、Issue の参照の前でも後でも 1 回だけ受け付ける。値は runner の agent 名の形（`[A-Za-z0-9][A-Za-z0-9_.-]*`、`tools/agent_runner/models.py` の識別子と同じ）に限る
- 値が無い・空・形に合わない・2 回以上の指定は、Issue を読む前に終了コード 2。`FUTURE_OPTIONS` から `--implement` だけを外し、`--merge` などはこれまでどおり「#116 で入れる予定」で止める
- 出力の JSON に `implement` を足す。ほかの項目は変えない。#158 は同じ語の並びの解析にループ用のオプションを足し、`merge` を出力に足す

### 雛形

`.devcontainer/agent-runner.toml` の最後に `[workflows.issue.assignments.implement]`（`agents = ["self"]`）を足す（#116 の D-12・D-13）。無いと `check` が `invalid_reference` で止まる。

### SKILL.md

- 1 章: 「オプションは受け付けない」を、`--implement` だけを受け付け、`--merge` などは止まることに書き換え、`--implement` の節を足す
- 2 章の 3: 出力の項目に `implement` を足し、続けて `implement_task.py check` を実行して、`assignment`・`self` を Spec の決定記録に写すこと、終了コード 2 なら止まることを書く
- 4 章の 4: 実行方式の表に、`self` が false の行を足す
- 4 章: 「Task の実装を runner の担当に依頼する（`self` 以外のとき）」の節を足す（出力先、依頼の JSON、依頼、`verdict` ごとの操作、確認とレビュー、依頼ごとの記録と後片付け、`run` の終了コード 2、`self` で引き取らないこと、PR 本文に書くこと）
- 「停止時の報告」に、`check` の終了コード 2、依頼の `failed`、再試行の上限に達した `retry`・`rejected`、残したもののパスを足す
- 「ランタイムごとの違い」と frontmatter の `argument-hint` に `--implement` を足す

### テスト

- `tests/test_implement_task.py`: `check` を一時の TOML で実際に起動する（既定の `self`、`--implement` の置き換えと `fallback` の保持、個人設定の上書き、拒否）、実際の雛形で `self` になること、`TaskRequest`・`TaskResult` の自前の検査、`allowed`、終了コード
- `tests/test_implement_task_run.py`: 本物の一時 Git リポジトリと linked worktree で、偽の担当（runner の worktree でファイルを書き・消し・commit する Python）を runner で起動し、判定・`accept`・`cleanup` を確かめる
- `tests/test_resolve_issue.py`: `--implement` の受け付け・拒否と、`resolve_issue.py` → `implement_task.py check` の 2 段

### 評価（evals）

`evals/scenarios.json` に `--implement` の場面を足し、変更前（`origin/main` の SKILL.md）と変更後で、Claude Code の Agent ツールのサブエージェント（model `sonnet`）に各 3 回答えさせ、`evals/validation.md` に記録する（writing-skills の振る舞いの比較）。

### 実機の確認

使い捨ての対象（`PARENT_ROOT/tmp/agents/issue-157.*/live/` に作る小さな Git リポジトリと、その linked worktree を feature worktree にしたもの）で、小さな Plan の 1 Task を `--implement codex` で `run` に依頼し、`importable` なら `accept` で取り込み、関連テストを実行し、`cleanup` で片付ける。使い捨てのリポジトリは remote を持たない。結果を #157 に記録する。

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-157-1 `implement_task.py` は移植元のまま写す**
  - 選択: 移植元の `implement_task.py` を変えずに写す（`check`・`run`・`accept`・`cleanup`、`TaskRequest`・`TaskResult` の形、担当への依頼の文）
  - 別案: 移植先に合わせて書き直す、機能を減らす
  - 理由: 移植先の runner の API が同じで、変える箇所が無い。#116 の「移植元の名前と形は移植のために変えない」
- **D-157-2 helper の起動は `uv run --project "$PARENT_ROOT" --locked`**
  - 選択: `uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/implement_task.py" <サブコマンド>`。`resolve_issue.py` は今までどおり `--no-project`
  - 別案: 移植元の `--project "$PARENT/tools/devenv"`、`implement_task.py` も `--no-project`
  - 理由: #116 の D-7（環境はルートの `pyproject.toml`）。`implement_task.py` は pydantic と `tools.agent_runner` を使う。`resolve_issue.py` は依存を増やさない
- **D-157-3 `resolve_issue.py` は #114 の版に `--implement` を足す**
  - 選択: 「設計」の `resolve_issue.py` のとおり。値を agent 名の形に限る
  - 別案: (a) 移植元の版（pydantic・`tools.workspace`・ループ用のオプションの表）を写す、(b) 値の形を確かめない（移植元と同じく、値なし・空・重複だけを拒否）
  - 理由: (a) は #116 の注意書き（`tools/workspace` を入れない）と #158 の範囲に触れる。(b) は値がそのまま次のコマンドの引数になるので、シェルの特殊文字を含む値を通す。agent 名の形は runner の規則なので、正しい名前を拒まない。最終の判断（設定にある agent か）は `check` が行う
- **D-157-4 `--implement` の無い run も `check` を実行する**
  - 選択: 移植元と同じく、`--implement` の有無に関係なく worktree の前に `check` を実行し、`self` が true なら今までどおり自分で実装する
  - 別案: `--implement` があるときだけ `check` を実行し、無ければ `self` とみなす
  - 理由: 担当は雛形 < 個人設定 < `--implement` で決まる（#116 の D-13、移植元）。別案では、個人設定で担当を選んだ利用者の指定を落とす。既定の雛形と今の個人設定では `self` になるので、`--implement` の無い run の実装の方法は変わらない（受け入れ条件 2）
  - 既知の制限: 個人設定が壊れていると、`--implement` の無い run も worktree の前で止まる（runner を使うほかの入口と同じ）
- **D-157-5 雛形の既定は `self`**
  - 選択: `[workflows.issue.assignments.implement] agents = ["self"]` を雛形の最後に足す
  - 別案: 足さない
  - 理由: #116 の D-12・D-13。無いと `check` が `invalid_reference` で止まり、`--implement` の無い run も止まる
- **D-157-6 SKILL.md は `--implement` に関わる箇所だけを変える**
  - 選択: #116 の表の 2 つの節（1 章の `--implement`、4 章の「Task の実装を runner の担当に依頼する」）を足し、`--implement` を入れると古くなる箇所（1 章の「オプションは受け付けない」、2 章の 3、4 章の 4 の表、「停止時の報告」、「ランタイムごとの違い」、`argument-hint`）に、`--implement` に関わる語句だけを足す。#158 の担当の箇所（`--merge`）は変えない
  - 別案: 2 つの節だけを変える
  - 理由: 2 章の出力の説明・4 章の表・停止の列挙が古いままだと、担当の検査と実行方式の選択が文面とずれる。移植元の評価では、表の行が無い版は `self` を「委譲できない」と読んで実行方式を誤った
- **D-157-7 移植元の SKILL.md から変える点**
  - 選択: repository-ownership・`projects.toml`・`.claude/worktrees/`・`ci_required` を、移植先の `AGENTS.md` の「リポジトリ境界」・`.worktrees/`・2 章の表に置き換える。`--merge`・ループ用のオプションとの組み合わせの説明は #158 に回す。`RUN_DIR` は `agent_tmp.py mkdir issue-<N>-implement` で作るセッションディレクトリの下に置く。`run` の終了コード 2 のうち `checkout_audit` は、並んだ登録を報告して止まり、自分で prune・削除しないことを足す
  - 別案: 移植元の文をそのまま写す
  - 理由: 移植元の前提（`projects.toml` など）は移植先に無い。`checkout_audit` は 2026-10-19 に親の checkout で実際に起きる状態で、片付けは他の作業の領域に触れる
- **D-157-8 テストは「テストの採用基準」に合うものだけを移植する**
  - 選択: 移植元の 2 つのテストのモジュールを写し、pydantic の型・必須・`Literal`・`min_length`・strict・`extra` だけを確かめる場合を除く（`TaskResult` の不正な形は、`test_implement_task_run.py` が同じ入力で runner の `fallback` の挙動として確かめる）。自前の検査（完全な小文字の SHA、1 行の task、正規化した相対パス、空でない prompt・commit_message、絶対パスの repository）、`check` の起動、runner の経路・`accept`・`cleanup` は残す。実際の雛形で `self` になるテストは、「`--implement` の無い run は runner の担当を起動しない」を守るために残し、理由をテストに書く
  - 別案: 全部写す、書き直す
  - 理由: `AGENTS.md` の作らない型 5、Issue の「基準に反するものは写さない」
- **D-157-9 新しいテストのモジュールは git の環境を隔離する**
  - 選択: `test_implement_task_run.py` に、`GIT_*` を外し `GIT_CONFIG_GLOBAL=/dev/null`・`GIT_CONFIG_NOSYSTEM=1` にする autouse の fixture を置く（`review-verify/tests/test_dispatch.py`・`pr-review/tests/conftest.py` と同じ形）。`test_resolve_issue.py` の既存の fixture は変えない
  - 別案: 移植元のまま隔離しない、`test_resolve_issue.py` も直す
  - 理由: linked worktree の `git rebase --exec` が `GIT_DIR` を export すると、fixture の git が実リポジトリを書き換える（#166 で再現済み）。新しいモジュールでこの不具合を増やさない。既存のモジュールは #166 の範囲
- **D-157-10 振る舞いの比較は Claude Code の sonnet で行う**
  - 選択: 移植元の評価（`implement_assign`・`rundir_cleanup`）を移植先の形にした場面を `scenarios.json` に足し、変更前・変更後を各 3 回
  - 別案: 移植元と同じく Pi で評価する
  - 理由: 移植先の既存の評価（#114・#139）が Claude Code の sonnet で行っている
- **D-157-11 実機の確認は使い捨ての対象で、担当は `codex`**
  - 選択: 「設計」の「実機の確認」のとおり。依頼は最大 2 回。1 回目が `importable` → `accept` → `cleanup` まで通らなければ、もう 1 回だけ依頼し直す（担当の振る舞い（`BLOCKED`・`rejected` など）なら同じ `codex` に、`codex` が動かない（認証待ち・起動の失敗）なら `pi-deepseek` に）。2 回とも通らなければ、受け入れ条件 4 は未達として、PR は作るがマージしない（D-157-13 の停止条件）。正しく `rejected` と判定したことは、受け入れ条件 4（取り込み）の代わりにしない
  - 別案: (a) この PR の Task を runner に依頼する、(b) 親の checkout の別の Issue で行う、(c) 担当を `claude-opus`・`pi-deepseek` にする
  - 理由: (a)(b) は親の checkout が対象になり、消えた worktree の登録（他の作業の残り）で `checkout_audit` が止まる。片付けは他の作業の領域を変えるので、この子の範囲外。使い捨ての対象なら、親の登録・GitHub に触れずに、runner の起動・判定・取り込み・後片付けを本物の担当で通せる（#116 の D-21）。担当は Issue の受け入れのとおり DSH 以外で、移植元の実機の確認の意図（Claude 以外の担当）に合わせて `codex` にする（#150 で起動を確認済み）。`--config` を使わず、実際の雛形と個人設定と `--implement codex` で決まる経路を通す
- **D-157-12 この Issue の実装の方式は inline（`superpowers:executing-plans`）**
  - 選択: 自分で実装する。サブエージェントは、この Spec の builder check、振る舞いの比較、PR のレビュー（D-157-13）にだけ使う
  - 別案: `superpowers:subagent-driven-development`
  - 理由: 中心は移植元のコードの写しと移植先の API との照合で、その文脈（移植元のコード・テスト、runner の差分、テストの採用基準の判断）は既にこのセッションにある。Task は `resolve_issue.py` の出力 → SKILL.md → evals → 実機と 1 本の流れでつながり、子に文脈を渡しきれない（issue-to-pr の 4 章の 4 の表の条件）
- **D-157-13 「`--merge` 相当」は、PR の作成後のレビュー修正のサイクルとマージ**
  - 選択: 利用者の「`/issue-to-pr #157 --merge` 相当で進めて」を、移植元の `--merge`（PR の作成後にレビュー修正のループを回し、修正不要と確かめられたらマージと関連 Issue の更新まで進む）に当たる指示として扱う。ループの部品（#155 の `run_roles.py`・`finalize.py`、#156 の pr-review-fix-loop、#158 の `--merge`）はまだ無いので、既存のスキルで手で回す。1 サイクルは、既定のレビュアー（agent-runner の workflow `review` の `inspect`。雛形と個人設定で決まる）がそれぞれ pr-review の非対話の入口で PR 全体をレビューし（DSH は `prepare-parent` の親入力を使う）、`review-fix-planning` が三択で結論し、修正するときは検証・push する。移植元の既定に合わせて、サイクルの上限は 3、利用者の判断が要る指摘は直さずに記録して進める。PR は draft にしない。実装の最後のブランチ全体のレビューは、1 サイクル目のレビューで代える（移植元の `--merge` と同じ）。マージは review-fix-planning が修正不要と結論したときだけ行い、`Closes #157` で #157 を close し、#157・#116 に結果を書く。上限に達したら、修正を push した状態で止まって報告する（マージしない）
  - サイクルの細部（移植元の pr-review-fix-loop の「サイクル」「終わり方」に合わせる）:
    - レビュアーは workflow `review` の `inspect`（2026-10-19 は雛形と個人設定で `pi-gpt`・`devin-swe`・`dsh-ccd`・`claude-opus`・`pixg`）で、役割の期限（2700 秒）のまま。レビュアーには `PARENT_ROOT` の pr-review を読ませる（PR で変えているスキルでレビューさせない。移植元と同じ）。起動は runner の CLI（`run --workflow review`、`--write-exception` は pr-review の `helper_write_exceptions` の値、DSH 向けに `prepare-parent` の親入力をプロンプトに入れる）。プロンプトと親入力はセッションディレクトリに置き、コミットしない
    - 全レビュアーの終了と停止の確認を待つ。受け付けたレビューが 1 つ以上あれば review-fix-planning に進む。runner は成功したが結果を受け付けられなかったレビュアーは、同じサイクルで 1 回だけ起動し直す。runner の失敗（期限切れ・認証待ち・起動の失敗）は起動し直さない。全員の失敗は停止
    - 修正したら、関連テストと README の「テスト」の 3 つを修正後の HEAD でやり直す。SKILL.md の振る舞いに関わる文面を変えたら、変更後の評価を 3 回取り直す。`implement_task.py` の `run`・`accept`・`cleanup` の経路を変えたら、実機の確認を 1 回やり直す。それ以外の変更では実機の記録を引き継ぎ、変更がその前提を変えない理由を書く
    - マージの前に `origin/main` が進んでいれば、`origin/main` を feature branch に merge し（force push しない）、競合は節が分かれていて機械的に解消できるときだけ解消し、全体の検証をやり直してから push する。機械的に解消できなければ止まる
    - マージは `gh pr merge --merge`（merge commit。branch は消さない）。その前に、PR が draft でない、`headRefOid` が検証した HEAD（その後の commit が Spec・Plan の記録だけなら、検証した HEAD からの差分が `docs/superpowers/` だけであること）、マージできる状態であることを確かめる
  - 別案: (a) この版の SKILL.md の「`--merge` は止まる」に従って止まる、(b) 利用者に解釈を確かめる、(c) PR の作成で終える
  - 理由: 利用者は、この版で `--merge` が使えないことを踏まえて「相当で」と明示した。#116 の D-21 と #157 の「反映先」は、利用者の明示の指示があればマージを認める。手順の既定は移植元の `--merge` の既定で決まり、確かめる必要のある未決の判断が無い
  - 停止条件: 安全の失敗、レビュアーの全員の失敗、マージの前の状態の不一致（HEAD が検証したものと違う、PR が draft、機械的に解消できない競合）、review-fix-planning の「停止」、実機の確認の未達（受け入れ条件 4）。予算（Plan の「実行予算」）の 100% で止まって報告する
- **D-157-14 外部のリポジトリでも同じ手順で使える**
  - 選択: `TARGET_REPO` が usaturn/resoloop・usaturn/resoloop-meshy でも、`--implement` を同じ手順で使える。依頼の `repository` は `TARGET_ROOT/.worktrees/<名前>` の feature worktree、`RUN_DIR` は `PARENT_ROOT/tmp/agents/` の下。実機では確かめていないことを validation.md に書く
  - 別案: create-reso-world だけに限る
  - 理由: `implement_task.py` は対象のリポジトリに依存しない（linked worktree の root であることだけを確かめる）。移植元も登録された全てのリポジトリで使える。限る理由が無い

## 受け入れ条件

1. `uv run pytest .agents/skills/issue-to-pr` が通る。`TaskRequest` の `prompt` に `tools.test_support.texts.FINDING_CONTENT`（複数行・CRLF・タブ・非 ASCII）を使う場合を含む
2. `--implement` の無い run は今と同じ（`self`）: `resolve_issue.py` の出力の `implement` が `null`、実際の雛形で `implement_task.py check` が `self: true`、runner を起動しない
3. `resolve_issue.py` が `--implement` を受け付け、`--merge` などはこれまでどおり #116 の理由で止める
4. 実機: 使い捨ての対象で、小さな Plan の 1 Task を DSH 以外の担当（`codex`）に依頼し、`accept` で feature worktree に取り込み、`cleanup` で runner の worktree の登録と出力先を片付ける。担当・観測したモデル・所要時間・`verdict`・取り込んだ commit を #157 に記録する
5. `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` が通る
6. SKILL.md の振る舞いの比較（変更前・変更後）を `evals/validation.md` に記録する
7. D-157-13 のサイクルの結果（各サイクルの結論、マージした場合はマージのコミットと #157 の state）を #157 と PR に記録する

## 防御範囲

- 受け付ける入力: `#N --implement codex`、`--implement codex #N`、`#N --implement=codex`、`#N --implement self`、`--implement` の無い `#N`
- Issue を読む前に終了コード 2: `--implement`（値なし）、`--implement=`、`--implement a --implement b`、`--implement 'x;touch y'`、`--implement --merge`、`#N --implement codex --merge`（#116 の理由）
- `check` の終了コード 2: 設定に無い agent、一次担当が 2 つ、`writes = false`、`result_shape = "text"`、workflow `issue` が無い、役割 `implement` が無い
- `run` の判定: 担当の commit と helper の commit の取り込み、報告と食い違う未 commit の変更、commit の後に残った変更、担当ファイルの外の変更（途中の commit で戻したものを含む）、merge commit、`revision` の子孫でない commit、HEAD と違う `commit`、`outside_changes`、`BLOCKED`・`NEEDS_CONTEXT`、結果の形の誤りと `fallback`、停止を確認できない試行、`self` の拒否、feature worktree が動いた・汚れた・main checkout、非 ASCII・空白のパスと CRLF の依頼、リネーム、ignored のファイル
- 対象にしない: DSH を `implement` に割り当てたときの実機の動作、外部のリポジトリ（resoloop・resoloop-meshy）の feature worktree での実機の確認、`--merge` との組み合わせ（#158）

## 範囲外

- `--merge` とループ用のオプションの解析・SKILL.md の節（#158）
- `tools/`、`.agents/skills/pr-review-fix-loop/`（#156）、review-fix-planning の新しい版（#155）
- 既存のテストの `GIT_*` の扱い（#166）
- 親の checkout の消えた worktree の登録の片付け（他の作業の残り）
- 親 #116 の実行マップ・公開台帳の更新（調整役）

## 実装者に任せること

- テストの関数の分け方と名前、`resolve_issue.py` の内部の構成（出力と拒否の条件は上のとおり）
- 評価の指示文の文面（場面と期待は `scenarios.json` に書く）
- 実機の確認の小さな Plan の中身（1 Task、テストを伴う小さな変更）
