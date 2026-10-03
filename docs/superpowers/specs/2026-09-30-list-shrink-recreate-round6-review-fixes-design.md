# PR #5: list-shrink recreate の checkpoint index 修正（round 6）

- 状態: **2026-09-30 承認済み・実装済み**（Claude Code セッションで SDD 実行。反映結果は §9）
- 作成日: 2026-09-30
- brainstorming 経路: **bounded**。既存の index 保存・照合処理と回帰テストに限定する。review-fix-planning の指定により bounded でも Spec を保存する。
- 対象 PR: https://github.com/usaturn/resoloop/pull/5 （OPEN）
- 対象 branch: `fix/list-shrink-recreate`
- PR_REPO: `usaturn/resoloop`
- TOPLEVEL: `/workspaces/reso-world`
- MAIN_ROOT: `/workspaces/reso-world/external/resoloop`
- 検証 HEAD: `485e508e8c651fc701f0a36c4889feeeb86a8228`
- fork remote: origin=`usaturn/resoloop`、upstream=`orange3134/resoloop` を確認済み。

## 1. 目的・範囲・進行状況

レビューで挙がった指摘を現行コミットで検証し、既存の再開処理が保存する index の不整合だけを修正対象とする。実装の成功条件は、対象の中断系列が正しい Component に再束縛され、再適用で収束し、その次の apply が書き込み 0 件になること。

レビュー対象外の問題、他 worktree の変更、既存の未コミット Spec は入力にしていない。以前の判断はレビュー文書内の記述として参照するが、解消の根拠は今回確認したコミット済みコードと実行結果である。

- [x] 指定 PR に対応する唯一のレビューディレクトリを確定し、全6ファイルを読む
- [x] リポジトリ境界と現行 HEAD を確認する
- [x] コミット済みコード・隔離 worktree で検証し、worktree を撤去する
- [x] 全指摘を4区分へ分類する
- [x] brainstorming で bounded と判定し、修正方針を整理する
- [x] Spec を保存し、一覧・件数・根拠を照合する
- [x] ユーザーの明示承認を受ける（2026-09-30、Claude Code セッション）

## 2. 入力と集計単位

入力ディレクトリ: `external/resoloop/reviews/#5-fix-list-shrink-recreate/`

| 接頭辞 | 読んだファイル | 冒頭の対象 HEAD | 文書内のレビュー履歴 |
| --- | --- | --- | --- |
| G | `Grok-4.7.md` | `485e508e8c65` | `485e508` |
| S | `SWE-2-Max.md` | `485e508e8c65` | `d615eeb` → `dc1c651` → `30476c4` → `929c9ae` → `616c510` → `485e508` |
| O | `claude-opus-5-5.md` | `485e508e8c65` | 同上 |
| C | `commandcode-deepseek-deepseek-v4.1-flash.md` | `929c9ae337e6` | `d615eeb` → `dc1c651` → `30476c4` → `929c9ae` |
| D | `deepseek-deepseek-v4.1-flash.md` | `485e508e8c65` | `616c510` → `485e508` |
| Q | `qwen3.8-max.md` | `616c510b6ffe` | `d615eeb` → `dc1c651` → `30476c4` → `929c9ae` → `616c510` |

`U1` などは各ファイルの「Unverified candidates」を掲載順で採番した。過去の Resolved findings も一覧に含める。同じ問題の複数レビューを省略せず、入力上の各項目を1件として数える。Test suggestions は対応する項目の検証案であり、別件には数えない。

| 区分 | ID 付き指摘 | 未検証候補 | 合計 |
| --- | ---: | ---: | ---: |
| 解消済み | 16 | 1 | **17** |
| 対応する | 3 | 3 | **6** |
| 判断保留 | 0 | 0 | **0** |
| 対応しない | 16 | 9 | **25** |
| 全件 | 35 | 13 | **48** |

「対応する」6件は重複をまとめると **2つの修正項目**。すべて採用基準 **(a) 現行 HEAD で再現した誤動作**に該当する。設計変更を必要とする既知の制限や、実機根拠のない仮説は判断保留へ移さない。

## 3. 検証方法と結果

ソース・既存テストは `git show 485e508:<path>` で読み取った。再現は `mktemp -d /tmp/review-fix-planning.XXXXXX` で作った一意な親ディレクトリ内の detached worktree で行い、HEAD の完全 SHA 一致を確認した。プロダクトコードおよび既存テストの差分はゼロ。一時 partial test ファイルだけを追加した。テストの `TMPDIR`、ログ、コミット内容の読み取り用コピーも同じ親配下に限定した。

