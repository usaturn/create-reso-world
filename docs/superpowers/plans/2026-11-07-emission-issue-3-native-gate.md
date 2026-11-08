# Issue #3 native Drivegate 実行計画

- 状態: draft。内容承認SHAは発明しない。
- 対象: `usaturn/resonite-emission-editor#3`。同じコード/文書branchで継続する。
- Spec: `../specs/2026-11-07-emission-issue-3-native-gate-design.md`。
- 実行許可: 利用者が2026-11-08に具体的に指示した、Root全値一致不要・不一致時の自動再試行・本Issue作業全体での保護範囲変更の追加確認不要を適用する。セッション限定ではない。
- 機能の元Spec/Planと完了条件は維持し、検証/再試行/確認手続きは本Specの現在有効な作業方針へ更新する。旧停止規則を別資料から再導入しない。

## Goal / Architecture / Environment

欠けている短いDrivegateの実行物と照合を整え、元Task4/5/6を順番に進める。既存raw基盤→隔離package/SDK封印→意味/範囲/phase判定→現在contextのpreflight→controllerの逐次実機と自動回復/再試行。

Dev Container、Python3.14/uv/標準ライブラリ、実行時のResoLoop/Flux SDK/native DLL。現在の16070の適用性を確認する。作業ルートは既存の名前付きlinked worktree。PR4 raw基盤・既存の本体PGを不必要に再実装せず、汎用的な任意mutationランナーを作らない。

## Global Constraints — 現在有効

- Root全体の値の完全一致をpreflight/復元/cleanupの条件にしない。全Rootを採取した場合のpayloadは残し、姿勢等の時点差分は診断とする。
- 不一致、切断、検査失敗ではIssue全体を停止せず、原因調査・修正・新観測・自動再試行へ進む。失敗した試行は失敗として残す。
- 保護対象や比較の実質変更は、本Issueでは追加確認なし。理由・対象・新検証をSpec/ledgerと担当briefへ記録して実行する。これを承認待ちへ戻さない。
- 対象操作のsession/ID/親/型/所有/write-set/delete-set、完全色/型/private Before/readback/Done、seal/SDK/全結線の検証は維持する。既存パネル/実アバター/登録済みsynthetic/materialを短いgateのwrite/delete先にしない。
- write/deploy/削除の再試行は適用状況を先に読み戻し、適用済みなら重複実行しない。部分適用は所有範囲内で回復・再plan。不明なmutationの盲目的な再送と同時writerは禁止するが、確認・回復作業自体は自動継続する。
- current試行の検証可能なcheckpointと、別session/帰属不明の旧stateの再生を区別する。新試行のtoken/state/logは分け、原raw/verdict/seal/Beforeを上書きしない。
- 唯一のレビュアーは`claude-code_opus_default`、Read/Grep/Globのみ、MCP/commands無効、実tool一覧/使用を検査。逸脱runを不採用にして制限を修正・自動再確認する。別model/fallback/自己レビューへ置換しない。
- 短いgateをS4全体/実UI/二人/save-reload成功にせず、S4→S5→S6b→S6→S7を維持する。未検証の成功報告や未完了を隠す公開をしない。
- コード1branch/必要な同テーマ文書1branch、Issue3 open、手動merge。個人設定、親/常設checkout、凍結した旧履歴は変更しない。

## 共通の受け入れ基準・防御範囲

Specの「現在有効な作業方針」「受け入れ基準・環境・防御範囲」「自動再試行と回復」「専用fixtureとnative手順」を実装担当/レビュアー双方のbriefへ同じ内容で渡す。旧briefの全値一致/初回停止/追加確認待ちは使わない。

実入力はnative HDR/alpha非1/Linear・sRGB完全色、bool、非ASCII JSON。bool/int、欠落/null、未知kind、opaque保全とprivate意味を区別する。Root全値差分と、操作対象・明示した保護対象の検証を混同しない。別プロセス再採取を異transport独立検証と呼ばない。

誤対象write/delete、重複mutation、Beforeや証拠の上書き、完全色/型損失、失敗の成功化を防ぐ。全rawの整合的な悪意ある改ざん認証や、他利用者との厳密な排他は対象外。

## 実行予算・自動再試行・contingency

利用者の時間制限なしを維持し、過去の169.09能動分/158秒の予算前作業と各continuation記録をリセットしない。Task境界・30能動分・失敗後にcheckpointし、所要時間と実質進捗を残す。検証/共有writerを外側timeoutで強制終了しない。読取専用reviewは720秒枠と終了確認を用いる。

