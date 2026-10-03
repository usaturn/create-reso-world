# PR #9 レビュー修正設計（第2回）

- 日付: 2026-10-02
- brainstorming 経路: **architectural**。削除と checkpoint、セッションをまたぐ再照合の安全性が連動するため。
- 対象: `usaturn/resoloop` の OPEN な PR #9、head `fix/list-shrink-recreate-split`、検証時 HEAD `1eab03e7a5d9b3d26f404c56ad0ae5b5486d119a`。fork の `origin` は `usaturn/resoloop`、`upstream` は `orange3134/resoloop`。
- 入力: `external/resoloop/reviews/#9-fix-list-shrink-recreate-split/` の8ファイル。対象 HEAD は `claude-opus-5-5.md`、`gpt-6-sol.md`、`qwen3.8-max.md` が `1aeb26faece1`、`claude-sonnet-5-5.md`、`commandcode-deepseek-deepseek-v4.1-flash.md`、`opencode-go-muse-spark-1.3-contributor.md`、`SWE-2-Max.md`、`xai-grok-4.7.md` が `1eab03e7a5d9`（一部には古い HEAD の履歴・Resolved findings を含む）。
- 意図と成功条件: 中断した Component 削除・移動の後に Slot の index を保存できなくても、次のセッションの apply が別 Component、特に管理外のものへ書き込まない。list 短縮の対象範囲はドキュメントと現行実装を一致させる。未確認の実機挙動や旧バージョンとの互換性を追加保証するものではない。別の意図があれば実装承認前に調整する。
- この Spec は計画であり、実装・commit・push は未実施。既存の同日付 Spec `2026-10-02-pr9-list-shrink-review-fixes-design.md` は古い HEAD の成果物なので変更しない。

## 全指摘の選別

21件（レビュー内の見出しをファイル名＋IDで識別。重複も別件として計上）: **解消済み 10 / 対応する 3 / 判断保留 0 / 対応しない 8**。対応根拠の (a) は現行 HEAD での誤動作、(b) は現行 HEAD で事実と異なる記述。未検証候補や一般的なテスト提案は確定した指摘には数えない。

