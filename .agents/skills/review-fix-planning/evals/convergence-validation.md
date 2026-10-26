# Issue #176: 収束改善の評価記録

## 対象と結果の読み方

- 対象: `issue-to-pr` と `review-fix-planning`、共通参照 `references/convergence.md`。
- 基準: `1335f410e624355cd558029bdcdad65eaa944ed8`。改善後pilotの手順版: `442d78c`。
- 正式な設計・計画: `docs/superpowers/specs/2026-10-18-create-reso-world-issue-176-review-convergence-design.md`、`docs/superpowers/plans/2026-10-18-create-reso-world-issue-176-review-convergence.md`（リポジトリルート基準）。
- 手順の机上照合、既存helperのテスト、スキル無し／有りの意思決定pilotを区別する。pytest件数は行動改善の証明ではない。
- 新規の文面一致テスト・実装helper・schemaは作成していない。

## 従来対策との差分と机上照合

| 既存の対策 | 今回具体化した点 | 接続する場所 | 確認の範囲 |
|---|---|---|---|
| Spec/Planと担当別Task | 条件・除外範囲からTask・観測結果・検証への対応、共有前提の統合担当 | issue-to-pr 4章3・5、5章 | pilot S1、追加p/q/rの机上確認 |
| 守る条件と影響経路の表 | 前提と境界・操作順を起点に入口から終了・復旧まで追い、観測結果と実行証拠を列にする | review-fix-planning の経路表、共通参照2 | pilot S2、追加15/20の机上確認 |
| 失敗時の状態比較・安全ガード対照 | 判定の正常側・拒否側、影響する次操作、期待値の独立した根拠 | 共通参照3、自己レビューの反証 | pilot S1/S2、追加16/17の机上確認 |
| 同じ条件の再発時に設計見直し | 後続指摘の原因4分類と既存採否3分類を分離。最終変更後の経路・証拠を更新 | 再発の節、公開前判断 | pilot S2、追加18/19の机上確認 |
| 自己レビュー最大1回、権限・公開境界 | 維持。上限到達を原因解消の根拠にしない | 既存本文、共通参照冒頭と末尾 | 差分確認、ブランチ全体レビュー |

追加シナリオは issue-to-pr の p〜r（3件）、review-fix-planning の15〜20（6件）。既存JSONの method と過去の評価を今回の9件へ流用しないよう、各追加ケースに method/added を記した。9件を個別の fresh agent で実行したわけではない。小変更で帳票・全組み合わせ・文面一致pytestを増やさないことも机上で照合した。

## Pilot の実施方法と限界

- 日時: 2026-10-18 UTC。同じ S1/S2 packet、各条件1回、1回の回答に2ケース。
- pi-superagents の `sp-research`、`sessionMode=standalone`、`skill=false`。既定のロール設定を使用し、モデルを上書きしていない。tool が正確なモデル識別子を返さないため不明とし、別モデル間の比較とは呼ばない。
- baseline: スキル・Issue・Spec/Plan・evals・他の回答を読まず、ツール・変更・外部操作を禁止。改善後: 2スキルと convergence.md の読み取りだけ追加で許可。採点基準・baseline回答・evalsは渡していない。
- 共通指示: supplied facts だけを使い、各ケースの具体的な次操作と ready/not-ready を日本語500 words以下で答える。評価方法を論じず、証拠を創作しない。末尾に Report elapsed time を付けた。
- これは回答上の判断の評価であり、コマンド実行・修正・push・マージ・停止能力を試したものではない。
- baseline は主要な安全判断を既に満たした。S2 では「正規化は別関心事」と根拠なく分離し、最終変更後の全影響経路の証拠更新・公開順序を明示しなかった。改善後は現行版の根拠・経路表での証拠整備を明示した。これを観測上の差とし、全体の効果や因果関係の実証とは呼ばない。
- 改善後S1は既存の安全ガード対照まで提案した。新規変更一般への一律要求と解釈しないことは共通参照と追加r/17で机上確認したが、過剰検証の退行が無いとの独立した行動実証は未実施。
- 5回以上の独立反復による wording 比較、旧スキル有りとの比較、別モデル横断、9件各々の実行、実運用の効果・退行評価は**未実施**。全件成功率・統計的改善を記載しない。
- baselineは自身の所要時間ではなくシナリオ内の2時間を回答し、改善後は未計測と回答した。担当自身の所要時間は測定不能であり、作業全体はcontrollerの壁時計とbudget ledgerで記録する。

