# リスト縮小時の Component の作り直し（分割案）と Slot の index の保存し直し

- **状態**: 設計確定（2026-10-01）。第 1〜4 節はユーザが節ごとに承認した。第 5・6 節は、ユーザの指示（「途中で止めずに、推奨案で進めてください」）により推奨案で確定した。同日、Spec と計画のレビュー（`docs_draft/2026-10-01-list-shrink-recreate-split-review.md`、R-01〜R-65）を反映した。反映の判断と、ユーザが決める事項をレビューの推奨で決めたもの（D-27〜D-33）は、`docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-review-fixes-design.md` と 12 章にある。
- **引き継ぎ元**: usaturn/resoloop#6（この Spec ができるまでの正本）。上流での相談は orange3134/resoloop#5。「第 n 節」は brainstorming で提示した設計の節を指す。第 1・2 節の本文は usaturn/resoloop#6 の §5.1・§5.2 にある。
- **実装計画**: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`。計画のコードは、上流 `b3a84ae` の使い捨てのコピーで試作して検証した（試作で見つかった設計の補正は D-26）。実装は、この Spec と計画を含む create-reso-world の PR #8 がマージされてから、マージされた版を参照して始める。
- **対象**: fork の usaturn/resoloop（作業ルートは create-reso-world の `external/resoloop`）。分岐元は fork の main `b3a84ae`（上流の `v0.1.0-preview.15` と同じ）。
- **用語**: 「上流」は orange3134/resoloop、「fork」は usaturn/resoloop を指す。「A」は Slot の index を保存し直す修正、「B」はリスト縮小時に Component を作り直す修正を指す。

## 1. 目的

ResoniteLink 0.13.1 には、リストの要素を削除する操作が無い。宣言したリスト型のメンバー（例: `MeshRenderer.Materials`）を短くすると、apply は収束しない。要素がワールドの参照（`$component:` など）のリストでは `APPLY_REFERENCE_NOT_RETAINED` で止まり、止まった時点で、ほかの変更はすでに書き込まれている。それ以外のリストは、apply のたびに書き直して収束しないまま成功を返す。

- **B**: 宣言したリストが実機より短い既存の管理 Component を、apply が自動で作り直す（上流 Issue #5 の選択肢 (a)）。
- **A**: Component を削除した後に、同じ Slot に残る key の `componentIndex` がずれる上流の不具合を直す。B の前提でもある。あわせて、ワールドの再読込後に、文書から外した key の照合結果が state に保存されない不具合を直す。
- **最終目的**: 上流に手間をかけずに取り込んでもらう。レビュー量、マージ順の管理、コンフリクトの解消、マージ後の保守を上流に負わせない。

## 2. 用語

- **作り直し（recreate）**: 同じ Slot に新しい Component（置き換え先）を作り、管理 Component からの参照を張り替えてから、元の Component（置き換え元）を削除すること。
- **途中の作り直し**: state の Component の記録に `supersededId` が残っている key。
- **宣言中の key / 文書から外した key**: 文書が宣言している key と、state にはあるが文書に無い key。
- **同じセッション**: state の `sessionId` と、接続の `UniqueSessionId` が一致すること。上流の判定と同じ。
- **照合**: state の key を、実機の Slot・Component に結び付けること。上流の `MatchComponent`、`FindManagedSlot`、削除計画の処理が行う。

## 3. 前提となる事実

### 3.1 上流のコード（`b3a84ae` の `src/RLoop.Core/WorldService.cs`）

- **Component の照合（`MatchComponent`）**: 同じセッションなら ID で照合する。ID で見つからないとき、または別のセッションでは、`StableComponentCandidates` で、型、`memberNames`、`identityValues`、参照トポロジ（`referenceSelectors`）の順に候補を絞る。それでも複数残り、identity が無ければ、`componentIndex`（Slot のすべての Component の並びでの位置）で 1 つに決める。`componentIndex` が同じ型の別の Component を指していると、その Component に黙って結び付く。state に `memberNames` と `identityValues` の両方が無い場合は `TypeOrdinal` で決める。
- **Slot の照合**: 同じセッションでも ID が空ならパスで探す。runtimeRelocatable の Slot は、別のセッションでも ID を先に試す。
- **`componentIndex` の決め方**: plan の時点で決まる。既存の Component は実機の並びでの位置、新しい Component は「実機の件数＋その Slot で先に作る件数」。宣言中の key は、apply のたびに Component の段階とフィールドの段階の 2 回、plan の時点の値（実行時の `ComponentRuntime.ComponentIndex`）で保存し直す。
- **apply の段階**: アセット → Slot → Component（作成） → フィールド → Slot の移動 → prune → 参照の再確認、の順に進む。
  - Component の作成では、`AddComponentAsync` の前に、ID が空の記録を checkpoint する。作成後に ID 付きで checkpoint する。
  - フィールドの段階では、変更があれば `ForgetComponentAssetEvidence` → checkpoint → `SetComponentMembersAsync` の順に進む。Component の移動（`RelocationSource`）は、移動先で作成 → フィールドを書く → 移動元を `RemoveComponentAsync`、の順。
  - **prune も移動元の削除も、同じ Slot に残る key の `componentIndex` を保存し直さない。**
  - 参照の再確認: 作成・更新・削除が 1 件以上あるとき、ワールドの参照（`$asset:` を除く）を含む宣言済みフィールドだけを読み直す。一致しなければ書き直して再確認し、それでも一致しなければ `APPLY_REFERENCE_NOT_RETAINED` を出す。要素がワールドの参照のリストが縮まないときの症状はこれである。それ以外のリストは再確認の対象にならず、apply のたびに書き直して収束しない。
- **`Checkpoint`**: state の `sessionId` を現在のセッションにして保存する。
- **削除計画（`BuildDeletionPlans`）**: 文書から外した key を、同じセッションなら ID だけで、別のセッションなら Slot はパス、Component は `MatchComponent` で照合する。照合の結果は state に保存しない。
- **state の書き出し**: `JsonSerializerOptions` に null を省く設定が無く、null の値も `"identityValues": null` のように書き出す。読み込みは未知のプロパティを無視する。

### 3.2 ResoniteLink のリスト

- Resonite `2026.9.18.82`、ResoniteLink `0.13.1` の実機で、テスト用の Slot を使って次を観測した。
  - `[A,B]` の `MeshRenderer.Materials` に `[A]` を送っても `[A,B]` のまま。
  - `[]` を送っても変わらない。
  - その後 `[B]` を送ると `[B,B]` になる。
- 上流が固定している `YellowDogMan.ResoniteLink 0.13.1` のメッセージ型に、リストの要素を削除する操作は無い。公式ドキュメントにも、短いリストの扱いは書かれていない。
- ResoniteLink は Component の同期メソッドを呼べる（`callSyncMethod`。上流は `CallComponentMethodAsync` として使う）が、`MeshRenderer` の同期メソッドは `AutoRig`（`Rig` を 1 つ取る）・`SplitSubmeshes`・`MergeByMaterial`（どちらも引数なし）だけで、リストの要素を指定して削除するものは無い（slum02 のリフレクションのキャッシュで確かめた）。
- 上流のアダプターは、`SyncList` を要素の種類によらず kind `list` として写す。実機で観測したのは参照のリスト（`Materials`）だけだが、検出（7.1）は最上位のリストを要素の種類によらず対象にする（値のリスト、syncObject を要素とするリストを含む）。syncObject の中のリストは対象外。値のリストがその場で縮むかどうかは、実機での確認（10.3）で確かめる。

### 3.3 使い捨てのテストで確かめたこと（2026-10-01、上流 `b3a84ae` のコピー）

リポジトリの外で、偽クライアントを使って確かめた。テストのコードは残していない。

1. **A の再現**: identityFields の無い同じ型の Component 3 つ（key `t1`〜`t3`）から `t1` を prune した。state には `t2` が index 1、`t3` が index 2 のまま残った（実機の位置は 0 と 1）。ワールドを再読込して apply すると、`STABLE_COMPONENT_AMBIGUOUS` で止まった。
2. **文書から外した key の照合結果（Component）**: `t3` を文書から外した（prune はしない）。再読込直後の `plan --prune` は `t3` を削除対象に挙げた（1 件）。しかし同じセッションで apply を 1 回実行すると、次の `plan --prune` では 0 件になった。state の `t3` の ID は再読込前のまま残り、`sessionId` だけが新しくなったため、ID で探して見つからなくなった。
3. **同じ問題（Slot）**: Slot とその Component を文書から外し、同じ手順で確かめた。削除対象は 2 件から 0 件になった。

### 3.4 手元のデータ（create-reso-world の apply 文書。git 管理下の 27 件と未追跡の export 2 件の計 29 件。各プロジェクトの `tmp/` と `.resoloop/` を除く）

- 参照のリストを持つ Component は `MeshRenderer`（`Materials`）だけで、2,256 個ある（git 管理下だけなら 27 件・2,177 個）。値のリストの宣言は 0 件。
- 同じ Slot に同じ型の `MeshRenderer` が複数ある例は 0 件。`MeshRenderer` どうしの参照も 0 件。宣言の中で `MeshRenderer` を参照する Component も 0 件で、今のデータでは REFERENCED の停止も参照の張り替えも起きない。
- `identityFields` を使っているのは slum02 の 13 か所だけ。

### 3.5 fork PR #5（`555338e`）から流用するもの

fork PR #5 は上流の最新と衝突し、レビュー修正も打ち切っている（usaturn/create-reso-world#5）。B は rebase せず、上流の main から作り直す。流用するのは考え方と文言だけで、次のものに限る。

- 作成 → 参照の張り直し → 置き換え元の削除、という順序
- `supersededId` という名前
- 停止コードの考え方（名前は 7.7 で決め直した）
- 偽クライアントに「`Materials` の末尾の要素が残る」挙動を足すこと
- 文書の文言（作り直すと、`initialFields` は宣言の初期値に、宣言していないメンバーは型の既定値に戻る）
- 旧 PR #5 のレビューで一度直した修正のうち、このレビュー（R-01〜R-65）で再発が分かったものの形: round 7 の「実行時の index も合わせる」（R-01）、round 8 の修正 B（`2c324e3`、syncObject の部分宣言。R-06）、`555338e` の修正 C（検証が終わるまで置き換え先を参照先にしない。R-02）と修正 D（作成前の checkpoint の selector。R-12）、round 5 の G13（ID の無い key を位置で照合して止める。R-05）

## 4. 範囲

### 4.1 範囲内

- **A**
  - Component を削除した後に、その Slot の key の `componentIndex` を保存し直す（`SaveSlotIndexesAsync`）。
  - 削除計画が文書から外した key（Component と Slot）に照合した結果を、state に保存する。
- **B（分割の範囲）**
  - 同じセッションの中での作り直しと、作り直しの途中からの再開。
  - 作り直しの途中でセッションが変わった場合などは、変更前に止める。

### 4.2 範囲外

次は 11 章に記録するだけで、実装しない。

- 作り直しの途中で中断し、ワールドを再読込した後の再開
- syncObject の中のリスト
- runtime が非同期にリストを詰め直す場合
- Component の削除の応答が失われ、次の apply が成功する前にワールドを再読込した場合（修正前からある問題）。prune で削除した Component の応答が失われた場合は、同じセッションの後続の apply が成功しても、その key が state に残る（11.1。D-29）
- Component の移動が、移動先の作成前の checkpoint の後に中断すると、移動元が残る問題（上流の既存の設計課題）。移動先に同じ型の Component がある移動を中断すると、修正前からある所有権の衝突で止まる場合もある

次は、この作業では扱わない。

- fork PR #5 とブランチ `fix/list-shrink-recreate` の修正・rebase・force push、そのレビュー修正
- `external/resoloop/reviews/` にある過去のレビュー指摘への対応
- create-reso-world の CI の失敗 2 件（gitleaks の権限、`test-herdr-migration.bash` の環境依存）
- 判定基準（10.3）を満たす前の、上流への Issue・PR・コメント

## 5. 不変条件

- **I1（完了時点の index）**: apply が成功して終わった時点で、作り直しが途中でない Slot について、その Slot に結び付く state の key（宣言中の key、文書から外した key、この apply で作った key）のうち、apply が Component に照合できたものの `componentIndex` は、実機の並びでの位置と一致する。照合できない key（Component が見つからない、候補が一意でない）の値は変えない。
- **I2（途中の扱い）**: `supersededId` が残っている key は、ID だけで再開する。使う ID は、置き換え元の ID（`supersededId`）と、記録があれば置き換え先の ID（`id`）。再開するのは、同じセッションで、かつその key が同じ Slot に宣言されているときだけ。それ以外は変更前に止める。
- **I3（位置で推測しない）**: 置き換え先の ID が無い場合、またはその ID の Component が Slot に無い場合は、次のように決める。
  - どの key にも結び付いていない同じ型の Component が Slot に無ければ、新しく作る。
  - 1 つでもあれば、変更前に止める。
- **I4（取り消しで参照を壊さない）**: 置き換え元が残っている間は、段階 3 で全件の検証が通る前の置き換え先を指す参照を、apply は書かない（置き換え先どうしの参照を含む）。置き換え元がすでに無い key の置き換え先は、検証も取り消しもしないので、そのまま参照先にする（12 章の D-26）。前の apply で参照先になりうる置き換え先は、宣言の縮小では取り消さない。apply が読んだ範囲でそれを参照するものがあれば、変更前に止める（7.4。D-27）。
- **I5（所有権）**: apply（作り直し、再開、取り消しを含む）が変更・削除するのは、state の ID または照合で key に結び付いた Component と、その apply が作った Component だけ。ID が空の key を型と位置で照合して得た Component は、作り直しの対象にしない（7.1）。I3 は、I5 のうち再開の経路の規則である。
- **I6（追跡と停止の安全性）**: 収束した時点で、apply が作った Component は key と 1 対 1 に結び付き、管理外の Component は変わらない（利用者が置いた管理外の Component と、4.2 の移動元の残りは対象外）。止まるときの suggestions は、そのとおりに実行すれば I5 を破らずに収束できる手順を示すか、自動では収束できないことと手で確かめる点を明示する。

## 6. 設計 A: index の保存し直しと、文書から外した key の照合結果の保存

### 6.1 `SaveSlotIndexesAsync`

- **入力**: `PreparedApply`、Slot の stable key、Slot の ID。
- **処理**: `GetSlotAsync(slotId, 0, false)` で Slot を読み直し、Component の ID の並びを得る。state の Component のうち `slotKey` がその Slot のものについて、保存している `id` が並びの中にあれば、その位置を `componentIndex` に保存する。見つからない key は変えない。あわせて、その Slot に宣言した key の実行時の `ComponentIndex` も実機の位置に合わせる。フィールドの段階が、実行時の値で state を書き直すためである（移動先が先に処理される向きの移動で、フィールドの段階が古い index を書き戻していた。R-01）。
- **保存**: メモリ上の state だけを変える。呼び出し側が直後の checkpoint で保存する。削除で state から key を外す変更は、Slot を読み直す前に checkpoint する（上流と同じく、削除とそれを state に反映する checkpoint の間に await を挟まない。R-08）。`SaveSlotIndexesAsync` の結果はその後の checkpoint で保存する。
- **呼び出し場所**:
  - A: Component の移動元を削除した後（移動元の Slot）、prune で Component を削除した後（その Component の Slot）
  - B: 置き換え元を削除した後、置き換え先を取り消した後（7.5）
- **将来の拡張への備え**: 段階に依存しない形にし、どの checkpoint の前からでも呼べるようにする（11 章）。
- **費用**: 削除 1 回につき、Component のデータを含まない Slot の読み取りが 1 回増える。prune では、削除 1 回につき state の書き出しも 1 回増える。
- **実装のメモ**: 移動元の Slot の key と ID は、plan の時点で `FindStateSlot` が得たものを `ComponentRuntime` に持たせる。prune の Component 削除には、`DeletionRuntime` に Slot の key と ID を持たせる。

### 6.2 文書から外した key の照合結果の保存

- **Slot**: 削除計画が文書から外した Slot の key に Slot を照合したら、その ID を state に保存する（ID が変わる場合だけ）。
- **Component**: 削除計画が文書から外した Component の key に Component を照合したら、その ID と、Slot の並びでの位置を state に保存する。
- **保存の時期**: `PrepareAsync` の中でメモリ上の state を変える。`plan`・`diff`・`test` は state を保存しないので、影響しない。apply では最初の checkpoint で保存される。変更前の検査（所有権の重複など）で止まった場合は、何も保存されない。
- **安全性**: 保存するのは、同じ apply の削除計画（と `--prune`）がすでに使っている照合結果である。同じ Component や Slot を複数の key が指していれば、`APPLY_COMPONENT_OWNERSHIP_CONFLICT` または `APPLY_SLOT_OWNERSHIP_CONFLICT` で、保存より前に止まる。
- **上流の方針は変えない**: 同じセッションでは ID だけで照合する（パスで探し直さない）。パスで探し直すと、同じパスに後から作られた別の Slot を削除しかねないためである。
- **修正前の state**: 修正前の apply で、古い ID のまま同じセッションになった key は、この修正でも同じセッションの間は見つからない。次にセッションが変わったときに照合し直され、保存される。

### 6.3 I1 が成り立つ理由

- **宣言中の key**: apply のたびに、plan の時点の位置を保存し直す（上流の挙動）。そのうえで、削除のたびに `SaveSlotIndexesAsync` が保存し直す。フィールドの段階は、`SaveSlotIndexesAsync` が合わせた実行時の値で保存するので、削除の後に処理される key も実機の位置になる。
- **文書から外した key**: 6.2 で照合結果を保存し、削除のたびに `SaveSlotIndexesAsync` が保存し直す。
- **この apply で作った key**: plan の時点の位置（作成時点で正しい）を保存し、その後の削除のたびに `SaveSlotIndexesAsync` が保存し直す。
- **途中の作り直しがある Slot**: I1 の対象外。完了時（7.3 の段階 5）に保存し直す。

## 7. 設計 B: 作り直し

### 7.1 検出（plan）

- **対象**: 既存の管理 Component のうち、state に記録があり、通常どおり照合でき、移動中でも途中の作り直しでもないもの。state に記録の無い key（`--adopt` の初回の apply で結び付けたもの）は、移動と同じく対象にしない（その場で更新する。D-28）。
- **判定**: `fields` に宣言した値が JSON の配列で、観測したメンバーが kind `list` で、その要素数が宣言より多ければ、その Component を作り直す。要素の種類（参照・値・syncObject）は問わない（3.2）。`initialFields` は作成時にしか書かないので、判定に使わない。
- **ID で確かめられない Component**: state の `id` が空の key（作成が中断した key）は、型と位置だけで照合される。照合した Component のリストが宣言より長くても作り直さず、変更前に既存の `STABLE_COMPONENT_AMBIGUOUS` で止める（管理外の Component を削除しないため。I5、R-05）。新しいコードは増やさない。
- **作り直しにした Component の扱い**: `Existing` を空にして作成の対象とし、観測した Component を `Superseded`（置き換え元）として持つ。理由の文言（7.8）を付ける。
- **対象外**: リストが長くなる場合と長さが変わらない場合は、従来どおりその場で更新する。syncObject の中のリストは従来どおり。移動中の Component は、移動先で新しく作るので作り直しは要らない。

### 7.2 state

- `ApplyStateComponent` に、省略できる `SupersededId`（string?）を追加する。`[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]` を付け、null のときは書かない（ほかの項目は null も書き出すが、作り直しの無い state を変えないため）。
- `CreateComponentState` は、作り直しの間、`SupersededId` を引き継ぐ。値を消すのは置き換え元の削除の段階（7.3 の段階 5）と、取り消し（7.5）だけ。
- `schemaVersion` は 2 のまま変えない。古い state はそのまま読める。
- 古い版の resoloop は `supersededId` を無視する。途中の作り直しがある state を古い版で apply することは対応しない（既知の制限、11 章）。

### 7.3 apply の段階

上流の段階に、★の 2 つを加える。括弧内に、設計の第 1 節（usaturn/resoloop#6 §5.1 の apply の手順）の番号を示す。

1. **アセット、Slot**: 従来どおり。
2. **Component の段階（作成）**: 置き換え先を作る。
   - 作成の直前に、その key の state の記録を控える（7.5 の取り消しで戻す記録。アセットの段階で再インポートにより消した根拠は、この時点ですでに消えている。R-03）。
   - 作成前の checkpoint で、`id: ""`、`supersededId: 置き換え元の ID`、`assetFields: {}` を保存する（第 1 節の手順 2）。
   - `AddComponentAsync` で作成し、`id: 新しい ID` を保存する（手順 3）。`supersededId` は残す。
   - 置き換え元が残っている間、置き換え先は全件の検証が通るまで参照先にしない（I4）。この段階で後から作るほかの Component（ほかの置き換え先を含む）は、検証待ちの置き換え先（作る Component 自身を含む）を参照するフィールドだけを除いて作り、参照以外のフィールド（`initialFields` を含む）は作成時に書く（R-11）。除いた参照はフィールドの段階で書く。
   - この apply で作る Component の、フィールドを書く前の checkpoint（作成前・作成後）には、作成時に書いた参照の selector だけを保存する。書いていない参照を照合の条件にすると、作成応答を失った後の再実行が作成済みの Component を候補から外し、もう 1 つ作るため（R-12）。
3. **★作り直しの検証**: 作り直す key ごとに、文書の順で次を行う（手順 4）。
   - 作成時に書けなかったフィールド（`initialFields` と `fields`）のうち、検証待ちの置き換え先（自分自身を含む）を参照しないものを、`ForgetComponentAssetEvidence` → checkpoint → `SetComponentMembersAsync` の順に書く。検証待ちの置き換え先を参照するフィールドは、フィールドの段階で書く（R-02）。
   - 前の apply から再開した置き換え先は、作成時に書いた値かどうかを区別できないので、`initialFields` を含めて宣言と違う値を書き直す（作り直しが完了するまでは作成の途中とみなす）。
   - 置き換え先を読み直し、宣言したリストのうち、宣言より要素数が多いものがあれば失敗とする。
   - すべての key を確かめた後、失敗があれば 7.5 の取り消しを行って止める。失敗が無ければ、置き換え先を参照先に加え、書いた値を作成時の値として扱い、フィールドの段階で書き直さない。
   - 置き換え元がすでに無い key（前の apply で削除が済み、その後の checkpoint だけが失われたもの）は、検証しない。段階 5 で記録を片付けるだけにする。
4. **フィールドの段階**: 従来どおり。管理 Component の宣言済みの参照は、ここで置き換え先の ID に張り替わる（手順 5）。移動元を削除した後には `SaveSlotIndexesAsync` を呼ぶ（A）。
5. **★置き換え元の削除**: 作り直す key ごとに、次を行い、1 回の checkpoint で保存する（手順 6）。
   - 置き換え元が残っていれば `RemoveComponentAsync` で削除する。
   - その Slot に `SaveSlotIndexesAsync` を呼ぶ。
   - `supersededId` を消す。
6. **Slot の移動、prune、参照の再確認**: 従来どおり。prune で Component を削除した後には `SaveSlotIndexesAsync` を呼ぶ（A）。

作り直しは件数として、Component の作成 1 件と削除 1 件に数える（`ComponentsAdded`・`ComponentsDeleted`）。検証の段階の書き込みは件数に含めない。進捗の表示には、置き換え元の削除を加える（移動元の削除と同じく、段階名 `fields` の進捗として出す。置き換え先の作成は、通常の作成として表示される）。

### 7.4 再開（I2・I3）

state に `supersededId` がある key は、次のように扱う。位置による照合（`StableComponentCandidates`）は使わない。

- **止める条件（変更前）**
  - 同じセッションでない → `APPLY_RECREATE_INTERRUPTED`（`reason: session-changed`）。Slot の照合と asset の計画（`BuildNode`・`BuildAssetPlans`）の後、Component の照合（`BuildComponentPlans`）の前に判定する。candidates を Slot の snapshot から作るためで、位置による照合より先に止まる。runtimeRelocatable の root の再解決など、それより前の読み取りで止まる場合は、そちらのエラーが先に出る。`plan`・`diff`・`test` も同じく止まる。止まったときは checkpoint しないので、state の `sessionId` は変わらず、何度実行しても同じく止まる。
  - その key が同じ Slot に宣言されていない（文書から外した、別の Slot に移した）→ `APPLY_RECREATE_INTERRUPTED`（`reason: key-not-declared`）。宣言された key がそろった後（`BuildComponentPlans` の後）に判定する。別の Slot に移した key は、移動元の Slot で型や位置で照合しない（R-13）。`migrateFrom` で key の名前を変えた場合は、記録ごと移るので（上流の移行の処理）、移った先の key が同じ Slot に宣言されていれば再開する。
  - 置き換え元が残っている再開の key で、置き換え先のリストが宣言より長く（作り直しの途中で宣言をさらに短くした場合など）、apply が読んだ範囲でその置き換え先を参照するものがある → `APPLY_RECREATE_INTERRUPTED`（`reason: declaration-shrank`）。置き換え先はその場で縮められず、取り消すと前の apply で張り替えた参照が切れるためである（D-27）。参照するものが無ければ止めず、通常どおり検証し、失敗すれば 7.5 の取り消しになる（実行時に詰め直されたリストの取り消しを、途中で止めた場合もこの経路で続く）。
- **照合**
  - 置き換え元: Slot の Component のうち、ID が `supersededId` のもの。無ければ削除済みとして扱う。
  - 置き換え先: Slot の Component のうち、ID が state の `id` のもの（置き換え元は除く）。
  - 置き換え先が無い場合は I3 に従う。「どの key にも結び付いていない」とは、宣言中の key の照合結果、移動元、置き換え元、削除計画の照合結果のどれにも含まれないことをいう。この判定は削除計画を作った後に行う。該当する Component が無ければ、置き換え先を新しく作る（段階 2 の手順を、`supersededId` を保ったまま行う）。1 つでもあれば `APPLY_RECREATE_INTERRUPTED`（`reason: replacement-unverified`）で止める。
- **再開した key の検証**: 置き換え元が残っていれば、段階 3 で新しく作った置き換え先と同じく検証する。
- **置き換え元がすでに無い再開の key**: 置き換え先のリストが宣言より長ければ（宣言をさらに短くした場合）、置き換え先を置き換え元とする新しい作り直しにする（D-27）。そうでなければ、置き換え先をそのまま参照先にする（D-26）。

### 7.5 検証の失敗と取り消し

- **取り消す対象**: 検証に失敗した key と、この apply で置き換え先を作った key のすべて。後者は検証を通ったものも含む。置き換え元がすでに無い key は、戻す先が無いので取り消さない。
  - この apply で作った置き換え先は、I4 によりまだどこからも参照されていない（置き換え先どうしの参照も書いていない）ので、削除しても参照は壊れない。
  - 前の apply から再開した置き換え先は、検証を通れば残す。前の apply で参照の張り替えが済んでいる可能性があるためである。次の、同じセッションの apply で再開する。NOT_CONVERGED の context の `inProgress` に、残した key を示す（R-34）。
  - 前の apply から再開した置き換え先が検証に失敗するのは、apply が読んだ範囲で何も参照していない場合（7.4 の `declaration-shrank` の条件に当たらない場合）か、runtime が検証の後に詰め直した場合（11.4、範囲外）だけである。
- **取り消しの手順**: 対象の key ごとに次を行い、最後に 1 回 checkpoint してから `APPLY_LIST_SHRINK_NOT_CONVERGED` で止める。
  1. 置き換え先が残っていれば削除する。
  2. state の記録を戻す。この apply で作り直しを始めた key は、置き換え先を作る直前の記録（7.3 の段階 2 で控えたもの。アセットの段階で再インポートにより消した根拠は戻さない）に戻す。再開した key は、`id` を `supersededId` の値に戻し、`supersededId` を消し、`assetFields` を空（根拠なし）にする。
  3. その Slot に `SaveSlotIndexesAsync` を呼ぶ（同じ apply で置き換え先の後ろに作った Component の index も直る）。
- **投げる前の片付け**: `APPLY_LIST_SHRINK_NOT_CONVERGED` を投げる前に、置き換え元がすでに無い key は段階 5 と同じく `SaveSlotIndexesAsync` を呼んで `supersededId` を消し、checkpoint する（削除はしない）。検証も取り消しの対象にもならない key なので、このまま止まると `supersededId` が残り、再読込のあとの apply が `session-changed` で止まる（PR #8 のレビュー）。`inProgress` には入れない。
- **取り消しの途中で失敗した場合**: その時点のエラーで止まる。state には `supersededId` が残るので、次の同じセッションの apply で再開する。再開した置き換え先は、検証を通れば残り（前の apply から再開した置き換え先の規則）、検証に失敗した key と、その apply で作り直した置き換え先は改めて取り消す。

### 7.6 変更前の検査

`PrepareAsync` の中で、変更の前に次を行う。

- **所有権**: `ValidateComponentOwnership` の対象に、置き換え元（種類 `superseded`）を加える。宣言中の key、移動元、削除計画と同じ Component を指していれば、`APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止める。
- **中断した作り直し**: 7.4 の止める条件と I3。
- **ID で確かめられない Component**: 7.1 の `STABLE_COMPONENT_AMBIGUOUS`。
- **参照（`APPLY_LIST_SHRINK_REFERENCED`）**: 置き換え元が残っている作り直しがあれば、apply がすでに読んだ snapshot（`SnapshotSlots`）を調べる。置き換え元、またはそのメンバー（入れ子と要素を含む）を参照しているものが、次のどれでもなければ止める。
  - 管理 Component の宣言で、その参照と同じ位置（syncObject・dictionary は同名の子、list は同じ index、トップレベルはそのメンバー）に `$component:` などの参照の指定があるもの（apply が張り替える）。syncObject の部分宣言は宣言した子だけを書き込むので、宣言していない子の参照は除外しない（R-06）。
  - この apply で削除する Component（置き換え元、移動元）
