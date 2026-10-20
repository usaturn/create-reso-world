# Issue #196 検証の後に base が進んだ PR を finalize.py がマージしないようにする

- 文書管理・対象: `usaturn/create-reso-world`、Issue #196（ラベル `bug`。親 Issue・依存なし。重複の #197 は統合済みで close）
- 基準 HEAD: `d29c93c1`（`origin/main`、2026-10-20）。Issue が指す `b65ef0c` から `.agents/skills/review-fix-planning/`・`.agents/skills/pr-review-fix-loop/`・`.agents/scripts/review_records.py` に変更は無い
- 状態: `completed`。実装と PR #203 のレビュー確認を完了した。内容の承認は記録しない
- 実行許可: 利用者が 2026-10-20 に `/issue-to-pr #196` と指示した。issue-to-pr の規則により、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける（マージはしない）。これは実行の許可であり、この文書の内容の承認ではない。以下の判断は、確認を取らずに決めたエージェントの判断である
- 実装の担当: `implement_task.py check` の出力は `assignment={"agents": ["self"], "fallback": []}`、`self=true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で（個人設定の `workflows.issue` はコメントアウトされている）、利用者の指定ではない
- Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue196-finalize-verified-base.md`
- レビュー後の実行許可: 利用者の 2026-10-20 の `$review-fix-planning #203` により、指摘の確認・採否・必要な修正と、修正不要の場合のマージ・関連 Issue の更新まで進める。上の issue-to-pr の実行許可とは別に記録する

## 意図

review-fix-planning の結論 2（修正不要としてマージ）は、手順 2 で base を 1 回だけ取り直し、その base を含めて検証する。`finalize.py` は検証した base を知らず、マージの直前にも base を確かめない。そのため、検証の後に別のセッションが PR をマージして base が進むと、検証していない組み合わせ（PR の head と新しい base）がそのまま `main` に入る。create-reso-world は CI を止めているので、壊れた組み合わせを自動では検出できない。2026-10-19〜20 の 2 日で 3 回起きた（#192・#191・#195）。

検証の記録に検証した base を持たせ、`finalize.py` がマージの直前（投稿する経路では投稿の前も）に base ブランチの今の先端と照合して、違えばマージせずに止める。手順には、投稿・push の直前の再確認と、止まったときに新しい base で検証し直す方法を書く。`finalize.py` が最後に確かめてから GitHub がマージを処理するまでの間の競合は残るので、既知の制限として書く。

あわせて、Issue のコメント（2026-10-20T01:29Z）が指摘した問題も扱う。Spec の commit の push の直後に GitHub がまだ前の head を返すと、`finalize.py --spec-commit` は待てば進む状態なのに待たずに止まる。同じ `check_view` と手順 7 の止まり方を変えるためである。

## 確認した事実（2026-10-20、`d29c93c1`）

- `finalize.py`
  - `check_evidence`（73-96 行）: 検証の記録のキーは `head`・`commands` だけで、どの base を含めて検証したかを持たない
  - `FIELDS`（46-56 行）: PR から base の名前も SHA も読まない
  - `check_view`（207-220 行）: head・state・draft・mergeable だけを確かめる。head が違えば `wait_for` 無しで止まる
  - `finalize`（278-377 行）: `--spec-commit` が無い経路は 332-336 行で状況を投稿し、337-342 行で PR を読み直してから、345-348 行で `gh pr merge --merge --match-head-commit` を呼ぶ。`--match-head-commit` は head だけを固定する
  - 既にマージ済みの PR（再実行で Issue の更新だけを行う経路、320-323 行）は、base を問わずに Issue の更新へ進む。マージの後の base の先端はマージの commit になる
