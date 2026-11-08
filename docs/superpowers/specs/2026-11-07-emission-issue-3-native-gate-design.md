# Issue #3 native Drivegate と継続作業の仕様

- 状態: draft。コミットしただけで内容承認SHAを発明しない。
- 対象: `usaturn/resonite-emission-editor#3`。このIssueの完了まで、担当・セッションが変わっても以下の作業方針を適用する。
- 実行許可: 利用者の既存の準備・実装・実機確認の委任に加え、2026-11-08の具体的な変更指示を記録する。「Root全体の値は完全一致する必要はない」「最初の不一致で停止せず自動再試行する」「保護範囲を実質的に変える場合も、今回のIssue作業に限り確認不要」。直前の「今回のセッションに限り」は最新指示の「今回のIssue作業に限り」で置き換える。
- コード: `external/emission-editor/.worktrees/issue-3-native-gate`、`feat/issue-3-native-gate`。常設checkoutと親detached HEADは編集しない。
- 文書: create-reso-worldの`docs/resonite-emission-editor-issue-3-native-gate`ブランチ。コードrepoに残る元機能Spec/Planと、今回の作業・検証方針を区別する。

## 現在有効な作業方針（Issue #3限定）

この節は、同じIssueの旧Spec/Plan、brief、ledger、handoff、停止時の裁定にある、Root全値一致・初回不一致で作業全体停止・自動再試行禁止・保護範囲変更の再確認待ちより優先する。一般規約の実質変更時の確認は、本Issueでは利用者の明示的な事前委任で充足する。他のIssueやリポジトリへ例外を広げない。過去のraw、失敗判定、レビュー原文、sealは事実として保持し、旧失敗を遡って成功へ書き換えない。

1. **Root全体の値の完全一致を要求しない。** アバターや利用者の位置・回転・scale、solverや入力状態を含め、Rootの時点差分だけでpreflight失敗や作業停止にしない。Root全体を採取する場合も全payloadを残し、差分は診断情報として扱う。動作原因は観測だけから断定しない。
2. **不一致・切断・検査失敗は自動で調査・修正・再観測・再試行する。** 最初の不一致でIssue全体を止めたり、通常の再開許可を求めたりしない。失敗した試行と新しい試行の記録は分け、同じ失敗の無益な高速反復ではなく原因に応じて方法を自動変更する。
3. **保護範囲・比較対象・その実装の実質的な見直しも、本Issueでは利用者への追加確認なしに進める。** 担当が理由、新しい保護対象、検証方法をSpec/Plan/ledgerに記録し、実装・レビュー・再試行へ進む。新しい内容版の承認待ちを作らない。これは確認手続きの委任であり、未検証の成功報告、利用者データの破壊、対象外への書込の許可ではない。

## 目的・構成

元PlanのS4/R101以降に必要な、別所有fixtureの短いtyped Drivegateを現行の公開ソースから実行可能にする。PR4のraw receipt基盤は再実装しない。旧tmp/worlds/toolsや旧state/sessionを探索・復元・再生せず、現在の観測から必要な資料を新しく準備する。関連変更はコード1branch/PRと同テーマ文書1branch/PRへ集約する。

private ValueFieldだけのfixture、host-only mutable writer、eventlessなcolorX/bool Drive helperを別々の安定親へ置く。既存ReadbackProof/CommitProof全体の配備や、一般的な任意mutationランナーは採用しない。

## 受け入れ基準・環境・防御範囲

Dev Container、Python3.14/uv/標準ライブラリ、実行時に確認するResoLoop・Flux SDK・Resonite DLL。現在の接続先を確認し、port/session/実IDを公開ソースへ固定しない。

native colorXは完全RGBA/profile（HDR、alpha非1、Linear/sRGB）、bool、非ASCII raw JSONを扱う。boolと整数、欠落memberと既知null、型違いを同一視しない。installed CLI0.2.0のserializerが省略するnullable値は、完全なkind/id付きreference、またはkind/id/type付きfieldがpresentな場合に限り既知nullとして扱う。member欠落やunknown kindを補完せず、nullをfalse/0/空文字列に置換しない。

保全専用の比較は、名前付き非有限値`Infinity`/`-Infinity`/`NaN`、完全RGBAと非空profile文字列、既知`Array_float3`/`Array_floatQ`の全要素・軸・内外ID・payloadを保持する。型付きopaque値の保全とprivate writerへの意味解釈は別であり、private targetは有限値/Linear・sRGBの基準を維持する。低レベルの厳密比較APIを保持しても、それをRoot全体の一律な合否条件にはしない。

