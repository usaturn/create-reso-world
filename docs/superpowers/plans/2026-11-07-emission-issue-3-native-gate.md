# Issue #3 native Drivegate 実行計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development for implementation tasks; controller executes live verification sequentially. Steps use checkbox syntax.

**Goal:** 欠けている短いDrivegateの実行物と照合を整え、元Task4/5/6の未完了を順番に減らす。
**Architecture:** 既存raw基盤→隔離package/SDK生成物の封印→意味/範囲/phase gate→fresh preflight→controllerの逐次実機。
**Tech Stack:** Python3.14/uv、標準ライブラリ、ResoLoop0.2.0、Flux SDKと現行DLL、ProtoGraph。
**Spec:** ../specs/2026-11-07-emission-issue-3-native-gate-design.md

- 状態: draft（現在の具体的な不足を示した後の利用者の全面的な実行委任により実行、承認SHAは発明しない）。
- 本計画はraw基盤のcompleted Planを再開せず、元open PlanのS4 native前提の具体化を記録する。同じテーマの追加修正は本書を更新する。
- code base743f1f9 / docs base0d58ac7。ブランチはSpec記載。旧保全文書worktreeを変更しない。
- 実装担当は検査済みissue assignment selfを既定とし、bounded sp-implementerへTask別委譲。レビューはclaude-code_opus_defaultのみ（inspect/self-review/fix-checkに委譲する場合も同じ、fallbackなし）。
- 最新の具体的な実行委任は不足する試験準備と既存範囲の実機write/cleanupも含むが、必須gate・安全失敗時の停止・手動mergeは維持する。

## Global Constraints
- Python3.14/uv/標準ライブラリ。PR4 read_receipts.pyは再利用し、raw基盤を再実装しない。
- 旧tmp/worlds/tools、旧state/session、古いrun/IDを探索・復元・再生しない。
- 新しいlinked worktreeで実装し、常設/親HEAD・既存文書worktree・元PGと既存証跡を変更しない。
- 新fixtureのprivate ValueFieldだけが試験write/delete対象。実アバター/保存パネル/既存syntheticへ書かない。
- sealされた原本とdeploy用copyを分け、compilerの全経路のsidecarを隔離する。
- mutation担当/検証を外側timeoutで止めない。最初の実機不一致/切断/安全失敗で停止、自動修復なし。
- 短いgateをS4全体や実UI/Task6の成功としない。S4→S5→S6b→S6→S7の依存順を維持。
- コードPR1本＋必要な同テーマ文書PR1本へ集約、手動merge、Issue3 open。実session/state/brsonをcommitしない。

## 受け入れ基準・防御範囲・動作環境
Specの同名節と「専用fixtureとnative手順」「package・保全・preflight」を各担当/レビューbriefへ同文で渡す。
動作環境はDev Container、Python3.14以上、現在のSDK/DLLを明示したcheck/buildと16070（実行時に現在確認）。
実入力はnative HDR/alpha非1/LinearとsRGBの完全色、bool、非ASCII raw JSON。別processの再採取は異transportの独立検証と呼ばない。
防御対象は誤対象write/delete・履歴/利用者ファイルの上書き・改変/失敗の受理・完全色/型の欠落。対象外は全証跡の整合的な悪意ある書換えの認証・厳密な複数利用者排他。
必須検証: code repoでuv sync --locked、uv run pytest、変更PGすべての実check/build/manifest検証、Python compile、git diff --check。旧52passedは不変raw基盤の根拠として再利用し、新コード/PG/実機結果へ流用しない。

## Review Focus
1. helperを削除する際に別module/保存パネル/ユーザ所有部分を対象にしない。
2. mutable入力のOnWritten/OnFailと、CLI exit0やValueCopyのhookを取り違えない。
3. 前面化・session・seal・詳細diff・全subtreeのどれかが欠けたままwriteへ進まない。
4. bool/int・欠落/null・完全colorXのprofile/alpha差を見逃さない。
5. 元PG/封印物の隣へcompiler sidecarを出さず、同じphaseや古いstateで復元記録を上書きしない。

