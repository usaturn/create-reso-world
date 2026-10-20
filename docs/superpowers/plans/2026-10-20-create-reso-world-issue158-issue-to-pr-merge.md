# Issue #158: issue-to-pr の `--merge` 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans（inline。Spec の D-158-21）。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/issue-to-pr <Issue> --merge [ループ用のオプション]` で、PR の作成後に PR 修正ループを回し、修正不要ならマージと関連 Issue の更新まで進めるようにし、`FUTURE_OPTIONS` による拒否を無くす。

**Architecture:** `resolve_issue.py` が利用者の引数から `--merge` とループ用のオプションを書いた順に取り出し（`merge.loop_args`）、SKILL.md が worktree の前に `loop.py check-options` で検査し、PR の作成後に `PARENT_ROOT` の `loop.py start` に同じ列を渡す。ループの中の判断・修正・マージは、#156 の pr-review-fix-loop と #155 の review-fix-planning・`finalize.py` のまま。

**Tech Stack:** Python 3.14（`uv run --no-project`、標準ライブラリだけ）、pytest、Markdown の SKILL.md、Claude Code の Agent ツール（評価）。

**Spec:** `docs/superpowers/specs/2026-10-20-create-reso-world-issue158-issue-to-pr-merge-design.md`

- 状態: draft
- 作業場所: `/workspaces/reso-world/.worktrees/issue-158-issue-to-pr-merge`（branch `feat/issue-158-issue-to-pr-merge`、`origin/main` の `d29c93c` から）
- セッションディレクトリ: `/workspaces/reso-world/tmp/agents/issue-158.p1qjczc_`（ledger `budget.jsonl`、ベースラインと検証のログ、評価の回答、移植元の clone `src-aw`）

## Global Constraints

- `resolve_issue.py` は `uv run --no-project` で動く。pydantic・`tools` を import しない
- `FUTURE_OPTIONS` を無くす。拒否はどれも Issue を読む前（`gh` を呼ぶ前）に、終了コード 2、標準出力は空、標準エラー出力は `issue-to-pr:` で始まる
- 出力の JSON の項目は `repo`・`number`・`url`・`title`・`body`・`merge`・`implement`。`merge` は `null` か `{"loop_args": [...]}`
- 受け付けるループ用のオプションは `--max-cycles`・`--assign`・`--template`・`--config` だけ。`--hold-action`・`--fresh-review` は理由付きで拒否
- 変えないもの: `implement_task.py` とそのテスト、`.agents/skills/pr-review-fix-loop/`、`.agents/skills/review-fix-planning/`、`tools/`、SKILL.md の 4 章・2 章の表・`--implement` の節
- テストは `AGENTS.md` の「テストの採用基準」に従う（文書の文言を照合しない）。日本語は `AGENTS.md` の「日本語表現」に従う

## Review Focus

1. `--merge` より前に書いたループ用のオプション（`#42 --max-cycles 2 --merge`）: 受け付けて、書いた順に `loop_args` に入る → Task 1 の `test_merge_arguments_are_passed_in_the_written_order` の場合に入れる
2. `~` を含むパスで、ホームディレクトリを決められない（`~nosuchuser-158/x.toml` のように、存在しないユーザー）: traceback を出さず終了コード 2 → Task 1 の `test_unresolvable_home_is_rejected`
3. `--merge` の後ろに書いた `--implement codex`: ループ用のオプションにならない → Task 1 の `test_implement_is_returned_separately_from_loop_args`
4. 利用者の `--template` がテストの `--template` より後ろに来る 2 段目: 後の値（利用者の存在しないパス）が効いて `check-options` が終了コード 2 → Task 1 の `test_resolve_then_check_options` の場合に入れる
5. 空白を含む引用したパス（`--config '~/c d.toml'`）: 1 つの要素のまま絶対パスになる → Task 1 の `test_template_and_config_become_absolute_from_the_starting_directory`

## 要件の照合（実装前、`convergence.md` の 1）

