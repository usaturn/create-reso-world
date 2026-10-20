# Issue #207 マージ済み・確認未了の PR を merged:false と報告しないようにする

- 文書管理・対象: `usaturn/create-reso-world`、Issue #207（ラベル `bug`。親 Issue・依存・コメントなし。関連: PR #203、#155、#156）
- 基準 HEAD: `f2350a4`（`origin/main`、2026-10-20）。Issue が指す `c4f7ed0` から `finalize.py`・`loop.py` に変更は無い
- 状態: `draft`。内容の承認は記録しない
- 実行許可: 利用者が 2026-10-20 に `/issue-to-pr #207 --merge` と指示した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続け、PR の作成後に PR 修正ループを回し、修正不要と確かめられたらループの中の `finalize.py` がマージと関連 Issue の更新まで行う。これは実行の許可であり、この文書の内容の承認ではない。以下の判断は、確認を取らずに決めたエージェントの判断である
- ループの設定: `loop.py check-options` の出力は `options={"max_cycles": 3, "assign": {}, "template": "/workspaces/reso-world/.devcontainer/agent-runner.toml", "config": null}`。利用者はループ用のオプションを書いておらず、どれも既定の適用である。レビュアーは `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正の担当は `claude-opus`、自己レビューと修正の確認は `self`（設定のとおり）
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、利用者の指定ではない
- Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue207-finalize-merged-state.md`

## 意図

`finalize.py` は、PR の状態を読んだ後、head・Spec・判断の記録の判定に通ってから `merged` を代入する。判定で止まると、GitHub が `state=MERGED` を返していても `merged:false` を返す。マージの操作の後の確認だけが失敗したときも、操作の前の `false` が残る。PR 修正ループの `cycle_end` は実際の PR を読み直すのに、finalize の `merged` が true のときしか照合せず、false ならそのまま run・cycle の結果に保存する。マージは取り消せない操作なので、実際の状態が報告と復旧の判断から失われる。

止まること（`outcome: stopped`）は今までどおりにし、「成功の条件を満たしたか」と「マージ済みか」を分ける。`merged` は観測した事実だけを表し、未マージを確かめていないときは `false` と言わない。

## 確認した事実（2026-10-20、`f2350a4`）

- `finalize.py`
  - `finalize` の結果の既定（336 行）と最後の代入（432 行）は `merged=False`。CLI の `main`（458 行）も、入力ファイルを読む前の結果を `merged: False` にする
  - 最初の読み取り（354-357 行）と、マージ直前の読み取り（387-390 行）は、`check_view` の後に `merged = view["state"] == "MERGED"` を代入する。`check_view` が head の違いで例外を投げると、MERGED を読んでいても `merged` は前の値（`False`）のまま
  - マージ（397-402 行）の後の確認（403-407 行）で `pr view` が失敗すると、`merged` は操作の前の `False` のまま
  - GitHub に問い合わせる前の入力の誤り（記録・検証の記録・マージしてよい範囲・`--spec-commit`）も `merged:false` で返り、`gh` を呼ばない（テストが `gh.calls == []` を確かめている）
  - 同じ head でマージ済みのとき、記録が投稿済みなら Issue の更新だけを続け、無ければ `merged:true` の `stopped` を返す（既存の経路）
- `loop.py`
  - `_read_finalize`（1384-1399 行）は `merged` を真偽値に限る
  - `cycle_end`（1489-1529 行）は、記録の結果が `no_fix_needed` のとき、finalize の `merged` が true なら実際の PR のマージと head を照合する。false のまま `stopped` なら、実際の PR を見ずに `merged=False` を保存する。記録の結果が `stopped` のときも `merged=False` を保存する
- 文書: review-fix-planning の `SKILL.md` の結論 2 の手順 7、`references/execution.md` の 3.3・3.4 節、PR 修正ループの `SKILL.md` の「最終化の停止」、`references/records.md` の 6 章が `merged` を説明する。issue-to-pr の `SKILL.md` はループの結果（run の `merged`）だけを読む
- 再現（Issue の表と同じ）: `test_finalize.py` の `FakeGh` で、Spec の親の head・別の head でマージ済み、投稿後に別の head で手動マージ、マージの後の `pr view` だけが失敗、の 4 経路が `merged:false` を返す。`cycle_end` は、偽の PR をマージした後に `stopped`・`merged:false` の finalize の結果を渡すと、返り値と `run.json` の両方が `merged:false` になる

## 受け入れ条件

