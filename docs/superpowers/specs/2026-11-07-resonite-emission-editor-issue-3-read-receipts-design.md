# Issue #3: 読み取り証跡の採取基盤を再構築する

- 状態: draft（PR #4 のレビュー選別は完了。マージは許可範囲外のため手動待ち）
- 実装状態: raw receipt 基盤は completed。今回のレビューでコードの変更はない。
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

## PR #4 のレビュー指摘の選別（2026-11-07）

### 範囲・実行許可・文書の選択

- 対象: https://github.com/usaturn/resonite-emission-editor/pull/4、`feat/issue-3-resume`。
- reviewed HEAD: `007ed5e3355c2711e5a8b153a36075d79c8c3c75`。base は取り直した `main` の `7d34f6b77dcedb7bf4a87c85e36ba9ef25e06548` で、HEAD の祖先。
- 利用者の明示した `pr-review-fix-loop` と PR URL が、同 PR のレビュー・選別・必要な修正の実行許可。実機操作や通常ツールの自動マージの許可ではない。内容承認の記録にはしない。
- 同じリポジトリ・Issue #3・raw receipt のテーマの現行文書は本 Spec と対応 Plan の一組。別のサイクル文書は新設せず本節を追加した。元の UI/Drivegate の Spec・Plan と未完了の範囲は変えない。
- `CODE_ROOT`: 冒頭と同じ既存の linked worktree。clean かつ HEAD 一致を確認して再利用し、削除しない。`DOC_ROOT` と文書ブランチも冒頭のものを再利用。
- planner: `openai-codex/gpt-6.1-sol`（pi、bash ツールの `PI_PROVIDER` と `PI_MODEL` で確認）。判断のサイクルは 1、loop run は `779d361157564a3cb8843a4353108b0a`。
- 前の判断の記録は空。全入力は `reviews/usaturn/resonite-emission-editor/#4-feat-issue-3-resume/` 配下の本文2件・候補2件・実行記録4件。loop の診断も確認した。

### レビュアーの構成

| ファイル／要求担当 | 実担当・モデル／runtime | レビュー HEAD／再実行 | loop の判定と今回の入力 |
| --- | --- | --- | --- |
| `SWE-2-Max.md` | `devin_swe2-max_default` / SWE-2 Max / devin | `007ed5e3355c` / Initial、現行 HEAD | accepted、active Low 1。採否の入力とする。Merge recommendation は Approve |
| `gpt-6.1-sol.md` | `pi_openai-codex_gpt6-sol_max` / gpt-6.1-sol / pi | 履歴は13桁の `007ed5e3355c2`。初回と許可された再試行1回、末尾は Update | 初回・再試行とも artifacts で rejected（HEAD の12桁照合不一致）。本文と候補は読んだが、受理済みの現行レビューとして数えず、記録の HEAD は unknown、rerun=false。active 0。Merge recommendation は Approve |
| 本文なし / `pi_commandcode_deepseek4-flash_max` | 同担当。runner が観測したモデルは不明 / pi | 2700秒で timed_out、exit -15 | rejected（runner）、reported_state=response_failed、stop_confirmed=true。指摘0件とは扱わず、採否の入力にする成果なし |

失敗した3試行の診断の cause はすべて unknown。実行要求のモデル名で観測モデルを補わない。診断は loop run の `cycle-1/diagnostics/` に保存済み。独立調査を `sp-research` に委譲したが no output だったため成果として数えず、controller が以下の確認を行った。

### 全指摘の分類

| 出典 | 分類 | 根拠 |
| --- | --- | --- |
| `SWE-2-Max#L-1@007ed5e3355c` | 解消済み（反証、コード変更なし） | 裸の NaN/Infinity の拒否は再現するが、実 CLI がその形を出すという前提は誤り。NuGet ResoLoop 0.2.0 の実 `OutputWriter.Success` は非有限 float/double を引用した JSON 文字列で出力する。その実 bytes を隔離した現行 HEAD の collect/load に渡すと全5操作で成功し、解析済み応答も保持される |

合計: 解消済み1／対応する0／対応しない0。前のサイクルからの引き継ぎは0。PR に関係する追加の致命的な欠陥は確認していない。

### 要件・共有条件と今回の確認の対応

PR の約束と本 Spec・Plan の対象範囲を維持する。統合担当は controller。変更はないため「対応する」項目の修正経路表は不要だが、共有する入力・出力の解釈を次のように照合した。