- `SKILL.md` の結論 2: base の確認は手順 2（250 行）の 1 回だけ。手順 6（254-259 行）の投稿・push と、手順 7（262 行）の `finalize.py` の前には確かめない。手順 7 は、`wait_for` 付きの停止を待って同じ入力で再実行し、それ以外の停止を結論 3 にする
- `references/execution.md` の 3 章: 検証の記録の形は `{"head", "commands"}`（3.1 節）。`wait_for` は `ci`・`mergeable` だけ（3.4 節）
- 記録付きの投稿（`upsert_pr_comment.py` の `_check_pull_request`、293-304 行）は、PR の head が記録の `reviewed_head` と同じときだけ通る。create-reso-world の PR では、Spec の commit を push した後に状況コメントを直せない
- 記録を読む側は、マーカーの無いコメントを記録の無いコメントとして扱う（`.agents/review-records.md` の 9 章の表の「旧形式のコメント」）
- PR 修正ループ: `loop.py` の `cycle_end`（1428 行から。finalize の結果の扱いは 1502-1529 行）は、結果の `outcome`・`merged`・`issues`・`spec_commit`・`stop_reason` を読み、結果全体を `FinalizePart.result`（`dict[str, Any]`、305-308 行）に保存する。ほかのキーを拒否しない。`SKILL.md` の 24 行は PR への書き込みを状況コメントと最終化だけとし、「最終化の停止」（107 行）は `--round-dir` の同じ記録・本文・検証記録で finalize.py を再実行すると書く
- GitHub の `GET /repos/{owner}/{repo}/branches/{branch}` は `name` と `commit.sha` を返し、`branch` はスラッシュを含められる（Context7 `/websites/github_en_rest`）。`gh api repos/usaturn/create-reso-world/branches/main` は `d29c93c1…` を返し、`git ls-remote origin refs/heads/main` と一致した
- PR の `baseRefOid` は base ブランチの先端に追従しない（Issue の 2026-10-20 の観測: open の PR #194・#195 の `baseRefOid` は `8f5074a` のままで、`main` は `b65ef0c`）。今は open の PR が無く、再確認はしていない。リポジトリのコードは `baseRefOid` を使っていない
- PR #192 では、push の直後の `gh pr view --json headRefOid` が前の head を返し、数秒後に Spec の commit になった（Issue のコメント）
- PR #192 の後に、利用者のセッションはマージ commit で検証を取り直し、`補足（review-fix-planning、claude-opus-5-5）:` で始まる通常のコメントで PR に書いた（コメント 6274262468）

## 受け入れ条件

| ID | 条件 | 出典 |
| --- | --- | --- |
| A-1 | 検証の後に base が進んだ PR を `finalize.py` がマージしない。マージを呼ばずに停止理由と次の一手を返すことを、偽の `gh` のテストで確かめる。base が進んでいない場合と、新しい base との merge ツリーで検証した場合はマージする | Issue |
| A-2 | 検証の記録が、どの base を含めて検証したかを持ち、`finalize.py` がそれを base ブランチの現在の先端（PR の `baseRefOid` ではない）と照合する。既存の head・コマンドの照合を弱めない | Issue |
| A-3 | review-fix-planning の手順（`SKILL.md`・`references/execution.md`）が、再確認の時点と止まったときの再実行を述べる。PR 修正ループの最終化も同じ判定を通り、その説明と食い違わない | Issue |
| A-4 | 残る競合（最後の確認とマージの呼び出しの間）を既知の制限として文書に書く | Issue |
| A-5 | `--spec-commit` で、PR の head がまだ検証した HEAD（push の反映前）なら、待てば進む停止にする。それ以外の head は今までどおり待たずに止める | Issue のコメント（2026-10-20T01:29Z） |

## 判断（決定記録）

各項目に、選択した案・検討した別案・選択理由・委任の指示または停止の条件を書く。

### D-1 検証の記録に `base` を足す

- 選択した案: 検証の記録を `{"head", "base", "commands"}` にする。`base` は、検証したツリーが含む base の commit の完全な SHA（小文字の 16 進数 40 桁か 64 桁）である。結論 2 の手順 2 で取り直した base の先端がそれに当たる。先端が head の祖先なら head で、祖先でなければ head に先端を merge したツリーで検証し、そのコマンドを `commands` に書く。`base` が無い・完全な SHA でない記録は、GitHub に問い合わせる前に `environment:` で止める
- 検討した別案:
  1. `base` を `{"ref", "sha"}` にする
  2. `base` を省略可能にし、無ければ今までどおり照合しない
  3. merge ツリーで検証したかを表す真偽値を足す
