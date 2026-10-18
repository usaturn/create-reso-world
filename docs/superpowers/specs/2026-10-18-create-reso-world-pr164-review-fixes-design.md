# PR #164 レビュー指摘の選別と修正（Issue #152 レビューの共通 helper）

## 管理・実行許可

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/164（`feat/issue-152-review-helpers`、base `main`、関連 Issue #152）
- 状態: completed
- 回: 1 回目（レビュー対象の HEAD `60849067e1e7`、修正 `6bf6ba4`）、2 回目（レビュー対象の HEAD `738680742c29`、修正 `9bc5205`）
- 実行許可: 1 回目・2 回目とも 2026-10-18（UTC）、利用者が `/review-fix-planning #164` を実行した。計画で止める指定が無いので、review-fix-planning の「完遂」として、この PR のレビュー修正の実装・検証・commit・push・状況コメントの投稿（結論 1）、または修正不要のときのマージと関連 Issue の更新（結論 2）まで進めることが許可されている。下の判断は、確認を取らずに決めたエージェントの判断であり、利用者の承認ではない
- 関連 Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue152-review-helpers-design.md`（PR の設計。とくに D-3「`review_findings.py` は形式と挙動を移植元のまま」、D-11「テストの範囲」）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-152-review-helpers`（PR の head を checkout した既存の worktree。どちらの回も、未コミットの変更が無く、HEAD が PR の head と一致していたので使った）

## 2 回目（レビュー対象の HEAD `738680742c29`）

### 入力

レビューディレクトリ `reviews/usaturn/create-reso-world/#164-feat-issue-152-review-helpers/`。選別の時点の PR の head は `738680742c29a4cb8abb23e9145c9dc95919bde8`（4 本の対象と同じ）。

| ファイル | 対象 HEAD | 結論 | 指摘 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `738680742c29`（Update） | Approve | なし |
| `SWE-2-Max.md` | `738680742c29`（Update） | Approve | なし（Unverified candidates 2 件。1 回目からの継続） |
| `deepseek-deepseek-v4.1-flash.md` | `738680742c29`（Update） | Approve | Info 1（1 回目からの継続） |
| `gpt-6.1-sol.md` | `738680742c29`（Initial） | Approve | なし |
| `openai-codex-gpt-6.1-sol.md` | `60849067e1e7`（Initial、更新なし） | Approve | Medium 3・Low 1（Review coverage に既出の事項 1 件） |

### 指摘の分類

解消済み 1 / 対応する 1 / 対応しない 11。

