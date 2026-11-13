# 起票の手順

新しい Issue を起票するときの手順。節・ラベル・機械可読ブロックの形は `.agents/issue-format.md` が定める。ここには写さない。投稿の流れ・承認・非対話の実行・後片付けは `SKILL.md` に従う。

## 1. 起票先を決める

対象を `--repo owner/repo` で明示し、AGENTS.md「リポジトリ境界」と共通 resolver で常設親・採用済み台帳・remote を確認する。不在・不一致・未登録なら止まり、別対象へ切り替えない。起票先が決まらず、答えで起票先が変わるときは尋ねる。

## 2. 同じ目的の Issue を探す

open・closed の両方を、全ページで探す（PR は除く）。

- タイトルの一覧:

  ```bash
  gh api --paginate "repos/<owner>/<repo>/issues?state=all&per_page=100" --jq '.[] | select(.pull_request == null) | [.number, .state, (.state_reason // ""), .title] | @tsv'
  ```

- 本文の語の検索（`is:issue` で PR を除き、state を指定しないので open・closed の両方。全ページを取る）:

  ```bash
  gh api --paginate -X GET search/issues -f q='<語> repo:<owner>/<repo> is:issue' -f per_page=100 --jq '.items[] | [.number, .state, (.state_reason // ""), .title] | @tsv'
  ```

  検索 API は 1 つの検索で 1,000 件までしか返さない。一致の件数は次で確かめ、1,000 を超えたら語を絞る。

  ```bash
  gh api -X GET search/issues -f q='<語> repo:<owner>/<repo> is:issue' -f per_page=1 --jq .total_count
  ```

探した範囲（語・件数・日付）と結果を、本文の「関連 Issue・依存関係」の「重複」に書く。同じ目的の open の Issue があれば、新しく作るか既存のものを使うか（答えで作るものが変わる）を尋ねる。closed のものは「過去の類似」に書く。

## 3. 項目を決める

尋ねるかどうかは、項目の名前ではなく、**入手済みの根拠で決められるか**で分ける。根拠は、依頼の文・会話・リポジトリのファイル・定義元・既存の Issue である。

| 項目 | 決める根拠 |
|---|---|
| 種別（`type:`） | 依頼の内容と定義元の説明 |
| 対象領域（`area:`） | 触れるファイルのパスと、共有書式の `area:` の定義 |
| 優先度（`priority:`） | 依頼が述べる影響（止まっているか、回避策があるか、手作業が続くか）と定義元の説明 |
| 規模（`size:`）と見積もり（`estimate`） | 作業の数・触れる範囲・不確実さ。確信度と不確実さの要因を書く |
| 起票の契機（`source:`） | 依頼が生まれた経路。リンクがあれば `discovery.links` |
| 基準値・目標値 | 取れる値。測っていなければ「未計測」と理由 |
| 作るものが分かれる選択（どちらの挙動にするか、何を対象外にするか） | 利用者の決定だけ（根拠からは決まらない） |

- **根拠で決められる項目:** 自分で決め、根拠を案に書く。利用者に尋ねない（利用者は承認のときに直せる）。例: 触れるファイルが `tools/agent_runner/` だけなら `area: agent-runner`
- **根拠が足りず、利用者の答えで事実を補える項目**（例: 依頼から、作業が止まっているのか回避策があるのか分からず、優先度が P0〜P2 のどれにもなりうる）と、**作るものが分かれる選択:** 4 の方法で尋ねる
- **答えがまだ無い値（尋ねてターンを終える、または尋ねられない非対話の実行）、または利用者も決められない値:** 定義元の「未確定の値」の手順（本文の `未確定（理由: …。決め方: …）`、`undetermined`、`triage: needed`）で案を作る。作るものが分かれる選択は「未決事項」に書く

## 4. 尋ね方

3 で尋ねると決めた項目だけを、1 回にまとめて尋ねる。各問いに 2〜4 個の選択肢と推奨、答えで何が変わるか（どの項目が決まるか、作るものがどう変わるか）を書く（ランタイムごとの道具は `SKILL.md`）。尋ねるものが無ければ尋ねずに案を作る。尋ねてターンを終えるときも、非対話の実行でも、先に 3 の未確定・未決事項で案を作って保存する（手順は `SKILL.md` の投稿の流れ）。報告には問いを選択肢つきで書く。

## 5. タイトル

1. 「何をどうするか」を日本語の 1 文にする
2. 接頭辞（`fix:`・`agent-runner:`・`[Jev]` など）を付けない。種別・対象領域はラベルに置く
3. 英語で依頼されたことは opt-out ではない。利用者が「タイトルを英語で」と明示したときだけ英語にし、機械可読ブロックの `title_language` を `"en"` にする

## 6. 本文

定義元の 3 章の節を順に書く。

- 「決定済みの事項」には、利用者が決めたこと（会話で答えたことを含む。日付つき）を書く
- 「エージェントに任せる事項」には、推奨案で決めてよいことを書く
- 「未決事項」には、利用者しか決められず、答えで作るものが変わることだけを書く（無ければ「なし」）
- 利用者の記述をそのまま載せるときは、中の最も長い backtick の並びより長い囲みに入れる（行頭の `<!--` があると、そこから先が GitHub の画面に出ない。`draft` の `warnings` に出る）
- 概要の「次の操作」は、規模が L・XL なら `planning-parallel-issues` での分割、XS〜M なら `issue-to-pr` での着手を書く

## 7. 機械可読ブロック

`IssueMetadata`（定義元の 5 章）の JSON を、`SKILL.md` の投稿の流れの手順 1 の入力用ディレクトリ（`--out-dir` の外）にファイルで書き、`draft create --metadata-file` で渡す。helper が `write_metadata` で本文に入れるので、ブロックを手で書かない。`bases` の `sha` は、clone が無くても次で取れる。

```bash
gh api repos/<owner>/<repo>/commits/<branch> --jq .sha
```

## 8. ラベルと関係

- ラベルは 5 系統（未確定があれば `triage: needed` も）を `--label` で渡す。名前は次の出力の定義から選ぶ。作るラベルは helper が案に出す

  ```bash
  uv run --locked python .agents/scripts/issue_format.py labels --repo <owner>/<repo>
  ```

- 親（Sub Issue）は `--parent`、先行（`blocked_by`）は `--blocked-by` で渡す。値は同じリポジトリの番号 `N` か、登録したリポジトリの `OWNER/NAME#N`
- 関連・過去の類似は本文だけに書く

## 9. 案を見せる

`SKILL.md` の投稿の流れで見せる。`preview.md` の全文に加えて、次を書く。

- エージェントが決めた項目と、その根拠
- 次の操作の推奨（規模が L 以上なら `planning-parallel-issues` での分割、M 以下なら `issue-to-pr`）

## 10. 投稿の後

`published` の URL を報告し、次の操作（`/issue-to-pr <URL>` か `planning-parallel-issues`）を勧める。
