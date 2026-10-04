# PR #9 レビュー修正設計（第3回）

- 日付: 2026-10-03
- brainstorming 経路: **architectural**。Component 削除と checkpoint の順序、セッションをまたぐ照合の安全性、エラー context（利用者とエージェントが読む情報）が連動するため。
- 対象: `usaturn/resoloop` の OPEN な PR #9、head `fix/list-shrink-recreate-split`、検証時 HEAD `36d955e8de7f4f9413c2d5209058b177ae307037`（`gh pr view` の `headRefOid` と一致）。fork の `origin` は `usaturn/resoloop`、`upstream` は `orange3134/resoloop`。
- 入力: `external/resoloop/reviews/#9-fix-list-shrink-recreate-split/` の9ファイルすべて。対象 HEAD は `claude-opus-5-5.md`・`gpt-6-sol.md`・`qwen3.8-max.md` が `1aeb26faece1`、`claude-sonnet-5-5.md`・`xai-grok-4.7.md` が `1eab03e7a5d9`、`Grok-4.7.md`・`SWE-2-Max.md`・`commandcode-deepseek-deepseek-v4.1-flash.md`・`opencode-go-muse-spark-1.3-contributor.md` が `36d955e8de7f`。
- 以前の Spec（`2026-10-02-pr9-list-shrink-review-fixes-design.md`、`2026-10-02-pr9-list-shrink-round2-review-fixes-design.md`）は古い HEAD に対する成果物なので変更しない。仕様論点の判断は以前の回と揃える。
- この Spec は計画であり、実装・commit・push は未実施。

## 意図と成功条件

- 目的: 中断した作り直し（recreate）の後にワールドを再読込し、`APPLY_RECREATE_INTERRUPTED`（`reason: session-changed`）の案内どおりに復旧しても、次の apply が古い保存 index で管理外の同型 Component に結び付いて書き込まないようにする。あわせて、list 短縮の対象範囲を説明する文書のうち、残る1か所を実装に合わせる。
- 維持する PR #9 の設計判断: 再読込後に作り直しを自動では再開しない。未確認 index（`componentIndex: -1`）が残る state は、再読込後に変更前で停止する。state の schema は変えない。
- 成功条件: 下記の3つの再現手順を、新しい案内どおりに辿っても管理外 Component の値が変わらないこと（収束するか、書き込み0回で停止する）。関連する既存テストが、新しい案内に沿って収束すること。
- ユーザの選択（2026-10-03）: 修正方針 A（削除直前だけ未確認化し、手作業の復旧手順を案内で補う）。

## 全指摘の選別

24件（レビューの見出しをファイル名＋IDで識別する。各レビューの Resolved findings 節に載った指摘も数え、重複も別件として計上する）: **解消済み 12 / 対応する 3 / 判断保留 0 / 対応しない 9**。`Grok-4.7.md` と `opencode-go-muse-spark-1.3-contributor.md` は指摘0件。未検証候補・テスト提案・「検討して指摘にしなかったもの」は指摘として数えない。対応する理由は (a) 現行 HEAD での誤動作の再現、(b) 現行 HEAD で事実と異なる記述。

行番号は特記が無ければ `36d955e` の `src/RLoop.Core/WorldService.cs`。