| 既存の条件 | 今回の方針 | 観測する結果／方法 | 現行 HEAD の結果 |
| --- | --- | --- | --- |
| 型付き要求から5操作と明示 URL を束縛する | 変更しない | 既存 S テストと偽 CLI の全5操作で実 argv を観測 | 許可操作が通り、別 URL の環境変数に置き換わらない |
| raw bytes・実終了コードを保持し、既存証跡を上書きしない | 変更しない | 全 suite、採取後の stdout bytes と再読込を比較 | 52 passed。実 OutputWriter の bytes が採取後と一致、load の返値も一致 |
| 正常な JSON envelope だけを成功として扱う | strict JSON を維持 | 実 CLI DLL の出力と独立に構成した不正 JSON を対照とする | 引用した NaN/Infinity は true、裸の3定数・ネスト内 NaN・重複キーは false。有限指数は true |
| native/full preflight と書き込み許可を混同しない | 変更しない | 全正例で complete/executionPermission、既存 live 3入口の未起動を確認 | 常に false。inspect/register/unregister は失敗として終了し、偽 CLI の呼出数も増えない |
| 実機や元の world/state を使わない | 変更しない | 同梱 DLL のオフライン呼出と実行可能な偽 CLI に閉じ込める | 実 Resonite 接続0。既存資料の復元・探索・world変更なし |

### L-1 の反証と設計判断

- 同梱 `source/src/RLoop.Cli/OutputWriter.cs` の32–38行は `JsonSerializer.Serialize`、106–112行は `AllowNamedFloatingPointLiterals` を設定する。Context7 CLI の問い合わせ3回以内で公式 `.NET` 文書の JSON string tokens の仕様と照合した（https://github.com/dotnet/docs/blob/main/docs/standard/serialization/system-text-json/migrate-from-newtonsoft.md）。
- SDK 10.0.401 で NuGet ResoLoop 0.2.0 の実 `resoloop.dll` と `RLoop.Core.dll` を参照する一時プログラムをビルドし、`OutputWriter.Success` に float/double の NaN、正負 Infinity、ネスト内 NaN、非 ASCII・改行の文字列を渡した。出力は `"NaN"`、`"Infinity"`、`"-Infinity"` の引用文字列。
- 同じ bytes を偽 CLI の stdout とし、PR head を照合した隔離 worktree で全5操作を collect/load した。すべて `transportSucceeded=true`、response と raw が一致し、complete/executionPermission は false。実入力を検証せず fake に裸 NaN を埋め込む再現の誤前提を取り除いた。
- 別入力8件も確認。裸 NaN/正負 Infinity/ネスト内 NaN と重複キーは false、引用3文字列・有限指数・`1e999` は true。`1e999` は有効な JSON 数値であり、有限値の業務判定はこの transport の保証外。非 JSON 定数の拒否と矛盾しない。
- 選択: strict JSON を維持。裸定数を許容する別パーサへの変更は実 CLI に必要がなく、既存の防御を緩めるため採用しない。存在しない実 CLI 制限の README 追記もしない。以前の同条件の修正・回帰はなく、設計見直しのきっかけには該当しない。
- テスト追加は不要。欠陥の修正をしていないため、今回の反証は一時プログラムと実行記録で残し、固定文言テストや重複した回帰テストはコミットしない。

### 検証・結論・残り

- 専用 worktree: `uv run --locked pytest -q -p no:cacheprovider --basetemp=<隔離root>/pytest` → exit0、52 passed / 0.91s。`uv run --locked python -B` で scripts/tests の22 Pythonファイルをメモリ上で compile → exit0。`git diff --check <base>..HEAD` → exit0。検証前後の HEAD は上記のまま、status は空。
- 隔離 worktree: `dotnet build FloatProbe.csproj`、実 DLL の OutputWriter 呼出、`PYTHONPATH=<隔離worktree> uv run --project <親> --locked python -B probe.py <隔離root>` → すべて exit0、偽 CLI 13回。隔離 worktree と一時rootは検証後に登録解除して削除した。
- controller が `gh api repos/usaturn/resonite-emission-editor/actions/permissions` を読み、実設定 enabled=false と採用済み台帳 ci=disabled の一致を確認。親のローカル check だけで CI を免除したものではない。
- 確認済み一覧: `reviews/usaturn/resonite-emission-editor/#4-feat-issue-3-resume/verified/007ed5e3355c.json` と `.md`。confirmed0 / not_reproduced1 / unverified0。工程の記録は同 stem の `.planning.json`。
- 修正実装・自己レビューは不要のため `run_roles.py` 未起動、自己レビュー0回。既定割り当ては implement=`claude-code_opus_default`、self-review/fix-check=`self` だが、実行した担当として記録しない。
- **結論3: permission による停止。** この通常ツールは `review-fix-planning` の自動マージ許可範囲外。追加コード修正は不要だが、手動マージ待ちであり、マージ・Issue更新の完了とはしない。Issue #3 の full preflight、Drivegate、S4以降、実UI、Task6 は引き続き未完了。
- 本 Spec は停止時の規則に従い draft。対応する文書 PR #336 は既に MERGED なので、今回の文書コミットはローカルのみ（公開未実施）。新しい PR は作らず、マージ済み PR へ push しない。
- 検証の実測範囲: 2026-11-07T15:26:05Z–15:28:56Z、171秒。待ち時間の内訳は未計測。ループ全体とサイクルの時間・状況コメント URL は helper の最終記録と完了報告に残す。
- 証跡と停止時の記録: `/workspaces/create-reso-world/tmp/agents/emission-pr4-loop.5gbmtyj5/`。関連する一時プログラム・実出力・全 suite ログを `evidence/` に保存し、手動マージ判断と診断のため保持する。
