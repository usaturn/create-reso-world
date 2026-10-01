# リスト縮小時の Component の作り直し（分割案）と Slot の index の保存し直し

- **状態**: 設計確定（2026-10-01）。第 1〜4 節はユーザが節ごとに承認した。第 5・6 節は、ユーザの指示（「途中で止めずに、推奨案で進めてください」）により推奨案で確定した。
- **引き継ぎ元**: usaturn/resoloop#6（この Spec ができるまでの正本）。上流での相談は orange3134/resoloop#5。
- **実装計画**: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`。計画のコードは、上流 `b3a84ae` の使い捨てのコピーで試作して検証した（試作で見つかった設計の補正は D-26）。
- **対象**: fork の usaturn/resoloop（作業ルートは create-reso-world の `external/resoloop`）。分岐元は fork の main `b3a84ae`（上流の `v0.1.0-preview.15` と同じ）。
- **用語**: 「上流」は orange3134/resoloop、「fork」は usaturn/resoloop を指す。「A」は Slot の index を保存し直す修正、「B」はリスト縮小時に Component を作り直す修正を指す。

## 1. 目的

ResoniteLink 0.13.1 には、リストの要素を削除する操作が無い。宣言したリスト型のメンバー（例: `MeshRenderer.Materials`）を短くすると、apply は収束せず、`APPLY_REFERENCE_NOT_RETAINED` で止まる。止まった時点で、ほかの変更はすでに書き込まれている。

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

- **Component の照合（`MatchComponent`）**: 同じセッションなら ID で照合する。ID で見つからないとき、または別のセッションでは、`StableComponentCandidates` で、型、`memberNames`、`identityValues`、参照トポロジ（`referenceSelectors`）の順に候補を絞る。それでも複数残り、identity が無ければ、`componentIndex`（Slot のすべての Component の並びでの位置）で 1 つに決める。それも無い古い state は `TypeOrdinal` で決める。
- **`componentIndex` の決め方**: plan の時点で決まる。既存の Component は実機の並びでの位置、新しい Component は「実機の件数＋その Slot で先に作る件数」。宣言中の key は、apply のたびに Component の段階でこの値を保存し直す。
- **apply の段階**: アセット → Slot → Component（作成） → フィールド → Slot の移動 → prune → 参照の再確認、の順に進む。
  - Component の作成では、`AddComponentAsync` の前に、ID が空の記録を checkpoint する。作成後に ID 付きで checkpoint する。
  - フィールドの段階では、変更があれば `ForgetComponentAssetEvidence` → checkpoint → `SetComponentMembersAsync` の順に進む。Component の移動（`RelocationSource`）は、移動先で作成 → フィールドを書く → 移動元を `RemoveComponentAsync`、の順。
  - **prune も移動元の削除も、同じ Slot に残る key の `componentIndex` を保存し直さない。**
  - 参照の再確認: 削除などの後、参照を含む宣言済みフィールドを読み直す。一致しなければ書き直して再確認し、それでも一致しなければ `APPLY_REFERENCE_NOT_RETAINED` を出す。リストが縮まないときの症状はこれである。
- **`Checkpoint`**: state の `sessionId` を現在のセッションにして保存する。
- **削除計画（`BuildDeletionPlans`）**: 文書から外した key を、同じセッションなら ID だけで、別のセッションなら Slot はパス、Component は `MatchComponent` で照合する。照合の結果は state に保存しない。
- **state の書き出し**: `JsonSerializerOptions` に null を省く設定が無く、null の値も `"identityValues": null` のように書き出す。読み込みは未知のプロパティを無視する。

### 3.2 ResoniteLink のリスト

- Resonite `2026.9.18.82`、ResoniteLink `0.13.1` の実機で、テスト用の Slot を使って次を観測した。
  - `[A,B]` の `MeshRenderer.Materials` に `[A]` を送っても `[A,B]` のまま。
  - `[]` を送っても変わらない。
  - その後 `[B]` を送ると `[B,B]` になる。
- 上流が固定している `YellowDogMan.ResoniteLink 0.13.1` のメッセージ型に、リストの要素を削除する操作は無い。公式ドキュメントにも、短いリストの扱いは書かれていない。

### 3.3 使い捨てのテストで確かめたこと（2026-10-01、上流 `b3a84ae` のコピー）

リポジトリの外で、偽クライアントを使って確かめた。テストのコードは残していない。

1. **A の再現**: identityFields の無い同じ型の Component 3 つ（key `t1`〜`t3`）から `t1` を prune した。state には `t2` が index 1、`t3` が index 2 のまま残った（実機の位置は 0 と 1）。ワールドを再読込して apply すると、`STABLE_COMPONENT_AMBIGUOUS` で止まった。
2. **文書から外した key の照合結果（Component）**: `t3` を文書から外した（prune はしない）。再読込直後の `plan --prune` は `t3` を削除対象に挙げた（1 件）。しかし同じセッションで apply を 1 回実行すると、次の `plan --prune` では 0 件になった。state の `t3` の ID は再読込前のまま残り、`sessionId` だけが新しくなったため、ID で探して見つからなくなった。
3. **同じ問題（Slot）**: Slot とその Component を文書から外し、同じ手順で確かめた。削除対象は 2 件から 0 件になった。

### 3.4 手元のデータ（create-reso-world の apply 文書 29 件、`tmp/` を除く）

- 参照のリストを持つ Component は `MeshRenderer`（`Materials`）だけで、2,256 個ある。
- 同じ Slot に同じ型の `MeshRenderer` が複数ある例は 0 件。`MeshRenderer` どうしの参照も 0 件。
- `identityFields` を使っているのは slum02 の 13 か所だけ。

### 3.5 fork PR #5（`555338e`）から流用するもの

fork PR #5 は上流の最新と衝突し、レビュー修正も打ち切っている（usaturn/create-reso-world#5）。B は rebase せず、上流の main から作り直す。流用するのは考え方と文言だけで、次のものに限る。

- 作成 → 参照の張り直し → 置き換え元の削除、という順序
- `supersededId` という名前
- 停止コードの考え方（名前は 7.7 で決め直した）
- 偽クライアントに「`Materials` の末尾の要素が残る」挙動を足すこと
- 文書の文言（作り直すと、`initialFields` と宣言していないメンバーが既定値に戻る）

## 4. 範囲

### 4.1 範囲内

- **A**
  - Component を削除した後に、その Slot の key の `componentIndex` を保存し直す（`SaveSlotIndexes`）。
  - 削除計画が文書から外した key（Component と Slot）に照合した結果を、state に保存する。
- **B（分割の範囲）**
  - 同じセッションの中での作り直しと、作り直しの途中からの再開。
  - 作り直しの途中でセッションが変わった場合などは、変更前に止める。

### 4.2 範囲外

次は 11 章に記録するだけで、実装しない。

- 作り直しの途中で中断し、ワールドを再読込した後の再開
- syncObject の中のリスト
- runtime が非同期にリストを詰め直す場合
- Component の削除の応答が失われ、次の apply が成功する前にワールドを再読込した場合（修正前からある問題）
- Component の移動が移動先の作成後に中断すると、移動元が残る問題（上流の既存の設計課題）

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
- **I4（取り消しで参照を壊さない）**: 置き換え元が残っている間は、検証を通る前の置き換え先を指す参照を、apply は書かない。置き換え元がすでに無い key の置き換え先は、検証も取り消しもしないので、そのまま参照先にする（12 章の D-26）。

## 6. 設計 A: index の保存し直しと、文書から外した key の照合結果の保存

### 6.1 `SaveSlotIndexes`

- **入力**: `PreparedApply`、Slot の stable key、Slot の ID。
- **処理**: `GetSlotAsync(slotId, 0, false)` で Slot を読み直し、Component の ID の並びを得る。state の Component のうち `slotKey` がその Slot のものについて、保存している `id` が並びの中にあれば、その位置を `componentIndex` に保存する。見つからない key は変えない。
- **保存**: メモリ上の state だけを変える。呼び出し側が直後の checkpoint で保存する。
- **呼び出し場所**:
  - A: Component の移動元を削除した後（移動元の Slot）、prune で Component を削除した後（その Component の Slot）
  - B: 置き換え元を削除した後、置き換え先を取り消した後（7.5）
- **将来の拡張への備え**: 段階に依存しない形にし、どの checkpoint の前からでも呼べるようにする（11 章）。
- **費用**: 削除 1 回につき、Component のデータを含まない Slot の読み取りが 1 回増える。
- **実装のメモ**: 移動元の Slot の key と ID は、plan の時点で `FindStateSlot` が得たものを `ComponentRuntime` に持たせる。prune の Component 削除には、`DeletionRuntime` に Slot の key と ID を持たせる。

### 6.2 文書から外した key の照合結果の保存

- **Slot**: 削除計画が文書から外した Slot の key に Slot を照合したら、その ID を state に保存する（ID が変わる場合だけ）。
- **Component**: 削除計画が文書から外した Component の key に Component を照合したら、その ID と、Slot の並びでの位置を state に保存する。
- **保存の時期**: `PrepareAsync` の中でメモリ上の state を変える。`plan`・`diff`・`test` は state を保存しないので、影響しない。apply では最初の checkpoint で保存される。変更前の検査（所有権の重複など）で止まった場合は、何も保存されない。
- **安全性**: 保存するのは、同じ apply の削除計画（と `--prune`）がすでに使っている照合結果である。同じ Component や Slot を複数の key が指していれば、`APPLY_COMPONENT_OWNERSHIP_CONFLICT` または `APPLY_SLOT_OWNERSHIP_CONFLICT` で、保存より前に止まる。
- **上流の方針は変えない**: 同じセッションでは ID だけで照合する（パスで探し直さない）。パスで探し直すと、同じパスに後から作られた別の Slot を削除しかねないためである。
- **修正前の state**: 修正前の apply で、古い ID のまま同じセッションになった key は、この修正でも同じセッションの間は見つからない。次にセッションが変わったときに照合し直され、保存される。

### 6.3 I1 が成り立つ理由

- **宣言中の key**: apply のたびに、plan の時点の位置を保存し直す（上流の挙動）。そのうえで、削除のたびに `SaveSlotIndexes` が保存し直す。
- **文書から外した key**: 6.2 で照合結果を保存し、削除のたびに `SaveSlotIndexes` が保存し直す。
- **この apply で作った key**: plan の時点の位置（作成時点で正しい）を保存し、その後の削除のたびに `SaveSlotIndexes` が保存し直す。
- **途中の作り直しがある Slot**: I1 の対象外。完了時（7.3 の段階 5）に保存し直す。

## 7. 設計 B: 作り直し

### 7.1 検出（plan）

- **対象**: 既存の管理 Component のうち、通常どおり照合でき、移動中でも途中の作り直しでもないもの。
- **判定**: `fields` に宣言した値が JSON の配列で、観測したメンバーが kind `list` で、その要素数が宣言より多ければ、その Component を作り直す。`initialFields` は作成時にしか書かないので、判定に使わない。
- **作り直しにした Component の扱い**: `Existing` を空にして作成の対象とし、観測した Component を `Superseded`（置き換え元）として持つ。理由の文言（7.8）を付ける。
- **対象外**: リストが長くなる場合と長さが変わらない場合は、従来どおりその場で更新する。syncObject の中のリストは従来どおり。移動中の Component は、移動先で新しく作るので作り直しは要らない。

### 7.2 state

- `ApplyStateComponent` に、省略できる `SupersededId`（string?）を追加する。`[property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]` を付け、null のときは書かない。
- `CreateComponentState` は、作り直しの間、`SupersededId` を引き継ぐ。値を消すのは置き換え元の削除の段階（7.3 の段階 5）と、取り消し（7.5）だけ。
- `schemaVersion` は 2 のまま変えない。古い state はそのまま読める。
- 古い版の resoloop は `supersededId` を無視する。途中の作り直しがある state を古い版で apply することは対応しない（既知の制限、11 章）。

### 7.3 apply の段階

上流の段階に、★の 2 つを加える。括弧内に、第 1 節の手順の番号を示す。

1. **アセット、Slot**: 従来どおり。
2. **Component の段階（作成）**: 置き換え先を作る。
   - 作成前の checkpoint で、`id: ""`、`supersededId: 置き換え元の ID`、`assetFields: {}` を保存する（第 1 節の手順 2）。
   - `AddComponentAsync` で作成し、`id: 新しい ID` を保存する（手順 3）。`supersededId` は残す。
   - 置き換え元が残っている間、置き換え先は検証を通るまで参照先にしない（I4）。この段階で後から作るほかの Component の初期値には、置き換え先への参照を入れない。そうした Component は参照を含めずに作り、参照はフィールドの段階で書く。
3. **★作り直しの検証**: 作り直す key ごとに、文書の順で次を行う（手順 4）。
   - 作成時に書けなかったフィールド（`initialFields` と `fields`）があれば、`ForgetComponentAssetEvidence` → checkpoint → `SetComponentMembersAsync` の順に書く。
   - 置き換え先を読み直し、宣言したリストのうち、宣言より要素数が多いものがあれば失敗とする。
   - すべての key を確かめた後、失敗があれば 7.5 の取り消しを行って止める。失敗が無ければ、書いた値を作成時の値として扱い、フィールドの段階で書き直さない。
   - 置き換え元がすでに無い key（前の apply で削除が済み、その後の checkpoint だけが失われたもの）は、検証しない。段階 5 で記録を片付けるだけにする。
4. **フィールドの段階**: 従来どおり。管理 Component の宣言済みの参照は、ここで置き換え先の ID に張り替わる（手順 5）。移動元を削除した後には `SaveSlotIndexes` を呼ぶ（A）。
5. **★置き換え元の削除**: 作り直す key ごとに、次を行い、1 回の checkpoint で保存する（手順 6）。
   - 置き換え元が残っていれば `RemoveComponentAsync` で削除する。
   - その Slot に `SaveSlotIndexes` を呼ぶ。
   - `supersededId` を消す。
6. **Slot の移動、prune、参照の再確認**: 従来どおり。prune で Component を削除した後には `SaveSlotIndexes` を呼ぶ（A）。

作り直しは件数として、Component の作成 1 件と削除 1 件に数える（`ComponentsAdded`・`ComponentsDeleted`）。進捗の表示には、置き換え元の削除を加える（置き換え先の作成は、通常の作成として表示される）。

### 7.4 再開（I2・I3）

state に `supersededId` がある key は、次のように扱う。位置による照合（`StableComponentCandidates`）は使わない。

- **止める条件（変更前）**
  - 同じセッションでない → `APPLY_RECREATE_INTERRUPTED`（`reason: session-changed`）。`PrepareAsync` の中で、state を読み込み、接続のセッションを確かめた直後に判定する。`plan`・`diff`・`test` も同じく止まる。止まったときは checkpoint しないので、state の `sessionId` は変わらず、何度実行しても同じく止まる。
  - その key が同じ Slot に宣言されていない（文書から外した、別の Slot に移した）→ `APPLY_RECREATE_INTERRUPTED`（`reason: key-not-declared`）。宣言された key がそろった後（`BuildComponentPlans` の後）に判定する。`migrateFrom` で key の名前を変えた場合は、記録ごと移るので、移った先の key が同じ Slot に宣言されていれば再開する。
- **照合**
  - 置き換え元: Slot の Component のうち、ID が `supersededId` のもの。無ければ削除済みとして扱う。
  - 置き換え先: Slot の Component のうち、ID が state の `id` のもの（置き換え元は除く）。
  - 置き換え先が無い場合は I3 に従う。「どの key にも結び付いていない」とは、宣言中の key の照合結果、移動元、置き換え元、削除計画の照合結果のどれにも含まれないことをいう。この判定は削除計画を作った後に行う。該当する Component が無ければ、置き換え先を新しく作る（段階 2 の手順を、`supersededId` を保ったまま行う）。1 つでもあれば `APPLY_RECREATE_INTERRUPTED`（`reason: replacement-unverified`）で止める。
- **再開した key の検証**: 置き換え元が残っていれば、段階 3 で新しく作った置き換え先と同じく検証する。

### 7.5 検証の失敗と取り消し

- **取り消す対象**: 検証に失敗した key と、この apply で置き換え先を作った key のすべて。後者は検証を通ったものも含む。置き換え元がすでに無い key は、戻す先が無いので取り消さない。
  - この apply で作った置き換え先は、I4 によりまだどこからも参照されていないので、削除しても参照は壊れない。
  - 前の apply から再開した置き換え先は、検証を通れば残す。前の apply で参照の張り替えが済んでいる可能性があるためである。次の、同じセッションの apply で再開する。
- **取り消しの手順**: 対象の key ごとに次を行い、最後に 1 回 checkpoint してから `APPLY_LIST_SHRINK_NOT_CONVERGED` で止める。
  1. 置き換え先が残っていれば削除する。
  2. state の記録を戻す。この apply で作り直しを始めた key は、apply の開始時の記録（plan の時点で控えておく）に戻す。再開した key は、`id` を `supersededId` の値に戻し、`supersededId` を消し、`assetFields` を空（根拠なし）にする。
  3. その Slot に `SaveSlotIndexes` を呼ぶ。
- **取り消しの途中で失敗した場合**: その時点のエラーで止まる。state には `supersededId` が残るので、次の同じセッションの apply で再開し、検証と取り消しをやり直す。

### 7.6 変更前の検査

`PrepareAsync` の中で、変更の前に次を行う。

- **所有権**: `ValidateComponentOwnership` の対象に、置き換え元（種類 `superseded`）を加える。宣言中の key、移動元、削除計画と同じ Component を指していれば、`APPLY_COMPONENT_OWNERSHIP_CONFLICT` で止める。
- **中断した作り直し**: 7.4 の止める条件と I3。
- **参照（`APPLY_LIST_SHRINK_REFERENCED`）**: 置き換え元が残っている作り直しがあれば、apply がすでに読んだ snapshot（`SnapshotSlots`）を調べる。置き換え元、またはそのメンバー（入れ子と要素を含む）を参照しているものが、次のどれでもなければ止める。
  - 管理 Component の宣言済みフィールドで、値に `$component:` などの参照の指定を含むもの（apply が張り替える）
  - この apply で削除する Component（置き換え元、移動元）
- 調べる範囲が、apply の読んだ snapshot に限られることは、エラーの suggestions と文書に書く。

### 7.7 エラーコード

| コード | 終了コード | 止まる時点 | ワールドの状態 |
|---|---|---|---|
| `APPLY_LIST_SHRINK_REFERENCED` | 6（`ValidationFailed`） | 計画（変更前） | 変更なし |
| `APPLY_RECREATE_INTERRUPTED` | 6（`ValidationFailed`） | 計画（変更前） | 変更なし |
| `APPLY_LIST_SHRINK_NOT_CONVERGED` | 7（`OperationFailed`） | 作り直しの検証 | 置き換え先は取り消し済み。それより前の段階の変更は残る |

- 終了コードは既存のコードに合わせる。変更前に止まるものは `APPLY_COMPONENT_OWNERSHIP_CONFLICT` と同じく 6、実機の挙動で止まるものは `APPLY_REFERENCE_NOT_RETAINED` と同じく 7。
- 第 1 節で決めた `APPLY_RECREATE_INTERRUPTED_ACROSS_SESSION` は、`APPLY_RECREATE_INTERRUPTED` にまとめ、`reason` で区別する（第 3 節後半で承認）。3 つとも「途中の作り直しを自動では再開できないので、変更前に止める」点が同じで、違うのは復旧手順だけである。
- **context**
  - REFERENCED: `stateFile`、`recreates`（key、置き換え元の ID、理由）、`references`（参照先の key と ID、参照元の ID・型・メンバー、Slot の ID とパス）
  - INTERRUPTED: `reason`、`stateFile`、`componentKey`、`slotKey`、`slotPath`、`type`、`supersededId`、`savedId`、`candidates`（同じ型の候補ごとの ID と、宣言したリストのメンバーごとの要素数）
  - NOT_CONVERGED: `failures`（key、メンバー、宣言と実機の要素数）、`undone`（取り消した key）。apply の通常の context（`stateFile`、件数、`recovery`）も付く。
- **メッセージと suggestions の案**（英文。実装で文言を整える）
  - REFERENCED: "A declared list member must shrink, which requires recreating its Component, but something other than a declared managed reference points at the Component or its members. No mutations were performed."
    - "Declare the referencing member as a managed field with a $component/$member selector so apply can re-point it, or remove the reference."
    - "Only the snapshots this apply read were checked. Inspect other references to the Component before applying."
  - INTERRUPTED（`session-changed`）: "A list-shrink recreate of '{key}' was interrupted and the world session changed, so the replaced Component and its replacement can no longer be told apart by ID. No mutations were performed."
    - "Keep exactly one same-type Component for the key, preferably removing the one whose list is longer than declared, with 'resoloop component remove ID --yes'. Then delete supersededId from components.{key} in the state file and re-run apply."
  - INTERRUPTED（`key-not-declared`）: "A list-shrink recreate of '{key}' was interrupted, and the document no longer declares the key on its Slot. No mutations were performed."
    - "Declare the key again on the same Slot and re-run apply in this session to finish the recreate."
    - "Or keep exactly one same-type Component for the key, remove the other with 'resoloop component remove ID --yes', and delete supersededId from components.{key} in the state file."
  - INTERRUPTED（`replacement-unverified`）: "A list-shrink recreate of '{key}' was interrupted before its replacement ID was saved, and the Slot holds a same-type Component that no key owns. No mutations were performed."
    - "If a candidate's lists match the declaration, it is most likely the replacement that the interrupted apply created. Remove it with 'resoloop component remove ID --yes' and re-run apply; apply creates the replacement again."
    - "If every candidate is unrelated content, set components.{key}.id back to its supersededId, delete supersededId, and re-run apply to start the recreate again."
  - NOT_CONVERGED: "The runtime kept a list longer than declared on the replacement Component, so recreating it cannot converge. The replacement was removed and the original Component is unchanged."
    - "Declare the list length that the runtime keeps, or find what refills the list."
    - "Re-run apply after changing the declaration. The undone keys have no recreate in progress."

### 7.8 plan の表示

- Component の操作に `recreate` を追加する。差分（`diffs`）は update と同じ形で出す。新しく作り直す場合は、置き換え元の観測と比べる。
- **理由の文言**
  - 新しく作り直す場合: "list member '{member}' shrinks from {n} to {m} elements; ResoniteLink cannot remove list elements, so apply replaces the Component (initialFields and undeclared members return to their defaults)"。メンバーが複数あれば、メンバーごとの部分を "; " でつなぐ。
  - 再開して、置き換え先がある場合: "resumes an interrupted recreate: removes the replaced Component '{id}' after managed references point at the replacement"
  - 再開して、置き換え先が無い場合: "resumes an interrupted recreate: creates the replacement, then removes the replaced Component '{id}'"
  - 再開して、置き換え元がすでに無い場合: "resumes an interrupted recreate: the replaced Component is already removed; apply saves the final Component indexes"
- **サマリーの件数**: `recreate` は、`relocate` と同じく `updates` に数える。件数の項目は増やさない。
- **フィルター**: `--creates-only`・`--deletes-only` には出さない（prune による削除ではない）。`--changes-only` には出る。

### 7.9 アセット移行（`f46bdd0`）との統合

1. 置き換え先の `assetFields` は、作成前の checkpoint で空にする（上流で新しく作る Component と同じ）。フィールドを書いた後に、宣言から記録する。
2. `DetectSavedAssetMigrations` は、新しく作り直す key について置き換え元を観測する（`Existing ?? RelocationSource ?? Superseded`）。これが無いと、resdb へ移行したアセットを使うのが作り直す Component だけの場合に、`local://` の URL を書き戻す（fork 版の `d615eeb` で見つかった問題）。再開した置き換え先は、フィールドを書くまで `assetFields` が空なので、根拠として使われない（上流の規則どおり）。
3. 検証の段階で書くときも、`ForgetComponentAssetEvidence` → checkpoint → 書き込み、の順にする。
4. `assetFields` の無い古い state で作り直す場合は、置き換え元の観測を確かめられないので、上流と同じく `APPLY_ASSET_MIGRATION_UNVERIFIED` で変更前に止まる。
5. 取り消し（7.5）では、この apply で作り直しを始めた key は apply の開始時の記録に戻し、再開した key は空（根拠なし）にする。