### 共通のシナリオ本文（原文）

```text
S1: A CLI migration Spec promises safe read/write of both single records and batch records, with no writes on invalid input. The Plan splits parser.py and apply.py to different implementers; each checks its own unit tests. Batch behavior is absent from Plan and fixture generation uses the same normalization routine as the implementation. Implementers report all tests passing. A release window closes in 10 minutes, the lead says the file-level approvals are sufficient, and two hours were already spent. Choose the next action: proceed with this Plan to PR, minimally amend before implementation, or redesign everything. Show the actual amendment or release rationale, not a generic checklist.
S2: A fatal review finding showed an importer rejected unsupported IDs too late. Only the web entry was fixed; the local import and replay entries share the assumption but are not investigated. One test proves the bad ID is now rejected; the valid-ID path and operation after rejection are untested. Engineer marks all three paths 'handled' because a warning was shared in chat and names of future tests are listed. A second review finding names the replay function. The prior fix has one successful review, the current patch changes normalization, and the manager asks to label the second finding duplicate and push now to end a costly loop. Self-review budget is one and has already been used. Decide the cause classification, completion state and exact bounded next verification/publication actions. Do not invent execution evidence. Report elapsed time.
```

### 人手での判断比較

| 観点 | スキル無し | スキル有り |
|---|---|---|
| S1: 要件欠落、独立した入力、統合担当 | いずれも提案。baseline自体は主要目標を満たす | 条件単位の保証と具体的な観測を提案 |
| S2: 同系別経路を重複として捨てない | 捨てない。因果関係は要確認 | 適用漏れと分類し、現行HEADで再現を提案 |
| S2: 両側と次操作 | 正常と拒否後を提案 | 全入口・両側・次操作を提案 |
| S2: 最終正規化変更後の証拠 | 別関心事と分離。現行版の全経路更新を明示せず | 別版レビューを根拠にせず、現行版と経路表の証拠を要求 |
| S2: 自己レビュー上限 | 上限は検証の代わりにならないとするが再レビュー有無は不明確 | 2回目をせず、再レビュー未実施の記録を明示 |
| 実際に検証・公開できたか | 未評価 | 未評価 |

## 構造・実行検証

- baselineの関連pytest: 180 passed / 25.64秒 / exit0。
- 改善後のskill-efficiency-check: 両スキル exit0、Issues none。両方の日本語descriptionに `description may not clearly say when to use the skill` のwarning。descriptionは変更していない。issue-to-prの `no references found` suggestionは checker がスキル外への相対参照を数えないためで、リンク先の実在を別途確認した。
- 最終JSON/ID検査: issue-to-pr 18件、review-fix-planning 20件、重複なし。両SKILL.mdの相対Markdownリンク先が実在、`git diff --check` exit0。
- READMEの非ワールド3検証（2026-10-18 21:46:36〜21:57:04 UTC）: `uv run pytest tests/skills .agents/skills .agents/scripts tools` は **2568 passed / 1 skipped / 626.14秒 / exit0**。`bash .devcontainer/run-tests.bash` は **33 test(s) PASS / 444.9秒 / exit0**。`bash scripts/check-layout.sh` は **PASS / 0.7秒 / exit0**。同時起動し、いずれもforegroundで終了を待ち実ログを確認。全体pytestには関連helperテストも含む。
- pytestの1件のskipについて、この実行のログは `-rs` を付けていないため理由の詳細は表示されていない。成功件数へ加えない。
- 最後のブランチ全体レビュー（sp-review、`1335f41..2c2c4a5`）: Critical 0 / Important 1 / Minor 0。承認済みSpecの反映だけの入口で公開前照合を迂回できる指摘を確認し、実装後4へ接続した。eval19をこの入口へ具体化、机上で経路をたどって確認した。変更後に追加の行動pilot・再レビューは実施していない。初回のNEEDS_CONTEXTは未完了で、差分ファイルを渡した1回の再試行だけが完了レビューである。
- 修正後の最終検証（22:03:39〜22:14:39 UTC）: pytest **2569 passed / skip 0 / 659.23秒 / exit0**、環境 **33 test(s) PASS / 454秒 / exit0**、layout **PASS / 0.5秒 / exit0**。構造checker、JSON/ID、相対参照の実在、diff checkも再確認して成功。追加の手順は文書のみであり、fixture/fakeや実行コード・テストは変更していない。

