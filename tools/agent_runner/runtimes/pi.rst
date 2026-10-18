.. _agent_runner_pi:

==========================
Pi ランタイム
==========================

.. _agent_runner_pi_overview:

概要
====

``runtime = "pi"`` は Pi 系 launcher を非対話で起動する adapter である。
プロンプトは標準入力へ渡し、標準出力の NDJSON イベントから応答と観測できた identity を取り出す。
``collect`` は保存済みログの解析だけを行い、追加のプロセスを起動しない。

.. _agent_runner_pi_launch:

起動と skill 指定
====================

起動時の argv は次の形になる。

.. code-block:: text

    <command...> --print --mode json --no-session --no-approve
      [--provider <provider>] --model <model> [--thinking <effort>]
      [--skill <source>]... <args...>

``--print --mode json`` は非対話の JSON イベント出力、 ``--no-session`` はセッション保存の抑止に使う。
Pi 1.3.0 の ``--no-approve`` はプロジェクトローカルの設定ファイルを読み込まない指定であり、ツール利用の全承認を意味しない。
グローバルの拡張や launcher の設定は別途適用され得る。

``agent.skill_sources`` は ``--skill`` へ渡し、相対パスは実行 worktree を基準に絶対パスにする。
``role.skills`` は標準入力の指示へ追加する。
設定された source の下に対象の ``SKILL.md`` があれば、実行 worktree を基準に解決した絶対パスを明示し、native discovery より優先するよう指示する。
JSON の役割では最終回答を JSON object にする指示も加える。

.. _agent_runner_pi_collection:

応答と失敗の判定
====================

最後の ``agent_end`` に含まれる最後の assistant を回答に採用する。
その後の ``agent_settled`` が必須であり、先に出た settlement や以前の成功だけでは成功にしない。
後続の ``agent_start`` や ``turn_start`` がある場合は、次の実行が未完了として扱う。
``agent_settled.aborted = true`` または中断を示す ``stopReason`` は ``interrupted`` になる。

正常な ``stopReason`` と、役割に対応した空でない JSON object または text を要求する。
Pi の JSON 出力は失敗でも終了コード 0 になる場合があるため、イベントの欠落、異常な終了理由、不正な応答は ``response_failed`` とする。
JSON では object 全体か JSON code fence 内の object を受け付ける。
非ゼロ終了は runner が失敗として扱う。

stderr と明示的なエラーイベント、失敗した最終 assistant の診断内容から認証待ち・承認待ちを分類する。
これらの診断は一見有効な回答より優先する。
成功した回答やプロンプト、通常のツール出力に認証に関する語が含まれても、それだけでは認証待ちにしない。
JSON でない通知行や壊れたイベントは無視し、完了条件は別途検査する。

.. _agent_runner_pi_identity:

identity の観測範囲
========================

- ``model`` と ``provider`` は最終 assistant の同名フィールド、 ``effort`` は ``thinkingLevel`` から取得する。
- ``session_id`` は ``session.id`` から取得する。
- 未観測のフィールドは null とし、要求された設定値をコピーしない。CLI 版は現在のイベントから取得せず null とする。
- ``skill_versions`` は同じ ``toolCallId`` の native ``read`` 開始と成功した完了を対応付け、読み取った全文が現在の UTF-8 ファイル内容と一致した場合だけ SHA-256 を記録する。

範囲指定、切り詰め、読み取り失敗、設定されただけの source、単なるパスの出現からは skill の版を推測しない。
全文を証明できない CLI 出力では ``skill_versions`` が空でも正常である。

.. _agent_runner_pi_verification:

検証の出所と制限
====================

移植元 snapshot ``a47b2065fddad76b7475752fd0088af0733de204`` の runtime 文書には、 Pi 1.0.4 と ``pigs`` の実機観測がある。
それは移植元の記録であり、この環境での実機成功を示さない。
本変更では偽 launcher を使い、標準入力、起動引数、完了系列、認証・承認待ち、非ゼロ終了、観測値と skill 読み取り証拠を検証した。
実モデル・API の実行や認証変更は行っていない。

この環境の読み取り専用調査では Pi 1.3.0 の help とローカル実装を確認した。
各 provider の接続、launcher の前提条件、モデルの利用可否は別途実機確認が必要である。
``agent.args`` は末尾へ渡すため、非対話指定やモデル指定を上書きしない引数を設定する。

以上