| Spec の受け入れ条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| 1 issue-to-pr のテストが通る | Task 1 | 全テストが成功 | `uv run pytest .agents/skills/issue-to-pr` |
| 2 `--merge` の無い run は今と同じ | Task 1（出力）、Task 3（SKILL.md） | `merge: null`、ほかの項目は今と同じ。SKILL.md の `--merge` の無い流れが変わらない | 既存の成功の場合のテスト、評価の (mb)、`git diff` で `--merge` の無い流れの文が残ることを読む |
| 3 `--merge` とループ用のオプションの受け付け・拒否、`FUTURE_OPTIONS` が無い | Task 1 | 書いた順の `loop_args`、Issue を読む前の拒否 | Task 1 のテスト |
| 4 `resolve_issue.py` → `check-options` の 2 段 | Task 1（テスト）、Task 4（実環境） | 両方を通る・どちらかで止まる | `test_resolve_then_check_options`、実環境の `#158 --merge` |
| 5 SKILL.md の `--merge` の流れが loop・review-fix-planning と食い違わない | Task 3、Task 4（統合） | 2 章・5 章・停止・ランタイムの記述 | 評価の比較、最後のブランチ全体のレビュー |
| 6 振る舞いの比較の記録 | Task 2（対照）、Task 3（比較） | 対照・比較の各 3 回の判定 | `evals/validation.md` |
| 7 README の「テスト」 | Task 4 | 3 つとも終了コード 0 | 検証の記録 |
| 8 実機のループは未実施と書く | Task 4 | PR と #158 の記述 | PR 本文・#158 のコメント |

共有する条件: 「利用者が書いたループ用のオプションを、書いた順に、足さずに渡す」は Task 1（`resolve_issue.py`）と Task 3（SKILL.md の `check-options`・`start`）にまたがる。Task 4 の統合確認で、テストの `loop_args` と SKILL.md の 2 つのコマンドが同じ列を同じ形（各要素を 1 つの引数）で渡すことを確かめる。

## 実行方式

inline（`superpowers:executing-plans`）。理由は Spec の D-158-21。サブエージェントは、評価（対照・比較）と、最後のブランチ全体のレビューにだけ使う。

## 実行予算

`.agents/execution-budget.md` に従う。ledger は `/workspaces/reso-world/tmp/agents/issue-158.p1qjczc_/budget.jsonl`（2026-10-20 に `start`、予算 360 分）。

1. 全体の能動時間: 360 分。根拠: #157（`--implement`、Task 4 つ、実機の確認と「`--merge` 相当」の 1 サイクルを含む）の予算が 600 分。#158 はループの実機とマージが無く、コードは `resolve_issue.py` だけ
2. phase の目安: 準備（読み・予約・Spec・Plan）90 分 / Task 1 45 分 / Task 2 30 分 / Task 3 75 分 / Task 4（統合・全体レビュー・PR・Issue の更新）75 分 / 予備 45 分
3. worker: 評価のサブエージェント（Agent ツール）は 1 回 15 分ほどを見込み、30 分で回答が無ければ stall として記録する（Agent ツールは task_watch で止められないので、宣言による打ち切りはしない）。検証のコマンド（`run-tests.bash`・`check-layout.sh`・pytest）は止めない。`run_in_background` の完了通知で待ち、10 分ごとにログの mtime を確かめる
4. 再試行の上限: 同じ失敗の再試行は 1 回まで（評価のサブエージェントの無回答、検証の一時的な失敗）
5. checkpoint: 各 Task の境界、予算の 50%（180 分）と 100%（360 分）、worker の失敗の直後
6. 縮小・切り出し・方法変更の候補: 評価の場面を (b)・(w)・(md)・(mf)・(me) に絞る / 比較で外れた場面の文面の直しを 1 回に限り、残りは PR の既知の制限に書く / 最後の全体レビューの指摘のうち致命的でないものは PR に持ち越しとして書く

## contingency

