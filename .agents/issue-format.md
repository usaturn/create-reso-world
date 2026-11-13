# issue-format v1: Issue の共有の書式

この文書は create-reso-world の Issue の共有書式（`issue-format v1`）を定める。節の名前と順序、タイトル、ラベル、機械可読ブロック、実行記録・評価コメントの形はここに定義する。移植元は `usaturn/agent-workspace` の commit `6e71fae4d25f217b23ce2409517cf602437a3cbf` である。

- 既存の `planning-parallel-issues` や `issue-to-pr` がこの書式に対応済みであることを意味しない
- 検査と、ブロックの読み書きは `.agents/scripts/issue_format.py` が行う（9 章）。この helper は、この文書の表を読んで規則にする。節の表（1 列目が `` `## <見出し>` `` の行）とラベルの表（1 列目が `` `<系統>: <値>` `` の行）の 1 列目の形を変えると、検査の結果が変わる。これらの形の表は、この文書の本文（コードブロックの外）にほかの用途で書かない
- 記入例は架空のもの（リポジトリ `example-owner/example-repo`、Issue #9001 など）。実在の Issue・PR・指摘を記入例にしない。記入例をコードブロックに入れずに Issue やコメントへ貼らない（機械可読ブロックとして読まれる）
- 機械可読ブロックの記入例（5〜7 章）は、`issue_format.py` の `render_block` が出す形をそのまま載せている

## 1. 適用範囲

- `--repo owner/repo` を明示する。対象は create-reso-world、ResoLoop fork/upstream、固定経路の resoloop-meshy、採用済み external-tools 台帳の通常ツールに限る
- helper は常設親と対象の checkout・remote を共通 resolver で検証する。未登録・不在・不一致は拒否し、別対象に切り替えない。`root` は書式を読む作業ツリーであり、台帳の親ではない
- 外部対象にもこの書式を使う場合は案にその旨を明示し、対象の `AGENTS.md` と `README.md` を先に読む。対象の検証は実装・release・実機操作の許可ではない
- 投稿案の提示後に利用者が承認した案だけを公開する。非対話では下書きで止める。PR と既存 Issue の一括移行は対象外にする

## 2. タイトル

- 既定は、日本語の 1 文で「何をどうするか」を書く
- 接頭辞を付けない。種別（`fix:`・`feat:`・`chore:`）も、構成要素（`agent-runner:`・`issue-to-pr:`）も、角括弧のタグ（`[Jev]`）も付けない（種別・対象領域はラベルにある）
- 利用者が明示したときだけ英語にする（opt-out）。opt-out したら、機械可読ブロックの `title_language` を `"en"` にする
- helper の検査（タイトルを渡したとき）: ASCII の語と `:` で始まる、または角括弧のタグで始まる → `title_prefix`。日本語の文字（ひらがな・カタカナ・漢字）を含まず、`title_language` が `"ja"` → `title_not_japanese`。空 → `title_empty`

## 3. 本文の節

本文は、次の表の必須の節を、この順に、レベル 2 の見出し（`## <見出し>`）で持つ。見出しの文字列は表と完全に一致させ、補足は本文に書く。表は `issue_format.py` が読む（1 列目が `` `## …` `` の行）。

| 見出し | 必須 | 書く内容 | 対応する metadata 配列 |
|---|---|---|---|
| `## 概要` | 必須 | 表: 種別・対象領域・優先度・規模（能動時間の幅・確信度・不確実さの要因）・起票の契機（発見経路とリンク）・次の操作 | — |
| `## 問題と影響` | 必須 | 誰が何に困っているか、影響を受ける人数、停止時間、手作業の量、回避策の有無 | — |
| `## 改善前の状態（基準値）` | 必須 | 指標・値・データ源・取得日。測っていなければ「未計測」と理由 | `baselines` |
| `## 目標値と評価方法` | 必須 | 指標ごとの目標、評価方法（データ源・測定回数・測定条件）、評価時期 | `targets` |
| `## 再現手順` | 任意 | 不具合（`type: bug`）で推奨。手順・期待・実際 | — |
| `## 作るもの` | 任意 | 推奨案。細部を Spec に任せる範囲 | — |
| `## 受け入れ条件` | 必須 | 観察できる形で書く。動作環境・受け付けるべき実入力・防御範囲（対象と、対象にしない反例）・テスト（「テストの採用基準」に当たるものだけ）・完了条件 | — |
| `## 対象外` | 必須 | やらないこと | — |
| `## 関連 Issue・依存関係` | 必須 | 親・先行・重複（探した範囲と結果）・過去の類似・関連 | — |
| `## 決定済みの事項` | 必須 | 利用者が決めたこと（決めた日と根拠） | — |
| `## エージェントに任せる事項` | 必須 | 推奨案で決めてよいこと | — |
| `## 未決事項` | 必須 | 利用者の判断が要り、答えで作るものが変わることだけ。無ければ「なし」と書く | — |

4 列目は、その節の内容を入れる機械可読ブロック（5 章）の配列を示す。`baselines`・`targets` はそれぞれちょうど 1 つの必須の節に対応する。対応する節に、コードブロックと HTML コメントを除いた読む行の内容があり、metadata の配列が空なら、helper は `section_metadata_empty` にする（9 章）。

書く規則は次のとおり。

