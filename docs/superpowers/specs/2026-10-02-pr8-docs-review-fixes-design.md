# PR #8 ドキュメントレビューの指摘選別と修正計画

- **状態**: 承認済み（2026-10-02）
- **対象**: PR #8（`docs/list-shrink-recreate-split`）、現行 HEAD `b851852385b27299f02d4cfcb526295b75f0cd34`
- **入力**: `reviews/#8-docs-list-shrink-recreate-split/`（SWE-2-Max.md、deepseek-deepseek-v4.1-flash.md、qwen3.8-max.md、xai-grok-4.7.md。4 件とも対象 HEAD は `b851852385b2` で現行 HEAD と同一）
- **brainstorming の経路判定**: **bounded**（既存文書への限定的な修正と PR 本文の更新のみ。新規サブシステム・インターフェース変更なし）
- **検証方法の前提**: 対象は文書のみの PR で実行対象のコードを含まないため、「現行 HEAD での再現」は `git show <HEAD>:<path>` のコミット済み blob と、上流 `b3a84ae`（fork `external/resoloop` のコミット済み blob）との照合・計画コードの追跡で行った。working tree のファイルは検証根拠に使っていない

## 分類の集計

| 区分 | 件数（重複統合後） |
|---|---|
| 解消済み | 0 |
| 対応する | 6 |
| 判断保留 | 0 |
| 対応しない | 2 |

現行 HEAD が全レビューの対象 HEAD と同一のため、レビュー後の修正で消えた指摘は無い。

## 対応する（6 件）

### RFP-01: PR #8 本文の検証数値と決定事項の範囲が古い (b)

- **出典**: deepseek L-1、qwen3.8-max L-1（同一指摘）
- **現状**: `gh pr view 8` の本文が「`RLoop.Tests` 361 件」「実装の要点 13 か所」「回帰を固定するテスト 4 件」「決定事項（D-1〜D-26）」のまま。現行 HEAD の文書は 394 件・33 か所・7 件・D-1〜D-33（計画 18-20 行・3980 行、Spec 12 章 481 行の D-33、review-fixes 記録 5 章）
- **修正方針**: `gh pr edit 8 --body-file` で本文を更新する（361→396〔本ラウンドで計画にテストを 2 件追加した後の最終期待値。再生時の記録は 394 件〕、13→33、4→7、D-1〜D-26→D-1〜D-33、レビュー R-01〜R-65 と本ラウンドの反映済みである旨）。あわせて Spec 10.4（396 行）の「本文の件数は直前の実行結果に合わせ、レビュー修正の後は `gh pr edit --body-file` で更新する」が fork の PR のみを対象にしているので、このリポジトリの PR も対象に含める 1 行を足し、今回の更新漏れの再発を防ぐ（両レビューの推奨対応）
- **検証方法**: 更新後に `gh pr view 8 --json body` で 4 箇所の数値が現行文書と一致することを確認。Spec 10.4 の差分を目視確認

### RFP-02: Spec 冒頭の決定事項の範囲が D-33 を欠く (b)

- **出典**: deepseek I-1、qwen3.8-max I-1、xai-grok-4.7 I-1（同一指摘）
- **現状**: `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md` 3 行目が「レビューの推奨で決めたもの（D-27〜D-32）」。12 章の表（481 行）には D-33（検証・取り消し・I4・NOT_CONVERGED の設計を残す判断）があり、review-fixes 記録 43 行も「D-27〜D-33」と記載。誤記は Spec 3 行目のみ（他の文書に D-27〜D-32 の残存は無いことを HEAD の blob で確認済み）
- **修正方針**: Spec 3 行目を `D-27〜D-33` に直す
- **検証方法**: `git show` で修正後に `D-27〜D-32` が残らないこと、3 文書の範囲表記が一致することを確認

### RFP-03: 計画のコードブロック 2 箇所で `stateComponent` の `!` 欠落 → CS8602 (b)

