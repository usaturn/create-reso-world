# 既存 Issue の整形手順

既存の Issue を `.agents/issue-format.md` の書式へ組み直すときの手順。節・ラベル・機械可読ブロック・整形前の本文の保存の定義は同文書を読み、ここには写さない。投稿の流れ・承認・非対話・後片付けは `SKILL.md` に従う。ボードと子の管理対象、子の本文の節の置き場所は `planning-parallel-issues/references/issue-board.md` を読む。

整形は、意味の整理をエージェントが行い、分割・合成・最終案の保存検査を `.agents/skills/issue-authoring/scripts/reshape_issue.py` が行う。この helper は GitHub へ接続も投稿もしない。本文・タイトル・ラベルなどの通常投稿には既存の `publish_issue.py` の draft → 承認 → publish を使い、直接の編集や PATCH で迂回しない。同一目的の統合元を閉じるときだけ、下記 7 の条件を満たして重複ラベル追加と duplicate close を行う。

## 1. 対象を読む

対象を `--repo owner/repo` で明示し、AGENTS.md「リポジトリ境界」と共通 resolver により常設親・採用済み台帳・checkout・remote を確認する。不在・不一致・未登録では止まり、別対象へ切り替えない。PR は対象外で、`reshape_issue.py` と `publish_issue.py` の入口が拒否する。

`SKILL.md` の投稿の流れの手順 1 と同じく、入力用のディレクトリを作り、対象の snapshot と現在のラベルをファイルに保存する。

```bash
gh api --hostname github.com repos/<owner>/<repo>/issues/<N> > <入力ディレクトリ>/issue.json
gh api --hostname github.com --paginate repos/<owner>/<repo>/labels > <入力ディレクトリ>/labels.json
```

- `number`・`html_url`・`pull_request` を確認する。snapshot が別のリポジトリ・別の番号のものなら止まる。`prepare` も URL と番号を照合し、`pull_request` を拒否する
- closed・空本文・HTML・CRLF・非 ASCII・コードの囲み・HTML コメントを含む本文も、そのまま snapshot に保存する。改行コードを変換しない。自分でファイルを読み書きするときも、`Path.read_text()` などの改行変換を使わず、UTF-8 のバイト列として読む
- 現在のラベルは snapshot の `labels` を使う。本文の概要表より現在のラベルを優先し、昔の本文の分類へ戻さない。`planning:`・`implementation:` は変えない
- 本文に管理対象があるかどうかにかかわらず、管理対象の外に独立した開始指示が無いか、`issue-board.md` の形に照らして確認する。既知の管理対象が無く、開始指示だけがある本文も通常の 1 スロットとして扱わない。境界が不明なら、推測して整形せず止まる

### 関連 Issue の調査と整理の適格性

snapshot 取得後、タイトルと通常本文から特徴語を選び、登録先を固定して軽く検索する。例えば次のように `is:issue` を付け、state は指定しない。全件収集は必須でない。結果が多ければ語を絞り、有力候補は `gh api --hostname github.com repos/<owner>/<repo>/issues/<候補番号>` で現在の本文・state・番号・URL・`pull_request` を読み、対象自身と PR を除いて目的と受け入れ条件を比べる。

```bash
gh api --hostname github.com -X GET search/issues -f q='<特徴語> repo:<owner>/<repo> is:issue' --jq '.items[] | [.number, .state, .title] | @tsv'
```

検索の終了状態も確認し、成功して候補が無い場合と、失敗して調査できなかった場合を区別する。検索語と候補番号、候補なし、または調査できずを「関連 Issue・依存関係」に短く記録する。失敗時も通常整形は続けられる。closed 候補は過去の類似としてのみ参照し、目的や関係を判断できなければ関連リンクに留める。

統合・分割の参加者はすべて同じ登録 repo の open な通常 Issue に限る。各候補の repo・番号・`pull_request`・state と本文を確認する。対象自身が closed の場合は本文整形のみとし state を変えない。ボード・子マーカー・ledger・既存の管理対象を持つ Issue は整理の参加者から除き、この手順の既存の本文整形で保存する。管理対象の確認は 1 と 2 に従う。対象自身を同一目的の統合元として閉じる案なら本文保持を優先し、その調査記録は残す先の同欄に「元 #N の整形時の調査」と分かるように書く。

### 整理案を決める

