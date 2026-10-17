# Issue #114: issue-to-pr スキルとモデルを固定した alias を取り入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/114
- 検証した基準 HEAD: 移植先 `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`）、移植元 usaturn/agent-workspace `84469b9bb1c35febc6e94e0a8bfa92cf75e7f4c4`（`main`、2026-10-17T10:58Z）
- 状態: draft（利用者の明示承認は得ていない）
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue114-issue-to-pr-alias.md`
- 実行許可: 2026-10-17（JST）、利用者が「#114 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」と指示した。推奨案での実装、隔離 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージと rebuild は利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

Issue を渡すと、推奨案で Spec → Plan → 実装 → 検証 → PR まで止めずに進める `issue-to-pr` スキルを、usaturn/agent-workspace から取り入れる。移植元が前提にしている仕組み（`projects.toml`、`repository-ownership`、`agent_tmp.py`、`tools/devenv`、`docs_draft/` の Spec）は移植先に無いので、移植先の `AGENTS.md`（「リポジトリ境界」「Spec・Plan の保存と公開」「GitHub Actions」）に置き換える。あわせて、Cursor・Devin の alias のモデルを移植元に合わせて固定する。

## 確認した事実（2026-10-17）

- 移植元の `issue-to-pr` は `3bc4769` の後に `84469b9` まで 2 コミット進んだ。変わったのは `SKILL.md` の 2 章の 4（既存の open PR で止まるときの報告と、`--merge` のときの再開の案内）と、その評価だけ。`--merge` に関わる部分は持ち込まない。PR の URL と base を報告に書く部分は取り入れる
- 移植元の `ec13c3e` の版（`SKILL.md` 91 行、`resolve_issue.py` 113 行）は `--merge`・`--implement` を持たない。移植はこの版を土台にする
- 移植先の既存のスキルのスクリプト（`pr_review_workspace.py`・`upsert_pr_comment.py`）と共通の context helper（`scripts/superpowers_context.py`）は、標準ライブラリだけで書かれている。ルートの `pyproject.toml` の依存は `pytest`・`pyyaml`（dev）だけで、pydantic は無い
- `scripts/superpowers_context.py` は「リポジトリ境界」の表のうち create-reso-world と usaturn/resoloop の経路を固定で持つ（resoloop-meshy は持たない）。`pr-review`・`review-fix-planning` が CLI として使う
- 対象の 3 つのリポジトリの状態: usaturn/create-reso-world は private で CI を止めている。usaturn/resoloop は public で Actions が有効、既定の branch は `main`、checkout は `external/resoloop`（`.worktrees/` は `.git/info/exclude` で無視）、テストは `dotnet test ResoLoop.slnx --nologo`。usaturn/resoloop-meshy は private で Actions は無効、checkout は `external/resoloop-meshy`、テストは worktree での `uv run pytest`（`docs/resoloop-meshy-workflow.md`）
- ボードの子は、GitHub の親子関係（Sub Issue）と、子の本文の親とボードのキーの記載（例: #110 の「関連: #95（ボード `resoloop-plugins-board`）」）で見分けられる。予約は create-reso-world の `refs/heads/agent-claims/issue-N`（`planning-parallel-issues`）。移植先のボードは統合用の branch を使っていない
- create-reso-world のボードの子には、実装の対象が usaturn/resoloop のもの（#110〜#112 など。本文に「実装の対象: usaturn/resoloop」）がある
- alias の 5 つのモデル名は、今の CLI のモデル一覧にある: Cursor（`agent` 2026.10.16-e3cb207）の `grok-4.7-xhigh`・`claude-opus-5-5-xhigh`、Devin（3000.11.92）の `swe-2-max`・`gpt-6-1-sol-xhigh`・`claude-opus-5-5-xhigh`
- `.devcontainer/test-readme.bash` は、README のツールの表の「zshrc の関数」の列の名前が `zshrc.txt` に alias か関数としてあることを確かめる

## 判断

### issue-to-pr

- **D-1 扱うリポジトリ**: 「リポジトリ境界」の表にある usaturn/create-reso-world・usaturn/resoloop・usaturn/resoloop-meshy の 3 つだけ（Issue の推奨）。orange3134/resoloop（上流）は `docs/resoloop-fork-workflow.md` の流れで扱うので拒否する。それ以外は「リポジトリ境界」が一般的な外部実装を非対応としているので拒否する
- **D-2 Issue の置き場所と実装の対象**: 実装の対象（`TARGET_REPO`）は、既定で Issue の置き場所（`ISSUE_REPO`）と同じとする。Issue 本文が実装の対象を明記していれば（「実装の対象: usaturn/resoloop」など）、それに従う。明記された対象が 3 つの外なら停止する。create-reso-world のボードの子の多くが resoloop を対象にするので、この経路を持つ
- **D-3 受け付ける表記**: `https://github.com/<owner>/<repo>/issues/N`、`<owner>/<repo>#N`、`#N`。`#N` は現在の checkout の `origin` で解決する。移植元の `<name>#N` は `projects.toml` の名前を前提にしており、`resoloop#N` は fork と上流のどちらか決まらないので受け付けない
- **D-4 リポジトリの判定**: `tools/workspace`（`projects.toml`）は入れない。3 つのリポジトリは `resolve_issue.py` に固定値で持ち、checkout の位置と確認事項は `SKILL.md` の表に「リポジトリ境界」と同じ内容で書く。`projects.toml` を入れると「リポジトリ境界」の表と同じ情報を 2 か所で管理することになり、既存の `superpowers_context.py` も固定値で経路を持っている。#116 もこの判断に従う
- **D-5 依存**: `resolve_issue.py` は標準ライブラリだけで書き、pydantic を使わない。GitHub の応答の形は数行の型の検査で確かめる。既存のスキルのスクリプトと同じ書き方で、#115 が同時に変える `pyproject.toml`・`uv.lock` に触れずに済み、マージの順序の制約も無くなる。実行は `uv run --no-project python`（`pr-review` の context helper と同じ）
- **D-6 オプション**: `-` で始まる語はすべて拒否する（終了コード 2）。移植元のオプション（`--merge`・`--implement`・`--max-cycles`・`--hold-action`・`--assign`・`--template`・`--config`・`--fresh-review`）は「#116 で入れる予定で、今は使えない」と理由を表示する。ほかは「未知のオプション」とする。`INPUT` の切り出し方（利用者の引数の先頭から、Issue の参照とオプションのうち最後のものまでを書かれたまま渡し、後ろの自然文を含めない）は移植元に従う
- **D-7 helper の範囲**: `resolve_issue.py` は入力の解析、リポジトリの判定、`gh issue view` での Issue の確認（PR・番号や URL の不一致・closed の拒否）だけを行い、Git と GitHub の状態を変えない。出力は `repo`・`number`・`url`・`title`・`body` の JSON。競合・予約・承認の確認は `SKILL.md` の手順で行い、helper の成功をその証拠にしない
- **D-8 Spec・Plan の置き場所と確認用のコピー**: Spec・Plan は `AGENTS.md` のとおり create-reso-world の `docs/superpowers/` に `draft` でコミットする。利用者の実行指示は「実行許可」として記録し、内容の承認（`approved`）にしない。利用者に確認を求めない流れなので、確認用のコピー（`scripts/superpowers-review-copy.sh`）は作らない。`TARGET_REPO` が create-reso-world なら、Spec・Plan は実装と同じ PR に入れる。ほかのリポジトリなら、create-reso-world の文書用の worktree・branch にコミットし、コードの PR を作った後に文書専用の PR で公開し、互いに参照する。`AGENTS.md` の「Spec・Plan の保存と公開」に、issue-to-pr のこの扱いを 1 項目で足す
- **D-9 統合用の branch**: 持ち込まない。PR の向き先は常に `main`。親 Issue・handoff が `main` 以外を向き先に指定していれば、worktree を作る前に停止する（黙って `main` に向けない）。移植先のボードは統合用の branch を使っておらず、使い始めるときに入れる
- **D-10 競合の確認**: 移植元と同じく、worktree を作る前に、同じ Issue の open PR（`TARGET_REPO` と、文書専用の PR を出す場合は create-reso-world）、`refs/heads/agent-claims/issue-N` とコメントの未解放の担当、既存の worktree とローカル・remote の branch（`issue-N` を番号の境界で照合）、未完了の先行 Issue を調べ、どれかあれば作業を作らずに止まる。既存の open PR で止まるときは PR の URL と base を報告し、レビューは `/pr-review <PR の URL>` で行えると伝える（移植元 `84469b9` の、URL で案内する部分）
- **D-11 ボードの子**: GitHub の親 Issue があり、子の本文か親の本文にボードのキーがある Issue は、`planning-parallel-issues` に従う（予約・先行条件・成果の公開・解放）。手順はこのスキルに写さない
- **D-12 worktree と名前**: worktree は対象の checkout の `.worktrees/` に、最新の `origin/main` から作る（create-reso-world は親 checkout の `.worktrees/`、resoloop・resoloop-meshy は各 checkout の `.worktrees/`）。名前は `issue-N-<要約>`、branch は `feat/issue-N-<要約>` か `fix/issue-N-<要約>`。Issue が create-reso-world の外にあるときは、名前の先頭にリポジトリ名を付ける（`resoloop-issue-18-<要約>`）。文書用の worktree・branch は `docs/<同じ名前>`
- **D-13 実行方式**: 移植元の `ec13c3e` の表（独立した Task は `superpowers:subagent-driven-development`、同じファイルの逐次変更や 1〜2 Task は `superpowers:executing-plans`）。常にこのセッションが実装の責任を持つ（移植元の `self` と同じ流れ）
- **D-14 Herdr**: `HERDR_ENV=1` のとき、現在の pane の名前とタスクを設定する。現在の pane が分からない、rename が失敗したときは、別の pane を推測せず、rename を省いて続け、報告に書く。移植元は停止するが、表示のための操作の失敗で PR までの作業を止める理由は無いと判断した（エージェントの判断）
- **D-15 検証と CI**: 検証は対象ごとの入口で行う（create-reso-world は `README.md` の「テスト」、resoloop は worktree での `dotnet test ResoLoop.slnx --nologo`、resoloop-meshy は worktree での `uv run pytest`）。CI は `AGENTS.md` の「GitHub Actions」に従い、public のリポジトリ（usaturn/resoloop）だけ PR の checks が green になるのを確かめてから完了する
- **D-16 PR**: `gh pr create --repo "$TARGET_REPO" --base main --head <branch>`。本文は、同じリポジトリの Issue なら `Closes #N`、別のリポジトリなら `Refs <Issue の URL>`（マージで別のリポジトリの Issue を自動で close しない）。変更概要、Spec の判断と理由、実行方式と理由、実行した検証と結果、作業時間と主要 Task 別の内訳を書く。マージはしない。最終報告で、レビューは `/pr-review <PR の URL>` で行えることを 1 行で伝える
- **D-17 評価**: `superpowers:writing-skills` の、スキル無し・有りの行動の比較を行い、`evals/scenarios.json` と `evals/validation.md` に記録する。文言を照合するテストは書かない
- **D-18 テスト**: `resolve_issue.py` の入力の解析と拒否（PR の URL、closed の Issue、対象外のリポジトリ、未対応のオプション、応答の不一致）を、実際の git の checkout と `gh` の代わりのスクリプトでテストする（`AGENTS.md` の「テストの採用基準」の「書く」）。3 つのリポジトリの固定値は、扱ってよいリポジトリの範囲を守るための固定値として使う
- **D-19 Codex 用の `agents/openai.yaml`**: 作らない。移植元にも無い