Rootの差分とは別に、次を検証する。
- 操作ごとに、現在のsession、明示した対象ID/親/型/所有、実際のwrite-set/delete-setを照合する。
- この短いgateのwrite/delete先は新規所有fixtureとそのmodule/helperだけ。既存パネル・実アバター・登録済みsynthetic・materialを試験対象にしない。動作を止めるための既存アバター変更も行わない。
- 封印資料、SDK生成物、実module/writer/Drive/global/binding/継続edge、private Before/対象/readback/Doneの意味を検証する。未知の情報を成功にせず、自動で必要な採取・解釈・実装修正へ進む。
- 既存パネル等の確認対象は、ツールの保持すべき値・参照・所有情報・登録内容などを明示する。Root全体の姿勢等の差分をこの対象へ無条件に混ぜない。確認対象の差分は原因と適用状況を調べて回復・再検証する。

厳密な他利用者排他、悪意ある管理者による全証跡の整合的な改ざんの認証は対象外。`complete`/`executionPermission`と個別検査結果を分け、CLI exit0だけでnative成功にしない。

## 自動再試行と回復

- 読取/接続の一時失敗は、現在contextを更新し、短いbackoffを入れて自動再試行する。Root全値一致が得られるframeを探すための再採取は不要である。
- 同じsignatureが続く場合は、同一操作の反復からsource調査、decoder/照合/実装の修正、再build、新しい試行への切替を自動で行う。「再試行1回まで」「失敗したらIssue全停止」という上限は本Issueへ適用しない。所要時間と進捗は記録し続ける。
- 書込/作成/削除/deployが失敗・timeoutした場合は、戻り値だけで未適用と決めず、先に現在の値・Done・実体・所有・state・プロセス終了を読み戻す。適用済みなら検証して先へ進み、未適用なら再試行し、部分適用なら所有範囲内で回復・再planして再試行する。状態不明のmutationを盲目的に重複送信しない。
- 1つのwrite担当が生存中に別のwrite担当を重ねない。生存/終了が不明なら、確認・再接続・ローカル修正を自動継続し、危険な重複操作は実施しない。
- Capture済みBeforeを現在値で上書きしない。再試行には現在試行の検証可能なcheckpointを使う。別session、帰属不明、改変済みの旧stateを再生しない。継続できない試行は証拠を保持し、所有確認したfixtureを安全に回復/片付け、新token/stateでやり直す。
- 正当なnative不具合は実装を調査・修正して再試行する。A/B/C、OnWritten/OnFail等の期待を観測結果へ合わせて成功にしない。失敗した試行の原raw/verdictを上書きせず、再試行ごとに新記録を作る。
- 安全な実行条件を満たさない操作は送らず、その条件の回復を自動で進める。回復不能が具体的に確定した場合は、試行・残作業・不能理由を正確に報告する。単なる不一致を理由に許可待ちへ戻らない。

## 専用fixtureとnative手順

rootは`ResoLoop_Test_EmissionEditor_Drivegate_<token>`、独自ownership。private ValueField<int/bool/colorX>とObjectRootを用い、Material/Renderer/AvatarRootは含めない。probe/color-helper/bool-helperは別の安定親、portは自分のfixtureの`$member`だけへ結ぶ。world/Flux stateは試行専用にする。

BeforeColor=[0,0,0,1]、BeforeBool=false、ColorTarget=[4.25,.5,1.125,.3125]、BoolTarget=true。profileは名前から推測せずnative完全値を観測する。capture未実施やbool復元漏れを検出できる初期値にする。

Probeはhost-only FireOnValueChange<int>1入口、毎frame処理なし、Command0=no-op。
1. BeforeColor/BeforeBoolを一度だけcapture、Captured=true/Done=1。
2. mutable ColorTarget/BoolTargetへA（HDR/Linear/非1alpha、true）。OnWritten=1/OnFail=2を別々に記録し、完全readback後Done=2。
3. color/bool helperがA/trueをDriveした状態でB（別完全色/sRGB、false）。両OnFail=2、実対象/readbackはA/true。
4. 所有/subtreeを確認してcolor helperだけを除去、不在を確認。B/false候補でcolor=OnWritten、bool=OnFail、B/true。
5. 同様にbool helperだけを除去。C（別HDR/Linear/非1alpha、false）で両OnWritten、C/false。
6. native Beforeを復元し、完全5成分/boolを確認する。

現在値がBeforeと異なる時点で、別のnative再capture要求が拒否されBeforeが保持されることも実測する。6phaseだけで代用しない。各不一致は自動回復/再試行の記録へ送り、Root全値一致を追加の完了条件にしない。

## package・SDK・preflight