### 実行結果

| 証拠 | 内容 | 結果 |
| --- | --- | --- |
| E1 | `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ApplyWorkflowTests'`、一時テスト追加前 | **153成功 / 0失敗、exit 0** |
| E2 | `ReviewProbeNewKeyBeforeRecreateReload`、後続 write 失敗・作成直後 cancel・作成応答喪失の3ケース | いずれも新 key の保存 index=0、実位置=1。reload 後は前2件が ownership conflict、応答喪失は ambiguity。いずれも書き込み0 |
| E3 | `ReviewProbeResumedRecreateRestoresWrongSiblingIndex`、最初の停止位置と sibling 数の3ケース | **置換作成後中断 + sibling 1件**では、再開時の cancel が final index 0 を current index 1 に戻し、reload・ヒント復旧後に ownership conflict、書き込み0 |
| E4 | `ReviewProbeEvidenceOnlyAdoptionStillPresent` | create 前中断の後に置いた管理外 Component を採用し、Label/Materials を上書きして旧 Component を削除する挙動が残る |
| E5 | `ReviewProbeInterruptedRelocateTracking`、reload 有無の2ケース | reload なしでは移動元の置換 Component が残存。reload ありでは停止候補が移動先の1件のみで、移動元の2件を含まない |
| E6 | `ReviewProbeIndexOnlyAdoptionAfterManualReorder` | fake の先頭挿入後は管理外 Component を採用し、本来の置換 Component が残存する。実機での先頭挿入可能性は未確認 |
| E7 | `ReviewProbePrunedReferenceStillStops` | prune 対象からの参照でも `APPLY_LIST_SHRINK_REFERENCED`、書き込み0 |
| E8 | `ReviewProbeMissingReplacementLeavesStateOnPrune` | 置換が手動削除済みだと、prune 後に実在しない ID の state key が残る |
| E9 | `ReviewProbeMissingOldStillStopsAfterReload` | 旧 Component が手動削除済みでも reload 後は `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION`、書き込み0 |

一時観測テストの最終コマンドは `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter 'FullyQualifiedName~ReviewProbe'`。**13成功 / 0失敗、exit 0**。これは現行挙動を確認するアサーションの成功であり、修正後の回帰テストが成功したという意味ではない。

E3 の追加探索では、最初が create 前停止の場合、sibling 1件ならヒント復旧後に収束し、2件なら2回目の apply が checkpoint より前の候補照合で `STABLE_COMPONENT_AMBIGUOUS` になる。後者を最初は cancel と予想したため観測テストが1件失敗したが、停止位置を追跡して期待を修正した。**すべての二重中断が同じ障害になるとは主張しない**。修正項目Bの採用根拠は E3 の置換作成後停止ケースである。追加探索の早期停止を新しい修正項目として取り込まない。

Resonite 実機、ソリューション全体、他プロジェクトのテストは未実施。外部 world に対する操作は行っていない。

検証用 `/tmp/review-fix-planning.czjX87/worktree` は `git worktree remove --force` の成功後に親ディレクトリごと削除した（09:59:23 JST に不存在確認）。一時ログ・テストは残していない。再現条件は本 Spec に記録している。

## 4. 全指摘の分類

以下の `W` は現行 HEAD の `src/RLoop.Core/WorldService.cs`、`T` は `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`。行番号は `485e508` 基準。テスト名で示した解消根拠はすべて E1 の対象に含まれる。

### G: Grok

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| G-H1 | recreate 前に作った同型新 key の保存 index が reload 後の所有権衝突を起こす | 対応する | **(a)** E2、W:479,487–490。修正A |