### 7.10 既存の挙動との関係

- `APPLY_REFERENCE_NOT_RETAINED` は、リストの縮小以外の原因（ほかの driver が参照を握っている場合など）では従来どおり出る。
- Component の移動では、移動元の削除を `--prune` も `--yes` も無しで行う（上流の前例）。作り直しも同じく、置き換え元の削除を `--prune` と `--yes` 無しで行う。上流の `AGENTS.md` の「CLI delete/remove must retain explicit --yes」は、削除そのものを目的とするコマンド（`slot delete`、`component remove`、`apply --prune`）についての規則である。作り直しは移動と同じく、宣言に収束させるための置き換えであり、plan の `recreate` の理由で置き換えることを事前に示す。
- `ApplyResult` に項目は増やさない。

## 8. テスト

### 8.1 偽クライアントの拡張（`tests/RLoop.Tests/ApplyWorkflowTests.cs` の `FakeResoniteClient`）

1. **参照のリスト**: 指定したメンバー（例: 型 `Test.Renderer` の `Materials`）を、参照を要素とする kind `list` で持つ。短いリストを送ると、先頭だけを置き換えて末尾を残す（`[A,B]` に `[A]` は `[A,B]`、`[]` は変化なし、続けて `[B]` は `[B,B]`）。型の説明（`DescribeComponentTypeAsync`）も合わせる。
2. **書き込みの失敗の注入**: 書き込みの位置で指定する方式にそろえる。既存の `FailOnWrite`（反映する前に失敗）に加え、`LoseResponseOnWrite`（反映してから応答を失う）を足す。Slot・Component の作成と削除、フィールドの書き込みのすべてを対象にする。
3. **リストの詰め直し**: 書き込んだリストを、実機が指定の長さまで詰め直す設定（`RefillListsTo`。NOT_CONVERGED の確認用）。
4. **特定の Component の削除の失敗**: 指定した Component の削除が、反映前に失敗する設定（`FailRemovingComponent`。置き換え元の削除で止める確認用）。