prepare に進む前に、調査した目的と受け入れ条件を比較し、適格な候補があれば関連リンクだけで終わらせず、次の形を検討して具体案を作る。根拠が足りない関係は統合せず関連に留める。

- **同一目的:** 例えば #101 と #102 が同じ目的なら、残す番号、閉じる番号、選んだ理由、引き継ぐ要件を示す。残す先の通常本文に元へのリンクと引き継ぐ要件を書く。閉じる元の現在の本文はそのまま保持し、整形も本文更新用 draft の作成もしない。元から先へのリンクは duplicate 記録に残す。archive に要件があるだけでは移動完了としない。
- **部分重複:** A=X+Y、B=X+Z なら、例えば X を A の担当に集め、A の通常本文に X と固有 Y、B の通常本文に固有 Z を残す。B には X の担当先 A へのリンク、A には B へのリンクを書く。両方 open とし、固有要件を削らない。
- **独立した目的の混在:** 移す目的に適切な既存 open Issue があれば優先し、無ければ新規分割を提案する。新規先の通常本文に元へのリンクと移す要件を書き、元の通常本文には残す固有要件と新規先へのリンクを残す。元の承認案では「新規 A の URL」など一意な仮文字列を使い、挿入箇所と対応先を明示する。分割だけを理由に元を閉じない。

本文を更新する既存 Issue ごとに 1〜6 の snapshot、prepare、build、draft update、verify を行う。書式・archive・metadata・管理対象の保存は各節と `.agents/issue-format.md` に従う。新規先は `references/authoring.md` の既存の create 手順で元リンクを含む draft を作る。各 Issue の source ラベルは保持する。まとめて提示・承認する方法と公開順は 7 に従う。

## 2. 本文をスロットへ分ける（prepare）

入力とは別の新しい空ディレクトリを作り、`prepare` を実行する。出力先は空でなければ拒否される。段階ごとに新しいディレクトリを使う。

```bash
uv run --locked \
  python .agents/skills/issue-authoring/scripts/reshape_issue.py prepare \
  --repo <owner>/<repo> --issue <N> \
  --read-json <入力ディレクトリ>/issue.json \
  --out-dir <prepare の空ディレクトリ>
```

終了コード 0 の `status: prepared` で、`original.md`・`segments.json`・`manifest.json`・既存の有効な metadata があれば `metadata.json` ができる。`original.md` は snapshot の本文そのもので、以後変更しない。

`manifest.json` の `managed_count` と管理対象の一覧、`archive`、`metadata` を確認する。`segments.json` は「管理対象の数 + 1」個の文字列で、管理対象の前後と間の編集可能な部分である。管理対象は helper が不透明なバイト列として保持し、スロットには含めない。

次の場合は整形を進めず、標準エラー出力の理由を報告して止まる。

- 終了コードが 0 以外、または `managed_count` と本文の見た目が合わない
- 管理対象の開始・終了の対応が壊れている、未知の `planning-parallel-issues` の行がある
- 管理対象が HTML コメントや閉じていない囲みの中に隠れている、archive や metadata が管理対象と重なる
- 既存 metadata が壊れている、未知の版である、archive が壊れている
- PR・未登録リポジトリ・snapshot の対象違い

helper が拒否する入力は終了コード 2 で止まる。`managed_count` と本文の見た目が合わない場合や、管理対象がコメントの中に見えない場合は、helper が範囲を捨てて進むことがあるので、manifest と `original.md` を照合して自分で止まる。黙って範囲を捨てたり、metadata を消して作り直したりしない。

### 整形後の管理対象の増減

新形式 archive の保存後に管理対象が増減したときの扱い。復元の意味の定義は `.agents/issue-format.md` の「整形前の本文の保存」。

- 追加は許容する。archive の位置マーカーが live の管理対象に順序を保って一意に対応するときだけ復元し、archive に無い live の管理対象（追加）は復元に使わない。追加は live にのみ残り、archive は増えない。追加の位置は archive の後ろ・前（先頭側やほかの管理対象の間）のいずれでもよい（下記の停止の形を除く）
- 削除・順序違い・kind/name の違い・一意でない対応（同じ kind:name が live に複数あり対応が決まらない）は `prepare` が終了コード 2 で止まる
- `pad` 付き archive で、追加を最後の archive 管理対象と包みの間に置くと `prepare` が止まる。追加の kind:name が最後の archive 管理対象と異なれば pad の LF の帰属が合わず、同じ kind:name なら位置マーカーの対応が一意でなくなる一意性判定で止まる
- `pad` フラグ無しの archive で、末尾 LF なしの追加が本文末尾の最後の管理対象になる形は、`build` が保存検査の失敗で止まる（終了コード 2）。包みを次の行に置くために足す LF を再走査で追加の管理対象が吸収し、保存検査の管理対象比較が落ちる。末尾 LF なしの管理対象への追記停止の既存機構であり、追加の許容でも変わらない。`pad` 付きは包みを最後の archive 管理対象の直後に再接続してこの LF を足さないため、この形でも成功する