| ID | 条件 | 出典 |
| --- | --- | --- |
| A-1 | Issue の表の各経路で、観測した MERGED を失わず、head の違いは停止したまま報告する。意図しないマージ・コメント・Issue の close を足さない | Issue |
| A-2 | マージの成功の後の応答・確認の障害を模したケースで、未確認と未マージを区別し、状態を読み直して復旧できる | Issue |
| A-3 | `cycle_end` と保存する run・cycle の結果が、実際の PR のマージ状態を失わない。正常完了の head・Spec の照合は保つ | Issue |
| A-4 | 正常な OPEN、同じ head の既存のマージ、Issue の更新の再開、GitHub に問い合わせる前の入力の拒否が、引き続き正しく動く | Issue |
| A-5 | テストは偽の `gh` とローカルの Git の fixture で行う。実際のサービスのマージや有料のエージェントで再現しない | Issue |

## 判断（決定記録）

各項目に、選択した案・検討した別案・選択理由・委任の指示または停止の条件を書く。

### D-1 finalize の `merged` を true・false・null の 3 値にする

- 選択した案: `merged` は、finalize が最後に観測した PR のマージ状態である。`true` はマージ済みを観測した、`false` は未マージ（OPEN か CLOSED）を観測し、その後にマージを依頼していない、`null` は確かめられていない（GitHub に問い合わせる前に止まった、PR の状態を読めなかった、マージを依頼した後に状態を読めなかった）
- 検討した別案:
  1. `merged` は真偽値のまま、`merge_state`（`merged`・`not_merged`・`unconfirmed` など）を足す
  2. マージの後の確認の失敗を、finalize の中で再試行する
  3. マージの依頼が終了コード 0 なら `merged:true` とみなす
- 選択理由: 別案 1 は、`merged` だけを読む側が今までどおり `false` を未マージと読み違える。同じ事実を 2 つの値で持ち、食い違いうる。別案 2 は再試行も失敗しうるので、未確認の結果は残る（再取得は再実行で行う。D-4）。別案 3 は Issue が不適切と明記している。`null` は JSON で「値が分からない」を表す普通の形で、読む側の変更は `loop.py` の 1 か所と手順書で済む
- 委任の指示・停止の条件: `outcome` の意味（`no_fix_needed` だけが完了）は変えない。`merged:true` の `stopped` は今までどおり停止である

### D-2 PR の状態を読んだら、判定より先に `merged` を更新する

- 選択した案: `pr view` の応答を受け取るたびに、`check_view`・Spec の比較・判断の記録の照合より先に、`state` から `merged` を決める。`MERGED` なら `true`、`OPEN`・`CLOSED` なら `false`、それ以外（読めない値）なら `null`。マージは取り消せないので、一度 `true` を観測したら後の応答で戻さない。`gh pr merge` を呼ぶ直前に `null` にし、その後の読み取りで決め直す
- 検討した別案:
  1. `check_view` が例外に `merged` を載せる
  2. `state` に加えて `mergedAt` が無ければ `null` にする
- 選択理由: 判定の種類を増やすたびに例外へ載せ忘れる余地がある（別案 1）。観測と判定を分ければ、どの判定で止まっても観測が残る。`state` は GitHub がマージ済みかどうかを表す値で、完了の判定（マージの後の確認）は今までどおり `mergedAt` と head も確かめる。観測にまで `mergedAt` を要求すると（別案 2）、崩れた応答でマージ済みの事実を捨てる
- 委任の指示・停止の条件: head が違えば今までどおり止まり、投稿・マージ・Issue の更新をしない

### D-3 別の head でマージ済みのときの停止理由を分ける

- 選択した案: `check_view` で head が違い、`state` が `MERGED` なら `external: PRが検証済みHEADと別のHEADでマージされた` で止める。ただし `--spec-commit` で、head が検証した HEAD（Spec の commit の親）のままマージされていたら `external: Specのcommitを載せる前に、PRが検証したHEADのままマージされた` で止める（最終レビューの指摘で追加。入ったのは検証済みのコードで、欠けているのは Spec の commit だけなので、検証していないコードが入ったと読ませない）。OPEN で head が違う停止（`external: PRのHEADが検証済みHEADから変わった`）と、`--spec-commit` の `wait_for: head` は今までどおり
- 検討した別案: 停止理由を変えず、`merged:true` だけで分かるようにする
- 選択理由: OPEN で head が動いたなら新しい head でやり直せるが、別の head でマージ済みなら再実行しても完了しない。何がマージされたかを人が確かめる必要があり、次の一手が違う
- 委任の指示・停止の条件: なし

### D-4 `null` の復旧は、同じ入力での再実行で状態を読み直す

- 選択した案: finalize の中では再試行しない。手順書に、`merged:null` を未マージと報告せず、原因を直してから同じ記録・本文・検証の記録で再実行すると書く。再実行は最初に PR の状態を読み直し、同じ head でマージ済みで、このサイクルの記録が投稿済みなら Issue の更新だけを続けて完了する（既存の経路）。OPEN なら今までどおり照合してマージする。報告するときは、`gh pr view <PR> --repo <repo> --json state,mergedAt,headRefOid` で読み直した状態を書く
- 検討した別案: `null` のときに finalize が別の回復用のコマンドを返す
- 選択理由: 既存の再実行の経路が、状態の読み直しと、マージ済みのときの Issue の更新を兼ねる。新しいコマンドは要らない。`--match-head-commit` と base の照合があるので、OPEN の PR を再実行でマージしても、検証していない head や base は入らない
- 委任の指示・停止の条件: GitHub に問い合わせる前の入力の誤りは、再実行しても同じ理由で止まる。`stop_reason` の `environment:` を見て入力を直す

