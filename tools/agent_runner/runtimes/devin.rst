.. _agent_runner_devin:

========================
Devin CLI adapter
========================

概要
====

``devin`` の非対話実行を runner に接続する adapter である。
依頼を attempt 内の ``prompt.txt`` に保存し、標準出力と ``export.json`` の ATIF 形式の記録をローカルで解析する。
回答は export の最後の agent 応答とする。

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
``devin -p`` の標準出力には、実行中のすべての agent 応答が区切りなしで連結される。
そのため回答は最終 ATIF 応答とし、標準出力がその回答で終わることだけを確かめる。
回答の後ろには改行で区切った通常の行を許すが、回答と同じ行に続く文字と、後続の JSON や壊れた JSON は失敗とする。
JSON 形式の役割では、最終 ATIF 応答を ``json_result.json_object`` で読み、payload は最後にデコードできた JSON object とする。
文章の後に JSON が続く形（fence 付きを含む）を受け付け、訂正では最後の有効な object を採用する。
壊れた object 候補がある場合は応答全体を拒否し、前の有効な JSON にフォールバックしない。
閉じたインラインコード span・閉じた非 JSON fence の中の壊れた候補は拒否に使わない（移植元の既知の限界は ``json_result`` の docstring に従う）。
最後の発話だけを読み、途中の発話や stdout から JSON を探さない隔離は変わらない。
非ゼロ終了の判定と停止確認は runner が行う。

認証・承認待ちは、標準エラーと export の error の step（ ``source`` が ``error`` 、 ``is_error`` が真、または ``error`` を持つ step）の文だけで判定する。
標準エラーの認証・承認の診断と export の error の step は、成功候補より優先する。
error の step の文が認証・承認に当たらなければ ``response_failed`` とする。
標準出力と最終 ATIF 応答はモデルの発言なので、診断に使わない。
そのため、回答がコードブロックなどで ``Error: invalid api key`` のような行を引用しても、正しい回答で終われば成功とする。
回答の無い実行は、標準出力の内容によらず ``response_failed`` とする（Issue #239）。

ATIF の tool 引数に skill のパスが現れても、成功した読み取りや全文の確認は証明できない。
この adapter は ``skill_versions`` を空の map として返す。
runner は保持する export を collect 前に秘匿値の除去処理に通す。
意図して保存する prompt には資格情報を含めない。

検証と制約
==========

移植元は commit ``a47b2065fddad76b7475752fd0088af0733de204`` の Devin adapter と偽 CLI テストである。
同梱の旧実機記録は Devin 3000.11.3 に基づくものであり、この環境での成功確認ではない。
事前調査ではインストール済み 3000.11.92 の help に上記の起動オプションがあることを確認した。
3000.11.92 による PR のレビュー（PR #185・#186、2026-10-19）の標準出力と export で、応答の連結の形と、最後の step が tool 呼び出しの無い agent 応答であることを確かめた（Issue #188）。
3000.11.205 では、認証情報の無い一時 HOME で ``devin -p`` を起動すると、標準エラーに ``Error: Login canceled`` を出して終了コード 1 で終わり、標準出力に診断は無く、export も作らないことを確かめた（Issue #239。認証が無いのでモデルは起動していない）。
adapter のテストは偽 CLI だけを使い、実 CLI・モデル・API を起動しない。

偽 CLI の起動、入力、成功と失敗の解析、export の保持と秘匿値除去を検証する ::

    uv run pytest tools/agent_runner/tests/adapters/devin -q

以上