## 未実施・残る追跡

mainへの取り込み、運用でのレビュー修正回数・費用・退行の追跡は未実施。採用回数・レビュー数だけを増やす運用へ戻らず、今後の実例では条件の欠落、同原因の別経路、最終版証拠の不足を追跡する。新しい実モデル評価の反復は別の明示された予算で実施し、この資料の机上照合で代用しない。

## 回答の記録

以下は両条件の生の回答。スキル本文へ実行規則として取り込むものではない。

### スキル無し

**S1: 最小限の修正を実装前に入れる — not ready（Plan のまま PR へ進めない）**

理由: バッチ挙動が Plan に無い。fixture が実装と同じ正規化関数を使うため、同じ思い違いをテストで検出できない。parser と apply を別担当にすると、どちらの単体テストも境界を見ない。

Plan に入れる修正:
- 単体とバッチで振る舞いを対称に列挙する。単体は正常1件／不正1件、バッチは全件正常／混在／全件不正／空。各ケースの期待値を「戻り値」と「保存先の状態が前後で一致するか」で書く。
- 不正入力で書き込みゼロを、apply が呼ばれない、または呼ばれても保存先が前後一致することで確かめる。
- fixture は実装の normalize を通さず、生の入力（辞書リテラル等）を手で構成する。
- parser→apply を通す結合テストを1本、どちらかの担当が持つ。共有仕様（単体・バッチの形、エラー型、無書き込み保証）の所有者を1人決める。
- 承認はファイル単位ではなく上記の振る舞い単位で取り直す。10分の窓は未検証のバッチを公開する理由にならず、2時間の消費も判断を変えない。

**S2**

原因の分類: 修正範囲の特定ミス（共有された前提を1つの入口だけ直した）と、完了主張の未検証（チャットの警告と将来のテスト名は実行証拠ではない）。現在の patch の正規化変更は別関心事で、レビュー面を混ぜている。

完了状態: 第1の指摘は未完了。不正 ID の拒否しか確認しておらず、正常 ID 経路と拒否後の状態が未検証。第2の指摘は重複と言えない — 同じ前提が replay にもあるか未確認で、根因が同じでも入口が違う。ラベル付けにはコード確認が要る。自己レビュー枠の消費はテストの代わりにならない。

次の行動（上限付き）:
1. replay とローカル取り込みの入口を読み、同じ「拒否が遅い」前提があるか確認する（読み取りのみ、判断まで編集しない）。
2. テスト: 正常 ID が通ること、拒否後に部分書き込みが無く後続操作が壊れないこと。replay は不正 ID と正常 ID の各1本。
3. 正規化の変更はこの PR から分離し、ID 検証の修正だけをレビュー面に残す。
4. 公開: 第1の指摘の修正は上記テストが通ってから push。第2の指摘は重複とせず、入口の確認後に別 commit で直す。今すぐの push はしない。

経過時間: S1 は2時間（供給された事実）。S2 は経過時間の記載が無いため報告できない。

DONE_WITH_CONCERNS — S2 の経過時間は供給された事実に無い。

### スキル有り

## S1 — 次は「実装前に最小限の修正」（not ready）

Spec の条件「バッチの read/write」「不正入力で書き込みなし」が Plan の Task に無く、parser.py / apply.py の分担では parse→apply をまたぐ条件の担当が不在。担当別の単体テスト成功は条件単位の保証にならない。また fixture が実装と同じ正規化を通るため、期待値が実装と同じ誤前提を共有し、独立した根拠にならない。

実装前の追加（Plan / Spec に追記）:
1. Task「統合担当」を追加: 単一/バッチ × 正常/不正の 4 象限を、読取→変換→書込→終了の順に観測。parse と apply の両方を通す。
2. 不正入力の検証は、対象ファイルの有無・バイト列・mode・バックアップ・一時ファイル・symlink 参照先を書込前後で比較（終了コードだけを見ない）。負例は異常 1 つ。バッチ内 1 件不正で残りが書かれないことも比較。
3. fixture は正規化を通さない生の入力（外部仕様の例、移行前 CLI の出力）から独立に作り、期待値も同じ経路で作らない。
4. ガードを 1 つ外した対照で負例が落ちることを隔離 mktemp worktree で確認。