- 選択理由: base ブランチの名前は PR から読めるので、記録には SHA だけでよい（別案 1 は同じ情報を二重に持ち、食い違いうる）。別案 2 は、古い形の記録で照合を飛ばせるので保証が弱くなる。照合に要るのは「どの base を含めて検証したか」だけなので、別案 3 は不要
- 委任の指示・停止の条件: `base` の無い古い形の記録で始めた最終化は止まる。同じセッションの中で記録を作り直して再実行する

### D-2 base の今の先端の読み方

- 選択した案: PR の `baseRefName` を読み（`FIELDS` に足す）、`gh api repos/<repo>/branches/<baseRefName>` の `commit.sha` を先端とする。`baseRefName` が空・応答の `name` が `baseRefName` と違う・`commit.sha` が完全な SHA でないときは、`external:` で止める
- 検討した別案:
  1. PR の `baseRefOid`
  2. `gh api repos/<repo>/git/ref/heads/<name>`
  3. ローカルの `git ls-remote`
- 選択理由: 別案 1 は base ブランチの先端に追従しない（Issue の観測）。別案 2 も同じ先端を返すが、Issue の推奨（branches）に合わせる。`finalize.py` は checkout を持たず、GitHub への問い合わせだけで動くので、別案 3 は今の作りに合わない。`name` を照合するのは、改名した branch のリダイレクトや、URL の中で別の意味になる名前（`#` を含むなど）の応答を、成功と見なさないためである（名前の URL の符号化はしない。名前が違えば止まる）
- 委任の指示・停止の条件: なし

### D-3 照合する時点

- 選択した案: (1) `--spec-commit` が無い経路では、状況の投稿の直前に照合する。(2) どちらの経路でも、マージの直前（PR を読み直して head・CI を確かめた後、`gh pr merge` の直前）に照合する。既にマージ済みの PR（再実行で Issue の更新だけを行う経路と、読み直したらマージ済みだった経路）では照合しない
- 検討した別案: PR を最初に読んだ直後にも照合する。マージ済みの PR でも照合する
- 選択理由: Issue の対応案 2 のとおり。(1) で、古い base の検証の状況を投稿しない。(2) を最後の確認にして、競合の幅をマージの呼び出しの直前までに狭める。最初に読んだ直後の照合は、`--spec-commit` が無い経路では (1) と重なる。ある経路では (2) までの間に行うのが比較・コメントの取得だけなので、要らない。マージの後は base の先端がマージの commit に進むので、マージ済みで照合すると、Issue の更新をやり直す再実行が必ず止まる
- 委任の指示・停止の条件: なし

### D-4 base が進んだときの止め方（`base_moved`）

- 選択した案: マージを呼ばずに `stopped` を返す。`stop_reason` は `external:` で始め、結果に `base_moved: {"ref", "verified", "current"}`（base の名前、検証の記録の `base`、今の先端）を足す。`wait_for` は付けない。終了コードは今の `stopped` と同じ 1。`stop_reason` には branch の名前を入れない（`base_moved.ref` にある）
- 検討した別案:
  1. `wait_for: base`
  2. `environment:` の停止だけにして、構造化した情報を返さない
- 選択理由: Issue の対応案 4 のとおり、base の前進は待っても解消せず、検証の記録の作り直しが要る。別案 1 は、「待って同じ入力で再実行する」という `wait_for` の意味と合わない。別案 2 では手順 7 が結論 3 にするので、2 日で 3 回起きた事象のたびにサイクルが止まる。`base_moved` があれば、司令塔は次の一手（新しい先端で検証し直す）と、検証に使う SHA を結果から得られる。branch の名前を `stop_reason` に入れないのは、停止理由が判断の記録に写されうるためである（`round_target` が問題の文を写さないのと同じ配慮）
- 委任の指示・停止の条件: なし

