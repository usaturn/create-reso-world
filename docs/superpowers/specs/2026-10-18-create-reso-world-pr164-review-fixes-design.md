# PR #164 レビュー指摘の選別と修正（Issue #152 レビューの共通 helper）

## 管理・実行許可

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/164（`feat/issue-152-review-helpers`、base `main`、関連 Issue #152）
- レビュー対象の HEAD: `60849067e1e7a70d741398203acdff3a9108f791`（4 本のレビューとも同じ。選別の時点の PR の head も同じ）
- 状態: completed
- 実行許可: 2026-10-18（UTC）、利用者が `/review-fix-planning #164` を実行した。計画で止める指定が無いので、review-fix-planning の「完遂」として、この PR のレビュー修正の実装・検証・commit・push・状況コメントの投稿（結論 1）、または修正不要のときのマージと関連 Issue の更新（結論 2）まで進めることが許可されている。下の判断は、確認を取らずに決めたエージェントの判断であり、利用者の承認ではない
- 関連 Spec: `docs/superpowers/specs/2026-10-18-create-reso-world-issue152-review-helpers-design.md`（PR の設計。とくに D-3「`review_findings.py` は形式と挙動を移植元のまま」）
- 作業場所: `/workspaces/reso-world/.worktrees/issue-152-review-helpers`（PR の head を checkout した既存の worktree。未コミットの変更が無く、HEAD が PR の head と一致していたので使った）

## 入力

レビューディレクトリ `reviews/usaturn/create-reso-world/#164-feat-issue-152-review-helpers/`

| ファイル | 対象 HEAD | 結論 | 指摘 |
| --- | --- | --- | --- |
| `claude-opus-5-5.md` | `60849067e1e7` | Approve | なし |
| `SWE-2-Max.md` | `60849067e1e7` | Approve | なし（Unverified candidates 2 件） |
| `deepseek-deepseek-v4.1-flash.md` | `60849067e1e7` | Approve | Info 1 |
| `openai-codex-gpt-6.1-sol.md` | `60849067e1e7` | Approve | Medium 3・Low 1（Review coverage に既出の事項 1 件） |

## 指摘の分類

解消済み 0 / 対応する 1 / 対応しない 7。確認中に自分で見つけた致命的な欠陥は無い。

| ID | 内容 | 区分 | 根拠 |
| --- | --- | --- | --- |
| Codex M-2 | 見出しの無い Unverified candidates を、`from-markdown` が空の一覧として成功させる | **対応する**（(a) 再現した誤動作） | 下の「対応する項目」 |
| Codex M-1 | 番号・URL の経路は、新しい配置のディレクトリの `findings/` が別の PR を指していても受理する | 対応しない | 番号・URL の経路は、照会した PR から保存先と Git 操作の対象を決めるので（`review_target.py:653-675`）、対象の取り違えは起きない。食い違う `findings/` が置かれるのは、別の PR の候補一覧を手で写したときだけ（pr-review は照会した PR の保存先に、その PR の候補一覧を書く）。移植元も同じ挙動 |
| Codex M-3 | Markdown の指摘 ID が重複すると、`check-pair` が片方を照合から落とす | 対応しない | 発生には、形式の違反（ID の重複。[review-records](../../../.agents/review-records.md) 4.3 節は ID の衝突を禁じる）と、JSON 側での片方の欠落という 2 つの誤りが重なる必要がある。JSON 側の重複は `validate` が拒否し、`from-markdown` も重複を拒否する（再現で確認）。移植元と同じ挙動 |
| Codex L-1 | 外側 4 個・内側 3 個のバッククォートのコードフェンスで、内側の見出しを指摘と読む | 対応しない | 再現した。ただし pr-review の様式で必須の Summary の件数表があれば `Summary counts 0 High finding(s) but 1 were read` で止まり、黙って誤った結果にはならない |
| DeepSeek I-1 | `review_target.py:97` のコメント「pr-review の helper もここを使う」が実態と違う | 対応しない | コメントの記述だけで、挙動に影響しない。規則の統一は #153 の担当（PR の Spec D-6） |
| SWE-2-Max U-1 | `check-pair` の位置の照合が部分文字列の一致で、2 行目以降の `位置` を読まない | 対応しない | 照合を弱めるだけで、主要な処理の結果を誤らせない。文書 7 章の「`位置` の行に含まれる」とも一致する。移植元と同じ挙動 |
| SWE-2-Max U-2 | 番号だけの指定で `origin` の URL を insteadOf の展開前の値で読む | 対応しない | 正式な URL で識別するための意図した選択（`review_target.py:215-218` のコメント）。この環境に insteadOf の設定は無い（`git config --get-regexp '^url\.'` が 0 件） |
| Codex（既出） | `--pr` を添えたとき、層からも `findings/` からも決まらないディレクトリを名前だけで受け付ける | 対応しない | 発生には、別リポジトリの `reviews/<owner>/<repo>/#<N>-<同じ head ブランチ名>` を置き、パスと `--pr` を食い違えて明示する必要がある。PR の Spec の「実装・検証結果」で Minor 2 として持ち越し済み |