確認の範囲: 全指摘、PR の変更ファイル 11 本の全文（`review_target.py` 系は自分で、`review_findings.py` 系と `review_records.py` 系はサブエージェント 2 体に分けて読んだ）、呼出元（repo 内でこの 3 つの helper を使うのは `review_findings.py` が読む `review_records.py` だけで、スキルからの呼び出しは無い）とテスト。`review_target.py` と `review_records.py` は 1 回目の HEAD から変わっていない（`git diff --stat 60849067e1e7 738680742c29`）。

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Codex M-2 | 見出しの無い Unverified candidates を `from-markdown` が空の一覧として成功させる | 解消済み | `6bf6ba4`。`738680742c29` で箇条書きの候補を渡すと `unparsed Unverified candidates …` で終了コード 65（`review_findings.py:1567-1570`） |
| 自己確認 S-1 | PR が足したテストの git が親プロセスの `GIT_*` を引き継ぎ、linked worktree の `git rebase --exec` で実リポジトリの設定・index・ブランチを書き換える | **対応する**（(a) 再現した誤動作） | 下の「対応する項目」 |
| Codex M-1 | 番号・URL の経路は、新しい配置のディレクトリの `findings/` が別の PR を指していても受理する | 対応しない | 1 回目と同じ（コードは変わっていない）。番号・URL の経路は照会した PR から保存先と Git 操作の対象を決める（`review_target.py:653-675`）。食い違う `findings/` は、別の PR の候補一覧を手で写したときにしか置かれない |
| Codex M-3 | Markdown の指摘 ID が重複すると、`check-pair` が片方を照合から落とす | 対応しない | 再現した（`check-pair` が終了コード 0）。1 回目と同じく、形式の違反（ID の重複）と JSON 側の欠落という 2 つの誤りが重ならないと起きない。同じ入力の `from-markdown` は重複を拒否する |
| Codex L-1 | 外側 4 個・内側 3 個のバッククォートのフェンスで、内側の見出しを指摘と読む | 対応しない | 再現した。pr-review の様式で必須の Summary の件数表があれば `Summary counts … but … were read` で終了コード 65 になる。件数表が無いときだけ 0 で通る |
| Codex（既出） | `--pr` を添えたとき、層からも `findings/` からも決まらないディレクトリを名前だけで受け付ける | 対応しない | 1 回目と同じ。別リポジトリの同じ番号・同じ head ブランチ名のディレクトリを、パスと `--pr` で食い違えて明示したときだけ起きる |
| DeepSeek I-1 | `review_target.py:97` のコメント「pr-review の helper もここを使う」が実態と違う | 対応しない | 1 回目と同じ。コメントだけで挙動に影響しない。規則の統一は #153 の担当 |
| SWE-2-Max U-1 | `check-pair` の位置の照合が部分文字列の一致で、2 行目以降の `位置` を読まない | 対応しない | 再現した。部分一致は照合を弱めるだけで、2 行目の `位置` は止まる側（終了コード 65）に倒れる。移植元と同じ |
| SWE-2-Max U-2 | 番号だけの指定で `origin` の URL を insteadOf の展開前の値で読む | 対応しない | 1 回目と同じ。意図した選択（`review_target.py:215-218`）で、読めなければ終了コード 7 で止まる |
| 自己確認 S-2 | `review_records.py` が信頼する投稿者は OWNER・MEMBER・COLLABORATOR だけで、orange3134/resoloop での usaturn は CONTRIBUTOR。上流の PR では利用者自身の記録が無視される（`review_records.py:39`・`:982`） | 対応しない | 記録を書く・読む処理がまだ無く（#153・#155）、この PR では誤った結果にならない。仕様の論点として #155 へ申し送る |
| 自己確認 S-3 | フェンスの判定がバッククォートだけで、`~~~` のフェンスの中の見出しも指摘として読む | 対応しない | 再現した。L-1 と同じ種類で、Summary の件数表があれば終了コード 65 で止まる。件数表が無いときだけ `H-99` を読んで 0 で通る |
| 自己確認 S-4 | `COMMENT_BODY_LIMIT` を Python の文字数で数えている（`review_records.py:889`） | 対応しない | GitHub の上限の数え方との一致は未確認だが、投稿する処理がまだ無い。#155 で投稿をつなぐときに確かめる |
| 自己確認 S-5 | `stopped` の `stop_reason` の検査はコロンだけを見て、文書の言う `': '` までは求めない（`review_records.py:614-619`） | 対応しない | 検査が少し緩いだけで、記録の読み書きの結果は変わらない |

1 回目に判定した Unverified candidates の見出しの表記ゆれ（`## Unverified Candidates` など）は、今回のサブエージェントも再現したが、1 回目の自己レビューの反証 5 と同じ論点で、判定は変えない。

### 対応する項目: 自己確認 S-1

#### 現行 HEAD での確認

`7386807` の追跡ファイルを隔離した一時リポジトリに写し、linked worktree から `git rebase --exec '<pytest で 1 ファイル>' HEAD~1` を実行した（`git` は rebase の中のコマンドに `GIT_DIR=<common>/.git/worktrees/<name>` を export する）。

| テスト | テストの結果 | リポジトリの状態 |
| --- | --- | --- |
| `test_review_target.py` | 39 failed・20 passed、rebase が止まる | 共有の設定に `core.bare=true`・`user.name`・`user.email`・`remote.origin.*`。main checkout の git が `fatal: this operation must be run in a work tree` で止まる。worktree は fixture の commit に detached、index も置き換わる |
| `test_review_findings.py` | 231 passed、rebase は「unstaged changes」で止まる | 共有の設定に `core.bare=true`・`user.*`・`diff.mnemonicprefix`・`diff.noprefix`。worktree の index が fixture の 3 ファイルになり、実ファイルは全て未追跡の扱い。HEAD は fixture の commit |
| `test_review_records.py` | 187 passed | 変わらない（git を起動しない） |

