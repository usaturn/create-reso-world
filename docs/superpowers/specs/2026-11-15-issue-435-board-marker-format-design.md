# Issue #435: ボードマーカーの形式を issue-authoring の整形 helper と揃える（設計）

## 管理・実行許可

- 状態: `completed`（PR #449 のレビュー修正ループのサイクル 1 で修正不要と判定。内容の承認（`approved`）は記録しない）
- 対象: usaturn/create-reso-world#435（https://github.com/usaturn/create-reso-world/issues/435）
- 利用者の指示（2026-11-15）: `/issue-to-pr #435 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review claude-code_sonnet_xhigh --implement claude-code_sonnet_xhigh --assign implement=claude-code_sonnet_xhigh --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh`
- 許可された範囲: issue-to-pr の委任により、通常の設計判断を推奨案で決め、検証・commit・push・PR 作成まで進める。`--merge` により、PR 修正ループ（pr-review-fix-loop）で修正不要と確かめられたときだけ、ループの `finalize.py` がマージする。これは実行許可であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` `refs/heads/main` `273ace19215430fa05042a512d63dc19e4e3a058`

## 背景

`planning-parallel-issues` のボード（親 Issue）の本文を `issue-authoring` の整形（`reshape_issue.py prepare`）にかけると、#349 のボードは終了コード 2・`an unknown planning-parallel-issues marker is present on line 64` で止まる。#349 の本文は次の形を持つ。

```text
## Publication ledger