- 調べる範囲は、apply の読んだ snapshot（宣言の親 Slot 以下、読み取りの深さまで。読み取りの深さは、文書の階層の深さ＋1 と、state に記録した階層の深さの大きい方）に限られる。このことは、エラーの suggestions と文書（README を含む）に書く。

### 7.7 エラーコード

| コード | 終了コード | 止まる時点 | ワールドの状態 |
|---|---|---|---|
| `APPLY_LIST_SHRINK_REFERENCED` | 6（`ValidationFailed`） | 計画（変更前。`plan`・`diff`・`test` も同じく止まる） | 変更なし |
| `APPLY_RECREATE_INTERRUPTED` | 6（`ValidationFailed`） | 計画（変更前。`plan`・`diff`・`test` も同じく止まる） | 変更なし |
| `APPLY_LIST_SHRINK_NOT_CONVERGED` | 7（`OperationFailed`） | 作り直しの検証 | この apply で作った置き換え先と、失敗した置き換え先は取り消し済み。それより前の段階の変更は残る |

- 終了コードは既存のコードに合わせる。変更前に止まるものは `APPLY_COMPONENT_OWNERSHIP_CONFLICT` と同じく 6、実機の挙動で止まるものは `APPLY_REFERENCE_NOT_RETAINED` と同じく 7。
- 第 1 節で決めた `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` は、`APPLY_RECREATE_INTERRUPTED` にまとめ、`reason` で区別する（第 3 節後半で承認）。3 つとも「途中の作り直しを自動では再開できないので、変更前に止める」点が同じで、違うのは復旧手順だけである。
- **context**
  - REFERENCED: `stateFile`、`recreates`（key、置き換え元の ID、理由）、`references`（参照先の key と ID、参照元の ID・型・メンバー、Slot の ID とパス）
  - INTERRUPTED: `reason`、`stateFile`、`componentKey`、`slotKey`、`slotPath`、`type`、`supersededId`、`savedId`、`candidates`（同じ型の候補ごとの ID、kind が list のメンバーごとの要素数（宣言の有無を問わない）、`referencedBy`（apply が読んだ範囲でその候補か候補のメンバーを参照している Component の ID・型・メンバー））。`supersededId` と `savedId` は state の値で、`session-changed` では前のセッションの ID なので、`remove` には使わない。
  - NOT_CONVERGED: `failures`（key、メンバー、宣言と実機の要素数）、`undone`（取り消した key）、`inProgress`（再開して検証を通ったので残した、作り直しが途中の key）。apply の通常の context（`stateFile`、件数、`recovery`）も付く。