停止したときは、次の回復手順で live の本文を直し、新しい snapshot で `prepare` をやり直す。管理対象を archive に書き写す・archive を手で直す・範囲を削って通さない、は引き続き禁止。

1. 削除・順序違い・kind/name の違い・一意でない対応: archive の位置マーカーが示す kind:name と順序に live の管理対象を戻す。削除された管理対象のバイト列は Issue の編集履歴・親のボード/ledger などから取得する。子マーカーなら 1 行目に元のマーカー行を戻す。追加が原因の一意でない対応は、追加した管理対象の kind:name（ボードのキーなど）を archive のラベルと重複しないものに変える
2. 最後の archive 管理対象と包みの間への追加: 追加した管理対象を archive の後ろ（機械可読ブロックがあればその直前）へ移す
3. 末尾 LF なしの追加が本文の最後の管理対象になる形: 追加の末尾に LF を足すか、追加を archive より前（最後の管理対象でなくなる位置）へ移す

## 3. スロットを整理する

`segments.json` を複製し、複製した JSON 配列だけを編集する。要素の数・順序は変えない。管理対象を移すためにスロットを結合・分割・並べ替えたり、管理対象のマーカーや開始指示をスロットへ書き写したりしない。

- 通常の Issue はスロットが 1 個である。共有書式の必須の節を、事実を失わないように組み直す
- 親のボードは、共有書式の節 → ボードの管理対象 → 後置きの内容、の順を保つ。ボードの範囲・ledger・開始指示は `issue-board.md` の形のまま触らない。利用者が開始指示の文言を整えてよいと言っても、管理対象の開始指示・ledger・ボード範囲はバイト同一のまま動かさない。文言の変更が必要なら、管理対象を編集する別の依頼として止まる
- 子は先頭のマーカーを 1 行目のままにする。最初のスロットは空文字のままにし、共有書式の節とボード固有の節をその後ろに置く。担当ファイル・共有インターフェース・検証・成果物・状態と反映などの子固有の項目は、archive にだけ残さず、live の本文にも書く。マーカーの `parent:` が親の番号と食い違っても、勝手に直さずに報告する
- 空本文は空のスロットから始める。閉じた Issue も本文を整形してよいが、state は変えない
- HTML と HTML コメント、コードの囲み、非 ASCII は、意味を変えずに扱う。閉じていない囲みやコメントをスロットへ入れない。入れた結果、helper の再走査で管理対象の認識が変わる本文は拒否される
- 元の本文にしかない事実を消さない。判断できない値は、共有書式の「未確定の値」の手順に従い、理由と決め方を本文と `undetermined` に書く。事実を捏造しない

### metadata

`prepare` が `metadata.json` を出した場合は、それを基にする。`filed_on`・`bases`・`targets`・`baselines`・`discovery` などの事実は保持し、現在のラベルに合わせて `undetermined` などの必要な項目だけを直す。元の本文に旧 metadata がある場合も、live のスロットから除いたあとで、archive の復元結果には残る（保存の意味は `.agents/issue-format.md` の「整形前の本文の保存」）。metadata は `draft update` の `--metadata-file` で渡し、既存の `write_metadata` の経路で archive の後ろに付ける。metadata のブロックをスロットや `body.md` に手で書かない。

既存 metadata が無い場合は、共有書式の 5 章と `IssueMetadata` に合う JSON を、snapshot の `created_at`・base branch の SHA・現在のラベルなど、取得済みの事実から作る。必須の事実を作れないときは推測せず止まる。既存 metadata が壊れている・未知の版である場合は、削除や上書きをせず、`prepare` の理由を報告して止まる。

### ラベル

現在のラベルを基準にする。`uv run --locked python .agents/scripts/issue_format.py labels --repo <owner>/<repo> --existing-json <入力ディレクトリ>/labels.json` で不足を確認し、不足するラベルだけを根拠付きで案に加える。古いラベルの扱いは共有書式の 4 章に従う。付ける・外すは `draft update` の `--add-label`・`--remove-label` で渡し、`gh label` で直接変更しない。新しいラベルは承認後に `publish` が作る。