- Task 1 の最初の RED で、`loop.py check-options` の実際の出力や必要な雛形の節が前提と違えば、仕様の意味（書いた順に渡す、意味の検査は `check-options`）を保つ最小限の直しをして、ledger に記録して続ける
- ベースラインの検証（`origin/main` の `d29c93c`、作業前）が失敗していたら、変更の前からの失敗かを切り分けて記録する。変更と関係の無い既知の失敗なら、Task 4 で同じ失敗だけが残ることを確かめる。原因が分からなければ止まる
- 評価のサブエージェントが起動できないときは、1 回だけ起動し直し、それでも駄目なら比較は未実施として記録する（受け入れ条件 6 は未達。PR に書く）

---

### Task 1: `resolve_issue.py` の `--merge` とループ用のオプション

テスト: 要る（入力の解析・Issue を読む前の拒否という安全条件・`check-options` との接続を、スクリプトを実際に起動して確かめる）。

**Files:**
- Modify: `.agents/skills/issue-to-pr/scripts/resolve_issue.py`
- Test: `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`

**Interfaces:**
- Consumes: `loop.py check-options`（#156。`--max-cycles`・`--assign`・`--template`・`--config`。成功は `{"status": "ok", "options", "assignments", "next": null}`、拒否は終了コード 2）
- Produces: `parse_input(text: str, cwd: Path) -> ParsedInput`（`ParsedInput(reference: str, loop_args: list[str] | None, implement: str | None)`）、出力の JSON の `merge`（`null` か `{"loop_args": list[str]}`）

- [ ] **Step 1: テストを書く**

既存のテストを次のように直し、足す（`resolve()`・`assert_rejected()`・`gh_stub`・`checkout` は今のものを使う）。

- `test_resolves_supported_forms_without_changing_git`: 期待の辞書に `"merge": None` を足す
- `test_rejects_options_with_reason` を消し、次に置き換える
- `test_merge_arguments_are_passed_in_the_written_order`（parametrize `(argument, loop_args)`）: 終了コード 0、`payload["merge"] == {"loop_args": loop_args}`、`payload["implement"] is None`、`git status --porcelain` と `git for-each-ref` が変わらない
  - `"#42 --merge"` → `[]`
  - `"#42 --merge --max-cycles 2 --assign inspect=claude-opus,devin-swe --assign implement=self"` → `["--max-cycles", "2", "--assign", "inspect=claude-opus,devin-swe", "--assign", "implement=self"]`
  - `"--merge #42 --max-cycles=2"` → `["--max-cycles", "2"]`
  - `"#42 --max-cycles 2 --merge"` → `["--max-cycles", "2"]`
  - `"#42 --merge --max-cycles 2 --max-cycles 3"` → `["--max-cycles", "2", "--max-cycles", "3"]`
  - `"#42 --merge --max-cycles 0"` → `["--max-cycles", "0"]`（範囲は `check-options` が確かめる）
- `test_template_and_config_become_absolute_from_the_starting_directory`: `HOME` を `tmp_path/"home"` にし、`"#42 --merge --template sub/a.toml --config '~/c d.toml'"` → `["--template", str((checkout / "sub" / "a.toml").resolve()), "--config", str((home / "c d.toml").resolve())]`
- `test_unresolvable_home_is_rejected`: `"#42 --merge --config ~nosuchuser-158/x.toml"`（`Path.expanduser` が `RuntimeError` を出す）→ `assert_rejected`、`gh` を呼ばない、標準エラー出力に `Traceback` が無い
- `test_rejects_malformed_arguments_before_looking_up_issue`（parametrize）: `assert_rejected`、`gh` を呼ばない、`git` の状態が変わらない、`injected` が作られない
  - `"#42 --max-cycles 2"`、`"#42 --assign implement=self"`、`"#42 --template x.toml"`、`"#42 --merge --merge"`、`"#42 --merge=yes"`、`"#42 --merge --max-cycles"`、`"#42 --merge --max-cycles x"`、`"#42 --merge --max-cycles -1"`、`"#42 --merge --max-cycles=٣"`、`"#42 --merge --assign inspect"`、`"#42 --merge --assign 'inspect=a;touch injected'"`、`"#42 --merge --assign =a"`、`"#42 --merge --template"`、`"#42 --merge --template="`、`"#42 --merge --template --config x"`、`"#42 --merge --config 'a\nb'"`（改行を含む）、`"#42 --merge --foo"`、`"#42 --merge -x"`、`"#42 extra --merge"`、`"#41 #42 --merge"`、`"--merge"`、`"#42 --merge --template 'a"`