- **メッセージと suggestions**（英文）
  - REFERENCED: "A declared list member must shrink, which requires recreating its Component, but something other than a declared managed reference points at the Component or its members. No mutations were performed."
    - "Declare the referencing member as a managed field with a $component/$member selector so apply can re-point it, or remove the reference."
    - "Only the snapshots this apply read were checked. Inspect other references to the Component before applying."
  - INTERRUPTED（`session-changed`）: "A list-shrink recreate of '{key}' was interrupted and the world session changed, so the replaced Component and its replacement can no longer be told apart by ID. No mutations were performed."
    - 同じ Slot に同じ型の key がほかに無い場合: "Keep the candidate that the Components in its referencedBy point at, or either one if none is referenced, and remove the other with 'resoloop component remove ID --yes'. Use only the IDs in candidates; supersededId and savedId are IDs from the earlier session." と "Then back up the state file, set components.{key}.id to its supersededId if the ID is empty, delete supersededId, and re-run apply."（管理 Component の参照が今指している方を残す。宣言より長い方を削除する規則では、参照の張り替えの前後で中断したときに管理 Component が重複した。D-30）
    - 同じ Slot に同じ型の key がほかにある場合: "Another key on this Slot has the same type, so the candidates include its Components and apply cannot tell the recreate's Components apart. Keep the state file as it is, check in Resonite what each candidate references and what references it, and do not repair this by guessing IDs."（自動では収束できず、手で確かめる点を示す。I6）
  - INTERRUPTED（`key-not-declared`）: "A list-shrink recreate of '{key}' was interrupted, and the document no longer declares the key on its Slot. No mutations were performed."
    - "Declare the key again on the same Slot and re-run apply in this session to finish the recreate. Then remove the key and apply with --prune --yes if you no longer want it."（state を手で直す 2 つ目の手順は、従うと残した Component が同じセッションの間 prune できなかったので削った。R-16）
  - INTERRUPTED（`declaration-shrank`）: "A list-shrink recreate of '{key}' was interrupted, and the document now declares a list shorter than its replacement holds while something references the replacement. No mutations were performed."
    - "Declare at least as many elements as the replacement holds (see candidates) and re-run apply in this session to finish the recreate, then shorten the list again."
  - INTERRUPTED（`replacement-unverified`）: "A list-shrink recreate of '{key}' was interrupted before its replacement ID was saved, and the Slot holds a same-type Component that no key owns. No mutations were performed."
    - "If a candidate's lists match the declaration, it is most likely the replacement that the interrupted apply created. If the declaration references a Component that the same apply creates later, apply creates the replacement without initial values, so its lists are all empty; a Component with empty lists that you added looks the same. Inspect each candidate with 'resoloop component inspect ID', remove only one you can confirm the interrupted apply created with 'resoloop component remove ID --yes', and re-run apply; apply creates the replacement again."
    - "If no candidate fits that description, back up the state file, set components.{key}.id back to its supersededId, delete supersededId, and re-run apply to start the recreate again."
  - NOT_CONVERGED: "The runtime kept a list longer than declared on a replacement Component, so recreating it cannot converge. The undone replacements were removed and their original Components are unchanged."
    - "Declare the list length that the runtime keeps, or find what refills the list."
    - "Re-run apply only after changing the declaration; re-running the same command recreates and undoes the Component again. The undone keys have no recreate in progress."
    - `inProgress` があるとき: "The recreate of '{keys}' stays in progress. Finish it by re-running apply in this session; after a world reload, apply stops with APPLY_RECREATE_INTERRUPTED."
  - 7.1 の `STABLE_COMPONENT_AMBIGUOUS`: "Component '{key}' has no saved ID, so it was matched by type and position only, and its list is longer than declared. Apply does not recreate a Component it cannot verify. No mutations were performed." context は `candidateIds`・`type`・`componentKey`。
    - "If an interrupted apply created this Component, remove it with 'resoloop component remove ID --yes'; otherwise it is unmanaged content and should stay."
    - "Then back up the state file, remove components.{key} from it, and re-run apply; apply creates the Component for this key."