### タイトル

現在のタイトルが共有書式の検査を通るなら変えない。通らない場合は、共有書式の 2 章に合う日本語のタイトル案を作り、`draft update --title` で渡す。タイトルの変更も承認の対象に含める。利用者が旧タイトルの維持を明示していて、そのタイトルが書式に合わない場合は、両立しないので止まる。

## 4. 本文を組み立てる（build）

編集した `segments.json` を `--segments-file` に渡し、新しい空ディレクトリへ `build` する。

```bash
uv run --locked \
  python .agents/skills/issue-authoring/scripts/reshape_issue.py build \
  --repo <owner>/<repo> --issue <N> \
  --read-json <入力ディレクトリ>/issue.json \
  --segments-file <編集した segments.json> \
  --out-dir <build の空ディレクトリ>
```

`status: built` で `body.md` と `diff.patch` ができる。`body.md` は metadata を含まず、archive を 1 つだけ含む。archive の形・3 つの使い分け・復元の意味は `.agents/issue-format.md` の「整形前の本文の保存」に定義する。helper はそこで判定し、ここでは手順だけを書く。

- archive が無い初回は、管理対象が 0 件なら旧形式、1 件以上なら新形式を作る。復元は snapshot の本文全体と一致する。起票の経路や metadata の有無では分けない
- 既存の旧形式は、同文書の移行条件（包みが `wrap_original` の旧形式とバイト単位で一致し、管理対象の数・順序・kind・name・text が live と一致し、1 件以上）を満たすときだけ新形式へ移す。summary は旧包みのものを残す。条件を満たさない包みはバイト単位で再利用し、移行として扱わない
- 既存の新形式は、包みをバイト単位で再利用する

整形後の本文には必ずこの archive を含める。`<details>` や囲みは手で書かず、`build` に作らせる。ツールを使えない出力評価などで本文だけを提案する場合も、archive を省略しない。管理対象のバイト列を archive に写さない。metadata を除いた編集用のスロットから archive を作らない。

`preservation.ok` が `true` であることを確認する。成功判定は、管理対象の数・順序・バイト列、先頭の子マーカー、archive の復元結果が保存すべき本文（初回は snapshot 全体、移行は旧 archive の中身、再利用は既存の保存本文）と一致し、包みが期待する形（初回は再構成した本文と、包みに記録された保存日の summary から一意に作った包み。移行は再構成した本文と旧 summary から一意に作った包み。再利用は既存の包み）と一致し、archive が 1 つだけであることによる。初回の summary の日付は build を実行した日であり、verify を実行した日では判定しない。判定の定義は `.agents/issue-format.md` の「整形前の本文の保存」。`metadata_present` は metadata の有無を示す情報で、`false` でも正常であり、成功判定に含めない。`diff.patch` は archive と metadata を除いた本文の差分で、archive の写しで本文の削除が隠れない。

`build` の `body.md` を手で直さない。内容を変えるときは、新しい snapshot で `prepare` からやり直す。ただし 7 の承認済み新規 URL の限定置換は、保存した同じ snapshot と segments を使い、指定箇所の置換後に新しい出力先で build からやり直す。

`status: too_large`（終了コード 1）は、`original_length`・`managed_length`・`assembled_length`・`limit`・`remaining` を示して止まる。元の本文・管理対象・archive を削って通さない。metadata を含めた最終的な長さは `draft update` と `verify` でも検査される。`preservation_failed` も、管理対象や archive を書き換えずに止まる。

## 5. 更新の案を作る（draft update）

新しい空ディレクトリを作り、`build` の `body.md` と metadata、ラベルの差分、必要ならタイトル案を渡す。`--read-json` は `prepare`・`build` と同じ snapshot を使う。`draft update` は GitHub を読むだけで、まだ書き込まない。

```bash
uv run --locked \
  python .agents/skills/issue-authoring/scripts/publish_issue.py draft update \
  --repo <owner>/<repo> --issue <N> \
  --read-json <入力ディレクトリ>/issue.json \
  --body-file <build のディレクトリ>/body.md \
  --metadata-file <metadata.json> \
  [--title <タイトル案>] [--add-label <名前>]... [--remove-label <名前>]... \
  --out-dir <draft の空ディレクトリ>
```