<!-- planning-parallel-issues board: agent-workspace-port-2026-11-08 -->
<!-- board-ledger:start -->
…（ledger の表・説明文。非 ASCII を含む）…
<!-- board-ledger:end -->
```

helper が認識するのは `<!-- planning-parallel-issues:<名前>:start -->` 〜 `:end -->`（`<名前>` は `board:<key>` か `ledger`）と、子の先頭行の `<!-- planning-parallel-issues board:<b> child:<c> parent:<N> -->` だけである。マーカーの構文は `.agents/issue-format.md` の「ほかのスキルの管理対象の節」に 1 行で書かれているが、`planning-parallel-issues` の references（`issue-board.md`・`github-operations.md`）は「managed parent-body section」とだけ書き、構文を示さない。このため coordinator が独自の形式を書いた。

マーカーを解釈するコードは 3 か所ある。

| 場所 | 用途 | 現状 |
| --- | --- | --- |
| `.agents/skills/issue-authoring/scripts/reshape_issue.py` の `_managed_ranges` | 整形で管理対象をバイト単位で保つ | `:board:` 形式と子マーカーだけ。ほかの `planning-parallel-issues` 行は拒否 |
| `.agents/scripts/issue_format.py` の `_excluded_numbers` | 節の検査で管理対象を読まない | `:board:` 形式の範囲だけを除く |
| `.agents/skills/issue-authoring/scripts/publish_issue.py` の `KNOWN_COMMENT` | 隠れたコメントの警告から除く | `planning-parallel-issues:`・`planning-parallel-issues board:` を除く。`<!-- board-ledger:… -->` は警告になる |

GitHub 上で `board-ledger` を本文に持つ create-reso-world の Issue は #349 だけである（2026-11-15 に `search/issues` で確認。ほかの検索結果はコメントでの言及）。

## 目的・目標外

- 目的: `board-ledger` 形式（#349 の形）のボードを整形でき、管理対象（ボード・ledger・子マーカー）がバイト単位で保たれる。マーカーの構文の定義元を 1 つの文書にし、両スキルの references・helper・テストを一致させる
- 目標外: #349 の本文の更新（この修正の後に別途行う）、既存ボードの一括移行、ledger の値・子・依存関係の変更、archive 形式（`issue-format-original-managed-v1`）の変更
- 失敗とみなすこと（anti-goal）: 本当に未知・破損したマーカーを通す、任意の HTML コメントを管理対象として扱う、管理対象のバイト列を変える、`:board:` 形式のボードの整形が退行する

## 決定記録

### 用語

マーカーの 2 つの形を、archive の「旧形式」「新形式」（`issue-format-original`・`issue-format-original-managed-v1`）と混ざらないよう、次の名前で呼ぶ（S6）。

- **`:board:` 形式**: helper が以前から認識する `<!-- planning-parallel-issues:<名前>:start -->` 〜 `:end -->` の形
- **`board-ledger` 形式**: #349 の coordinator が書いた `<!-- planning-parallel-issues board: <key> -->` と `<!-- board-ledger:start -->` 〜 `:end -->` の形

### D1. 修正の方向

- 選択した案: (a)+(c)。helper が `board-ledger` 形式も管理対象として読み（後方互換）、マーカーの構文を `.agents/issue-format.md` に定義して、`planning-parallel-issues` の references からその節を参照する。新しく作るボードは `:board:` 形式だけを書く。helper は `board-ledger` 形式を認識するが、新しいボードに `board-ledger` 形式を書かない
- 検討した別案: (b) `planning-parallel-issues` に helper の形式を書かせ、既存ボードのマーカーを移行する。移行には #349 の本文の書き換えが要り、Issue の「対象外」（#349 の本文更新そのもの）に当たる。移行中に `board-ledger` 形式の本文を整形できない期間も残る。(c) だけ（定義を書くだけ）では #349 が整形できない
- 選択理由: 既存のボードを書き換えずに、#349 の整形を可能にできる。`board-ledger` 形式の構文を厳密に決めて読むので、未知のマーカーの拒否は弱まらない
- 委任指示: issue-to-pr の推奨案による委任（Issue の「エージェントに任せる事項」に修正方向の選択がある）

### D2. 定義元と既存ボードの保守

- 選択した案: `.agents/issue-format.md` に、`planning-parallel-issues` のマーカー構文を定義する小節を設ける（`:board:` 形式・`board-ledger` 形式・子マーカー・拒否する形）。今の「ほかのスキルの管理対象の節」の項（54 行目付近）と「節の検査で読まない範囲」の (3)（487 行目付近）は、この小節を参照する形に直す。`.agents/skills/issue-authoring/references/reshaping.md` の停止条件「未知の `planning-parallel-issues` の行」（64 行目付近）も、この小節の拒否する形を参照する。同じファイルの「`issue-board.md` の形」（21・91 行目付近）は、ボードの内容の形（`issue-board.md`）とマーカーの構文（この小節）の両方を指す形に直す（再レビュー S4）。`.agents/skills/issue-authoring/evals/reshape-validation.md` は移植元の過去の評価記録（冒頭に明記）なので書き換えない（S3）
- `:board:` 形式の構造: コードが受け付ける構造（`board:<key>` の範囲の中に `ledger` の範囲を入れる形と、`ledger` の範囲の単独）をそのまま定義する。新しいボードの推奨は、`board:<key>` の範囲の中に `ledger` の範囲を 1 つ入れる形とする（S6）。範囲の内側に置くのは key を持つ ledger の表と依存関係の端点の表（と、`issue-board.md` の開始指示を管理対象にするならその文）で、`## Publication ledger` の見出しは範囲の外に置く（範囲の中の見出しは節の検査で読まれず、整形でもバイト列のまま動かない）。推奨の例（再レビュー S4）:

  ```text
  ## Publication ledger

  <!-- planning-parallel-issues:board:<key>:start -->
  <!-- planning-parallel-issues:ledger:start -->
  | key | issue | database id | node_id | html_url | canonical parent |
  |---|---|---|---|---|---|
  | `<child-key>` | #N | … | … | … | #P |

  | child key | blocked_by key | child database id | blocker database id |
  |---|---|---|---|
  <!-- planning-parallel-issues:ledger:end -->
  <!-- planning-parallel-issues:board:<key>:end -->
  ```

- 既存ボードの保守の規則（S2）: 既存のボードは、今のマーカーの形のまま範囲の中身（ledger の表など）だけを更新する。`board-ledger` 形式から `:board:` 形式への書き換えは管理対象の変更に当たり、整形済み（archive を持つ）ボードでは archive の位置マーカーと対応しなくなり次の prepare が止まるので行わない。移行が必要なら別の依頼にする
- `planning-parallel-issues` の `references/issue-board.md` の Publication ledger の項から、この小節を参照し、新しいボードは `:board:` 形式で書くこと・既存ボードはマーカーを保つことを明記する。`github-operations.md` の ledger の記録の段落にも同じ小節への参照を 1 文足す
- 検討した別案: `planning-parallel-issues/references/issue-board.md` を定義元にする。マーカーを読む helper（`issue_format.py`）とその規則の文書が `.agents/` の共通部分にあり、スキル側に置くと共通部分がスキルの references に依存する
- 選択理由: 既に構文の 1 行がある共通の規則の文書で、両スキルから参照されている
- 委任指示: 推奨案による委任