仕様の論点として 1 行残す: Codex M-1 の、番号・URL の経路でも `findings/` との食い違いを確かめるかどうかは、review-verify（#154）・review-fix-planning（#155）を接続するときに決める。

## 対応する項目: Codex M-2

### 現行 HEAD での確認

- `review_findings.py:1592-1605`（修正前）は、Unverified candidates の節の ID を `### <ID>:` の見出しからだけ読み、見出しの無い行を読み飛ばす。`problems()` は見出しの読み取りの失敗と Summary の件数しか見ない
- このレビューディレクトリの `SWE-2-Max.md`（Unverified candidates に箇条書きで 2 件）に `from-markdown` を実行すると、`unverified_candidates: []`・終了コード 0 になった
- この repo の今の pr-review（`.agents/skills/pr-review/SKILL.md:388-390`）は、Unverified candidates の書き方を「位置・具体的な疑い・…を記載する。なければ「なし」と書く」とだけ定め、`### U-<n>:` の見出しを求めない。移植元の pr-review は見出しを求めている。そのため移植先では、今あるレビューファイルが全て `from-markdown` の言う旧形式に当たる
- 手元の実レビュー 274 本（`reviews/`・`external/resoloop/reviews/`）のうち 46 本が、見出しの無い候補を持つのに空の一覧として成功していた

### 致命的である理由

`.agents/review-findings.md` の 7 章・8 章は、候補一覧の無いレビュアーのレビューファイルを `from-markdown` で読むと定める。この手順のとおりに今の pr-review のレビューファイルを読むと、未確認の候補が黙って 0 件になり、review-verify（#154）が確かめる対象から消える（手順・ツールのとおりに使うと誤った結果になる）。`candidates_from_markdown` 自身の docstring も「読めなかった指摘は黙って落とさずに `FindingsError` を送出する」と定めていて、それに反する。

### 修正方針

推奨案: Unverified candidates の節の最初の空でない行が `### ` の見出しか「なし」（前に `- `・`* ` があってもよい）で始まらなければ、`ParsedReview.problems()` に挙げる。`from-markdown` は `FindingsError`（終了コード 65）で止まり、呼び出し側はレビューファイルを直接読む（docstring と 8 章の既存の扱い）。`check-pair` も同じ問題を markdown の問題として報告する。

- 「なし」で始まれば、後に説明や棄却した候補の箇条書きが続いても空の宣言として扱う。実ファイルにこの書き方が複数ある（「なし。検討して棄却した候補: …」）ため
- 最初の行だけで決めるので、見出しの前に導入文を書いた節は止まる（実ファイルには無い）。黙って落とすより、止めて直接読ませるほうを選んだ
- 文書 `.agents/review-findings.md` の 7 章・8 章に、止まる条件と、止まったら直接読むことを 1 行ずつ足した

比べた別案:

- 箇条書きの候補を読み取って `U-<n>` を振る: 箇条書きの区切り（1 候補が何行か）に決まった形が無く、読み違えると候補の数や中身を誤る。形式を移植元から大きく変えることにもなる
- 修正せず、#154 で review-verify が `from-markdown` を使わないようにする: この PR の文書とツールの組み合わせが誤った結果を返す状態でマージすることになる