### 8.2 網羅テスト（B の中心）

- **シナリオ**
  - S1: Component を 1 つ作り直す。それを参照する管理 Component が 1 つある。
  - S2: 同じ Slot で 2 つを作り直す。その Slot から別の Component を移動する。文書から外した key が 1 つ残っている。index の保存が重なる場合を確かめる。
- **手順**: 書き込みの位置 k を 1 から最後まで、2 つの失敗の仕方（反映前に失敗、反映後に応答を失う）で止める。そのたびに、次の 2 つを確かめる。
  - 同じセッションで apply し直す → 収束するか、`replacement-unverified` で変更前に止まる。止まった場合は suggestions の復旧手順（候補の削除）を行い、その後に収束することを確かめる。
  - ワールドを再読込してから apply する → state に `supersededId` があれば、書き込み 0 件のまま `session-changed` で止まる。
- **収束の判定（共通の確認関数）**
  - Slot に、その型の Component が 1 つだけあり、リストが宣言どおり。
  - 管理 Component の参照が、その Component を指している。
  - state に `supersededId` が無く、Slot のすべての key の `componentIndex` が実機の位置と一致する（I1）。
  - もう一度 apply すると書き込みが 0 件。ワールドを再読込してからの apply も、書き込みが 0 件。
- **ねらい**: 前回の手戻りの原因の 1 つ（シナリオを固定したテスト）を避け、どこで止まっても誤った状態のまま黙って進まないことを確かめる。