旧「同じ失敗は再試行1回」「安全失敗ならIssue全停止」「不一致なら利用者の判断待ち」は、本Issueの進行規則として使わない。失敗を記録し、現在状況を読み直し、必要な制限・資料・実装を自動修正して再試行する。同じsignatureが続けば同一手順の高速反復でなく調査/方法変更へ切り替え、作業全体を通常の許可待ちにしない。対象外への危険操作は送らず、その必要条件の回復を続ける。

一時読取失敗はbackoff後に再採取。state/session変更はdiscover/doctor/対象解決から更新する。mutatingコマンドのtimeoutは適用状況/Done/プロセス終了を先に確認する。所有範囲内の回復で継続できなければ、元Beforeを保全し安全に片付けた後、新しいfixture/token/state/封印入力で再試行する。新SDK/型/default差はsource根拠を調査して照合器を修正し、新しい入力/試行へ結ぶ。A/B/CやOnFailを実測に合わせて成功へ変更しない。

## Task 0: 今回のIssue限定ルールを全作業文書へ反映する

**Files:** 本Spec/Plan、create-reso-world作業worktreeのAGENTS.md、コードworktreeのAGENTS.md/README.md/元機能Spec/Plan、共通ledger、新current handoffとbrief。
**テスト:** 不要（F/Lの文言・一覧テストは作らない）。代わりに対象限定の全文検索、旧規則との矛盾確認、参照先実在/JSON解析、git diff --checkと差分レビュー。原raw/review/sealを変更しない。
- [x] 最新指示は「今回のIssue作業全体」と記録し、session限定という旧表現を現行規則に残さない。
- [x] Root全値一致不要、自動回復/再試行、保護範囲変更の追加確認不要を定義する。
- [x] 現在参照されるAGENTS/README/元機能文書/ledger/handoff/briefの旧規則を置換または履歴として明確に失効させる。
- [x] 指定Claudeで文書だけの矛盾チェックを1回実施し、必要な文書修正とローカル検証/commitを行う。nativeはこの文書改訂では実行しない。

検証記録: 指定Claude（実model claude-opus-5-5）の文書限定レビューは58.605秒/exit0/停止確認済み、PASS。実公開tools=Glob/Grep/Read、使用Read9/Grep2、MCPなし、outside_changesなし。I1Infoの旧ledger見出しをhistoricalへ明確化。I2Infoの常駐helper/Modによる単独動作要件の変更は、今回の保護範囲/再試行の3変更とは別の機能要件なので維持する。追加レビュー循環/固定文言テストなし。原指摘とtool-policy proofは今回のセッション領域へ保存。機能実装やnative試行を実施済みとはしない。

## Task 1: 専用3PGと隔離package/封印

**Files:** `flux/emission-editor/drivegate/{DriveGateProbe,ColorDrive,BoolDrive}.pg`、`drivegate_package.py`、対応tests、README。
**テスト:** S。元ソース/既存ファイルの上書き、範囲外参照、seal改変/不足、失敗成功化を代表正負例と実fake compilerで防ぐ。PGの構文/型は実check/build、固定文字列Fテストなし。
- [x] private fieldだけのfixture/別親/別stateと3PGを実装。
- [x] 実行copyを封印先から分離し、check/build/3manifest/全file-set/hash/clean HEAD provenanceを検証。
- [x] Taskレビュー/採用修正/限定再確認。`8882ae5..3908f34`、71passed、実SDK/原PG不変確認済み。

## Task 2: raw意味/phase/範囲照合と既知正規化

**Files:** `drivegate_evidence.py`、`drivegate_runtime.py`、`drivegate_capture.py`、必要なpackage補足と対応tests。
**テスト:** S。bool/int/完全色/欠落null/receipt再利用/別session/誤削除/不完全結線/Before漏れ等を代表正負例で防ぐ。F/L/Dテストを増やさない。
- [x] 基本照合とstage結合、実SDKparse、独立typed BoolDriveのoffline検証。`c46cef7`まで104passed、指定レビュー修正済み。
- [x] installed AI markerをv3 normalizedFixtureへ表現。`74c0eab`、106passed、前後SHA/MVID source根拠、指定レビュー。
- [x] Rootの名前付き非有限値/完全profile/既知配列の保全専用対応。`505fb7b`、108passed/compile/diff。private writer意味は無変更。
- [x] 同じClaudeを実Read/Grep/Globだけへ制限して再確認。42.784秒/exit0/stopped、技術SpecPASS/qualityPASS_WITH_ISSUES。
- [x] clean505の新package43files/211DLL/3実SDKcheck-build-manifest-parse。旧packageは履歴保持。

## Task 2b: 新ルールを実行側へ反映しSDK layout接続を完成する（一部完了）

