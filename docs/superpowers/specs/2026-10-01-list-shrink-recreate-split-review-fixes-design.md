# リスト縮小時の作り直し（分割案）: レビュー指摘の選別と反映

- **対象**: create-reso-world PR #8（ブランチ `docs/list-shrink-recreate-split`）の Spec `docs/superpowers/specs/2026-10-01-list-shrink-recreate-split-design.md` と実装計画 `docs/superpowers/plans/2026-10-01-list-shrink-recreate-split.md`
- **入力**: `docs_draft/2026-10-01-list-shrink-recreate-split-review.md`（R-01〜R-65。対象 HEAD は `8856b10`。High 7、Medium 24、Low 31、Info 3）
- **現行 HEAD**: `8856b10`（レビューの対象と同じ）。計画のコードは、上流 `b3a84ae` の使い捨てのコピーに計画の Task を順に当てたもの（再生の `b7679c0`）で確かめた
- **ユーザの指示**: 「レビューを確認し、妥当であると判断できる指摘を吟味し取り入れてから、作業引き継ぎ書を作成せよ」（2026-10-01）
- **経路**: architectural（不変条件 I5・I6 の追加、停止の reason の追加、エラーの context と suggestions の変更を含むため）。設計の承認の代わりに、ユーザの上の指示で反映まで行い、反映後の Spec と計画のレビューをユーザに求める（PR #8 は draft のまま）

## 1. 検証の方法

review-fix-planning の手順に従い、現行 HEAD のコミット済みの内容だけを根拠にした。

1. **再現**: 計画のコードを再生した `b7679c0` の隔離 worktree（使い捨て）に調査用のテスト 14 件を足し、レビューの主張を確かめた。14 件とも主張どおりに再現した。

   | 指摘 | 再現した結果 |
   |---|---|
   | R-01 | 子から親への移動の直後に「Key 'v2' is saved at index 1 but its Component is at 0.」。再読込後は `STABLE_COMPONENT_AMBIGUOUS` |
   | R-02 | 互いを参照する 2 つの作り直しで、1 回目も 2 回目も `APPLY_REFERENCE_NOT_FOUND`。Rubble01 に Test.Renderer が 4 つ残った |
   | R-03 | 再インポートの後の NOT_CONVERGED で、取り消し後の `assetFields` に `{"URL":"$asset:mesh"}` が戻った（実機の URL は古い `asset-1`、state のアセットは `asset-2`） |
   | R-04 | 置き換え元の削除を失敗させた後に宣言を短くすると NOT_CONVERGED になり、Source の `Target` が削除済みの Component（C7）を指した |
   | R-05 | ID が空の `extra` が管理外の Test.Renderer に照合され、plan は `recreate`、apply で管理外の Component が削除された |
   | R-06 | syncObject の部分宣言の宣言していない子が置き換え元を指したまま、apply は止まらずに成功し、参照先が消えた |
   | R-08 | prune の削除の直後のキャンセルで `APPLY_CANCELLED`。ワールドの Component は 2 つなのに、state の key は v1・v2・v3 のまま |
   | R-09 | prune の削除の応答を失うと、同じセッションの次の apply の後も state に v1 が残り、再読込後は `APPLY_COMPONENT_OWNERSHIP_CONFLICT` |
   | R-11 | NOT_CONVERGED の後に watcher の `initialFields`（`Enabled: true`）が書かれず false のまま |
   | R-12 | watcher の作成応答を失うと（書き込み 3）、再実行で Late の Test.Source が 2 つになった |
   | R-13 | 同じ型の兄弟がある Slot から作り直しの途中の key を移すと `STABLE_COMPONENT_AMBIGUOUS`（`key-not-declared` にならない） |
   | R-14 | S1 で suggestion どおりに復旧すると、反映前の失敗の書き込み 2 と応答の喪失の書き込み 1 で Source が 2 つになった |
   | R-15 | S2 の書き込み 3 の応答の喪失で、候補の Materials が 0（宣言は 3）。1 つ目の suggestion に当たらない |
   | R-16 | `key-not-declared` の 2 つ目の手順に従うと、`plan --prune` の削除対象に renderer が出ない |