### S: SWE

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| S-L1 | prune 予定参照元も recreate をブロックする | 対応しない | E7で安全側停止を確認。W:1332–1353 は実際に存在する参照を検査する。削除順序を含めた停止条件の緩和は仕様の変更 |
| S-L2 | 中断 recreate の移動・宣言削除で旧 Component が残る | 解消済み | W:553–577,1511–1533、`MovingAComponentWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` と `PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent` が成功。移動自体の再中断はS-L3として区別 |
| S-L3 | 中断 recreate の relocate が再中断すると移動元の置換を追跡できない | 対応しない | E5で残存を確認。W:479–491,553–577の2-ID追跡を、通常relocateにもある削除元追跡へ拡張する設計課題。index修正とは分離 |
| S-L4 | 再開 recreate が先行 sibling の final index を current へ戻す | 対応する | **(a)** E3、W:457,488–490。修正B |
| S-I1 | action一覧・停止コード・復旧手順の文書追記 | 対応しない | `docs/DECLARATIVE.md:57`にrecreateの値リセットは記載済み。残りは情報追加。AGENTS.mdの「Skills are workflows, not command mirrors」を踏まえ、網羅表・エラー手順の重複記載は増やさない |
| S-I2 | fake の list string が `JsonNode.Parse` で例外になる | 対応しない | `ApplyWorkflowTests.cs:1706,1715`に裸文字列のparseは残るが、現行のMaterialsテストは参照/JSON値で153件成功。未使用入力へのfake一般化であり、現行機能の誤動作として採用しない |
| S-I3 | relocate再中断・reload時の候補に移動元が出ない | 対応しない | E5、W:1094–1096,1254。候補は現在stateのSlot内という実装。S-L3と同じ移動元追跡・候補範囲の設計課題 |
| S-M1 | undoで新規参照元に削除済み置換IDが残る | 解消済み | W:449,486,500–503が検証前の参照解決を遅延。`UndoneRecreateLeavesNoReferenceToTheRemovedReplacement`成功 |
| S-M2 | 作成前中断したkeyを移動すると他keyの同型を束縛する | 解消済み | W:1102–1106,1122–1124,1236–1240,1937–1942。heldを照合結果へ適用。`InterruptedCreateOfANewKeyThatMovesIsCreatedOnTheNewSlot`成功 |
| S-U1 | stale ID・手動削除・空ID別keyでrecreate対象を二重主張する懸念 | 対応しない | W:1207–1223,1554–1575。複合条件の端到端再現なし。ownership検査による停止を緩和する根拠なし |
| S-U2 | 空作成して中断した通常ComponentのinitialFieldsが再適用されない | 対応しない | W:474–482,506–511,537。recreate以前からのcreate再開とinitialFieldsの仕様論点。対象経路の再現・回帰根拠なし |
| S-U3 | relocate/prune後の移動元sibling indexがずれる懸念 | 対応しない | W:1119–1136,553–577。通常relocate/prune全体のindex更新設計。対象PRでの誤束縛を端到端で確認していない |
| S-U4 | relocation source照合にrecreatedOnNodeがなく空IDを誤束縛する懸念 | 対応しない | W:1122–1124。heldは適用されるが、管理外候補まで含む端到端再現なし。移動元照合の設計変更を追加しない |
| S-U5 | 新規Componentのcheckpointだけsuperseded保存前もfinal indexになる | 対応する | **(a)** E2、G-H1/O-L10と同一。修正A |
| S-U6 | 実機GetComponentAsyncが作成直後に完全なmemberを返すか不明 | 対応しない | W:512–513の即時観測が前提。実機で不足を確認しておらず、adapter推測修正は行わない |

