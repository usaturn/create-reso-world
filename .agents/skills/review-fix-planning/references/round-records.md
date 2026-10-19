# 判断の記録の作り方と投稿

review-fix-planning の planner が、サイクルの判断を記録（review-records）にして、状況コメントとして投稿する手順である。形式・検査の規則は `.agents/review-records.md` が定義元で、検査は `.agents/scripts/review_records.py` が行う。この文書は、それを planner の作業の順に並べ、[SKILL.md](../SKILL.md) の 3 区分と三択の結論に対応させたものである。規則が食い違って見えるときは `.agents/review-records.md` に従う。ただし、マージしてよい範囲の外のリポジトリへの状況の投稿を必須にしない例外（6 章）は、外部のリポジトリへの書き込みを増やさないための SKILL.md の規則である。

変数は SKILL.md と [execution.md](execution.md) のもの（`PR_REPO`・`PR_NUMBER`・`MODEL_NAME`・`SESSION`）を使う。`TOPLEVEL` は読んだスキルの source checkout で、SKILL.md の「第1引数の解決」の `REVIEW_TOOL_ROOT` と同じパスである（スキルを親の main checkout から読んだときは、手順 2 の共通 context の `tool_root` とも同じになる）。

## 1. 前の状態を読む（手順 1）

各ツール呼び出しで、認証済みの login の取得・検査から利用までを 1 つのブロックで実行する（シェルの変数は次の呼び出しに残らないと考える）。

```bash
TRUSTED_LOGIN="$(gh api user --jq '.login // empty')" && [ -n "$TRUSTED_LOGIN" ] || {
  printf '%s\n' '認証済み利用者の login を取得できないため停止する。' >&2
  exit 1
}
gh api --paginate --slurp "repos/$PR_REPO/issues/$PR_NUMBER/comments" \
  | uv run --no-project python "$TOPLEVEL/.agents/scripts/review_records.py" fold \
      --repo "$PR_REPO" --pr "$PR_NUMBER" --trusted-login "$TRUSTED_LOGIN"
```

- 終了コード 0: 出力の `rounds` が記録済みのサイクル、`decisions` が判断の現在の状態、`ignored_comments` が読まなかったマーカー付きのコメントである。このサイクルの番号は、`rounds` の最大の `round` + 1（記録が無ければ 1）。ただし、計画のみで投稿したサイクル（`stopped` の `permission:`）を承認・push の後に更新するときは、新しい番号を取らず、そのサイクルの番号と `reviewed_head` をそのまま使う（同じサイクルの更新。判断も同じ記録を基にする）
- login を取れない、終了コード 65（壊れた記録・ほかの PR の記録）、`gh` の失敗: 判断を引き継げないので、ここで止まる（SKILL.md の結論 3。壊れた記録は環境、`gh` の失敗は外部障害）。コメント ID と問題を報告する。利用者がコメント ID を指定したときだけ、`--exclude-comment <ID>` を付けて読み直す
- サイクルのマーカーの無い旧形式の状況コメントしか無い PR は、記録が無いものとして 1 から数える。旧形式で「対応しない」とした指摘がこのサイクルの入力にあれば、`new` として記録し、`reason` に旧形式のコメントの ID を書く

## 2. レビュアーの構成（`seats`）

レビューディレクトリの `<model>.md` ごとに 1 件。`findings/`・`verified/`・`runs/` はレビュアーではない。

| キー | 値の取り方 |
| --- | --- |
| `review_file` | ファイル名から `.md` を除いたもの |
| `model`・`runtime` | 先頭の `- レビュアー: <モデル>（ランタイム: <ランタイム>）` の行。行が無い旧形式・様式外は、`model` にファイル名、`runtime` に `unknown`、`note` に理由 |
| `file_head` | `## Review history` の最後の行の HEAD（先頭 12 桁）。表の無いファイルは、ファイルが示す対象 HEAD。分からなければ `unknown` |
| `mode` | 同じ行の Mode（`Initial`・`Update`）。表の無いファイルは `Initial` |
| `rerun` | `file_head` が `reviewed_head` の先頭 12 桁と同じときだけ `true` |
| `merge_recommendation` | `Request changes`・`Needs manual verification`・`Approve` のどれかをそのまま。無い・ほかの文言なら null にし、原文を `note` に書く |

- `reviewed_head` は、このサイクルで判断の対象にした PR の head（SKILL.md の `HEAD_SHA`、全桁）で、再実行したレビュアーがレビューした HEAD と同じである。`rerun` が `true` のレビュアーが 1 人もいなければ `stopped` 以外の記録を作れないので、SKILL.md の手順 2 のとおり止まる（完遂では結論 3。次の操作は「現行の HEAD でレビューを取り直す」）
- `rerun` が `false` のレビュアー（古いレビュー）は、状況コメントの「入力から外したファイル」に理由とともに書く。判断済みの指摘は引き継ぎで済ませ、未判断の指摘だけを検証する
- 指摘 ID の無いレビューファイルは、planner が `planner-<n>` を付け、そのレビュアーの `note` に書く
- 新しい記録（v2）は、`planner` と各 `seats` に `provenance`（`.agents/review-findings.md` 3.1 節の全キー）を書く。測れない値は `unknown` にし、設定の値や別の試行の成功で埋めない