### alias

- **D-20 定義**: `.devcontainer/zshrc.txt` の `cur`・`dev` を移植元（#515、`3bc4769` でも同じ）の定義に置き換え、`curo`・`devs`・`devo` を足す
- **D-21 README**: `.devcontainer/README.md` のツールの表の Cursor・Devin の「zshrc の関数」の列に、足した alias を書く
- **D-22 移植の記録**: `docs/maatlog-poc-porting.md` の Cursor と Devin の alias の行を、判断「移植」・担当 #114 に書き換え、#17 では対象外としたことを理由の列に残す
- **D-23 確かめ方**: テストは書かない（設定値だけの変更）。変更後の `zshrc.txt` の alias を読み込んだ zsh で 5 つを実際に起動し（非対話の `-p`）、指定したモデルで応答することを確かめる。rebuild の後に利用者が確かめる項目は #114 にコメントで記録する

## 範囲外

- `--merge`・`--implement`・agent-runner・PR の修正ループ（#116）
- pi のランチャーと設定、Vertex AI の Gemini（#125）
- `ccd` 系の alias と関数、dsh
- `pr-review`・`review-fix-planning`・`planning-parallel-issues` の本文
- `pyproject.toml`・`uv.lock`・`README.md` の「テスト」の節（#115 が変える）
- 実際の Issue で issue-to-pr を起動して PR まで通すこと（この PR のマージ後に利用者が使う）