原因: `test_review_target.py` の `make_repo`・`make_checkout`・`git()`・`make_remote`（`:42-97`）と、`test_review_findings.py` の `_git`・`_repo`・`_commit`（修正前の `:1701-1724`）は、`GIT_*` を除かずに git を起動する。`GIT_DIR` があると `git -C <一時ディレクトリ>` でも `GIT_DIR` のリポジトリが使われる。`test_review_target.py` の `isolated_git` は `GIT_CONFIG_NOSYSTEM`・`GIT_CONFIG_GLOBAL` を設定するだけだった。テストから呼ぶ helper 本体の git（`review_target._git`、`scripts/superpowers_context.py`、`review_findings._git_output`）も同じ環境を引き継ぐ。

`test_review_findings.py` の fixture は移植元のまま写したもので、`test_review_target.py` の fixture はこの PR で作り直したもの（PR の Spec D-11）。

#### 致命的である理由

`AGENTS.md` の「編集前の確認」は、追跡ファイルの編集を `.worktrees/<topic>` の linked worktree で行うと定めている。各コミットでテストを通すための `git rebase --exec` は普通の手順で、この組み合わせで PR のテストを実行すると、実リポジトリの共有の設定が `core.bare=true` になって main checkout の git が止まり、worktree の index が置き換わってステージした変更が失われる（データの破損・主要な処理が止まる）。`test_review_findings.py` は全件通るので、テストの出力だけでは気づきにくい。同じ型の問題は PR #163 の review-fix で「到達しない」と判定した後に実害を再現し、Issue #166 にした。

#### 修正方針

推奨案（`9bc5205`）: 2 つのテストモジュールの autouse fixture `isolated_git` で、環境変数の `GIT_*` を `monkeypatch.delenv` で除く。`test_review_target.py` は既存の fixture に足し、`test_review_findings.py` には同じ名前の fixture を足した。`.agents/skills/repo-cleanup-after-merge/tests/test_detached_update.py:34-50` と同じ形で、テストの中の fixture の git、helper 本体の git、`uv run` で起動する CLI のサブプロセスが、どれも除いた後の環境を引き継ぐ。

比べた別案:

- fixture の git の呼び出しに、`GIT_*` を除いた `env=` を渡す: テストから呼ぶ helper 本体の git（`review_target._git`・`superpowers_context.py`）は親の環境のままで、条件の一部しか満たさない
- `.agents/scripts/tests/conftest.py` に autouse fixture を置く: 同じディレクトリの既存の `test_agent_tmp.py` の挙動も変え、PR と関係しない既存の問題（#166 の範囲）に踏み込む
- 直さずに #166 へ追記する: マージした後、この PR のテストで実リポジトリが壊れ得る状態が残る

「同じ条件の再発と設計の見直し」のきっかけには当たらない。1 回目に直した条件（Unverified candidates の節を空の一覧として黙って通さない）とは別の条件で、原因の fixture は 1 回目の修正（`6bf6ba4`）より前の `42e8d36`・`ccff011` で入った。自己レビューでもこの回の修正が原因の指摘は無い（下の「自己レビュー」）。

#### 守る条件と影響経路

守る条件: 「この PR が足したテストが起動する git（fixture の git、テストから呼ぶ helper の git、テストが起動する CLI のサブプロセスの git）は、親プロセスの `GIT_*` を引き継がず、テストの一時リポジトリだけを操作する」

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| `test_review_target.py` の fixture（`make_repo`・`make_checkout`・`make_remote`・`git()`・`git clone`・`worktree add`）と、テストから呼ぶ `review_target._git`・`superpowers_context.resolve_context` の git | 修正する（`isolated_git` で `GIT_*` を除く） | 下の状態の比較（修正後に 59 passed・状態不変、ガードを外すと変化） |
| `test_review_findings.py` の `_git`・`_repo`・`_commit`、statement-candidates の `review_findings._git_output`、`uv run` で起動する CLI | 修正する（同じ名前の fixture を足す） | 同上（修正後に 231 passed・状態不変、ガードを外すと変化） |
| `test_review_records.py` | 既に満たす（git もサブプロセスも起動しない） | 修正前も修正後も状態不変 |
| helper 本体の git（利用者・エージェントがシェルから CLI を呼ぶ） | 対象外（git hook・`rebase --exec` の中から呼ぶ経路が無い。スキルへの接続は #153〜#155） | — |
| PR より前からある同じ形のテスト（`.agents/scripts/tests/test_agent_tmp.py`・`tests/scripts/test_superpowers_context.py`・`tools/agent_runner/tests/` など） | 対象外（PR と関係しない既存の問題で、Issue #166 が扱う） | 今回、`test_agent_tmp.py`・`test_superpowers_context.py` でも同じ条件で `core.bare=true` などへの変化を再現した（報告だけ） |