`prepare_package`は新規出力先だけへfixture・3PGコピー・3manifestを作り、同期check/build/manifest検証後に入力/record/logをSHA inventoryで封印する。全経路のsidecarを隔離し、原PGや封印物の隣へ再buildしない。実行用copyと別々のstateを使い、code commit/CLI/SDK/211等のDLL実inventoryを結ぶ。失敗した出力先を上書きせず新しい試行を自動準備する。

v3の`normalizedFixture`はinstalled ResoLoop0.2.0の自動markerを入力宣言とは別に表す。key=`drivegate-root/component:FrooxEngine.AI_GeneratedContent:0`、plan型=`FrooxEngine.AI_GeneratedContent`、state/native型=`[FrooxEngine]FrooxEngine.AI_GeneratedContent`、Source=`[resoloop 0.2.0]`。入力へ重複追加せず、markerをwriterのValueFieldへ混ぜない。CLI変更や未知componentは調査・モデル更新・新封印・再試行で扱い、無条件に無視しない。

native SDKの全layoutとruntime graphを区別する。従来の`assess_owned_graph`が`_sdk_graph`のruntime-only出力へ全native componentを渡す経路は旧オフライン検査用として区別し、現在のnative controllerへ転用しない。新しい`assess_native_owned_graph`/`NativeDeployedStage`は全layoutを検証してからruntime subsetへ接続する。BSONの3D専用`Meta: Comments`/`Meta: Packing`や`persistant-ID`をnative member identityへ誤写像しない。新経路の実装と独立レビューはTask2b-bで行い、実機成功は別に実測する。

Task2bのlayout照合入力は、3D用BSONから手作業で推測せず、同じinstalled SDKの`Build.moduleCompiler`と`Link.batchAddProtoGraphNodes`でオフライン生成する全AddSlot/AddComponent操作を基準とする。`Link.initialize`・`linkInterface`・Query・Loaderは呼ばず、接続先の引数も設けない。封印したPGの隔離コピー、exporterソース、SDK/native DLL全inventory、実終了コード・原出力・生成物を試行ごとに結ぶ。既存packageやPGの隣に生成物を作らない。生成した操作のprivate portは外部実IDでなく記号で表し、適用しない。未知の操作、外部参照、欠落・改変した資料を成功にしない。

このオフライン入力の成功はlayout比較・native default/alias解決・実機成功ではない。BSONとnativeでnode位置・slot名・metadataの差が実際にあるため、3D情報の丸写しは採用しない。

Task2b-bの比較モデルは、exact native DLLのGetSyncMember/NameOverride/generic型、ComponentBase/WorkerInitializerの初期化、Slot.Initialize、SyncField/Coder.Default、ProxyとSyncRefListのconstructorを根拠にする。比較モデルを6つの関連DLLのhashへ結び、異なるDLLでは古いdefault表を流用しない。これは導入版の固定ではなく、更新時にsource調査とモデル更新へ自動的に進めるための拒否条件である。Field_TypeはSystem.Typeのfieldでvalueがencoded型文字列、Field_stringのnullはnullのままというCLI/nativeの変換を扱う。

実IDはHost内のaliasであり永続RefIDではない。slotを親・完全Name・PG source-span Tag、componentを所有slot・型・VariableName、member/list elementを所有と名前/位置から対応付ける。実同期要素のIDと対応表を一対一に検証し、未送信memberのIDも重複を拒否する。同名兄弟は順番だけで割り当てず、曖昧なら未知としてsource調査へ進める。全slot/component/memberと全reference target/type、完全slot metadata/defaultに一致してから、検証済みdefaultだけを除いたruntime graphをBSON意味検査へ渡す。passive metadataは全構造で検証するため、無条件に無視しない。

pure比較の入力資料自体は呼出側が認証し、native段階では元layout/BSON receiptと同じpackage/current DLL/所有state/private fieldを`assess_native_owned_graph`で結ぶ。現在のRoot診断化・自動回復/retry controllerは別の未完了作業であり、新照合器だけで全Task2bや実機成功にしない。

preflightは現在の前面化/URL/他編集停止の適用性、discover、別doctor、native session/対象所有、明示した保護対象、private色/型/実参照、panel/fixture詳細diffと新root不在、sealed inputs/SDK全結線を確認する。今回の引き継ぎ開始時、利用者はport16070と「現在は背面、必要なら前面化を依頼する」を明示した。前面化についてはこの最新の申告を優先し、実機操作に必要な時点で依頼する。他編集停止の既存申告は、反する事実がないのに未回答へ戻さない。Root全体の完全一致は要求しない。新たな値変化やcontext変更は自動再採取/再planで扱う。