`status: draft_saved` で `draft.json` と `preview.md` が保存され、出力に `sha256` が示される。`preview.md` の本文は metadata を含む最終案である。

- `check_failed` は、共有書式・ラベル・タイトルの問題を直し、新しい snapshot で `prepare` から作り直す
- `conflict` は、読んだ後に Issue が変わっている。最新の snapshot を取得し直して `prepare` からやり直す
- `secret_detected` は、検出の `target` と行を確認する。archive の範囲内なら archive を消さず、該当位置と理由を報告して止まる。組み直した部分なら、その部分だけを直して `prepare` からやり直す。「秘密情報を除く」ために archive を壊さない
- `too_large`・`unknown_label`・`not_an_issue`・`scan_failed` は、出力の内容を確認して止まる。`gh` で直接回避しない

`draft update` の後に `draft.json` や `body.md` を手で編集しない。これらは検査済みの案と一致していなければならず、`draft.json` を変えると承認対象の SHA も変わる。

## 6. 最終案を検査する（verify）

`draft update` が保存した `draft.json` を、新しい空ディレクトリへ `verify` する。

```bash
uv run --locked \
  python .agents/skills/issue-authoring/scripts/reshape_issue.py verify \
  --repo <owner>/<repo> --issue <N> \
  --read-json <入力ディレクトリ>/issue.json \
  --draft <draft のディレクトリ> \
  --out-dir <verify の空ディレクトリ>
```

`status: verified` で、`body.md`（最終 draft の本文）、`diff.patch`、`preservation.json` ができる。`diff.patch` は archive を除いた最終差分で、metadata の変更も含む。

- `draft_sha256` が `draft update` の `sha256` と一致することを確認する。一致しなければ、その案を承認対象にしない
- `expected_body_sha256` と `snapshot_body_sha256` が一致し、`preservation_report.ok` が `true` であることを確認する。`preservation` は結果を保存した `preservation.json` のパスで、判定には使わない。`expected_mismatch` は snapshot が古いので、最新を取得して `prepare` からやり直す
- `too_large`・`preservation_failed` は、元の本文・管理対象・archive を削らずに止まる
- `metadata` が `true` なら、最終 draft に metadata が入っている

## 7. 整理案・承認・公開

### まとめて見せる・承認する

`verify` が成功してから、`SKILL.md` の投稿の流れに従って各案をまとめて見せる。少なくとも次を全文で示す。

- `preview.md` の全文（最終本文・タイトル・ラベル・警告を含む）
- `verify` の `diff.patch` の全文（archive を除き、metadata を含む最終差分）
- `preservation.json` の保存検査の結果
- `sha256`（`draft update` の `sha256` と `verify` の `draft_sha256` が一致した値）
- `draft.json` のパスと、archive に保存した元本文の存在
- タイトル・ラベルを変える場合は、変更前と変更後

さらに、全対象の repo・番号・操作、タイトル/ラベルの変更、移す項目と担当、実行順、閉じる元と重複先を示す。閉じる元は現在本文の全文・番号・閉じる操作・重複先を示し、本文を変えないと明記する。新規分割の元も仮文字列入りで作成前に prepare → build → draft update → verify を済ませ、preview・diff・保存検査・SHA を他の案と一緒に示す。作成前に分かる書式・長さ・秘密・保存の問題を先に検出する。

承認は、この一連の案を見せた後の対話での利用者の返答だけで、一回の返答でまとめて承認できる。最初の依頼や「急いで」は承認ではない。非対話では案と次の操作を提示して終わり、`publish` もラベル追加も close も実行しない。移動先の更新が不要な場合も close には承認が必要で、helper の非対話拒否だけに依存しない。

### 新規先 URL の限定置換

承認後に新規先を作成したら応答を読み、正しい登録 repo の Issue URL であることを確認する。承認時の draft、編集済み segments、snapshot、対象・操作と関係を比較元として保持する。同じ編集済み segments の指定箇所だけを承認された新規先の実 URL に置き換え、新しい空の出力先で build → draft update → verify を行う。新旧 draft の最終本文・対象 repo/番号・操作・タイトル/ラベル/関係を機械的に比較する。例えば仮文字列が本文中に 1 回だけ現れる場合、次で承認済み draft と新 draft の差がその置換だけか検査できる。引数は保存した `draft.json`、新しい `draft.json`、仮文字列、確認済み URL の順に渡す。

