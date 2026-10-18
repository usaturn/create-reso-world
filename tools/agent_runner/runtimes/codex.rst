.. _agent_runner_codex:

================================
Codex ランタイムアダプター
================================

.. _agent_runner_codex_overview:

概要
====

``tools.agent_runner.adapters.codex`` は ``codex exec`` を非対話で起動し、
JSONL の最終応答と同じセッションの rollout から結果を収集する。
収集処理はローカルファイルだけを読み、CLI を追加起動しない。

.. _agent_runner_codex_launch:

起動と入力
==========

起動引数は次の形式である ::

    codex exec --json -s <sandbox> -m <model> [-c model_reasoning_effort=<effort>] [args...] -

prompt は末尾の ``-`` と組み合わせて標準入力へ渡す。
本文を引数へ入れない。
読み取りロールでは ``read-only`` 、書き込みロールでは ``workspace-write`` を使う。
対話的な承認や認証の操作は行わず、失敗時に別モデルへ切り替えない。

``agent.model`` は ``-m`` 、設定済みの ``agent.effort`` は
``-c model_reasoning_effort=...`` へ渡す。
汎用の provider 選択引数は実装していない。
``agent.provider`` の設定だけで provider の選択や観測を保証しない。

``role.skills`` は ``$<name>`` 形式で prompt に追加する。
``agent.skill_sources`` に対応ファイルがある場合は、共有の解決処理で
最初に見つかった ``<source>/<name>/SKILL.md`` の絶対パスを示し、読み込みを指示する。
設定しただけでは skill の読み込みを観測したことにはならない。

.. _agent_runner_codex_collection:

応答と失敗の判定
================

``item.completed`` の ``agent_message.text`` を最終応答とし、
その後の ``turn.completed`` を必要とする。
後続の未完了ターン、不正な message 、壊れた JSON らしいイベントがあれば、
先行する成功応答を再利用せず ``response_failed`` とする。
JSON ではない通常の進捗行だけで正常完了を無効にしない。
JSON 形式の結果には空でないオブジェクト、text 形式には空でない本文を必要とする。

``error`` / ``turn.failed`` は応答本文より優先する。
stderr 、非 JSON の stdout 行、失敗イベントの診断に認証要求があれば
``awaiting_authentication`` 、承認要求があれば ``awaiting_approval`` とする。
成功応答やツール出力に含まれる認証関連の単語だけでは失敗にしない。
終了コードが非ゼロの場合は、ランナー本体が成功を拒否する。

.. _agent_runner_codex_identity:

観測する identity
=================

``session_id`` は ``thread.started.thread_id`` から得る。
パス区切りやワイルドカードを含む ID 、不正な型、異なる複数 ID は拒否する。
``model`` / ``provider`` / ``effort`` / ``cli_version`` は同じセッションの
rollout にある ``payload.model`` / ``model_provider`` / ``effort`` /
``cli_version`` の観測値を使う。
要求した設定値を観測値へコピーしない。

rollout は子プロセスへ渡した ``context.environment`` の ``CODEX_HOME`` 、
未設定なら ``HOME/.codex`` を使う。
直接呼び出しで環境が指定されていない場合だけ ``os.environ`` を使う。
``sessions/<年>/<月>/<日>/rollout-<日時>-<thread_id>.jsonl`` を探索し、
ファイル名とセッションメタデータを確認する。
設定したランタイムの保存先から逸脱する symlink は読まない。
一致するファイルや観測フィールドがなければ対応項目は null のままである。
設定ファイルや認証ファイルを使って補完しない。

``skill_versions`` は、単純な ``cat <絶対パス>/SKILL.md`` または
``/bin/bash -lc 'cat <絶対パス>/SKILL.md'`` の成功イベントから得る。
``command_execution`` が ``completed`` 、終了コードが 0 で、
``aggregated_output`` が現在の UTF-8 の生バイトと完全一致するときだけ
共有の検証処理で SHA-256 を記録する。
失敗・部分読み込み・変更済みや削除済みのファイル・複合コマンド・単なる言及では記録しない。

.. _agent_runner_codex_verification:

検証と出所
==========

この移植では偽 CLI による単体テストとランナー統合テストを実行する。
実モデルへの接続、ログイン、認証設定の変更は行っていない。
実機での成功確認は、この環境では未実施である。

移植元は snapshot ``a47b2065fddad76b7475752fd0088af0733de204`` の
同名アダプターとテストである。
移植元の文書には 2026-10-07 UTC の ``codex-cli 0.160.1`` による
読み取り・指定 skill ・書き込みの実機記録があるが、この移植の成功実績とは区別する。
事前調査はインストール済み ``codex-cli 0.163.0`` の help/version で引数を確認した。
現行 CLI の JSONL / rollout 形式は実モデルでは再検証していない。

以上