| 指摘（ファイル名中の識別子・ID） | 区分 | 現行 HEAD の根拠・判断 |
| --- | --- | --- |
| opus L-1: さらに短い宣言の再開案内 | 解消済み | `WorldService.cs:1196-1200,2369-2382` に同じ宣言で再実行できる分岐・案内があり、`DECLARATIVE.md:196` も一致。 |
| opus I-1: recovery と suggestion の矛盾 | 解消済み | `WorldService.cs:2373-2393` は固有 recovery を付け、`:672-675` の共通 catch はそれを保持する。 |
| sonnet L-1: prune の Slot 再読込・二重 checkpoint | 対応しない | `WorldService.cs:577-583` の削除直後の checkpoint は中断時に削除済み key を残さないため必要。Slot ごとの集約は性能改善であり、今回の誤動作の修正根拠 (a)〜(d) を満たさない。 |
| sonnet I-1: recreate に `--yes` がなく範囲外参照を失う | 対応しない | `AGENTS.md` の `--yes` は CLI delete/remove に対する規則。`DECLARATIVE.md:193-195` は recreate と観測範囲を明示済み。仕様の是非として記録し、今回変更しない。 |
| gpt-6-sol H-1: 保留 list を検証せず旧 Component を消す | 解消済み | `WorldService.cs:2329-2345` の2段階書き込み・読み戻しが `:542-557` の旧 Component 削除に先立つ。 |
| commandcode L-1: schemaVersion を上げず supersededId を追加 | 対応しない | `ApplyWorkflow.cs:618-625,645-658` で任意フィールド追加と旧 schema の読み取りは事実。旧ビルドへ戻す互換性の取り扱いは仕様判断であり、現行版の誤動作・誤記述の根拠はない。 |
| commandcode L-3: 入れ子 list が recreate 対象外 | 対応する (b) | `WorldService.cs:1184-1194` は `fields` 直下の配列のみ対象、`ApplyWorkflowTests.ListShrink.cs:65-87` は入れ子で `update` を確認。一方 `DECLARATIVE.md:193` は `fields` の list member 全般が `recreate` になるように読める。docs の対象範囲を明確にする。実機での非収束そのものは未再現。 |
| commandcode I-1: undo 時に added/deleted を両方計上 | 対応しない | `WorldService.cs:489,2356-2360` は作成と削除の実操作を各1回計上する。net 増分と定義する根拠はなく、表示上の解釈変更は対象外。 |
| commandcode L-2: 旧 Component 不在の再開経路で list 未検証 | 解消済み | `WorldService.cs:2567` は `SupersededId` により検証し、`:2300-2326` で読み戻す。 |
| qwen L-1: recreate を `--yes` なしで実行 | 対応しない | sonnet I-1 と同じ仕様論点。`AGENTS.md` は CLI delete/remove の明示操作に `--yes` を要求、`DECLARATIVE.md:193` は置換を告知。 |
| qwen L-2: 入れ子 list の対象外が文書にない | 対応する (b) | commandcode L-3 と同じ記述の不正確さ。`WorldService.cs:1184-1194`、入れ子が `update` のテスト、`DECLARATIVE.md:193` で確認。 |
| qwen L-3: 参照済み再開置換を undo で削除 | 解消済み | `WorldService.cs:2349-2355` は参照がある再開置換を undo せず、deferred 書き込み時は参照グループを残す。 |
| qwen I-1: 実機・fork CI 未検証 | 対応しない | レビューが述べる未検証は環境依存の確認事項で、現行 HEAD の誤動作や記述の誤りではない。実機での確認を済ませたとは主張しない。 |
| SWE L-1: null 宣言・prune 対象の参照も recreate を停止 | 対応しない | `WorldService.cs:1584-1605,1620-1628` は保守的に事前停止する。停止条件を緩めるのは仕様・安全性の判断であり、再現済みのデータ破壊ではない。 |
| SWE I-2: AwaitsVerification のコメントが新条件を説明しない | 対応しない | `WorldService.cs:2566-2567` のコメントは旧 Component が存在する場合の説明として成立し、「その場合のみ」とは述べていない。条件の追加説明は Info 級の追記。 |
| SWE L-2: null ID ガード漏れ | 解消済み | `WorldService.cs:1107` は `string.IsNullOrEmpty` で null・空の双方を拒否する。 |
| SWE L-3: deferred list の最終書き込み未検証 | 解消済み | `WorldService.cs:2332-2339` が相互参照の2段目を旧 Component 削除前に読み戻す。gpt H-1 と同じ原因。 |
| SWE I-1: undo 範囲の docs 誤記 | 解消済み | `DECLARATIVE.md:196` は再開置換も安全なら取り消し、参照済みなら保持する旨へ更新済み。 |
| xai M-2: index 保存失敗後、セッション変更で別 Component に書く | 対応する (a) | 現行 HEAD の一時隔離 worktree に追加した probe で再現。2件の管理同型 Component の先頭を prune、index 保存前に cancel、末尾に同型の管理外 Component（`Value=999`）を置いて world reload 後に再 apply すると、末尾の値が `2` に変更された。`WorldService.cs:577-583,2003-2024,2082-2085`。probe の変更は破棄済み。 |
| xai M-1: recreate 予定を test が存在しないと扱う | 解消済み | `WorldService.cs:706-710` が `Existing ?? Superseded` を現在の Component として採用。 |
| xai L-1: NOT_CONVERGED の再実行案内が矛盾 | 解消済み | opus I-1 と同じ修正。`WorldService.cs:2373-2393,672-675`。 |

判定対象外の未検証候補（opus の `initialFields`、sonnet の stale binding など）は実行再現や事実誤認の根拠がなく、このレビューの確定指摘と混ぜない。レビュー外の新規問題は追加しない。

## 修正案の比較と選択

