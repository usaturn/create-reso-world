# 評価の手順

Issue の目標値を評価し、評価コメントの案を作るときの手順。評価コメントの形は `.agents/issue-format.md` の 7 章が定める。ここには写さない。投稿の流れ・承認・非対話の実行・後片付けは `SKILL.md` に従う。

評価は利用者が評価時期に呼び出したときだけ行う。自動で実行したり、通知したりしない。

## 1. 入力と対象を確かめる

1. 対象を `--repo owner/repo` で明示し、共通 resolver と AGENTS.md「リポジトリ境界」に従い常設親・採用済み台帳・remote を確認する。不在・不一致・未登録では止まり、別対象に切り替えない
2. 対象が Issue であり、PR ではないことを確かめる。`gh api --hostname github.com repos/<owner>/<repo>/issues/<N>` の応答に `pull_request` があれば PR であり、評価の対象外である。PR の番号でも `gh issue view` は成功することがあるので、`gh issue view` だけで判断しない
3. 評価する Issue の母集団を先に決める。対象の選び方（番号の一覧、ラベル、期間など）とデータ源を決め、母集団と根拠を `scope` に残す。JSONL の Issue 行には `created_at` が無いので、期間で選ぶときは独立した API 情報や事前に確認した番号一覧を使う。対象を特定できなければ情報不足として扱い、読めた `metadata` だけを対象全体としない。選択済みの Issue は、`metadata` の `status` や `value`（`filed_on` を含む）で母集団から外さない。この選択は、記録の `extraction.status` で有効な run・評価だけを数える操作とは別である
4. 本文と、全ページのコメントを読む（open・closed のどちらでもよい）。既存の評価コメントをすべて確認し、どの目標をいつ評価したか、同じ目標を二重に記録しないかを見る。評価コメントを編集したり、過去の評価を現在の値として流用したりしない
5. `metadata` の状態を抽出結果で確かめる。`value` を読むのは `status` が `ok` のときだけである。`broken` のときは理由と行を、`unknown_version` のときは版と行を報告する。壊れた JSON や知らない版から、目標値を復元しない
6. `status` が `ok` のときは、`metadata.value.targets` を読み、本文の「目標値と評価方法」と照合する。目標・評価方法（データ源・回数・条件）・評価時期のどれかが食い違う、または片方にしか無いときは、どちらを根拠にするかを利用者に尋ねる
7. `metadata` が `missing` の旧書式の本文でも、目標・評価方法・評価時期が本文から具体的に読み取れるなら、その記述を根拠にしてよい。`broken`・`unknown_version` でも、本文に同じ項目が具体的に書かれていればその記述を根拠にしてよいが、壊れたブロックから値を推測しない。読み取れないときは推測せず、不足している項目を尋ねる
8. 目標が無い Issue では、評価の数値を作らない。値が決まるまで `evaluation` のブロックを作らず、人向けのコメントと不足の問いを用意する（案の保存まで進めてよい）

親 Issue と子 Issue の両方に同じ目標があるときは、子の件数だけ目標を重ねない。それぞれの Issue の `targets` をその Issue の目標として扱い、親の目標を子の評価に写さない。run を再開した Issue では、停止した run と再開後の run の実行記録が複数並ぶことがある。時間・規模を run の数や子の数だけ重複して数えず、どの記録をどの範囲として扱ったかを `scope` に書く。

## 2. 目標ごとに実測する

各目標の `method` に書かれたデータ源・測定回数・測定条件に従う。人が結果と根拠を確かめ、必要ならログ・実行記録・コメントを読む。機械的な合計・割合・可視化のコードは追加しない。抽出 helper は、判断に使う観測を集めるために使う。

`method` が書式検査を指定するときは、`check.complete`・`check.problems`・`check.undetermined` を観測根拠にし、`method` が求める基準に従う。`complete` の仕様は `.agents/issue-format.md` の 9 章の `check` に従い、この手順で新しい既定の適合基準を作ったり、`--allow-undetermined` を適用したりしない。未確定を許すかで結果が変わり、`method` から判断できないときは、`true` / `false` を推測せず、目標・評価方法の不足として利用者に尋ねる。