### D3. `board-ledger` 形式の構文と管理対象の単位

- 選択した案: `board-ledger` 形式は、次の 3 種の行が、この順で、ボード行と開始の行の間に別の行を挟まずに並ぶ 1 つの範囲とする。範囲全体を 1 つの管理対象（kind `ledger`、name `legacy-ledger:<key>`）として扱う
  1. ボード行 `<!-- planning-parallel-issues board: <key> -->`（`board:` の後に半角空白 1 個、`<key>` は空白を含まない 1 文字以上。行全体が一致する）
  2. 直後の行 `<!-- board-ledger:start -->`（行全体が一致する）
  3. その後の最初の `<!-- board-ledger:end -->` の行（行全体が一致する）
- 拒否する形（終了コード 2）: ボード行の直後が `<!-- board-ledger:start -->` でない、`board-ledger:end` が無い、ボード行の無い `<!-- board-ledger:start -->`・`<!-- board-ledger:end -->`、`board-ledger` 形式の範囲の中の `planning-parallel-issues` 行（子マーカーを除く）・`board-ledger` 行、`:board:` 形式の範囲の中の `board-ledger` 形式の行。コードブロック・HTML コメントの中の行は、`:board:` 形式と同じく無視する
- 拒否の対象の行の形: `planning-parallel-issues` 行は今の `^ {0,3}<!-- planning-parallel-issues`（ボード行・子マーカー・`:board:` 形式の開始と終わりとして読めた行を除く）。`board-ledger` 行は `^ {0,3}<!-- board-ledger:` に当たる行（`board-ledger` 形式の開始と終わりとして読めた行を除く）。どちらも、コードブロック・HTML コメントの中は無視する
- 新しい制限: `planning-parallel-issues` 行の拒否は今の挙動を保つだけである。`board-ledger` 行の拒否（ボード行の無いもの、`:board:` 形式の範囲の中のもの、`board-ledger` 形式の範囲の中の入れ子）は新しい制限で、今はただの HTML コメントとして通る。`board-ledger` を本文に持つ Issue は #349 だけなので、影響は小さい（再レビュー S3）
- 範囲の中の子マーカー行: `:board:` 形式と同じく無視する（管理対象の一部としてバイト列を保ち、拒否しない）（S4）
- 任意の HTML コメント: Issue の防御範囲は「引き続き拒否する」と書くが、helper は今も任意の HTML コメントを拒否せず、管理対象にしないだけである。この Spec はその既存の挙動を保ち、「管理対象にしない」と読み替える。拒否するのは `planning-parallel-issues` 行と `board-ledger` 行の未知・破損の形だけである（S4）
- 検討した別案: ボード行と ledger の範囲を別々の管理対象にする。ボード行だけが単独で現れる形・ledger だけの形も許すことになり、構文が緩くなる。#349 では 2 つは隣り合っている
- 選択理由: 実在する形（#349）だけを、隙間なく厳密に受け入れる。name を `:board:` 形式（`board:<key>`）と分けるので、archive の位置マーカー（`ledger:legacy-ledger:<key>`）が `:board:` 形式の範囲と混ざらない
- 委任指示: 推奨案による委任

### D4. 3 か所の helper の合わせ方