1. **推奨: 削除・移動の前に index の未確定状態を checkpoint へ残す。** 同じ Slot の保存 index を無効値にし、セッション内では保存 ID から正しいレイアウトを読み直して一括更新する。再読込前に失敗したら、次セッションでは位置だけを根拠に照合・書き込みをしない。現行 state の `componentIndex` と `STABLE_COMPONENT_AMBIGUOUS` を活用し、新しい state schema は導入しない。欠点は読み取り失敗後の再開で明示的な照合が必要になる場合があること。
2. 後から修復できると見込んで index の更新をまとめる: 読み取り回数は減るが、再読込直後の誤書き込み窓を閉じないため不採用。
3. Slot ごとの pending フィールドを state schema に追加する: 状態は明示的になるが、旧ビルドとの互換性と schema 更新を別途設計する必要がある。今回の範囲より大きいため不採用。

## 対応する項目と検証

### xai M-2 — 削除・移動の checkpoint と再照合

- `src/RLoop.Core/WorldService.cs` の prune／移動元削除（必要なら recreate の同じ index 保存経路も安全性確認）の前に、対象 Slot の保存済み index が未確認であることを checkpoint へ記録する。副作用と checkpoint の順序を明示し、削除が成功したが応答を失った場合も位置による誤照合を許さない。削除確定後の state は削除済み key を残さない。保存済み ID と取得した Slot の現在の並びを照合できたら index を保存して未確認状態を解除する。
- `MatchComponent` と文書から外れた key の再照合経路も、未確認 index の値や ordinal から他の同型 Component を推測しない。前セッションの ID が使えず identity 等でも一意に確認できない場合は、**副作用前に** `STABLE_COMPONENT_AMBIGUOUS`（または専用の明確な検証エラー）で止め、候補 ID と安全な復旧手順を提示する。生きている同一セッションでは ID で照合し、再読込可能なら index を修復して従来どおり継続する。
- 切断・キャンセル・応答喪失時の checkpoint がどの段階でも誤書き込みを許さないよう、before-delete／after-delete／after-index-save の遷移をテストで固定する。未確認の marker があるだけで既存の managed key の削除結果を勝手に推測・確定しない。`--prune --yes` の確認条件と管理外 Component 保護は維持する。
- `tests/RLoop.Tests/ApplyWorkflowTests.SlotIndexes.cs` に (1) 現行 HEAD で失敗した prune→index 保存失敗→再読込→管理外 `Value=999` 保持の回帰テスト、(2) 同セッションでの回復・checkpoint 整合、(3) 移動元削除の中断と再読込、(4) 結果が不明な削除応答の安全な扱いを追加する。既存の成功パス・cancel テストを維持する。
- 本番の実機 Resonite への破壊的操作は行わない。fake client の offline テストで分岐を確認する。

### commandcode L-3 / qwen L-2 — ドキュメントの対象範囲

- `docs/DECLARATIVE.md:193` と、同じ全般的な説明がある README の該当箇所を、**`fields` 直下の list member だけを recreate 対象とする**事実に合わせて修正する。syncObject 内などの入れ子 list の縮小は現時点で recreate の対象外であり、収束保証がないと明記する。入れ子 list の検出機能は追加しない。
- 検証: 現行 HEAD の `AShorterListInsideASyncObjectIsNotRecreated`（plan は `update`）と文書の表現を照合し、`dotnet test tests/RLoop.Tests/RLoop.Tests.csproj --filter FullyQualifiedName~ApplyWorkflowTests` を実行する。変更したファイルに応じて既存の文書・CLI 関連テストも確認する。

## 承認・反映の境界

この Spec を提示して停止する。ユーザの明示的な「進めて」までは fork のソース／テスト／ドキュメントに変更を加えない。承認後は実装と関連 `dotnet test` が成功した場合にのみ、既存 PR #9 の head ブランチへ commit / push し、PR コメントの指定フォーマットで結果を残す。PR を増やさない。再現に使った一時 worktree と親ディレクトリは検証後に削除済み。