`check` は本文・ラベル・タイトルを対象にする検査結果であり、抽出 helper が目標の達成を判定するわけではない。時間など別の測定を `method` が求める場合は、その測定を使い、`check` だけから達成を決めない。

`check` の対象として先に選択した Issue の `metadata` が `missing`・`broken`・`unknown_version` でも、その Issue を母集団から外さない。不適合として残し、観測された理由を `actual` または `notes` に記録する。`metadata` の状態や値で、選択済みの Issue を絞り込まない。

実行記録を数えるときは `run_records[].extraction.status` が `ok` の要素だけを有効な run とし、評価記録を数えるときは `evaluations[].extraction.status` が `ok` の要素だけを有効な評価とする。`broken`・`unknown_version` は診断用で、有効な件数に含めない。配列の長さをそのまま有効件数にしない。`unreadable_comments` は診断用で、有効な run・評価に数えない。`missing` のコメントブロックは `run_records`・`evaluations` の配列に入らない。

結果は `Evaluation` の `results` に、目標ごとに次の 5 つを記入する。

| 項目 | 内容 |
|---|---|
| `metric` | 指標。`targets` の `metric` と対応させる |
| `target` | 目標値。`targets` の `target` をそのまま使う |
| `actual` | 実測値と根拠。数値だけでなく、データ源・件数・条件も分かるように書く |
| `achieved` | 目標を達成したか。判定できるときだけ `true` / `false` |
| `gap` | 目標と実測のずれ。達成なら「なし」 |

未計測、データ不足、抽出の失敗などで判定できないときは、`actual` にその事実を書き、`achieved` を `null` にし、`gap` に判定できない理由を書く。0・未達・成功に置き換えない。測れていない値を 0 として扱わない。

`scope` には、指標が数える単位（Issue、run、評価）・範囲・件数・選択／除外条件・データ源を書く。対象 Issue の母集団は、番号一覧や独立した API 情報など、`metadata` の状態や値によらない根拠で示す。Issue を選ぶ操作と、`run_records`・`evaluations` から `extraction.status=ok` の記録だけを数える操作を混ぜず、Issue 1 件に複数の run がある場合や再開した run でも単位をそろえる。`notes` には、計測の限界、除外したデータ、再開した run の扱いなどを残す。全目標について `metric`・`target`・`actual`・`achieved`・`gap` を埋める。

## 3. 抽出 helper で観測を読む

登録済みリポジトリの Issue とコメントは、読み取り専用の抽出 CLI で JSONL として読める。ワークスペースの root で実行する。clone や git は使わず、`gh api` の GET だけを使う。

```bash
uv run --locked python .agents/skills/issue-authoring/scripts/extract_issues.py --repo <owner>/<repo>
```

