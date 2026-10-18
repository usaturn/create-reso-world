# PR #170（Issue #151 DSH headless レビュアー）のレビュー指摘の選別と修正

## 管理・実行許可

- 対象: `usaturn/create-reso-world` PR #170（`feat/issue-151-dsh-headless`、`Closes #151`）
- 状態: `completed`
- 実行許可: 利用者の `/review-fix-planning #170`。計画で止める指示が無いので完遂の流れで進めた。この PR の承認済み実装修正と、push・状況コメントの投稿の実行許可として扱う。内容の承認（`approved`）ではない
- 入力: `reviews/usaturn/create-reso-world/#170-feat-issue-151-dsh-headless/` の 4 ファイル。対象 HEAD はすべて `7bd3d6552582`
  - `claude-opus-5-5.md`（Medium 1・Low 3、Approve）
  - `gpt-6.1-sol.md`（High 1・Medium 1・Low 1、Request changes）
  - `SWE-2-Max.md`（Low 1・Info 1、Approve）
  - `commandcode-deepseek-deepseek-v4.1-flash.md`（Low 2・Info 1、Needs manual verification）
- 現行 HEAD: `7bd3d65525827972b2c1fe856b7b82f096c6b1a3`（レビューの対象 HEAD と同じ）。base は `origin/main` の `a024a22`（PR の分岐点から進んでいない）
- 作業場所: 既存の worktree `/workspaces/reso-world/.worktrees/issue-151-dsh-headless`（head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致したので再利用した）
- 以前のレビュー修正: なし（同じテーマの review-fix Spec は無い。PR の履歴の `7bd3d65` は PR 作成前の独立レビューで直した、モデル経路の変更の拒否で、今回の守る条件とは別）。「同じ条件の再発と設計の見直し」のきっかけ 1〜3 には当たらない

## 結論

**結論 1: 修正して push する。** 4 人のレビュアーが挙げた「/tmp 配下の checkout で DSH の sandbox のテスト 2 件が偽の失敗になる」だけを直す（テスト 2 ファイル、7 行）。他の指摘は現行 HEAD で事実として確かめたが、致命的ではない。そのうち実在する制約で PR の説明と食い違い得る 4 件（G-H1・M-1・L-1・O-L2）は、PR の説明の既知の制限に条件と回避方法を書き足す。

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 4（同じ原因。修正は 1 つ） |
| 対応しない | 8 |

## 指摘の振り分け

ID の接頭辞は O = claude-opus-5-5、G = gpt-6.1-sol、S = SWE-2-Max、D = commandcode-deepseek-deepseek-v4.1-flash。