## 実行予算
当初は今回の不足前提/最初のnative gateに180能動分。2026-11-08再開時、利用者が時間制限なしを明示したため、この上限は解除するが過去の所要時間は保持する。元ledgerはPARENT_ROOT/tmp/agents/emission-native-gate.oq3olakn/budget.jsonl（endまで記録済み、約169.1能動分）。budget開始前17:46:16–17:48:54の準備約2分38秒は別記し、既存の過去予算はリセットしない。今回の着手は01:49:55UTC、続行記録はPARENT_ROOT/tmp/agents/emission-native-next.gk7mchty/continuation.jsonl。30分checkpointとTask別所要時間は引き続き記録し、安全停止は解除しない。
準備15、package/判定実装55、検証/レビュー30、fresh preflight/native60、保存/公開20分を目安。元Task4/5/6全完了までの保証時間ではない。
30能動分ごと・Task境界・50%/100%・失敗直後にcheckpoint。worker目安30分、保存予約5分、無進捗10分でcontroller確認（共有writer/検証をkillしない）。reviewerは各12分枠内、Task1・全差分/実機前・native結果の3段階を同じ1名で担当する。採用修正確認が必要なら同じ担当に範囲限定。PR後の追加ループは起動しない。
同じ信頼性失敗の再試行1回、安全失敗は全停止。予算不足は同じbranchに保全してhandoffし、小タスクごとにPRを増やさない。

## contingency（代替策）
最初のREDで実API/SDK出力の前提差が判明したら、仕様の意味を保つ最小修正をledgerに残す。mutable writerの期待OnFailやboolの性質が実機で成立しなければ、期待値/本体PGを変えて通さず停止。資料が欠けている場合はoldtmpを復元せず必要な新規資料を本branchで準備。full gateに時間が足りなければ封印packageとS回帰を保全して次の担当へ渡し、native成功とはしない。

### Task 1: 専用3PGと隔離package/封印を実装する
**Files:** 新規 flux/emission-editor/drivegate/{DriveGateProbe,ColorDrive,BoolDrive}.pg、scripts/emission_editor/drivegate_package.py、tests/test_emission_drivegate_package.py、READMEの範囲説明。
**Interfaces:** fixture_declaration(token) -> dict。prepare_package(destination: Path, token: str, *, library_path: Path) -> dict はcopy上でcheck/build/manifest検証し全過程exit0後のみsealを返す。verify_package(path: Path) -> dict は全入力/生成SDK record/manifestの完全file-setとhashを照合。Source PGの原本は変更しない。生成manifestのworld/Flux stateは試行専用で初回不在。実装結果のv2は別のsibling実行領域を作り、全manifestが実行領域だけを指す。verify_execution(package_path, execution_path)はfresh実行領域の全file-set/hashを封印物と照合する。Git clean/HEADの前後照合でcodeCommitの出所を確認する。
**テスト:** S（元ソース/既存出力/利用者ファイルの上書き、範囲外参照、sealの改変/不足/未知追加、失敗成功化を防止）。fake resoloopを実subprocessで動かしsidecarを書かせる。PGの型/構文はLなので実check/build、PG固定文字列テストは追加しない。
- [x] 生成物がprivate fieldのみ・3module別親/別state・外部target無しである正例と、既存directory/source/link/失敗/改変のS回帰を先にREDにする。
- [x] SpecのCommand0–6に沿って3PGを最小実装。Captureは一度、hostのみ、helperはeventless。完全native色を使い、mutable書込の結果とreadbackとDoneを記録。
- [x] package生成/コピー/SDK check/build/3manifest検証/封印を実装する。sourceディレクトリの全3PG/sidecar不変を実fake compilerで確認。
- [x] 対象pytest→全suite→実SDK check/build→manifest検証→compile→diffを同期実行し、ログ/elapsedをsessionへ保存する。
- [x] 明示したファイルだけcommit。claude-code_opus_defaultでTask品質と仕様のレビュー。必要修正は同じ担当でRED/GREENし、指摘原文と裁定を保存する。

実行記録: 8882ae5で3PG/package初版、3908f34で実行copyの分離とclean provenanceを修正。全71passed、実SDK43artifact/211DLL hash、コピー再build後も封印/原PG不変。Task1レビューF1–F3採用→限定再レビュー全addressed、PASS/PASS。raw/read_receiptsと既存PGは未変更。native成功/実機writeは0。詳細はSESSION/task1-fix1と同SDD/task-1-report.md。レビュー/修正は実装約15分＋修正約8分、レビュー128.581秒/限定78.535秒（controller能動内）。