- 引数は `--repo OWNER/NAME` だけである。共通 resolver で対象を確認し、`gh` を呼ぶ前に不在・不一致・未登録を拒否する。未登録なら標準エラー出力に `extract_issues: <理由>` を書いて終了コード 2 で止まる
- open・closed の Issue を全ページ取得し、Issue 番号の昇順で 1 Issue 1 行の JSON を出す。PR は除く。コメントも全ページ取得する。記録として読むのは `author_association` が `OWNER`・`MEMBER`・`COLLABORATOR` のコメントだけである
- 各 Issue の行は `repository`・`number`・`url`・`title`・`state`・`state_reason`・`labels`・`metadata`・`check`・`run_records`・`evaluations`・`unreadable_comments` を持つ
- `state_reason` は API の値をそのまま出す。`null`、`completed`・`not_planned`・`duplicate`・`reopened` などを、この手順で別の値に正規化しない
- `metadata`・`run_records[].extraction`・`evaluations[].extraction` は、`status`・`version`・`reason`・`line`・`value` を持つ。`status` は `ok`・`missing`・`broken`・`unknown_version` のどれかである。`value` は `ok` のときだけ入る。`metadata` の `missing` は本文にブロックが無いことを示し、コメントの `missing` はそのコメントにブロックが無いことを示す
- `run_records`・`evaluations`・`unreadable_comments` の要素は、コメントの `id`・`url`・`created_at` と `extraction` を持つ。`run_records`・`evaluations` には、その種類のブロックがあるコメントだけを入れる（`missing` のコメントは入らない）。ブロックの対象 Issue が行の Issue と違うときは `broken` になる。コメントのブロックの種類を判別できない形で壊れている場合（実行記録・評価のどちらとしても読めず、同じ行で壊れている場合）は `unreadable_comments` に入る
- `run_records` と `evaluations` のうち、有効な実行記録は `run_records[].extraction.status` が `ok` の要素、有効な評価記録は `evaluations[].extraction.status` が `ok` の要素だけである。`broken`・`unknown_version` は診断用で有効件数に含めない。配列の長さをそのまま有効件数にしない。`unreadable_comments` は診断用で、有効な run・評価に数えない
- `check` は本文・ラベル・タイトルを対象にする書式の検査結果で、`complete`・`problems`（`code`・`where`・`message`）・`undetermined` を持つ。`metadata` の状態の確認と、`method` が書式検査を指定するときの観測根拠に使う。抽出 helper 自体が目標の達成を判定するわけではない
- 終了コードは、壊れたブロック・未知の版・対象の違うブロックが無ければ 0、1 件以上あれば 1 である。終了コード 1 は、診断付きの JSONL が得られたことを示すだけで、全データを捨てる理由にはしない。`check` の `complete=false`・`problems`・`undetermined` と終了コード 1 を同一視しない。終了コード 1 でも全 Issue の JSONL は標準出力に出て、問題は `extract_issues: issue #<N> <種類>: <理由>` の形で標準エラー出力に出す
- 取得・入力の失敗（未登録、`gh` の失敗、JSON でない応答など）は終了コード 2 で、標準出力には何も書かない。argparse の usage エラーも終了コード 2 である。評価では、観測が得られないときは取得失敗・未計測・不足として扱い、`achieved` を `null` にして 0 や成功を作らない

この CLI は観測を集めるだけで、目標の合計や達成率は出さない。集計はこの手順で人が行い、その条件を `scope` に書く。CLI の出力に現れた Issue だけを対象全体にせず、母集団は 1 の手順で先に決める。

## 4. 評価コメントを組み立てる

評価の入力は、次の 2 つに分ける。

- 評価の JSON（`Evaluation` の値）。`issue`・`evaluated_at`・`runtime`・`model`・`scope`・`results`・`notes` を持つ
- 人向けの本文（見出しと、結果の要約）

`runtime` と `model` は、この評価を実行しているランタイムで観測した識別子を書く。記入例の値や、ほかの実行で見た値を実績として使わない。評価の JSON は厳密な JSON で書き、`model_validate_json` で読む。

記入例（架空の値。`<...>` は確認した値に置き換える）:

```json
{
  "issue": {
    "repository": "<owner>/<repo>",
    "number": 9001
  },
  "evaluated_at": "2026-11-30T00:00:00Z",
  "runtime": "<runtime を観測して記入>",
  "model": "<model を観測して記入>",
  "scope": "マージ後 2 週間の作業ログ 5 件。データ源: 対象の作業ログ",
  "results": [
    {
      "metric": "手作業の確認にかかる時間",
      "target": "1 回あたり 3 分以内",
      "actual": "未計測（作業ログが揃っていない）",
      "achieved": null,
      "gap": "判定できない（作業ログが揃っていない）"
    }
  ],
  "notes": "作業ログの期間が短く、通常の条件と比べられない"
}
```

人向けの本文の例:

```markdown
## 評価の結果

目標の 1 指標は、作業ログが揃っていないため今回は判定できなかった。揃った時点で再評価する。
```

本文に HTML コメントを手で置かない。`<!--` で始まる行は画面に出ず、評価のブロックは `compose_comment` が付ける。

次のスクリプトは、評価の JSON と人向けの本文を読み、`compose_comment` で `evaluation` のブロックを付けた本文を一時ファイルに保存し、保存したファイルを `extract_block` で読み戻す最小例である。`issue_format.py` は `importlib.util` で読み、`sys.modules` に登録してから実行する。`--root` にはワークスペースの root を渡す。