- 選択した案: `reshape_issue.py` の `_managed_ranges` に `board-ledger` 形式を足す（D3）。`issue_format.py` の `_excluded_numbers` は、節の検査で `board-ledger` 形式の範囲（ボード行から `board-ledger:end` まで）も読まない。範囲の判定は D3 と同じ隣接の条件（ボード行の直後の行が `<!-- board-ledger:start -->`）を使い、`:board:` 形式と同じく、対応する終わりが無い開始は範囲にしない（拒否はしない）（S4）。`publish_issue.py` の `KNOWN_COMMENT` に `<!-- board-ledger:start -->`・`<!-- board-ledger:end -->` を足し、警告から除く
- 検討した別案: 3 か所の解釈を 1 つの関数にまとめる。`reshape_issue.py` は拒否を伴う厳密な解析で、`issue_format.py` は拒否しない除外であり、目的が違う。まとめると変更が大きくなる
- 選択理由: 定義は文書の 1 か所にし、各 helper はその節に沿って最小の変更で合わせる
- 委任指示: 推奨案による委任

### D5. テスト

- 選択した案: `.agents/skills/issue-authoring/tests/test_reshape_issue.py` に S のテストを 3 つ足す（S5・再レビュー S1）
  1. 保存: #349 の形を縮めた架空の本文（LF、非 ASCII を含む）を基本形にし、同じ本文を CRLF に変換した形も parametrize で確かめる。prepare → build が成功し、`verify_body` が ok、管理対象のバイト列が保たれ、archive から元の本文が復元される。改変した管理対象では `verify_body` が ok にならない（陽性対照と改変の検出）
  2. 子マーカー: parametrize で 2 ケース。(i) 1 行目に子マーカーを持つ子の本文（`:board:` 形式の範囲なし）で prepare → build が成功し、`verify_body` が ok、整形後も子マーカーが 1 行目に残る。(ii) `board-ledger` 形式の範囲の中に子マーカー行を含む本文で、拒否されずに範囲全体が 1 つの管理対象として保たれる（D3 の「無視する」の確認）。既存のテストには子マーカーのケースが無いので、これが子マーカーの認識の退行を確かめる（再レビュー S1）
  3. 拒否: parametrize で 3 ケース。ボード行はあるが ledger が閉じていない、ボード行の無い `board-ledger` 行、本当に未知の `planning-parallel-issues` 行（既存の拒否が `board-ledger` 形式の追加で弱まっていないことの確認）。1 の陽性対照が、何でも拒否する実装を落とす
- テストしないもの: `issue_format.py` の除外と `publish_issue.py` の警告（壊れても節の検査の問題・警告として表に出るので L）。文書の文言（F）。`:board:` 形式の範囲の退行は既存の 2 件のテストが確かめる（D）。子マーカーは上の 2 が確かめる
- 委任指示: AGENTS.md の「テストの採用基準」

### D6. 実データでの確認

- 選択した案（S1）: マージの前に、#349 の snapshot（`gh api` の読み取りだけ）で `reshape_issue.py prepare` と、`segments.json` を変えない `build` をローカルで実行し、両方の終了コード 0 と、`build` の出力の `preservation.ok` が true であることを確かめる（`build` は内部で `verify_body` を実行する）。GitHub への書き込みはしない
- `publish_issue.py draft update` → `reshape_issue.py verify` は、#349 の本文が共有書式の必須の節を持たない（`issue_format.py check` が `section_missing`）ため、編集しない本文では `draft update` が `check_failed` で止まり、実行できない。#349 での `draft update` → `verify` は、#349 の本文を共有書式に組み直すとき（Issue の対象外。この修正の後に別途行う）に行い、この Issue のマージの条件に含めない。PR 本文と Issue に、マージ後に確かめる項目として書く
- 委任指示: Issue の受け入れ条件（「動作環境: 実 GitHub へ書き込まない」）と「対象外」（#349 の本文更新）

## 受け入れ基準