**Files:** controllerの試行/観測手順、`tools/drivegate-native-layout/`、`drivegate_native.py`、必要な`drivegate_evidence.py`/`drivegate_runtime.py`/対応Sテスト、README、試行brief。
**テスト:** S。正当なRoot時点差分でprivate操作を誤拒否しない正例と、誤対象write/delete・Before上書き・timeout後の二重適用・未知metadataの成功化を防ぐ代表例。スクリプト文言や全組合せF/L/Dは追加しない。同期suite/compile/diff、隔離copyの実SDK検証を行う。
- [x] 旧`check_fresh_root.py`を再利用せず、`assess_precreate_scope.reviewed_parent`とRoot最終cleanupの全値一致を診断へ分離。明示した保護subtree/親の経路、session/所有/write-set等は別に判定する。Task2b-cの実機読取診断は成功、完全preflightではない。
- [ ] 読取/検査/接続失敗を自動回復・再試行する。mutationの適用済み/未適用/部分適用/不明を区別し、実体/Done/所有/終了確認後に継続する。任意コマンドの汎用再送APIは作らない。
- [x] Task2b-a: exact installed SDKの純粋な操作生成APIを、封印PGの隔離コピーで実行する内部exporter/receiptを追加する。全AddSlot/AddComponentと記号private bindingを生成し、入力・exporter・SDK/native DLL inventory・終了コード・原出力を保存する。既存ファイルの上書き、失敗の成功化、seal外PG/別DLLの混入を代表Sテストで防ぎ、実SDKは3moduleをオフライン実行する。新規native接続なし。
- [x] 新しいnative専用経路でruntime-only SDK graphとnative全layoutの接続を修正する。passive metadataの全field/default/reference/slotをcurrent producerと独立native modelから検証し、3D-only BSON metadataやpersistant-IDを誤解釈しない。`assess_native_owned_graph`/`NativeDeployedStage`を使い、旧BSON-only経路を現在のnative controllerへ転用しない。実機照合の成功はTask3で確認する。
- [ ] current driver/code hashを実行前に記録し、同じ要件の指定レビュー/必要修正後、新code HEADのpackage/executionを再封印する。資料/READMEのみの変更でも旧sealのcodeCommitを黙って書換えない。

Task2b-aの委譲枠: 指定ClaudeのRead/Grep/Globだけのsource調査1回（248.817秒/exit0/停止確認済み、outside_changesなし）と、実装後の同じ受け入れ基準のレビュー1回。採用した不具合修正の再確認は別途記録する。source調査はnative全layoutの比較器とruntime-onlyの件数不一致を確認し、BSONのmodule名/位置/3D-only metadataとnative生成物の相違を具体化した。最初のローカルF#試作は、linkを初期化せずBoolDriveの19操作を生成できた。native defaults/aliasの未確認は残し、Task2b完了とはしない。記録はPARENT_ROOT/tmp/agents/emission-sdk-join.p7zq2tov。

Task2b-a完了記録: code `b0383cd`（入口）→`206fb44`（F1/F2修正）→`54c3011`（F2/R1残り修正）→`49db2fa`（READMEのhash対象だけ明確化）。全115passed/5.99s、compileall/diff exit0。最初の実SDK試行はF#型推論エラーで失敗として保持し、文字列型注釈を修正して新試行を実行した。最新r4はtoolchain/restore/build/runを分離し、空feed・環境allowlist・`dotnet msbuild -noAutoResponse`・user wildcard import無効化・DLL直接実行で、bool19/color31/probe219操作すべて成功。これは古いseal/code505のPGをオフライン入力として新exporterを検証した事実だけで、新HEADのpackageやlive適用性ではない。

指定Claudeの実装レビュー211.189秒/exit0/stoppedはF1越境とF2build出所を指摘。F1/F2採用、F3timeoutはLかつ検証への外側timeout禁止によりskip。限定再確認57.787秒はF1解決とF2/R1残りを指摘、実MSBuildでresponse-fileの影響を再現し修正。最後の限定再確認60.983秒/exit0/stoppedはR1解決/新regressionなし/限定した説明は正確とした。4runとも実model claude-opus-5-5、Read/Grep/Globだけ、MCPなし、outside_changes=[]。原指摘・裁定・各失敗試行は保存する。READMEだけの最終表記修正に追加モデルreviewは行わない。

この部分の完了とTask2b全体の完了を混同しない。Task2b-a完了時点では全layout/default/alias照合、runtime join、Root診断化・自動回復controllerは未実装だった。現在の状態は後続のTask2b-b/c完了記録を基準とする。新package/実機preflight/native0–6/再capture拒否/復元cleanup/元工程は未実施。接続/書込0、公開未実施。