2. **git の模擬**（R-07）: A に 2 件、B に 2 件のコミットを作り、A にレビュー修正を足した後、B を載せ直さずに計画の B8 Step 4 と同じ `reset --soft` を行うと、`git diff --stat A HEAD` に `A.txt | 1 -`（A の修正の打ち消し）が出た。reset の後の `merge-base --is-ancestor` は成功するので、ガードは reset の前に置く必要がある。
3. **ミューテーション**（R-03、R-10、R-21）: `ApplyWorkflowTests` 149 件に対し、取り消しの後の `SaveSlotIndexesAsync` の呼び出しを消す、控えた記録（`StateBeforeRecreate`）を使わない、I3 の出所から移動元と削除計画を外す、のどれでも 149 件がすべて成功した（テストが無い）。
4. **事実の確認**: R-26 のコマンドの失敗（`fatal: Needed a single revision`）は、このセッションでも同じ形で確かめていた。R-52 の `MeshRenderer` の同期メソッド（`AutoRig(rig)`・`SplitSubmeshes()`・`MergeByMaterial()`）は slum02 のリフレクションのキャッシュで確かめた。R-22 のフィルタに一致しない B のテスト 4 件は、テスト名で確かめた。
5. 隔離 worktree は、検証の後に `git worktree remove` と親ディレクトリの削除で片付けた。

## 2. 分類

| 区分 | 件数 | 内容 |
|---|---|---|
| 解消済み | 0 | レビューの対象 HEAD から変わっていないため |
| 対応する | 64 | (a) 現行 HEAD で再現した誤動作、(b) 事実と違う記述、(d) ユーザの指示「妥当な指摘を吟味して取り入れる」で妥当と判断したもの |
| 判断保留 | 0 | ユーザが決める事項（R-04・R-18・R-23・R-24 と 5.5 の確認）は、ユーザの指示によりレビューの推奨で決め、12 章の D-27〜D-33 に記録した（ユーザが覆せる） |
| 対応しない | 1 | R-43 |

「(d)」の妥当性は、次の 3 つを満たすかで判断した。現行 HEAD の Spec・計画・コードで指摘の事実が確かめられる、直さないと実装・レビュー・上流への提出で手戻りが出る見込みがある、修正の費用が効果に見合う。

## 3. 指摘ごとの扱い

区分の列の (a)・(b)・(d) は上の根拠。反映先の「S」は Spec、「P」は計画（Task 名）、「T」は計画に足した・直したテスト。