公開判断: 10 分では上記の証拠は揃わない。リリース枠のためにバッチ保証を落とすのは Spec の保証を狭める変更で、委任範囲外なので独断で確定しない。単一レコードのみに絞るなら既知の制限として Spec と PR に明示し、承認を得てから出す。2 時間の消費やリードの「ファイル単位で十分」は、要件欠落と独立根拠の不在を埋めない。

## S2 — 分類は「既存原因の適用漏れ」、未完了

2 件目は同じ守る条件の 2 回目（きっかけ 1）で、重複として捨てない。原因は「未対応 ID を副作用の後に拒否」で、web だけ直し local import と replay が同じ前提の別入口。設計の見直しに引き上げ、点の修正を続けない。

完了状態: 未完了。3 経路を handled とした根拠はチャットの注意共有と将来のテスト名で、実行証拠ではない。拒否テスト 1 本は判定の片側のみ、正当 ID 経路と拒否後の操作は未確認。先行修正のレビュー 1 回成功も、正規化を変えた現行パッチの根拠にならない。

次の境界付き検証・公開:
- 現行 HEAD の commit 済み内容で local import / replay の誤動作を隔離 worktree で再現し、経路表に結果を記す。
- 修正は条件を 1 か所で保つ形（3 入口共通の事前検証、または validate→apply 一本化）を第一案に、点の修正・保証を狭める案と比較し理由を Spec に残す。
- 全入口で拒否前後の状態全体を比較し、正常 ID の成功、拒否後の次操作、異常 1 つの負例、ガードを外した対照を確認。
- 自己レビューは 1 回使用済みなので 2 回目をしない。再レビュー未実施を Spec と状況コメントに書く。
- 証拠が経路表で揃ってから push し、PR にレビュー状況・判断・結果を投稿。duplicate 指定と即 push は受けない。

経過時間: 未計測（測定手段なし。実行証拠を作らない）


# Issue #189: 要件照合・委任確認の限定評価

## 対象・変更前の確認

- 対象は review-fix-planning の本文、共通参照1章、implement の引き渡し。初回実装の Spec → Plan → Task の照合は維持する。
- 基準は `5b2c535`。実装開始時の `3fcdae8` と基準との間で、今回の5ファイルに差分が無いことを `git diff --exit-code` で確認した（exit 0）。
- 変更前の確認は 2026-10-27、pi-superagents の `sp-research`、`sessionMode=lineage-only`、同じ回答に2ケース、各1回。読み取り専用の子が返した回答を controller が要約・引用して保存した。子の所要時間は未計測。正確なモデル識別子はこの要約からは確認できない。
- 以下は保存された要約に基づく観測であり、未観測の失敗を補わない。コマンド実行・修正・公開を伴わない判断シナリオである。

### ケースの要約と観測

| ケース | 与えた状況 | 変更前の観測 |
|---|---|---|
| A: 要件照合と共有条件 | directory importer の CLI/interactive 両入口で未対応 URI を無変更で拒否、network URL は除外。既存 Spec が保証し、Plan は別 worker だが parser 状態を共有。CLI の致命的な状態変更は確認済み。残り15分、interactive worker の local tests は green、修正は staged という架空の状況 | 現行 committed HEAD の確認 → 分類 → 経路表 → 再発判定 → 方針の順を挙げ、要件対応の作成を経路表より前の独立した段として挙げなかった。保証の記録と Plan 修正は後段の Spec 内容に挙げた。共有状態・操作順は統合担当が確認するとした |
| B: 縮小への委任 | 同じ PR で local 入力の field loss が再発。承認済み Spec は local と symlink を保証。完遂依頼で縮小委任は無い。保証維持は1時間、symlink を外すと5分、残り10分、2回のレビューによる費用・収束圧力。明示委任あり・計画のみの場合も対比 | 「Narrowing is not allowed without explicit delegation.」「Maintain the approved local+symlink guarantee and choose a structural fix.」と回答。無断縮小の行動失敗は観測していない |