### Task 2: 既存rawを使う意味/phase/範囲の照合を実装する
**Files:** scripts/emission_editor/drivegate_evidence.py、tests/test_emission_drivegate_evidence.py、固定diff採取のdrivegate_capture.py、stage/SDK結合のdrivegate_runtime.pyと各代表Sテスト、必要なpackage最小補足。一般的なmutationランナーは作らない。
**Interfaces:** raw receiptをload_readで検証し、sealed package/宣言/SDK record/現在typed観測に対してsession/時刻窓/別採取/全subtree/全結線/全memberを照合。native phase verdictは正常phaseと拒否phaseの正確な結果/対象値/Done/保全を照合。missingはinconclusive、completeとexecutionPermissionを安易にtrueにしない。任意CLIや旧state再生の入口を作らない。
**テスト:** S。bool/int/profile/alpha差、同receipt別path、別session/時刻・不足subtree/結線・別削除root/改変宣言と期待値・phase抜け/失敗を成功化しない代表正負例。模擬profile負例のdict共有はここで修正し、独立な入力を使う。
- [x] それぞれの損害の代表S正負例をRED→GREEN。L/F/Dの追加なし。
- [x] Task1のSDK生成recordの実形状から対応を実装し、独立に組み立てたraw入力/期待値で検証する。simulatedはnative成功にしない。
- [x] 全suite/静的検証、変更経路の安全確認。controllerがpackageとvalidator共通のID/型/順序を統合確認。
- [x] 同じbranchにcommitし、指定Claude1名の全差分/実機前レビューで確認。レビュー不能ならwriteしない。

実行記録: c46cef7まで。全104passed/compile/diff成功。実SDKの全3graphを封印済parseに結び、独立typed BoolDrive/所有graphで正例・実参照逸脱等の負例を確認。T2-R1（実宣言のcapture/restoreが観測不能）とT2-R2（未使用の弱いdiff API/2重複テスト）を採用し修正、唯一のClaudeで限定確認PASS/PASS。実行copy分離とclean provenanceはTask1で確認済み。現在使える新packageはSESSION/task2-fix1/sdk-observable、codeCommit=c46cef7、43ファイル/211DLL、正確なsibling executionRoot。過去sdk-finalは宣言変更により不適格であり、変更せず履歴として残す。present nullと欠落、保全専用opaque値とprivate target意味、SDKの正確なpersistant-ID表記とnative persistentの関係はSpecの実装記録に従う。native再capture拒否は未実施であり、6phase比較が代わりに証明しない。

#### Task2/3 接続部のinstalled正規化修正（2026-11-08）

**Files:** drivegate_package.py・drivegate_runtime.pyと対応Sテスト、README。本体PG/raw基盤には触らない。
**範囲:** Specの「2026-11-08 再開時の正規化補足」と既存受け入れ基準をそのまま適用する。input宣言へ自動metadataを重複記述せず、v3 sealに正規化期待モデルを保持する。precreate/配備後所有照合に一貫して使用し、markerはtyped Sourceと正確なkey/親/型を検証、private ValueFieldへ混入させない。
**テスト:** S（metadataの欠落/改変や余分なComponentを見逃した範囲許可を防止）。代表正負例だけ追加し、既存全subtree/偽CLIテストと統合する。CLI版拒否は、未対応の正規化を黙って許可する損害を防ぐS。文書/固定文言/ファイル一覧だけのFテストは追加しない。
**代わりの検証:** 全pytest、compile/diff、現在assembly前後hash付きIL再採取、sole-Claudeの修正範囲確認、新しいclean HEADから実SDK3PG/package/parse検証。過去失敗/旧sealは変更せず、修正後の成功やnative許可へ読み替えない。
- [x] source-groundedな正例と欠落/改変/余分なmetadata拒否をRED→GREENにする。
- [x] 全suite/compile/diff後にcommitし、同じ受け入れ基準・原文の要件を唯一のclaude-code_opus_defaultへ渡して確認する。
- [x] 新規IL証跡と新package/executionを準備し、nativePermission=falseのまま残る前面化/fullpreflight条件を明示する。

記録:74c0eab、106passed/compile/diff成功。roleツール2呼出しが無出力/レポートなしだったため、これ以上再試行せずcontrollerがinlineでこの限定修正を実装した。レビューは指定Claude1名だけ、実測205.587秒/exit0/停止確認済み/outside_changes=[]、SpecPASS・qualityPASS_WITH_ISSUES。R1Lowの実行物hash結合条件は、新package/実SDK3parseの前後hashと新sealSHAを結ぶcontroller記録で満たした。R2LowのSource型/kind負例追加候補は、実装の拒否が存在するため次の同領域変更/最終レビューまで保留。追加レビューループは実行していない。