| ID | 重要度 | 区分 | 反映した内容 | 確かめ方 |
|---|---|---|---|---|
| R-01 | High | 対応する (a) | P A2: `SaveSlotIndexesAsync` が同じ Slot の実行時の `ComponentIndex` も合わせる（案 1。`ComponentIndex` を set 可能に）。T A1 に `move-up`、A3 の中断テストに上向きの移動と「中断しなかった回は次の apply の前に I1」。S 3.1・6.1・6.3・8.4 | 再生で A1 の `move-up` が A2 の前に失敗・後に成功。旧コードで A1・A3 の上向きが失敗 |
| R-02 | High | 対応する (a) | P B3・B4: 検証では解決できるフィールドだけを書き（`CanResolve`）、全件が通った後に置き換え先を参照先に加える（形 (2)）。T B3 相互参照、B5 再開との組み合わせ。S I4・7.3・7.5・11.4・12 章の補正。改善案 4（再開した置き換え先の後回しの `initialFields` の参照）は実装せず 11.4 に記録 | 旧コードで 2 件とも失敗、修正後に成功 |
| R-03 | High | 対応する (a) | P B2: plan 時点の記録を控えない。B3: 置き換え先を作る直前（アセットの段階の後）に控える。T B4 に再インポートの有無の 2 ケース。S 7.3・7.5・7.9・8.3・12 章の補正 | 旧コードで再インポートありが失敗。控えた記録を使わないミューテーションは再インポートなしのケースが検出 |
| R-04 | High | 対応する (a)・判断はレビューの推奨 | P B5: 置き換え元がすでに無ければ新しい作り直し（案 1）。置き換え元が残り、置き換え先を参照するものがあれば `declaration-shrank` で止める（案 2）。案 2 には「参照するものが無ければ止めない」を足した（取り消しの途中で止めた後の再開を誤って止めないため。D-27）。T B5 に 2 件。S I4・7.4・7.5・7.7・11.1・D-27 | 旧コードで 2 件とも失敗、修正後に成功 |
| R-05 | High | 対応する (a) | P B2: ID が空の key で縮小を検出したら `STABLE_COMPONENT_AMBIGUOUS` で止める。T B2 に同じセッションと再読込後の 2 ケース（key を外すと収束、次の apply は書き込み 0 件）。S 7.1・7.6・7.7・9 章・11.4 | 旧コードで 2 ケースとも失敗 |
| R-06 | High | 対応する (a) | P B6: 除外を「同じ位置に参照の指定がある場合だけ」にする（`2c324e3` と同じ形）。T B6 に 3 ケースの Theory。S 7.6・9 章 | 旧コードで宣言していない子のケースが失敗 |
| R-07 | High | 対応する (a) | P C1 Step 4 を手順に置き換え（`fixup!`・`--autosquash`・`rebase --onto`）、B8 Step 4 の reset の前にガード、push の手順、C3 に追従。S 10.4 | git の模擬で再現。手順の形はレビューの模擬（git 2.55.0）で確かめられている |
| R-08 | Medium | 対応する (a) | P A2: prune は削除の結果を checkpoint してから Slot を読み直す。T A2 にキャンセルのテスト。S 6.1 | 再生で A2 の前に失敗・後に成功。旧コードで失敗 |
| R-09 | Medium | 対応する (a)(b)・判断はレビューの推奨 | 案 (b): S 8.4 の主語を移動元の削除に限る、4.2・11.1・D-29 に追記、P A3 のテストのコメントと PR A の Verification の範囲を限る。案 (a)（A で key を外す）は採らず上流に別に相談 | 文書の変更。prune を A3 の Theory に足さない（案 (b) では失敗するため） |
| R-10 | Medium | 対応する (d) | T B4 の `AReplacementThatTheRuntimeRefillsIsUndone` に、置き換え先の後ろに作る `extra` を足す。S 8.3 | ミューテーション（取り消し後の `SaveSlotIndexesAsync` を消す）で失敗することを確かめる（5 章） |
| R-11 | Medium | 対応する (a) | P B3: 作成時は検証待ちの置き換え先への参照だけを除いて書く（`ReferencesComponentKeys`）。T watcher に `initialFields`、B4 で `Enabled` を確かめる。S 7.3・11.4 | 旧コードで失敗 |
| R-12 | Medium | 対応する (a) | P B3: 作成前・作成後の checkpoint には作成時に書いた参照の selector だけを保存する（`555338e` の修正 D と同じ形）。T B5 に回帰テスト（再開の実装が要るので B5 に置く）、B7 の S1 に watcher。S 7.3・8.2。PR B の Root cause に 1 行 | 旧コードで回帰テストと S1 の応答の喪失が失敗 |
| R-13 | Medium | 対応する (a) | P B5: 途中の作り直しの key は移動元の Slot で照合しない。T B5 の `key-not-declared` に同じ型の兄弟がある構成 | 旧コードで失敗 |
| R-14 | Medium | 対応する (a)・規則の変更はレビューの推奨 | P B5: suggestions を「`referencedBy` で参照されている候補を残す。ID が空なら `supersededId` の値にする」に変え、同じ型の key がほかにある Slot では区別できないことを示す。candidates に `referencedBy` を足す（リストの要素の参照先 ID は足さない）。T B7 の再読込の分岐で S1 の復旧と S2 の suggestion。S 7.7・8.2・11.2・11.4・D-30。「ID が空なら」はレビューの案への補正（R-05 の停止と両立させるため） | 旧コードで B7 の再読込の 4 ケースが失敗 |
| R-15 | Medium | 対応する (a) | P B5: `replacement-unverified` の 1 つ目の suggestion を、空のリストの場合と inspect での確認を含む形にし、2 つ目を排他にする。DECLARATIVE.md の断定をやめる。T B7 は基準で選んだ候補が 1 つで、中断した apply が作ったものであることを確かめてから削除 | 再生の B7 が成功 |
| R-16 | Medium | 対応する (a) | P B5: `key-not-declared` の suggestion を 1 つにする（第一案）。T B5 のテストに、同じセッションで宣言を戻すと完了し、その後 `--prune` で削除できる後続 | 再生の B5 が成功 |
| R-17 | Medium | 対応する (d) | S 7.7・11.4・10.5、D-31。上流の文書に手編集の手順を新しく載せない。PR B の Known limitations と上流 #5 へのコメントで扱いを尋ねる。state を編集する suggestion に「back up the state file」を足す | 文書の変更 |
| R-18 | Medium | 対応する (d)・判断はレビューの推奨 | 案 1: P B2・B5 で `stateComponent is null` なら作り直さない。T B2 に adopt の plan。S 7.1・7.10・D-28。DECLARATIVE.md に 1 文 | 旧コードで失敗 |
| R-19 | Medium | 対応する (d) | P B1: 偽クライアントのリストが値の要素も持てるようにする。T B4 に値のリストの 2 ケース。P C2 に値のリストと syncObject のリストの確認、その場で縮む種類があれば止まってユーザに報告。S 3.2・7.1・8.1・10.3 | 再生で B4 の後に成功 |
| R-20 | Medium | 対応する (d) | T 収束の判定を強める（Test.Renderer と Test.Source が 1 key ずつ、参照先が実在）。B7 の再読込の後の復旧。A1・A3 の上向きの移動。B5 に取り消し中の中断と K-H1 の回帰テスト。B7 にキャンセルの Fact（S1）。S 8.2・8.4 | 再生で成功。旧コードで強めた判定が S1 の重複を検出 |
| R-21 | Medium | 対応する (d) | T B6 を 4 ケースの Theory（置き換え元、メンバー、要素、宣言していないメンバー）にし、移動元の除外の Fact を足す。B7 の session-changed で plan も止まり state が変わらないこと。S2 の leftover を Test.Renderer にし、B5 に移動元の除外の Fact。`migrateFrom` は S 7.4 に上流の処理で満たされると書く（テストは足さない） | ミューテーション（I3 の出所を外す）で失敗することを確かめる（5 章） |
| R-22 | Medium | 対応する (b) | P B8 Step 2 をフィルタなしの全件にし、Expected を件数と名前で書く。PR B の Verification も件数で書く。S 8.5 | 再生の「A の `src/` で全件」の結果で埋めた |
| R-23 | Medium | 対応する (d)・判断はレビューの推奨 | 選択肢 B: S 5 章に I5・I6、10.3 に重大度の定義・見直しの条件（同じ不変条件または同じ問題群の 2 件目）・差分だけの確認。P C1。D-32。テストの強化は R-20、管理外の Component の個別テストは B5 | 文書の変更 |
| R-24 | Medium | 対応する (d)・判断はレビューの推奨 | 案 2: 設計を残し、PR B の Summary に理由を 1〜2 文。本文の正確さ（NOT_CONVERGED は変更前ではない、README_JA の「元の長さに戻す」）を直す。S 11.4・D-33 | 文書の変更 |
| R-25 | Medium | 対応する (d) | P Global Constraints に「各ブロックは 1 回の Bash 呼び出しで、先頭に `set -euo pipefail`、作業ディレクトリへ絶対パスで cd」。A4 Step 1・B8 Step 2 を比較の手順（`BASE`、全件、worktree の片付け）に置き換え。cd の無いブロックに cd | 文書の変更 |
| R-26 | Medium | 対応する (a) | P Task 0 Step 1 を `git rev-parse origin/main upstream/main`（完全なハッシュ）にする | このセッションで同じ失敗を確かめていた |
| R-27 | Medium | 対応する (b)(d) | P C3 をチェックリスト（前提、文面の書き換え、出す順序、提出後、リリース後）に置き換え。`resoloop skills sync --check` → `--update`。S 10.5 | 文書の変更 |
| R-28 | Medium | 対応する (d) | P の Spec の参照を絶対パスにし、Task 0 Step 0 に PR #8 のマージの確認。設計の変更は create-reso-world に Spec を直す PR を別に出す。S 冒頭・10.3・12 章の補正 | 文書の変更 |
| R-29 | Medium | 対応する (b)(d) | P C2 に、使い捨てのワールド、`discover` での接続先の決定、`--url auto --session`、保存し直し、失敗時の片付け、書き込み 0 件の定義（`--profile` の `mutations`）、記録する版 | 文書の変更 |
| R-30 | Medium | 対応する (b) | P B8 Step 1: README・README_JA・build SKILL・debug SKILL・DECLARATIVE.md に検査の範囲を書く。S 7.6・9 章 | 再生の文書の照合 |
| R-31 | Medium | 対応する (d) | P PR A・B の本文に Known limitations、互換性、`--yes` との関係、OS と SDK、実機で未確認であること。S 10.4 | 文書の変更 |
| R-32 | Low | 対応する (d) | S 7.7 の表（`plan`・`diff`・`test` も止まる）、7.10 に `test` の扱い | 文書の変更 |
| R-33 | Low | 対応する (d) | T B1 に偽クライアントの Fact | 再生の B1 で成功 |
| R-34 | Low | 対応する (b)(d) | P B4: NOT_CONVERGED の context に `inProgress` と、その key があるときの suggestion。T B5 で `inProgress` を確かめる。S 7.5 の最後の項目を実際の規則に合わせる | 旧コードで失敗 |
| R-35 | Low | 対応する (b) | S 7.4 の判定の位置を計画に合わせる | 文書の変更 |
| R-36 | Low | 対応する (b) | S 7.3（段階名 `fields`）・7.7（candidates の範囲）・7.8（4 つ目の文言）。T B5 の plan のテストに置き換え元がすでに無い場合 | 再生の B5 で成功 |
| R-37 | Low | 対応する (d) | P B4: NOT_CONVERGED の 2 つ目の suggestion を「宣言を変えてから」に | 文書・コードの変更 |
| R-38 | Low | 対応する (d) | S 7.3 に、再開した置き換え先は `initialFields` も書き直すこと、検証の書き込みは件数に含めないこと | 文書の変更 |
| R-39 | Low | 対応する (b) | P A2・A3 の DECLARATIVE.md の文を、保証を言い切らず plan・diff が state を書かないことを含む形に。S 9 章 | 再生の文書の照合 |
| R-40 | Low | 対応する (d) | P「この計画のコードについて」に Markdown の目印の当て方の規則（改行を除いて探す、空行から始まらない追加は同じ行に続ける） | 文書の変更 |
| R-41 | Low | 対応する (d) | T A3 に再読込後の最初の apply のテスト（レビューのコード）。所有権の衝突で state が変わらないテストは足さない（今の構造で必ず成り立つ） | 再生の A3 で、実装前に失敗・後に成功 |
| R-42 | Low | 対応する (d) | T B4 の 2 つ目に Source の参照の確認、B3 の prune のテストにコメント | 再生で成功 |
| R-43 | Low | 対応しない | 挙動を変えない重複の整理で、上流の既存コードへの差分とレビュー量が増える。上流のレビューで求められたら対応する | — |
| R-44 | Low | 対応する (b) | P B2: plan の理由を "initialFields return to their declared values and undeclared members to their type defaults" に。B8 の DECLARATIVE.md・README_JA。S 3.5・7.8 | 再生の B2 で成功 |
| R-45 | Low | 対応する (d) | T B7: 再開の apply の前に書き込みを数え直し、`replacement-unverified` の時点で 0 件。テストのコメントと PR B の Verification に収束の判定の範囲。S 4.2 の文言を「作成前の checkpoint の後」に | 再生の B7 で成功 |
| R-46 | Low | 対応する (d) | T B5 に終了コードの確認 | 再生で成功 |
| R-47 | Low | 対応する (d) | P B3〜B6 の Step 2 の Expected を件数と失敗するテストの名前で書く | 再生の結果で埋めた |
| R-48 | Low | 対応する (d) | P のコードとテストのコメントから I1〜I4 のラベルを外す | 再生の差分を grep |
| R-49 | Low | 対応する (d) | P B2 の `JsonIgnore` のコメント、B8 の DECLARATIVE.md の diff の列挙に `recreate`。S 7.2 | 再生の文書の照合 |
| R-50 | Low | 対応する (b) | S 3.4 の集計範囲 | 文書の変更 |
| R-51 | Low | 対応する (b) | S 1 章・3.1、PR B の Root cause に、`APPLY_REFERENCE_NOT_RETAINED` は要素がワールドの参照のリストに限ること | 文書の変更 |
| R-52 | Low | 対応する (b) | S 3.2、PR B の Root cause に同期メソッドの事実 | リフレクションのキャッシュで確かめた |
| R-53 | Low | 対応する (d) | S 冒頭・7.3 に「第 n 節」の出所 | 文書の変更 |
| R-54 | Low | 対応する (d) | P Issue・PR の本文の表記（「削除した Component より後ろ」「index の修正」、PR A のタイトル） | 文書の変更 |
| R-55 | Low | 対応する (d) | P B8 Step 4 から `Refs` を外し、C1 Step 4 の最後のまとめ直しで付ける。S 10.4 | 文書の変更 |
| R-56 | Low | 対応する (d) | P A1 Step 3 の Issue に Environment and verification と Expected/Actual、PR A の Verification に実機で未確認 | 文書の変更 |
| R-57 | Low | 対応する (d) | P 番号をコマンドで取って `sed` で置き換える（A4 Step 3、B8 Step 5・6）。`InterruptedAsync` を A3 へ。S 10.1・10.2 | 文書の変更 |
| R-58 | Low | 対応する (d) | P C3・S 10.5 に上流 #5 へのコメントの要点 3 つ | 文書の変更 |
| R-59 | Low | 対応する (d) | P Global Constraints に AGENTS.md の規則、引き継ぎの区切り、所要時間の記録 | 文書の変更 |
| R-60 | Low | 対応する (d) | P Task 0 に checkout が無い場合の案内、A1 Step 2 に D-15 で止めたときの扱い。S 10.1 | 文書の変更 |
| R-61 | Low | 対応する (d) | P Global Constraints に pr-review の `reviews/` の例外 | 文書の変更 |
| R-62 | Low | 対応する (d) | P A4 Step 2・B8 Step 3 に pack と導入したツールでのスモークテスト（Linux）。Windows は上流 CI に任せると明記 | 文書の変更 |
| R-63 | Info | 対応する (d) | S 11.4 に 2 文 | 文書の変更 |
| R-64 | Info | 対応する (d) | T A1・A3 の上向きの移動は移動先に同じ型を置かず、理由をコメントに。S 4.2 | 再生で成功 |
| R-65 | Info | 対応する (d) | P PR B の本文に読む順序 | 文書の変更 |