- **出典**: SWE-2-Max F-01
- **現状**: `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md` 420 行目 `(stateComponent.SlotKey, sourceSlot!.Id)` と 3042 行目 `!string.IsNullOrEmpty(stateComponent.SupersededId)` が、nullable な `stateComponent`（`ApplyStateComponent?`）を `!` なしで参照外しする。上流 `b3a84ae` の `WorldService.cs` 1031・1045-1047 行で `relocating = stateComponent is not null && ...` かつ `stateComponent!.SlotKey` と `!` を付けており、`<Nullable>enable</Nullable>`（Directory.Build.props 3 行）のため CS8602 が出る。計画自身の検証記録「0 warnings」（1024・3980 行）と矛盾する計画文書内の事実誤認
- **修正方針**: 420 行目を `stateComponent!.SlotKey`、3042 行目を `stateComponent!.SupersededId` に直す
- **検証方法**: 修正後のコードブロックが上流の `if (relocating)` ブロック内の既存 `!` 使用（1047 行・計画 2992-2993・3021 行と同じ形）と一致することを目視確認。実コンパイルの確認は計画の実装時（Task ゲート）に行う

### RFP-04: Spec の `SaveSlotIndexes` と計画の `SaveSlotIndexesAsync` の表記不一致 (b)

- **出典**: qwen3.8-max I-2
- **現状**: Spec が `SaveSlotIndexes`（14 箇所、6.1 節の見出しを含む）、計画と review-fixes 記録が `SaveSlotIndexesAsync`（計画 14 箇所）。実装名は `SaveSlotIndexesAsync` であり、語句一致検索で Spec 側が引っかからない
- **修正方針**: Spec 側の 14 箇所をすべて `SaveSlotIndexesAsync` に統一する（6.1 節の見出し・「`SaveSlotIndexes` を呼ぶ」等の本文表記を含む）
- **検証方法**: 修正後に Spec 内で `SaveSlotIndexesAsync` 以外の表記（`SaveSlotIndexes` 単独）が残らないことを grep で確認

### RFP-05: NOT_CONVERGED で止まると置き換え元がすでに無い key の `supersededId` が state に残り案内にも出ない (a)

- **出典**: xai-grok-4.7 M-1
- **再現（計画コードの追跡で確認）**:
  1. 前の apply で key A の置き換え元削除（段階 5 の `RemoveComponentAsync`）まで進み、`supersededId` を消す checkpoint の前に中断 → state に `supersededId` だけ残る
  2. 次の apply で A は `SupersededId is not null && Superseded is null` となり `AwaitsVerification` が偽（計画 2260 行）→ 検証（2524 行）・取り消し（2564 行）・`inProgress`（2578 行）のいずれの対象にもならない
  3. 同じ apply で key B の検証が失敗すると `VerifyReplacementsAsync` が `APPLY_LIST_SHRINK_NOT_CONVERGED` を投げ（2469→2564-2596 行）、その後段にある段階 5 の片付け（2110-2126 行）は実行されない
  4. `inProgress` が空なら再読込警告の suggestion も付かない（2595-2596 行）。再読込後は `supersededId` 残存により `session-changed` で止まり、state の手編集が要る。Spec 7.3（「段階 5 で記録を片付けるだけにする」）・7.5（`inProgress` の定義）・I6（案内の要件）と矛盾する設計の穴
- **修正方針**: 計画 B4 の `VerifyReplacementsAsync`（2518-2600 行付近）で `APPLY_LIST_SHRINK_NOT_CONVERGED` を投げる前に、置き換え元がすでに無い key（`SupersededId is not null && Superseded is null`）だけ段階 5 と同じ片付けを行う — `SaveSlotIndexesAsync` → `supersededId` を消す → checkpoint（`RemoveComponentAsync` はしない。D-26 の置き換え先はそのまま残す）。片付けた key は `inProgress` に入れない。計画 B5 に、key A の削除応答が失われて `supersededId` だけ残った状態で key B の検証を失敗させたとき、A の `supersededId` が消え再読込後も `session-changed` にならないことを固定するテスト（`ANotConvergedApplyStillSettlesARecreateWhoseSourceIsGone`）を足す。Spec 7.5 に「NOT_CONVERGED を投げる前に、置き換え元がすでに無い key は検証・取り消しの成否に関わらず記録を片付ける」を 1 文足す
- **検証方法**: 修正後の計画コードブロックの追跡で、上記シナリオで A が stranded しないことを確認。追加するテストの記述が既存テストヘルパー（偽クライアントの応答喪失シミュレーション）と整合することを確認

### RFP-06: 自己参照を持つ作り直しで参照以外の `initialFields` も作成時に渡されない (b)