### Task2b-b: native defaults・alias・全layout照合

既存Task2bの次の小区切り。current SDKの全操作を基準に、slot/component/memberの全件とprivate/internal参照を照合してからruntime意味検査へ接続する。BSONのruntime意味検査を保持し、3D metadataをnative期待へ写さない。未知defaultは成功にせず、exact native DLLのIL根拠を追加採取する。

委譲枠は、指定ClaudeのRead/Grep/Globだけの未解決defaults/SyncType/alias調査1回と実装レビュー1回。採用修正の限定再確認は必要箇所だけ別記する。1run720秒、fallbackなし、個人設定無変更、実tool/終了/停止/outside_changesを確認する。controllerは同期で待ち、IL解析と代表Sテスト・実SDK入力検証を実施する。未知の挙動が残れば範囲と根拠不足を記録して追加の採取へ進む。

テストはSのみ。全layoutの余分なslot/component/member、誤った既定値/型、private portと内部member aliasの取り違え、別native DLL/default根拠の混入による誤成功を代表正負例で防ぐ。固定文言や全組合せのテストは作らない。read-only IL採取・構造検査・suite/compile/diffと実オフライン3moduleによる検証を行う。Root診断/回復controllerやnative/fullIssue成功はこの小区切りだけで完了にしない。

Task2b-b完了記録: code `417fe08`→`9d803c1`、全120passed/6.19s、compileall/diff exit0。exact native ILの追加採取と35closed typeのgeneric宣言型を含むschema抽出、6関連DLLへのmodel binding、全slot/component/member/default/reference/alias照合、検証済み未送信defaultだけを除くruntime projection、元layout/BSON receiptと所有private fieldを結ぶnative stageを追加した。3つの保存済みSDK入力（19/31/219操作）をオフラインのmodel materializationへ適用して全照合を検証したが、実観測nativeやcurrentHEAD live packageの証拠ではない。旧505seal/rawは不変。

指定Claudeのsource調査429.036秒、実装レビュー237.491秒、採用F1の限定再確認22.674秒はすべてexit0/停止確認済み/outside_changes=[]、実model claude-opus-5-5、Read/Grep/Globだけ/MCPなし。F1は、明示送信されたEnabled=falseをdefault名だけでruntime比較から除ける潜在的な誤成功を実際にREDで再現し、未送信条件で修正した。最後の限定再確認はF1解決/新regressionなし。F2はsource defectではなくcoverage-onlyで、既存guardのD/Lテストは増やさず、隔離fake-CLIで元receipt→所有→全layout/runtime joinの正例と元layout-byte改変の拒否を一時検証した。初回のPATH変更による正当なbuild-context拒否と、IL/schemaの失敗試行も保持する。原結果・裁定・ログはPARENT_ROOT/tmp/agents/emission-native-layout.asdk5_j0。

全Task2bは未完了。Task2b-b完了時点ではRoot診断化・実際の自動回復/retry controller、新HEAD package/driver hash/preflight/native0–6/別再capture拒否/復元cleanup/元工程は未実施だった。Root診断と固定読取の後続結果はTask2b-cに記録する。新経路の旧`id_maps`引数は参照せず、native対応表は全構造から導出する。接続/書込0、公開未実施。

### Task2b-c: Root診断化・cleanup境界と固定読取の回復

作成前の`reviewed_parent`全値比較と、Rootを安定親とした最終cleanupから全値一致条件を除く。Rootの完全構造/ID、明示した保護対象、所有fixtureだけの削除、既存のsession/diff/SDK/raw検査を保持する。Rootの時点値変化と追加は診断にし、所有外のslot/component消失は成功にしない。これは削除の境界の保全を確認するためであり、並行した消失の原因を断定するためではない。

テストは既存のprecreate/cleanupの代表Sテストへ、動いているRootの正例と保護対象の破損/誤削除の拒否を組み込む。新しい固定文言/L/Dテストは増やさない。suite/compileall/diffを同期実行し、固定読取controllerは隔離fake CLIと新しい実機診断資料で確認する。失敗したraw/attemptを上書きせず、読取失敗はbackoff・新試行、同じ失敗の反復はsource調査へ戻す。mutationの回復は次の未完了項目として区別する。

この区切りは指定ClaudeのRead/Grep/Glob限定の実装・結果レビュー1回（720秒、fallbackなし）を使い、採用修正が必要な場合だけ限定再確認を別記する。実tool/MCP/exit/停止/outside_changesを確認する。現在の利用者申告は16070/前面である。実機診断だけで全Task2b/native/Issue完了にせず、currentHEAD package封印/完全preflight/mutation-aware controller/元工程を残す。