### O: Claude Opus

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| O-M1 | recreateでinitialFields/未宣言memberが初期値に戻る説明の矛盾 | 解消済み | `docs/DECLARATIVE.md:57`、`README-DETAILS.md:181`、build skill手順6がrecreate時の例外を明記。値を引き継がない挙動自体は維持 |
| O-L1 | undo後にsibling indexが不整合になる | 解消済み | W:1297–1308の`UndoRecreateState`、`UndoneRecreateKeepsSiblingIndexesSoAWorldReloadStillBindsThem`成功 |
| O-L2 | recreate中断後にkeyを外してpruneすると旧Componentが残る | 解消済み | W:1511–1533,592–605、`PruningAKeyWhoseRecreateWasInterruptedAlsoRemovesTheReplacedComponent`の2ケース成功 |
| O-L3 | 非同期refillでapplyごとにrecreateを繰り返す懸念 | 対応しない | W:512–513は一度の観測。実機の遅延refill未確認。履歴永続化による停止方針は別設計で、仮定だけでは採用しない |
| O-L4 | create前中断後、同型siblingと所有権衝突する | 解消済み | W:1236–1240,1937–1942のheld判定。`InterruptedRecreateNextToASameTypeSiblingResumes`と`InterruptedCreateOfANewKeyNextToAManagedSameTypeComponentResumes`成功 |
| O-L5 | reload後の復旧ヒントが同型sibling/未作成置換を識別できない | 解消済み | W:1246–1270がfields付き候補とsavedId有無別手順を提示。`InterruptedRecreateNextToSameTypeSiblingsRecoversAfterWorldReloadByFollowingTheHint`成功 |
| O-L6 | 新keyの作成応答喪失で同一セッションの再開が重複作成する | 解消済み | W:1102–1106,1207–1223の候補配置補正。`ResumedCreateOfANewKeyNextToARecreateBindsWhatItCreated`の宣言順2ケース成功。修正Aで再退行させない |
| O-L7 | 同型sibling複数でヒント復旧後のindexがずれる | 解消済み | W:461–464がsuperseded checkpointと一緒にfinal保存。上記復旧テストのsibling2件を含む5ケース成功。再開をさらに中断する別経路はS-L4 |
| O-L8 | superseded保存前の停止で既存siblingだけfinal indexになる | 解消済み | W:487–490。`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload`の3ケース成功。新規keyはO-L10として区別 |
| O-L9 | 保存IDがない通常createの一致候補を長いlistのため削除する | 解消済み | W:1108–1111,1274–1283。`InterruptedCreateOfANewKeyDoesNotRecreateAnUnmanagedComponentWithALongerList`の同一/別session2ケース成功 |
| O-L10 | recreate前に作った同型新keyのindexが現配置を指さない | 対応する | **(a)** E2の3経路で再現。修正A |
| O-I1 | recreate/停止コードの文書、deletes-only表示の不足 | 対応しない | 文書追記はS-I1と同じ。`deletes-only`を置換処理まで含めるかは既存relocateにも共通する表示仕様で、今回変更しない |
| O-U1 | fields未適用の置換をresumeするとrefill検証をすり抜ける懸念 | 対応しない | W:506–513,537。fields設定に応じた実機refill未確認。fakeの仮定を増やして実機の誤動作と断定しない |
| O-U2 | 既にsuperseded保存済みでも再中断でsibling indexがcurrentへ戻る | 対応する | **(a)** E3の置換作成後中断ケースでS-L4と同じ不整合を確認。before-add全構成で再現するという主張はしない。修正B |

### C: commandcode / DeepSeek（旧世代レビュー）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| C-H1 | held候補の除外でindexがずれ管理外Componentを採用する | 解消済み | W:1937–1942は候補配列を縮めず結果にheldを適用。`ResumedRecreateBindsItsReplacementNextToAnUnmanagedSameTypeComponent`と`ResumedCreateOfANewKeyBindsWhatItCreatedNextToAnUnmanagedSameTypeComponent`成功 |
| C-H2 | 位置で採用した管理外Componentをrefillのundoが削除する | 解消済み | W:516–521が保存ID一致のない置換を削除せず保持。`UndoneRecreateKeepsAReplacementMatchedWithoutItsSavedId`と`ResumedRecreateKeepsARefilledReplacementWhoseCreateResponseWasLost`成功 |
| C-L1 | 旧Componentが既にない場合でもreload後停止する | 対応しない | E9、W:1092–1097,1511–1513。session-scoped IDから削除済みと推定せず停止する安全方針。候補list長だけで自動復旧を許可しない |
| C-I1 | recreate/action/停止コードの説明不足 | 対応しない | S-I1と同じ。リセットの例外記載は存在し、残る網羅説明は情報追加 |
| C-I2 | plan warningsへsnapshot外参照の注意がない | 対応しない | W:1359–1371の停止時suggestionsとPR本文が観測範囲制限を明示。成功planにも警告を追加するのはUX改善で、誤動作の修正ではない |
| C-I3 | 置換が存在しないpruneでstate keyが残る | 対応しない | E8、W:598–600,1528–1531。実在対象がないkeyを残す通常pruneと同じ方針。stateの自動削除条件を広げない |
| C-U1 | 同一Slotのrelocate+recreateで追加順とindexがずれる懸念 | 対応しない | W:1285–1291の追加順と作成ループはplan順。誤動作の再現根拠なし。将来の組合せテストのみを追加しない |
| C-U2 | 移動元siblingのindexを削除後に再計算しない | 対応しない | S-U3/Q-I2と同じ通常relocate全体の設計論点。reload後誤束縛の実行根拠なし |
| C-U3 | 通常createも管理外候補を採用し、null IDでheldが効かない懸念 | 対応しない | W:1236–1240,1918–1942。候補採用方針はD-H1と共通。公式writerはIDを空文字以上で保存し、欠落/null stateの実入力経路は未確認。任意stateの防御を加えない |