### D-5 Spec の commit の push の反映待ち（`wait_for: head`）

- 選択した案: `--spec-commit` のとき、最初に PR を読んだ時点で、PR が open で head がまだ検証した HEAD なら、`wait_for: head` 付きの `external:` で止める。それ以外の head のとき、またはマージ済みで head が違うときは、今までどおり待たずに止める
- 検討した別案: 手順 6 の push の後に、`headRefOid` が Spec の commit になるのを期限付きで待ってから手順 7 に進む（手順だけの変更）
- 選択理由: Issue のコメントの 2 案のうち、helper で判定すれば、手順を読み落としても止まり方が正しくなる。手順 7 は既に「`wait_for` 付きの停止は期限を決めて待ち、同じ入力で再実行する」と定めているので、手順の変更は値を足すだけで済む。マージの直前に読み直したときは、最初の時点で head が Spec の commit だったので、検証した HEAD に戻っていても待たずに止める
- 委任の指示・停止の条件: なし

### D-6 手順の再確認の時点（`SKILL.md` の結論 2）

- 選択した案:
  - 手順 2: 取り直した base の先端の SHA を検証の記録の `base` にする。head の祖先でなければ、その SHA（ref の名前ではない）を merge したツリーで検証して、そのコマンドを記録する
  - 手順 5: 本文の検証の状況に、検証したツリー（head だけか、merge したツリーか）と `base` を書く
  - 手順 6（create-reso-world の PR）: 状況コメントの投稿の直前と push の直前に base を取り直す。先端が `base` と違えば、投稿・push をせずに手順 2〜5 を新しい先端でやり直す。Spec を直し、Spec の commit を `git commit --amend` で作り直す（push の前なので書き換えてよい）。作り直した commit で、commit の後の確認からやり直す。手順 3 で結論 1 に切り替えるときは、Spec の commit を結論 3 の「書き始めた Spec の扱い」の方法で取り消す
  - 手順 7: `finalize.py` が投稿の前とマージの直前に base を照合することと、`base_moved` の扱い（D-7）を書く
- 検討した別案:
  1. 手順 6 の再確認をせず、`finalize.py` の照合だけに任せる
  2. 再確認で base が進んでいたら、Spec の commit を `reset --keep` で取り消して書き直す
- 選択理由: Issue の対応案 3 のとおり。別案 1 では、Spec を書いている間（数分）に進んだ base が、状況コメントと Spec に古いまま残る（PR #191 の事象）。別案 2 では Spec の本文が作業ツリーから消え、書き直しになる。`--amend` なら、Spec の commit は検証した HEAD の直接の子 1 つのまま（`finalize.py` の比較の条件）で、本文を直すだけで済む
- 委任の指示・停止の条件: なし

### D-7 `base_moved` で止まったときの再実行と記録

- 選択した案:
  - `base_moved.current` を head（`HEAD_SHA`）に merge したツリーで手順 2 と同じ検証を通し、検証の記録を `base: current`・`commands: この実行` で作り直してから、同じ判断の記録で `finalize.py` を再実行する
  - create-reso-world の PR（`--spec-commit`）: 状況コメントを直せないので、再実行の前に補足のコメントを `gh pr comment <PR> --repo <repo> --body-file <file>` で新しく投稿する。1 行目は `補足（review-fix-planning、<MODEL_NAME>）:` とし、状況コメントのサイクル、`verified` から `current` へ進んだこと、merge したツリーで実行したコマンドと終了コードを書く。判断の記録・マーカー（`<!--`）を含めない。状況コメントの代わりにはせず、記録付きの投稿が拒否されたときの代わりにも使わない。push 済みの Spec は直さない
  - それ以外の PR: 本文の検証の状況を新しい検証に直してから再実行する（`finalize.py` が同じサイクルのコメントを更新する）
  - 検証し直さずに検証の記録の `base` だけを書き換えることを、`SKILL.md` の合理化の表と Red flags で禁じる