Task2b-c完了記録: code`d2fa633`、121passed/compileall/diff。旧2経路のRoot値変化によるREDを実際に再現し、明示保護subtree/祖先・bool/int・所有外の消失拒否を保持して修正した。作成前とRoot最終cleanupへ接続し、非Root所有親の厳密比較は保持する。local-only固定読取controllerの実fake CLIで、原失敗記録を保持した新試行の成功と、同一失敗反復からsource調査への切替を確認した。永久のL/F/Dテストは追加していない。

16070の新しい実機診断は06:16:28.172229–06:16:55.176519UTC、7読取/7exit0/1attempt。両Root8953slots/17977components、追加/消失0、全Root比較4226issueは診断として残し、Root contextは合格。native-session field/discoveryの局所整合のみであり、producer source/明示保護対象の意味/完全preflight/native0–6は未検証、world write0。driver/code hashを新試行へ結び、旧raw/seal/Beforeは未変更。全Task2bは未完了で、mutationの適用状況/Done/所有/終了/checkpointを確認するfixed-phase controllerが次である。

指定Claudeの実装・結果レビュー135.531秒/exit0/停止確認済み/outside_changes=[]はPASS、実modelclaude-opus-5-5、公開Read/Grep/Glob、使用Read15/Grep8/Glob1、MCPなし。唯一のF1Lowはlocal-only読取driverの交互failure signatureで終了しない可能性であり、偽成功/書込はなく実1attemptへ影響なし。Lの生存性だけの指摘としてskip、永久テスト/外側timeout/追加reviewは不要と裁定した。レビューworktreeはclean/停止確認後に削除。原指摘・裁定・全raw・fake/RED/GREENはPARENT_ROOT/tmp/agents/emission-native-controller.0wmzw5erに保存。公開未実施。

### Task2b-d: private Commandの適用確認と逐次再試行（この部分のみ完了）

まずmutable Commandの固定1–6と独立した再capture拒否要求に区切る。任意argvやwriter callbackを受け取らず、検証済みNativeDeployedStageからprivate Command componentだけを導出して`component set … Value N`を同期実行する。元baselineから期待を生成し、完全field/Before/Done、session/fixture/型/所有/SDK、helper役割を再検証する。実機readerは現在の新しいNativeDeployedStageを返す読み取り専用の依存として分離する。

適用済みなら再送せず先へ進み、元checkpointと完全一致する未適用なら新attemptへ再試行する。Commandだけ変わった部分適用や未知状態は再観測し、反復時はsource調査へ返す（Issue全体停止や追加許可待ちではない）。executionごとの排他とprocess終了確認、launch前intent/実終了コード/raw、新attempt別記録、元baselineのfingerprintを保持する。クラッシュ後のprocess不明は再送しない。

受け入れ基準は共通基準を維持し、実入力は完全HDR/Linear・sRGB/alpha、boolと非ASCII context。防御対象はtimeout後の重複write、部分captureのBefore上書き、別session/私有field/元baselineへの切替、同時writer、旧receiptの再利用。対象外はcreate/deploy/helper削除/最終cleanupの実行制御とfullpreflightそのもの。これらは次のTask2b作業として残し、Command部分だけでfull mutation controller完了にしない。

SテストはCLIの失敗後に適用済みなら一度しか送らない正例、未適用からの再試行、部分適用/別context/同時writer/クラッシュ不明時の誤送信拒否を代表例で実行する。文言/一覧/F/L/Dテストは増やさない。既存suite/compile/diffとfake CLIで検証し、実機成功とは呼ばない。指定ClaudeのRead/Grep/Globだけの実装レビュー1回（720秒、fallbackなし）、採用修正の限定再確認のみを使用する。元raw/seal/Beforeは不変。実装・レビュー後に新HEAD packageと実機reader/残り制御を結ぶ。

Task2b-d完了記録: code`d96327a`→`bf020f8`。Command1–6/独立再captureの内部実行処理、execution単位のwriter lock、元baseline descriptor/state binding、launch intent/process group終了/raw/新観測と別attemptを実装した。元のphase期待は`phase_expectations`に分離し、A/B/C/Before/bool/完全色/OnWritten/OnFailは変更しない。既存121passedを引継時に再確認し、4件の代表Sテスト追加後125passed/6.40s、compileall/diff exit0。fake CLIは実プロセスとして起動するが、native検証の依存はstubであり、実機統合やnative成功の証拠ではない。