- 必須の節は空にしない。当てはまらないときは `該当なし（<理由>）` と書く。理由の無い `該当なし` だけの節は、helper が `section_no_reason` として拒否する。空の節は `section_empty`
- 「未決事項」だけは例外で、無ければ「なし」と書く。ほかの必須の節には、「なし」ではなく `該当なし（<理由>）` と書く（helper は「なし」だけの節を拒否しないが、書式の規則としては `該当なし（<理由>）` を使う）
- 任意の節と、表に無い節（ボードの子の「担当ファイル」など、ほかのスキルが足す節）は、どこに置いてもよい。helper は表に無い見出しを無視する
- **指標の節と空の配列**: 基準値の節と目標値の節に内容があるのに、対応する `baselines`・`targets` が空のままでは、評価の対象から黙って抜ける。内容がある節では配列を埋める。配列を空にできるのは、節全体が理由付きの `該当なし（<理由>）`・`なし`・親の節を参照するだけの文のときだけである（9 章）。基準値が未計測でも、`baselines` を空にせず、`value` に「未計測」と理由を入れる。目標値の節が「未計測」だけで `targets` が空なら `section_metadata_empty` になる。目標そのものが無いときは、仮の目標を作らず、節を理由付きの `該当なし（<理由>）` にする
- **未決事項とエージェントに任せる事項の区別**: `issue-to-pr` は、本文が利用者の判断・承認を求めていると停止する（`issue-to-pr` の SKILL.md 2 章の 4）。推奨案で決めてよいことは「エージェントに任せる事項」に書く。「未決事項」には、利用者しか決められず、答えで作るものが変わることだけを書く。着手してよい Issue の「未決事項」は「なし」にする
- 受け入れ条件は、`issue-to-pr` の Spec レビュー・builder check が「利用者の判断」の問いを出さない程度に、観察できる形で書く
- **概要の表の分類の行**（種別・対象領域・優先度・規模の区分・起票の契機の区分）は、ラベルの値の表示である。ラベルを基準とし、食い違ったらラベルに合わせて本文を直す。helper は本文の表とラベルの一致を検査しない
- **ほかのスキルの管理対象の節**: `planning-parallel-issues` の `<!-- planning-parallel-issues:<名前>:start -->` から同じ名前の `:end -->` までの範囲（ボード、ledger など）は、そのスキルの形のまま置く。helper は節の検査でこの範囲を読まない。ボードの子の先頭のマーカー行（`<!-- planning-parallel-issues board:… -->`）も変えない
- 見出しの判定は、コードブロック（backtick 3 個以上か `~~~` 以上の囲み）の外の行だけで行う。リスト項目の中の囲み（リスト記号（`-`・`*`・`+`・`1.`・`1)`）と空白 1〜4 個の直後に書いた囲み）もコードブロックとして扱う。この囲みの閉じの行は、リスト項目の内容の位置（開きの行で囲みの文字が始まる列）から 3 列以内に字下げして書く。内容の位置より字下げの少ない行（空行を除く）はリスト項目の終わりなので、閉じの無い囲みはその行の前で終わり、その行は囲みの外として判定し直す。引用（`>`）の中の囲みは追わず、コードブロックとして扱わない
- 見出しは、行頭から `## ` で書く（行頭に空白を置かない）。行頭に空白を置いた行は、GitHub の画面では見出しとして表示されることがあるが、helper は見出しとして数えず、その節が無いものとして `section_missing` にする
- **HTML コメント**: コードブロックの外で、行頭（空白 0〜3 個）が `<!--` の行から、最初に `-->` を含む行まで（`-->` が無ければ本文の終わりまで）は、GitHub の画面に出ない。helper は節の検査でこの範囲を読まない。コメントの中に書いた見出しは節として数えず、コメントだけの節は空の節（`section_empty`）になる。画面に出したい節は、コメントの外に書く

### 未確定の値（最低限の手動フロー）

起票の時点で決められない値は、本文に「未確定」と書いて理由と決め方を添え、次の 3 つをそろえる。

1. 本文の該当箇所に `未確定（理由: …。決め方: …）` と書く
2. 機械可読ブロックの `undetermined` に、項目（`type`・`area`・`priority`・`size`・`source`・`estimate` のどれか）・理由・決め方を書く
3. ラベル `triage: needed` を付ける

決めたら、ラベルを付け、`undetermined` から外し、`triage: needed` を外す。整形時は、ラベルを基準として本文を合わせる。

### 整形前の本文の保存

整形では、整形前の本文を `<details>` で 1 つだけ残す。通常は新しい書式に組み直した本文の末尾に置くが、`pad` 付きの包みを再利用するときは最後の archive 管理対象の直後に接続し、包みの後ろにスロットと管理対象が続くことがある（下の `pad` の記述）。保存の意味は、archive を読み戻して再構成した本文である（helper の `PreparedBody.archive_body` と manifest の `archive_body_sha256`）。再構成の結果は、保存すべき本文とバイト単位で一致しなければならない。元の本文には、新しい書式と同じ名前の見出しや、古い機械可読ブロック・ボードのマーカーが含まれうる。囲みの中は、見出し・ブロック・管理対象の範囲の走査から外れる（上の「見出しの判定は、コードブロックの外の行だけで行う」）。

保存の仕方は 2 つある。どちらも payload を JSON 文字列にしない。囲みの backtick の数は、中身に現れる最も長い backtick の並びより 1 つ以上多く、3 以上にする。囲みは helper の `wrap_original` で作り、`unwrap_original` で取り出す（9 章）。`info` を省略した呼び出しは旧形式のままである。手で書かない。

**旧形式**（info string は `issue-format-original`）は、保存すべき本文をそのまま囲みに入れる。この記入例の外側の囲みは `~~~` である（中の backtick の囲みで閉じないため）。

~~~text
<details><summary>整形前の本文（2026-11-09 に issue-authoring が保存）</summary>

`````issue-format-original
<元の本文をそのまま>
`````

</details>
~~~

**新形式**（info string は `issue-format-original-managed-v1`）は、管理対象のバイト列を複製しない。囲みの中は次のテキストである。

1. 1 行目は `issue-format-original-managed-v1`、空白 1 つ、区切りである。区切りは `@` の並びで、長さは 2 以上、かつ管理対象外の切り出しと `kind:name` に含まれない最短の長さである。含まれるなら `@` を足して長くする。保存すべき本文の末尾が管理対象の中で、その末尾に LF が無いときだけ、区切りの後に空白と `pad` を足す
2. 改行のあと、管理対象外の原文を、保存すべき本文の位置の切り出しの順に置く。管理対象があった位置には、位置マーカー `{区切り}{kind}:{name}{区切り}` を置く。マーカーも切り出しも、改行を足したり末尾の改行を削ったりしない
3. 復元は、位置マーカーを live の管理対象の `text` で置き換える。archive の位置マーカーが live の管理対象に順序を保って一意に対応するときだけ置き換える。archive に無い live の管理対象（追加）は復元に使わず許容する。対応しない archive マーカー（削除）、順序や kind・name の違い、対応の一意性が無い場合（同じ kind:name が live に複数あり対応が決まらない）、区切りが本文と衝突して一意に読めないときは失敗として止め、通常の本文として黙って通さない。位置マーカーを全て消した場合も構造不正として止める。位置マーカーの一部の消去は、live の管理対象が増えた状態と同じ形になり追加と区別できないため検出しない。archive は helper が管理し、位置マーカーを手で編集しない