### 8.3 個別のテスト（B）

- リストが長くなる場合・変わらない場合は、従来どおりその場で更新する。syncObject の中のリスト、移動中の Component は作り直さない。
- REFERENCED: 管理外の Component からの参照があると、変更前に止まる。宣言済みの参照は張り替わる。
- `key-not-declared`: 作り直しの途中で key を外す、または別の Slot に移すと止まる。
- NOT_CONVERGED: 置き換え先を取り消し、元の Component・state・参照が変わらない。この apply で作った置き換え先は、検証を通ったものも取り消す。前の apply から再開した置き換え先は、検証を通れば残る。同じ apply で作った Component が、取り消した置き換え先を指さない（I4）。
- plan: `recreate` の理由と件数。置き換え元が所有権の検査に含まれる。
- アセット移行: 移行済みのアセットを使う Component を作り直しても `local://` に戻らない。`assetFields` の無い古い state は `APPLY_ASSET_MIGRATION_UNVERIFIED` で止まる。
- identityFields を持つ Component を作り直しても、identity の値が state に残り、再読込後も結び付く。
- 管理 Component が `$member:` で作り直す Component のメンバーを参照していれば、置き換え先のメンバーに張り替わる。
- 途中の作り直しがある state で `plan` を実行すると、再開の内容を理由に示し、ワールドにも state にも書き込まない。
- 同じ apply で、同じ Slot の prune と作り直しが起きても、index が実機の位置と一致する。
- 作り直すと、`initialFields` が宣言の初期値に戻る（文書どおりの挙動であることを固定する）。

