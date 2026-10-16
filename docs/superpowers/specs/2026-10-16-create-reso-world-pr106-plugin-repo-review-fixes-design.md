# PR #106: Meshy プラグインのリポジトリ（Issue #96）のレビュー修正要否

- 文書管理・対象リポジトリ: `usaturn/create-reso-world`
- PR: https://github.com/usaturn/create-reso-world/pull/106（`feat/issue-96-plugin-repo` → `main`）
- 関連 Issue: #96（本文の `Refs #96`。`closingIssuesReferences` は空）、親 #95
- 関連文書: `docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md`、`docs/superpowers/plans/2026-10-16-create-reso-world-issue-96-plugin-repo.md`
- 検証したコード HEAD: `0c57c4f61487595875337fa9fca2c1ed457529e1`（PR の分岐点 `e7eb72a1602a`。base `main` は `1129cb3f2d5d` まで進んでいるが、#108 の文書だけで、この PR の変更ファイルと重ならない）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning #106` を指定。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が必要なら既存 PR への push）として扱う
- 結論: 1（修正して push）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-96-plugin-repo`（PR head を checkout 済みの既存 worktree を、clean・PR head 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#106-feat-issue-96-plugin-repo/` の 4 ファイル。対象 HEAD はすべて `0c57c4f61487` で、取得した `pull/106/head` と一致する。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `SWE-2-High.md` | Approve | Low 1 |
| `claude-opus-5-5.md` | Approve | Info 1 |
| `deepseek-deepseek-v4.1-flash.md` | Approve | Low 1、Info 2 |
| `gpt-6.1-sol.md` | Approve | Medium 1 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | SWE L-1、Opus I-1、DeepSeek I-1 | `status` は「常に 0」と書かれているが、使い方の誤りで 2、git が無いと 3 で終わる | 対応しない。隔離 worktree で確認した（`env PATH=/nonexistent bash scripts/resoloop-meshy.sh status` が 3、`status extra` が 2）。どちらも何も変えずに理由を出して止まり、誤った結果は残らない。git の無い状態はこの Dev Container では起きない。PR 本文の「後回しにした軽微な点」に既に書かれている |
| R2 | DeepSeek L-1 | `tests/scripts/test-docs.bash` の既定の対象に `docs/resoloop-meshy-workflow.md` が無い | 対応しない。確認した（`tests/scripts/test-docs.bash:51`）。現在の参照先はすべて実在する（`--refs docs/resoloop-meshy-workflow.md AGENTS.md` が 0）。将来の参照切れを検出する範囲の網羅の話で、直さなくても誤った結果にならない |
| R3 | DeepSeek I-2 | Plan の冒頭に「検証したコードの HEAD」が無い | 対応しない。記録の書き方。基準の `e7eb72a1602a` は Spec の冒頭にある |
| R4 | GPT M-1 | 運用文書の手順 5 の `gh pr create --repo usaturn/resoloop-meshy` に `--head` が無い。親 checkout で実行すると PR を作れない | **対応する**。致命的: 文書の手順どおりに進めると、プラグインの変更を反映する主要な処理（PR の作成）が止まる。発生条件: 文書は親 checkout のルートでの実行を指定し、親 checkout は `AGENTS.md` の「ローカルは常に origin/main に保つ（ローカルの main は作らない）」により detached HEAD が通常である（実環境の `git worktree list` で `(detached HEAD)`）。#90・#102 がこの手順に従う。親 checkout が push していないブランチの上にあり、端末が対話できるときは、`gh` がそのブランチ（create-reso-world の履歴）の push 先や base のリポジトリの fork を尋ねる（`gh pr create --help` の 5〜8 行目）。(a)(b) を満たす: 隔離した scratch リポジトリを detached HEAD にして `gh pr create --repo usaturn/resoloop-meshy --title t --body b --dry-run` を実行すると、`could not determine the current branch` で 1。ブランチの上でも `aborted: you must first push the current branch to a remote, or use the --head flag` で 1。`--base main --head <branch>` を付けると、同じ detached HEAD から `Would have created a Pull Request with: ... head: <branch>` になる |

