# Emission Editor — 最小実用版への短縮計画（Issue #3）

- 状態: completed（A案の最小受け入れ基準、Task 1–3の実装と通常の2行操作確認）。提示したA案の受け入れ基準・動作環境・防御範囲について利用者が「1」を選択した。承認内容commitは`19870487d00f411f57a0687424d0156207643927`。利用者の推奨案選択により、前の試験用1行版と付属見本だけを削除済み。動作確認済みの2行版と見本は保持。
- 対象: `usaturn/resonite-emission-editor#3`。
- 文書管理: `usaturn/create-reso-world`。同じ文書branchを使う。
- Spec: `../specs/2026-11-07-emission-issue-3-native-gate-design.md`。
- 実装先: `external/emission-editor/.worktrees/issue-3-native-gate`、`feat/issue-3-native-gate`、検討時HEAD `95c3fcf34c7762b23e2b7bf1dd1e9ca445c2f05c`。
- 実行許可: 仕様見直し・工程削減の許可に続き、利用者が「1（単独パネルを維持して、この短縮案で進める）」を選択した。A案で実装・実機確認へ進む。内容承認は上記commitへ結び付け、公開許可とは区別する。
- 旧Planの詳細・完了記録はcommit `f9c536616efbffb228547dcbcfb3fcf2952560f4` の同じパスに保存済み。旧FAIL/未検証を成功へ変更しない。

## ゴール

検証基盤ではなく、使えるパネルを先に仕上げる。既存の登録/UI/RowPreview/RowCommand/Commitを再利用し、試験用対象1体・共有材1行で「選択・ライブ反映・元に戻す・キャンセル・OK」を実機で使えることを最初の完成条件とする。

## 共通の受け入れ基準・環境・防御範囲

- 環境: 現在のDev Container、uv/Python、現行ResoLoop/Flux/Resonite。指定先は16070で、実行前に現在の接続を確認する。登録後の通常操作はPC補助プロセスなしで行う。
- 実入力: 新しく作る試験用対象1体・共有材1行、日本語名、HDR RGB、Alpha非1、有効入力・不正入力1例。
- 成立条件: 選択した材質の見た目と読み戻し値が変わる。元に戻す・キャンセルで元の完全な色へ戻り、OKで変更を保持する。不正入力を送らず、失敗を成功と表示しない。
- 残す防御: 選択対象とEmissionColorの確認、元値の保持、当該値の読み戻し、今回作った試験物だけの片付け。
- 対象外: 二人操作の保証、編集中保存/退出からの自動復旧、完全な外部共有走査、Drive拒否の故障注入、全native構造/全DLLの証明、全ケースの検証。
- 非目標: 既存のガードを削除するためのリファクタ、汎用retry/controller/証跡基盤の追加、旧Drivegateや旧S4プロトコルの完遂。

## Task 1: 本体へ直行できる入口を整える

既存の登録データ・UI生成・必要なPGの配備方法を確認し、現在の接続で試験用対象と小さいパネルを用意できる入口を作る。旧worlds/toolsや旧sessionのstateは再生せず、現在のソースから必要な宣言・manifestだけ生成する。保存済みの本体パネルのclaim等を手動で消さず、必要なら別の小さい試験パネルを新規作成する。

Drivegate/lifecycle/fullpreflightの完成は待たない。必要なbuildと対象の確認を行ったら本体の実行へ進む。公開live CLIが現在無効であることは明示し、無断で汎用live入口を有効化せず、このTaskの明示的な試験実行経路を用意する。README/AGENTS/handoffに残る旧gate参照は、利用者が選んだ簡略Specの適用を明記して矛盾を解消する。

**テスト:** 文書・一覧変更には不要（F/L）。入口のコードを変更し、誤対象への書き込みや元値消失などが黙って起き得る場合だけ代表Sを追加する。既存の同じ守りは再テストしない。
**代替検証:** 差分確認、必要箇所の構文/build、現接続と作成先の読み取り、既存suite。