### 8.4 A のテスト

- 同じ型で identityFields の無い 3 つから 1 つを prune、または移動 → 再読込 → apply が書き込み 0 件で収束する（修正前は `STABLE_COMPONENT_AMBIGUOUS`）。
- 文書から外した key が残る Slot で、ほかの Component を削除 → 再読込 → 削除計画にその key が 1 回だけ出て、所有権の衝突が起きない。
- 再読込 → apply（prune なし） → 同じセッションの `plan --prune` が、文書から外した Component と Slot を挙げ続ける（3.3 の 2・3。修正前は 0 件）。
- 削除の直後に応答を失った場合 → 同じセッションの次の apply（削除なし）で index が直り、その後に再読込しても正しく結び付く。

### 8.5 修正前との比較

上流 PR #4 と同じく、使い捨ての worktree で `src/` だけを分岐元に戻し、追加したテストが失敗することを確かめる。分岐元は、A では main、B では A のブランチ。

## 9. 文書

上流の `AGENTS.md` は、CLI の挙動を変えたら README と `skills/codex/*/SKILL.md` も更新するよう求めている。

- **A**: `docs/DECLARATIVE.md` に 2 点を追記する。
  - Component を削除・移動した後に、同じ Slot に残る key の index も保存し直す。
  - 再読込の後も、文書から外した key は削除計画が照合した ID を保存するので、同じセッションの後の `--deletes-only` や `--prune` でも対象に残る。