分類: **解消済み 0 / 対応する 1 / 対応しない 3**。

仕様の論点として残すもの: なし。

## R4 の修正

### 方針

親 checkout で実行する方針（`docs/resoloop-meshy-workflow.md` の「開発の流れ」の冒頭）は変えず、手順 5 の PR の作成で base と head を明示する。

- `docs/resoloop-meshy-workflow.md` 手順 5: `gh pr create --repo usaturn/resoloop-meshy --base main --head <type>/<topic>` にし、`--head` を省くと止まる理由を 1 文で書く
- Spec D-6: 同じコマンドを書いているので、同じ形に直す

他の案: 手順 5 だけ worktree を cwd にして `gh pr create` を実行させる（`gh` が現在のブランチと remote から head を決める）。手順の他のコマンドは親 checkout 基準の `git -C` なので、手順 5 だけ cwd が変わると手順 6 の相対パスを取り違えやすい。このため選ばない。

### 守る条件と影響経路

守る条件: `docs/resoloop-meshy-workflow.md` の手順を親 checkout のルートで実行するとき、プラグインのリポジトリを操作する各コマンドは対象（checkout・worktree・ブランチ）を明示し、cwd（親 checkout）の git の状態に依存しない。

| 守る条件 | 経路 | 判定 | 確かめる方法 |
| --- | --- | --- | --- |
| 上記 | 手順 1 `bash scripts/resoloop-meshy.sh clone`・`status` | 既に満たす（スクリプトが git の common dir から場所を決める） | `tests/scripts/test-resoloop-meshy.bash` のケース 9 が PASS。PR の head の隔離 worktree から `status` を実行し、親 checkout の `external/resoloop-meshy` を表示した |
| 上記 | 手順 2 `git -C external/resoloop-meshy pull --ff-only` | 既に満たす（`-C` で対象を指定） | 文書の差分を読んだ |
| 上記 | 手順 3 `git -C external/resoloop-meshy worktree add -b <type>/<topic> .worktrees/<topic> origin/main` | 既に満たす（相対パスは `-C` の場所が基準） | scratch で `git -C external/plugin worktree add -b feat/x .worktrees/x HEAD` を親の位置から実行し、`external/plugin/.worktrees/x` に作られ、親の側に `.worktrees` ができないことを確かめた |
| 上記 | 手順 4 worktree での `uv run pytest` | 既に満たす（実行場所を worktree と明示） | 文書の差分を読んだ |
| 上記 | 手順 5 `git -C .../.worktrees/<topic> push -u origin <type>/<topic>` | 既に満たす | 文書の差分を読んだ |
| 上記 | 手順 5 `gh pr create --repo usaturn/resoloop-meshy` | **修正する**（`--base main --head <type>/<topic>`） | scratch の detached HEAD で、`--head` なしは 1（`could not determine the current branch`）、明示すると `--dry-run` で head・base が表示される |
| 上記 | Spec D-6 の同じコマンド | **修正する**（設計の記録から手順を組み立てる人が同じ失敗をする） | 修正後の差分を読んだ |
| 上記 | 手順 5 のマージ、手順 6 のブランチの削除 | 対象外（コマンドを書いていない。番号を指定した `gh pr merge` は cwd のブランチに依存しない） | — |
| 上記 | 手順 6 `git -C external/resoloop-meshy worktree remove .worktrees/<topic>` | 既に満たす（`-C` の場所が基準） | 手順 3 と同じ scratch で `worktree remove .worktrees/x` が成功した |
| 上記 | `origin` の修正 `git -C external/resoloop-meshy remote set-url ...` | 既に満たす | 文書の差分を読んだ |
| 上記 | `AGENTS.md` の「リポジトリ境界」の行 | 既に満たす（コマンドを書かず、手順を運用文書に委ねる） | 差分を読んだ |
| 上記 | `docs/resoloop-fork-workflow.md:82` の上流への PR | 既に満たす（`--head usaturn:fix/<topic>` を明示） | 行を読んだ |
| 上記 | プラグインのリポジトリの `README.md`・`AGENTS.md`（`origin/main` = `1b64663`） | 既に満たす（README は `cd external/resoloop-meshy` の後で実行、PR の作成のコマンドは書いていない） | `git -C external/resoloop-meshy show origin/main:<file>` を読んだ |