- state の手編集を要する復旧手順（`session-changed`、`replacement-unverified` の 2 つ目、7.1 の `STABLE_COMPONENT_AMBIGUOUS`）は、エラーの suggestions と既知の制限（11.4）と PR 本文の既知の制限にだけ書く。上流の文書（DECLARATIVE.md、README、skills）には、上流の回答が出るまで新しく載せない（D-31）。

### 7.8 plan の表示

- Component の操作に `recreate` を追加する。差分（`diffs`）は update と同じ形で出す。新しく作り直す場合は、置き換え元の観測と比べる。
- **理由の文言**
  - 新しく作り直す場合: "list member '{member}' shrinks from {n} to {m} elements; ResoniteLink cannot remove list elements, so apply replaces the Component (initialFields return to their declared values and undeclared members to their type defaults)"。メンバーが複数あれば、メンバーごとの部分を "; " でつなぐ。
  - 再開して、置き換え先がある場合: "resumes an interrupted recreate: removes the replaced Component '{id}' after managed references point at the replacement"
  - 再開して、置き換え先が無い場合: "resumes an interrupted recreate: creates the replacement, then removes the replaced Component '{id}'"
  - 再開して、置き換え元がすでに無く、置き換え先がある場合: "resumes an interrupted recreate: the replaced Component is already removed; apply saves the final Component indexes"
  - 再開して、置き換え元も置き換え先も無い場合: "resumes an interrupted recreate: the replaced Component is already removed; apply creates the replacement"（検証はしない。I4・D-26 のとおり）