- 検討した別案:
  1. 補足を `upsert_pr_comment.py` の記録なしの投稿で書く
  2. PR の本文（`gh pr edit`）に書く
  3. 補足を書かず、完了報告だけに書く
- 選択理由: 別案 1 では、記録なしの投稿は 1 エージェントに 1 件で上書きされ、`.agents/review-records.md` の「review-fix-planning は記録付きの投稿だけを使う」も変える必要がある。別案 2 では、PR の作者の説明に工程の記録が混ざる。別案 3 では、PR だけを読む人に、状況コメントの base が古いことが伝わらない（PR #191 の事象）。通常のコメントは利用者が PR #192 で書いた形と同じで、記録を読む側はマーカーの無いコメントを無視する
- 委任の指示・停止の条件: `finalize.py` は補足を投稿しない。補足は司令塔が書く

### D-8 やり直しの上限

- 選択した案: base の前進によるやり直し（手順 6 の再確認と、手順 7 の `base_moved`）は、1 サイクルで合わせて 3 回まで。超えたら結論 3（`external: 検証の間に base が進み続けた`）にする
- 検討した別案: 上限を設けない。`wait_for` と同じく期限で区切る
- 選択理由: merge ツリーの検証は 1 回で 9〜14 分かかり（Issue のコメント、PR #195）、並行するセッションが多いと終わらない。回数で区切れば数えやすい
- 委任の指示・停止の条件: 3 回は推奨案として決めた値で、利用者の指定ではない

### D-9 残る競合（既知の制限）

- 選択した案: `references/execution.md` に「3.5 既知の制限」を足す。`finalize.py` が base の先端を最後に読んでから GitHub が `gh pr merge` を処理するまでの間に別のマージが入ると、検証していない組み合わせがマージされる。GitHub のマージは base を固定できない（`--match-head-commit` は head だけを固定する）。セッションの間でマージを排他にする仕組みは無い。起きたかどうかは、マージ commit の最初の親が検証の記録の `base` と違うことで分かる
- 検討した別案: マージの後に、`finalize.py` がマージ commit の最初の親を検証の記録の `base` と照合して、結果に書く（または止める）
- 選択理由: Issue の対応案 5 は、この競合を既知の制限として書き、防ぐ仕組みを別に検討するとしている。マージの後に気付いても取り消せないので、確かめ方を書けば足りる。照合を足すと、マージ済みの PR の再実行（手でのマージを含む）の扱いも決め直す必要が出る
- 委任の指示・停止の条件: マージを排他にする仕組みは、この Issue では作らない

### D-10 PR 修正ループ

- 選択した案: `loop.py` は変えない。`pr-review-fix-loop/SKILL.md` の 3 か所を直す。24 行の PR への書き込みに補足を含める。手順 3 の計画に、`finalize.py` の `wait_for`・`base_moved` による再実行は計画の中で行ってから `cycle-end` を呼ぶと書く。「最終化の停止」に、`base_moved` では検証し直し、`--round-dir` の検証記録を作り直してから再実行すると書く
- 検討した別案: `loop.py` の `_read_finalize` で `base_moved` を検査する
- 選択理由: loop は review-fix-planning の最終化（同じ `finalize.py`）を通るので、判定は自動で同じになる。`cycle_end` は `stop_reason` を記録し、結果全体を保存するので、`base_moved` も残る。loop が結果の中身で分岐する場面は無い
- 委任の指示・停止の条件: なし

### D-11 テスト