```python
#!/usr/bin/env python3
"""評価コメントの本文を組み立て、保存したファイルを読み戻して確かめる。"""

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_issue_format(root: Path) -> Any:
    path = root / ".agents/scripts/issue_format.py"
    spec = importlib.util.spec_from_file_location("issue_format", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"issue_format.py を読み込めません: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["issue_format"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--evaluation", required=True, type=Path)
    parser.add_argument("--body", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    fmt = load_issue_format(args.root)
    rules = fmt.load_rules(args.repo)
    record = fmt.Evaluation.model_validate_json(args.evaluation.read_bytes())

    destination = fmt.IssueRef(repository=rules.repository, number=args.issue)
    same_issue = (
        record.issue.repository.casefold() == destination.repository.casefold()
        and record.issue.number == destination.number
    )
    if not same_issue:
        raise SystemExit(
            "評価 JSON の issue が確認済みの投稿先と一致しません: "
            f"{record.issue.repository}#{record.issue.number} != "
            f"{destination.repository}#{destination.number}"
        )

    text = args.body.read_text(encoding="utf-8")
    composed = fmt.compose_comment(text, record)
    args.output.write_bytes(composed.encode("utf-8"))

    saved = args.output.read_bytes().decode("utf-8")
    extracted = fmt.extract_block(saved, "evaluation")
    if extracted.status != "ok" or extracted.value != record:
        raise SystemExit(f"保存した本文を読み戻せません: {extracted.status}: {extracted.reason}")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

入力の `--evaluation` と `--body`、出力の `--output` は、投稿案の `--out-dir` の外に置く。`--output` の親ディレクトリは先に作っておく。実行例:

```bash
uv run --locked python "$SRC/compose_evaluation.py" \
  --root "$PWD" \
  --repo "$REPO" \
  --issue "$ISSUE" \
  --evaluation "$SRC/evaluation.json" \
  --body "$SRC/comment.md" \
  --output "$SRC/comment-composed.md"
```

`$SRC` は `SKILL.md` の投稿の流れの手順 1 で作る入力用のディレクトリである。`--repo` は登録済みの `OWNER/NAME`、`--issue` は確認済みの投稿先の番号にする。評価 JSON の `issue` がこれと違えば、スクリプトは上書きせずに止まる。保存した本文に `evaluation` のブロックが 1 つだけあり、読み戻した値が入力と同じでなければ、次の `draft` に進まない。

## 5. 案を保存し、承認を待つ

`draft` は、`SKILL.md` の投稿の流れの手順 2 で作った新しい空のディレクトリを `--out-dir` にして実行する。`--body-file` には 4 で保存した本文を渡し、入力ファイルを `--out-dir` に置かない。

```bash
uv run --locked python .agents/skills/issue-authoring/scripts/publish_issue.py draft comment \
  --repo "$REPO" \
  --issue "$ISSUE" \
  --body-file "$SRC/comment-composed.md" \
  --out-dir "$DRAFT"
```

`draft` は Issue を読むだけで、投稿しない。PR の番号なら `not_an_issue` で止まる。返った `draft`・`sha256`・`preview` を確認し、`preview.md` の全文を `draft` のパスと `sha256` とともに利用者に見せて、ターンを終える。

- 最初の「評価して」「今すぐ投稿して」は、案の承認ではない。承認の返答を受け取るまで `publish` を実行しない
- 案の内容を変えたら、新しい空のディレクトリに `draft` を作り直し、新しい `sha256` で改めて承認を得る
- 承認の返答を受け取れない非対話の実行では、`draft` までで終え、`draft` のパス・`sha256`・尋ねたかった問いを報告する
- `publish` は、`publish_issue.py publish --draft <直近に見せた案のディレクトリ> --sha256 <直近に見せた値>` だけを使う。直接の `gh api` の POST や `gh issue comment` で投稿しない
- helper の出力ごとの次の操作と後片付けは、`SKILL.md` の「helper の出力ごとの次の操作」「後片付け」に従う

## 対象外

この手順では、評価時点の Issue・コメントのスナップショットを別に保存する仕組み、定期的な自動実行や通知、評価結果の集計・可視化は作らない。実在の Issue への試し投稿は行わない。1 つの案の投稿は、利用者がその案を承認した後の 1 回だけである。