管理対象の終端にある LF と CRLF は、直後が archive でも管理対象に含めたままにする。archive が続くからといって、もともと範囲に含まれる改行を外したり、編集できるスロットへ出したりしない。

保存すべき本文の末尾が管理対象の中で、その末尾に LF が無いときだけ、archive を次の行に置くために足す LF を管理対象にも保存本文にも含めない。位置マーカーも、この LF を足さない。印は新形式の 1 行目の `pad` だけである。`pad` が無い新形式は、この LF を足していない。復元は、この LF を足さずに元のバイト列と一致する。この LF は編集できるスロットには出さず、archive の範囲に含める。`pad` があるのに、包みの直前の LF が管理対象の終端でないときは、範囲を黙って変えずに拒否する。CR だけで終わる行の直後にこの LF を足すときも、その LF は管理対象へ混ぜず、CR を CRLF に変えない。pad の LF は最後の archive 管理対象（archive の最後の位置マーカーに対応する管理対象）に帰属する。最後の archive 管理対象と包みの間への追加は停止する。追加の kind:name が最後の archive 管理対象と異なれば pad の LF の帰属が合わず、同じ kind:name なら帰属検査はラベルの一致で通過するため、位置マーカーの対応が一意でなくなる一意性判定で止まる。同名のときは追加の範囲が帰属検査で pad の LF を引き受けるが、復元が成功することはない。`pad` 付きの包みを再利用するときは、包みを本文の末尾ではなく最後の archive 管理対象の直後に pad の LF 1 つを挟んで接続し、その管理対象より後ろのスロットと管理対象は包みの後ろに続ける。追加が無いときは最後の archive 管理対象が最後の live の管理対象なので、本文の末尾への接続と同じになる。

管理対象外の切り出しは、metadata を除いた編集用のスロットではなく、保存すべき本文の位置から取る。live から旧 metadata を除いても、復元結果からは消えない。

旧形式と新形式のどちらも、囲みの前後の `<details><summary>…</summary>` の行と `</details>` の行（空行を挟んで隣り合うもの）は、節の内容として数えない。本文の末尾にこの包みが付いても、最後の必須の節が空なら `section_empty` になる。元の本文は、表示上コードとして出る。整形の記録として残すもので、読み物として表示しない。

1 つの本文に archive は 1 つだけ置く。旧形式と新形式が両方ある、または archive が複数あるときは、どれかを選ばずに拒否する。

使い分けは次の 3 つである。包みを手で変えたものを移行として扱わない。

1. **初回**（archive が無い）: 管理対象が 0 件なら、snapshot の本文全体を旧形式で保存する。1 件以上なら新形式で保存する。復元は snapshot の本文全体と一致する。起票の経路や metadata の有無では分けない。summary は build を実行した日を記録する。verify は、その記録した summary で期待する包みを作る。verify を実行した日の日付では判定しない。記録した summary の形でない初回の包みは、期待する包みと一致しない
2. **旧形式の条件付き移行**: 既存の包みが、その中身と summary から `wrap_original` が作る旧形式とバイト単位で一致し、中身の管理対象の数・順序・kind・name・text が live と一致し、かつ 1 件以上あるときだけ、新形式へ移す。summary は旧包みのものを保持する。復元は旧 archive の中身と一致する。一致しない、0 件、または包みがその形でないときは移行しない
3. **再利用**: 既存の新形式、および移行しない旧形式は、包みをバイト単位でそのまま残す。保存本文は、旧形式なら中身そのもの、新形式なら位置マーカーを live の管理対象で戻した本文である

上限を超える本文は、新形式でも `too_large` で止める。本文・管理対象・archive を削らない。

## 4. ラベル

ラベルの名前は `<系統>: <値>`（コロンの後に半角空白 1 つ）にする。ラベルの表は 3 列（`| ラベル | 色 | 説明 |`）で、1 列目にラベル名を backtick で書く。節の表（3 章）は 4 列（`| 見出し | 必須 | 書く内容 | 対応する metadata 配列 |`）で、4 列目に `baselines`・`targets` のどちらかを backtick で書くか、対応しない節は `—` を書く。`issue_format.py` は、この文書の表のうち、1 列目が `` `<系統>: <値>` ``（系統は `type`・`area`・`priority`・`size`・`source`・`triage`）の行を読む。表の行以外（本文・記入例）に、この形の 1 列目を持つ表を書かない。色は `#` の無い 6 桁の 16 進、説明は 100 文字以内（GitHub の上限）にする。表の定義の行（節・ラベル。1 列目が `` `## …` `` か `` `<系統>: …` `` で始まる行）は、`|` で始めて `|` で終え、節はちょうど 4 セル、ラベルはちょうど 3 セルにする。セルの中に `|` を書かない。helper は行を `|` で単純に分けるので、`|` を書くとセルが増え、余ったセルは読み捨てられて、説明が黙って途中で切れる（`\|` と書いても同じ）。1 列目に `|` を書くと、定義の行が黙って読み飛ばされる。そのため、定義の行のセルが節は 4 つ・ラベルは 3 つでない、末尾に `|` が無い、`\|` がある、1 列目の形が合わない場合は、`load_rules` が拒否する。節の 4 列目が空・`—`・`baselines`・`targets` のどれでもない場合も拒否する。

| 系統 | 付ける数 | 値の定義元 |
|---|---|---|
| type: | ちょうど 1 | この文書 |
| area: | 1 以上（複数の領域にまたがるときは複数） | この文書 |
| priority: | ちょうど 1 | この文書 |
| size: | ちょうど 1 | この文書 |
| source: | ちょうど 1 | この文書 |
| triage: | 未確定の値があるときだけ `triage: needed` を 1 つ | この文書 |

ラベル名は、大文字・小文字を区別せずに照合する（GitHub がそう扱う）。

**`type:`**

