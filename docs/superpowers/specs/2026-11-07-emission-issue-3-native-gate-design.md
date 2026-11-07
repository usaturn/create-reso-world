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

入力はnative colorXの完全RGBA/profile（HDR、alpha非1、Linear/sRGB）、bool、非ASCIIを含むraw JSON。値比較でboolと整数、欠落とnull、型違いを同一視しない。模擬値のprofile変更で元のdictまで変える共有参照を作らない。

防御対象: 他のパネル/実アバター/既存syntheticを試験write/deleteの対象にしない、古いsession/stateを使わない、生成物や利用者ファイルの上書き、失敗を成功とすること、完全色値の損失、Drive下のOnWrittenをOnFailの成功と誤認すること、未検証/改変したpackageからの実行。
対象外: 他利用者との不可分な排他、悪意ある管理者による全rawの整合的な書換えの認証、現在のパネルの修復、駆動の解除による既存対象への強制write。complete/executionPermissionと、個別の試験の判定・実行許可を分ける。

## 専用fixtureとnative手順
生成するrootはResoLoop_Test_EmissionEditor_Drivegate_<token>、独自ownership。許可するComponentはprivate ValueField<int/bool/colorX>と通常のObjectRootのみ。Material/Renderer/AvatarRootは含めない。probe/color-helper/bool-helperは別々の安定親を使う。ポートは$memberの自分のfixtureだけに結ぶ。world/各Flux stateは新しい試行ディレクトリだけに置く。

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

## 記録・公開
採取/実session/絶対の個人パス/state/brsonはlocal-only。コードrepoへはPG/生成処理/安全判定とSテスト、READMEだけを追跡する。文書はこのSpec/Planと既存レビュー記録を1つの文書PRへまとめる。新しい小タスク別PRやPR後の自動レビューループを作らない。部分PRはRefs #3、Issueはopen維持。通常ツールのマージは手動限定。