## 3. 判断（`decisions`）

このサイクルの入力にある指摘（`rerun` が `true` のレビュアーの active・Pending previous findings・Unverified candidates と、古いレビュアーの未判断の指摘）と、前の状態で `fix` の判断を、すべてどれかの判断の `sources` に含める。Decided findings の指摘は入力に含めない。

SKILL.md の 3 区分を、次のとおり `state` に写す。

| SKILL.md の区分 | `state` | 必須の欄 |
| --- | --- | --- |
| 解消済み | `resolved` | `reason` に根拠（コミット・該当行） |
| 対応する | `fix` | `reason` に、致命的である理由（実在する構成で到達できる発生条件）と、(a)〜(d) のどれに当たるか |
| 対応しない | `skip` | `reason` に一行の理由、`revisit_when` に見直す条件 |

- `hold` は使わない（判断保留の区分は無い）
- `unverified` は、結論 3（`stopped`）の記録でだけ使う。停止の原因で確かめ終えられなかった指摘に付け、`unverified_reason` に足りない確認を書く。未確認を残したまま結論 1・2 にしない（SKILL.md「未確認は結論ではない」）
- `severity` には、判断に使ったレビューの重大度のラベルを写す（`sources` がすべて `U-<n>` なら null）。採否の根拠にはしない
- `d1` は書かない。`carry_over` は、「対応しない」で既存の Issue か別 Issue の候補があるときだけ書く
- `pr_relation` は、持ち込み `introduced`・顕在化 `surfaced`・既存 `preexisting`・不明 `unknown`
- `change` は、新規 `new`・引き継ぎ `inherited`・変更 `changed`（`previous_state`、前が `skip` なら `new_evidence` も）

| Spec での決定 | JSON |
| --- | --- |
| 指摘の参照 `<ファイル名>#<ID>@<検出時 HEAD 12 桁>` | `id`（最初の出典の参照。分けるときだけ `/<部分>`）と `sources`（まとめた参照すべて） |
| 位置と発生条件 | `summary`（1 行）、`locations`（`reviewed_head` での `path:line`） |

参照の出所が、レビューファイル以外のとき:

- 修正の確認（fix-check）が新たに見つけた問題: `fix-check#V-<n>@<確かめたローカルの HEAD の先頭 12 桁>`（`.agents/review-records.md` 2.1 節）
- 修正後の自己レビュー（self-review の役割の pr-review。保存名は `<model>-commit-<全桁の SHA>.md`）の指摘: そのファイル名から `.md` を除いたものを `<ファイル名>` にした通常の参照 `<model>-commit-<全桁の SHA>#<ID>@<HEAD の先頭 12 桁>`
- planner が確認の途中で見つけた PR の欠陥（SKILL.md の手順 3 の「自己確認」）: `planner#S-<n>@<reviewed_head の先頭 12 桁>`（n は 1 から）。`severity` には planner の見積もりを書く（採否の根拠にしない）。この取り決めは移植先のもので、記録の検査は参照のファイル名の形だけを確かめる

前のサイクルの判断の扱い（`.agents/review-records.md` 8.2・8.4 節）:

- 前のサイクルで `fix` の判断は、出典にかかわらず修正後の HEAD で確かめる。解消していれば `resolved`（`changed`、`previous_state: fix`）、していなければ `fix`（`inherited`）
- `skip` は引き継ぐ（`inherited`）。見直すのは新しい根拠（記録に無い実行した再現、別の利用経路・結果を示す再現、発生条件を変えるコードの変更、利用者の指定）があるときだけで、変えるなら `changed`・`previous_state: skip`・`new_evidence` を書く。言い換え・別のレビュアー・重大度の表記だけは新しい根拠ではない
- `resolved` の問題が再現したら、`changed`（回帰）にする
- 記録済みの参照を別の判断に移さない。同じ問題だと後で分かった 2 つの判断は、一方を `skip` にし、`reason` と `revisit_when` に他方の判断 ID を書く

## 4. 結果（`outcome`）

| SKILL.md の結論 | `outcome` | 追加のキー |
| --- | --- | --- |
| 結論 1: 修正して push | `fixes_pushed` | `commit`（push した完全な SHA） |
| 結論 2: 修正不要としてマージ | `no_fix_needed` | ― （マージ・Issue の更新が終わったかは `finalize.py` の結果で確かめる） |
| 結論 3: 停止 | `stopped` | `stop_reason`: `permission: <具体的な障害>`・`environment: <…>`・`external: <…>` |

