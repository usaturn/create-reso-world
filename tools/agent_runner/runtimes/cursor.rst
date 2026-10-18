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

    agent -p --output-format stream-json --trust (--mode ask | -f) --model <model> [args...]

prompt は標準入力に渡し、本文を引数には含めない。
読み取りロールには ``--mode ask`` 、書き込みロールには ``-f`` を付ける。
``--trust`` は新しい worktree を信頼済みとして扱う指定であり、対話による trust 確認は行わない。
``agent.model`` は ``--model`` に渡す。
``agent.effort`` があれば ``model[effort=<value>]`` 形式にする。
既にブラケット指定がある model と別の effort 設定は、二重の指定を避けるため起動準備で拒否する。
汎用の provider 選択引数は実装しておらず、``agent.provider`` の設定だけでは provider の選択を保証しない。
認証操作や失敗時のモデル切り替えは行わない。

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
通常の進捗行は成功を無効にしない。
stderr 、非 JSON の stdout 行、失敗イベントの診断に認証要求があれば ``awaiting_authentication`` 、trust や承認要求があれば ``awaiting_approval`` とする。
成功応答や prompt echo の認証関連の単語だけでは失敗にしない。
終了コードが非ゼロの場合はランナー本体が成功を拒否する。

.. _agent_runner_cursor_identity:

観測する identity
=================

``model`` と ``session_id`` は ``system`` / ``init`` イベントから得る。
model は CLI が返す表示名である。
未観測の値は要求設定から補完せず null にする。
``provider`` / ``effort`` / ``cli_version`` は、このイベント形式では観測しておらず null のままである。

``skill_versions`` は完了した ``readToolCall.result.success`` の結果だけを使う。
結果に返された絶対パスが ``**/skills/**/SKILL.md`` に一致し、``exceededLimit: false`` 、空でない読み込み、``readRange.startLine: 1`` と ``endLine == totalLines`` が必要である。
共有の ``verified_versions`` で、返された ``content`` が現在のファイルの UTF-8 の生バイトと完全一致する場合だけ SHA-256 を記録する。
開始イベント、引数だけのパス、部分読み込み、失敗、本文の言及、内容の欠落や不一致では記録しない。
読み込みを確認できなければ空 map のままである。

.. _agent_runner_cursor_verification:

検証と出所
==========

この移植では偽 CLI による単体テストとランナー統合テストを実行する。
実モデルへの接続と認証設定の変更は行っていない。
この環境での実機の成功確認は未実施である。

移植元は snapshot ``a47b2065fddad76b7475752fd0088af0733de204`` の同名アダプター、偽 CLI 、テストである。
移植元の文書には 2026-10-07 UTC の ``2026.10.01-e373342`` による読み取り・指定 skill ・書き込みの実機記録があるが、この移植の成功実績とは区別する。
事前調査ではインストール済み ``2026.10.16-e3cb207`` の help/version で起動引数を確認した。
現行 CLI のイベント形式とモデルの利用可否は実モデルでは再検証していない。
共通の入出力仕様は ``tools/agent_runner/interfaces.rst`` にある。

以上