- `test_refused_options_name_the_option`（parametrize `"#42 --merge --hold-action skip"`・`"#42 --hold-action fix"`・`"#42 --merge --fresh-review"`・`"#42 --fresh-review"`）: `assert_rejected`、`gh` を呼ばない、拒否したオプションの名前（`--hold-action` か `--fresh-review`）が標準エラー出力にある
- `test_rejects_unknown_options`: `"#116" not in result.stderr` の行を消す（`FUTURE_OPTIONS` が無くなるので区別が要らない）
- `test_implement_is_returned_separately_from_loop_args`（parametrize `(argument, implement, merge)`）:
  - `"#42 --implement claude-opus --merge --max-cycles 2"` → `"claude-opus"`、`{"loop_args": ["--max-cycles", "2"]}`
  - `"#42 --merge --max-cycles 2 --implement codex"` → `"codex"`、`{"loop_args": ["--max-cycles", "2"]}`
  - `"#42 --merge --assign implement=self"` → `None`、`{"loop_args": ["--assign", "implement=self"]}`
- `test_resolve_then_check_options`（parametrize `(argument, expected)`、`expected` は（resolve の終了コード、check-options の終了コード））: 一時の雛形（`claude-opus`（claude-code）・`devin-swe`（devin）・`codex`（codex）の agent、4 つの役割、review の `inspect` は `claude-opus`・`devin-swe`、fix は `implement` が `claude-opus`、`self-review`・`fix-check` が `self`）を書き、`[sys.executable, LOOP, "check-options", "--template", <雛形>, *loop_args]` を `AGENT_RUNNER_CONFIG` に存在しないパスを入れて実行する。check-options が終了コード 2 で標準出力があれば `status == "error"`
  - `"#42 --merge"` → `(0, 0)`
  - `"#42 --merge --max-cycles 2 --assign inspect=claude-opus,devin-swe --assign implement=self"` → `(0, 0)`
  - `"#42 --max-cycles 2"` → `(2, None)`
  - `"#42 --merge --hold-action skip"` → `(2, None)`
  - `"#42 --merge --max-cycles 0"` → `(0, 2)`
  - `"#42 --merge --assign inspect=nobody"` → `(0, 2)`
  - `"#42 --merge --assign inspect=codex"` → `(0, 2)`
  - `"#42 --merge --template missing.toml"` → `(0, 2)`
- `test_resolve_then_implement_check` に `("#42 --implement self --merge", (0, 0, True))` を足す

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr/tests/test_resolve_issue.py -q`
Expected: `--merge` を含む場合が失敗する（今の版は「#116 で入れる予定」で終了コード 2）。`merge` の無い成功の場合は `"merge"` の項目が無いので失敗する

- [ ] **Step 3: `resolve_issue.py` を直す**

- `FUTURE_OPTIONS` を消し、ループ用のオプションの集合（`--max-cycles`・`--assign`・`--template`・`--config`）、パスのオプション（`--template`・`--config`）、理由付きで拒否するオプション（`--hold-action`・`--fresh-review` → 理由の文）を定数で持つ
- 値の形: `--max-cycles` は `[0-9]+`、`--assign` は `[a-z][a-z-]*=` の後に agent 名の形（`IMPLEMENT_VALUE` と同じ）をカンマでつないだもの、パスは空でなく制御文字（`\x00`〜`\x1f`・`\x7f`）を含まない。`~` の展開の失敗（`RuntimeError`）は `ValueError` にする
- `parse_input(text, cwd)` は `--merge` の回数、ループ用のオプションの列、`--implement` を集め、`--merge` が無いのにループ用のオプションがあれば拒否する。値が無い（次の語が無い・`-` で始まる）・空は今の `--implement` と同じく拒否する
- `main` は `parse_input(args.input, Path.cwd())` を呼び、出力に `"merge": None if parsed.loop_args is None else {"loop_args": parsed.loop_args}` を `implement` の前に足す。`argparse` の `input` の help の「オプションは --implement AGENT だけ」を直す。docstring の 1 行目も直す

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run pytest .agents/skills/issue-to-pr -q`
Expected: すべて成功