- `no_fix_needed` は、前の状態にこのサイクルの判断を重ねた結果に `fix`・`hold`・`unverified` が残らないときだけ照合を通る。前のサイクル（旧形式の記録を含む）に `hold`・`unverified` が残っていれば、このサイクルで判断し直して `changed` で記録してから終える
- 旧 `awaiting_approval`・`stopped_*` は読むだけで、新しい結果として書かない。前の記録は変換しない

## 5. ファイルを作って検査する

記録は Write で `$SESSION/round.json` に書く（`recorded_at` は書いた時刻の UTC）。本文（見出しから作業結果まで）は SKILL.md の「作業終了前の PR 投稿」の雛形に従う。

投稿の前に検査する（login のブロックは 1 章と同じく、同じ呼び出しの中で実行する）。

```bash
TRUSTED_LOGIN="$(gh api user --jq '.login // empty')" && [ -n "$TRUSTED_LOGIN" ] || {
  printf '%s\n' '認証済み利用者の login を取得できないため停止する。' >&2
  exit 1
}
uv run --no-project python "$TOPLEVEL/.agents/scripts/review_records.py" validate --record-file "$SESSION/round.json"
gh api --paginate --slurp "repos/$PR_REPO/issues/$PR_NUMBER/comments" > "$SESSION/comments.json"
uv run --no-project python "$TOPLEVEL/.agents/scripts/review_records.py" validate \
  --record-file "$SESSION/round.json" --comments-file "$SESSION/comments.json" --trusted-login "$TRUSTED_LOGIN"
```

同じサイクルのコメントを更新するときは、2 つ目の `validate` に `--exclude-comment <そのコメントの ID>` を付ける。終了コード 65 は内容の問題で、標準エラー出力の 1 行ずつの問題を直してから検査し直す。

## 6. 投稿する

SKILL.md の「作業終了前の PR 投稿」の雛形で、`--records-file "$ROUND_JSON"` を付けて helper を実行する（`ROUND_JSON="$SESSION/round.json"`）。

- helper は、認証済みの login を自分で取り、記録単体の検査、`--model-name` と `planner.model` の一致、PR が open で `pr` と一致すること、PR の head（`fixes_pushed` なら `commit`、それ以外は `reviewed_head`）、前の状態との照合を確かめてから、同じサイクルの自分のコメントを更新するか、無ければ作る。照合の対象は、書き込み権限のある投稿者か認証済み利用者自身のコメントだけである
- 終了コード 64 は拒否である。標準エラー出力の問題が記録の内容なら直して投稿し直す。それ以外（login を取れない、`gh` の失敗、ほかのエージェントが同じサイクルを記録した、番号の大きいサイクルがある、同じサイクルのコメントが 2 件以上）は止まって報告する。記録なしの投稿や `gh` の直接の呼び出しに切り替えない。`gh pr comment --edit-last` を使わない
- 本文が 65,536 文字を超えると拒否される。作業判断の「対応しない」を判断 ID と一行の理由だけにして投稿し直す。それでも超えるなら、投稿できない停止として報告する
- 投稿する時点:
  - 結論 1: push の後。`commit` は push した SHA、`recorded_at` は更新した時刻
  - 結論 2（create-reso-world の PR）: Spec の commit を push する前（[execution.md](execution.md) 3.2 節）。本文はマージの前の採否・検証の状況で、マージ済み・Issue の更新済みと先に書かない
  - 結論 2（usaturn/resoloop の PR）: `finalize.py` が投稿する
  - 結論 3: PR が open で、記録を読めた場合に、判明した内容と行っていないことを書いて投稿する。マージしてよい範囲の外のリポジトリ（上流の `orange3134/resoloop` など）では、commit・push まで行ったターンだけ必須で、それ以外は任意（SKILL.md「マージしてよい範囲」）
- 投稿できなかった記録は、次のサイクルの前に同じ内容で投稿し直す。次のサイクルが先に記録された後は前のサイクルを更新できないので、報告し、次のサイクルの planner が前のサイクルの `fix` を修正後の HEAD で確かめる

## 7. 工程の記録（`planning.json`）の最後の更新

確認済みの一覧があるサイクルでは、サイクルの最後（投稿の後）に `REVIEW_DIR/verified/<reviewed_head の先頭 12 文字>.planning.json`（review-findings v2）を更新する（無ければ作る）。`outcome`・`comment_id`、判断・実装・自己レビュー・修正の確認・待ちの実際の時間（`activities`）、fix-check のファイルと push を止めた修正の数（`fix_checks`）を書く。`run_roles.py` が足した `pre_push_review` の行は消さない（自己レビューの回数の根拠）。枠の件数と実際の作業時間は別のものとして書き、行っていない工程を 0 秒にしない。`review_findings.py validate` を通す。

## 8. 後片付け

`SESSION` は、最終の投稿・最終化が終わり、Spec にレビュアーの構成・planner のモデル・コメントの URL・役割と回数と時間を写した後に、`rm -rf -- "${SESSION:?}"` で消す。失敗・復旧に使う記録は残し、完全パスを報告する。自己レビューの予約を持つ `planning.json` は回数の根拠なので、別のファイルを作って上限をやり直さない。
