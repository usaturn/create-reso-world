# create-reso-world#96: Meshy プラグインのリポジトリを作り、external/ から開発できるようにする

## 管理・実行許可

- 文書管理: `usaturn/create-reso-world`（ブランチ `feat/issue-96-plugin-repo`）
- コード対象: `usaturn/create-reso-world`（同じブランチ）と、新しく作る `usaturn/resoloop-meshy`
- 対象 Issue: usaturn/create-reso-world#96（親 #95、ボードのキー `resoloop-plugins-board`、子のキー `plugin-repo`）
- 検証した基準: create-reso-world `main` の `e7eb72a1602ac03e723bc50c9734773102947df1`
- 状態: draft（内容の承認は得ていない）
- 関連 Plan: `docs/superpowers/plans/2026-10-16-create-reso-world-issue-96-plugin-repo.md`
- 実行の指示（2026-10-16 JST）: 利用者が「#96 に着手せよ。途中で止めずに推奨案で PR まで作成して」と指示した。この指示に基づき、Spec・Plan の承認を待たずに、推奨案で実装、GitHub のリポジトリの作成と初期コミットの push、create-reso-world への PR の作成まで行う。内容の承認は得ていないので状態は draft のままにし、PR のレビューで確認を受ける。create-reso-world の PR のマージは利用者の指示による
- 予約: `refs/heads/agent-claims/issue-96` = `b066ccef078603e70438a4f36e2c8ffcd4d0388c`（#96 のコメント 6199592037）

## 1. 目的

Meshy プラグインのリポジトリを GitHub に作り、create-reso-world の `external/` の下に checkout して、エージェントが create-reso-world の規約のもとで開発できるようにする。`AGENTS.md` の「リポジトリ境界」の表に行を足し、#90・#102・#103 がこの行だけを根拠に作業ルートを決められるようにする。

### 成功の条件（#96 の受け入れ条件）

- リポジトリがあり、Actions が無効になっている（`gh api repos/usaturn/resoloop-meshy/actions/permissions` が `"enabled": false`）
- `bash scripts/resoloop-meshy.sh clone` で checkout ができる。既にあれば remote を確かめるだけで、食い違いがあれば止まる
- `AGENTS.md` の表に行があり、エージェントがその行だけを根拠に作業ルートを決められる
- 新しいリポジトリで、`uv run pytest` が成功する

## 2. 決定

利用者の指示により、Issue の「Spec で決めること」は推奨案でエージェントが決めた。代案と理由を残す。

### D-1 リポジトリの名前

`usaturn/resoloop-meshy`（#96 の推奨）。`resoloop-<名前>` の形は、fork の `usaturn/resoloop` と並べたときに resoloop のプラグインだと分かり、短い。

- 代案: `resoloop-plugin-meshy`。役割は明確だが長く、プラグインが増えたときの利点も小さい

### D-2 公開範囲

非公開（private）で作る。#105 で上流へ外部のプラグインの例として見せるときに、利用者の確認を経て public に変える。

- 理由: 公開は外部への操作で、一度公開した中身は取り消せない（キャッシュや複製が残る）。#90・#102 の作業は private で足りる。create-reso-world と reso-workshop も private である
- 代案: 最初から public。#105 で公開範囲を変える手間は省けるが、中身が揃う前に公開になる
- 影響: private なので、`clone` には GitHub の認証が要る。この Dev Container は `gh auth git-credential` を git の認証に使っているので、`gh auth status` が通っていれば足りる

### D-3 ライセンス

GNU Affero General Public License v3.0 or later（AGPL-3.0-or-later）。resoloop と同じにする。`LICENSE` には全文（GitHub のライセンス API の `agpl-3.0` の本文）を置く。`pyproject.toml` の `license` は `AGPL-3.0-or-later`。

