.. _agent_runner_cursor:

================================
Cursor ランタイムアダプター
================================

.. _agent_runner_cursor_overview:

概要
====

``tools.agent_runner.adapters.cursor`` は Cursor Agent CLI の ``agent`` を非対話で起動し、JSONL イベントから最終応答と観測した identity を収集する。
収集時にはローカルログだけを解析し、CLI を追加起動しない。

.. _agent_runner_cursor_launch:

起動と入力
==========

起動引数は次の形式である ::

    agent -p --output-format stream-json --trust -f [--sandbox disabled] --model <model> [args...]

prompt は標準入力に渡し、本文を引数には含めない。
どのロールにも ``-f`` を付け、``writes = false`` のロール（``inspect`` ・ ``self-review`` ・ ``fix-check``）にだけ ``--sandbox disabled`` を足す（#201）。
``writes = true`` のロールは #201 の前と同じく ``-f`` だけで起動する。
担当の名前・モデルでは分けず、runtime が ``cursor`` の担当は一次担当でも fallback でも同じ起動になる。
``--trust`` は新しい worktree を信頼済みとして扱う指定であり、対話による trust 確認は行わない。
``agent.model`` は ``--model`` に渡す。
``agent.effort`` があれば ``model[effort=<value>]`` 形式にする。
既にブラケット指定がある model と別の effort 設定は、二重の指定を避けるため起動準備で拒否する。
汎用の provider 選択引数は実装しておらず、``agent.provider`` の設定だけでは provider の選択を保証しない。
認証操作や失敗時のモデル切り替えは行わない。

次の 3 つは、#201 で ``2026.10.19-6bbf2c4`` の ``agent --help`` を読んで確かめた。

- ``-f`` は、利用者の allowlist（``~/.cursor/cli-config.json`` の ``permissions.allow``）に無いシェルのコマンドも確認なしで実行する。
  明示的に拒否したもの（``permissions.deny``）は ``-f`` でも拒否される。
- ``--sandbox disabled`` は利用者の設定（``sandbox.mode``）を上書きする。
  利用者が対話用に sandbox を有効にしていても、``writes = false`` のロールは同じ起動になる。
- ``--mode ask`` ・ ``--mode plan`` は read-only のモードである。

``--mode ask`` ・ ``--mode plan`` は使わない。
#201 までは ``writes = false`` のロールを ``--mode ask`` で起動していた。
usaturn/agent-workspace#753 の観測では、Ask mode でシェルのコマンドが拒否され、PR レビュー（``inspect``）の担当が pr-review の helper（``review_run.py prepare`` ・ ``complete``）を実行できずに PR 修正ループで rejected になった。
この環境では #201 の前の起動での失敗を再現していない。

``--sandbox disabled`` を明示するのは、Cursor の sandbox が helper の書き込み先を拒否するからである。
pr-review の helper は、親の checkout の ``reviews/`` の保存先、Git の共有ディレクトリ（保存のロック・レビュー用 worktree の登録）、uv のキャッシュに書き（``review_run.helper_write_exceptions``）、PR の取得に ``gh`` ・ ``git fetch`` でネットワークを使う。
usaturn/agent-workspace#753 の観測（merge commit ``6e7b16e5e5de11e4beb711b4a5a84f5f274249e1`` の ``tools/agent_runner/runtimes/cursor.rst``）では、sandbox は worktree と ``/tmp`` の外・共有 ``.git`` ・ HOME の下への書き込みとネットワークを拒否した。
同じ観測で ``-f`` のときは sandbox が掛からなかったが（``2026.10.18-ea085cb``）、この挙動は文書に無く版によって変わりうるので頼らない。
この環境では sandbox の範囲を再観測していない。

``writes = false`` は、runner が依頼の冒頭に書く指示（``This is an instruction, not a sandbox.``）であり、Cursor の sandbox や OS による書き込みの禁止ではない。
claude-code ・ devin ・ pi も、``writes`` によらずシェルを使える起動である。

``role.skills`` は共有の ``prompt_lines`` で prompt に追加する。
``agent.skill_sources`` から最初に見つかった ``<source>/<name>/SKILL.md`` があれば、その絶対パスでの読み込みを指示する。
相対 source は work_dir を基準に解決する。
指定しただけでは、読み込みを観測したことにはならない。

.. _agent_runner_cursor_collection:

応答と失敗の判定
================

最終応答には ``type: result`` 、``subtype: success`` 、``is_error: false`` と文字列の ``result`` を必要とする。
JSON 形式には JSON オブジェクト、text 形式には空でない本文を必要とする。
散文と JSON が混在するときは最初の JSON オブジェクトを取り出すが、不正な外側の JSON から内側だけを取り出して成功にはしない。

``error`` イベント、不正な result 、壊れた JSON らしいイベントがあれば、先行する成功結果を再利用せず ``response_failed`` とする。
成功 result の後に ``assistant`` または新しい ``system`` / ``init`` が出た場合、その応答に対応する新しい完了 result を必要とする。
未完了のまま終われば以前の payload は返さず、新しい完了 result が出ればその payload を採用する。
通常の通知・進捗行は成功を無効にしない。
stderr 、非 JSON の stdout 行、失敗イベントの診断に認証要求があれば ``awaiting_authentication`` 、trust や承認要求があれば ``awaiting_approval`` とする。
成功応答や prompt echo の認証関連の単語だけでは失敗にしない。
終了コードが非ゼロの場合はランナー本体が成功を拒否する。

.. _agent_runner_cursor_identity:

観測する identity
=================