| 指摘 | 区分 | 現行 HEAD の根拠・判断 |
| --- | --- | --- |
| opus L-1: 再開中の置換をさらに短く宣言すると誤った案内 | 解消済み | `:1210-1214` の plan 理由が「置換が短い宣言より長いので取り消し後に作り直す」を示し、`:2389-2401` が同じ apply の再実行を案内する。`DECLARATIVE.md:196` も一致。 |
| opus I-1: NOT_CONVERGED の recovery と suggestion の矛盾 | 解消済み | `:2412` が専用の `recovery` を context に入れ、`:675-679` の共通 catch は `recovery` がある例外へ汎用の再実行文を足さない。 |
| gpt-6-sol H-1: 保留した list を検証せず旧 Component を削除 | 解消済み | `:2349-2360` が相互参照の list を2段目で書いて読み戻し、旧 Component の削除（`:544-559`）より前に失敗を検出する。 |
| qwen L-1: recreate が `--yes` なしで管理 Component を削除 | 対応しない | relocate と共通の既存設計（第1・2回と同じ判断）。`AGENTS.md` の `--yes` は CLI の明示的な delete/remove の規則。論点は下記「仕様論点」に残す。 |
| qwen L-2: 入れ子 list が対象外であることが文書に無い | 解消済み | `DECLARATIVE.md:193`・`README.md:18`・`README_JA.md:7` が「`fields` 直下の list member」に限り、入れ子は対象外と明記した。残る `README-DETAILS.md` は deepseek L-3 で扱う。 |
| qwen L-3: 参照済みの再開置換を undo で削除 | 解消済み | `:2372-2375` が、参照のある再開置換を取り消し対象から外す（`ReferencesTo(...).Length == 0` と `retainGroup`）。 |
| qwen I-1: 実機確認・fork CI が未実施 | 対応しない | 作業上の未完了事項で、現行 HEAD の誤動作や記述の誤りではない。実機確認を済ませたとは書かない。 |
| sonnet L-1: prune の削除ごとに Slot 再読込と checkpoint | 対応しない | 性能の指摘で、実測の問題は無い。現行 HEAD の削除前の未確認化を含め、各 checkpoint は中断時の安全性に必要。 |
| sonnet I-1: recreate が `--yes` なしで削除し、範囲外の参照を失う | 対応しない | qwen L-1 と同じ仕様論点。snapshot の範囲に限る検査は `DECLARATIVE.md:195` と suggestions に明記済み。 |
| xai M-2: index 保存の失敗後、セッションが変わると兄弟 key が別 Component に結び付く | 解消済み | `36d955e` で prune（`:579`）と移動元（`:528`）の削除前に `MarkSlotIndexesUnverified` を呼び、再読込後は `:1013-1023` で変更前に停止する。`APruneInterruptedBeforeIndexSaveCannotWriteToAnUnmanagedSiblingAfterReload` ほか3件が固定し、隔離 worktree で `ApplyWorkflowTests` 196件が合格。recreate・undo の削除経路に残る同種の穴は SWE L-4 で扱う。 |
| xai M-1（Resolved）: recreate 予定の Component を `test` が存在しないと扱う | 解消済み | `:706-711` が `Existing ?? Superseded` を現在の Component とする。 |
| xai L-1（Resolved）: NOT_CONVERGED の再実行案内の矛盾 | 解消済み | opus I-1 と同じ修正。 |
| SWE L-1: 参照を上書きする宣言・prune 予定の参照元でも停止 | 対応しない | `:1582-1652` の保守的な事前停止。`null` 宣言や prune 予定の参照元を張り替え済みとみなすのは、停止条件を緩める仕様判断（第1・2回と同じ）。 |
| SWE L-4: recreate 完了時の旧 Component 削除と undo の置換削除で、削除前に index を未確認化しない | **対応する (a)** | 隔離 worktree の probe で `:549` と `:2379` の両経路を再現（下記「再現」A・C）。 |
| SWE I-2: `AwaitsVerification` のコメントが条件の拡大に追随していない | 対応しない | `:2626` のコメントは旧 Component が残る場合の説明として誤りではなく、「その場合だけ」とは書いていない。Info 級の追記（第2回と同じ判断）。 |
| SWE L-2（Resolved）: 保存 ID が null のときのガード漏れ | 解消済み | `:1121` が `string.IsNullOrEmpty(stateComponent?.Id)` で null・空の両方を停止する。 |
| SWE L-3（Resolved）: 保留した list の最終書き込みを検証しない | 解消済み | gpt-6-sol H-1 と同じ修正。 |
| SWE I-1（Resolved）: undo の範囲が文書の記述より広い | 解消済み | `DECLARATIVE.md:196` が、前の apply の再開中の置換も安全なら取り消し、参照済みや旧 Component が無いものは残すと、実装どおりに書く。 |
| deepseek L-1: `supersededId`・`componentIndex: -1` を足しても `schemaVersion` が2のまま | 対応しない | 旧ビルドとの互換性の扱いは仕様判断（第1・2回と同じ）。`-1` が加わっても論点は変わらない。 |
| deepseek L-3: `README-DETAILS.md:181` が入れ子 list も recreate 対象のように書く | **対応する (b)** | `README-DETAILS.md:181` は「宣言したlist memberの要素数が実機より少ない既存Componentも…（planの`recreate`）として扱います」と書くが、実装は `fields` 直下の配列だけを対象にし（`:1198-1206`）、他の3文書も入れ子を対象外と明記している。 |
| deepseek L-4: 再読込後に `-1` が残ると apply が止まり続け、復旧手順が示されない | 対応しない | 止まり続けるのは PR が選んだ安全側の停止で、誤動作ではない。prune・移動の停止文面を具体化するのは案内の改善で、(a)〜(d) に当たらない。ただし SWE L-4 の修正で recreate の復旧経路も `-1` に至るため、`session-changed` の案内には `-1` の key の扱いを含める（下記「対応1」）。 |
| deepseek L-5: 復旧の案内が勧める `resoloop component remove` は state の index を直さない | **対応する (a)** | `:1524-1525` の `session-changed` の経路を probe で再現（下記「再現」B）。`:1126`・`:1534` の案内は再現を確認していないため、今回は変えない。 |
| deepseek I-1: 取り消し時に `componentsAdded` と `componentsDeleted` を二重に数える | 対応しない | 件数は実行した操作の数で、純増減とは定義していない（第1・2回と同じ）。 |
| deepseek L-2（Resolved）: 旧 Component が無い再開経路で list を読み戻さない | 解消済み | `AwaitsVerification`（`:2627`）が `SupersededId is not null` を条件にし、`VerifyReplacementsAsync`（`:2320`）が旧 Component の無い再開でも読み戻す。 |