#### 状態の比較とガードを外した対照

守る条件は失敗時の扱いではないが、「失敗時の検証」と同じ方法で確かめた。

- 方法: PR の追跡ファイルの作業ツリーの内容を `mktemp -d` の一時リポジトリに写し、2 つの commit と linked worktree（branch `work`）を作る。worktree から `git rebase --exec 'uv run --project <専用の worktree> --no-sync python -m pytest -q -p no:cacheprovider <テスト>' HEAD~1` を実行し、前後で、共有の設定、worktree の設定、全 refs、main と worktree の HEAD、両方の index（`ls-files -s` の sha256）、両方の status（未追跡を含む）、worktree の一覧、remote、オブジェクトの数を比べた。期待値は実行前の状態から取った
- 修正前（`7386807`）: 上の表のとおり、2 ファイルで変化
- 修正後（`9bc5205`）: 3 ファイルとも rebase が成功し、59・231・187 passed、状態は変わらない
- 対照: 修正後の写しで、1 ファイルずつ `GIT_*` を除くループだけを外すと、2 ファイルとも再び `core.bare=true` などに変わった（検出力 2/2）。対照は一時リポジトリだけで行い、消した

### 実行した検証

専用の worktree のルートで実行した（全て終了コード 0）。

- `uv run pytest .agents/scripts tests/scripts/test_superpowers_context.py`: 548 passed、109 subtests passed
- `bash .devcontainer/run-tests.bash`: PASS 32
- `bash scripts/check-layout.sh`: PASS
- ruff（`uvx ruff check`）: 変えた 2 ファイルの指摘は修正前と同じ（`test_review_findings.py` の ISC004 1 件。移植元のまま写した箇所）
- 変えた 2 ファイルの `ast.parse(..., feature_version=(3, 12))`: 成功
- 上の「状態の比較とガードを外した対照」
- 未確認: Python 3.12 での実行（この環境には 3.14.4 しか無い。構文だけ確かめた）

### 自己レビュー

修正後（`9bc5205`）に 1 回だけ、3 つの観点を別々のサブエージェントに同時に任せた。3 観点とも致命的な指摘は 0 件。自己レビューの後の修正はこの Spec と PR 本文だけで、再レビューはしていない。

- 反証: fixture より前に git が走る箇所（import 時・module/session スコープの fixture・conftest）、`os.environ` の写しを `env=` で渡す呼び出しはどちらも無い。未確認だった git hook の経路も、隔離したリポジトリの linked worktree の pre-commit hook から実行して確かめた（hook は `GIT_DIR`・`GIT_INDEX_FILE` などを渡す）。修正後は 59 件・231 件が通って状態は変わらず、修正前は共有の設定が `core.bare=true` などに変わった。`TMPDIR` を別のリポジトリの中に置いても、そのリポジトリは変わらなかった。3 ファイルを 1 回の実行で通しても 477 件が通り、状態は変わらない
- PR 全体: 修正後の PR 全体を読み、`review_target.py` が書くのは `fetch_pull_head` の ref だけ、`review_findings.py` の git は読むだけ、書き込みは検査を通った後の `--output` だけであることを確かめた。偽のリポジトリの `GIT_DIR`・`GIT_WORK_TREE`・`GIT_INDEX_FILE` を渡したまま 3 ファイルを実行し、477 件が通って偽のリポジトリも worktree も変わらなかった
- 検証の検出力: `rebase --exec` の中で `GIT_DIR` が export されること（git 2.55.0）、写しの tree が `9bc5205`・`7386807` の tree と一致すること、対照と修正後の差が 3 行だけであることを確かめた。比べる範囲を `.git` の objects 以外の全ファイル・作業ツリーの全ファイル（無視されたものを含む）・一時 HOME の `.gitconfig` に広げて実行し直し、修正後の変化は rebase 自身の reflog だけ、対照では修正前と同じ種類の変化が出た

軽微な指摘の判定（すべて致命的でない）:

| 指摘 | 判定 | 理由 |
| --- | --- | --- |
| `test_review_findings.py` の fixture は `GIT_CONFIG_GLOBAL`・`GIT_CONFIG_NOSYSTEM` も除き、設定し直さないので利用者の `~/.gitconfig` を読む（`commit.gpgsign` などでテストが落ち得る）（反証 1・PR 全体 2・検出力 3） | 対応しない | 落ちるだけで何も書き換えない。修正前もこのモジュールは利用者の設定を読んでいた（呼び出し側が隔離したときだけ差が出る） |
| 呼び出し側が設定した `GIT_CEILING_DIRECTORIES` も除く（反証 2） | 対応しない | git の書き込みはどれも `git init` 済みの一時リポジトリに向き、上位のリポジトリに届かないことを確かめた |
| helper 本体の git も `GIT_*` を引き継ぐ（PR 全体 3） | 対応しない | 上の表の「対象外」のとおり、`rebase --exec`・hook の中から CLI を呼ぶ経路が無い |
| 状態の比較のスクリプトが、`GIT_DIR` の export を記録に残していない。古い比較でオブジェクトの数が auto gc の途中の pack を拾った（検出力 1・2） | 対応しない | `GIT_DIR` の export は検出力の担当と最初の再現で別に確かめた。オブジェクトの数は `cat-file --batch-all-objects` で数え直した |
| Spec に 2 回目の修正が書かれていない（PR 全体 1） | 直した | この節を含む「2 回目」を書いた |

反証の担当が修正前の hook の経路を再現したとき、テストの `git commit` が外側の hook を起動し直して再帰した。そのとき作られた pytest の一時ディレクトリが `/tmp/pytest-of-vscode/` に残っている（lock 付き。pytest が 3 日後に消す。ほかのセッションの実行と区別できないので消していない）。

### 申し送り

- #155: 自己確認 S-2（上流の PR で、usaturn の記録が CONTRIBUTOR として無視される）と S-4（コメントの長さの数え方）を、記録の投稿・読み取りをつなぐときに確かめる
- #166: `.agents/scripts/tests/test_agent_tmp.py`・`tests/scripts/test_superpowers_context.py` も、linked worktree の `git rebase --exec` で実リポジトリの共有の設定を `core.bare=true` に変えることを再現した（#166 の本文では「未確認」）

### 結論

結論 1（修正して push）。

### 作業時間

着手 2026-10-18T12:31Z。所要時間と内訳は、状況コメントと完了報告に書く（記録だけのコミットを PR に足さないため）。

## 1 回目（レビュー対象の HEAD `60849067e1e7`）

レビュー対象の HEAD は `60849067e1e7a70d741398203acdff3a9108f791`（4 本のレビューとも同じ。選別の時点の PR の head も同じ）。

### 入力

レビューディレクトリ `reviews/usaturn/create-reso-world/#164-feat-issue-152-review-helpers/`

| ファイル | 対象 HEAD | 結論 | 指摘 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `60849067e1e7` | Approve | なし |
| `SWE-2-Max.md` | `60849067e1e7` | Approve | なし（Unverified candidates 2 件） |
| `deepseek-deepseek-v4.1-flash.md` | `60849067e1e7` | Approve | Info 1 |
| `openai-codex-gpt-6.1-sol.md` | `60849067e1e7` | Approve | Medium 3・Low 1（Review coverage に既出の事項 1 件） |

### 指摘の分類

