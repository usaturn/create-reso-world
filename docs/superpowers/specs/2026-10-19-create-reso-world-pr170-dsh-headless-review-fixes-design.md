# PR #170（Issue #151 DSH headless レビュアー）のレビュー指摘の選別と修正

## 現行の判断（2026-10-18、HEAD 392da21 の再検証）

- 対象: `usaturn/create-reso-world#170`、`feat/issue-151-dsh-headless`
- 状態: `completed`。レビュー指摘の選別とローカル検証の完了であり、rebuild 後の実機受け入れの完了ではない
- 実行許可: 利用者が `review-fix-planning` を明示して `#170` を指定。計画だけに留める指示が無いため、同スキルの完遂（既存 PR への記録の反映、修正不要ならマージと関連 Issue の更新）の許可として扱う。内容の承認を記録するものではない
- 検証した HEAD: `392da213fda81844db6776b3830e509133d4e5b4`。全入力の対象 HEAD がその祖先（または同一）であることを確認
- base: `main` / `a024a22626d4ff6daa46e92aa7cb8aae081aa7ac`。取得し直した remote の main と一致し、PR の祖先なので一時 merge の検証は不要
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-151-dsh-headless`。HEAD と clean を確認して既存 worktree を再利用。このセッションで作った worktree・ブランチではないため削除しない
- 文書の選択: 対象 repo・PR・テーマを `docs/superpowers/specs/`・`plans/` で検索し、現行のレビュー修正文書は本ファイル 1 件と確定。同じ文書を更新し、下部に以前の判断を履歴として残す
- 結論: **2 修正不要としてマージする**。解消済み **4** / 対応する **0** / 対応しない **8**。今回のコード・設定・テストの変更は無く、本ファイルのみ更新する

### 入力と全指摘の分類

入力ディレクトリは `reviews/usaturn/create-reso-world/#170-feat-issue-151-dsh-headless/`。以下の 4 ファイルを全文読んだ。接頭辞は O = claude-opus-5-5、G = gpt-6.1-sol、S = SWE-2-Max、D = commandcode-deepseek-deepseek-v4.1-flash。

| ファイル | 冒頭の対象 HEAD | 履歴にある以前の HEAD |
| --- | --- | --- |
| `SWE-2-Max.md` | `392da213fda8` | `7bd3d6552582` |
| `claude-opus-5-5.md` | `392da213fda8` | `7bd3d6552582` |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `392da213fda8` | `7bd3d6552582` |
| `gpt-6.1-sol.md` | `7bd3d6552582` | なし |

| ID | 内容 | 区分 | 現行 HEAD での根拠・判断 |
| --- | --- | --- | --- |
| S-L1 | /tmp の checkout で sandbox テストが偽の失敗 | 解消済み | `fb6b4ad`、`test_sandbox.py:15` と `test_adapter.py:103` の interpreter resolve。/tmp の隔離 worktree で 124 件成功 |
| O-L3 | 同上 | 解消済み | 同じ修正と同じ 124 件の実行で再現しないことを確認 |
| D-L2 | 同上 | 解消済み | 同じ修正と同じ 124 件の実行で再現しないことを確認 |
| G-L1 | 同上 | 解消済み | 古いレビューの対象から既に修正済み。sandbox の profile と assertion は維持 |
| G-H1 | 標準 write/edit は scoped runner を通らずホスト /tmp に書ける | 対応しない | 固定版 fs-sandbox の実装と read→version 付き write で再現。`interfaces.rst:297-299`・`runner.py:396-399` の既存仕様は全 runtime とも書き込み範囲を指示として渡し、強制境界を保証しない。scoped runner はコマンド実行への追加制限。全プロセスを隔離する設計への変更は今回の修正対象にしない。PR 本文に範囲と /tmp 外の output-dir による回避が記載済み |
| O-M1 | 応答前のログで認証・中断の診断が上書き | 対応しない | ログ無しでは認証待ち/中断、同じ stream に正常な応答前ログを加えると response_failed を再現（`dsh.py:299-308`、`dsh_identity.py:124-125`）。認証失敗は同様に fallback。DSH 自身の中断は fallback に進む差があるが、runner 自身の取消・期限切れは独立して保たれる（`runner.py:496-499,546`）。成功を偽らずログは残る。既知の制限に記載済み |
| G-M1 | 同上 | 対応しない | O-M1 と同じ再現・理由。初回認証失敗時の診断ラベルの不正確さとして扱う |
| O-L1 | tool_result の 401/403 で正常 payload を破棄 | 対応しない | 実 DSH の read エラー文言相当を含む completed stream で awaiting_authentication、403 を 402 にすると success を再現（`dsh.py:33-36,116-119`）。1 試行の結果を失い fallback へ進むが、誤った結果を成功として返さない。既知の制限に記載済み |
| D-L1 | 同上（stderr の数値誤分類も含む） | 対応しない | 同じ `_diagnostic` が stderr にも適用される（`dsh.py:290-292`）。安全側の誤分類であり、同じ理由で対応しない |
| O-L2 | symlink 経由 output-dir で全コマンド拒否 | 対応しない | canonical な出力先の runnerCommand は rc 0、symlink 経由は rc 127 を再現（`dsh.py:177-181,210`、`dsh_sandbox.py:15-18`）。何も実行せず拒否する。既定の出力先では発生せず、PR が正規パスを使う回避方法を明記している任意パスの制限 |
| S-I1 | 履歴表 R-1 の [25/25] と現在の step 数の不一致 | 対応しない | 文言は実在するが base から同じ。`maatlog-poc-porting.md:240` は 2026-10-05 の観測記録と明記し、現行手順を README に案内。#151 が更新するのは R-2/R-3。実行ロジックを壊さない履歴表現の問題 |
| D-I1 | sandbox_write_paths の配線テスト不在 | 対応しない | `AdapterContext:19` → `runner.py:428` → `dsh.py:210` の配線を確認。cli.py は引数を渡さず、現在の caller は既定の空 tuple。欠陥が再現した指摘ではなく網羅の提案で、helper の grant 検証は既存実行テストが確認 |