- **B**
  - `README.md` と `README_JA.md`: アセット移行の注記と同じ程度の短い段落。リストを短くすると Component を作り直すこと、既定値に戻ること、3 つのコード。
  - `README-DETAILS.md`: `initialFields` の説明に、作り直すと初期値に戻ることを足す。plan の `recreate`。
  - `docs/DECLARATIVE.md`: `initialFields` の注意。「Diff、rename、prune、recovery」の節に、`recreate`、`--prune` なしで置き換え元を削除すること、3 つのコードと復旧手順。
  - `skills/codex/resonite-build/SKILL.md`: `initialFields` の注意と、plan の `recreate` を確認すること。
  - `skills/codex/resonite-debug/SKILL.md`: 3 つのコードの意味と復旧手順。

## 10. 作業の流れ、PR、判定基準

### 10.1 A

1. fork の main から使い捨ての worktree を作り、8.4 の最初のテストを書いて失敗を確かめる。再現しなければユーザに報告し、A をやめて I1 は B の中だけで扱う（D-15）。
2. fork に A の Issue を出す（英日併記。再現手順と 3.3 の結果を載せる）。
3. main から `fix/slot-index-after-removal` を分岐し、6 章を実装する。fork の main 向けに PR を出す。

### 10.2 B

1. A のブランチから `fix/list-shrink-recreate-split` を分岐し、7 章を実装する。A のブランチ向けに PR を出す。
2. Issue は上流の orange3134/resoloop#5 を参照する（fork に B の Issue は作らない）。
3. このとき、古い fork PR #5 に「作り直した」とコメントして close する。ブランチ `fix/list-shrink-recreate` は残す。