- **出典**: xai-grok-4.7 L-1
- **現状**: 計画 2030-2033 行の除外は `ReferencesComponentKeys(field.Value, awaitingKeys, component.Spec.Key)` で、2211-2219 行の `stable.Key != self` により自分自身への参照は「検証待ちの参照」とみなさない。作り直しの key は `awaitingKeys`（2011 行）に含まれるため、`self` 除外がなければ自己参照は除外できるのに、現行では `withoutPending == createFields` となり `withoutPending.Count < createFields.Count` が偽 → `createFields` がそのまま残り、自己参照が解決できず `CanResolveAll` が失敗する。上流 `b3a84ae` の 464-476 行では `CanResolveAll` が偽だと空の `initialFields` で `AddComponentAsync` するため、自己参照と `Enabled` のような非参照フィールドを同時に持つ Component は `initialFields` を全部落とす。Spec 7.3 の「検証待ちの置き換え先（自分自身を含む）を参照するフィールドだけを除き、参照以外のフィールドは作成時に書く」と矛盾する計画コードの誤り
- **修正方針**: 計画の作成ブロックで、`component.AwaitsVerification` のときは `self` 除外を適用しない（`ReferencesComponentKeys(field.Value, awaitingKeys, component.AwaitsVerification ? null : component.Spec.Key)`）。計画 B3 に、自己参照と非参照 `initialFields` を同時に持つ作り直しで `AddComponentAsync` に非参照フィールドが渡ることを固定するテスト（`ARecreateReferencingItselfKeepsItsOtherInitialFields`）を足す。Spec 7.3 はすでに「自分自身を含む」と正しく書いているので変更不要
- **検証方法**: 修正後のコードブロックで、自己参照フィールドは除外され非参照フィールドだけが `CanResolveAll`/`ResolveFieldsAsync` を通ることを追跡確認

## 対応しない（2 件）

### RFP-07: 作り直しの旧 Component 削除の進捗を `"fields"` 段階として報告する

- **出典**: SWE-2-Max F-02（Info）
- **理由**: Spec（187 行付近）が「置き換え元の削除を加える（移動元の削除と同じく、段階名 `fields` の進捗として出す）」と明示的に決めた設計判断であり、上流 `b3a84ae` でも移動元の `RemoveComponentAsync`（WorldService.cs 513 行）に続く進捗報告は `"fields"` 段階（520-521 行）で行われる。レビュー自身も「機能的な誤りではない」と認定する Info 級の表示一貫性の話であり、(a)〜(d) を満たさない
- **論点メモ**: 段階名と処理内容の対応を厳密にするなら独自段階名や `"prune"` の選択肢もあるが、Spec が上流先例に合わせて決着済み

### RFP-08: Spec 7.8 の plan フィルター主張を固定するテスト・確認手順がない

- **出典**: qwen3.8-max L-2
- **理由**: 主張自体は上流 `b3a84ae` で事実確認済み —— `Program.cs` 536-542 行で `--creates-only`/`--deletes-only` は `Action == "create"`/`"delete"` のホワイトリスト（`recreate` は出ない = Spec どおり）、`--changes-only` は `result.Changes`（`Models.cs` 284 行、`Action != "no-op"` の一覧）で `recreate` が出る = Spec どおり。残るのは「既に正しい主張を固定するテスト追加」という保険だけで、(a)〜(d) を満たさない
- **論点メモ**: 実装時に RLoop.Cli の絞り込み実装が変わる場合は、その変更の中でテストを足すのが自然

## 実施の順序と範囲

1. RFP-02・RFP-03・RFP-04・RFP-05・RFP-06・RFP-01 の Spec 10.4 部分: 3 文書（Spec・計画）を編集する。レビュー対象ブランチ `docs/list-shrink-recreate-split` 上で行う
2. RFP-01 の PR 本文更新: `gh pr edit 8 --body-file` で実行（コミットではなく PR メタデータ）
3. 変更の種類に応じた検証: 環境の変更（`docs/` 配下の文書のみ）なので `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を通す。文書のみの変更のため追加の自動テストは無し（計画内のコードブロック修正の実コンパイル確認は fork 実装時の Task ゲートに委ねる —— Spec には「実装時に行う」と明記済み）
4. `docs/list-shrink-recreate-split` へ commit し、既存 PR #8 へ push する（新しいブランチ・PR は作らない）
5. push 後に status comment を投稿する（`PR_REPO=usaturn/create-reso-world`）

## 触らないもの

- `external/resoloop` のソース（本 PR は文書のみ。fork の実装は PR #8 マージ後に別途行う）
- レビューに挙がっていない問題の新規調査
- `docs_draft/2026-10-01-list-shrink-recreate-split-review.md`（git 非追跡・規約により対象外）