| ID | 内容 | 区分 | 根拠（1 行） |
| --- | --- | --- | --- |
| O-L3・G-L1・S-L1・D-L2 | checkout が /tmp 配下にあると、sandbox の writable profile の `--tmpfs /tmp` が venv の `sys.executable` を隠し、`test_adapter_cache_paths_are_writable_with_its_scoped_runner` と `test_explicit_grants_preserve_neighboring_host_files` が `bwrap: execvp` で失敗する | 対応する | (a) 現行 HEAD の /tmp の隔離 worktree で 2 failed / 122 passed を再現。pr-review・review-fix-planning は /tmp の使い捨て worktree でテストを流す手順なので、手順のとおりに使うと実装に欠陥が無くても失敗する |
| G-H1 | DSH 標準の `write`・`edit` ツールは scoped runner を通らず、DSH の workspace-write（worktree・ホストの /tmp・TMPDIR）に書ける | 対応しない | 事実だが、runner の書き込みの規則は全 runtime で指示であり sandbox ではない（`interfaces.rst:299`・`runner.py:396-399`）。scoped runner はコマンド実行を絞る追加の層で、ファイル操作ツールの範囲は DSH 0.2.0-rc.2 が既定とする意味のまま。既知の制限に書き足す |
| O-M1・G-M1 | 開始後の認証失敗・DSH 自身の中断で、ログはあるが `assistant/message` が無いと、`awaiting_authentication`・`interrupted` が `response_failed` に上書きされる | 対応しない | 現行 HEAD で再現。ただし失敗として扱われる点は変わらず（`awaiting_authentication` と `response_failed` はどちらも fallback へ進む）、診断に使う stdout.log・stderr.log は残る。既知の制限に書き足す |
| O-L1・D-L1 | tool_result のエラー本文に `401`・`403` などが入ると、完了した回答でも `awaiting_authentication` になり payload を捨てる | 対応しない | 現行 HEAD で再現。誤判定でも失敗側に倒れ、fallback へ進む。bash の非ゼロ終了は DSH がエラーにしないので、テストの失敗出力では起きない。既知の制限に書き足す |
| O-L2 | `--output-dir` がシンボリックリンクを経由すると、HOME・TMPDIR の grant が拒否され sandbox 内のコマンドがすべて失敗する | 対応しない | 現行 HEAD で再現（rc 127）。何も実行せずに止まる。既定の出力先（`/tmp` の `mkdtemp`）と、この環境の `/tmp`・`/workspaces/reso-world`・`tmp/` はリンクではなく、到達する構成を示せない。既知の制限に書き足す |
| S-I1 | `docs/maatlog-poc-porting.md` の R-1 の期待値 `[25/25]` が現行の 32 手順と合わない | 対応しない | 同じ文書が「上の rebuild 表は 2026-10-05 の観測記録」と明記し、#151 で変わる点の節も R-2・R-3 だけを挙げる。R-1 のとおり確かめても誤った判断にならない |
| D-I1 | `sandbox_write_paths` を `--grant` にする配線がテストされていない | 対応しない | テストの網羅の指摘で欠陥は再現していない。配線は `dsh.py:210` の 1 行、grant の検証は `test_sandbox.py` が実 bubblewrap で確かめる。この PR では CLI に渡す経路が無く（`cli.py` は渡さない）、#153 以降で使う |

### 対応する: /tmp 配下の checkout での偽の失敗（O-L3・G-L1・S-L1・D-L2）

- 現行 HEAD での確認: `mktemp -d /tmp/review-fix-planning.XXXXXX` の隔離 worktree（HEAD `7bd3d65`）で `uv run --locked pytest tools/agent_runner/tests/adapters/dsh tools/test_support` を実行し、2 failed / 122 passed。stderr はどちらも `bwrap: execvp /tmp/review-fix-planning.…/worktree/.venv/bin/python: No such file or directory`
- 致命的である理由: このリポジトリの pr-review は `/tmp/pr-review-*`、review-fix-planning は `mktemp -d /tmp/...` の worktree で関連テストを実行する。その手順のとおりに DSH のテストを流すと、実装に欠陥が無いのに必ず 2 件が失敗する。今回のレビュアー 4 人全員がこの偽の失敗に当たっており、base が進んだときの review-fix-planning の結論 2（base を merge した一時ツリーでの検証）も通らない
- 修正方針: sandbox の中で起動する probe は標準ライブラリ（`pathlib`・`json`）だけを使うので、`Path(sys.executable).resolve()`（venv の `python` がリンクしているシステムの interpreter。この環境では `/usr/bin/python3.14`）を起動する。sandbox の profile とテストの assertion は変えない。checkout を `--read-root` で見せる案は、検査対象の helper に渡す引数を変え、sandbox で見える範囲を広げるので選ばない

#### 守る条件と影響経路