### D: DeepSeek（現行世代レビュー）

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| D-H1 | create未実行のresumeが管理外の短いlist候補を採用する | 対応しない | E4で残存確認。W:1918–2005は保存ID以外にtype/member/index等の証拠による採用を許す。応答喪失時の正当な再開との区別には証拠・停止方針の変更が必要で、入力にも据え置き判断が記録された仕様論点。安全と断定しない |
| D-M1 | 中断後の手動並び替えで管理外を採用し本来の置換が孤立する | 対応しない | E6でfake上は再現。実機の並び替え条件未確認で、任意編集後の位置一致採用の是非はD-H1と同じ設計課題。`identityFields`推奨（DECLARATIVE:57/build skill手順6）は維持 |
| D-U1 | 連続中断によりcurrent/final indexが混在する懸念 | 対応する | **(a)** E3の「置換作成後に失敗→sibling checkpoint後cancel→reload」が具体的再現。採用はS-L4に一致する範囲だけ。すべての連続create失敗へ一般化しない。修正B |

### Q: Qwen

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Q-M1 | 中断recreateの移動で新旧どちらかが残る | 解消済み | S-L2と同じW:553–577、移動・reload時停止テストが成功。relocate自体の再中断はS-L3に分離 |
| Q-M2 | resume時にrefill検証自体を飛ばして旧を削除する | 解消済み | W:500–513と`VerifiesRecreate`がresumeも対象にする。`ResumedRecreateThatTheRuntimeRefilledStopsAndKeepsTheOriginal`成功 |
| Q-L1 | 空fields置換のresumeでfields設定前のrefill検証が空回りする | 対応しない | O-U1と同じ。実機のfields起因refillが未確認。設計の変更や追加fake仕様だけでは採用しない |
| Q-I1 | action/停止コードの文書不足（原レビューでは解消扱い） | 対応しない | 値リセットの説明矛盾はO-M1で解消確認したが、停止コード一覧などの不足自体は残る。原レビューのResolved表示を理由に全体を解消済みにせず、情報追加として見送る |
| Q-I2 | relocate元のsibling indexが削除前の値で残る | 対応しない | W:553–577,1113–1136,1285–1291。通常relocateを含む既存設計で、対象の端到端誤束縛は未検証。移動全体の修正を混ぜない |
| Q-U1 | ループ前のfinal一括保存がsuperseded未保存の停止窓を作る | 解消済み | `616c510`のループ前一括保存は`485e508`で廃止。W:461–490と`ApplyStoppedBeforeARecreateIsSavedConvergesAfterWorldReload`の3ケース成功。新key/再開時の残存は修正A/Bで別管理 |

## 5. 修正方針

### A. 新しい同型keyも、その時点のcheckpointが表す配置で保存する

対応ID: **G-H1 / O-L10 / S-U5**、基準 **(a)**。

再現手順:

1. `ApplyFourMaterialsAsync`でRubble上に4要素のrendererを作る。identityFieldsは指定しない。
2. `leadingComponents`へ同型の新key `extra`（Label=east、Materials 1要素）を置き、rendererを3要素へ縮める。
3. 以下のいずれかでrendererのsuperseded checkpointより前に止める。
   - extraの後に`Test.Material`のmarkerを置き、`FailOnWrite=2`。
   - markerなし、`CancelAfterWrites=1`とCancellationTokenでextra作成直後停止。
   - markerなし、`LoseNextComponentCreateResponse=true`。
4. 現行では実配置`[old renderer, extra]`に対しextraの保存index=0。`ReloadWorld`後、前2件は`APPLY_COMPONENT_OWNERSHIP_CONFLICT`、応答喪失は`STABLE_COMPONENT_AMBIGUOUS`になる。

方針:

- **現在の配置のindex**と**作り直し完了後のindex**を混同しない。planが持つ最終indexを、全checkpointへ無条件に流用しない。
- 対象SlotでsupersededIdがまだ一度も保存されていない間、新しいComponentの作成前・作成後checkpointには現在の追加位置を保存する。位置はSlotのsnapshotと、同じSlotでこのapplyが先に作成したComponentを数える。型別ordinalではなくSlot全体のindexを使う。
- 最初のsupersededIdを保存する同じcheckpointで、既存Componentだけでなく、このapplyで作成済みのkeyも最終配置のindexへ更新する。以後に作るkeyは最終配置を基準とする。
- **照合側も同じ基準に揃える。** 現在の`RecreatedOnNode`はsuperseded未保存の「これから縮小するComponent」まで除外する。保存をcurrentへ直すだけでは、応答喪失後の同一セッション再開で候補配列との基準がずれる。対象Slotの永続checkpointにsupersededIdが既にあるかに応じ、空ID keyの候補配列をcurrent/finalへ揃える。
- 上記の配置フェーズ判定は保存側・照合側で共通化するか、同じ条件から導く。runtime内の補助値は許容するが、永続state schemaや外部APIは増やさない。

検証:

- 上記3中断系列で、停止直後のextra indexが現配置/追加予定位置を表すことを確認する。
- reload後にextraを自分のComponentへ束縛し、rendererの縮小が収束すること、余分なComponentを作らないこと、その次のapplyが0 writesになること。
- reloadしない作成応答喪失の再開も成功させる。同型siblingを加えて単一候補の早期returnに依存しないケースを含める。
- extraをrecreateの前/後に宣言する既存テストを維持する。
- extraの後にrecreateが開始して中断した場合、extraのindexも同じsuperseded checkpointでfinalへ切り替わっていることを確認する。

### B. 既にsupersededIdを保存したSlotではcurrentへ戻さない

対応ID: **S-L4 / O-U2 / D-U1**、基準 **(a)**。

再現手順:

1. 4要素のrendererを作成し、別applyで同型sibling（Label=south、4要素）を追加する。宣言はsiblingが先、実配置はrendererが先になる。
2. rendererを3要素へ縮め、`FailOnWrite=2`で置換作成後・旧削除前に中断する。stateは`renderer{id:N,supersededId:O}`、sibling index=0。
3. 同一セッションの再開で、`ApplyOptions.Progress`が`Stage=="components" && Path.EndsWith("/@sibling")`を報告した時にキャンセルする。
4. 現行はsibling indexを1に戻して保存する。
5. reload後は既存のcross-session停止になる。ヒントに従いLabel=northのうち長いリストを持つ旧Componentだけを削除し、rendererの`supersededId`だけをstateから除く。
6. 配置`[sibling,N]`でsibling index=1のため、次のapplyが`APPLY_COMPONENT_OWNERSHIP_CONFLICT`、0 writesで止まる。

方針:

- apply開始時点で対象Slotに中断recreateの永続supersededIdがあるなら、そのSlotはすでにfinal配置を基準とするフェーズである。
- `recreatingNodes`相当の「最初のsuperseded保存を待つSlot」に、そのSlotを再登録しない。先行siblingのcheckpointでもfinal indexを維持する。
- Aのフェーズ判定と統一し、`Superseded != null`だけで毎回フェーズを初期化しない。
- cross-session時の自動停止と候補・手動復旧ヒント自体は変えない。

検証:

- 上記の二重中断でsiblingのindexが0のまま保たれること。
- reload直後は従来どおり`APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION`、0 writesであること。
- ヒントどおりの復旧後はsiblingの所有を保ってrendererが収束し、さらにapplyすると0 writesになること。
- 既存の初回中断・superseded未保存の3ケースと、sibling 1/2件を含む既存ヒント復旧5ケースを維持すること。
- E3の「before-add + sibling 1件」のように元から収束する構成も壊さない。別条件で候補照合が先に止まるものを、この修正で自動採用へ変えない。

## 6. 対象ファイル・非対象・互換性

実装予定ファイル（forkルート基準）:

- `src/RLoop.Core/WorldService.cs`: checkpoint indexと空ID照合の配置フェーズを一致させる。
- `tests/RLoop.Tests/ApplyWorkflowTests.ListShrink.cs`: A/Bの回帰テストを追加する。既存fakeのキャンセル・失敗・応答喪失フックを利用する。

変更しないもの:

- 永続state schema、公開CLI/API、新しいエラーコード。
- 位置・member等の証拠だけによる採用を全面禁止する方針変更（D-H1/D-M1/C-U3）。**管理外Componentが書き換わる制限は残る**。
- relocateの削除元IDの追加保存、移動元index、複数Slot候補への復旧拡張（S-L3/S-I3等）。
- 非同期refill履歴、adapterの推測修正、エラーコード一覧や警告の情報追加。
- 既存の不整合なcheckpointを推測で自動修復するmigration。古いcheckpointはcurrent/finalの意図を一意に識別できない場合があるため、本修正で既存の全破損stateが自動復旧するとは保証しない。