`Grok-4.7.md` と `opencode-go-muse-spark-1.3-contributor.md` は、recreate の旧 Component 削除に未確認化が無い点を検討し、「別セッションでは `ThrowIfRecreateInterruptedAcrossSessions` が止める」として指摘にしなかった。下記の再現 A は、その停止の案内どおりに復旧した後の apply で誤った結び付きが起きることを示しており、この判断と矛盾しない（停止そのものは働いている）。

### 仕様論点（今回は変えない）

- apply の recreate に `--yes` などの明示的なオプトインを要求するか（qwen L-1、sonnet I-1）。
- state の `schemaVersion` を3に上げるか（deepseek L-1）。
- 参照を消す宣言（`null` など）や prune 予定の参照元を、張り替え済みとみなすか（SWE L-1）。
- prune・移動の `-1` 停止の案内を具体化するか（deepseek L-4）。
- `:1126`・`:1534` の案内が勧める手作業の削除が、後続の Component の位置をずらす点（deepseek L-5 の残り。再現は未確認）。

## 再現（現行 HEAD）

`git worktree add --detach` で `36d955e` を `mktemp -d` の一時ディレクトリへ展開し、SHA の一致を確認したうえで `tests/RLoop.Tests` に probe を追加して `dotnet test --filter FullyQualifiedName~ReviewProbe` で実行した。fake client を使う。検証後に worktree を `git worktree remove --force` で外し、一時ディレクトリも削除済み。3件とも、案内どおりの復旧の後の apply は成功を返し、管理外 Component の値を書き換えた。