指定Claudeの実装レビュー190.448秒/exit0/停止確認済み/outside_changes=[]、実modelclaude-opus-5-5、Read/Grep/Globのみ/MCPなし、PASS_WITH_ISSUES。F1Lowの書込直後読取失敗に再観測が不足する点は、unconfirmed read回数と未適用write回数を分けて修正した。一時fake検証で修正前は2観測でsource-investigation、修正後は3観測でapplied、いずれもCLI1回。Lのみなので永久テストは増やさない。F2Lowは実行CLIのPATH解決先/実versionを封印cliVersion/SDK/sourceと照合するfullpreflightが後続で必須とREADMEへ明記して対応。Command API単体にCLI binary inventoryの認証があるとは扱わない。F3Infoのraw hash追加はoptionalでskip、stage descriptor/state fingerprintと記載する。F4Infoの各phase期待treeを封印宣言/元baselineから導出する点は、未実装の実機readerで守る。

同じ指定Claudeの限定再確認40.631秒/exit0/停止確認済み/outside_changes=[]、Read/Grep/Globのみ/MCPなしはCLOSED、F1解決/F2文書による対応完了、新regressionなし。原raw/review/rulings/fake検証はPARENT_ROOT/tmp/agents/emission-mutation-controller.pp7lz4c2へ保存。既存の全Root診断/SDK/raw/seal/Beforeは不変。

**残作業:** 全Task2bは未完了。新しいNativeDeployedStageの実機reader、create/deploy/helper削除/最終cleanupの適用済み/未適用/部分適用/不明と回復、currentdriver/source-producer/保護意味baseline/fullpreflight、新HEAD package、実機0–6/別再capture拒否/復元cleanupと元工程を次に実装する。今回の実機call/write/resourceは0。公開未実施、通常の許可待ちではない。

### Task2b-e: deployed native readerの接続（この部分のみ完了）

Command controllerが要求する新しいNativeDeployedStageを実際の固定読取で採取する。元anchorの独立検証を先に行い、session-before/fixture/protected/diff/session-afterを別receiptへ保存する。期待treeは元anchorの安定構造・metadata・IDを保持し、module部分だけは元layout receipt/current DLL modelから構成する。型/IDを固定したprivate Valueだけを現在値の観測として取り出す。これはBeforeやphase成功期待の採用ではなく、適用済み/未適用/部分適用の分類入力である。phase期待は元baselineだけから生成し、未知kind/default/余分なmetadataは受理しない。

受け入れ基準は共通基準と元機能要件を維持。環境はcurrent SDK/native DLL/Python3.14/uv。入力は非ASCII session、完全HDR/alpha/profile、bool、元値と異なる部分適用、helper有/無。防御範囲はanchor/保護対象/所有/receipt/diff/current layout/型/Beforeの取り違えと観測丸写しによる誤成功。create-onlyの認証、create/deploy/delete実行制御と完全preflightそのものは別の残作業である。

Sテストは、正当なprivate現在値を取得しながら元anchorを変更しない例と、型/metadata/参照/保護/receipt不一致の代表的拒否を実実装へ入力する。重複の層/組合せ、固定文言やLだけの永久テストは追加しない。fake CLIの固定5読取と既存native全構造検査への接続を検証し、実機成功とは呼ばない。同期suite/compile/diff、指定ClaudeのRead/Grep/Glob限定実装レビュー1回（720秒）と採用修正の限定再確認だけを行う。作業全体の時間制限なし/既存予算記録/30分checkpointを維持する。

Task2b-e実装レビュー: code`d38ba66`、127passed/6.59s/compileall/diff。指定Claude190.474秒/exit0/停止確認済み/outside_changes=[]、実modelclaude-opus-5-5、Read/Grep/Globのみ/MCPなし、PASS。Sテスト2件、pure scope/native bool modelは実処理、collector境界はstubのため実CLI/native統合成功ではない。I2Infoの未使用FAKE_DIFF_DATA設定は無害な任意整理としてskip。I1Infoの読取結果を初回baselineへ流用しない条件は、次の初期値照合で具体化する。実機call/write0。

### Task2b-f: 初回baselineを封印宣言の初期値へ結ぶ（Command入口のみ完了）

readerの現在値と初回baselineを同じNativeDeployedStageで表していても、Command実行前には封印した全private initialFieldsとの一致を別途検証する。全11fieldの型/完全値を照合し、Command/Done/Capturedだけの未使用判定で任意のTarget/Beforeを採用しない。元のpure phase比較APIの意味は変えず、実行controllerのbaseline入口へこの検査を接続する。