## Task 2: 1行の実機操作を通し、動かない箇所だけ直す

試験用対象へ登録・選択し、RGB編集、元に戻す、再編集してキャンセル、再編集してOKを通す。当該EmissionColorを読み戻し、利用者に見た目と操作を確認してもらう。不正入力1例を確認する。

既存の本体PGを先に使う。正常な操作を妨げる不具合やガードがあれば、その経路だけを確認・修正する。正常操作と直接関係しない全SDK/DLL調査、failure injection、全world比較へ広げない。クリック等の人の操作と、CLIによる値設定は区別して記録する。

**テスト:** 基本動作は実機で確認する。実際に見つかった、誤対象書込・元値喪失・誤った成功表示等のSだけ再発防止テストを追加する。単なるbuild/型/構文の失敗に永久テストを足さない。
**検証:** 操作前/反映後/復元後/確定後の当該値、実際の見た目、簡潔な結果記録。故障条件の網羅やモデルレビューは必須にしない。

## Task 3: 利用できる形へまとめて完了する

同じ実装で通常の複数行表示を確認し、最低限の使い方と制限をREADMEへ記載する。今回新しく作った試験物は、確認した対象だけ片付ける。利用者が残したいパネルは残す。

**テスト:** 文書・記録だけなら不要（F/L）。追加のコード変更にSがあればその部分だけ検証する。
**検証:** 既存suite、変更PGのbuild、最小受け入れ基準の実測とgit diff。二人操作・幅違い撮影・編集中保存復旧・旧S4以降の全検査・指定モデルレビューを完了待ちにしない。

最小受け入れ基準を通した時点で、この簡略範囲を完了とする。未確認の旧保証は制限として残し、旧仕様の全条件を満たしたとは報告しない。push/PR/mergeは別許可の段階とし、依頼がなければ公開未実施。

## 実行予算・contingency

時間上限は設けないが、最初の実機1行の操作へ到達することを優先する。従来の時間記録は保持し、リセットしない。30分checkpointは短い進捗記録とし、時間経過だけを理由に作業を引き継いで停止しない。コード変更がない文書整理にfull suiteや追加モデルを繰り返さない。

同じ問題が続いたら同じ検査を繰り返さず、問題の機能に絞る。単独native方式の本体に新しい根本制約が見つかった場合だけ、PC補助を許すB案を利用者へ選択肢で提示する。先にB案へ勝手に作り替えない。実行中writerに別writerを重ねたり、適用状況不明の書き込みを盲目的に再送したりしないが、完全な自動復旧基盤の実装は要求しない。

## A案の実行記録（2026-11-08）