- **A（SWE L-4、`:549`）**: `Rubble01` に `renderer`（`Test.Renderer`、Materials 3要素）と `v1`（`Test.Indexed`、Value=1）を宣言して apply し、管理外の `Test.Indexed`（Value=999）を末尾に追加する。Materials を2要素に縮めて apply し、旧 Component を削除する書き込みの応答を失わせる（`LoseResponseOnWrite=2`）。checkpoint は `renderer` の `supersededId` を残し、`v1` の `componentIndex` は1のまま（削除後の実際の位置は0）。`ReloadWorld` の後の apply は `session-changed` で停止し、候補は置換先1件。案内どおり `supersededId` を消して再実行すると成功（書き込み1回）し、管理外 Component の Value が 999 から 1 になった。
- **B（deepseek L-5、`:1524-1525`）**: A の構成に `source`（`Test.Source`、`Target: $ref:renderer`）を加える。縮める apply を旧 Component の削除で失敗させる（`FailRemovingComponent`。参照は置換先へ張り替え済み）。`ReloadWorld` の後の apply は `session-changed` で停止し、候補は参照の無い旧 Component と、`source` が参照する置換先。案内どおり旧 Component を削除し、`supersededId` を消して再実行すると成功（書き込み1回）し、管理外 Component の Value が 999 から 1 になった。`v1` の保存 index 2 が、旧 Component の削除で前に詰まった後は管理外 Component の位置を指していた。
- **C（SWE L-4、`:2379`）**: `renderer` だけを宣言して apply し、次に Materials を縮めつつ `k3`（`Test.Indexed`、Value=3）を加えた宣言を apply して、旧 Component の削除で失敗させる（置換先の後に `k3` が作られ、保存 index は2）。管理外の `Test.Indexed`（Value=999）を末尾に追加し、置換先の Materials を3要素にしてから同じセッションで apply する。検証の失敗で置換先が取り消され、その削除の直後にキャンセルする（`CancelAfterWrites=2`）。`k3` の保存 index は2のまま（実際の位置は1）。`ReloadWorld` の後、案内どおり復旧すると成功（書き込み3回）し、管理外 Component の Value が 999 から 3 になった。

## 修正方針の選択

- **採用（A）: 削除の直前だけ未確認化し、手作業の復旧手順を案内で補う。** prune・移動と同じ `MarkSlotIndexesUnverified` を、作り直しの旧 Component の削除と取り消しの削除の直前にも呼ぶ。`session-changed` の案内には、手作業の削除で後続の位置がずれることと、その直し方を加える。変更が小さく、PR #9 の既存の仕組みと一貫する。削除が失敗した中断点（再現 B など、多くの場合）では保存 index が正しいので、「削除した候補より後ろの index を1減らす」という機械的な手順で直せる。
- 不採用（B）: 置換先を作る checkpoint から完了時の index 保存まで、同じ Slot の他の key を `-1` に保つ。どの中断点でも位置での照合を止められるが、再読込後の復旧では毎回 `-1` の停止を挟み、元の位置の情報が失われるため、すべての key を実機で特定し直す必要がある。fields 段の checkpoint も変える必要があり、変更とテストへの影響が大きい。
- 不採用: 案内だけを直し、削除前の未確認化を足さない。再現 A・C では削除済みの Component の位置が state に残らないため、利用者が機械的に index を直す手順を示せない。

## 対応する項目と検証

### 対応1: SWE L-4 と deepseek L-5 — 作り直しの削除と、再読込後の復旧手順

**コード（`src/RLoop.Core/WorldService.cs`）**

1. 作り直しの完了ループ（`:544-559`）で、`component.Superseded is not null` のとき、`RemoveComponentAsync(component.Superseded.Id)` の直前に `MarkSlotIndexesUnverified(prepared, component.Node.StableKey)` を呼ぶ。削除後の `SaveSlotIndexesAsync`（`:553`）と checkpoint（`:556`）で実際の index に戻る流れは変えない。
2. 取り消しのループ（`:2376-2384`）で、`RemoveComponentAsync(component.Id!)` の直前に `MarkSlotIndexesUnverified(prepared, component.Node.StableKey)` を呼ぶ。ループの後の `SaveSlotIndexesAsync`（`:2385-2386`）と checkpoint（`:2387`）は変えない。先に取り消した key の復元済みの記録がこの checkpoint に載るのは、その削除が完了しているので正しい。
3. `MarkSlotIndexesUnverified` が `supersededId` を持つ key を対象外にする挙動（`:2451`）は変えない。再開は ID だけで照合し、同じセッションの `ReconcileUnverifiedIndexesAsync` が未作成の置換先で止まらないようにするため。作り直し中の key 自身の index は、下の案内で利用者が設定する。
4. `RecreateInterrupted`（`:1510-1555`）の context を次のように拡張する。
   - `candidates` の各要素に `position`（Slot の現在の Component の並びでの0始まりの位置。`node.Existing.Components` での位置）を加える。全 reason で共通。
   - `reason` が `session-changed` のとき、`slotKeys`（state で同じ `SlotKey` を持つすべての key と、その `componentIndex`。作り直し中の key 自身を含む）を加える。