| ラベル | 色 | 説明 |
|---|---|---|
| `type: bug` | `d73a4a` | 期待と違う挙動・壊れた手順・誤った結果 |
| `type: feature` | `a2eeef` | 新しい機能・スキル・コマンド・設定を足す |
| `type: improvement` | `84b6eb` | 既存の機能の挙動・使い勝手・性能・書式を良くする |
| `type: maintenance` | `c5def5` | 依存の更新・片付け・リファクタリング・テストの整理（利用者に見える挙動を変えない） |
| `type: investigation` | `bfd4f2` | 調査・評価。成果は報告で、コードの変更を伴わないことがある |

**`priority:`**（P0〜P3）

| ラベル | 色 | 説明 |
|---|---|---|
| `priority: P0` | `b60205` | すぐ対応する。利用・開発が止まっている、データや秘密情報を失う・漏らす |
| `priority: P1` | `d93f0b` | 次に着手する。回避策はあるが、毎回の手作業や誤りが続く |
| `priority: P2` | `f9d0c4` | 計画して着手する。開発は止まっていないが効果が大きい |
| `priority: P3` | `fef2c0` | 余裕があるときに着手する。小さな改善・将来の候補 |

**`size:`**（能動時間の目安。L の「2 日」を能動時間 16 時間とした）

| ラベル | 色 | 説明 |
|---|---|---|
| `size: XS` | `c2e0c6` | 能動時間 30 分以内 |
| `size: S` | `9be9a8` | 能動時間 2 時間以内 |
| `size: M` | `40c463` | 能動時間 6 時間以内（1 セッション） |
| `size: L` | `30a14e` | 能動時間 16 時間以内（2 日。分割を勧める） |
| `size: XL` | `216e39` | 能動時間 16 時間を超える（分割が必須） |

規模の書き方: 概要の表の「規模」の行に、区分・能動時間の幅・確信度（高・中・低）・不確実さの要因（外部 API の挙動が未確認、実機での確認が必要、複数リポジトリにまたがる など）を書く。区分は、見積もりの上限が入る区分にする。数値は機械可読ブロックの `estimate` に入れる。L 以上は「次の操作」で `planning-parallel-issues` での分割を、M 以下は `issue-to-pr` を勧める。helper は区分と時間の食い違いを検査しない（区分はラベルを基準とし、利用者が画面で直すことがある）。

**`source:`**（発見経路）

| ラベル | 色 | 説明 |
|---|---|---|
| `source: usage` | `bfdadc` | 利用中（利用者・エージェントの作業中）に気づいた |
| `source: user-report` | `bfdadc` | 利用者からの報告 |
| `source: ci` | `bfdadc` | CI の失敗 |
| `source: monitoring` | `bfdadc` | 監視・定期の検査で見つけた |
| `source: code-review` | `bfdadc` | コードレビュー（PR のレビュー・修正ループの持ち越し候補を含む） |
| `source: ai-detected` | `bfdadc` | 調査・監査を依頼した AI の検出 |
| `source: planned` | `bfdadc` | 計画した改善 |

本文（概要の「起票の契機」）と機械可読ブロックの `discovery.links` に書くリンクは、`source:` ごとに次のとおり。

- usage: 気づいた作業の記録（PR・コメント・ログの場所）
- user-report: 元の報告
- ci: CI の run
- monitoring: 検出の記録
- code-review: レビューのコメント
- ai-detected: 検出した実行の結果
- planned: 計画の根拠（親 Issue・議論）

ローカルにしか無い記録は、`discovery.note` にパスと日時を書く。helper は `source:` ごとのリンクの有無を検査しない。

**`area:`** — 1 Issue に 1 つ以上、最も具体的なものを付ける。

表の説明は GitHub の上限（100 文字）に収めるため、表に書ききれない領域とパスの対応を、次に書く。

- `area: review`: PR レビューと修正のスキル・補助ツール
- `area: issue-workflow`: Issue の起票・計画・着手と共有書式
- `area: skills`: 上記以外のスキル
- `area: python`: ルートの `pyproject.toml`・`uv.lock` と共通 Python 環境
- `area: external-tools`: `external-tools.toml` と `tools/external_tools/` の対象解決

| ラベル | 色 | 説明 |
|---|---|---|
| `area: agent-runner` | `1d76db` | 外部の agent の起動と割り当て（tools/agent_runner/・.devcontainer/agent-runner.toml） |
| `area: review` | `1d76db` | PR のレビューと修正ループ |
| `area: issue-workflow` | `1d76db` | Issue の起票・計画・着手（issue-authoring・planning-parallel-issues・issue-to-pr・issue-format.md） |
| `area: skills` | `1d76db` | review・issue-workflow に当たらないスキル（.agents/skills/・.claude/skills/） |
| `area: devcontainer` | `1d76db` | Dev Container の構成・導入・ランチャー（.devcontainer/・scripts/ の導入スクリプト） |
| `area: external-tools` | `1d76db` | external-tools 台帳と対象リポジトリの解決 |
| `area: python` | `1d76db` | ルートの Python 環境と依存関係 |
| `area: test-ci` | `1d76db` | ローカル検証とテストの基盤 |
| `area: resonite-blender` | `1d76db` | Resonite・Blender のワールド、モデル、ツール |
| `area: docs` | `1d76db` | AGENTS.md・README など、特定の領域に属さない文書 |

**`triage:`**

| ラベル | 色 | 説明 |
|---|---|---|
| `triage: needed` | `ff9f1c` | 決められない値（未確定）がある。決めたら外す |

### 既存のラベルとの対応

| 既存のラベル | 扱い |
|---|---|
| `bug` | 新しく付けない。`type: bug` を付ける。整形では外す案を出す（ラベルそのものは削除・改名しない） |
| `enhancement` | 新しく付けない。`type: feature` か `type: improvement` を付ける。整形では外す案を出す |
| `documentation` | 新しく付けない。`area: docs` など文書の対象領域を付ける。種別は内容で決める |
| `duplicate`・`invalid` | 重複・誤検知で閉じるときに付ける（8 章） |
| `wontfix`・`question`・`good first issue`・`help wanted`・`accessibility` | 新しく付けない。付いていても helper は無視する |
| `planning:`・`implementation:` | `planning-parallel-issues` が使う。変えない |
| `dependencies`・`github_actions`・`javascript`・`python:uv` | 依存の更新の自動化が PR に付ける。変えない |

### 不足するラベルを作る手順