- 動作環境: Dev Container・uv。テストは偽の本文・ローカルファイルだけを使い、実 GitHub へ書き込まない
- 実入力: #349 の形の本文（`## Publication ledger` の下にボード行・ledger の開始・日本語の説明文と表・ledger の終わり。実際の #349 は LF。CRLF は同じ本文の変換で確かめる）
- `board-ledger` 形式のボードで prepare が終了コード 0 で成功し、build で管理対象がバイト単位で保たれる（`preservation.ok`）。#349 の snapshot でも同じ
- `:board:` 形式のボードと子マーカーの整形が引き続き成功する（既存テストが通る）
- 防御範囲: 対象は `:board:` 形式・`board-ledger` 形式のボードマーカーと子マーカー。対象外の反例は次の 3 つに分けて扱う（再レビュー S2）
  - (a) 管理対象にしない（今の挙動どおり。拒否しない）: 任意の HTML コメント、コードの囲み（閉じていない囲みを含む）・HTML コメントの中のマーカー
  - (b) `reshape_issue.py` が拒否する（終了コード 2）: 終わりの無い開始マーカー（`:board:` 形式・`board-ledger` 形式とも）、壊れた `board-ledger` 形式の範囲、ボード行の無い `board-ledger` 行、本当に未知の `planning-parallel-issues` 行
  - (c) `issue_format.py` の節の検査の除外: 終わりの無い開始を範囲にしないだけで、拒否しない
  - Issue の「閉じていない囲み…は引き続き拒否する」は、(a) の閉じていないコードの囲みについては「管理対象にしない」と読み替える（今の helper も拒否せず、`reshaping.md` の手順で人が止まる）。終わりの無いマーカーの範囲は (b) のとおり拒否する
- マーカーの構文の定義が `.agents/issue-format.md` の 1 か所にあり、同じファイルの他の記述、`issue-authoring` の `references/reshaping.md`、`planning-parallel-issues` の references はそこを参照する
- マージ後に確かめる項目: #349 の本文を共有書式に組み直すときの `draft update` → `verify` の成功（D6）

## 残す判断（実装担当に任せる）

- 正規表現・エラーメッセージの文言、関数の分け方
- テストの本文の具体的な文字列

## レビューの記録

### 設計レビュー（1 回目）

