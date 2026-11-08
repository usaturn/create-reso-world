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

## Task 2b: 新ルールを実行側へ反映しSDK layout接続を完成する（未実装）

**Files:** controllerの試行/観測手順、`tools/drivegate-native-layout/`、`drivegate_native.py`、必要な`drivegate_evidence.py`/`drivegate_runtime.py`/対応Sテスト、README、試行brief。
**テスト:** S。正当なRoot時点差分でprivate操作を誤拒否しない正例と、誤対象write/delete・Before上書き・timeout後の二重適用・未知metadataの成功化を防ぐ代表例。スクリプト文言や全組合せF/L/Dは追加しない。同期suite/compile/diff、隔離copyの実SDK検証を行う。
- [ ] 旧`check_fresh_root.py`の全Root compare_subtree失敗によるassert終了を現行実行手順へ転用しない。Root差分は診断、明示対象のsession/所有/write-set等は別に判定する。
- [ ] 読取/検査/接続失敗を自動回復・再試行する。mutationの適用済み/未適用/部分適用/不明を区別し、実体/Done/所有/終了確認後に継続する。任意コマンドの汎用再送APIは作らない。
- [ ] Task2b-a: exact installed SDKの純粋な操作生成APIを、封印PGの隔離コピーで実行する内部exporter/receiptを追加する。全AddSlot/AddComponentと記号private bindingを生成し、入力・exporter・SDK/native DLL inventory・終了コード・原出力を保存する。既存ファイルの上書き、失敗の成功化、seal外PG/別DLLの混入を代表Sテストで防ぎ、実SDKは3moduleをオフライン実行する。新規native接続なし。
- [ ] runtime-only SDK graphとnative全layoutの接続を修正する。passive metadataの全field/default/reference/slotをcurrent producerから検証し、3D-only BSON metadataやpersistant-IDを誤解釈しない。非runtime全除外で解決しない。
- [ ] current driver/code hashを実行前に記録し、同じ要件の指定レビュー/必要修正後、新code HEADのpackage/executionを再封印する。資料/READMEのみの変更でも旧sealのcodeCommitを黙って書換えない。

Task2b-aの委譲枠: 指定ClaudeのRead/Grep/Globだけのsource調査1回（248.817秒/exit0/停止確認済み、outside_changesなし）と、実装後の同じ受け入れ基準のレビュー1回。採用した不具合修正の再確認は別途記録する。source調査はnative全layoutの比較器とruntime-onlyの件数不一致を確認し、BSONのmodule名/位置/3D-only metadataとnative生成物の相違を具体化した。最初のローカルF#試作は、linkを初期化せずBoolDriveの19操作を生成できた。native defaults/aliasの未確認は残し、Task2b完了とはしない。記録はPARENT_ROOT/tmp/agents/emission-sdk-join.p7zq2tov。

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