### 10.3 判定基準とレビュー

- **テスト**: `dotnet test ResoLoop.slnx` がすべて成功する。8 章のテストを含む。
- **実機**: リストが縮むケース（瓦礫の `Materials` が 4 から 3 など）で apply が収束する。完了後にワールドを保存・再読込し、次の apply の書き込みが 0 件になる。実機の操作は、上流の `AGENTS.md` の安全規則に従い、`ResoLoop_Test*` の Slot の下で行う。ユーザのワールドに対する apply は、ユーザの明示的な指示があるときだけ行う。
- **レビュー**: 前回の手戻りを繰り返さないため、次の規則で進める。
  - レビューは PR ごとに 1 ラウンドを基本にする。
  - 修正するのは、現行の HEAD で再現する High と Medium の指摘だけ。Low はまとめてユーザに判断を仰ぐ。
  - 同じ不変条件が 2 回破れたら、修正を止めて設計を見直す。

### 10.4 コミットと PR の本文

- **コミット**: A は 2 件（index の保存し直し／文書から外した key の照合結果の保存）、B は 2 件（実装とテスト／文書）。件名は英文の命令形とし、必要に応じて `Refs orange3134/resoloop#5` を付ける。Claude Code が書くコミットの末尾には `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` を付ける。
- **レビュー修正**: fork でのレビュー修正は同じブランチに積む。`*-review-fixes` のような別のブランチや PR は作らない。上流に出す前に上の構成へまとめ直す。force push するのは、新しく作るこの 2 本のブランチだけにする。
- **本文**: fork の Issue・PR の本文は、上流にそのまま流用できるよう、最初から英日併記で書く。Summary / Root cause / Verification の構成にする。B の PR には「A を先にマージ」と書く。
- **fork の PR はマージしない**（D-8）。上流でマージされた後に close する。