守る条件: sandbox の中で起動するテストの probe は、checkout の置き場所（/tmp 配下を含む）に関係なく起動でき、書き込みの許可・拒否の検査まで到達する。

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| `test_adapter.py::test_adapter_cache_paths_are_writable_with_its_scoped_runner` の sandbox 内の interpreter | 修正する | /tmp の隔離 worktree と専用 worktree の両方で DSH テストが 124 passed。grant を外した対照で失敗する |
| `test_sandbox.py::invoke` の sandbox 内の interpreter（`test_explicit_grants_preserve_neighboring_host_files`・`test_readonly_does_not_apply_additional_grants`・`test_unsafe_grants_or_profile_never_run_the_command` が使う） | 修正する | 同上 |
| `test_sandbox.py::invoke` の外側の helper の起動（`sys.executable` で `dsh_sandbox.py` を実行） | 既に満たす（sandbox の外で動く） | 同上の実行 |
| `test_sandbox.py::test_missing_bwrap_never_executes_command` の command | 既に満たす（bwrap が無い扱いで command を起動しない） | 同上の実行 |
| `test_runner.py`・`fake_cli.py` の `sys.executable`（偽 CLI と pytest の起動） | 既に満たす（runner が直接起動し、bwrap を通らない） | /tmp の隔離 worktree で `test_runner.py` の 27 件を含む 124 passed |
| `dsh.py` の runnerCommand の `sys.executable`（helper の起動） | 既に満たす（DSH がホスト側で起動する。bwrap の中で動くのは helper が exec する command だけ） | `dsh.py:203-212`・`dsh_sandbox.py:53` の確認 |
| `tools/devenv_migration/tests` の bwrap（`--tmpfs /tmp` を使う 3 ファイル、PR の差分外） | 既に満たす（checkout の `ROOT` を `--ro-bind` し直している） | `test_pi_installer_isolation.py:31-33`・`test_pi_mcp_adapter_migration.py:63-64`・`test_pi_provider_setup.py:61` の確認 |

### 対応しない: G-H1 の扱い

- 現行 HEAD での確認: 導入対象と同じ `@deepseek-ai/*@0.2.0-rc.2` を一時ディレクトリに `npm pack` して読んだ（グローバル導入・CLI の起動・provider の接続はしていない）。`dsh-headless` は `dsh-base` の上に直接載り、`dsh-base` は `tool-fs`（`read`・`write`・`edit` を常に登録し、無効にする設定は無い）と `fs-sandbox` を有効にする。`fs-sandbox` の `checkedTarget` は `dsh-sandbox` の `writableRoots` に含まれるパスへの書き込みを許し、workspace-write の `writableRoots` は workspace・`/tmp`・`os.tmpdir()` を返す。PR の patch はこの 2 つを置き換えていない。DSH 自身も `fs-sandbox` を「containment, not a security boundary」とし、bwrap 側の ephemeral な `/tmp` との違いを既知の差としている
- 致命的でない理由: runner は全 runtime に「writes=…: This is an instruction, not a sandbox.」と渡し、書き込みの規則を強制しない（`interfaces.rst` の `write_exceptions` の節も「sandbox ではない」と明記する）。DSH のファイル操作ツールがホストの /tmp に書けるのは、他の runtime が受ける信頼の前提（指示に従う）と同じで、この PR が新しく開ける経路ではない。scoped runner はコマンド実行を worktree と grant に絞る追加の層として機能している（4 人とも確認）
- 論点（設計の是非）: ファイル操作ツールも grant だけに絞るには、DSH の外側の process 全体を bwrap に入れるか、`tool-fs` を無効にして読み取りを bash に寄せる必要がある。どちらも実 DSH での確認（#151 の rebuild 後）が前提の設計変更なので、この PR では行わない
- 扱い: PR の説明の「sandbox の範囲は書き込み制限です」を、コマンド実行の制限であることと、ファイル操作ツールの範囲、他の担当の記録を範囲から外す回避方法（/tmp の外の `--output-dir`）が分かる形に書き換える

### 対応しない: 既知の制限に書き足すもの（M-1・L-1・O-L2）

- O-M1・G-M1: `write_session` のログを header だけ、header と `request/header` だけに切り詰め、`turn_end` の reason を `MISSING_CREDENTIAL` と `aborted` にした 4 通りがすべて `response_failed`（ログが無い場合は `awaiting_authentication`・`interrupted`）。runner の fallback は `success`・`interrupted`・`timed_out` 以外で次へ進むので、認証失敗の扱いは変わらない。DSH 自身の中断は `interrupted` と違って fallback へ進むが、runner の取り消し・期限切れは runner 側で `interrupted`・`timed_out` に決まる（`runner.py:496-499`）
- O-L1・D-L1: tool_result（status `error`、本文 `tools/agent_runner/runner.py:403: AssertionError`）の後に completed と有効な final が続く stream が `('awaiting_authentication', None)` になることを再現。失敗側に倒れるだけで、誤った payload を成功として返すことは無い
- O-L2: 正規のディレクトリとリンク経由のディレクトリで prepare した runnerCommand に workspace-write の profile と `/bin/true` を渡し、前者は rc 0、後者は rc 127・`dsh-sandbox: grant must be an existing canonical absolute path`