現在の保全基準は元機能仕様と意味・型・実参照を照合し、指定Claudeに独立レビューさせて実行前に記録する。担当が保護範囲を見直した理由も同じbriefへ渡し、利用者への再確認をgateにしない。旧G0/固定件数の復元、観測の丸写しだけによる適合判定、旧state採用や保存パネルへの宣言適用はしない。

## レビュー・工程・公開

唯一のレビュアーは`claude-code_opus_default`、fallback/自己レビュー代替なし。run単位でRead/Grep/Globだけ、空strict MCP/deny、skills/commands無効、個人設定無変更。実init/tools/tool-useを確認し、計時はrunnerへ任せる。制限逸脱や失敗したrunは不採用にし、制限修正・再確認を自動で行う。旧「別途再開許可待ち」は作らない。OS sandbox保証とは呼ばない。

短いgateはS4全体/C9/C30/C23/C31の合格ではない。native成功・結果レビュー・復元/cleanup後にS4残り→S5→S6b→S6→S7へ進む。実UI・二人・保存再読込を模擬成功にしない。利用者への保護範囲の承認要求と、物理的に必要な二人目の参加等を区別する。

raw/実session/state/brson/個人絶対パスはlocal-only。コード/必要な同テーマ文書へ集約し、未検証の成功としてpush/PRしない。Issue部分進捗はRefs #3/open維持、手動merge、force/auto-merge/Actions有効化なし。公開前の秘密情報検査等は維持する。

## 実行済みの事実と今回の変更境界

詳しい従来記録は本ファイルとPlanの`edb7de5332107d69a081798eb78b007082cd62a3`以前のGit履歴、下記の保存済み原証拠へ残す。そこでの停止・確認待ちは当時の判断の説明であり、現在の作業指示ではない。

| 段階 | 実行済みの事実 |
| --- | --- |
| Task1/2 | `c46cef7`まで、104passed、実SDK3graph、指定Claudeレビュー。native成功ではない。 |
| installed正規化 | `74c0eab`、106passed、v3 marker期待、前後SHA/MVID付きcurrent IL。旧17期待/18actual停止は不変。 |
| Root carrier | `505fb7b`、108passed/compile/diff、835leafの未対応を保全専用で修正。旧02:21のinconclusiveは不変。 |
| reviewer範囲逸脱 | 固定/tmp計時fileの作成/削除を自己申告、当時停止。既存内容/上書き/漏洩は不明。同じClaudeのtool制限で解消済み。 |
| 制限付き再確認/新package | 42.784秒/exit0/stopped、実tools=Glob/Grep/Read、使用Read7/Grep1、MCPなし。新505packageは43files/211DLL/3実SDKparse、stateなし。 |
| Task2b-a offline入力 | `b0383cd..49db2fa`。115passed/compile/diff、実installed SDK全3moduleの操作生成（bool19/color31/probe219）。F1の`..`越境とF2のbuild環境/response-file影響を再現して修正し、指定Claudeの限定再確認で解決、追加regressionなし。接続/書込0、全layout/default/alias比較とcontroller自動回復は未完了。 |
| Task2b-b native全構造照合 | `417fe08..9d803c1`。120passed/compile/diff、35closed type/6DLLの独立model、全layout/default/member alias/runtime subsetとreceipt/所有結合。指定Claudeのsource429.036秒/実装237.491秒/採用F1限定22.674秒で解決。3SDK入力のoffline materialization合格であり、実機観測や新HEAD packageではない。Root/retry controllerは未完了、接続/書込0。 |
| 03:21の旧Root試行 | 6読取/全CLIexit0、Root各8953Slot/17977Component、診断1415slot metadata/2792typed member差分。旧全値一致gateでfailed、03:21:09.468067UTCに停止。after session未採取、world write0。 |
| 旧停止の結果レビュー | 113.439秒/exit0/stopped、実tools=Glob/Grep/Read、当時条件で停止ACCURATE。現在はRoot一致blockingと再試行禁止を本Issueの新方針で解除する。 |

旧Rootの原因がanimation/他利用者/編集とは断定しない。埋込panel/synthetic一致は専用読取やbaseline承認の代わりにしない。過去のdriver hash不足を遡及補完しない。診断件数はcomponent非member属性を網羅する採否基準ではない。

保存先はPARENT_ROOTの`tmp/agents/emission-native-live.enko3n41`、`emission-native-next.gk7mchty`、`emission-native-finish.nkermyxf`と既存ledger。旧原review/raw/seal/停止裁定は改変しない。今回の文書改訂そのものはgate実装の修正・native再試行の実行・Issue完了を意味しない。