- [ ] **Step 5: Commit**

```bash
git add .agents/skills/issue-to-pr/scripts/resolve_issue.py .agents/skills/issue-to-pr/tests/test_resolve_issue.py
git commit -m "feat(issue-to-pr): parse --merge and the loop options in resolve_issue.py (#158)"
```

### Task 2: 評価の場面と対照（RED）

テスト: 要らない（評価の場面の記述だけ）。代わりに JSON の構文の検査と、変更前の SKILL.md での対照の 3 回。

**Files:**
- Modify: `.agents/skills/issue-to-pr/evals/scenarios.json`

**Interfaces:**
- Produces: 場面の ID（Task 3 の比較と `validation.md` が使う）

- [ ] **Step 1: 場面を直し、足す**

- (b) `b-merge-option` と (w) `w-implement-with-merge` の `expected` を新しい振る舞いに直し、`"changed": "#158 で期待を変えた（--merge を受け付ける）。#158 より前の結果は validation.md の各節"` を足す
  - (b): `resolve_issue.py -- "#202 --merge"` → `merge.loop_args = []` → worktree の前に `PARENT_ROOT` の `loop.py check-options`（引数なし）→ 最後の全体レビューは省かない → PR は draft にしない → `PARENT_ROOT` の `loop.py start <PR の URL> --controller-model <正確な ID> --controller-runtime claude-code`（オプションを足さない）→ pr-review-fix-loop の SKILL.md をファイルとして読んで従い、結果の表で報告
  - (w): `implement = "codex"`、`loop_args = []`。`check-options` と `implement_task.py check --implement codex` の両方を worktree の前に実行。Task は runner の担当に依頼し、PR の作成後にループ
- 新しい場面（`added`: `#158 で追加。方法は (s) と同じ`）
  - (ma) `ma-natural-language-merge`: `/issue-to-pr #43` の後、自然文で「マージまでやっておいて」。PR #90 の作成後 → ループもマージもしない、PR の作成で終え、`/pr-review <PR の URL>` を 1 行で伝える
  - (mb) `mb-loop-options-verbatim`: `/issue-to-pr usaturn/resoloop#7 --merge --max-cycles 2`。usaturn/resoloop の PR #12 の作成直後で CI は実行中 → `check-options --max-cycles 2`、`start https://github.com/usaturn/resoloop/pull/12 ... --max-cycles 2`、既定値を足さない、CI を待たない、文書の PR はループに乗せない
  - (mc) `mc-hold-action`: `/issue-to-pr #44 --merge --hold-action skip` → helper が終了コード 2 で止まり、理由を伝える。`--hold-action` を外して続けない
  - (md) `md-existing-pr`: `/issue-to-pr #45 --merge`、Issue を閉じる open PR #91（base `main`、作ったセッションは不明）がある → 止まって報告、既存の PR をループに乗せない、続けるなら `/pr-review-fix-loop <PR の URL>`
  - (me) `me-meshy-merge`: `/issue-to-pr usaturn/resoloop-meshy#3 --merge` → worktree の前に止まる（ループも `finalize.py` も扱えない）
  - (mf) `mf-cycle-limit`: ループが `fixes_pushed`・`ended_by: cycle_limit`・`merged: false` で終わった → 未完了・未マージ、続けるなら `/pr-review-fix-loop <PR の URL>`、run ID・`<review_dir>/loop/<run_id>/` の完全パス・サイクルごとの結果
  - (mg) `mg-board-child-claim`: ボードの子 #46 を `--merge` で進め、PR を作った → 予約はループの `finish` の後、結果を子 Issue に書いてから解放する（PR の作成の直後に解放しない）
  - (mh) `mh-checks-reuse`: `--merge` の 1 サイクル目で修正不要、サイクルの HEAD は PR の作成時に記録した検証の HEAD と同じ、base は進んでいない → 記録を結論 2 の検証の記録に使ってよい。base が進んでいたら merge の検証は省かない
  - (mi) `mi-input-with-trailing-text`: 引数が `#42 --merge --max-cycles 2 途中で止めずに PR まで` と `--merge #42` → `INPUT` はそれぞれ `#42 --merge --max-cycles 2` と `--merge #42`（並べ替えない）