## 確認の範囲

- 全指摘を現行 HEAD のコミット済みの内容で確かめた。挙動の指摘（O-L3 系・M-1・L-1・O-L2）は `mktemp -d /tmp/review-fix-planning.XXXXXX` の隔離 worktree（SHA を照合）で再現し、G-H1 は導入対象の版の配布物のソースで確かめた。隔離 worktree と一時ディレクトリは検証後に `git worktree remove` と `rm -rf` で片付けた
- 変更ファイル 16 件: `dsh.py`・`dsh_identity.py`・`dsh_sandbox.py`・`tools/test_support/dsh.py` とテスト 5 ファイル、Spec の全文を読み、`.devcontainer/` の 4 ファイルと `docs/maatlog-poc-porting.md`・Plan の差分を読んだ。関連する処理は `runner.py` の DSH 専用処理・`_collect`・fallback の判定、`interfaces.rst`、`cli.py` の `--output-dir`
- 自己確認で致命的な欠陥は見つからなかった

## 修正

- `tools/agent_runner/tests/adapters/dsh/test_sandbox.py`: sandbox の中で起動する interpreter を `PYTHON = str(Path(sys.executable).resolve())` にした
- `tools/agent_runner/tests/adapters/dsh/test_adapter.py`: 同じく、sandbox の中で起動する interpreter を `Path(sys.executable).resolve()` にした
- テストの採用基準: 既存のテストを実際に起きた偽の失敗が出ない形に直すもので、新しいテストは足していない

## 検証

| コマンド・手順 | 場所 | 結果 |
| --- | --- | --- |
| `uv run --locked pytest tools/agent_runner/tests/adapters/dsh tools/test_support`（修正前） | /tmp の隔離 worktree（HEAD `7bd3d65`） | 2 failed / 122 passed（再現） |
| 同上（修正後の差分を適用） | /tmp の隔離 worktree | 124 passed |
| 同上（修正後） | 専用 worktree | 124 passed |
| 対照: `dsh_sandbox.py` の writable の mount から grant（`*additions`）を外して `test_sandbox.py` と対象の adapter のテストを実行 | /tmp の隔離 worktree（専用 worktree では行わない） | 2 failed / 5 passed。失敗は `denied != written` と sandbox 内の `mkdir` の失敗で、`execvp` ではない（修正後のテストが書き込みの検査まで到達し、grant の欠落を検出する）。対照の変更は `git checkout` で戻した |
| `uv run --locked pytest tools/agent_runner tools/test_support` | 専用 worktree | 463 passed（61 秒） |
| `bash .devcontainer/run-tests.bash` | 専用 worktree | PASS 33 本 |
| `bash scripts/check-layout.sh` | 専用 worktree | PASS |
| `git diff --check` | 専用 worktree | PASS |

- base は分岐点から進んでいないので、base を merge したツリーでの再検証は不要
- CI: `usaturn/create-reso-world` は private で CI を止めているので確認しない（`AGENTS.md` の「GitHub Actions」）

## 自己レビュー

1 回だけ行った。このリポジトリの Claude Code は利用者の明示依頼なしに Agent を起動しない運用なので、本体が 3 観点を見た。自己レビュー後の修正は無い。

- 反証: `Path(sys.executable).resolve()` の実体が /tmp 配下にあると同じ失敗になるが、この環境の uv はシステムの Python を使い（Issue #122）、`uv python install` もしない。probe は標準ライブラリだけを使うので、venv を通さずに起動しても挙動は変わらない。外側の helper の起動（`sys.executable`）は変えていない
- PR 全体: 修正後の全差分と変更ファイルを読み、上の振り分けのほかに致命的な問題は無かった
- 検証の検出力: grant を外した対照で、修正した 2 件のテストが書き込みの検査で失敗することを確かめた。assertion は変えていない
- 指摘: 0 件
