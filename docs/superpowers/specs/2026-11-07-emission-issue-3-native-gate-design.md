# Issue #3 native Drivegate の再開準備

- 状態: draft
- 対象: usaturn/resonite-emission-editor#3。元ツールの承認・Task4/5/6の意味は維持する。
- 実行許可: 利用者の「必要なことは全て承認します。今後は許可を求める必要はありません」。直前に具体的に示した、不足するDrivegate宣言・manifest・封印資料・照合処理・詳細diff基準の新規準備と、その後の既存Task4/5/6の実装/実機確認を許可する。以前の「オフライン実装不要」によるこの準備の停止を解消する。未作成の内容版の承認SHAは発明せず、内容はdraft、委任による実行許可として記録する。
- コード: /workspaces/create-reso-world/external/emission-editor/.worktrees/issue-3-native-gate、feat/issue-3-native-gate、開始743f1f97dcc3e5224170ffbbfcdcdc430b1997f5。
- 文書: create-reso-worldの本worktree、開始0d58ac76b3c364ec431a292c8bc41e58f57e933b。旧raw補足Planはcompletedのままで再開しない。元のopen Planはコードrepo mainの docs/superpowers/plans/2026-11-03-tools-avatar-emission-editor.md。
- PR4のraw receipt基盤は再実装しない。既存の未公開レビュー記録2d8635dは本ブランチへcherry-pickし、元worktreeは変更せず保持した。

## 目的・判断
元PlanのR101停止後に必要となった、別所有fixtureの短いtyped Drivegateを現在の公開ソースから実行可能にする。旧tmp/worlds/toolsや旧state/session、古い試行の継続・復元はしない。小タスクは進捗単位であり、関連変更は本コードbranch/PR1本、同テーマ文書PR1本に集約する。

選択: private ValueFieldだけの新規fixture、host-onlyのmutable writer、イベントを持たないcolorX/bool Drive helperを別々の親へ置く。既存のnative PG/manifestの方式を使い、元の本体PGや期待値を実機結果に合わせて変えない。
別案: 既存のReadbackProof/CommitProof全体を配備する方式は書き込み対象と分岐が広すぎるため採用しない。旧資料復元は明示禁止のため採用しない。raw基盤全面変更や一般的な任意コマンド実行ツールは不要。

## 受け入れ基準・環境・防御範囲
Python3.14/uv/Linux、標準ライブラリ、ResoLoop0.2.0、実機doctorで確認する現在のDLLとFlux SDK。port/session/実IDをソースへ固定しない。通常の実機利用の単独動作・二人操作・保存再読込をこの短い試験で証明したとはしない。

入力はnative colorXの完全RGBA/profile（HDR、alpha非1、Linear/sRGB）、bool、非ASCIIを含むraw JSON。値比較でboolと整数、未観測memberの欠落と既知null、型違いを同一視しない。CLI0.2.0はpresentなreference MemberValueのnullable targetIdをnull時に省略するので、その完全なkind/id付きreferenceレコードだけは既知nullとして正規化する。member自体の欠落/unknown kind/idや非null要求はこの規則で補わない（現在runの実ObjectWrite/GlobalReference/DriveProxyと同梱Models/Mapper/OutputWriterで根拠を照合）。presentな完全なkind/id/type付きfieldのvalue省略も同serializerの既知nullであり、null文字列と空文字列を区別する。bool/int/colorのnullをfalse/0として埋めない。完全な保護treeにある未解釈の型付きfieldは、型・ID・全JSON値を厳密に保全する用途だけで比較し、private書込対象として解釈・許可しない。既知mapperのempty/SyncPlaybackの観測と未知kind/欠落を区別し、全member/list/mapを残す。模擬値のprofile変更で元のdictまで変える共有参照を作らない。

防御対象: 他のパネル/実アバター/既存syntheticを試験write/deleteの対象にしない、古いsession/stateを使わない、生成物や利用者ファイルの上書き、失敗を成功とすること、完全色値の損失、Drive下のOnWrittenをOnFailの成功と誤認すること、未検証/改変したpackageからの実行。
対象外: 他利用者との不可分な排他、悪意ある管理者による全rawの整合的な書換えの認証、現在のパネルの修復、駆動の解除による既存対象への強制write。complete/executionPermissionと、個別の試験の判定・実行許可を分ける。