- 理由: #90・#102 で、fork（AGPL-3.0-or-later）の Meshy の同梱物やスキルの文面を移す可能性がある。同じライセンスなら制約なく移せる。#105 で上流に見せるときも、上流と同じライセンスの方が扱いやすい。Blender の Python API（GPL-3.0-or-later）を使うスクリプトとも両立する（GPLv3 と AGPLv3 は互いの第 13 条で組み合わせられる）
- 代案: MIT。制約は緩いが、AGPL の部分を移せなくなる

### D-4 checkout の場所と remote

- 場所: create-reso-world の親 checkout（`PARENT_ROOT`。git の common dir の親）の `external/resoloop-meshy`。`external/` はルートの `.gitignore` で無視済みで、リポジトリの中にあるので Rebuild の後も残る（`docs/resoloop-fork-workflow.md` の「checkout の位置と remote 構成」と同じ理由）
- remote: `origin` = `https://github.com/usaturn/resoloop-meshy.git` だけ。fork ではないので `upstream` は無い
- 確かめ方: `origin` の URL を期待値と比べる。末尾の `/` と `.git` の有無だけが違う URL は同じとみなす（`scripts/resoloop-fork.sh` と同じ）

### D-5 `scripts/resoloop-meshy.sh`

`clone` と `status` の 2 つのサブコマンドを持つ。形と終了コードは `scripts/resoloop-fork.sh` に合わせる。

| サブコマンド | 動作 |
| --- | --- |
| `clone` | checkout が無ければ `origin` から clone する。既にあれば `origin` を確かめるだけで、何も変えない。食い違いがあれば止まる |
| `status` | checkout の HEAD・ブランチ・未コミットの変更の有無と、`origin` の確認の結果を表示する。何も変えない。常に 0 |

- 終了コード: 0 成功、1 状態が期待と違う（その場所が自前の git の checkout でない、`origin` が無い・違う）、2 使い方の誤り、3 前提不足（git が無い）、4 `git clone` の失敗
- 既定の checkout の場所: スクリプトを含む create-reso-world の親 checkout の `external/resoloop-meshy`。git の common dir（`git rev-parse --path-format=absolute --git-common-dir`）の親を親 checkout とする。create-reso-world の worktree（`.worktrees/<topic>`）から実行しても同じ場所を指す。worktree の中に clone すると、worktree を消したときにプラグインの作業ごと消えるためである。`scripts/resoloop-fork.sh` はスクリプトの位置を基準にしているが、変えない（#96 の範囲外）
- 自前の checkout の判定: その場所が git の checkout のルートであること。外側の create-reso-world のサブディレクトリにすぎない場合は 1 で止まる（外側の `origin` を見て誤って一致としない）
- 環境変数（テストと特殊な運用向け）: `RESOLOOP_MESHY_CHECKOUT`（checkout の場所）、`RESOLOOP_MESHY_ORIGIN_URL`（`origin` の URL）
- `scripts/resoloop-fork.sh` と共通の関数（URL の比較、checkout の判定）は、小さいので複製する。共通化には `scripts/resoloop-fork.sh` の変更が要り、#96 の範囲外である

### D-6 開発の流れ

- checkout そのもの（`external/resoloop-meshy`）は `main` に置き、`git -C external/resoloop-meshy pull --ff-only` で `origin/main` に追従させる
- 実装は `main` から作ったブランチ（`<type>/<topic>`）で、`external/resoloop-meshy/.worktrees/<topic>` の worktree で行う。プラグインのリポジトリの `.gitignore` で `/.worktrees/` を無視する
- テストは checkout（または worktree）で `uv run pytest`
- 反映は PR で `main` へ。push・PR の作成（`gh pr create --repo usaturn/resoloop-meshy`）・マージは利用者の指示による。初期コミットだけは、#96 の成果物として `main` へ直接 push する
- Spec・Plan は create-reso-world の `docs/superpowers/` に置く（`AGENTS.md` の「Spec・Plan の保存と公開」）
- PR のレビューと修正: `pr-review`・`review-fix-planning` には、作業ルートを `CODE_ROOT` として明示して渡す。共通の helper（`scripts/superpowers_context.py`）の「その他の repo」の経路で、checkout 自身のルートであることと、対象と一致する remote が 1 つだけであることを照合する。helper は変えない。レビューの結果は `CODE_ROOT` の `reviews/` に書かれるので、プラグインのリポジトリの `.gitignore` で `/reviews/` を無視する
- CI は作らない（`.github/workflows/` を置かない）。作成直後に Actions を無効にする