### D-5 GitHub に問い合わせる前の停止は `merged:null`

- 選択した案: 記録・本文・検証の記録の誤り、マージしてよい範囲の外、`--spec-commit` の誤り、CLI の入力ファイルを読めない、で止まったときは `merged:null`。`gh` を呼ばない既存の条件は保つ
- 検討した別案: 今までどおり `false` にする
- 選択理由: PR の状態を見ていないので、未マージを確かめた結果と同じ値にしない（Issue の対応方針）
- 委任の指示・停止の条件: なし

### D-6 `cycle_end` は、停止のときに実際の PR のマージ状態を保存する

- 選択した案:
  - `_read_finalize` は `merged` に `true`・`false`・`null` を受け付ける
  - finalize の結果が `no_fix_needed` なら、今までどおり finalize の `merged` が `true`、実際の PR がマージ済み、head が `spec_commit`（無ければサイクルの HEAD）と同じことを求め、食い違えば `merge_mismatch` で止める
  - finalize の結果が `stopped` なら、run・cycle の `merged` を `cycle_end` が読んだ実際の PR の `merged` にする。finalize の `false`・`null` で上書きしない。finalize が `true` なのに実際の PR がマージされていなければ `merge_mismatch` で止める（マージは戻らないので、どちらかの読み取りが誤っている）。head が違うマージは `stopped` のままで、停止理由は finalize のものを保存する
  - 判断の記録の結果が `stopped`（finalize を呼ばない結論 3）でも、`merged` を実際の PR の値にする
  - `fixes_pushed` で PR が open でないときの `pushed_head_mismatch` の文に、`merged` を足す
- 検討した別案:
  1. finalize の結果の `merged` だけを使い、`null` を `false` として保存する
  2. 実際の PR がマージ済みなら、finalize の `stopped` を `no_fix_needed` に直す
  3. 判断の記録の結果が `stopped` のときは今までどおり `false` にする
- 選択理由: run・cycle の `merged` は真偽値で、`cycle_end` は実際の PR を読んでいる（読めなければ終了コード 5 で止まり、何も保存しない）。観測した事実を保存すれば、finalize の `null` を推測で埋めずに済む（別案 1 は Issue の不具合そのもの）。別案 2 は、想定外の head を正常完了として受け入れることになる（Issue の対応方針で禁止）。別案 3 は、結論 3 の間に人がマージした事実を同じ形で失う
- 委任の指示・停止の条件: `merge_mismatch` の条件は、`no_fix_needed` では弱めない

### D-7 テストの範囲

- 選択した案: `test_finalize.py` に、Issue の表の 4 経路、マージの依頼自体の失敗、確認の失敗からの再実行での復旧を足す。GitHub に問い合わせる前の停止を確かめる既存のテストは、期待を `merged is None` に直す。`test_loop_state.py` に、`stopped`・`merged:false`、`stopped`・`merged:null`、`stopped`・`merged:true`（別の head のマージを finalize が観測した結果。最終レビューの指摘で追加）の finalize の結果で実際の PR がマージ済みの場合、finalize が `true` なのに PR が未マージの `stopped` の場合、判断の記録が `stopped` で PR がマージ済みの場合を足す。偽の `gh`（`FakeGh`・`FakeGitHub`）とローカルの bare リポジトリだけを使う
- 検討した別案: 実際の PR で手動マージを再現する
- 選択理由: 取り消せない操作で、費用もかかる（受け入れ条件 A-5）
- 委任の指示・停止の条件: なし

## 変更しないもの

- `outcome` の値と意味、停止理由の接頭辞（`permission:`・`environment:`・`external:`）、`wait_for`・`base_moved`
- マージの方法（`--merge --match-head-commit`）、base の照合、CI の確認、記録の照合、closing Issue の扱い
- run・cycle の記録の形（`merged` は真偽値のまま。`FinalizePart.result` には finalize の結果をそのまま保存する）
- `upsert_pr_comment.py`・`review_records.py`・`.agents/review-records.md`・issue-to-pr の `SKILL.md`（ループの結果だけを読み、その `merged` は真偽値のまま）

## 検証

- `uv run pytest tests/skills .agents/skills .agents/scripts tools`（README の「テスト」）と、`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`
- リポジトリには ruff・pyright の設定もコマンドも無いので、静的解析は行わない。変更したテストを先に失敗させてから実装する
- 手順書の差分を、D-1〜D-6 の実装とテストに 1 つずつ対応させる