1. 対象のリポジトリの既存のラベルを `gh api --paginate repos/<owner>/<repo>/labels` で取得し、ファイルに保存する
2. `issue_format.py labels --repo <owner>/<repo> --existing-json <そのファイル>` で、この文書の表の定義のうち無いものを出す
3. 起票・整形の案に、作るラベル（名前・色・説明）を含め、利用者の承認を得る
4. 承認の後に `gh label create "<名前>" --repo <owner>/<repo> --color <色> --description "<説明>"` で作る。`--force` を付けない（既存のラベルの色・説明を上書きする）。already exists で失敗したら、取得し直して名前を比べる
5. ラベルの定義は必ずこの文書の表から読む。スキルや helper に写さない

## 5. 機械可読ブロック（本文）

本文に 1 つだけ置く HTML コメント。分類の値（種別・対象領域・優先度・規模の区分・発見経路の区分）はラベルだけに持たせ、ブロックに写さない。ブロックには、ラベルにできない値を入れる。

形（行単位。改行は LF）:

~~~text
<!-- issue-format:metadata:v1
{
  "filed_on": "2026-11-09",
  ...
}
-->
~~~

- 1 行目は `<!-- issue-format:<種類>:v<版>` だけにする（前後に何も書かない）。種類は `metadata`（本文）・`run-record`（実行記録コメント）・`evaluation`（評価コメント）。版は 1 から数える整数
- 続く行が JSON（`json.dumps(..., ensure_ascii=False, indent=2)` の出力）。**JSON の中の `<` と `>` は、6 文字の `\u003c`・`\u003e`（バックスラッシュ・`u`・4 桁の 16 進）に置き換えて書く**。JSON の文字列のエスケープなので、読み戻すと元の文字になる。これで、値に `-->`・`<!--`・`--!>` があってもコメントが途中で閉じない。改行・タブなどの制御文字は、JSON のエスケープ（`\n` など）で 1 行に収まる
- 最後の行は `-->` だけにする
- 置き場所: 本文の末尾（ほかのスキルの管理対象の節より後でもよい）。コードブロックの中に置かない。本文に同じ種類のブロックを 2 つ置かない。本文に `run-record`・`evaluation` のブロックを置かない
- 本文を書き換えるときは、helper の `write_metadata` を使う（既存のブロックをその位置で置き換えるか、末尾に足す）。手で JSON を書き換えない。書き込みの後に読み戻して確かめ、同じ値に戻らない本文は返さない

記入例（架空の値。`discovery.note` の `<A>`・`<B>`・`-->` が、エスケープの形で書かれる）:

~~~text
<!-- issue-format:metadata:v1
{
  "filed_on": "2026-11-09",
  "bases": [
    {
      "repository": "example-owner/example-repo",
      "branch": "main",
      "sha": "0123456789abcdef0123456789abcdef01234567"
    }
  ],
  "estimate": {
    "hours_low": 1.5,
    "hours_high": 3.0,
    "confidence": "medium",
    "uncertainties": [
      "外部 API の挙動が未確認"
    ]
  },
  "baselines": [
    {
      "metric": "手作業の確認にかかる時間",
      "value": "1 回あたり約 12 分",
      "source": "作業ログ（直近 5 回の平均）",
      "measured_on": "2026-11-08"
    }
  ],
  "targets": [
    {
      "metric": "手作業の確認にかかる時間",
      "target": "1 回あたり 3 分以内",
      "method": "作業ログ。直近 5 回の平均。通常の作業中に測る",
      "timing": "マージの 2 週間後",
      "due": "2026-11-30"
    }
  ],
  "discovery": {
    "links": [
      "https://github.com/example-owner/example-repo/pull/9000"
    ],
    "note": "PR #9000 のレビュー中に、手順 \u003cA\u003e -\u003e \u003cB\u003e の出力が途中で切れたログ（--\u003e）を見つけた"
  },
  "title_language": "ja",
  "undetermined": []
}
-->
~~~

v1 のキー（pydantic のモデル `IssueMetadata`。未知のキーは拒否する）:

| キー | 型 | 内容 |
|---|---|---|
| `filed_on` | 日付（`YYYY-MM-DD`） | 起票・事実の確認をした日 |
| `bases` | 配列（1 件以上） | 起票時の base。各要素は `repository`（`owner/name`）・`branch`・`sha`（40 桁） |
| `estimate` | object か `null` | `hours_low`・`hours_high`（能動時間。`0 ≤ low ≤ high`、`high > 0`）・`confidence`（`high`・`medium`・`low`）・`uncertainties`（文字列の配列。`confidence` が `high` 以外なら 1 件以上）。`null` は未確定のときだけで、`undetermined` に `estimate` が要る |
| `baselines` | 配列 | 基準値。各要素は `metric`・`value`（「未計測」も可）・`source`（データ源）・`measured_on`（日付か `null`）。本文の対応する節が理由付き `該当なし`・`なし`・親の節を参照するだけの文のときだけ空にする。未計測は配列を空にせず、`value` に「未計測」と理由を書く |
| `targets` | 配列 | 目標値。各要素は `metric`・`target`・`method`（データ源・測定回数・測定条件）・`timing`（評価時期の条件）・`due`（期日か `null`）。本文の対応する節が理由付き `該当なし`・`なし`・親の節を参照するだけの文のときだけ空にする。目標そのものが無いときは、本文を理由付き `該当なし` にし、仮の目標を入れない |
| `discovery` | object | `links`（`http(s)://` の URL の配列）・`note`（文字列か `null`） |
| `title_language` | `"ja"` か `"en"` | 既定は `"ja"`。`"en"` は利用者の明示の opt-out のときだけ |
| `undetermined` | 配列 | 未確定の項目。各要素は `item`（`type`・`area`・`priority`・`size`・`source`・`estimate`）・`reason`・`how_to_decide`。項目は重複しない |

文字列は空にしない（空白だけも不可）。改行・非 ASCII を含んでよい。

## 6. 実行記録コメント

実行記録を投稿する場合、1 回の run で 1 件の新しいコメントにし、ほかのコメントを編集しない。既存の `issue-to-pr` による投稿は実装済みと仮定しない。人が読む本文（見出し `## issue-to-pr の実行記録` など）の後に、空行を挟んで `run-record` のブロック（5 章と同じ形）を置く。ブロックがマーカーを兼ねる。

記入例（架空の値）:

~~~text
## issue-to-pr の実行記録