5. `session-changed` で同じ Slot に同型の別 key が無い場合の suggestions（`:1524-1525`）を、次の内容にする（英文は実装時に既存の文体へ合わせる）。
   - 1つ目（現状どおり）: 参照されている候補を残し（参照が無ければどちらでもよい）、他方を `resoloop component remove ID --yes` で削除する。ID は `candidates` のものだけを使う。
   - 2つ目（変更）: state をバックアップし、ID が空なら `components.{key}.id` を `supersededId` にし、`supersededId` を消す。続けて3つ目の手順で index を直してから再実行する。
   - 3つ目（追加）: 削除した Component より後ろの Component は1つ前に詰まり、再読込の後は `identityFields` の無い key を保存した `componentIndex` で照合する。`components.{key}.componentIndex` を残した候補の `position` にし、そのうえで `slotKeys` のすべての key（この key を含む）について、`componentIndex` が削除した候補の `position` より大きければ1減らす。`componentIndex` が `-1` の key は位置の手掛かりが無いので、Slot 上のその key の Component を `resoloop component inspect` で確かめ、その位置を設定する。どれか確かめられない場合は state をそのまま残し、推測しない。
   - 同じ Slot に同型の別 key がある場合の suggestions（`:1523`）は、手作業の削除を勧めていないので変えない。
6. `-1` の停止（`:1013-1023`）、`:1126`・`:1534` の案内は変えない（「仕様論点」を参照）。

**文書（`docs/DECLARATIVE.md`）**

- `:189` の「Componentのpruneまたは移動で削除を始める前に、同じSlotの保存indexを未確認値（`componentIndex: -1`）としてcheckpointします」を、作り直しの旧 Component の削除と、`APPLY_LIST_SHRINK_NOT_CONVERGED` の取り消しの削除も含む記述にする。
- `:197` の `session-changed` の説明に、手作業で候補を削除すると後ろの Component の位置がずれるため、エラーの `candidates` の `position` と `slotKeys` を使って state の `componentIndex` を直してから再実行する旨を1文で加える。手順の詳細は suggestions に任せる。
- README・README_JA・スキルは「エラーの suggestions に従う」とだけ書いており、変更しない。

**検証（`tests/RLoop.Tests`）**

- 回帰テスト（再現 A）: 管理外の同型 `Test.Indexed` を末尾に置いた Slot で、作り直しの旧 Component を削除する書き込みの応答を失わせる。checkpoint で兄弟の key が `componentIndex: -1` になることを固定する。同じセッションの再実行は収束する（`ReconcileUnverifiedIndexesAsync` による修復）。別の構成で、`ReloadWorld` の後に新しい suggestions どおり復旧したとき、`-1` の key を設定しなければ `STABLE_COMPONENT_AMBIGUOUS` で書き込み0回のまま止まり、正しい位置を設定すれば収束し、どちらでも管理外 Component の Value が 999 のままであることを固定する。
- 回帰テスト（再現 C）: 取り消しで置換先を削除した直後にキャンセルし、兄弟の key が `-1` になることと、`ReloadWorld` の後に新しい suggestions どおり復旧しても管理外 Component に書き込まないことを固定する。
- 回帰テスト（再現 B）: 旧 Component の削除で失敗させてから `ReloadWorld` し、`session-changed` の context に `candidates[].position` と `slotKeys` があることを確かめる。suggestions の手順（候補の削除、`supersededId` の削除、`componentIndex` の設定と1減らす手順）をテストで文字どおりに実行し、次の apply が収束して、管理外 Component の Value が 999 のままであることを固定する。
- 既存の `AWorldReloadDuringARecreateStopsBeforeAnyWrite` は、`one-recreate` の復旧を新しい suggestions どおりに更新する（index の調整と、`-1` の key をテストが把握している実際の位置に設定する手順）。加えて、同じ Slot に管理外の同型 Component を置くシナリオを足し、全書き込み位置で、復旧後の apply が収束するか書き込み0回で停止し、どちらでも管理外 Component を変えないことを固定する。
- 既存の `ARecreateInterruptedAtAnyWriteConvergesInTheSameSession`、`AnUndoInterruptedAtEitherRemovalResumesOnTheNextApply`、`ApplyWorkflowTests.SlotIndexes.cs` の各テストが、未確認化を足した後も通ることを確かめる。
- 修正の効き目の確認: 追加した `MarkSlotIndexesUnverified` の呼び出しを1つずつ外すと再現 A・C のテストが、suggestions を元に戻すと再現 B のテストが、それぞれ失敗することを実装時に一度確かめる（確認後は元に戻す）。