色4成分入力のprofileは推測せず、現current DLLのILを新規採取した。CLI ValueCodec.ColorXはLink.colorXをinitobjしRGBAのみ設定、FrooxEngine.ResoniteLinkTypeMapper.ToEngineはProfile null時にenum1を使い、Renderite.Shared.ColorProfile.sRGB=1である。native型の単なるconstructor既定値からの推測ではない。CLI0.2.0/current6DLL modelに解釈を結び、異なる版/DLLは新しいsource調査へ返す。初回採取/r2の原IL・hash/MVID/実restore/build/runはPARENT_ROOT/tmp/agents/emission-native-reader.azz5cvq_に保存、world call0。

共通受け入れ基準/環境/防御範囲に加え、実入力はBeforeColor/ColorAfter=[0,0,0,1]/sRGB、ColorTarget=[4.25,.5,1.125,.3125]/sRGBと各bool/int。防ぐのは観測済み任意値を新しいBefore/Targetの基準へ採用する誤成功である。Sの代表正例と完全色/型/Before差異の拒否を初期値比較モジュールで検証し、controller既存Sへ接続する。F/L/Dを追加しない。suite/compile/diff同期、同じ指定ClaudeのRead/Grep/Glob限定source/実装レビュー1回（720秒）と必要な採用修正の限定確認だけを行う。create-only全metadata/初回anchor/配備削除制御/実機preflightは残作業であり、これだけで実機書込に進まない。

Task2b-f完了記録: code`8f5d431`→`40a76fd`、128passed/6.48s/compileall/diff exit0。`compare_initial_fields`を認証済みnative baselineの直後に接続し、初期11fieldの完全値・型・profileとsealed initialFieldsを照合する。元のpure phase比較は維持。新S1件、controller既存Sの初期値とbaseline差替えのfingerprintを更新し、D/Lの追加なし。

指定Claudeのsource/実装レビュー219.400秒はPASS_WITH_ISSUES、読取結果を任意の初回baselineへ採用しない条件I1はCommand入口でCLOSED。F1Lowのfingerprintテストの緩いregexを既存Sの中で具体的な`command-baseline-binding-changed`へ修正。F2Lowは次のfinal native stage0判定に同じ初期値照合またはcontroller journalとの一致を結ぶ未実装義務としてdeferred（旧generic offlineの意味は維持）。F3InfoはREADMEのsource根拠を採取したValueCodec/engine mapperに限定し、initialFieldsからcodecまでの呼出経路/実CLI同一性をfullpreflightに残すと明記した。限定再確認27.240秒はclosed/新regressionなし。3run（reader190.474秒を含む）とも実claude-opus-5-5/CLI2.1.319、Read/Grep/Globのみ/MCPなし/exit0/停止確認済み/outside_changes=[]。

現在の実機call/write/resourceは0。新native readerと初期値検査の実装完了を、create-onlyの全metadata/所有認証、最初のanchor、create/deploy/helper削除/最終cleanupの回復制御、新package/全preflight/実機0–6/Issue全体の完了とは扱わない。原証拠・失敗した構文/fixture試行・原IL/receipt・レビュー・裁定はPARENT_ROOT/tmp/agents/emission-native-reader.azz5cvq_へ保持する。公開未実施。

### Task2b-g: created-only graph / stage と最終stage0の初期値照合（着手）

module未配備のfixtureはdeployed native graphとは別のCreatedStageで扱う。seal.normalizedFixtureとcurrent6DLL modelのslot schema、ValueField<int/bool/colorX>/ObjectRoot/AI_GeneratedContentのGetSyncMember・ComponentBase初期化から完全期待を作る。観測から使うのは宣言/stateへ一対一に結んだ実IDだけで、stable metadata/default/初期private値を観測へ合わせない。空roleを一般native graphへ解禁せず、CreatedStage専用branchで完全照合する。初回probe anchorはこのcreated scopeに元probe layout/BSONを加えた新しいNativeDeployedStageで認証する。

環境/共通受け入れ基準は維持。実入力はprivate完全RGBA/sRGB・bool・全slot/component/member、余分/欠落metadata、重複member ID、未知値/型、誤親・外部参照。防御範囲はcreated-onlyを既存パネル/異なる宣言/部分apply/未知metadataと取り違えること。既存のreceipt/session/protected/diff検査を使い、CreatedStageの正例と異常metadata/alias/初期値拒否を代表Sで確かめる。さらにdeferred INITIAL-F2をnative final stage0で同じ初期値APIへ接続し、legacy generic offlineは維持する。重複F/L/Dは増やさず同期suite/compile/diff/必要な一時入力で確認する。

current installed CLIのMapSlot/Inspect/AddPathsとnative schemaをsource根拠へ結び、readonly IL採取は新規session出力へ行う。指定Claude Read/Grep/Globのみのsource/実装レビュー1回（720秒）、採用修正の限定再確認のみ。create/deploy/delete実行controller、完全preflight、新HEAD package、実機試験は別の残作業であり、この型/照合の成功を実機write許可とは扱わない。今回の実行委任内で保護・比較の境界を具体化し、新たな確認待ちは作らない。