```bash
uv run --locked python - '承認時のdraft.jsonのパス' '新draft.jsonのパス' '仮文字列' '確認済みURL' <<'PY'
import json
import sys
from pathlib import Path

old = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
new = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
placeholder, url = sys.argv[3:5]
if not placeholder or old["body"].count(placeholder) != 1:
    raise SystemExit("仮文字列が指定箇所に一意でない")
old["body"] = old["body"].replace(placeholder, url, 1)
# 作成日時だけは案の保存ごとに変わる。他のフィールドはすべて比較する。
old.pop("created_at")
new.pop("created_at")
if old != new:
    raise SystemExit("URL 置換以外の差がある")
PY
```

複数の URL を入れる場合も、承認された各指定箇所と対応先だけを置換した結果と新 draft を比較する。一致しない場合は新しい preview・diff・SHA と変更分を示し再承認を得る。再 verify と比較に成功した新 draft は新 SHA で publish する。古い SHA を使わず、新 SHA は利用者が直接承認した値ではなく承認された限定置換から生成した値として示す。実 URL への置換で `too_large` になったら元本文を削らず、作成済み URL と未実施の操作を報告して止まる。

### 公開順

承認後にだけ、単票ごとに見せた SHA（限定置換は上記の新 SHA）を渡して公開する。移動元にも移動先の役割がある場合は、要件ごとに保存確認を先に行い、順序が循環して一括で安全に公開できなければ止まって案を分け、再承認を得る。

```bash
uv run --locked \
  python .agents/skills/issue-authoring/scripts/publish_issue.py publish \
  --draft <draft のディレクトリ> --sha256 <verify と一致した sha256>
```

複数 Issue では次の順に進める。各本文の投稿は上記 helper を使い、結果を記録する。

1. 承認された移動先を先に create または update する。更新不要の既存先も対象とする。
2. 移動先の現在本文を `gh api --hostname github.com repos/<owner>/<repo>/issues/<N>` で読み戻し、移す要件が archive だけでなく通常本文に載り、元へのリンクがあると確認する。
3. 部分重複・分割は、確認した移動先へのリンクと固有要件を残して元を更新する。複数の移動でも、各移動先の保存を確認してからその要件を元から外す。同一目的で閉じる元の本文は更新しない。
4. 案に含まれる全本文更新の成功と移動先の読戻しを確認後、残す先と閉じる元の repo・番号・通常 Issue・open 状態、承認済みの対応と対話での承認を再確認する。元の現在本文を読み直し、引き継ぐ要件に取りこぼしがなく、案を変える競合がないことを確認する。そのうえで承認された統合元だけに、次の 2 操作を順に行う。source ラベルは外さない。部分重複・分割だけでは close しない。

   ```bash
   gh issue edit <元> --repo https://github.com/<owner>/<repo> --add-label duplicate
   gh issue close <元> --repo https://github.com/<owner>/<repo> --duplicate-of <先>
   ```

5. 失敗・競合・結果不明なら停止し、済んだ操作・確認済み URL・未実施操作・次に確認するものを報告する。本文更新の失敗・競合・結果不明の後に close しない。作成結果が不明なら再送しない。再開時は現在の状態を読み、実施済みを繰り返さず残りだけ行い、案が変われば必要な再承認を得る。

`published`・`already_published` は URL を記録する。複数 Issue では全操作完了まで資料を保持し、`SKILL.md` の後片付けに従う。`draft_changed`・`conflict`・`labels_changed` は、最新を取得して `prepare` から作り直し、`verify` と承認をやり直す。実 Issue で試す場合も `publish` まで進めず、`prepare` → `build` → `draft update` → `verify` で止める（dry-run）。`non_interactive` は報告して終える。`uncertain` は送り直さず、GitHub の画面で結果を確かめるよう伝えて止まる。上記の承認された duplicate close を除き、state・native の親子関係・依存関係は変えない。

## 停止時の報告

整形を止めたら、次を報告する。入力と途中成果物は消さず、完全パスを残す。

- 止まった段階（prepare・build・draft update・verify・publish）と status
- helper が出した理由、`problems`、`findings`、長さと残り文字数
- 対象の `owner/repo#N` と snapshot の SHA
- 管理対象・archive・metadata を変更していないこと
- 再開に使う snapshot・segments・承認済み draft・URL 置換の比較元・実施結果の完全パス
- 複数 Issue の整理では、完了済みと未実施の操作、確認済み URL、次に確認する現状