PR の Spec D-3（`review_findings.py` の挙動は移植元のまま）からの例外は、この 1 点だけである。理由は、移植先の pr-review の様式が移植元と違い、移植元では古いファイルにしか無い書き方が、移植先では今の書き方であるため。

### 守る条件と影響経路

守る条件: 「`## Unverified candidates` の節の最初の空でない行が `### <ID>:` の見出しでも「なし」でもなければ、`parse_review_markdown` は `problems()` に挙げる（見出しの無い候補の節を、空の一覧として黙って通さない）」

この条件は節の最初の行で決める。次は条件の外で、`problems()` が空のまま候補が落ちうる（自己レビューで確認。手元の実ファイル 274 本には 0 件）。

- 見出しの後、または「なし」の後に続く見出しの無い候補。見出しの本文や「なし」の説明（棄却した候補の箇条書き）と区別できない
- 見出しの書き方が揺れて節として認識されないとき（`## Unverified Candidates`、`## Unverified candidates（1 件）` など）。PR より前からの挙動

| 経路 | 判定 | 確かめる方法 |
| --- | --- | --- |
| `candidates_from_markdown`（`from-markdown`） | 修正する | `test_from_markdown_refuses_findings_it_cannot_read` の 2 件（箇条書き、導入文＋箇条書き）。`SWE-2-Max.md` の CLI が終了コード 65・標準出力 0 バイト |
| `check_pair`（`check-pair`） | 修正する | `test_check_pair_refuses_unverified_candidates_it_cannot_read`（問題がちょうど 1 件で今回の理由）。CLI が終了コード 65 |
| 「なし」で始まる節（後に説明・棄却した候補が続くものを含む）、節が無い・空のファイル | 既に満たす（空のまま成功） | `test_from_markdown_reads_an_unverified_section_that_says_none` の 4 件、`test_parse_review_markdown_tolerates_empty_and_missing_sections`。実ファイル 225 本の結果が修正前と同じ |
| `### U-<n>:` の見出しで始まる節（review-records 4.3 節の形） | 既に満たす（従来どおり見出しから読む） | `test_parse_review_markdown_reads_active_findings_and_unverified_candidates`・`test_check_pair_*` ほか既存。実ファイル 3 本の結果が修正前と同じ |
| Critical〜Info の節の、見出しの無い指摘 | 既に満たす（Summary の件数表との照合で止まる。pr-review の様式は件数表を必須にしている） | 既存の `test_from_markdown_refuses_findings_it_cannot_read`（Summary の件） |
| Decided・Resolved・Pending の節 | 対象外（意図して数えない節。`_EXCLUDED_SECTIONS`） | — |
| `review_records.py`（Markdown を読まない）、文書の記入例を `from-markdown` に通すテスト | 既に満たす（Unverified の節を持たない） | `test_document_finding_example_is_read_by_from_markdown` が通る |

### 失敗時の検証

- 状態全体: `SWE-2-Max.md` の写しと候補一覧を置いた一時ディレクトリで、`from-markdown`・`check-pair` の前後に、ファイルの有無・サイズ・mode・種類・sha256 を比べて一致した。どちらも標準出力は 0 バイトで、終了コード 65。両コマンドは読むだけで、書き込むのは検査に通った後の標準出力だけである（`main()` は `candidates_from_markdown`・`validate_document` の後に書く）
- 負例の異常は 1 つずつ: 3 件とも Summary の件数・指摘の見出し・JSON の形は正しく、見出しの無い候補だけを入れた。`check-pair` の負例は、問題がちょうど 1 件で今回の理由であることまで確かめる
- ガードを外した対照: 修正後の内容を写した隔離 worktree で、`unparsed_unverified` に追加する行を外すと、負例 3 件が全て失敗し、正例 4 件と既存の 4 件は通った（検出力 3/3）。対照の worktree は検証後に消した

## 実行した検証

worktree のルートで実行した（全て終了コード 0）。

- `uv run pytest .agents/scripts tests/scripts/test_superpowers_context.py`: 548 passed、109 subtests passed（修正前の 541 件＋追加 7 件）
- `bash .devcontainer/run-tests.bash`: PASS 32
- `bash scripts/check-layout.sh`: PASS
- ruff の指摘は修正前と同じ 4 件（移植元のまま写した箇所）で、増えていない
- 実ファイル 274 本での修正前後の比較: 225 本は空のまま成功、3 本は見出し形式で結果が同じ、46 本が新たに止まる。46 本の先頭行はすべて実際の候補（前回からの引き継ぎを含む）で、誤検出は無かった

