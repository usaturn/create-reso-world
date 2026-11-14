# Issue #435: ボードマーカーの形式を issue-authoring の整形 helper と揃える（設計）

## 管理・実行許可

- 状態: `draft`
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
| `.agents/skills/issue-authoring/scripts/reshape_issue.py` の `_managed_ranges` | 整形で管理対象をバイト単位で保つ | 現行形式と子マーカーだけ。ほかの `planning-parallel-issues` 行は拒否 |
| `.agents/scripts/issue_format.py` の `_excluded_numbers` | 節の検査で管理対象を読まない | 現行形式の範囲だけを除く |
| `.agents/skills/issue-authoring/scripts/publish_issue.py` の `KNOWN_COMMENT` | 隠れたコメントの警告から除く | `planning-parallel-issues:`・`planning-parallel-issues board:` を除く。`<!-- board-ledger:… -->` は警告になる |

GitHub 上で `board-ledger` を本文に持つ create-reso-world の Issue は #349 だけである（2026-11-15 に `search/issues` で確認。ほかの検索結果はコメントでの言及）。

## 目的・目標外

- 目的: 既存形式（#349 の形）のボードを整形でき、管理対象（ボード・ledger・子マーカー）がバイト単位で保たれる。マーカーの構文の定義元を 1 つの文書にし、両スキルの references・helper・テストを一致させる
- 目標外: #349 の本文の更新（この修正の後に別途行う）、既存ボードの一括移行、ledger の値・子・依存関係の変更、archive 形式（`issue-format-original-managed-v1`）の変更
- 失敗とみなすこと（anti-goal）: 本当に未知・破損したマーカーを通す、任意の HTML コメントを管理対象として扱う、管理対象のバイト列を変える、現行形式のボードの整形が退行する

## 決定記録

### D1. 修正の方向

- 選択した案: (a)+(c)。helper が旧形式も管理対象として読み（後方互換）、マーカーの構文を `.agents/issue-format.md` に定義して、`planning-parallel-issues` の references からその節を参照する。新しく書くボードは現行形式だけを使い、旧形式は読み取りの互換だけにする
- 検討した別案: (b) `planning-parallel-issues` に helper の形式を書かせ、既存ボードのマーカーを移行する。移行には #349 の本文の書き換えが要り、Issue の「対象外」（#349 の本文更新そのもの）に当たる。移行中に旧形式の本文を整形できない期間も残る。(c) だけ（定義を書くだけ）では #349 が整形できない
- 選択理由: 既存のボードを書き換えずに受け入れ条件（#349 で prepare → build → verify が成功）を満たせる。旧形式の構文を厳密に決めて読むので、未知のマーカーの拒否は弱まらない
- 委任指示: issue-to-pr の推奨案による委任（Issue の「エージェントに任せる事項」に修正方向の選択がある）

### D2. 定義元

- 選択した案: `.agents/issue-format.md` の「ほかのスキルの管理対象の節」を、マーカー構文の定義の節に広げる（現行形式・旧形式・子マーカー・拒否する形）。`planning-parallel-issues` の `references/issue-board.md` の Publication ledger の項から、この節を参照し、新しいボードは現行形式で書くと明記する。`github-operations.md` は ledger の記録の手順だけを持つので、同じ節への参照を 1 行足す
- 検討した別案: `planning-parallel-issues/references/issue-board.md` を定義元にする。マーカーを読む helper（`issue_format.py`）とその規則の文書が `.agents/` の共通部分にあり、スキル側に置くと共通部分がスキルの references に依存する
- 選択理由: 既に構文の 1 行がある共通の規則の文書で、両スキルから参照されている
- 委任指示: 推奨案による委任

### D3. 旧形式の構文と管理対象の単位

- 選択した案: 旧形式は、次の 3 種の行が、この順で、間に別の行を挟まずに始まる 1 つの範囲とする。範囲全体を 1 つの管理対象（kind `ledger`、name `legacy-ledger:<key>`）として扱う
  1. ボード行 `<!-- planning-parallel-issues board: <key> -->`（`board:` の後に半角空白 1 個、`<key>` は空白を含まない 1 文字以上。行全体が一致する）
  2. 直後の行 `<!-- board-ledger:start -->`（行全体が一致する）
  3. その後の最初の `<!-- board-ledger:end -->` の行（行全体が一致する）