## 4. 設計の補正（レビューの案から変えた点）

反映の途中の試作で、レビューの案をそのまま入れると別の停止や誤りが起きることが分かったので、次のように補正した。どちらも Spec の 12 章に記録した。

1. **R-04 の `declaration-shrank`**: レビューの案は「置き換え元が残っている再開の key で、置き換え先が宣言より長ければ止める」。これだと、取り消しの途中で止めた apply の次の apply で、runtime が詰め直した置き換え先（参照の張り替えの前に検証で失敗したもの）まで `declaration-shrank` で止まり、復旧の案内も原因と合わない。止めるのは、apply が読んだ範囲でその置き換え先を参照するものがある場合（取り消すと参照が切れる場合）に限った。参照するものが無ければ、通常の検証と取り消しにする（R-20 の取り消し中の中断のテストで確かめた）。
2. **R-14 の復旧の規則**: レビューの案は「管理 Component の参照が今指している方を残し、`supersededId` を消す」。置き換え先の作成の前後で中断した場合は state の `id` が空なので、`supersededId` を消すだけだと、次の apply で R-05 の停止（ID の無い key が位置で照合した Component のリストが長い）に当たる。`id` が空のときは `supersededId` の値にする手順を足した（このとき残すのは必ず置き換え元である）。

## 5. 反映の確かめ方