解消済み 0 / 対応する 1 / 対応しない 7。確認中に自分で見つけた致命的な欠陥は無い。

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Codex M-2 | 見出しの無い Unverified candidates を、`from-markdown` が空の一覧として成功させる | **対応する**（(a) 再現した誤動作） | 下の「対応する項目」 |
| Codex M-1 | 番号・URL の経路は、新しい配置のディレクトリの `findings/` が別の PR を指していても受理する | 対応しない | 番号・URL の経路は、照会した PR から保存先と Git 操作の対象を決めるので（`review_target.py:653-675`）、対象の取り違えは起きない。食い違う `findings/` が置かれるのは、別の PR の候補一覧を手で写したときだけ（pr-review は照会した PR の保存先に、その PR の候補一覧を書く）。移植元も同じ挙動 |
| Codex M-3 | Markdown の指摘 ID が重複すると、`check-pair` が片方を照合から落とす | 対応しない | 発生には、形式の違反（ID の重複。[review-records](../../../.agents/review-records.md) 4.3 節は ID の衝突を禁じる）と、JSON 側での片方の欠落という 2 つの誤りが重なる必要がある。JSON 側の重複は `validate` が拒否し、`from-markdown` も重複を拒否する（再現で確認）。移植元と同じ挙動 |
| Codex L-1 | 外側 4 個・内側 3 個のバッククォートのコードフェンスで、内側の見出しを指摘と読む | 対応しない | 再現した。ただし pr-review の様式で必須の Summary の件数表があれば `Summary counts 0 High finding(s) but 1 were read` で止まり、黙って誤った結果にはならない |
| DeepSeek I-1 | `review_target.py:97` のコメント「pr-review の helper もここを使う」が実態と違う | 対応しない | コメントの記述だけで、挙動に影響しない。規則の統一は #153 の担当（PR の Spec D-6） |
| SWE-2-Max U-1 | `check-pair` の位置の照合が部分文字列の一致で、2 行目以降の `位置` を読まない | 対応しない | 照合を弱めるだけで、主要な処理の結果を誤らせない。文書 7 章の「`位置` の行に含まれる」とも一致する。移植元と同じ挙動 |
| SWE-2-Max U-2 | 番号だけの指定で `origin` の URL を insteadOf の展開前の値で読む | 対応しない | 正式な URL で識別するための意図した選択（`review_target.py:215-218` のコメント）。この環境に insteadOf の設定は無い（`git config --get-regexp '^url\.'` が 0 件） |
| Codex（既出） | `--pr` を添えたとき、層からも `findings/` からも決まらないディレクトリを名前だけで受け付ける | 対応しない | 発生には、別リポジトリの `reviews/<owner>/<repo>/#<N>-<同じ head ブランチ名>` を置き、パスと `--pr` を食い違えて明示する必要がある。PR の Spec の「実装・検証結果」で Minor 2 として持ち越し済み |

仕様の論点として 1 行残す: Codex M-1 の、番号・URL の経路でも `findings/` との食い違いを確かめるかどうかは、review-verify（#154）・review-fix-planning（#155）を接続するときに決める。

### 対応する項目: Codex M-2

#### 現行 HEAD での確認

- `review_findings.py:1592-1605`（修正前）は、Unverified candidates の節の ID を `### <ID>:` の見出しからだけ読み、見出しの無い行を読み飛ばす。`problems()` は見出しの読み取りの失敗と Summary の件数しか見ない
- このレビューディレクトリの `SWE-2-Max.md`（Unverified candidates に箇条書きで 2 件）に `from-markdown` を実行すると、`unverified_candidates: []`・終了コード 0 になった
- この repo の今の pr-review（`.agents/skills/pr-review/SKILL.md:388-390`）は、Unverified candidates の書き方を「位置・具体的な疑い・…を記載する。なければ「なし」と書く」とだけ定め、`### U-<n>:` の見出しを求めない。移植元の pr-review は見出しを求めている。そのため移植先では、今あるレビューファイルが全て `from-markdown` の言う旧形式に当たる
- 手元の実レビュー 274 本（`reviews/`・`external/resoloop/reviews/`）のうち 46 本が、見出しの無い候補を持つのに空の一覧として成功していた

#### 致命的である理由

`.agents/review-findings.md` の 7 章・8 章は、候補一覧の無いレビュアーのレビューファイルを `from-markdown` で読むと定める。この手順のとおりに今の pr-review のレビューファイルを読むと、未確認の候補が黙って 0 件になり、review-verify（#154）が確かめる対象から消える（手順・ツールのとおりに使うと誤った結果になる）。`candidates_from_markdown` 自身の docstring も「読めなかった指摘は黙って落とさずに `FindingsError` を送出する」と定めていて、それに反する。

#### 修正方針

推奨案: Unverified candidates の節の最初の空でない行が `### ` の見出しか「なし」（前に `- `・`* ` があってもよい）で始まらなければ、`ParsedReview.problems()` に挙げる。`from-markdown` は `FindingsError`（終了コード 65）で止まり、呼び出し側はレビューファイルを直接読む（docstring と 8 章の既存の扱い）。`check-pair` も同じ問題を markdown の問題として報告する。

- 「なし」で始まれば、後に説明や棄却した候補の箇条書きが続いても空の宣言として扱う。実ファイルにこの書き方が複数ある（「なし。検討して棄却した候補: …」）ため
- 最初の行だけで決めるので、見出しの前に導入文を書いた節は止まる（実ファイルには無い）。黙って落とすより、止めて直接読ませるほうを選んだ
- 文書 `.agents/review-findings.md` の 7 章・8 章に、止まる条件と、止まったら直接読むことを 1 行ずつ足した