- 拒否する形（終了コード 2）: ボード行の直後が `<!-- board-ledger:start -->` でない、`board-ledger:end` が無い、ボード行の無い `<!-- board-ledger:start -->`・`<!-- board-ledger:end -->`、旧形式の範囲の中の `planning-parallel-issues` 行・`board-ledger` 行、現行形式の範囲の中の旧形式の行（現行の「範囲の中の未知の `planning-parallel-issues` 行」の拒否を保つ）。コードブロック・HTML コメントの中の行は、現行形式と同じく無視する
- 検討した別案: ボード行と ledger の範囲を別々の管理対象にする。ボード行だけが単独で現れる形・ledger だけの形も許すことになり、構文が緩くなる。#349 では 2 つは隣り合っている
- 選択理由: 実在する形（#349）だけを、隙間なく厳密に受け入れる。name を現行形式（`board:<key>`）と分けるので、archive の位置マーカー（`ledger:legacy-ledger:<key>`）が現行形式の範囲と混ざらない
- 委任指示: 推奨案による委任

### D4. 3 か所の helper の合わせ方

- 選択した案: `reshape_issue.py` の `_managed_ranges` に旧形式を足す（D3）。`issue_format.py` の `_excluded_numbers` は、節の検査で旧形式の範囲（ボード行から `board-ledger:end` まで）も読まない（現行形式と同じく、対応する終わりが無い開始は範囲にしない）。`publish_issue.py` の `KNOWN_COMMENT` に `<!-- board-ledger:start -->`・`<!-- board-ledger:end -->` を足し、警告から除く
- 検討した別案: 3 か所の解釈を 1 つの関数にまとめる。`reshape_issue.py` は拒否を伴う厳密な解析で、`issue_format.py` は拒否しない除外であり、目的が違う。まとめると変更が大きくなる
- 選択理由: 定義は文書の 1 か所にし、各 helper はその節に沿って最小の変更で合わせる
- 委任指示: 推奨案による委任

### D5. テスト

- 選択した案: `.agents/skills/issue-authoring/tests/test_reshape_issue.py` に S のテストを 2 件足す
  1. 旧形式のボード（#349 の形を縮めた架空の本文。CRLF・非 ASCII を含む）で prepare → build → verify が成功し、管理対象のバイト列が保たれ、archive から元の本文が復元される。改変した管理対象の verify が失敗する（陽性対照と改変の検出）
  2. 拒否の代表を parametrize で 1 件: ボード行の直後に ledger の開始が無い、閉じていない ledger、ボード行の無い ledger の開始、本当に未知の `planning-parallel-issues` 行
- テストしないもの: `issue_format.py` の除外と `publish_issue.py` の警告（壊れても節の検査の問題・警告として表に出るので L）。文書の文言（F）。現行形式の退行は既存の 2 件のテストが確かめる（D）
- 委任指示: AGENTS.md の「テストの採用基準」

### D6. 実データでの確認

- 選択した案: マージの前に、#349 の snapshot（`gh api` の読み取りだけ）で `reshape_issue.py prepare` → 編集なしの `build` → `verify` をローカルで実行し、終了コード 0 と `preservation.ok` を確かめる。GitHub への書き込みはしない
- 委任指示: Issue の受け入れ条件（「動作環境: 実 GitHub へ書き込まない」）

## 受け入れ基準

- 動作環境: Dev Container・uv。テストは偽の本文・ローカルファイルだけを使い、実 GitHub へ書き込まない
- 実入力: #349 の形の本文（`## Publication ledger` の下にボード行・ledger の開始・日本語の説明文と表・ledger の終わり。改行は LF と CRLF）
- 旧形式のボードで prepare が終了コード 0 で成功し、build・verify で管理対象がバイト単位で保たれる（`preservation.ok`）
- 現行形式のボードと子マーカーの整形が引き続き成功する（既存テストが通る）
- 防御範囲: 対象は現行形式・旧形式のボードマーカーと子マーカー。対象外の反例（任意の HTML コメント、閉じていない囲み、本当に未知の `planning-parallel-issues` 行、ボード行の無い `board-ledger` 行）は管理対象にせず、`planning-parallel-issues` 行と `board-ledger` 行は拒否する
- マーカーの構文の定義が `.agents/issue-format.md` の 1 か所にあり、`planning-parallel-issues` の references はそこを参照する

## 残す判断（実装担当に任せる）

- 正規表現・エラーメッセージの文言、関数の分け方
- テストの本文の具体的な文字列

## レビューの記録

### 設計レビュー（1 回目）

- 担当: `--design-review pi_openai-codex_gpt6-sol_xhigh`（明示値。`fallback` なし）、`actual_agent` も同じ。`identity`: model `gpt-6.1-sol`・provider `openai-codex`・effort `xhigh`
- `review_id`: `462050a34ea848b19e6b298dc1a83a19`、reviewed の Spec SHA-256: `6f6bdcb43db929c3755c6bc0ea6e2e1662b0019cc245903ff6a4f30b64c42e17`、対象 revision `b98775b10cfd1536c9be364e82d6acad22efa057`
- 所要時間: 約 100 秒（`elapsed_seconds` 99.6）。`outside_changes`: なし。`unprotected_changes`: 他の作業が残した `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の 6 件（この run の変更ではない）
- 結果: verdict `sound`、concerns 0 件。採否の対象なし