新v3 package/executionはSESSION_NEXT/sdk-normalizedとそのsibling、43files/211DLL、全3実SDKcheck/build/manifest/parse成功。SESSION_NEXTはPARENT_ROOT/tmp/agents/emission-native-next.gk7mchty。current-binding-receipt.json・sdk-external-binding.json・package-characterization-binding.jsonで現在のbytesを結び、verify_ready_inputs.pyで再照合した。歴史的ILのhash bindingを遡って主張しない。現在のsource/IL characterizationは適切だが、adapter由来の実型/plan安定keyは次のfresh実観測でも厳密比較する。

今回のnativeアクセスは0。16070指定は前面化明示ではないため、Task3は現在のワールドの前面化と他編集の停止の明示待ち。fullpreflight/baselineレビュー/phase/recapture/cleanup/Task4以降は未完了。公開未実施。

#### Task2/3 接続部のRoot carrier保全修正（2026-11-08）

**Files:** drivegate_evidence.py・対応Sテスト・README。PG/raw/runtime・private writer意味判定は変更しない。
**範囲:** Spec「2026-11-08 fresh Root採取と保全専用carrierの補足」と既存受け入れ基準の同文をcontroller/reviewer共通briefにする。名前付き非有限値、完全RGBA/profile文字列carrier、既知float3/floatQ配列の全payloadを保全専用で照合する。未知kind/欠落を補わず、Rootの除外やprivate書込許可へ広げない。
**テスト:** S。変更された非有限値/profile/配列軸・要素・IDを黙って保全済みとする損害と、opaque値をprivate書込に許可する損害を防ぐ代表正負例だけを追加。CLI構文・固定文言のF/Lテストや組合せ網羅は追加しない。
**検証:** RED→GREEN、全suite/compile/diff、停止済みRoot原rawを使ったオフラインの形状/保全可能性確認、指定Claudeによる修正範囲と停止記録の確認、新しいclean HEADからの新seal/実SDK検証。原raw/停止判定を変更せず、自己照合を独立baselineへ読み替えない。
- [x] 2つの代表SテストをRED→GREENにし、全suite/compile/diff後に同じcode branchへcommitする。
- [ ] 同じ要件で唯一の指定Claudeにレビューし、原指摘と裁定を残す（実施済みだが実行範囲逸脱によりread-only gateとして未受理。下記参照）。
- [ ] 新code HEADの新package/executionと実SDKを準備・再照合する。停止windowのworld callは再開しない。

記録:505fb7b、108passed/compile/diff成功。停止済みRoot rawを使う最終HEADの自己形状照合はofflineのみpassed、source/blob/raw hashはSESSION_LIVE/final-head-local-verification.json。旧inconclusiveと過去のworking-tree参考結果は凍結し、native成功へ変えない。SESSION_LIVEはPARENT_ROOT/tmp/agents/emission-native-live.enko3n41。

指定Claudeの技術判定はSpecPASS・qualityPASS_WITH_ISSUES・sourceGROUNDED・停止妥当、実測143.204秒/exit0/停止確認済み/outside_changes=[]。Low R1の最終HEAD記録を新規ローカル検証で補完し、Info R2の配列組合せテストは代表Sで十分のため追加しない。原指摘はroot-carrier-review/result.json、裁定はcontroller-stop-ruling.md。

担当が明示範囲外の/tmp直下の固定名ファイルを計時用に作成・削除したと自己申告したため、実行範囲逸脱による安全上の停止を適用した。現在のパス不存在だけを確認し、過去の上書きや秘密漏洩を推測しない。Git監査はこの範囲を保証しない。技術PASSを次工程の許可にせず、追加review/fallback・新seal・実機再試行・公開を行わない。ローカル最終確認/記録/停止済み所有review worktree整理のみ実施。利用者が停止の解消を明示した後、同じClaudeの読取/検索専用ツール制限をCLI/adapter仕様で確かめる案と、完全に新しいpreflightを検討する。

新505fb7bpackageは未作成で旧74c0eabpackageを現版へ転用しない。前面化/他編集停止の明示は受領済み。今回の実機は5読取で停止、world writes0、baseline未承認、Task3/4未完了、公開未実施。