- 結果: PR を作成した（example-owner/example-repo#9002）
- 能動時間: 120 分（区分 S）

<!-- issue-format:run-record:v1
{
  "issue": {
    "repository": "example-owner/example-repo",
    "number": 9001
  },
  "skill": "issue-to-pr",
  "session": "00000000-0000-4000-8000-000000000001",
  "runtime": "example-runtime",
  "model": "example-model",
  "started_at": "2026-11-09T01:00:00Z",
  "ended_at": "2026-11-09T03:30:00Z",
  "outcome": "pr_created",
  "active_minutes": 120.0,
  "user_wait_minutes": 15.0,
  "tasks": [
    {
      "name": "Task 1",
      "minutes": 45.0
    },
    {
      "name": "Task 2",
      "minutes": 60.0
    }
  ],
  "actual_size": "S",
  "stops": [],
  "resumes": 0,
  "review_cycles": null,
  "pr": "https://github.com/example-owner/example-repo/pull/9002"
}
-->
~~~

v1 のキー（`RunRecord`）:

| キー | 型 | 内容 |
|---|---|---|
| `issue` | object | `repository`（`owner/name`）・`number` |
| `skill` | 文字列 | 投稿したスキル（`issue-to-pr`） |
| `session` | 文字列か `null` | セッションの ID |
| `runtime`・`model` | 文字列 | 例: `claude-code`・`claude-opus-5-5` |
| `started_at`・`ended_at` | タイムゾーン付きの日時 | `ended_at ≥ started_at` |
| `outcome` | `pr_created`・`merged`・`stopped` | run の終わり方 |
| `active_minutes`・`user_wait_minutes` | 数（0 以上） | `issue_budget.py show` の `active_seconds`・`user_wait_seconds` を分にしたもの |
| `tasks` | 配列 | 主要 Task 別の内訳。各要素は `name`・`minutes` |
| `actual_size` | `XS`〜`XL` | `active_minutes` を 4 章の `size:` の表に当てた区分 |
| `stops` | 配列 | 停止。各要素は `reason`・`kind`（`expected`: 想定された停止、`unexpected`: 予期しない障害）。`outcome` が `stopped` なら 1 件以上 |
| `resumes` | 整数（0 以上） | 停止の後に再開した回数 |
| `review_cycles` | 整数（0 以上）か `null` | レビュー修正ループのサイクル数。ループを回さなかったら `null` |
| `pr` | URL か `null` | `outcome` が `pr_created`・`merged` なら必須 |

## 7. 評価コメント

評価時期に目標値を持つ Issue へ評価コメントを投稿する場合、人が読む本文の後に、空行を挟んで `evaluation` のブロックを置く。

記入例（架空の値）:

~~~text
## 評価の結果

目標の 1 指標を達成した。

<!-- issue-format:evaluation:v1
{
  "issue": {
    "repository": "example-owner/example-repo",
    "number": 9001
  },
  "evaluated_at": "2026-11-30T00:00:00Z",
  "runtime": "example-runtime",
  "model": "example-model",
  "scope": "マージ後 2 週間の作業ログ 5 件（Issue #9001 の対象の作業）",
  "results": [
    {
      "metric": "手作業の確認にかかる時間",
      "target": "1 回あたり 3 分以内",
      "actual": "1 回あたり約 2 分 40 秒",
      "achieved": true,
      "gap": "なし"
    }
  ],
  "notes": null
}
-->
~~~

v1 のキー（`Evaluation`）:

| キー | 型 | 内容 |
|---|---|---|
| `issue` | object | `repository`（`owner/name`）・`number` |
| `evaluated_at` | タイムゾーン付きの日時 | 評価した日時 |
| `runtime`・`model` | 文字列 | 評価を実行した runtime・モデル |
| `scope` | 文字列 | 評価の対象。Issue の範囲・件数・抽出の条件 |
| `results` | 配列（1 件以上） | 各要素は `metric`・`target`・`actual`・`achieved`（真偽。判定できないとき `null`）・`gap`（期待とのずれ） |
| `notes` | 文字列か `null` | 補足 |

### 実行記録・評価コメントの共通の規則（読む側）

- 読む側（抽出 helper ほか）は、書き込み権限のある投稿者（`author_association` が `OWNER`・`MEMBER`・`COLLABORATOR`）のコメントだけを記録として読む
- 1 つのコメントに同じ種類のブロックを 2 つ置かない。記録のコメントは人が編集しない（補足は別のコメントに書く）
- この文書の記入例を、コードブロックに入れずにコメントへ貼らない（記録として読まれる）

## 8. 重複・誤検知で閉じるとき

- 重複: `gh issue close <N> --repo <owner>/<repo> --duplicate-of <重複先>`（`state_reason` が `duplicate` になる）。`duplicate` ラベルを付ける
- 誤検知（実際には問題が無かった）: `gh issue close <N> --repo <owner>/<repo> --reason "not planned"` と `invalid` ラベル
- 対応しない判断（問題はあるがやらない）: `--reason "not planned"`。`invalid` は付けない
- 発見経路（`source:`）ごとの重複・誤検知の割合は、`state_reason` とこのラベルから数える。閉じるときに `source:` のラベルを外さない

## 9. helper（`issue_format.py`）

`.agents/scripts/issue_format.py` は pydantic v2 と共通の対象 resolver を使う。この文書の表から書式を読み、検証済み常設親の採用済み台帳と対象 checkout を確認する。GitHub への問い合わせや clone はしない。検査や書式をスキル・helper に写さず、この helper とこの文書を使う。

### CLI

リポジトリルートから `uv run --locked python .agents/scripts/issue_format.py <サブコマンド> ...` で実行する。

~~~text
issue_format.py check --repo OWNER/NAME
    (--issue-json PATH | --body-file PATH [--label NAME]... [--title TEXT])
    [--allow-undetermined]
issue_format.py labels --repo OWNER/NAME [--existing-json PATH]
issue_format.py extract --kind {metadata,run-record,evaluation} --file PATH
~~~