## 専用fixtureとnative手順
生成するrootはResoLoop_Test_EmissionEditor_Drivegate_<token>、独自ownership。許可するComponentはprivate ValueField<int/bool/colorX>と通常のObjectRootのみ。Material/Renderer/AvatarRootは含めない。probe/color-helper/bool-helperは別々の安定親を使う。ポートは$memberの自分のfixtureだけに結ぶ。world/各Flux stateは新しい試行ディレクトリだけに置く。

初期Beforeと対象を同じ値にしない。BeforeColorのRGBAは[0,0,0,1]、BeforeBool=false、ColorTargetのRGBAは[4.25,.5,1.125,.3125]、BoolTarget=trueとする。nativeの初期profileは名前から推測せず完全値を観測・検証する。capture未実施やphase5後のbool復元未実施を検出できないbaselineは拒否する。再capture拒否は6phaseの値だけで実施済みとせず、現在値がBeforeと異なる時点の別のnative試行が必要である。

Probeはhost-only FireOnValueChange<int>1入口、毎frame処理なし。Command0はno-op。
1. native BeforeColor/BeforeBoolを一度だけcapture、Captured=true/Done=1。
2. mutable ColorTarget/BoolTargetへA（HDR/Linear/非1alpha、true）を代入。OnWritten=1/OnFail=2を別のColorOutcome/BoolOutcomeへ、完全なColorAfter/BoolAfterをnative readback、最後にDone=2。
3. color-helper/bool-helperがA/trueをDriveした状態でB（異なる完全色/sRGB、false）を代入。期待は両OnFail=2、実対象とreadbackはA/trueのまま。
4. color-helperだけを所有/全subtree再確認後に削除して不在を確認。同じB/false候補でcolor=OnWritten、bool=OnFail、B/true。
5. bool-helperだけを同様に削除して不在確認。C（別HDR/Linear/非1alpha、false）で両OnWritten、C/false。
6. BeforeColor/BeforeBoolをnativeで復元し、完全5成分とboolを確認。capture再実行は拒否しBeforeを書き換えない。
各phaseで試験範囲/実継続/Done/readbackを確認する。CLI exit0だけでnative成功にしない。最初の不一致で停止し、期待値変更や自動修復・再試行をしない。

## package・保全・preflight
prepare_packageは既存でない出力先だけに、fixture宣言・3PGのコピー・親ごとの3manifestを生成する。check/buildはコピーに対して同期実行し、原PGの隣へbrsonを生成しない。テストのfake compilerも実行してこの経路を確認する。packageは全入力/生成SDK record/manifestを列挙したSHA inventoryで封印する。SDK/DLL/CLI版とcode commitも記録する。
sealされた入力/期待recordはdeployの再ビルド先にしない。別の実行コピーと封印物を照合し、生成物の変更・不足・symlink/範囲外・追加未知ファイルを検出したら実行しない。

full preflightは、新しい前面化/URL/排他確認からdiscover→別doctor→native session/所有/全保護値/controls/完全色の別プロセス再採取→panel/fixtureの詳細diffと試験root不在→封印資料と全module/writer/Drive/global/binding/継続edge/subtreeを照合する。
現在の実機を読み取って用意する保全基準は、現在の意味/型/実参照を元Specと照合して別にレビューし、実機へwriteする前に封印する。観測を単にexpectedへコピーして仕様適合にしない。既存の旧G0や469という値を復元・固定して代用しない。保存パネルへの宣言適用・state採用はこの短いgateでは行わない。

この短いgateはS4全体/C9/C30/C23/C31の合格ではない。成功・結果レビュー・片付け後にだけ新しいS4全条件の準備へ進み、S4前にS5、S5前にS6bへ進まない。

## 2026-11-07 実装・停止記録

Task1/2のコードはc46cef703f14c73f15a38a6ccac48a6a7b58ce52まで。PR4のraw collectorと既存本体PGは無変更。全104passed、実SDK3PGのcheck/build/manifest検証と新package43ファイル/211DLLの照合、独立に作成した完全typed BoolDriveと実SDK/所有graphの結合比較を実行した。これはoffline比較でありnative成功ではない。唯一のclaude-code_opus_defaultによるTask1/Task2レビューと採用指摘修正の限定再レビューはPASS。capture/restoreが見えない初期値、封印先への再build、cleanな出所の不足、未使用の弱いdiff APIと重複テストは修正済み。