``model`` と ``session_id`` は最後の ``system`` / ``init`` イベントから得る。
新しい init に値が無ければ、以前のセッションから補わず null にする。
model は CLI が返す表示名である。
未観測の値は要求設定から補完せず null にする。
``provider`` / ``effort`` / ``cli_version`` は、このイベント形式では観測しておらず null のままである。

``skill_versions`` は完了した ``readToolCall.result.success`` の結果だけを使う。
結果に返された絶対パスが ``**/skills/**/SKILL.md`` に一致し、``exceededLimit: false`` 、空でない読み込み、``readRange.startLine: 1`` と ``endLine == totalLines`` が必要である。
共有の ``verified_versions`` で、返された ``content`` が現在のファイルの UTF-8 の生バイトと完全一致する場合だけ SHA-256 を記録する。
開始イベント、引数だけのパス、部分読み込み、失敗、本文の言及、内容の欠落や不一致では記録しない。
読み込みを確認できなければ空 map のままである。

.. _agent_runner_cursor_limits:

既知の制限
==========

- ``writes = false`` は runner の指示であり、Cursor の sandbox でも OS でも保証しない。
  ``-f`` のため、担当はファイルを書き換えられる。
  ほかの checkout の変更は、runner の ``outside_changes`` ・ ``checkout_audit`` が事後に報告するだけで、任意のパスへの書き込みは防がない。
- ``-f`` でも、利用者が ``permissions.deny`` に書いたコマンドは拒否される（CLI のヘルプ）。
  helper が使うコマンド（``uv`` ・ ``git`` ・ ``gh`` など）を拒否すると、PR レビューの担当は完了できない。
- ``writes = true`` のロールには ``--sandbox`` を付けないので、sandbox の扱いは利用者の設定（``sandbox.mode``）と ``-f`` の挙動に従う。
- ``--sandbox disabled`` の要否は usaturn/agent-workspace#753 の観測による。
  この環境の利用者の設定は ``sandbox.mode = "disabled"`` なので、ここでの実機の確認は ``--sandbox disabled`` の効果を独立には確かめていない。

.. _agent_runner_cursor_verification:

検証と出所
==========

この移植では偽 CLI による単体テストとランナー統合テストを実行する。
#201 の起動は、``prepare`` の単体テストと、偽 CLI が受け取った引数を返す runner の統合テストで確かめる。
統合テストは、任意の名前の担当と fallback で起動した担当が、``inspect`` ・ ``self-review`` ・ ``fix-check`` の ``writes = false`` のロールで同じ起動になることを確かめる。
認証設定の変更は行っていない。

移植元は snapshot ``a47b2065fddad76b7475752fd0088af0733de204`` の同名アダプター、偽 CLI 、テストである。
移植元の文書には 2026-10-07 UTC の ``2026.10.01-e373342`` による読み取り・指定 skill ・書き込みの実機記録があるが、この移植の成功実績とは区別する。
事前調査ではインストール済み ``2026.10.16-e3cb207`` の help/version で起動引数を確認した。
#201 より前は、この環境で実モデルを起動していない。
#201 の実機の確認は下の「実機の確認（#201）」にある。
usaturn/agent-workspace#753 の実機の記録（同 PR の ``runtimes/cursor.rst`` の「実機 run（#752）」）は、この環境の成功実績とは区別する。
共通の入出力仕様は ``tools/agent_runner/interfaces.rst`` にある。

.. _agent_runner_cursor_live_201:

実機の確認（#201）
------------------

2026-10-20 UTC、この環境の Dev Container で、#201 の adapter（commit ``d6b9daf``）を runner 経由で起動した。
CLI は ``2026.10.19-6bbf2c4``（ログイン済み）で、どの run の前後でも版は変わらなかった。
利用者の ``~/.cursor/cli-config.json`` は ``sandbox.mode = "disabled"`` 、``approvalMode = "allowlist"`` 、``permissions.allow = ["Shell(ls)"]`` 、``permissions.deny = []`` で、run の前後で ``sandbox`` ・ ``approvalMode`` ・ ``permissions`` は変わらなかった。
雛形の担当の定義から adapter が組んだ ``inspect`` の起動は次のとおり（prompt は標準入力） ::

    agent -p --output-format stream-json --trust -f --sandbox disabled --model auto
    agent -p --output-format stream-json --trust -f --sandbox disabled --model grok-4.7-xhigh

読み取りとシェル（``inspect`` 、``writes = false``）:
親の ``tmp/agents/`` の下に作った使い捨ての git リポジトリ（commit 1 つ、``marker.txt`` に ``8642``）を対象に、``marker.txt`` の読み取りと、``date -u +%Y`` ・ ``uv --version`` ・ ``mktemp -d`` で作ったディレクトリへの書き込み・読み取り・削除を 1 回の依頼で求めた。
担当ごとに 1 回ずつ実行した。

.. list-table::
   :header-rows: 1

   * - 担当
     - 結果
     - 観測した model
     - 所要
   * - ``cursor``
     - ``success`` 、payload ``{"marker": 8642, "year": "2026", "uv": "uv 0.13.3 (x86_64-unknown-linux-gnu)", "tmp": "ok"}``
     - ``Auto``
     - 29.6 秒
   * - ``cursor-grok47``
     - ``success`` 、同じ payload
     - ``Grok 4.7 256K Extra High``
     - 31.1 秒

どちらも終了コード 0 、``stop_confirmed`` は true 、``outside_changes`` ・ ``checkout_audit`` は空。
stdout には完了した ``readToolCall``（``marker.txt``）と ``shellToolCall``（3 つの操作を 1 つのコマンドにまとめたもの、``exitCode: 0``）が 1 つずつあった。
runner の worktree は変わらなかった（``git status --porcelain`` が空）。
init イベントの ``permissionMode`` は ``default`` だった。

以上