- **サマリーの件数**: `recreate` は、`relocate` と同じく `updates` に数える。件数の項目は増やさない。
- **フィルター**: `--creates-only`・`--deletes-only` には出さない（prune による削除ではない）。`--changes-only` には出る。既存の CLI のフィルター（`Action` による絞り込みと `Changes`）で満たされる。

### 7.9 アセット移行（`f46bdd0`）との統合

1. 置き換え先の `assetFields` は、作成前の checkpoint で空にする（上流で新しく作る Component と同じ）。フィールドを書いた後に、宣言から記録する。
2. `DetectSavedAssetMigrations` は、新しく作り直す key について置き換え元を観測する（`Existing ?? RelocationSource ?? Superseded`）。これが無いと、resdb へ移行したアセットを使うのが作り直す Component だけの場合に、`local://` の URL を書き戻す（fork 版の `d615eeb` で見つかった問題）。再開した置き換え先は、フィールドを書くまで `assetFields` が空なので、根拠として使われない（上流の規則どおり）。
3. 検証の段階で書くときも、`ForgetComponentAssetEvidence` → checkpoint → 書き込み、の順にする。
4. `assetFields` の無い古い state で作り直す場合は、置き換え元の観測を確かめられないので、上流と同じく `APPLY_ASSET_MIGRATION_UNVERIFIED` で変更前に止まる。
5. 取り消し（7.5）では、この apply で作り直しを始めた key は置き換え先を作る直前の記録（アセットの段階で再インポートにより消した根拠は戻さない）に戻し、再開した key は空（根拠なし）にする。plan の時点の記録に戻すと、再インポートで消した根拠が復活し、ワールドの保存・再読込の後に古い内容の resdb の URL を黙って採用していた（R-03。上流 `f46bdd0` が防いだ問題）。

### 7.10 既存の挙動との関係

- `APPLY_REFERENCE_NOT_RETAINED` は、リストの縮小以外の原因（ほかの driver が参照を握っている場合など）では従来どおり出る。
- Component の移動では、移動元の削除を `--prune` も `--yes` も無しで行う（上流の前例）。作り直しも同じく、置き換え元の削除を `--prune` と `--yes` 無しで行う。上流の `AGENTS.md` の「CLI delete/remove must retain explicit --yes」は、削除そのものを目的とするコマンド（`slot delete`、`component remove`、`apply --prune`）についての規則である。作り直しは移動と同じく、宣言に収束させるための置き換えであり、plan の `recreate` の理由で置き換えることを事前に示す。移動と同じく、state に記録のある key に限る（`--adopt` の初回の apply では作り直さない。上流の adopt は既存の内容を消さずに結び付ける操作である。D-28）。
- `test` は、作り直しを控えた key を、移動を控えた key と同じく、まだ存在しないものとして扱う（上流の既存の挙動）。この扱いになるのは apply の前と、NOT_CONVERGED・中断の後だけで、apply が完了した後の `test` には影響しない。
- `ApplyResult` に項目は増やさない。

## 8. テスト

### 8.1 偽クライアントの拡張（`tests/RLoop.Tests/ApplyWorkflowTests.cs` の `FakeResoniteClient`）

1. **リスト**: 指定したメンバー（例: 型 `Test.Renderer` の `Materials`）を kind `list` で持つ。文字列の要素は参照、それ以外の要素は値として持つ（値のリストのテスト用。R-19）。短いリストを送ると、先頭だけを置き換えて末尾を残す（`[A,B]` に `[A]` は `[A,B]`、`[]` は変化なし、続けて `[B]` は `[B,B]`）。型の説明（`DescribeComponentTypeAsync`）も合わせる。この挙動は、偽クライアントだけを確かめるテストで固定する（R-33）。
2. **書き込みの失敗の注入**: 書き込みの位置で指定する方式にそろえる。既存の `FailOnWrite`（反映する前に失敗）に加え、`LoseResponseOnWrite`（反映してから応答を失う）を足す。Slot・Component の作成と削除、フィールドの書き込みのすべてを対象にする。
3. **リストの詰め直し**: 書き込んだリストを、実機が指定の長さまで詰め直す設定（`RefillListsTo`。NOT_CONVERGED の確認用）。
4. **特定の Component の削除の失敗**: 指定した Component の削除が、反映前に失敗する設定（`FailRemovingComponent`。置き換え元の削除で止める確認用）。

### 8.2 網羅テスト（B の中心）

- **シナリオ**
  - S1: Component を 1 つ作り直す。それを参照する管理 Component が 1 つあり、同じ apply で新しく作る参照元（`initialFields` を持つ）が 1 つある（R-12）。
  - S2: 同じ Slot で 2 つを作り直す。その Slot から別の Component を移動する。文書から外した同じ型の key が 1 つ残っている（I3 の「削除計画の照合結果」の出所を確かめる。R-21）。r1 は同じ apply で後から作る material を参照する。index の保存が重なる場合を確かめる。
- **手順**: 書き込みの位置 k を 1 から最後まで、2 つの失敗の仕方（反映前に失敗、反映後に応答を失う）で止める。そのたびに、次の 2 つを確かめる。
  - 同じセッションで apply し直す → 収束するか、`replacement-unverified` で変更前に（書き込み 0 件で）止まる。止まった場合は suggestions の基準で選んだ候補（リストが宣言と一致するもの、または宣言が同じ apply で後から作る Component を参照する key では、リストがすべて空のもの）が 1 つだけで、中断した apply が作った Component であることを確かめてから削除し、その後に収束することを確かめる（R-15）。
  - ワールドを再読込してから apply する → state に `supersededId` があれば、`plan` と 2 回の apply が書き込み 0 件のまま `session-changed` で止まり、state が 1 バイトも変わらない（R-21）。S1 では suggestions の手順（`referencedBy` で参照されている候補を残し、もう一方を削除し、state を直す）を context だけを使って行い、収束することを確かめる。S2 では、同じ型の key がほかにあるので自動では区別できないことを示す suggestion が返ることを確かめる（R-14）。
  - S1 では、進捗の通知ごとにキャンセルする場合も確かめる（2 つの失敗の注入では作れない、checkpoint の直後の state を作る。R-20）。
- **収束の判定（共通の確認関数）**
  - state に `supersededId` が無い。
  - ワールドの作り直す型（Test.Renderer）と参照元の型（Test.Source）の各 Component が、state のちょうど 1 つの key に結び付いている（余分な Component が無い。R-20）。ほかの型は見ない（4.2 の移動元の残りは範囲外）。
  - 宣言した各 key の Component のリストが宣言どおり。
  - 参照元の参照先が実在し、管理 Component の参照が、作り直した Component を指している。
  - Slot のすべての key の `componentIndex` が実機の位置と一致する（I1）。
  - もう一度 apply すると書き込みが 0 件。ワールドを再読込してからの apply も、書き込みが 0 件。
- **ねらい**: 前回の手戻りの原因の 1 つ（シナリオを固定したテスト）を避け、どこで止まっても誤った状態のまま黙って進まないことを確かめる。

### 8.3 個別のテスト（B）