### Task 3: fresh preflightと短いDrivegateを逐次実行する
**Files:** 生成物/実raw/ログ/stateはSESSION以下だけ（commitしない）、Spec/Planの結果追記。
**テスト:** 新規テストなし。Task1/2のSを再利用し、実SDK/nativeの実出力と詳細diffを検証する。nativeの拒否機構と成功継続は実測でのみ確定する。
- [ ] 現在の前面化/16070/競合/現在sessionを確認、新試行のdiscover→別doctorから全fresh preflightを開始。
- [ ] 現在の全保護状態/controls/完全色/型/実参照から新しい保全基準を準備し、元Specと意味を照合して封印/指定Claude確認。旧G0復元や観測を丸写ししただけの適合判定はしない。panel/fixture詳細diff・root不在/新規作成だけの予定diff・seal・全raw gateをそろえる。
- [ ] 新fixtureだけapplyし、3moduleを別親/別stateに逐次deploy。各直前の範囲/入力と各直後の全結線/出力/対象を確認する。
- [ ] Specの0–6を順に実行し、各native outcome/readback/Doneと本体保全を照合。helperはfresh所有/subtree再確認後に1つずつ除去、解除後正例を確認。
- [ ] 初回不一致/切断で停止、修復や期待変更なし。成功時のみ元値/保全/静止と全所有を再確認してfixture1rootをcleanup、不在と本体詳細diff0/保全を確認。
- [ ] 結果レビュー、実測/未確認/残存パスを記録。短いgateだけでS4やTask4/6を完了にしない。

#### Task3 今回の停止（未完了）

最初の新規読取20:05:20UTCから、指定16070へ読取11件とprivate作成diff1件を実行した。doctor/同session/211DLL一致、完全panel1025Slot/2011Componentとsynthetic19Slot/21Componentの別プロセス保持を確認。20:16:36UTCのdiffは17期待に対し18creates（標準AI_GeneratedContent.Sourceが未宣言）となり、意味の照合FAILで停止した。native write=0。after bracket等を継ぎ足してfull preflightにしない。

installed GeneratedContentMetadata.csがrootの自動markerを、installed WorldService.csが現在のrecovery文面を定義する。古いfork checkoutの文面差を、installed source自体の不一致と表現しない。原因説明は封印済み期待値を変える許可ではない。残りはmarker等のinstalled正規化の明示的な取り扱い、独立baselineレビュー/panel詳細diff/完全Root保全/全bracket、new sealed inputs/fullfresh preflight、native全phase/再capture/cleanupと結果レビュー。本試行の再開や旧state復元はしない。Task1/2のcleanレビューや104テストで未完了を埋めない。

指定Claudeによる停止結果の確認は実測77.575秒/exit0/stopped、停止妥当・native_permission=false・baseline未承認。不正確だったworker報告のinstalled source差という表現は、古いfork checkoutとの差に訂正した。歴史的ILと現在binaryのhash bindingは未確認のまま残す。コードの新規修正・native再試行は行わない。

この統合検査が未解消のためpush/PRは行わず、コード1branch・文書1branchをローカル保全する（公開未実施）。同テーマの新規PRを進捗単位で増やさない。実行予算はリセットせず、停止結果の指定Claude確認とhandoffを行う。

### Task 4: 元Planの残りへ接続し、同一PRで公開する
**Files:** 元PlanのTask4/5/6に必要な変更だけ（判明時に本書へ具体的範囲/検証を追記）、同じbranch、README、Spec/Plan。
**テスト:** 各変更をS/L/F/Dで判定しSのみ追加。既存の検証を同版/同前提で再利用。実UI・二人・保存再読込を模擬で代用しない。
- [ ] Task3が成功し独立結果レビュー/cleanupを終えた場合だけ、S4残りの新しい全条件を準備・検証する。Task4全体未完了のままTask5を無条件に進めない。
- [ ] S4→S5→S6b→S6→S7と、元Task4実UI/Task6の未完了を順に対応。現場で必要な利用者操作は自動成功扱いにしない。
- [ ] 同じコード/文書branchで最終検証・指定Claudeの必要レビュー・秘密情報検査→同一SHA push→コードPR1本/同テーマ文書PR1本。Issue3部分進捗ならRefs #3、open維持。手動merge待ち。
- [ ] 予算/安全停止時は残るTaskをpendingとして保全しagent-handoff。PRを進捗単位で増やさない。