SDKの正確なpersistant-IDはBSON共通メタデータであり、native persistent memberのIDやengineの名前aliasではない。現在のSDKはNodeComponent.FieldsからAddComponentを作り、現在DLLのComponentBase.Initializeがpersistent=trueを設定する。実runtimeの当該memberは存在・型・値・ID重複を確認し、消して合わせない。SDK記録の余分な型を無条件に許す規則はない。

新しい16070のpreflightで、同じ現在session、別doctor、完全panel1025Slot/2011Componentとsynthetic19Slot/21Componentの別プロセス再採取・保持を確認した。現在の211DLL hashは新sealと一致する。元UIのnull Operator参照と残るclaim/使用中表示は保全し、所有・競合なし・操作可能性と読み替えたり手動修復したりしていない。

20:16:36UTC、private fixtureの詳細作成diffが宣言の17createsではなく18createsとなり、未宣言のAI_GeneratedContent.Sourceが1件含まれたため停止した。CLI exit0でも意味の照合はFAILである。installed NuGetのGeneratedContentMetadata.csはgenerated rootへの標準AI由来marker追加を定義し、installed WorldService.csのrecovery文面は実出力と一致する。古い別fork checkoutを期待値の根拠にしていた差は説明できるが、これで封印済み期待値や許可Componentの集合を事後変更しない。metadataを抑止する回避や自動再試行は行わない。

ワールドへの書き込みは0。fixture/state/moduleを作成せず、after session bracketは停止により未採取。独立baselineレビュー、panel詳細diff、完全Root保全条件、full preflight、native全phase/再capture/cleanup、S4以降、元Task4実UIとTask6は未完了。次はinstalled仕様から正規化・所有範囲を明示的に扱う修正を設計・レビューし、新しい封印入力と全fresh preflightを用意する。今回の停止windowを継ぎ足さない。検証の未解消をdraft PRで迂回せず、同じコード/文書branchをローカル保全する。公開未実施。

## 2026-11-08 再開時の正規化補足

利用者は指定handoffからの続行、ResoniteLink 16070、時間制限なしを指示した。従来の180能動分の記録は保持し、今回以降の時間を追記して合算するが、旧上限を停止理由にはしない。実行許可の範囲と安全停止条件は変更しない。接続先の指定は現在のワールドの前面化の明示ではないため、明示を得るまでは接続・読取・撮影・変更を行わずオフライン準備だけを進める。

Task3前提修正は、installed ResoLoop0.2.0のGeneratedContentMetadataとWorldServiceの正規化を、宣言とは別の封印済み期待モデルに記録する。入力fixtureへ自動markerを重複記述せず、CLIによるroot追加を表現する。対象は本fixtureのrootだけ、keyは`drivegate-root/component:FrooxEngine.AI_GeneratedContent:0`、plan型は`FrooxEngine.AI_GeneratedContent`、配備済みstate/native型は`[FrooxEngine]FrooxEngine.AI_GeneratedContent`（WorldService.CreateComponentStateはcreateで得たResolvedTypeを保存する）、Sourceは`[resoloop 0.2.0]`である。別CLI版・marker欠落・Source欠落/型違い/値違い・別親/余分なComponentを受理しない。完全subtree比較による他の全member保全も維持し、このmarkerは書込対象のValueFieldとして扱わない。既存の17件期待と失敗rawは変更しない。

新package形式v3は入力fixtureと正規化済み期待モデルの関係を検証し、後者をsealに含める。precreateの全key照合と配備後の所有/結線検証は同じ期待モデルを使う。未知のmetadataをまとめて無視する規則は追加しない。DLL/SDKの既存IL記録は過去のhash bindingを発明せず、現在ファイルの前後hashと新規のIL採取を結んだ別記録で検証する。これはnative成功やfull preflightを意味しない。

この補足は、既に具体的に委任されたinstalled正規化・封印入力・意味/範囲照合の不足修正に限る。旧本体PG、A/B/C/OnWritten/OnFail、実UIや依存順序、既存対象へのwrite禁止は変えない。内容はdraftのまま、承認SHAは発明しない。唯一の指定Claudeが同じ受け入れ基準で実装差分と前提を確認した後に新sealを作る。

## 記録・公開
採取/実session/絶対の個人パス/state/brsonはlocal-only。コードrepoへはPG/生成処理/安全判定とSテスト、READMEだけを追跡する。文書はこのSpec/Planと既存レビュー記録を1つの文書PRへまとめる。新しい小タスク別PRやPR後の自動レビューループを作らない。部分PRはRefs #3、Issueはopen維持。通常ツールのマージは手動限定。