### 10.5 上流への提出（D-11）

判定基準を満たしたら、文面をユーザに見せて確認を取ってから、次を一度に出す。

- A の Issue（fork の Issue を流用）
- PR A（main 向け）
- PR B（A のコミットを含めて main 向け。「A を先にマージ」と明記）
- 上流 Issue #5 へのコメント（B を出したことと、選択肢 (a) を選んだこと）

上流でマージ・リリースされたら、create-reso-world のロックを新しい版に切り替え、fork の PR を close し、各プロジェクトで `resoloop skills sync` を実行する。

## 11. 将来の拡張（再読込後の再開）と既知の制限

### 11.1 今は止めているケース

- `APPLY_RECREATE_INTERRUPTED` の 3 つの理由（`session-changed`、`key-not-declared`、`replacement-unverified`）
- Component の削除の応答が失われ、次の apply が成功する前にワールドを再読込した場合。index が古いまま残り、再読込後の照合が `STABLE_COMPONENT_AMBIGUOUS` などで止まるか、誤った Component に結び付くことがある。修正前からある問題で、A が直すのは削除が成功した場合だけ。

### 11.2 再読込後の再開に対応するときに変える箇所

- 作り直しの途中の checkpoint でも `SaveSlotIndexes` を呼ぶ（6.1 で、どこからでも呼べる形にしてある）。
- 置き換え元と置き換え先を、ID なしで見分けるための記録を state に残す（例: 置き換え先に書いたリストの要素数と参照先、置き換え元の位置）。
- I3 の判定に、その記録を使う。
- 削除の予定を、削除の前に state に記録する。11.1 の 2 つ目と、Component の移動が中断すると移動元が残る問題（3.1）も、この記録でまとめて扱える見込み。

### 11.3 そのときに必要な網羅テスト

- 書き込みの位置ごとに、ワールドの再読込を挟む。
- identityFields の有無、同じ型の兄弟の有無を組み合わせる。

### 11.4 そのほかの既知の制限

- 途中の作り直しがある state を、古い版の resoloop で apply することは対応しない（7.2）。
- `APPLY_LIST_SHRINK_REFERENCED` が調べるのは、apply の読んだ snapshot の範囲だけ（7.6）。
- runtime が非同期にリストを詰め直す場合、検証の時点では気付けない。次の apply でもう一度作り直しになる。

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
| D-20 | fix | 第 3 節前半: state、apply の段階、再開の条件に「同じ Slot に宣言」を追加、検証の失敗時の取り消しの範囲、`SaveSlotIndexes` の方式 | ユーザ承認（2026-10-01） |
| D-21 | fix | A の範囲に、文書から外した key（Component と Slot）の照合結果の保存を含める | ユーザ承認（2026-10-01） |
| D-22 | fix | 第 3 節後半: 3 つのコード、`APPLY_RECREATE_INTERRUPTED` への統合と `reason`、plan の表示、アセット移行との統合 | ユーザ承認（2026-10-01） |
| D-23 | fix | 第 4 節: テスト（書き込みの位置ごとの網羅テストを含む） | ユーザ承認（2026-10-01） |
| D-24 | fix | 第 5 節（文書、コミット、PR の本文）と第 6 節（将来の拡張、既知の制限）は推奨案で確定 | ユーザの指示（2026-10-01） |
| D-25 | skip | 削除の応答が失われた直後の再読込（11.1）は、今回は直さない | 第 4 節で承認 |
| D-26 | fix | I4 は、置き換え元が残っている間に限る。置き換え元がすでに無い key の置き換え先は、そのまま参照先にする | 試作の網羅テストで判明（2026-10-01）。置き換え元の削除の応答が失われた後の再開で、置き換え先を参照先にできずに止まっていた |