## Task 3: preflight・native Drivegate・回復/再試行

**Files:** 試行専用raw/log/state/verdictはPARENT_ROOT/tmp/agentsのセッション領域、結果を本Spec/Plan/ledgerへ追記。
**テスト:** Task1/2/2bのSを再利用。native成功/拒否は実測で確認し、新規文言テストなし。
- [x] 旧読取preflightとRoot差分の実採取を実施（当時基準で停止、native未実行）。
- [ ] current context/doctor/session/所有/明示保護対象/controls/完全色/型/実参照を確認。Root全値一致は要求せず、値変化・接続差は自動再採取/再planする。
- [ ] panel/fixture詳細diff、新root不在/作成予定write-set、sealed inputs、全SDK結線をそろえる。保護範囲の調整は理由を記録して担当判断で行い、追加確認待ちを作らない。
- [ ] 元機能仕様に照らして現在の意味baselineを準備・記録し、指定Claudeへ同じ現行方針で独立レビューを依頼する。観測の丸写しを適合判定にしない。
- [ ] 新fixtureだけapply、3moduleを別親/別stateへ逐次deploy。失敗時も現在の適用/所有/プロセスを確かめて回復・自動再試行する。
- [ ] Spec0–6/別再capture拒否、native outcome/readback/Done、helper所有/不在、Before完全復元を実測する。不一致は原結果を保存し、原因修正・回復・再試行へ進む。
- [ ] 所有fixtureをcleanupし、対象不在/明示保護対象/write-setを検証する。Root姿勢の完全静止は要求しない。削除が適用済みなら再削除せず不在確認で完了する。
- [ ] 最終成功結果を指定レビューし、実測/未確認/残存path/各retryを記録する。

## Task 4: 元Plan残り・同一テーマでの公開

**Files:** 元Task4/5/6の必要変更、README、同じSpec/Plan。必要な保護/比較の変更は本Issueの委任内で具体化する。
**テスト:** 変更ごとにS/L/F/D判定しSだけ追加。実UI/二人/save-reloadを模擬で代用しない。
- [ ] Task3成功/結果レビュー/復元cleanup後にS4残りの全条件を準備・検証。
- [ ] S4→S5→S6b→S6→S7と元Task4実UI/Task6を進める。技術的に必要な参加/操作と、不要になった保護範囲の許可確認を区別する。
- [ ] 最終検証/指定レビュー/秘密情報検査→検査済みSHA push→コードPR1本/必要な同テーマ文書PR1本。Issue3部分ならRefs #3/open維持、手動merge。
- [ ] 失敗は自動回復・再試行し、保護範囲の再承認待ちで終了しない。利用者が明示的に引き継ぎを指示した場合等は現在状態と回復手順を残す。

## 実行履歴と現在の未完了

詳細は本書/Specの`edb7de5332107d69a081798eb78b007082cd62a3`以前のGit履歴と保存raw/review/ledgerにある。過去の「停止せよ」「再開許可待ち」「Root一致blocking」は現在の進行規則ではない。

- 20:16の17期待/18creates: installed標準marker差を検出、write0。当時失敗のまま保持し、v3正規化で対応した。
- 02:21の5読取: Root8953Slot/17977Component、835未対応leafでinconclusive。当時write0、後に保全carrierを対応した。
- reviewerの/tmp計時file逸脱: 当時停止、過去の存在/上書き不明。現在はtool制限の実証で解消済み。
- 03:21の6読取: 両Root完全形状、1415slot metadata/2792typed memberの診断差分、旧完全一致gateでfailed。after bracket未採取、write0。113.439秒の指定レビューは当時条件で停止妥当とした。**Root時点差分を現在のblocking理由にはせず、新方針で自動継続する。**
- `emission-native-finish.nkermyxf`の新packageはcode505の記録。文書改訂や将来の実装修正後は出所を再確認し、必要な新packageを作る。旧seal/判定は変更しない。
- 今回は方針記載の改訂であり、Task2bの実装修正・native再試行・baseline承認・全Issue完了はまだ実行済みとしない。公開未実施。

既存ledger: PARENT_ROOT/tmp/agents/emission-native-gate.oq3olakn/sdd/2026-11-07-emission-issue-3-native-gate/progress.md。旧証拠はemission-native-{live,next,finish}の各保存領域、新しい文書改訂記録はPARENT_ROOT/tmp/agents/issue-3-policy.xan7gp06。