### D-7 新しいリポジトリの初期の構成

| ファイル | 中身 |
| --- | --- |
| `README.md` | 目的、状態（土台だけ、道具は #90・プラグインは #102）、開発の始め方、ライセンス |
| `AGENTS.md` | プラグインのリポジトリの規約（D-8） |
| `CLAUDE.md` | `@AGENTS.md` の 1 行 |
| `LICENSE` | AGPL-3.0 の全文（D-3） |
| `.gitignore` | uv・Python の生成物、`/.worktrees/`、`/reviews/`、`tmp/`、`/.superpowers/`、`/.claude/worktrees/`、Blender のバックアップ、個人設定 |
| `pyproject.toml` | uv の仮想プロジェクト（`package = false`）。`requires-python = ">=3.12"`（create-reso-world と同じ）、依存は無し、`dev` グループに pytest、`testpaths = ["tests"]` |
| `uv.lock` | `uv lock` の結果 |
| `tests/conftest.py` | テストのファイルが 1 つも無い間だけ、テストを集められなかった終了（終了コード 5）を成功に変える。最初のテストのファイルを足すと、pytest の既定に戻る |

- `.python-version` は置かない。open3d など版を選ぶ依存は #90 が足し、そのときに Python の版を決める（依存の配布物がその版にあるかの確認も #90 で行う）
- `tests/conftest.py` のフックは、テストのファイルの有無で自動的に効かなくなるので、消し忘れても、名前の誤りで集められなかったテストを見逃さない

### D-8 プラグインのリポジトリの `AGENTS.md`

簡潔に、次だけを書く。

- このリポジトリの目的。Meshy の API（生成、ダウンロード、`meshy-cli`）は使わず、Web アプリからダウンロードした GLB だけを入力にする（#95 の利用者の決定）
- create-reso-world の `external/resoloop-meshy` に checkout して開発し、create-reso-world の `AGENTS.md` にも従う。Codex は git のルートより上の `AGENTS.md` を読まないので、場所を明示する（checkout からは `../../AGENTS.md`、`.worktrees/<topic>` の worktree からは `../../../../AGENTS.md`）
- プラグインの manifest・コマンドの呼び出し・スキルの配布の仕様は fork（#97〜#100）で決まる。決まっていない仕様を推測で作らない
- uv、`uv run pytest`、ブランチと worktree、push・PR・マージは利用者の指示、CI を作らない、Spec・Plan の置き場所、Meshy の原本（GLB・テクスチャ）をコミットしない

### D-9 create-reso-world の `AGENTS.md`

- 「リポジトリ概要」に 1 文: resoloop のプラグイン（Meshy 用の `usaturn/resoloop-meshy`）は、別のリポジトリとして `external/resoloop-meshy` に checkout して開発する
- 「リポジトリ境界」の表に 1 行（「それ以外」の行の前）:

| PR や作業対象の owner/repo | 作業ルート | 確認事項 |
| --- | --- | --- |
| usaturn/resoloop-meshy | `<PARENT_ROOT>/external/resoloop-meshy` | `origin` が usaturn/resoloop-meshy であること。checkout が無ければ `bash scripts/resoloop-meshy.sh clone` を案内して停止する。実装は作業ルートの `.worktrees/<topic>` の worktree で行う。`pr-review`・`review-fix-planning` には作業ルートを `CODE_ROOT` として明示する。手順は `docs/resoloop-meshy-workflow.md` |

### D-10 handoff と復元用の manifest

#95 の「開始手順」は planning と実装を別のセッションで行う前提で、handoff の 2 ファイルと復元用の manifest を求める。今回は利用者の指示で、同じセッションで実装と PR の作成まで行い、実装へ引き継ぐ相手がいない。このため handoff と manifest は作らない。Spec・Plan は create-reso-world の PR のブランチで公開され、中身ごと取り出せる。この判断は #96 のコメントに記録する。