- リストが長くなる場合・変わらない場合は、従来どおりその場で更新する。syncObject の中のリスト、移動中の Component は作り直さない。
- 偽クライアントがリストを縮められない（8.1 の 1）。値のリストも作り直しになり、収束する。値のリストでも、runtime が詰め直すと NOT_CONVERGED で止まり、元の Component が残る（R-19）。
- REFERENCED: 管理外の Component からの参照（置き換え元そのもの、そのメンバー、リストの要素）と、管理 Component の宣言していないメンバーからの参照があると、変更前に止まる。宣言済みの参照は張り替わる。移動元からの参照では止まらない。syncObject の部分宣言で、宣言していない子が置き換え元を指していれば止まり、同じ位置に参照を宣言していれば張り替わり、入れ子に参照が無ければ成功する（R-06、R-21）。
- `key-not-declared`: 作り直しの途中で key を外す、または別の Slot に移すと止まる（同じ型の兄弟がある Slot からの移動でも、型や位置で照合せずに止まる。R-13）。終了コードは 6。同じセッションで key を元の Slot に戻すと完了し、その後 key を外して `--prune` で削除できる（R-16）。
- `declaration-shrank`: 置き換え元の削除で止めた後（管理 Component の参照は置き換え先に張り替え済み）に宣言を短くすると、書き込み 0 件で止まり、参照が生きている。宣言を戻して完了させてから短くすると収束する。置き換え元の削除の応答を失った後に宣言を短くすると、1 回の apply で収束する（R-04）。
- 作り直す 2 つの Component が互いを参照していても、1 回の apply で収束し、それぞれが相手の置き換え先を指す。再開した置き換え先が、同じ apply で取り消した置き換え先を指さない（R-02）。
- 同じ apply で作る参照元の作成応答を失っても、再実行が重複を作らない（R-12）。
- NOT_CONVERGED: 置き換え先を取り消し、元の Component・参照が変わらない（同じ apply で作った Component が取り消した置き換え先を指さない。I4）。state は置き換え先を作る直前の記録に戻る（アセットの段階で消した根拠は戻さず、再インポートが無ければ根拠を保つ。R-03）。この apply で作った置き換え先は、検証を通ったものも取り消す。前の apply から再開した置き換え先は、検証を通れば残り、`inProgress` に示される。取り消した Slot の `componentIndex` が、同じ apply で置き換え先の後ろに作った Component を含めて実機の位置と一致する（R-10）。作成時に初期値を書いた参照元の `initialFields` が失われない（R-11）。取り消しの削除のどちらで止めても、次の apply が再開と取り消しを続け、詰め直しが無くなれば収束する（R-20）。フィールドを書かずに作った置き換え先を再開して書いたときも、読み直して検証する（旧 round 9 の K-H1）。
- 再開: 管理外の同じ型の Component がある Slot では、置き換え先の作成が反映前に失敗しても `replacement-unverified` で止まり、管理外の Component は変わらない（収束は求めない。I5・I6、R-23）。同じ Slot から移動する同じ型の Component は、置き換え先と取り違えない（I3 の「移動元」の出所。R-21）。
- plan: `recreate` の理由と件数。置き換え元が所有権の検査に含まれる。state の `id` が空の key が型と位置で照合した Component のリストが宣言より長ければ、plan も apply も `STABLE_COMPONENT_AMBIGUOUS` で止まり、管理外の Component は変わらない（同じセッションと再読込後。R-05）。`--adopt` の初回の plan は `recreate` を出さない（R-18）。途中の作り直しがある state の plan は、置き換え元がすでに無い場合も含めて再開の内容を理由に示す（R-36）。
- アセット移行: 移行済みのアセットを使う Component を作り直しても `local://` に戻らない。`assetFields` の無い古い state は `APPLY_ASSET_MIGRATION_UNVERIFIED` で止まる。
- identityFields を持つ Component を作り直しても、identity の値が state に残り、再読込後も結び付く。
- 管理 Component が `$member:` で作り直す Component のメンバーを参照していれば、置き換え先のメンバーに張り替わる。
- 途中の作り直しがある state で `plan` を実行すると、再開の内容を理由に示し、ワールドにも state にも書き込まない。
- 同じ apply で、同じ Slot の prune と作り直しが起きても、index が実機の位置と一致する。
- 作り直すと、`initialFields` が宣言の初期値に戻る（文書どおりの挙動であることを固定する）。

### 8.4 A のテスト

- 同じ型で identityFields の無い 3 つから 1 つを prune、または移動（移動先の Slot が先に処理される向き、つまり子から親への移動を含む。R-01）→ 再読込 → apply が書き込み 0 件で収束する（修正前は `STABLE_COMPONENT_AMBIGUOUS`）。
- 文書から外した key が残る Slot で、ほかの Component を削除 → 再読込 → 削除計画にその key が 1 回だけ出て、所有権の衝突が起きない。
- 再読込 → apply（prune なし） → 同じセッションの `plan --prune` が、文書から外した Component と Slot を挙げ続ける（3.3 の 2・3。修正前は 0 件）。再読込後の最初の apply が移動を行い、文書から外した同じ Slot の key が残る流れでも、その後の再読込で削除計画に挙がる（R-41）。
- prune の削除が反映された直後にキャンセルされても、削除した key が state に残らない（R-08）。
- Component の移動元の削除の直後に応答を失った場合 → 同じセッションの次の apply で index が直り、その後に再読込しても正しく結び付く。移動の向きは両方（親から子、子から親）。中断しなかった回は、次の apply の前に I1 が成り立つ（R-01）。prune の削除の応答が失われた場合は、この保証の対象外（11.1。D-29）。

### 8.5 修正前との比較

上流 PR #4 と同じく、使い捨ての worktree で `src/` だけを分岐元に戻し、全件のテストを流す。分岐元は、A では main、B では A のブランチ。追加したテストのうち、今の挙動を固定するテスト以外が失敗し、それ以外のテストは成功することを、失敗するテストの件数と名前で確かめる（R-22）。

## 9. 文書

上流の `AGENTS.md` は、CLI の挙動を変えたら README と `skills/codex/*/SKILL.md` も更新するよう求めている。

- **A**: `docs/DECLARATIVE.md` に 2 点を追記する（保証を言い切らない。plan・diff は state を書かないことを書く。R-39）。
  - Component を削除・移動した後に、同じ Slot に残る key の index も実機の並びに合わせて保存し直す。
  - 再読込の後に apply が照合した、文書から外した key の ID は、その apply の checkpoint で保存する（plan・diff は state を書かない）。そのため、同じセッションの後の `--deletes-only` や `--prune` でも対象に残る。
- **B**
  - `README.md` と `README_JA.md`: アセット移行の注記と同じ程度の短い段落。リストを短くすると Component を作り直すこと、既定値に戻ること、3 つのコード。REFERENCED の検査が apply の読んだ範囲に限られること（R-30）。
  - `README-DETAILS.md`: `initialFields` の説明に、作り直すと初期値に戻ることを足す。plan の `recreate`。
  - `docs/DECLARATIVE.md`: `initialFields` の注意。diff の操作の列挙に `recreate` を足す。「Diff、rename、prune、recovery」の節に、`recreate`、`--prune` なしで置き換え元を削除すること、adopt の初回は作り直さないこと、ID で確かめられない Component は作り直さず止まること、REFERENCED の検査の範囲（宣言の親 Slot 以下、読み取りの深さまで）、3 つのコードと state を編集しない復旧手順（`declaration-shrank` を含む）。state の編集が要る手順は「エラーの suggestions に従う（state の編集が要る）」とだけ書く（D-31）。
  - `skills/codex/resonite-build/SKILL.md`: `initialFields` の注意と、plan の `recreate` を確認すること、検査の範囲の外の参照を確かめること。
  - `skills/codex/resonite-debug/SKILL.md`: 3 つのコードの意味と復旧手順。

## 10. 作業の流れ、PR、判定基準

### 10.1 A

1. fork の main から `fix/slot-index-after-removal` の worktree を作り、8.4 の最初のテストを書いて失敗を確かめる。再現しなければユーザに報告し、A をやめて I1 は B の中だけで扱う（D-15）。そのときは、作ったブランチと worktree を消さずに残して報告し、B の計画（分岐元、A の補助関数、`SaveSlotIndexesAsync`）の作り直しをユーザと決める。
2. fork に A の Issue を出す（英日併記。再現手順と 3.3 の結果、環境と確認方法（偽クライアントで確かめ、実機では未確認であること）を載せる）。Issue の番号は作業報告に記録する。
3. 6 章を実装する。fork の main 向けに PR を出す。本文の番号は、コマンドで取得して置き換える（引用付き heredoc の中で手で置き換えない）。

### 10.2 B

1. A のブランチから `fix/list-shrink-recreate-split` を分岐し、7 章を実装する。A のブランチ向けに PR を出す。
2. Issue は上流の orange3134/resoloop#5 を参照する（fork に B の Issue は作らない）。
3. このとき、古い fork PR #5 に「作り直した」とコメントして close する（PR B の番号はコマンドで取得して本文に入れ、コメントに失敗したら close しない）。ブランチ `fix/list-shrink-recreate` は残す。

### 10.3 判定基準とレビュー

- **テスト**: `dotnet test ResoLoop.slnx` がすべて成功する。8 章のテストを含む。
- **実機**: リストが縮むケース（瓦礫の `Materials` が 4 から 3 など）で apply が収束する。完了後にワールドを保存・再読込し、次の apply の書き込みが 0 件になる。値のリストと、syncObject を要素とするリストも 1 つずつ確かめ、その場で縮む種類があれば止まってユーザに報告する（検出の範囲を種類で絞るかを判断してもらう。R-19）。実機の操作は、上流の `AGENTS.md` の安全規則に従い、`ResoLoop_Test*` の Slot の下で行う。ユーザのワールドに対する apply は、ユーザの明示的な指示があるときだけ行う。
- **レビュー**: 前回の手戻りを繰り返さないため、次の規則で進める（D-32）。
  - レビューは PR ごとに 1 ラウンドを基本にする。
  - 修正の対象は、現行の HEAD で再現し、I1〜I6 のどれかを破るもの。それ以外は、下の重大度の定義で判断する。レビュアーが付けた重大度は、修正を担当する側がこの定義に照らして付け直してよい。
    - High: 書かれたとおりに実装すると、誤った動作、ワールドや state の破損、止まるべきところで黙って進むことが起きる。計画が実行できない（コードが当たらない、ビルドできない、テストが Expected と違う）。安全上の禁止事項（計画の Global Constraints、上流の `AGENTS.md` の安全規則）に反する。
    - Medium: 境界条件での不具合のおそれ、Spec の要求に対応する実装やテストの欠落、手戻りを起こしやすい誤った・あいまいな指示、上流が受け入れにくい要素。
    - Low: 表記ゆれ、軽微な不整合、読みやすさ。Low はまとめてユーザに判断を仰ぐ。
  - 同じ不変条件（I1〜I6）を破る指摘、または同じ問題群（create-reso-world#5 のコメント「原因調査」の 4.1 index の意味、4.2 初期化・検証の完了、4.3 所有権の根拠）に属する指摘が 2 件目になったら、修正を止め、どの不変条件・問題群がどの入力で破れたかをユーザに報告し、「既知の制限とする」「PR を分ける」「設計を見直す」のどれにするかの判断を仰ぐ。どの問題群にも入らず、不変条件も破らない指摘（手順と公開など）は数えない。
  - 修正の後は全体を再レビューせず、修正の差分と回帰テストだけを確かめる。