- 選択した案: `tests/test_finalize.py` の偽の `gh` に、base ブランチの API（`repos/<repo>/branches/<name>`）の応答と、投稿の後・マージの後の先端の移動を足す。足すテストは次のとおり
  - 検証の記録の `base` が無い・短い・null なら、GitHub に問い合わせる前に止まる（既存の負例に足す）
  - 両経路で、base が進んでいればマージしない（`--spec-commit` が無い経路は投稿もしない）で `base_moved` を返す。`baseRefOid` が検証した base のままでも、先端で判定する。新しい先端で検証し直した記録なら、同じ判断の記録でマージする
  - `--spec-commit` が無い経路で、投稿の後に base が進んだらマージしない。新しい記録での再実行は、同じコメントを更新してマージする
  - 両経路で、マージの後（base の先端はマージの commit）に Issue の更新をやり直す再実行は、base を照合せずに完了する
  - base の先端を読めない（API の失敗、`name` の不一致、短い SHA、`commit` が無い、オブジェクトでない、`baseRefName` が無い・空）なら、両経路でマージせずに `external:` で止まる
  - `--spec-commit` で head がまだ検証した HEAD（open）なら `wait_for: head` で止まり、反映後の再実行はマージする。別の head のときと、マージ済みで head が違うときは待たない（既存のテストを置き換える）
- 検討した別案: 手順書の文面を照合するテスト
- 選択理由: マージを止める条件は安全の条件で、`AGENTS.md` の「テストの採用基準」の「書く」に当たる。文面の照合は「作らない型」の 1 に当たる。各負例には異常を 1 つだけ入れる
- 委任の指示・停止の条件: なし

## 対象外

- セッションの間でマージを排他にする仕組み（D-9）
- マージの後の、マージ commit の親の自動の照合（D-9）
- push の後に base が進んだとき、状況コメントの記録を直す仕組み（記録付きの投稿の条件は変えない）
- `.agents/review-records.md`・`review_records.py`・`upsert_pr_comment.py`・`loop.py` のコード
- 公開 CI の結果が古い base で出ていること（resoloop の CI の再実行の扱い）

## 要件と経路の対応（実装前の判断）

| 経路 | 判定 | 観測する結果と確かめ方 |
| --- | --- | --- |
| `finalize.py` の入力（検証の記録） | 修正する | `base` の欠落・形式の誤りで、`gh` を 1 回も呼ばずに `environment:` で止まる（A-2） |
| `--spec-commit` が無い経路の投稿の前 | 修正する | 先端が違えば投稿・マージをせずに `base_moved` を返す（A-1・A-2） |
| 両経路のマージの直前 | 修正する | 先端が違えばマージせずに `base_moved` を返す。投稿の後の前進も止める（A-1） |
| 新しい先端で検証し直した記録での再実行 | 修正する | マージする。`--spec-commit` が無い経路は同じコメントを更新する（A-1） |
| `baseRefOid` を使わないこと | 修正する | `baseRefOid` が検証した base のままでも、先端が違えば止まる（A-2） |
| マージ済みの PR の再実行 | 既に満たす（照合を入れない） | マージの後の Issue の更新のやり直しが完了する（D-3） |
| head・コマンド・CI・記録・Spec の比較の既存の照合 | 既に満たす | 既存のテストを変えずに通す（A-2）。`--spec-commit` の head のテスト 1 件だけを D-5 に合わせて置き換える |
| `--spec-commit` の push の反映待ち | 修正する | open で head が検証した HEAD なら `wait_for: head`。別の head とマージ済みは待たない（A-5） |
| `SKILL.md` の結論 2・合理化・Red flags | 修正する | 差分を読み、手順 2・5・6・7、やり直しの上限、補足の形が D-1〜D-8 と一致することを確かめる（A-3） |
| `references/execution.md` の 3 章 | 修正する | 3.1〜3.5 が `finalize.py` の実装（キー・時点・結果）と一致することを、差分とテストの対応で確かめる（A-3・A-4） |
| PR 修正ループ | 修正する（文書だけ） | `pr-review-fix-loop/SKILL.md` の 3 か所が手順 7 と食い違わないことを差分で確かめる。`loop.py` の `cycle_end` が結果の余分なキーを拒否しないことはコードで確かめた（A-3） |

## PR #203 のレビュー確認（2026-10-20、サイクル 1）

### 対象と入力