### 対応2: deepseek L-3 — `README-DETAILS.md` の対象範囲

- `README-DETAILS.md:181` の「宣言したlist memberの要素数が実機より少ない既存Componentも」を、`docs/DECLARATIVE.md:193` と同じく「`fields`直下に宣言したlist memberの要素数が実機より少ない既存Componentも」に限り、「syncObject内などの入れ子のlistはこの作り直しの対象外で、短く宣言しても収束は保証されません」を1文加える。入れ子 list の検出機能は追加しない。
- 検証: `README.md:18`・`README_JA.md:7`・`docs/DECLARATIVE.md:193`・`README-DETAILS.md:181` の4か所の対象範囲が一致することを目視と grep で確かめる。実装側は既存の `AShorterListInsideASyncObjectIsNotRecreated` が固定している。

## 反映の手順と境界

- 承認後、fork の `external/resoloop` で PR #9 の head ブランチ `fix/list-shrink-recreate-split` の先端（`git fetch origin` で確認）に実装する。他の worktree の未コミット変更は取り込まない。
- 反映の条件は、上記の追加・更新したテストと `dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~ApplyWorkflowTests` の成功。`scripts/resoloop-fork.sh test` による全テストは条件にしない（既存 PR の CI に任せる）。
- 既存 PR #9 の head へ commit し `git -C external/resoloop push origin HEAD` で反映する。新しい PR や `*-review-fixes` ブランチは作らない。push の後、review-fix-planning の形式で PR #9 にコメントを作成または更新する。
- 実機 Resonite での確認は今回の範囲外で、fake client のテスト結果から実機での挙動を保証済みとは書かない。
- この Spec をユーザが明示的に承認するまで、fork のソース・テスト・文書は変更しない。

## 最終レビューでの追加裁定（SDD 実行指示後）

全ブランチレビューの I1 / I2 は静的な経路追跡で指摘されたため、修正担当がまず offline 回帰テストで再現を確認してから変更する。裁定と対象外17項目の確認は当該計画の SDD ledger に記録する。

- I1: 「対応1」手順5の1つ目を現状のまま残す指定は、候補が中断した apply の旧／新 Component だと利用者が確認できることを必須にする範囲で修正する。型や参照だけでは管理外候補の削除を許可しない。確認できない候補を削除せず、state を維持し推測しない。位置修復の方針 A と exact ID / `--yes` の制限は維持する。
- I2: stable selector の state reader と consumer にも、中断 recreate と未確認 index の情報を引き継ぐ。別セッションで未確認の保存位置から他 key を解決せず停止し、同セッションで現在の保存 ID が確かめられる経路は維持する。schemaVersion、`MarkSlotIndexesUnverified` の SupersededId 除外、apply の fields checkpoint、自動再開は変更しない。
- M1: plan の汎用 recovery にある削除条件は stale 対象の prune に限定する文面へ修正する。recreate のオプトインを追加しない。
- M2: baseline と同じ SDK/workload 通知は環境 Minor として残し、この作業で SDK 設定や workload を更新しない。
- 追加検証: 同型の管理外候補＋置換 Add 前失敗＋再読込、および複数 recreate の旧 Component 削除応答喪失＋再読込＋stable selector 解決を回帰テストで固定する。具体的な selector consumer へ渡す前に変更0回で停止すること、同セッションの確認済み ID、未確認 index、member selector、legacy state の既存挙動を確認する。既存の関連202件も引き続き通す。

