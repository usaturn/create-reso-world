# Issue #3: 読み取り証跡の採取基盤を再構築する

- 状態: completed
- 完了範囲: raw receipt基盤のみ。内容承認は未記録であり、Issue続行workflowの実行許可と区別する。S4/Drivegate/full preflightは未完了。
- 文書管理: usaturn/create-reso-world
- 対象: usaturn/resonite-emission-editor / https://github.com/usaturn/resonite-emission-editor/issues/3
- CODE_ROOT: /workspaces/create-reso-world/external/emission-editor/.worktrees/issue-3-resume
- コード開始点: 7d34f6b77dcedb7bf4a87c85e36ba9ef25e06548
- DOC_ROOT: /workspaces/create-reso-world/.worktrees/emission-editor-issue-3-preflight
- 実行許可: 利用者の明示SuperpowersでのIssue続行、16070指定、前面化、対象判定の委任、その後の「/goal 作業を続けてください」。issue-to-prの通常判断の委任を使い、内容承認と区別する。
- 既存設計: 対象repo mainの docs/superpowers/specs/2026-11-03-tools-avatar-emission-editor-design.md と plans/2026-11-03-tools-avatar-emission-editor.md。移行済み文書は移動・複製しない。
- 補足文書を新設する理由: 旧マシンにのみ存在し公開されていない採取実装のうち、独立して検証できるraw receipt基盤を現在のrepoへ再実装する。既存UI/Drivegate設計や過去の承認SHAを置き換えない。

## 目的と現状
保存checkpointが対象であることは現在の実参照と値から判定済み。新しい空worldは不要。
旧collector/validator/封印資料はディスクに存在すると仮定できない。旧tmp/worlds/toolsを探索しない。
既存ResoloopReadPortは任意argvと既存stateを前提とするため、そのまま安全な新規採取入口にしない。

## 選択した方式
1. **採用:** 読み取りコマンドを型付き要求から生成し、raw stdout/stderrと実終了コードを新規ディレクトリへ保存する小さな独立モジュール。
2. 一時スクリプトの継ぎ足し: 今回の対象調査には使ったが、操作範囲と誤報告防止の継続検証を残せないため採用しない。
3. 旧ファイルの復元: Issueが禁止するため採用しない。

## 仕様
- Python3.14以上、標準ライブラリのみ。新モジュールread_receipts.py。既存live inspect/register/unregisterは無変更・無効のまま。
- ReadRequest(operation, url, target=None, depth=0)からのみargvを生成する。許可はdiscover/doctor/hierarchy/inspect/component-inspect。任意argv、shell、batch、retry、mutationを受け取らない。
- urlは明示したwsのloopbackホストと1..65535のportのみ。auto、userinfo、query、fragment、非root path、別ホストは拒否。現在16070をコードに固定せず、呼出側が明示する。
- targetはRoot、Reso_の16進ID、ハイフン区切りUUIDだけ。名前や旧stateのstable keyを解決しない。depthはinspect/hierarchyだけ0..64の整数。
- collect_read(request, output_directory, *, cwd)は1回だけresoloopを同期実行する。CLI自身のtimeout/command-timeoutを設定し、外側timeoutでプロセスを強制終了しない。stdinは閉じる。
- 出力先の親は既存であること。出力ディレクトリは排他的に新設する。既存のファイル/ディレクトリ/symlinkを再利用せず、固定3ファイルreceipt.json/stdout.bin/stderr.binを排他的に保存する。
- receiptに要求、実argv/cwd、開始終了時刻、実終了コードまたは起動失敗、raw2ファイルのSHA256を保存する。失敗も消さず、再試行しない。
- load_read(directory)はargvを要求から再生成し照合し、raw hashを検証してからstrict JSON envelopeを読む。JSONのboolを終了コード0と同一視しない。非0、ok!=true、非object/壊れたJSONはtransportSucceeded=false。
- 結果のcompleteとexecutionPermissionは常にfalse。transportSucceededはCLI通信の結果だけで、native動作、doctor全項目、全preflight、Drivegate成功を意味しない。
- これはreceipt全体を書き換える攻撃者への認証ではない。二重読みの独立性、session/時刻窓、typed member/結線/完全subtree/詳細diffと封印資料の照合は後続の別工程。今の段階で代用・省略しない。

## 受け入れ基準・防御範囲・環境
- Dev Container/Linux、Python3.14、uv、既存CLI0.2.0。実機は使わず、実行可能な偽resoloopだけで検証する。
- 入力は改行・非ASCIIを含む実形状のJSON envelopeとbinary stderr。raw bytesが保持され、明示URLと対象IDがargvへ渡る。
- 防御対象: 許可外コマンド/対象/送信先での起動、出力の上書き、CLI失敗の成功化、rawまたはargv改変を見逃すこと。
- 対象外: 任意のremote URL、state/adopt/deploy、full preflight判定、world変更、保存済みデータの修復、全証跡を攻撃者が整合的に書き換えた場合の認証。

## テスト方針
防御対象はSとして、実subprocessを偽CLIへ向けてRED/GREENで確認する。拒否だけでなく正しい採取を残す。
構文/import/文書文言/固定一覧だけのテストは追加しない。既存suiteを変更せず全実行する。

## 実行上の制約
subagentは複数回no outputで、指定した報告ファイルも未生成。調査はcontroller実施。実装に入る際も利用不能ならexecuting-plansのfallbackを明示し、独立レビュー未実施を隠さない。
world接続・書込み、CLI入口有効化、S4/S5/S6b以降への遷移はこの補足の実行範囲外。

## 実行結果
コードは007ed5e3355c2711e5a8b153a36075d79c8c3c75で実装済み。初期実装はcontroller、採用指摘の修正はsp-implementer、Task/限定再レビュー/最終全体レビューはsp-reviewが担当した。sp-reconのno outputを全roleの利用不能とみなした初期判断は、reviewerの正常応答後に訂正した。
偽CLIのS/F∩Sテスト12件を追加し、全suite52passed。compileallとdiff検査成功。Taskレビューのdiscover URL記録不整合1件を、実行引数と要求の対応のRED/GREENで修正し、限定再レビューADDRESSED。最終全体レビューはCritical/Important/Minor0。新collectorを実機では使っていない。
CLI互換性はインストール済0.2.0のhelpと、明示したforkのProgram.cs107–133のglobal option処理を照合した構文上の根拠。新collectorの実機動作成功とは報告しない。
対象worldの確認はこの実装前の別read-only調査で完了しているが、その古い時刻窓を後続preflightへ継ぎ足さない。実機の残gate、独立した二重読み、封印資料、native試験は今後の準備に残す。