- PR: <https://github.com/usaturn/create-reso-world/pull/203>
- レビュー対象 HEAD: `3d4ab76c0b3445ad7ac5b08172b984b269e34abe`
- 差分の基準（merge-base）: `d29c93c12a817ca45cb8d0eb918a0a07615916ce`
- 最新 main: `6c2259b91e726a75f9d088e005f2bfac9d523561`
- HEAD と最新 main を merge した検証用の tree: `8e318e7f0236c3c7a74d53519d338ec56f100257`。競合なし。この merge は公開しない
- planner: `gpt-6-astra` / `codex`。実行中のセッション記録でモデル・ランタイムを確認した
- レビュー入力: `reviews/usaturn/create-reso-world/#203-fix-issue-196-finalize-verified-base/`。対応する候補 JSON・実行記録の形式、組み合わせ、本文と候補の SHA256 を照合した

| レビューファイル | モデル | ランタイム | レビュー HEAD | 今回の入力として再実行済み | 判定 | 指摘 / 未確認候補 |
| --- | --- | --- | --- | --- | --- | --- |
| `Grok-4.7.md` | `Grok 4.7` | `cursor` | `3d4ab76c0b34` | はい | Approve | 0 / 0 |
| `SWE-2-Max.md` | `SWE-2 Max` | `devin` | `3d4ab76c0b34` | はい | Approve | 0 / 0 |
| `claude-opus-5-5.md` | `claude-opus-5-5` | `claude-code` | `3d4ab76c0b34` | はい | Approve | 0 / 0 |
| `gpt-6.1-sol.md` | `gpt-6.1-sol` | `pi` | `3d4ab76c0b34` | はい | Approve | 0 / 0 |

ここでの「再実行済み」は、この HEAD を対象とした保存済みレビューを今回の入力に採用したことを指す。planner が 4 モデルを起動し直したわけではない。前のサイクルの判断記録・引き継ぐ指摘・除外したレビューファイルは無い。

### 採否と確認範囲

- 解消済み 0 件、対応する 0 件、対応しない 0 件。入力候補が無く、確認中にも PR が持ち込んだ致命的な欠陥は見つからなかった
- 結論 2（修正不要としてマージする）。既存の D-1〜D-11 を変える必要は無く、設計の見直しのきっかけに当たる項目も無い
- 変更 7 ファイルの全文と全体差分を確認した。関連する `upsert_pr_comment.py`・`review_records.py` の投稿と記録の照合、`loop.py` の `FinalizePart`・`_read_finalize`・`cycle_end` とテストも確認した
- 補助エージェント `pr203_related` は、変更された文書 5 件と関連処理・テストを独立して読み、追加の問題なしと報告した。終了を確認済み
- 実装コードの追加修正は無い。`run_roles.py` の implement・self-review・fix-check は未実施（呼び出し 0 回）。修正後の自己レビューを実施したという扱いにはしない
- 最後の base 照合から GitHub がマージを処理するまでの競合は D-9 の既知の制限として残る。PR 本文にも記載済み。PR 本文に残る過去のレビューの軽微な項目は、今回の入力候補に数えない

### 実行した検証

次の 3 コマンドを、clean な PR の HEAD と、最新 main を取り込んだ一時 worktree の両方で実行した。すべて終了コード 0 を確認した。

| コマンド | PR の HEAD | 最新 main との merge ツリー |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 33 本 PASS | 33 本 PASS |
| `bash scripts/check-layout.sh` | PASS | PASS |
| `uv run pytest tests/skills .agents/skills` | 1,454 passed | 1,491 passed |