- `check`: 本文・ラベル・タイトルを検査する。`--issue-json` は `gh api repos/<owner>/<repo>/issues/<N>` か `gh issue view --json title,body,labels` の出力（`title`・`body`・`labels[].name` を読む。`body` は `null` も可で、空文字として検査する。`body`・`labels` のキーが無い JSON は入力の誤り）。`--issue-json` は `--label`・`--title` と同時に使えない（usage エラー）。`--body-file` は改行を変換せずに読む（CRLF の本文をそのまま検査する）。標準出力に JSON（`ok`・`complete`・`problems`・`undetermined`・`metadata`（`status`・`version`・`reason`・`line`））を出す。`ok` は、終了コードが 0 になる結果かどうか。終了コードは、`complete` なら 0。`--allow-undetermined` を付けたときは、`problems` が無ければ未確定があっても 0（`issue-authoring` が未確定のまま起票するとき）。それ以外は 1
- `labels`: 定義を出す。標準出力に JSON（`repository`・`definitions`（`name`・`family`・`value`・`color`・`description`））を出す。`--existing-json`（`gh api --paginate repos/<owner>/<repo>/labels` の出力。`--paginate` で配列が複数連結されても、すべての配列の要素を読む）があれば、`missing`（定義にあって無いもの。`definitions` と同じ形）も出す。配列が 1 つも無い入力は入力の誤り。終了コードは 0
- `extract`: ファイル（本文かコメント）から指定した種類のブロックを取り出し、標準出力に JSON（`status`・`version`・`reason`・`line`・`value`）を出す。終了コードは、`ok` なら 0、それ以外は 1
- 入力・定義の誤り（未登録のリポジトリ、読めないファイル、壊れた JSON の入力、定義の表の誤り）は、標準エラー出力に `issue_format: <理由>` を書いて終了コード 2 で終える（argparse の usage エラーも 2）
- 標準出力の JSON は `ensure_ascii=False` で出す

定義の誤りは、検査の誤りのまま進めずに、`load_rules` が `FormatError` にする。次の場合である: `--repo` が許可された対象でない、対象や採用済み台帳を検証できない、定義の表が読めない（UTF-8 でない場合を含む）、5 系統と `triage` のどれかのラベルが 0 件、`triage:` が 1 件でない、同じ名前のラベルが 2 回、1 列目が `` `<系統>: <値>` `` の形に合わない、色が 6 桁の 16 進でない、説明が空か 100 文字を超える、必須の節が 0 件、同じ見出しの節が 2 回、節の 2 列目が `必須`・`任意` 以外、節の 4 列目が空・`—`・`baselines`・`targets` のどれでもない、`baselines`・`targets` の対応がそれぞれちょうど 1 つの必須の節でない（0 件・重複・任意の節への対応）、節の定義の行のセルが 4 つでない、ラベルの定義の行のセルが 3 つでない（`|` を書いて余ったセルが出た場合と、足りない場合）・末尾に `|` が無い・`\|` がある、節の 1 列目が `` `## <見出し>` `` の形に合わない。コードブロックの中の表は読まない。

### 検査の問題の識別子

`check` と `check_issue` の `problems` が持つ `code` は、次のとおり。後続のスキルは、この識別子で処理を分ける。

| code | 条件 |
|---|---|
| `section_missing` | 必須の節の見出しが無い |
| `section_duplicate` | 必須の節の見出しが 2 回以上 |
| `section_order` | 必須の節が表の順に並んでいない |
| `section_empty` | 必須の節の内容が空（節の検査で読まない範囲を除いて、空白しか無い） |
| `section_no_reason` | 必須の節の内容が `該当なし` だけ |
| `section_metadata_empty` | 対応する metadata 配列がある必須の節に、除外に当たらない内容があり、正常に読めた metadata の配列が空 |
| `label_missing` | 必須の系統のラベルが無く、未確定としても宣言されていない |
| `label_multiple` | `type`・`priority`・`size`・`source`・`triage` が 2 つ以上 |
| `label_unknown` | 5 系統と `triage` の接頭辞を持つが、定義に無い名前 |
| `undetermined_conflict` | `undetermined` に挙げた系統のラベルが付いている |
| `triage_missing` | 未確定の項目があるのに `triage: needed` が無い |
| `triage_stale` | `triage: needed` があるのに未確定の項目が無い |
| `block_missing` | 本文に `metadata` のブロックが無い |
| `block_broken` | `metadata` のブロックが壊れている（`metadata.reason` に理由） |
| `block_unknown_version` | `metadata` のブロックの版が分からない |
| `block_misplaced` | 本文に `run-record`・`evaluation` のブロックがある |
| `title_empty`・`title_prefix`・`title_not_japanese` | 2 章（`title` を渡したときだけ） |

- **節の検査で読まない範囲**: 次の行を読まない。(1) コードブロックの中（`issue-format-original` と `issue-format-original-managed-v1` の囲みと、リスト項目の中の囲みを含む。リスト項目の中の囲みは、リスト記号の後の囲みで、閉じはリスト項目の内容の位置から 3 列以内に字下げした行。字下げの足りない行でリスト項目が終わり、閉じの無い囲みはその行の前で終わる。引用（`>`）の中の囲みは追わない）と、その囲みの前後の `<details><summary>…</summary>` の行・`</details>` の行（空行を挟んで隣り合うもの）。(2) HTML コメント（コードブロックの外で、行頭（空白 0〜3 個）の `<!--` の行から、最初に `-->` を含む行まで。`-->` が無ければ本文の終わりまで。機械可読ブロックの範囲を含む。壊れたブロックも、表示されない範囲を除く）。(3) `planning-parallel-issues` の管理対象の範囲
- 節の検査は、上の読む行だけで行う。表に無い見出しは無視する。見出しは、行頭の `## ` で始まる行（行頭に空白を置いた行は数えない）のうち、`## ` の後ろの文字列から、前後の空白を除き、さらに末尾が「空白に続く `#` の並び」（閉じの `#`）ならそれも除いたものが、表の見出しと完全に一致するものだけを数える。`##   概要`（`## ` の後に空白が続く行）や `## 概要 ##`、行末に空白のある `## 概要` は `概要` として数える。`## 概要#` のように `#` の前に空白が無いときは `#` を除かず、`概要#` のままなので一致しない。節の内容は、見出しの次の行から、次のレベル 1・2 の見出しか本文の終わりまでの、読む行である（コードブロックやコメントだけの節は、内容が空になる）
- 5 系統と `triage` の接頭辞（`type:` のように `:` で終わる系統名）を持たないラベル（`bug`・`planning: ready` など）は無視する
- `label_missing`・`label_multiple` は、定義にあるラベルだけを数える。定義に無いラベルは `label_unknown` になり、数えない
- ブロックが `ok` のとき、`undetermined` の項目で、その系統のラベルが無いもの（と `estimate`）は `check` の `undetermined` に入り、`label_missing` にならない。このとき `complete` は成功にならない。ブロックが `ok` でないときは、未確定を読めないので、無いラベルはすべて `label_missing` になり、`triage_stale` は出さない（未確定の項目があるか分からない）
- `title_not_japanese` は、ブロックが `ok` で `title_language` が `"en"` なら出さない