- **設計の変更**: 実装はマージ済みの Spec と計画を参照して始める（D-18）。実装中に設計を変える場合は、ユーザの承認を得てから create-reso-world に Spec（と計画）を直す PR を別に出し、12 章に理由を残す。その PR がマージされてから実装を再開する（fork の「別のブランチや PR を作らない」規則の対象外）。

### 10.4 コミットと PR の本文

- **コミット**: A は 2 件（index の保存し直し／文書から外した key の照合結果の保存）、B は 2 件（実装とテスト／文書）。件名は英文の命令形にする。`Refs orange3134/resoloop#5` は、上流に出す前の最後のまとめ直し（計画の C1）で B の 2 件に付け、fork での作業中は付けない（push や rebase のたびに上流 #5 のタイムラインに参照が増えるため。R-55）。表記は完全な形の `orange3134/resoloop#5` のまま。Claude Code が書くコミットの末尾には `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。
- **レビュー修正**: fork でのレビュー修正は同じブランチに積む（対象のコミットを指定した `fixup!` にする）。`*-review-fixes` のような別のブランチや PR は作らない。A を変えたら、B を A の上へ載せ直してから（`git rebase --onto`）まとめ直す（R-07）。上流に出す前に、上の構成へまとめ直し、上流の main に追従する。上流に出す前の A・B の force push は `--force-with-lease` で行い、ほかのブランチは force push しない。
- **上流に出した後**: 原則としてコミットを足して直し、履歴を書き換えない。push の前に必ず fetch し、メンテナーのコミットがあれば取り込む。A が変わらずにマージされた場合は B を rebase しない（上流はマージコミットでマージするので、PR B の差分は B の変更だけになる）。A が変わって B と食い違った場合や、メンテナーの依頼がある場合に限り、ユーザの確認を取って、B を `--force-with-lease` で新しい A（または upstream/main）の上へ載せ直し、PR B にコメントする。A のブランチは、メンテナーの依頼が無い限り force push しない。メンテナーのコミットは消さない。載せ直した後は、修正前との比較と全件のテストをやり直す。B のまとめ直し（`reset --soft`）は、提出後は行わない。
- **本文**: fork の Issue・PR の本文は、上流にそのまま流用できるよう、最初から英日併記で書く。Issue は Summary / Reproduction / Environment and verification / Proposed fix、PR は Summary / Root cause / Verification / Known limitations（既知の制限。4.2 と 11 章に対応）の構成にする。PR の Summary に互換性と既存の規則（`--yes`）との関係を入れ、Verification に検証した OS と SDK、実機で確かめたかどうかを書く。B の PR には「A を先にマージ」と書く（R-31、R-56）。本文の件数は直前の実行結果に合わせ、レビュー修正の後は `gh pr edit --body-file` で更新する（このリポジトリの PR でも同じ）。
- **fork の PR はマージしない**（D-8）。上流でマージされた後に close する。

### 10.5 上流への提出（D-11）

判定基準を満たしたら、文面をユーザに見せて確認を取ってから、次を一度に出す。

- A の Issue（fork の Issue を流用）
- PR A（main 向け）
- PR B（A のコミットを含めて main 向け。「A を先にマージ」と明記）
- 上流 Issue #5 へのコメント。要点は 3 つ: 回答が無いまま (a) で PR を出したこと（PR A・B へのリンク、A を先にマージ）、(a) を選んだ理由（Component の移動と同じく宣言に収束させる置き換えで、plan・diff に `recreate` と理由が出て、安全に作り直せないときは変更前に止まる）、(b)・(c) を望む場合は PR B を絞れること（(b) は既存の確認と並ぶ opt-in の停止を `ApplyAsync` の `PrepareAsync` の直後に足す、(c) は検出を残してエラーで止める）。state の手編集を要する復旧手順を suggestions での案内のままでよいか、CLI の操作を望むかも 1 行で尋ねる（R-17、R-58）。

出す順序は、上流の Issue → PR A → PR B → #5 へのコメントとする（番号が前の投稿に依存するため）。fork の番号を使った記述（`Fixes usaturn/resoloop#…`、PR B の冒頭の「先にマージする PR」）は、上流の番号に書き換える。出す前に上流の main に追従する（10.4）。提出後の追従は 10.4 の「上流に出した後」に従う（R-27）。

上流でマージ・リリースされたら、create-reso-world のロックを新しい版に切り替え、各プロジェクトで `resoloop skills sync --check` で差分を確かめてから `--update` する。fork の PR A・B と fork の Issue A を close する（D-8）。引き継ぎの正本だった fork の Issue usaturn/resoloop#6 にも、Spec・計画（create-reso-world#8）と上流の PR・Issue のリンクをコメントしてから close する。どれも GitHub への書き込みなので、実行時にユーザに確認する。

## 11. 将来の拡張（再読込後の再開）と既知の制限

### 11.1 今は止めているケース

- `APPLY_RECREATE_INTERRUPTED` の 4 つの理由（`session-changed`、`key-not-declared`、`declaration-shrank`、`replacement-unverified`）
- Component の削除の応答が失われ、次の apply が成功する前にワールドを再読込した場合。index が古いまま残り、再読込後の照合が `STABLE_COMPONENT_AMBIGUOUS` などで止まるか、誤った Component に結び付くことがある。修正前からある問題で、A が直すのは削除が成功した場合だけ。
- prune で削除した Component の応答が失われた場合は、同じセッションの後続の apply が成功しても、その key は state に残る（同じセッションの削除計画は ID だけで照合し、A の保存も照合できた key だけが対象のため）。再読込後は古い index で照合され、`APPLY_COMPONENT_OWNERSHIP_CONFLICT` か `STABLE_COMPONENT_AMBIGUOUS` で止まるか、同じ型の管理外の Component に結び付いて `--prune` の削除対象に挙がることがある。復旧は、再読込の前（またはその後の `--prune` の前）に、state の components から該当する key を外す。修正前からある問題（D-29）。

### 11.2 再読込後の再開に対応するときに変える箇所

- 作り直しの途中の checkpoint でも `SaveSlotIndexesAsync` を呼ぶ（6.1 で、どこからでも呼べる形にしてある）。
- 置き換え元と置き換え先を、ID なしで見分けるための記録を state に残す（例: 置き換え先に書いたリストの要素数と参照先、置き換え元の位置）。
- I3 の判定に、その記録を使う。
- 削除の予定を、削除の前に state に記録する。11.1 の 2・3 つ目と、Component の移動が中断すると移動元が残る問題（4.2。移動先の作成前の checkpoint の後、作成が反映される前の失敗でも起きる）も、この記録でまとめて扱える見込み。
- 再読込後の再開に対応すれば、`session-changed` の復旧での state の手編集（11.4）は不要になる。レビューで出た「置き換え先を削除し、index を置き換え元の位置に保つ」案は、参照の張り替えの後に置き換え先を削除すると張り替え済みの参照元が重複するので、そのままでは採らない。採るなら、参照の張り替えの状態で手順を分け、`SaveSlotIndexesAsync` を置き換え元の位置で保存する形にする（D-20 の変更）。

### 11.3 そのときに必要な網羅テスト

- 書き込みの位置ごとに、ワールドの再読込を挟む。
- identityFields の有無、同じ型の兄弟の有無を組み合わせる。

### 11.4 そのほかの既知の制限