| 条件・経路 | 現行 HEAD で確認した証拠 |
| --- | --- |
| A-1・A-2: 入力、投稿の前、マージの直前、base 前進後の再実行 | 上の pytest に含まれる `test_finalize.py` 140 件が両ツリーで成功。偽の `gh` で正常時のマージ、進んだ base の拒否、投稿後の前進の拒否、新しい検証記録での再実行、記録の不備と API 応答の異常時の停止を確認した |
| A-2: `baseRefOid` と実際のブランチの先端を区別 | テストに加え、現行 HEAD の `check_base` と `GhRunner` で本物の branches API を読み取り実行。main の現在の先端は受理し、古い `d29c93c1` は `verified`・`current` を含む `base_moved` で拒否し、`wait_for` を付けなかった |
| 既存の照合とマージ済みの再実行 | 同じテスト群で head・記録・Spec・コマンド・CI の照合を確認。マージ後に base が進んでいても、Issue 更新を再開できるテストが成功した |
| A-5: Spec の push の反映待ち | open の PR がレビュー対象 HEAD のままなら `wait_for: head`、反映後は成功、それ以外の head とマージ済みの不一致は待たずに停止するテストが成功した |
| A-3・A-4: 手順書と PR 修正ループ | 文書 5 件の全文を実装と照合した。ループの結果保存は追加キーを保持し、`base_moved` の扱い、再検証、補足コメント、既知の制限の説明と矛盾しない |
| 負例の検出力 | 既存 Plan にある `7adfb5c` の 8 種類の変異が対応するテストで失敗した実行記録を確認した。その時点と今回の HEAD で `finalize.py`・`test_finalize.py` の差分は空。今回も通常のテストを実行し、コードを変えていないため変異の実行は繰り返していない |

`git diff --check` も成功した。実 GitHub への書き込みを伴う拒否経路の再現は、Issue の受け入れ条件どおり偽の `gh` で検証している。create-reso-world の GitHub Actions は共通規約に従い確認対象外とした。未確認候補・残る調査項目は無い。

今回追加する変更はこの Spec の記録だけであり、実行して守る新しい挙動が無いためテストは追加しない。文書の差分、参照先、検証記録の JSON 形式と、Spec 1 ファイルだけの commit であることを確認して公開する。

### 最終化に使う記録と手順

- 確認済みの一覧: 上記レビューディレクトリの `verified/3d4ab76c0b34.json` と `.md`
- 工程の記録: 同じ場所の `verified/3d4ab76c0b34.planning.json`。状況コメントの ID と実測時間は最終化後に保存する
- 判断の記録は `review-records/v2`、サイクル 1、`outcome: no_fix_needed`、`decisions: []`。状況コメントには、マージ前の判断と検証結果を記録する
- 検証の記録は `head: 3d4ab76c0b3445ad7ac5b08172b984b269e34abe`、`base: 6c2259b91e726a75f9d088e005f2bfac9d523561` と、merge ツリーで成功した上の 3 コマンドを持つ
- 最終化には、この PR のレビュー・検証済み `finalize.py` を明示して使う。親 checkout の旧版は `base` を照合しないため、この PR が追加した照合を今回のマージにも適用する。resolver・状況投稿・秘密情報検査は親 checkout の helper を使う
- 状況の投稿・push の直前に base と PR の HEAD を取り直す。検証した base が変わっていれば、新しい組み合わせで検証をやり直す。検査した Spec の commit だけを push し、`finalize.py --spec-commit` でマージと closing Issue の更新を行う
- マージ後は実際の merge commit の最初の親と検証した base を照合する。この文書の commit 時点では、マージ・Issue 更新の完了はまだ記録しない

### 所要時間と片付け

- planner 着手: 07:38:18Z。入力の準備・関連処理の調査は 07:45 頃までに終了し、検証の監視と最終化の準備を続けた
- 必須検証: HEAD 側は 07:40:53Z から、merge ツリー側は 07:43 頃から並行実行。すべての終了と結果の保存は 08:06:38Z。pytest の実測はそれぞれ 1,382.45 秒、1,408.49 秒
- review-verify の確認工程: 07:39:54Z〜08:06:38Z（1,604 秒、検証の待ちを含む）。待ち時間だけの内訳は未計測。調査と検証の実時間には重複があるため、各欄の時間を足し合わせない
- 補助エージェント: 07:41:45Z〜07:45:05Z（200 秒）。文書 80 秒、関連処理・テスト 105 秒、報告 15 秒
- 検証用の一時 worktree とそのスクラッチは、すべての検証プロセスの終了後、この追記の前に削除した。既存の PR 用 worktree は再利用したため残す。セッションの記録は、状況コメント・工程の記録へ保存した後に片付ける