- 承認内容commit `19870487`を維持し、状態・実行許可の記録だけを`447661c`で追記した。Task 1の本体接続はcode `a3646c4`。既存UI配備に未接続だったRowPreview/RowCommand/Commitと現行BeginRow等を組み合わせる`slim.py`、新しい試験物だけを作る明示入口`slim_demo.py`を追加した。汎用live registerは無効のまま。
- 指定16070のdiscover/doctorは成功。新しい試験用対象1体、共有発光材1個・メッシュ2個、別所有の1行パネルを作成し、本体11モジュールを実配備した。既存パネル/実アバターは変更していない。追加S1件は2行の反映先・復元元の混同を防ぐ代表例、全143passed/18.07s・compileall/diff成功。元値は完全なRGBA/profileのまま、初回の読み戻しでも試験材質は変更前と一致した。
- 最初の参照設定はCLIの`REFERENCE_VALUE_QUOTED`/exit6で拒否された。引数を既存CLI仕様の生文字列に直し、同じ試行の新規パネルが未公開・参照未設定で、試験材質の値とsessionが同じことを読んでから不足分を続行した。fixture/panel applyの再送や重複作成は行っていない。これは明示エラーで気付けるLのため永久テストを増やしていない。
- Task 2は実クリック待ち。配備成功と機能成功を区別し、選択・ライブ編集・復元・確定を実操作済みとは報告しない。前面の自動撮影はCOMMAND_TIMEOUT/exit8で画像未取得、撮影用rootは終了後の階層観測に存在しなかった。新しいパネル/試験物は利用者の操作確認のため残し、動作中のCLI/workerはない。
- 試行・現在ID・呼出raw・操作待ち情報はPARENT_ROOTの`tmp/agents/emission-slim-live.9h01t5g6/`。その`demo-r1/deployment.json`と`initial-observe.json`を参照する。Demoの68 CLI呼出は67exit0/1exit6であり、内部native protocolの呼出数とは同一視しない。時間制限なし、最初の正確な時計12:07:09Z、12:36時点でTask 1の実配備と本体1行パネルまで進んだ。過去の時間記録は保持。Task 2/3・簡略範囲の完了・公開はまだ未実施。
- 利用者から「2枚あって区別できない、片方で開始したが反応しない」と報告。新パネルの読み戻しではOperator取得・試験対象選択・epoch2・snapshot2・行表示/編集可能=trueを確認し、開始/選択は届いていた。code`f19ba40`で見出しに「動作確認用・新パネル [登録ID]」を付け、開始済みのボタン表示を追加した。新パネルのSessionだけを新しい出力先から更新し、元値・epochは保持。実validate/deployと表示readback、143passed/18.84s・compileall/diff成功。旧パネルは変更しない。
- 続いて新パネルの所有UI文字列だけをCLIからRGB=(0,4,0)へ変更し、既存native RowPreviewによる実材質への反映を確認した。Material/LastAppliedは(0,4,0,.37,sRGB)、Originalは(2,1,1,.37,sRGB)を保持、Result1/Valid=true/InputSeq=AppliedSeq=4/OpStage0。実ユーザーの文字入力を試したことにはせず、UIフィールド設定からnative反映までの確認と記録する。現在は試験用の緑プレビューを意図して残し、利用者の「元に戻す」の実押下を待つ。元値を上書き・再初期化・再配備しない。ログは同sessionの`start-feedback-1/`と`green-preview-from-ui-fields.json`。手動復元/キャンセル/OK/実文字入力・見た目はこの時点では確認待ち。
- その後の実操作で「元に戻す」は材質/Original/LastAppliedが(2,1,1,.37,sRGB)へ一致し、Result2・preview/row-pending=false・OpStage0を確認。利用者のキャンセル後も同じ完全色へ復元済みで、選択解除により数値行が隠れていた。OK/キャンセルで選択を外して編集を終了するのは承認済みの仕様であり、パネルの案内文にも明記した。
- 利用者がRGB=(0,4,0)を入力してOK後に選び直した観測では、実材質/新しい編集のOriginal/LastAppliedが(0,4,0,.37,sRGB)、epoch4、preview=false。確定した値が保持された。最初の元値2/1/1の記録は履歴へ保持し、編集終了後の新しいOriginalを不正な上書きとは扱わない。
- 緑の見本が見えないとの報告では、パネルが初期位置から移動した一方、別rootの見本は元の位置に残っていた（約2m離れていた）。code`23f17c8`で見本を同じ試行のパネル右側へ縦2個で取り付け、パネルと一緒に動かす。既存stateでrootのrelocateとmesh1のposition更新だけ、create/delete0、全slot/component IDと確定済みの緑の完全色を保持して実適用した。材質の色・shader設定は変更していない。新S1件で別の試験パネルへの接続拒否と材質設定の保持を確認、全144passed/18.52s・compileall/diff成功。見た目は利用者の再確認待ち。資料は同sessionの`cancelled-by-user*.json`、`after-user-ok.json`、`fixture-visual-check.json`、`visual-panel-and-fixture-poses.json`、`fixture-placement-1/`。`attach_fixture.py`は完了済みone-use、再実行しない。旧fixture.jsonは初回作成時の記録で、現在の親を戻すために再applyしない。
- 利用者の再確認は「立方体は見えるが緑ではない」。実材質のEmissionMap=nullを確認し、[XiexeToonMaterialの公式Wiki](https://wiki.resonite.com/Component:XiexeToonMaterial)に、map未設定ではEmissionColorが黒以外でも発光しないとの明記があった。実型照会でSolidColorTextureのColor/Size/Mipmapsを確認し、code`bef7788`で試験fixtureだけに白い1x1テクスチャとEmissionMap参照を追加。実applyはtexture slot/componentのcreate2＋既存materialのEmissionMapだけ更新、delete0。全既存ID、表面の白(1,1,1,1)、確定したEmissionColor(0,4,0,.37,sRGB)を保持し、Map参照先が白textureと一致した。表面色を緑に塗る代用や実avatarのmap変更はしていない。新規の固定設定テストはF/Lなので追加せず、実型照会・diff/apply/readback・既存144passed/18.33s・compile/diffで検証した。見た目はまだ再確認待ち。資料`emission-map-1/`、現在の配置/材質宣言は同下`fixture-emissive.json`。`add_emission_map.py`は完了one-use、旧fixture/placement宣言を再applyしない。
- 利用者が「緑になりました」と見た目を確認。fresh readでも実材質/Original/LastApplied=(0,4,0,.37,sRGB)、表面は白、mapは白textureへ接続、epoch4、preview/pending=false、OpStage/Intent0で一致した。目視の根拠は利用者の返答であり、agent画像撮影ではない。資料`green-confirmed-by-user-1.json`。Task 2の残り1例は、所有UIのG文字列だけをCLIで4→abcとしてnativeのValid=false/Result10を確認し、完全な材質値・元値・LastAppliedが不変だった。UI文字列を同じ4へ戻すとValid=true/Result0/preview=falseへ復帰した。人の不正値タイピング試験とは区別する。資料`invalid-input-2/`。確認スクリプトの最初の参照名はSTABLE_COMPONENT_NOT_FOUNDで停止し、いずれもnative書込前だったため現stateのEditor/Text参照から実キーを解決して続行、原エラーを保持した。`check_invalid_input.py`も完了one-use、再実行しない。これで1行の最小基本確認（既報の選択/ライブ数値反映/元に戻す/キャンセル/OK、今回の緑の実表示/不正入力拒否）を満たした。コード変更なしでsuiteは再実行しない。Task 3の通常の複数行・実アバター指定登録入口・最終使い方/制限の仕上げは残す。公開未実施。
- Task 3のcode`08e029b`で`slim_live register --avatar <明示Root>`を追加。指定階層のMeshRenderer/SkinnedMeshRendererと参照材質だけを読んで、公開colorX EmissionColorを参照ID別にまとめ、新規所有パネルへ各行のSource/provider/全既知使用先を設定して読み戻す。既存アバターには登録処理から書き込まず、操作者取得/選択はnativeのボタンで行う。旧`__main__`は無効のまま、新A入口をREADME/AGENTSに明示。外部共有未走査の警告と制限、失敗時の非再送も記載。行0固定の投入/row-countを一般化し、既存Sを参照投入まで拡張。新S3件は同名でも別参照を混同しない/完全HDR・Alpha・profile保持と読取専用、World Root拒否、指定IDと別のAvatarRoot拒否。147passed/18.34s・compile/diff成功。
- 同じcapture/create経路で、新しい試験対象2材質・各2共有メッシュを登録し、別所有の「複数行確認・新パネル [92dd24ae]」へ17モジュールをvalidate/deploy成功。全参照/既知のlist-entry/SourceフィールドIDを読み戻し、readyを最後に有効化した。元値は材質0=(2,1,1,.37,sRGB)、材質1=(1,0,2,.61,sRGB)のまま。各材質に白mapがあり、4見本はパネル右の2列へ取り付けた。前の1行版は変更していない。新パネルは1行版よりZが0.5手前、既存パネルや実アバターを移動・非表示・削除していない。試験用Rootでの共通登録経路の確認であり、実アバター操作済みとはしない。
- 自動操作の準備で新所有UIのUser参照をCLIから設定しようとすると、ResoniteLinkのWriteReferenceでNullReferenceException/COMPONENT_UPDATE_FAILED。fresh readでOperator/SelectedRootはnull、両材質/元値が変更前、preview/pending=falseを確認。再送やSDK変更へ広げず、試験側で書いたguard文字列だけを同じ値と確認して空へ戻した。Sourceやprivate Beforeは書き換えていない。開始はnativeの実ボタンで行い、利用者に2行表示→左列緑/右列青の別入力→元に戻すの通常確認を依頼する。`check_rows.py`はこの準備で失敗したone-use、現在の状態へ再実行しない。Task 3の実操作結果は未確認のまま。資料`tmp/agents/emission-multirow.8cjiic8i/`（prepare.log/deployment/参照readback、after-operator-set-error.json、pre-user-check.json）。17:52着手、18:06絞った4テスト、18:08–18:14頃実配備、18:14–18:22頃限定調査と未適用確認、18:35全suite/記録。30分時点の進捗を報告済みで、時間超過で停止するのでなく実操作待ち。公開/追加モデル起動なし。
- 利用者が2行表示・1行目RGB(0,4,0)/左2個緑・2行目RGB(0,0,3)/右2個青・元に戻すを「全て成功」と確認。fresh readで両材質/Original/LastAppliedは(2,1,1,.37,sRGB)/(1,0,2,.61,sRGB)へ一致し、両Result2、SnapshotEpoch=EditEpoch=2、表示中、preview-written/row-pending=false、行/全体OpStage0、Intent0、preview/pending=false、AckRemaining/AckFail/AckRefuse/AckWait全0。Statusは「元の値に戻しました」。資料`emission-multirow.8cjiic8i/restored-by-user-1.json`。この実表示・入力・復元は利用者の実操作であり、agentのUser参照設定/画像取得で代用したものではない。前の1行版もfresh readで材質/新編集Original=(0,4,0,.37,sRGB)を保持した（`emission-slim-live.9h01t5g6/after-two-row-success-r1.json`）。
- 以上でA案の最小受け入れと通常2行の確認、明示Root登録入口、使い方/制限を完了。実アバターは操作しておらず、全材質型/全World/多人数/編集中保存復旧など旧保証を確認済みにしない。コードは08e029bのまま、直前の147passed/18.34s・compile/diffの実績を使い、文書だけの変更でsuiteを繰り返さない。利用可能な試験用2行版と前1行版/見本、調査ログは保持し、削除は利用者の選択後に今回の所有物だけへ限定する（片付け未実施）。push/PR/merge・公開未実施。最終確認19:01着手、読み取り/記録のみ、writer/workerなし。
- 2026-11-09、利用者が片付けを「推奨案で」と指示。推奨②（前の試験用1行版だけを片付け、2行版を残す）として実行。現在の同session、R1の所有key/正確な名前・ID・Root直下・付属fixtureが子であること、待機処理なし/材質=元値をfreshで確認。R1だけのsummary2125slotsに未知のUserRoot/AvatarRoot/追加item rootがなく、直接の子が既知の所有slotであることも確認した。R2は別のRoot直下で削除範囲外。正確なR1のIDへslot delete --yesを1回だけ実行し、Root直下から消えたIDはR1のみ。他の直接rootを保持し、R1とfixtureは個別inspectでもSLOT_NOT_FOUNDを確認した。R2の2材質/Originalは削除前と完全一致し、preview/pending=falseのまま。原始の旧パネルや実アバターの削除・移動・値設定はしていない。ログ`emission-multirow.8cjiic8i/cleanup-r1-1/`、one-use`inspect_cleanup_r1.py`/`delete_r1.py`は完了済み、再実行しない。消失確認スクリプトで空stdoutのJSON解析に1度失敗したが、stderrの正式なエラー応答を読んで確認し直した。削除の再送はない。コード変更/追加モデル/再suite/公開なし。R1のstate/rawは履歴として残し、現在の対象として再利用しない。