「対応する」は 0 件なので、新しい守る条件・影響経路の表、設計の見直し、失敗時ガードの追加・対照検証は不要。前回修正した interpreter の条件は維持されており、同じ条件の再発には当たらない。実在する制約は全て既存 PR 本文の既知の制限と整合し、今回は PR 本文を変更しない。

### 検証・確認範囲

- PR 差分全体と変更 17 ファイルの全文を確認。実装、テスト 5 ファイルと test-support、installer、README 全文、TOML、移植記録、当初の Spec/Plan、本ファイルを含む。関連する runner の collect / cleanup / fallback、adapter protocol、CLI、interfaces、postCreate の呼出元・検証も確認
- `sp-recon` を同期で 2 件、直列に委譲（読み取り専用）。1 件目は環境・文書、2 件目はテスト・関連呼出元。実行検証は調整役が担当。子が shell 不在で確かめられない HEAD / base の差分と実行結果は調整役が直接照合。README の子が精読しなかった後半も調整役が全文を読んだ
- 挙動の再現は SHA を照合した `/tmp` の隔離 worktree で実行。認証 2 種・中断 1 種のログ有無、tool_result の 403・401 と 402 の対照、正規パスと symlink 経由の runnerCommand を確認
- G-H1 は `@deepseek-ai/dsh-fs-sandbox@0.2.0-rc.2` と依存だけを一時領域へ `--ignore-scripts` で配置し、workspace / private TMPDIR の外にある /tmp の隣接ファイルへの version 付き書き込みを再現。CLI・モデル・認証 API は起動しない。最初の probe はファイル read の戻り値からの version 取得が誤っていたため、stat の version を使う形に直し、終了コード 0 と変更後のバイト列で再確認
- 全再現・ログ・配布物・scratch は `/tmp/review-fix-planning.95PU72/` に閉じ込めた。検証終了後に `git worktree remove --force` の成功を確認して親ディレクトリを削除済み。Spec 作成まで残していない

| 検証 | 場所 | 結果 |
| --- | --- | --- |
| `uv run --locked pytest tools/agent_runner/tests/adapters/dsh tools/test_support -q` | /tmp の隔離 worktree | 124 passed / 12.00 秒 / exit 0 |
| `uv run --locked pytest tools/agent_runner tools/test_support -q` | 専用 worktree | 463 passed / 68.83 秒 / exit 0 |
| `bash .devcontainer/run-tests.bash` | 専用 worktree | 33 本 PASS / exit 0 |
| `bash scripts/check-layout.sh` | 専用 worktree | PASS / exit 0 |
| 認証・中断・tool_result・symlink の再現 | /tmp の隔離 worktree | 上表の状態・payload・終了コードを assertion で確認 / exit 0 |
| 固定版 fs-sandbox の隣接ファイルへの write | 一時領域 | original → changed / exit 0 |
| `git diff --check` | 専用 worktree | PASS |

- 今回は文書のみを更新するので新規テストを作らない（AGENTS.md の採用基準）。スキル自体の変更は無く、skills の追加一括検証は不要
- CI は private の create-reso-world で停止中のため確認対象外。base が進んでいないため統合用の一時 merge は作らない
- 自己確認で新たな致命的欠陥は無し。今回コード修正が無いため「修正後の自己レビュー」は未実施（初期検証の委譲を自己レビューとは数えない）
- 実 DSH のグローバル導入・CLI 起動・provider 接続・rebuild は未実施。これは #116 D-14 / D-21 と README が利用者へ分担した実機受け入れであり、検証済みとは扱わない。マージ後も版・短い依頼 1 回・payload と観測モデルの記録が残作業
- 所要: 18:11 UTC 着手、準備・入力確認約 3 分、文書/関連経路の調査（同期子 2 件）約 6 分、再現・環境回帰・runner 回帰約 7 分、判定・記録約 2 分。公開操作の時間と結果は状況コメント・完了報告に記録する

---

## 以前の判断（HEAD 7bd3d65 に対する初回の修正記録）

以下は `fb6b4ad` のテスト修正につながった以前の記録であり、現行の分類件数は上節を基準とする。

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