同じ条件の再発と設計の見直し: 当たらない。この PR に以前のレビュー修正は無い（Spec の記録と PR のコミット履歴で確認）。

テストの要否: 要らない。文書の文面だけの変更で、守る挙動が無い（`AGENTS.md` の「テストの採用基準」）。代わりに、上の scratch での `gh` の実行と、参照先の検査で確かめる。

## 確認の範囲

- PR の変更 6 ファイルの全文（`scripts/resoloop-meshy.sh`、`tests/scripts/test-resoloop-meshy.bash`、`docs/resoloop-meshy-workflow.md`、`AGENTS.md` の差分、Spec、Plan）
- 関連: `scripts/resoloop-fork.sh` との形の比較は Spec D-5 で決定済み。`docs/resoloop-fork-workflow.md` の PR の作成、`.agents/skills/agent-handoff/references/handoff-schema.md`・`.agents/skills/planning-parallel-issues/references/session-workflow.md` の「一般的な外部実装は経路未定義」の規定（新しい行は「それ以外」と別に経路を定めており、`AGENTS.md` がスキルより優先されるので矛盾しない）、プラグインのリポジトリの `README.md`・`AGENTS.md`
- 再現は `mktemp` の隔離 worktree（レビュー時の HEAD）と、その下の scratch リポジトリで行い、終わったら外した

## 検証

修正のコミット `cbfae52` の後、専用の worktree で実行した。

| コマンド | 結果 |
| --- | --- |
| `bash tests/scripts/test-docs.bash --refs docs/resoloop-meshy-workflow.md AGENTS.md` | 0 |
| `bash tests/scripts/test-instructions.bash` | PASS |
| `bash tests/scripts/test-resoloop-meshy.bash` | PASS |
| `bash .devcontainer/run-tests.bash` | 30/30 PASS（152 秒） |
| `bash scripts/check-layout.sh` | PASS |

参考: `test-docs.bash --refs` に Spec（`2026-10-16-create-reso-world-issue-96-plugin-repo-design.md`）を加えると、92 行目の `tests/conftest.py`（プラグインのリポジトリのファイル）で失敗する。修正前の head から変わっていない行で、Spec は PR の検証の対象に入っていない。

## 自己レビュー

サブエージェントは使わず、修正後に 1 回、3 観点を自分で見た。変更が文書の 2 行だけのため。自己レビュー後の修正は無い。

- 反証: 直したコマンドは、親 checkout が detached HEAD でも、ブランチの上でも、cwd のブランチを使わない（`--head` を付けると push と fork の確認を飛ばす。`gh pr create --help` の 7〜8 行目）。`--head` に owner を付けないと head のリポジトリは `--repo` と同じになり、手順 5 の push 先（`origin` = usaturn/resoloop-meshy）と一致する
- PR 全体: 変更 6 ファイルを読み直し、致命的な問題は無かった
- 検証の検出力: scratch での `gh` の実行は、`--head` なしの失敗と、明示したときの成功を両方確かめており、修正前の文書のままなら失敗する

自己レビューで出た指摘:

| ID | 指摘 | 分類と根拠 |
| --- | --- | --- |
| S1 | 親 checkout で `--fill` を併用すると、`gh` は cwd（create-reso-world）のコミットから title・body を作ろうとする | 対応しない。文書は `--fill` を指示していない |
| S2 | Spec を `test-docs.bash --refs` に渡すと、プラグインのリポジトリのファイルの参照で失敗する | 対応しない。修正前からの行で、Spec は PR の検証の対象外。設計の記録の読み取りに影響しない |

## 所要時間

着手（2026-10-16 04:30Z ごろ）から Spec の記録まで約 20 分。レビューと PR の読み込み 約 8 分、指摘の再現と経路の確認 約 5 分、修正と検証（一括検証 152 秒を含む）約 5 分、自己レビューと記録 約 2 分。