比べた別案:

- 箇条書きの候補を読み取って `U-<n>` を振る: 箇条書きの区切り（1 候補が何行か）に決まった形が無く、読み違えると候補の数や中身を誤る。形式を移植元から大きく変えることにもなる
- 修正せず、#154 で review-verify が `from-markdown` を使わないようにする: この PR の文書とツールの組み合わせが誤った結果を返す状態でマージすることになる

PR の Spec D-3（`review_findings.py` の挙動は移植元のまま）からの例外は、この 1 点だけである。理由は、移植先の pr-review の様式が移植元と違い、移植元では古いファイルにしか無い書き方が、移植先では今の書き方であるため。

#### 守る条件と影響経路

守る条件: 「`## Unverified candidates` の節の最初の空でない行が `### <ID>:` の見出しでも「なし」でもなければ、`parse_review_markdown` は `problems()` に挙げる（見出しの無い候補の節を、空の一覧として黙って通さない）」

この条件は節の最初の行で決める。次は条件の外で、`problems()` が空のまま候補が落ちうる（自己レビューで確認。手元の実ファイル 274 本には 0 件）。

- 見出しの後、または「なし」の後に続く見出しの無い候補。見出しの本文や「なし」の説明（棄却した候補の箇条書き）と区別できない
- 見出しの書き方が揺れて節として認識されないとき（`## Unverified Candidates`、`## Unverified candidates（1 件）` など）。PR より前からの挙動

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| `candidates_from_markdown`（`from-markdown`） | 修正する | `test_from_markdown_refuses_findings_it_cannot_read` の 2 件（箇条書き、導入文＋箇条書き）。`SWE-2-Max.md` の CLI が終了コード 65・標準出力 0 バイト |
| `check_pair`（`check-pair`） | 修正する | `test_check_pair_refuses_unverified_candidates_it_cannot_read`（問題がちょうど 1 件で今回の理由）。CLI が終了コード 65 |
| 「なし」で始まる節（後に説明・棄却した候補が続くものを含む）、節が無い・空のファイル | 既に満たす（空のまま成功） | `test_from_markdown_reads_an_unverified_section_that_says_none` の 4 件、`test_parse_review_markdown_tolerates_empty_and_missing_sections`。実ファイル 225 本の結果が修正前と同じ |
| `### U-<n>:` の見出しで始まる節（review-records 4.3 節の形） | 既に満たす（従来どおり見出しから読む） | `test_parse_review_markdown_reads_active_findings_and_unverified_candidates`・`test_check_pair_*` ほか既存。実ファイル 3 本の結果が修正前と同じ |
| Critical〜Info の節の、見出しの無い指摘 | 既に満たす（Summary の件数表との照合で止まる。pr-review の様式は件数表を必須にしている） | 既存の `test_from_markdown_refuses_findings_it_cannot_read`（Summary の件） |
| Decided・Resolved・Pending の節 | 対象外（意図して数えない節。`_EXCLUDED_SECTIONS`） | — |
| `review_records.py`（Markdown を読まない）、文書の記入例を `from-markdown` に通すテスト | 既に満たす（Unverified の節を持たない） | `test_document_finding_example_is_read_by_from_markdown` が通る |

#### 失敗時の検証

- 状態全体: `SWE-2-Max.md` の写しと候補一覧を置いた一時ディレクトリで、`from-markdown`・`check-pair` の前後に、ファイルの有無・サイズ・mode・種類・sha256 を比べて一致した。どちらも標準出力は 0 バイトで、終了コード 65。両コマンドは読むだけで、書き込むのは検査に通った後の標準出力だけである（`main()` は `candidates_from_markdown`・`validate_document` の後に書く）
- 負例の異常は 1 つずつ: 3 件とも Summary の件数・指摘の見出し・JSON の形は正しく、見出しの無い候補だけを入れた。`check-pair` の負例は、問題がちょうど 1 件で今回の理由であることまで確かめる
- ガードを外した対照: 修正後の内容を写した隔離 worktree で、`unparsed_unverified` に追加する行を外すと、負例 3 件が全て失敗し、正例 4 件と既存の 4 件は通った（検出力 3/3）。対照の worktree は検証後に消した

### 実行した検証

worktree のルートで実行した（全て終了コード 0）。