## 3. 範囲外

- 仕上げの道具・スキル・知見（#90）、プラグインの manifest・コマンドの入口（#102）
- create-reso-world の既存の Meshy のファイルと `README.md`（#103）
- `.devcontainer/` の全体、resoloop の本体
- `scripts/resoloop-fork.sh` の変更（共通の関数の切り出し、既定の場所の解決）
- `scripts/superpowers_context.py` に resoloop-meshy の既知の経路を足すこと。明示の `CODE_ROOT` で足りる
- 親（#95）の実行マップ・公開台帳の更新（調整役が行う）

## 4. 検証

- `tests/scripts/test-resoloop-meshy.bash`（新規）: ローカルの bare リポジトリで `scripts/resoloop-meshy.sh` の分岐を確かめる。ネットワークを使わない。対象は、使い方の誤り、clone の前の `status`、clone と 2 回目の clone、URL の表記の違い、`origin` の食い違いと欠落（何も変えずに 1）、外側のリポジトリの中の自前でないディレクトリ（1）、clone の失敗（4、ディレクトリを残さない）、`status` の表示、worktree から実行したときの既定の場所（親 checkout を指す）
- create-reso-world のルートで `bash scripts/check-layout.sh` と `bash .devcontainer/run-tests.bash`
- 新しい文書と `AGENTS.md` の参照先の実在: `bash tests/scripts/test-docs.bash --refs docs/resoloop-meshy-workflow.md AGENTS.md`
- 実際のリポジトリで: `gh api repos/usaturn/resoloop-meshy/actions/permissions`、`bash scripts/resoloop-meshy.sh clone`（2 回目は確認だけ）・`status`、checkout で `uv run pytest`
- 新しいリポジトリには、守る挙動が無い（雛形と設定だけ）のでテストを書かない。`tests/conftest.py` は、テストが無い状態で `uv run pytest` が 0 で終わることと、テストのファイルを置いて集められないときに 5 へ戻ることを、手で確かめる

## 5. 結果（2026-10-16 JST）

- `usaturn/resoloop-meshy` を作成した（private、既定のブランチ `main`、GitHub がライセンスを AGPL-3.0 と認識）。Actions は作成直後に無効にした（`{"enabled":false,...}`）
- プラグインのリポジトリの `main`: `c24d000`（初期の構成）、`1b64663`（最終レビューの修正: worktree から create-reso-world の `AGENTS.md` への相対パス、`/.superpowers/`・`/.claude/worktrees/` の無視）
- `bash scripts/resoloop-meshy.sh clone` を create-reso-world の worktree から実行し、親 checkout の `/workspaces/reso-world/external/resoloop-meshy` に clone した（worktree の中には作られない）。2 回目は確認だけ、`status` は `(main, clean)`・`remote: origin is as expected`
- プラグインのリポジトリで `uv run pytest` は 0（テスト無し）。テストのファイルを置いて集められないときは 5、通るテストを置くと 0（いずれも手で確認し、置いたファイルは消した）
- create-reso-world: `bash scripts/check-layout.sh` PASS、`bash .devcontainer/run-tests.bash` 30 本すべて PASS（`tests/scripts/test-resoloop-meshy.bash` を含む）
- 共通の helper: `--operation review-workspace --code-root /workspaces/reso-world/external/resoloop-meshy --repo usaturn/resoloop-meshy` は 0、`--code-root` を省くと 64（明示を求めて止まる）
- 最終レビューは作者のセルフレビュー（このセッションではサブエージェントを起動していない）

## 6. リスクと対処

- private の clone は認証が要る。認証が無ければ `git clone` が失敗し、4 で止まる。`docs/resoloop-meshy-workflow.md` に `gh auth status` の確認を書く
- `AGENTS.md` を変えるのは、ボードでは #96 だけである。ほかの PR と衝突したら、後からマージする方が rebase する（#95 の「共有インターフェースと担当」）
