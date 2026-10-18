.. _agent_runner_devin:

========================
Devin CLI adapter
========================

概要
====

``devin`` の非対話実行を runner に接続する adapter である。
依頼を attempt 内の ``prompt.txt`` に保存し、標準出力の回答と ``export.json`` の ATIF 形式の記録をローカルで解析する。

起動と入力
==========

次の形式で起動する。
``MODEL`` には agent 定義の値、各ファイルには attempt 内の絶対パスを渡す ::

    devin -p --prompt-file FILE --export FILE --model MODEL --permission-mode dangerous --respect-workspace-trust false

標準入力は空にし、依頼本文を argv に含めない。
JSON 形式の役割では、空でない JSON object を返す指示をファイルに加える。
``role.skills`` と ``agent.skill_sources`` の設定もファイルに反映し、存在する設定済み skill の絶対パスを明記する。
追加の ``agent.args`` は末尾に渡す。

観測する情報と完了条件
======================

ATIF の ``agent.model_name`` 、 ``agent.version`` 、 ``session_id`` をそれぞれ model、CLI の版、session ID として返す。
未観測の値は null とする。
専用の provider・effort 選択オプションは確認しておらず、設定値から観測値を補わない。

標準出力が空、export が存在しない・壊れている、最後の step が最終 agent 応答でない場合は失敗とする。
空の最終応答と tool 呼び出しが残る最終 step も未完了として扱う。
認証・承認の診断は成功候補より優先し、非ゼロ終了の判定と停止確認は runner が行う。
JSON 回答の後ろの通常の進捗行は許容するが、後続の壊れた JSON や認証・承認の診断は失敗とする。
回答本文が認証を話題にしただけでは失敗にしない。

ATIF の tool 引数に skill のパスが現れても、成功した読み取りや全文の確認は証明できない。
この adapter は ``skill_versions`` を空の map として返す。
runner は保持する export を collect 前に秘匿値の除去処理に通す。
意図して保存する prompt には資格情報を含めない。

検証と制約
==========

移植元は commit ``a47b2065fddad76b7475752fd0088af0733de204`` の Devin adapter と偽 CLI テストである。
同梱の旧実機記録は Devin 3000.11.3 に基づくものであり、この環境での成功確認ではない。
事前調査ではインストール済み 3000.11.92 の help に上記の起動オプションがあることを確認した。
今回の実装では実 CLI・モデル・API を起動していない。
ATIF の構造は移植元の観測に基づき、現在の CLI による実機検証は未実施である。

偽 CLI の起動、入力、成功と失敗の解析、export の保持と秘匿値除去を検証する ::

    uv run pytest tools/agent_runner/tests/adapters/devin -q

以上