- `uv run pytest .agents/scripts tests/scripts/test_superpowers_context.py`: 548 passed、109 subtests passed（修正前の 541 件＋追加 7 件）
- `bash .devcontainer/run-tests.bash`: PASS 32
- `bash scripts/check-layout.sh`: PASS
- ruff の指摘は修正前と同じ 4 件（移植元のまま写した箇所）で、増えていない
- 実ファイル 274 本での修正前後の比較: 225 本は空のまま成功、3 本は見出し形式で結果が同じ、46 本が新たに止まる。46 本の先頭行はすべて実際の候補（前回からの引き継ぎを含む）で、誤検出は無かった

PR の Spec（`2026-10-18-create-reso-world-issue152-review-helpers-design.md`）の D-3 と PR 本文に、今回の例外を書き足した。

#153 への申し送り: 移植元の pr-review の保存の手順は `check-pair` を通す。今回の修正で、Unverified candidates の節を見出しの前の導入文や「（なし）」「該当なし」「None」などで始めたレビューファイルは、`check-pair` で止まる。#153 で pr-review の様式を `### U-<n>:` の見出しにするときは、節を見出しか「なし」で始めるよう定める。

### 結論

結論 1（修正して push）。

### 自己レビュー

修正後に 1 回だけ、3 つの観点を別々のサブエージェントに同時に任せた。3 観点とも致命的な指摘は 0 件。自己レビューの後の修正は文書（この Spec の守る条件の書き方、PR の Spec の D-3、PR 本文）だけで、再レビューはしていない。

- 反証: 実ファイル 274 本の修正前後の比較、CLI、境界の入力（字下げ、CRLF、全角の空白、フェンスで始まる節、節の重複、ファイル末尾の節など）を確かめた
- PR 全体: 修正後の PR 全体を読み、移植元との一致（docstring を除いた構文木）、3.12 の文法、実環境の `resolve`・`fold` を確かめた
- 検証の検出力: 変異 15 種を試し、中心部分（追加の取りやめ、`problems()` から落とす、`check_pair` が足さない、`### ` の例外、「なし」の接頭辞・前方一致）を壊すと新しいテストが失敗することを確かめた。テストの採用基準に反するテストは無い

軽微な指摘の判定（すべて致命的でない）:

| 指摘 | 判定 | 理由 |
| --- | --- | --- |
| 守る条件の書き方が実装より強い（検出力 5） | 直した | 上の守る条件を、節の最初の行に限る書き方にした |
| PR の Spec の D-3・PR 本文が「挙動は移植元のまま」のまま（PR 全体 1） | 直した | 保証の記述を実装に合わせた。Plan の Global Constraints は実装時の指示の記録なので変えない |
| 見出しの前に導入文がある節や、「（なし）」「該当なし」「None」などで始まる節も止まる（反証 1・4、PR 全体 2） | 対応しない | 止まる側に倒れ、呼び出し側はレビューファイルを直接読む。実ファイルには 0 件。#153 への申し送りに書いた |
| 見出しの後・「なし」の後に続く見出しの無い候補、「なしで…」で始まる候補を通す（反証 2・3、PR 全体 3） | 対応しない | 実ファイルには 0 件。見出しの本文や「なし」の説明と区別できないので、上の守る条件の外として書いた |
| 見出しの表記の揺れ・閉じていないフェンスの後の節を認識しない（反証 5） | 対応しない | PR より前からの挙動で、実ファイル 274 本の見出しは全て `## Unverified candidates` |
| 文書 7 章は `### U-<n>:` と書くが、コードは任意の ID の見出しを候補として読む（反証 6、PR 全体 4） | 対応しない | 移植元からの挙動で、見出しから読む候補は落ちない |
| 「なし」を行頭で判定していること、節に入るときの初期化、CLI の終了コード 65 をテストで固定していない（検出力 1〜4） | 対応しない | コードは正しく動いている（手で確認）。CLI の終了コードは全ての `FindingsError` に共通の処理 |
| `review-findings.md` 2 章の保存先が、今の pr-review（`external/resoloop/reviews/`）と違う（PR 全体 5） | 対応しない | 文書は #153 の後の配置を書いていて、`review_target.py` の挙動とは一致する。切り替えは #153 の担当 |
| `--code-root` に相対パスを渡すと終了コード 2 でなく 7（PR 全体 6） | 対応しない | PR の Spec D-4 のとおり |

### 作業時間

着手 11:26Z。所要時間と内訳は、状況コメントと完了報告に書いた。