中断点は既存checkpointを保ち、関連するindex更新とsupersededId保存を同じ保存操作に含める。保存済みIDによる同一session照合を優先すること、heldによる他key保護、未保存の長いlist候補を削除しないこと、ownership conflict時に変更前停止することは維持する。

## 7. 承認後の検証・既存PRへの反映

1. A/Bの回帰テストを先に追加し、対象HEADで期待する収束条件が失敗することを確認する。一時観測テストの「不具合を期待するアサーション」をそのまま恒久テストにしない。
2. A/Bを実装し、追加テストと既存の`ApplyWorkflowTests`を実行する。
3. 変更プロジェクトに関連する検証として `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj` を実行する。失敗中はcommitしない。実機接続・無関係なworldテスト・fork全体の一括テストは条件にしない。
4. `git fetch origin`とPR HEAD再確認を行う。今回の根拠SHAから更新があれば関連部分を再確認する。
5. `fix/list-shrink-recreate`へcommitし、`origin`へpushする。main、追加のreview-fixes branch、新しいPRには載せない。
6. 正確な`PI_PROVIDER`/`PI_MODEL`を確認してモデル識別子を決め、TOPLEVEL側の`upsert_pr_comment.py`で既存PR #5へ日本語のレビュー状況・判断・結果を投稿する。他エージェントのコメントは編集しない。

このターンは計画のみ。PRコメントの投稿、commit、pushは行わない。**「進めて」の明示承認まで実装しない。**

## 8. 作業時間

担当: このセッション。2026-09-30 09:48頃（JST）に着手。

- Task 1–2: 入力・規約・PR/remote/HEADの確認 約3分。
- Task 3–4: コミット読解、153件の既存テスト、一時観測13ケース、分類、撤去 約8分。
- Task 5–7: bounded設計、Spec作成・一覧照合・提示 約5分。
- 合計: 約16分。再現コード・既存テストは同期実行し、終了コード確認後に撤去した。

サブエージェントは使用していない。利用可能なツールのschemaに、運用規約が起動前に要求する`action:list`/`capabilities`と`async:false`が無く、安全な起動条件を満たせないため、本体で順に確認した。

## 9. 承認後の実装と追加判断（2026-09-30、Claude Code）

- 実装計画: `docs/superpowers/plans/2026-09-30-list-shrink-recreate-round6-review-fixes.md`（Task 1: 修正A、Task 2: 修正B）。subagent-driven-development で、タスクごとのレビューとブランチ全体の最終レビューを実施した。
- commit: `43c262a`（修正A）、`3824a1f`（修正B）、`0acf969`（最終レビュー I1 の修正）。
- 最終レビュー I1（Important、修正Aによる 485e508 からの後退）: recreate より前に宣言した同型の新 key が、作成の実行前に止まったとする。同型 sibling のある Slot を同じセッションで再開すると、current 配置では index が範囲外になり、`STABLE_COMPONENT_AMBIGUOUS` で停止し続けた。**ユーザー判断で案 (a) を採用した。** 同じセッションでは、曖昧な候補がすべて他 key の保存 ID（held）なら、この key の Component はまだ存在しないとみなして作成する。既存の「単一候補が held なら作成」を複数候補へ広げたもので、管理外 Component は採用しない。held と非 held が混在する場合は従来どおり停止する。これに伴い、§3 E3 の「create 前停止 + sibling 2件」の同一セッション再開と、recreate の無い Slot での同じ停止も、作成して収束するようになる。§5B の「追加探索の早期停止を取り込まない」は、この判断によって上書きした。
- 最終レビュー M1（Minor、既知の制限として残す）: 1 つの Slot で、`supersededId` を保存済みの recreate と、今回新たに縮む recreate が重なるとする。この状態で sibling の checkpoint 時点で止まり、reload 後にヒントどおり復旧すると、2 つある配置の一方で ownership conflict になる。485e508 も、もう一方の配置で同じように失敗する。どちらも安全側の停止で、発生には実行と実行の間に文書を編集する必要がある。対策には、保存用の配置を「永続化済みの `supersededId` だけを除いたもの」に一般化する設計が要るため、別の課題として扱う。