PR の Spec（`2026-10-18-create-reso-world-issue152-review-helpers-design.md`）の D-3 と PR 本文に、今回の例外を書き足した。

#153 への申し送り: 移植元の pr-review の保存の手順は `check-pair` を通す。今回の修正で、Unverified candidates の節を見出しの前の導入文や「（なし）」「該当なし」「None」などで始めたレビューファイルは、`check-pair` で止まる。#153 で pr-review の様式を `### U-<n>:` の見出しにするときは、節を見出しか「なし」で始めるよう定める。

## 結論

結論 1（修正して push）。

## 自己レビュー

修正後に 1 回だけ、3 つの観点を別々のサブエージェントに同時に任せた。3 観点とも致命的な指摘は 0 件。自己レビューの後の修正は文書（この Spec の守る条件の書き方、PR の Spec の D-3、PR 本文）だけで、再レビューはしていない。

- 反証: 実ファイル 274 本の修正前後の比較、CLI、境界の入力（字下げ、CRLF、全角の空白、フェンスで始まる節、節の重複、ファイル末尾の節など）を確かめた
- PR 全体: 修正後の PR 全体を読み、移植元との一致（docstring を除いた構文木）、3.12 の文法、実環境の `resolve`・`fold` を確かめた
- 検証の検出力: 変異 15 種を試し、中心部分（追加の取りやめ、`problems()` から落とす、`check_pair` が足さない、`### ` の例外、「なし」の接頭辞・前方一致）を壊すと新しいテストが失敗することを確かめた。テストの採用基準に反するテストは無い

軽微な指摘の判定（すべて致命的でない）:

| 指摘 | 判定 | 理由 |
| --- | --- | --- |
| 守る条件の書き方が実装より強い（検出力 5） | 直した | 上の守る条件を、節の最初の行に限る書き方にした |
| PR の Spec の D-3・PR 本文が「挙動は移植元のまま」のまま（PR 全体 1） | 直した | 保証の記述を実装に合わせた。Plan の Global Constraints は実装時の指示の記録なので変えない |
| 見出しの前に導入文がある節や、「（なし）」「該当なし」「None」などで始まる節も止まる（反証 1・4、PR 全体 2） | 対応しない | 止まる側に倒れ、呼び出し側はレビューファイルを直接読む。実ファイルには 0 件。#153 への申し送りに書いた |
| 見出しの後・「なし」の後に続く見出しの無い候補、「なしで…」で始まる候補を通す（反証 2・3、PR 全体 3） | 対応しない | 実ファイルには 0 件。見出しの本文や「なし」の説明と区別できないので、上の守る条件の外として書いた |
| 見出しの表記の揺れ・閉じていないフェンスの後の節を認識しない（反証 5） | 対応しない | PR より前からの挙動で、実ファイル 274 本の見出しは全て `## Unverified candidates` |
| 文書 7 章は `### U-<n>:` と書くが、コードは任意の ID の見出しを候補として読む（反証 6、PR 全体 4） | 対応しない | 移植元からの挙動で、見出しから読む候補は落ちない |
| 「なし」を行頭で判定していること、節に入るときの初期化、CLI の終了コード 65 をテストで固定していない（検出力 1〜4） | 対応しない | コードは正しく動いている（手で確認）。CLI の終了コードは全ての `FindingsError` に共通の処理 |
| `review-findings.md` 2 章の保存先が、今の pr-review（`external/resoloop/reviews/`）と違う（PR 全体 5） | 対応しない | 文書は #153 の後の配置を書いていて、`review_target.py` の挙動とは一致する。切り替えは #153 の担当 |
| `--code-root` に相対パスを渡すと終了コード 2 でなく 7（PR 全体 6） | 対応しない | PR の Spec D-4 のとおり |

## 作業時間

着手 11:26Z。所要時間と内訳は、状況コメントと完了報告に書く（記録だけのコミットを PR に足さないため）。