- [ ] **Step 2: JSON を確かめる**

Run: `uv run --no-project python -c "import json,sys; d=json.load(open('.agents/skills/issue-to-pr/evals/scenarios.json')); ids=[s['id'] for s in d['scenarios']]; assert len(ids)==len(set(ids)); print(len(ids))"`
Expected: 場面の数が表示され、例外が無い

- [ ] **Step 3: 対照を 3 回取る**

変更前の SKILL.md（`git show d29c93c:.agents/skills/issue-to-pr/SKILL.md`）と `AGENTS.md` をセッションディレクトリの `eval/control/` に置き、(b)・(w)・(ma)〜(mi) を 1 つの指示文にまとめて、Agent ツールの新しいサブエージェント（model `sonnet`）を 3 回起動する（Read で 2 ファイルを 1 回ずつ読む以外のツールを使わせない）。回答を `eval/control/answer-{1,2,3}.md` に保存する

- [ ] **Step 4: Commit**

```bash
git add .agents/skills/issue-to-pr/evals/scenarios.json
git commit -m "test(issue-to-pr): add the --merge evaluation scenarios (#158)"
```

### Task 3: SKILL.md の `--merge`（GREEN）と比較

テスト: 要らない（SKILL.md の文面。「テストの採用基準」の書かない型）。代わりに振る舞いの比較 3 回、`bash scripts/check-layout.sh`、リンク先の実在の確認、`git diff` の確認。

**Files:**
- Modify: `.agents/skills/issue-to-pr/SKILL.md`
- Modify: `.agents/skills/issue-to-pr/evals/validation.md`

**Interfaces:**
- Consumes: Task 1 の `merge.loop_args`、Task 2 の場面の ID

- [ ] **Step 1: SKILL.md を直す**

Spec の「SKILL.md の変更箇所」の表のとおり。要点:

- `argument-hint`: `"<Issue> [--implement AGENT] [--merge [--max-cycles N] [--assign ROLE=AGENT[,AGENT]]... [--template PATH] [--config PATH]]"`
- 1 章: 冒頭の「マージはしない」の例外、オプションの段落、`### --merge` の節（`### --implement` の後）
- 2 章の 3: `INPUT` の例（`#12 --merge --max-cycles 2 途中で止めずに` → `#12 --merge --max-cycles 2`）、出力の `merge`、`check-options` の段（`implement_task.py check` の前）
- 2 章の 5: `merge` があり `TARGET_REPO` が usaturn/resoloop-meshy なら止まる
- 2 章の 6: 既存の open PR を `--merge` でもループに乗せない、`/pr-review-fix-loop <PR の URL>`
- 5 章: 検証の記録、draft にしない、CI を待たない、マージの例外、予約の解放の時点、完了の報告。`### --merge のとき: PR の作成後のループ` の節（Spec の 1〜6 と結果の表）
- 停止時の報告、ランタイムごとの違い

- [ ] **Step 2: 構造を確かめる**

Run: `bash scripts/check-layout.sh`
Expected: 終了コード 0。加えて、SKILL.md が参照するパス（`.agents/skills/pr-review-fix-loop/SKILL.md`・`scripts/loop.py`）が実在することを `test -f` で確かめる

- [ ] **Step 3: 比較を 3 回取る**

Task 2 の Step 3 と同じ指示文で、SKILL.md だけを変更後の版にして 3 回起動し、`eval/compare/answer-{1,2,3}.md` に保存する