### 本文の指標と空の配列

`baselines`・`targets` に対応する節（3 章の表の 4 列目）は、`metadata` のブロックが `ok` のときだけ、次のように検査する。

- 節の内容（読む行）が空なら `section_empty`、内容が `該当なし` だけなら `section_no_reason` を出し、`section_metadata_empty` は出さない（既存の問題を優先し、同じ節を二重に診断しない）
- 内容があり、対応する配列が空で、節全体が次のどれかなら問題にしない:
  - `該当なし（<空でない理由>）` または半角括弧版だけ。前後の空白・改行と末尾の句点を許す
  - `なし` だけ。末尾の句点を許す
  - 親などの Issue を参照するだけの文。代表形は `親 #9001 の「<指標に対応する節の見出し>」を参照する。この子に固有の指標は無い`。接頭辞は `親`・`親 Issue`・`Issue`・なし。参照先は `#9001`・`owner/repo#9001`・GitHub の Issue URL（Markdown リンクも可）。見出しは `baselines`・`targets` に対応する節の見出しのどちらでもよく、両方を `・` または `と` で並べてもよく、省略してもよい。後半の `この子に固有の指標は無い` は `この Issue に固有の指標はない` でもよく、省略できる。先頭の単一のリスト記号、空白・改行、末尾の句点を許す
- 上の除外は節全体に一致するときだけ使う。`該当なし（<理由>）` の理由は対応する閉じ括弧までとし、その後に指標の表・値・説明が続くときは除外しない。参照の後に指標の表・値・説明が続くときも同じ
- `metadata` のブロックが `ok` でないときは、この検査をしない（`block_missing`・`block_broken`・`block_unknown_version` だけを出す）

修正するときは、子の `baselines`・`targets` に親の値を複製しない。本文の節を親の参照の形に直し、配列は空のままにする。目標そのものが無いときは、目標値の節を `該当なし（<理由>）` にし、仮の目標を `targets` に入れない。基準値が未計測なら、`baselines` の `value` に「未計測」と理由を入れる（配列を空にしない）。

### 公開名

| 名前 | 使う場面 |
|---|---|
| `IssueMetadata`・`RunRecord`・`Evaluation` | ブロックのモデル。値を組み立てて `write_metadata`・`compose_comment` に渡す |
| `BaseRef`・`Estimate`・`Baseline`・`Target`・`Discovery`・`Undetermined`・`IssueRef`・`TaskTime`・`Stop`・`EvaluationResult` | モデルの部品 |
| `FormatError` | 書き込み・入力の拒否。`problems` に理由をすべて持つ |
| `Extracted` | `extract_block` の結果（`status`・`kind`・`version`・`value`・`reason`・`line`・`end_line`） |
| `render_block` | ブロックの文字列を描画する（読み戻して確かめる） |
| `extract_block` | 本文・コメントから、指定した種類のブロックを取り出す |
| `write_metadata` | Issue の本文に `metadata` のブロックを書き込む（既存のブロックはその位置で置き換える） |
| `compose_comment` | コメントの本文の後に `run-record`・`evaluation` のブロックを足す |
| `scan_lines`・`block_candidates` | コードブロックの内外を区別した行の走査と、ブロックの候補の行 |
| `ORIGINAL_INFO`・`MANAGED_ORIGINAL_INFO`・`wrap_original`・`unwrap_original` | 整形前の本文の保存と取り出し（3 章）。`wrap_original` と `unwrap_original` の `info` は keyword-only で、省略すると旧形式 |
| `LabelDefinition`・`SectionRule`・`Rules`・`load_rules` | 対象を検証し、この文書の表から規則を読む |
| `missing_labels` | 既存のラベルの一覧と比べて、無い定義を返す |
| `Problem`・`CheckResult`・`check_issue` | 本文・ラベル・タイトルの検査 |
| `KINDS` | 種類と版に対応するモデル |
| `BODY_LIMIT` | 本文の上限（65,536 文字） |
| `REQUIRED_FAMILIES` | 必須の系統（`type`・`area`・`priority`・`size`・`source`） |
| `ROOT` | リポジトリの root |
| `main` | CLI の入口 |

### スキルの helper からの読み込み方

スキルの helper は、自分のファイルの位置から辿って `importlib.util.spec_from_file_location` で読む（前例: `upsert_pr_comment.py` が `review_records.py` を読む）。`sys.modules` に登録してから実行する。`parents[N]` の `N` は、helper のファイルから見たリポジトリの root までの深さで決める（`.agents/skills/<スキル名>/scripts/<helper>.py` なら 4）。

```python
import importlib.util
import sys
from pathlib import Path

ISSUE_FORMAT = Path(__file__).resolve().parents[4] / ".agents/scripts/issue_format.py"


def _load_issue_format():
    spec = importlib.util.spec_from_file_location("issue_format", ISSUE_FORMAT)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ISSUE_FORMAT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["issue_format"] = module
    spec.loader.exec_module(module)
    return module


issue_format = _load_issue_format()
rules = issue_format.load_rules("usaturn/create-reso-world")
```

## 10. 形式の版を変えるとき

- 変更を扱う Issue を起票し、この文書と `issue_format.py` を同じ PR で変える
- 既存のブロックが新しいモデルでも検査に通り、意味が変わらない変更（既定値のあるキーの追加など）は、版を変えない
- それ以外は版を上げる（`v2`）。古い版のモデルは残し、古い版のブロックも読めるようにする（抽出 helper が古い Issue を壊れたと扱わないため）。知らない版は `unknown_version` として返す（成功にしない）
- ラベルの名前を変えるときは、既存の Issue の付け替えの手順も同じ Issue で決める