- 担当: `--design-review pi_openai-codex_gpt6-sol_xhigh`（明示値。`fallback` なし）、`actual_agent` も同じ。`identity`: model `gpt-6.1-sol`・provider `openai-codex`・effort `xhigh`
- `review_id`: `462050a34ea848b19e6b298dc1a83a19`、reviewed の Spec SHA-256: `6f6bdcb43db929c3755c6bc0ea6e2e1662b0019cc245903ff6a4f30b64c42e17`、対象 revision `b98775b10cfd1536c9be364e82d6acad22efa057`
- 所要時間: 約 100 秒（`elapsed_seconds` 99.6）。`outside_changes`: なし。`unprotected_changes`: 他の作業が残した `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の 6 件（この run の変更ではない）
- 結果: verdict `sound`、concerns 0 件。採否の対象なし

### Spec レビュー（1 回目）

- 担当: `--spec-review claude-code_sonnet_xhigh`（明示値。`fallback` なし）、`actual_agent` も同じ。`identity`: model `claude-sonnet-5-5`・CLI 2.1.325
- `review_id`: `41e9fd131a514a03b32313a0598d3744`、reviewed の Spec SHA-256: `96ce516dc7e14f82ed40ae3ee992887723157952d8d2b0f09923d34f56098502`、対象 revision `e7188f09ce424ed490751e974100236bd20c9a4c`
- 所要時間: 約 242 秒。`outside_changes`: なし。`unprotected_changes`: 設計レビューと同じ他の作業の 6 件
- 採否: 6 件すべて採用
  - S1（important）: D6 を、#349 では prepare と変更なしの build（`preservation.ok`）までをマージ前に確かめ、`draft update` → `verify` はマージ後の項目とする形に直した
  - S2（important）: D2 に既存ボードの保守の規則（マーカーを保ち、中身だけを更新する。移行は別の依頼）を足した
  - S3（minor）: D2 に文書の修正範囲（issue-format.md の 2 か所、reshaping.md）を列挙し、過去の評価記録は書き換えないとした
  - S4（minor）: D3 に範囲の中の子マーカーの扱いと HTML コメントの読み替えを、D4 に除外の判定の条件を足した
  - S5（minor）: D5 のテストを、LF の基本形と CRLF の変換、拒否 3 ケースに直した
  - S6（minor）: 「`:board:` 形式」「`board-ledger` 形式」の名前を付け、`:board:` 形式の構造と推奨を D2 に書いた

### Spec レビュー（2 回目・再レビュー）

- 担当: 1 回目と同じ `claude-code_sonnet_xhigh`（`actual_agent` も同じ。model `claude-sonnet-5-5`・CLI 2.1.325）
- `review_id`: `12c6117260b54557bb31cb05d844628a`、reviewed の Spec SHA-256: `1bbf3d7d29d1596e4dce800478ad905d5625630f4edd7ee89c65e6a91f72b591`、対象 revision `87bd4db9fc2137851d4f05f75ab50f748652e2ba`
- 所要時間: 約 228 秒。`outside_changes`: なし。`unprotected_changes`: 1 回目と同じ他の作業の 6 件
- 採否: 4 件すべて採用
  - S1（important）: D5 に子マーカーのテスト（子の本文と、`board-ledger` 形式の範囲の中の子マーカー）を足した
  - S2（important）: 受け入れ基準の防御範囲を (a) 管理対象にしない・(b) 拒否する・(c) 節の検査の除外に分け、Issue の文言の読み替えを書いた
  - S3（minor）: D3 に拒否の対象の行の形と、`board-ledger` 行の拒否が新しい制限であることを書いた
  - S4（minor）: D2 に推奨する `:board:` 形式の例と範囲の内外を書き、`reshaping.md` の「`issue-board.md` の形」を修正範囲に加えた
- 手順の逸脱の記録: controller の置換の失敗で、2 回目の `decide` の時点の Spec には上の 4 件の実質の反映が入っておらず、記録の追記だけが入っていた（`decide` の `reflected_spec_sha256` `937b29b4fc8ba48c563f354f13d44ccd774b626cf133473361dd33434906c5aa` はこの版で、commit `335c31338aa8e87760eef8f68e222fc70221bdaa`）。`decide` はやり直せないので、記録は変えず、4 件の実質の反映を次の commit で入れた。反映後の版はレビューを受けていない

## PR のレビュー（サイクル 1）

- 対象: PR #449、HEAD `1194ba89672a20d01962c1064dfe7ad35f003cd3`、base `273ace19215430fa05042a512d63dc19e4e3a058`。planner `claude-opus-5-5`（claude-code）。loop の run `64f77d05b5c84fa49185fef0e49f71a8`
- レビュアーの構成（すべてこのサイクルで再実行・Initial・Approve）:

| レビューファイル | モデル | ランタイム | レビュー HEAD | 指摘 |
| --- | --- | --- | --- | --- |
| SWE-2-Max | SWE-2 Max | devin | `1194ba89672a` | 0 |
| deepseek-v4.1-flash | deepseek-v4.1-flash | pi | `1194ba89672a` | 1（I-1・Info） |
| gpt-6.1-sol | gpt-6.1-sol | pi | `1194ba89672a` | 1（L-1・Low） |

- 確認済みの一覧: `reviews/usaturn/create-reso-world/#449-fix-issue-435-board-marker-format/verified/1194ba89672a.json`（confirmed 2）
- 分類: 解消済み 0 / 対応する 0 / 対応しない 2
  - `deepseek-v4.1-flash#I-1@1194ba89672a`（対応しない）: `.agents/issue-format.md:122` と Spec D2 の「受け付ける構造」の列挙が helper の実際の受理範囲（board 単独・board の中の ledger 2 つ・ledger の中の board）より狭い。文書の記述だけで、記述どおりに書いたボードは受理されるので致命的でない
  - `gpt-6.1-sol#L-1@1194ba89672a`（対応しない）: ledger の中の複数行 HTML コメントに終わりのマーカーがあると `issue_format._excluded_numbers` の範囲が途中で終わる。実在のボードに無い形で、結果は `draft update` の `check_failed` での停止（管理対象は reshape が保つ）。`:board:` 形式も base から同じ規則
- 要件対応: Spec の受け入れ基準と D1〜D6 は実装で満たされ、今回の修正は無い（共有条件の統合確認は Task 3 で実施済み）
- 結論: 2（修正不要でマージ）。実行許可は issue-to-pr の `--merge`（Spec 冒頭）
- 検証（HEAD `1194ba89` 単体。base はこの HEAD の祖先で一時 merge は不要）: `bash scripts/check-layout.sh` 0、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools -q` 0（1574 passed）、`bash .devcontainer/run-tests.bash` 0（27 suites）
- 自己レビュー: 修正が無いので実施していない（`run_roles.py` は起動していない）