- [ ] **Step 4: 判定する**

対照・比較の全回答を読み、場面ごとの期待を満たした回数を数える。比較で外れた場面があれば、外れ方に合う形で文面を 1 回だけ直し（writing-skills の「Match the Form to the Failure」）、その場面だけを 3 回取り直す

- [ ] **Step 5: `validation.md` に記録する**

`## --merge（#158）` の節を足す（評価方法と範囲、結果の表、観察、実行した検証、行っていない確認）。#157 の節と同じ形

- [ ] **Step 6: Commit**

```bash
git add .agents/skills/issue-to-pr/SKILL.md .agents/skills/issue-to-pr/evals/validation.md
git commit -m "feat(issue-to-pr): run the PR review-fix loop after the PR with --merge (#158)"
```

### Task 4: 統合確認・全体レビュー・PR

テスト: 新しく書かない。統合の確認と正式な検証。

**Files:**
- Modify: `docs/superpowers/specs/2026-10-20-create-reso-world-issue158-issue-to-pr-merge-design.md`（結果の記録）
- Modify: `docs/superpowers/plans/2026-10-20-create-reso-world-issue158-issue-to-pr-merge.md`（チェックと完了の記録）

- [ ] **Step 1: 共有する条件を確かめる**

SKILL.md の `check-options`・`start` のコマンドが `loop_args` の各要素を 1 つの引数として、足さずに渡すこと、Task 1 のテストの 2 段と同じ列であることを読み合わせる。`convergence.md` の「3. 検証と閉じ方」で、Spec → Plan → Task → 実行の証拠を条件ごとに照合する

- [ ] **Step 2: 実環境の 2 段**

Run（worktree のルートで）:

```bash
uv run --no-project python .agents/skills/issue-to-pr/scripts/resolve_issue.py -- "#158 --merge"
uv run --project /workspaces/reso-world --locked python /workspaces/reso-world/.agents/skills/pr-review-fix-loop/scripts/loop.py check-options
```

Expected: 1 つ目は終了コード 0 で `merge == {"loop_args": []}`、2 つ目は終了コード 0 で `status: ok`。結果をセッションディレクトリに保存する

- [ ] **Step 3: 最後のブランチ全体のレビュー**

`superpowers:executing-plans` の最後のレビューとして、新しいサブエージェントに `origin/main...HEAD` の差分全体と Spec・Plan を渡してレビューさせる。致命的な指摘は直して関連テストをやり直し、致命的でない指摘は PR の持ち越しに書く

- [ ] **Step 4: 正式な検証**

最後の commit の後、作業ツリーが clean な状態で、README の「テスト」の 3 つを実行する（`monitoring-long-tasks` に従い、`run_in_background` の完了通知で待つ）。

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
```

Expected: 3 つとも終了コード 0。HEAD・clean であること・終了コード・ログの完全パスを記録する

- [ ] **Step 5: Spec・Plan に結果を書いて commit**（状態は `draft` のまま）。commit したら Step 4 をその HEAD でやり直すか、変更が `docs/superpowers/` だけであることを `git diff --name-only` で確かめて記録する

- [ ] **Step 6: push と PR**

issue-to-pr の 5 章のとおり、Issue の状態と競合を確かめ直し、`scan-before-push.sh` で検査した SHA を push し、`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-158-issue-to-pr-merge`（draft にしない）。本文は `Closes #158`、変更概要、Spec の決定と理由、実行方式と理由、検証と結果、既知の制限、実機のループを行っていないこと、作業時間と Task 別の内訳

- [ ] **Step 7: #158 の状態と予約の解放**

#158 に状態（planning: ready / implementation: in-progress、PR の URL、検証）と、Spec・Plan の manifest（PR の branch の commit から新しいディレクトリへ取り出して SHA-256・バイト数を照合したもの）を書き、予約を `--force-with-lease` で解放して ref が無いことを確かめる

## 完了

（Task 4 の後に、検証の結果、作業時間と Task 別の内訳、残したパスを書く）
