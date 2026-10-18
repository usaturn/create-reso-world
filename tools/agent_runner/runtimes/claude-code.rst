.. _agent_runner_claude_code:

==========================
Claude Code ランタイム
==========================

.. _agent_runner_claude_code_overview:

概要
====

``runtime = "claude-code"`` は Claude Code を非対話で起動する adapter である。
プロンプトは標準入力へ渡し、保存した NDJSON イベントから最終回答と観測できた identity を取り出す。
``collect`` はローカル解析だけを行い、追加のプロセスを起動しない。

.. _agent_runner_claude_code_launch:

起動と skill 指定
====================

起動時の argv は次の形になる。

.. code-block:: text

    <command...> -p --output-format stream-json --verbose
      --model <model> [--effort <effort>]
      --dangerously-skip-permissions <args...>

``-p`` と ``--output-format stream-json --verbose`` で、標準入力を受け取る非対話実行とイベント出力を指定する。
``--dangerously-skip-permissions`` はツール承認の対話を省略するため、呼び出し側が用意した隔離 worktree で実行する。
``agent.effort`` は設定時だけ ``--effort`` に渡す。
``agent.provider`` を選択する汎用 CLI 引数は適用しない。
``agent.args`` は末尾に渡すため、非対話指定やモデル指定を上書きしない引数を設定する。

``role.skills`` は標準入力の指示へ追加する。
``agent.skill_sources`` の下に対象の ``SKILL.md`` があれば、実行 worktree を基準に解決した絶対パスを明示し、CLI の通常の探索より優先するよう指示する。
JSON の役割では最終回答を JSON object にする指示も追加する。
プロンプト本文を argv に含めない。

.. _agent_runner_claude_code_collection:

応答と失敗の判定
====================

最後の ``result`` イベントを最終回答に使う。
``subtype = "success"`` かつ ``is_error`` が偽であり、役割に対応した空でない JSON object または text が必要である。
JSON は object 全体か JSON code fence 内の object を受け付ける。
完了イベントの欠落、不正な応答、明示的なエラー、成功イベント後に続く未完了の応答は ``response_failed`` とする。
JSON でない通知行や壊れた行は無視し、完了条件を別途検査する。

stderr、明示的な ``error`` イベント、 ``error`` を持つ assistant、失敗した result の診断内容から認証待ち・承認待ちを分類する。
これらの診断は一見有効な回答より優先する。
通常の回答やツール出力に認証に関する語があるだけでは認証待ちにしない。
非空の ``permission_denials`` は ``awaiting_approval`` 、中断を示す result subtype は ``interrupted`` になる。
非ゼロ終了は runner が失敗として扱う。

.. _agent_runner_claude_code_identity:

identity の観測範囲
========================

- ``model`` は ``system/init.model`` を初期値とし、後続の ``assistant.message.model`` があれば更新する。
- ``session_id`` と ``cli_version`` は init の ``session_id`` と ``claude_code_version`` から取得する。
- 未観測のフィールドは null とし、要求された設定値をコピーしない。 ``provider`` と ``effort`` はこの解析では観測せず null とする。
- ``skill_versions`` は空 map とする。利用可能な skill の一覧、設定された source、 ``Skill`` ツールの呼び出しは、成功した全文読み取りの証拠にならない。

この形式のイベントだけでは ``SKILL.md`` の全文と現在のファイル内容が一致することを証明できないため、ファイル名だけから版を推測しない。

.. _agent_runner_claude_code_verification:

検証の出所と制限
====================

移植元 snapshot ``a47b2065fddad76b7475752fd0088af0733de204`` の runtime 文書には、Claude Code 2.1.291 の実機完走記録がある。
それは移植元の記録であり、この環境での実機成功を示さない。
今回の読み取り専用調査では、インストール済み Claude Code 2.1.302 の help に起動引数が存在することを確認している。
イベント形式は移植元の観測に基づき、この環境での実モデル実行による確認は行っていない。

本変更は偽 CLI で標準入力、起動引数、JSON/text、完了条件、認証・承認待ち、中断、非ゼロ終了、観測値と skill 指定の区別を検証する。
認証変更や実モデル・API の実行は行わない。

以上