- 途中の作り直しがある state を、古い版の resoloop で apply することは対応しない（7.2）。
- `APPLY_LIST_SHRINK_REFERENCED` が調べるのは、apply の読んだ snapshot の範囲だけ（7.6）。範囲の外からの参照は、置き換え元の削除で切れる。`--prune` で削除する予定の Component からの参照でも止まる（置き換え元の削除が prune より前に行われるため、安全側に止める）。
- runtime が非同期にリストを詰め直す場合、検証の時点では気付けない。次の apply でもう一度作り直しになる。同期の詰め直しは検証で止めるが、実機では観測していない（`MeshRenderer.Materials` では起きていない）。検証が無いと、そうしたリストは apply のたびに作り直され、値のリストや空の宣言では成功を返し続ける（参照の再確認の対象外のため）。
- 再開した置き換え先が検証に失敗した場合（runtime の詰め直し、または apply が読んだ範囲で何も参照していないときの宣言の縮小）は取り消す。その範囲の外に、前の apply で張り替えた参照があれば、取り消しで削除された置き換え先を指したまま残る。
- フィールドの段階に回したフィールド（検証待ちの置き換え先への参照。自分自身への参照を含む）を書いたことがきっかけで runtime がリストを詰め直しても、その apply では検出できない。次の apply でもう一度作り直しになる。前の apply から再開した置き換え先では、後回しにした `initialFields` の参照はフィールドの段階で書かれない（フィールドの段階が既存の Component に書くのは `fields` だけのため）。
- 作り直しと同じ apply で新しく作る Component の `initialFields` のうち、作り直す key への参照そのものは、NOT_CONVERGED で止まると書かれない（作成からフィールドの段階までの間に中断した場合の上流の挙動と同じ）。参照以外の `initialFields` は作成時に書く。
- 保存 ID のある key で、管理 Component が手で消され、同じ index に管理外の同じ型の Component があると、作り直しの対象になって削除されうる（同じセッションでも起きる。上流ではフィールドの上書きにとどまっていた）。保存 ID の無い key は 7.1 で止める。
- 再読込の後、同じ Slot に同じ型の key がほかにあると、中断した作り直しの Component を自動では区別できない（`session-changed` の suggestions は、手で確かめる点を示すだけ）。手で復旧するときは、余分な Component の削除に加えて、その Slot のすべての key の `componentIndex` を `resoloop component list` の位置に合わせる必要がある。
- 次の復旧には、state の手編集が要る: `session-changed`（`supersededId` を消し、`id` が空なら `supersededId` の値にする）、`replacement-unverified` の 2 つ目の手段、作成が中断して ID が空の key が管理外の Component に照合されて止まった場合（7.1。key を state から外す）、同じ型の兄弟がある Slot での `session-changed` からの手の復旧（`componentIndex` を合わせる）、11.1 の prune の削除の応答が失われた場合（key を外す）。上流は `docs/UIX-FEEDBACK.md` で state の直接の修正を一般的な手順として採らないとしているので、提出時に上流の方針を確かめる（10.5）。再読込後の再開（11.2）に対応すれば、`session-changed` の分は不要になる。

## 12. 決定事項

| ID | 扱い | 内容 | 出所 |
|---|---|---|---|
| D-1 | fix | B の挙動は上流 Issue #5 の (a)「apply が自動で作り直す」 | ユーザの決定 |
| D-2 | skip | 上流 Issue #5 へ、今の時点では決定をコメントしない（B を出すときにコメントする） | ユーザの決定 |
| D-3 | fix | B の範囲は「分割」。同じセッションの中の作り直しと再開だけを扱う | ユーザの決定 |
| D-4 | skip | 「全機能を設計から作り直す」「折衷案」は採らない | ユーザの決定 |
| D-5 | skip | 「縮小（identityFields 限定）」は採らない | ユーザの決定 |
| D-6 | fix | index の保存し直しは、独立した修正 A として B より先に出す | 第 1 節 |
| D-7 | fix | fork で先に検証してから、上流にまとめて出す | 第 2 節 |
| D-8 | fix | fork の PR はマージしない。上流でのマージ後に close する | 第 2 節 |
| D-9 | fix | fork の Issue・PR の本文は、最初から英日併記で書く | 第 2 節 |
| D-10 | fix | B の Issue は上流 #5 を参照し、fork には作らない | 第 2 節 |
| D-11 | fix | 上流への提出は 10.5 のとおり | 第 2 節 |
| D-12 | fix | 古い fork PR #5 は、B の PR を出すときにコメントして close する。ブランチは残す | 第 2 節 |
| D-13 | fix | 判定基準とレビューの規則は 10.3 のとおり | 第 2 節 |
| D-14 | fix | 不変条件と apply の手順の骨格 | 第 1 節 |
| D-15 | fix | A が上流の main で再現しなければ、A をやめて I1 は B の中で扱う | 第 2 節 |
| D-16 | skip | fork PR #5 に新しいレビュー修正のラウンドを始めない | 2026-09-30 の判断 |
| D-17 | resolved | 設計の第 3〜6 節 | この Spec で確定 |
| D-18 | fix | この Spec と実装計画は、create-reso-world のブランチ `docs/list-shrink-recreate-split` の PR 1 本にまとめる | ユーザの決定 |
| D-19 | resolved | create-reso-world PR #6（ロックを nuget 0.1.0-preview.15 に） | マージ済み（`eef3620`） |
| D-20 | fix | 第 3 節前半: state、apply の段階、再開の条件に「同じ Slot に宣言」を追加、検証の失敗時の取り消しの範囲、`SaveSlotIndexesAsync` の方式 | ユーザ承認（2026-10-01） |
| D-21 | fix | A の範囲に、文書から外した key（Component と Slot）の照合結果の保存を含める | ユーザ承認（2026-10-01） |
| D-22 | fix | 第 3 節後半: 3 つのコード、`APPLY_RECREATE_INTERRUPTED` への統合と `reason`、plan の表示、アセット移行との統合 | ユーザ承認（2026-10-01） |
| D-23 | fix | 第 4 節: テスト（書き込みの位置ごとの網羅テストを含む） | ユーザ承認（2026-10-01） |
| D-24 | fix | 第 5 節（文書、コミット、PR の本文）と第 6 節（将来の拡張、既知の制限）は推奨案で確定 | ユーザの指示（2026-10-01） |
| D-25 | skip | 削除の応答が失われた直後の再読込（11.1）は、今回は直さない | 第 4 節で承認 |
| D-26 | fix | I4 は、置き換え元が残っている間に限る。置き換え元がすでに無い key の置き換え先は、そのまま参照先にする | 試作の網羅テストで判明（2026-10-01）。置き換え元の削除の応答が失われた後の再開で、置き換え先を参照先にできずに止まっていた |
| D-27 | fix | 再開中に宣言をさらに縮めた場合: 置き換え元がすでに無ければ、置き換え先を置き換え元とする新しい作り直しにする。置き換え元が残っていて、apply が読んだ範囲で置き換え先を参照するものがあれば、変更前に `APPLY_RECREATE_INTERRUPTED`（`reason: declaration-shrank`）で止める（D-22 に reason を 1 つ足す）。参照するものが無ければ止めず、通常の検証と取り消しにする。取り消しの範囲（D-20）は変えない | レビュー R-04 の推奨（案 1・2）を採用（2026-10-01。ユーザの指示「妥当な指摘を吟味して取り入れる」による。ユーザが覆せる）。「参照するものが無ければ止めない」はレビューの案への補正で、取り消しの途中で止めた apply の次の apply が、詰め直された置き換え先を誤って `declaration-shrank` で止めないようにするため（試作で確認） |
| D-28 | fix | 作り直しは state に記録のある key に限る。`--adopt` の初回の apply では作り直さず、その場で更新する（縮小と重なると上流の今の挙動どおり `APPLY_REFERENCE_NOT_RETAINED` で止まり、次の apply で作り直して収束する） | レビュー R-18 の推奨（案 1）を採用（2026-10-01。ユーザが覆せる） |
| D-29 | skip | prune の削除の応答が失われた場合に key を state から外す修正（レビュー R-09 の案 (a)）は、A に含めない。Spec と PR A の本文の範囲を正し、既知の制限に書く（案 (b)。D-25 の範囲の補正）。上流には、提出の後に別の Issue として相談する | レビュー R-09 の推奨（案 (b)）を採用（2026-10-01。ユーザが A に含めたい場合は案 (a) にする） |
| D-30 | fix | `session-changed` の復旧の規則を「宣言より長い方を削除」から「管理 Component の参照が今指している方を残す（candidates の `referencedBy` で示す）。`id` が空なら `supersededId` の値にする」に変える。同じ Slot に同じ型の key がほかにある場合は、自動では区別できないことと手で確かめる点を示す（D-22 で承認した suggestions の規則の変更） | レビュー R-14 の推奨を採用（2026-10-01。ユーザに確認するよう勧められた変更。ユーザが覆せる）。`id` が空の場合の規則は、R-05 の停止（7.1）と両立させるための補正（試作で確認） |
| D-31 | fix | state の手編集を要する復旧手順は、エラーの suggestions と既知の制限（11.4）と PR 本文にだけ書き、上流の文書には上流の回答が出るまで新しく載せない。上流に扱いを尋ねる | レビュー R-17 の推奨を採用（2026-10-01。ユーザが覆せる） |
| D-32 | fix | 不変条件に I5（所有権）と I6（追跡と停止の安全性）を足し、10.3 に重大度の定義と、見直しの条件（同じ不変条件、または同じ問題群の 2 件目）、修正後は差分だけを確かめる規則を足す（D-13・D-14 の変更） | レビュー R-23 の推奨（選択肢 B）を採用（2026-10-01。ユーザが覆せる） |
| D-33 | fix | 検証・取り消し・I4・NOT_CONVERGED の設計（D-14・D-20・D-22・D-26）は残し、PR B の本文で理由（観測はしていないが、詰め直すリストを apply のたびに作り直さないため。値のリストや空の宣言では成功を返し続けるため）を 1〜2 文で説明する | レビュー R-24 の推奨（案 2）を採用（2026-10-01。PR の小ささを優先するなら案 3（取り消しと I4 を外し、段階 5 の後の読み直しだけ残す）を検討できる。ユーザが覆せる） |
| 補正 | fix | I4 の文言を「全件の検証が通る前」「置き換え先どうしの参照を含む」に締める（D-14 の明確化。R-02）。7.5・7.9 の取り消しで戻す記録を「apply の開始時の記録」から「置き換え先を作る直前の記録」に直す（D-22 の補正。R-03）。D-18 に「実装はマージ済みの Spec と計画を参照して始め、設計が変わったら Spec を直す PR を別に出す」を足す（R-28） | レビューで判明（2026-10-01） |