A では「The integration owner — not either entry worker — owns the shared parser state/order check.」と回答しており、統合担当の必要性も変更前から提案済みである。子は共通参照の全文を読み、1章を自発的に参照したため、旧 SKILL が指定する2・3章だけを読む経路との厳密な対照ではない。架空の staged 変更を実際の worktree の停止条件と混同する回答もあり、補助設定の影響を排除できない。

改善対象は、分類後かつ経路表・方針より前の要件対応、その必須読取経路、implement への引き渡し、保証縮小の選択前の委任確認を明示的につなぐことである。保証維持・統合担当を初めて獲得した、無断縮小を再現して防いだ、収束率が改善した、とは主張しない。

## 変更後の行動確認と限界

controller が `627402a` の文書を使い、変更前と同じ2ケースを新しい sp-research 子へ1回だけ渡した（2026-10-27、同期呼び出し54.4秒、子の自己計測は unknown）。PR・ファイルを実際に変更する評価ではなく、判断回答の確認である。回答はセッション領域の `green.md` に保存した。

- A: 方針の前に PR・Spec・Plan の条件対応、既存 Spec の対応メモ、統合担当、implement への除外範囲・共有前提・必要な証拠を挙げた。ただし回答の行動順は **要件対応→分類** で、指定する **分類→要件対応→経路表→方針** と一致しない。経路表は記録項目に挙げたが、行動順の明示も十分ではない。全面的な GREEN や完全遵守とは判定しない。
- B: 未委任の縮小・時間圧力による停止を選ばず local＋symlink の保証維持を選択した。明示委任ありなら根拠と許可内容を記録して縮小を選べ、計画のみなら既存の承認手順へ進むと対比した。
- task review は文書の仕様適合・品質を承認した一方、この順序不一致と既存 description warning を非ブロッキングの観測として挙げた。文書の構造確認と、実際のモデルが完全に従うことは分ける。

実装担当から別 agent・モデル CLI は起動していない。追加した eval 26/27 のケース単独の行動評価、独立反復、別モデル横断、実運用のレビュー修正回数・費用・退行の測定は未実施であり、構造確認や pytest の成功で代用しない。変更前にも保証維持を選んでおり、行動改善の因果関係は未実証のままである。


## 構造・実行検証（実装担当）

- 参照経路を机上で確認: SKILL 手順4の分類 → 共通参照1章の要件対応 → 経路表 → 手順5の方針選択。要件対応は Spec の必須内容とし、implement の prompt に条件・除外範囲・共有前提・統合担当の確認・必要な証拠を渡す。保証縮小は設計見直し手順3で選択前に委任を確認する。委任外の完遂は保証維持、計画のみは既存の承認手順へ進む。
- JSON 解析・ID/name の一意性: 27件、旧25件は変更せず2件だけ追加。変更対象 Markdown 4ファイルの相対リンク26件はすべて実在。`git diff --check` は exit 0。
- 変更は指定5ファイルだけ。frontmatter、RoleInput の5キーと表、共通参照2・3章、execution 2章以降は未変更。過去の評価記録は元のバイト列を維持したまま本節を追記した。新しい帳票・helper・schema・pytest は作っていない。
- `uv run --no-project python /home/vscode/.pi/agent/npm/node_modules/@howaboua/pi-skill-skill-creator/skills/skill-creator/scripts/skill-efficiency-check.py .agents/skills/review-fix-planning`: exit 0、Issues none。`description may not clearly say when to use the skill` の warning 1件。description は未変更。
- 指定の関連検査 `uv run pytest tests/skills .agents/skills` は1回実施し、**697 passed / 412.20秒 / exit 0**（2026-10-27 02:51:09〜02:58:03 +09:00）。
- 全体の Python 検査も `uv run pytest -rs` で同期実行し、**1237 passed / 422.45秒 / exit 0**（02:59:12〜03:06:15 +09:00）。pyproject.toml の testpaths は README の非ワールド pytest と同じ4ディレクトリ。失敗・skip・pytest の warning は無し。
- 上の検査は開始時 HEAD `3fcdae8` に今回の作業差分を加えた版で実施した。最終の評価記録・Spec/Plan 更新後の clean HEAD での非ワールド3コマンド、変更後の行動確認とブランチ全体レビューは controller の担当であり、ここで実施済みとはしていない。