- **再生**: 上流 `b3a84ae` の使い捨てのコピーに、直した計画の Task を順に当て、各 Task で「テストを先に足すと失敗し、実装すると成功する」ことと、Task ごとの全件の件数を確かめた（REPLAY OK）。`RLoop.Tests` は 326 → 331（A2）→ 337（A3）→ 340（B1）→ 347（B2）→ 355（B3）→ 361（B4）→ 377（B5）→ 385（B6）→ 394（B7）。最後の状態のソリューション全体で `RLoop.Tests` 394 件と `RLoop.IntegrationTests` 19 件が成功した。最後の状態のコードと文書は、試作と 1 文字も違わなかった。
- **修正前との比較**: A のツリー（337 件）を上流の `src/` で流すと、A で追加した 11 件だけが失敗した。B のツリー（394 件）を A の `src/` で流すと、B で追加した 57 件のうち 50 件が失敗し、今の挙動を固定する 7 件とそれ以外のテストは成功した。
- **ミューテーション**: 計画の 13 か所に、レビューで足した要点 20 か所（実行時の index、prune の checkpoint の順序、取り消し後の index、作成直前に控える記録、I3 の出所 2 つ、syncObject の同じ位置の判定、置き換え元のメンバーと要素、移動元の除外、selector の保存、検証で解決できるフィールドだけを書くこと、全件の検証の前に参照先にしないこと、ID が空の key の停止、adopt の初回、`declaration-shrank`、置き換え元が無い場合の新しい作り直し、作成時の除外、移動元での照合の禁止、同じ型の key がある場合の案内、`referencedBy`）を加えた 33 か所をそれぞれ壊し、33 か所すべてで対応するテストが失敗した。もとの 13 か所の 1 つ（置き換え先を作成直後に参照先にする変更）は、作成時の除外（R-11）でも防がれるようになったため、もとのテストでは検出されず、`AResumedReplacementNeverPointsAtAnUndoneReplacement` が検出する。
- **旧コードとの比較**: 直したテストを、直す前の計画のコード（`src/` だけを戻したもの）で流し、再現した誤動作をテストが検出することを確かめた（392 件中 23 件が失敗。この比較を実行した時点のツリー状態は記録に残っておらず、母数の 392 と上の最終の 394 件の関係は後から再導出できない）。

## 6. 範囲外として扱わなかったもの

- レビューに挙がっていない問題は探していない。旧 PR #5 の過去のレビュー指摘（`external/resoloop/reviews/`）は新たに取り込んでいない（Spec 4.2、D-16）。
- 実機での確認（C2）、fork・上流への投稿は行っていない（ユーザの指示が要る）。
