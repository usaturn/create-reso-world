# Issue #241: finalize.py が Spec の commit の push 直後の比較の失敗を待てば進む停止にし、gh の応答の要点を残す

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/241（親 Issue・ボード・先行 Issue・コメントは無い。関連: PR #240（この事象）、#196・PR #203（`wait_for: head`）、#206・#207（`finalize.py` の照合と `merged` の 3 値））
- 状態: completed（PR #256 の review-fix-planning の結論 2 で、マージの前に completed にした。内容の承認（`approved`）ではない）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue241-finalize-compare-wait.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-241-finalize-compare-wait`（branch `fix/issue-241-finalize-compare-wait`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-25（JST）、利用者が次のとおり指示した

  ```text
  /issue-to-pr #241 --merge
  ```

  issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #241`）まで行い、`--merge` により PR 修正ループ（pr-review-fix-loop）を回して、修正不要と確かめられたらループの `finalize.py` がマージと関連 Issue の更新を行う。下の判断はどれも、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- ループのオプション（`loop.py check-options` の出力）: `max_cycles = 3`・`assign = {}`・`template = .devcontainer/agent-runner.toml`・`config = null`（どれも既定の適用。利用者はループ用のオプションを指定していない）。割り当ては、レビュー（`inspect`）が `pi-gpt`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正（`implement`）が `claude-opus`、自己レビュー（`self-review`）・修正の確認（`fix-check`）が `self`（雛形と個人設定 `~/.config/agent-runner/config.toml` の適用）。いずれも `fallback` なし
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の `workflows.issue` の既定の適用。利用者の指定ではない）
- 基準: `origin/main` の `bdbe02b`

## 意図

create-reso-world の PR の結論 2 では、Spec の commit（S）を push した直後に `finalize.py --spec-commit S` を実行する。PR #240 では、GitHub が PR の head を S と返した後でも、比較の API（`gh api repos/<repo>/compare/<reviewed_head>...S`）だけが 1 回失敗し、helper は `wait_for` の無い `external:` で止まった。手順（review-fix-planning の結論 2 の手順 7）どおりなら結論 3 になり、修正不要と確かめた PR がマージされずにループも `stopped` で終わる。少し後に同じ入力で再実行するとマージできた。

この変更で、PR の head が S になった後の比較の API の失敗を待てば進む停止（`wait_for: compare`）にし、`gh` の失敗で止まったときに `gh` の標準エラーの要点を結果に残す。あわせて、review-fix-planning の結論 2 の手順 7 と pr-review-fix-loop の「最終化の停止」の書き方の食い違いをなくす。取り消せない操作（マージ）は今までどおり起きない側に倒す。

## 確認した事実（2026-10-25 JST、`bdbe02b`）

- `finalize.py`（`.agents/skills/review-fix-planning/scripts/finalize.py`）
  - `check_spec_change`（`:219-226`）は `poster.run_gh` で比較の API を呼び、`poster.load_json` で読む。`gh` の失敗も JSON の不正も `poster.CommentError` になる。応答の形が違えば `environment:` の `Stop`
  - 呼ぶのは `check_view`（`:308-338`）の後（`:432-434`）。`check_view` は PR の head が S でなければ止まる（head がまだ `reviewed_head` で open なら `wait_for: head`）ので、比較を呼ぶ時点で GitHub は PR の head を S と返している
  - `finalize` の `except poster.CommentError`（`:513-514`）は `stop_reason` を `external: {step} の取得・検査・書込みに失敗した` にし、`CommentError` の内容（`run_gh` が入れた `gh` の標準エラー、無ければ標準出力。`upsert_pr_comment.py:217-219`）を捨てる
  - `check_merge_parent`（`:276-281`）も、commit の取得の `CommentError` を捨てて「読めない」にする
  - `Stop`（`:66-89`）は `wait_for`・`base_moved`・`merge_parent` を持ち、`finalize` が結果に写す（`:503-510`）
- 再現（このセッション、偽の gh だけ。`/workspaces/reso-world/tmp/agents/issue-241.ftivqlbo/repro-before.log`）: `spec_gh()` で `compare_fails = True` にすると `{"outcome": "stopped", "merged": false, ..., "stop_reason": "external: Spec commit comparison の取得・検査・書込みに失敗した"}`（`wait_for` なし、偽の gh の標準エラー `fake failure` は残らない）。`compare_fails` を戻した同じ入力の再実行は `no_fix_needed`・`merged: true`
- 実際の `gh api` の失敗の標準エラー（読み取りだけ）: `gh api repos/usaturn/create-reso-world/compare/0000…...bdbe02b` は終了コード 1、標準エラー `gh: Not Found (HTTP 404)`
- `stop_reason` の行き先
  - 結論 3 の状況コメントの判断の記録（review-fix-planning の SKILL.md:273）。記録の検査（`.agents/scripts/review_records.py:174-191`・`:613-618`）は、`stop_reason` に制御文字・`<!--`・`-->` を禁じ、`permission:`・`environment:`・`external:` で始まることを求める。usaturn/resoloop の PR は public
  - ループは finalize の `stop_reason` を run の結果に写し（`loop.py:1555`）、finalize の結果全体を `planning.finalize.result` にそのまま残す（`FinalizePart.result: dict[str, Any]`、`loop.py:370-373`）。`_read_finalize`（`loop.py:1401-1418`）は `outcome`・`merged`・`issues`・`spec_commit` だけを検査し、ほかのキーを拒否しない
- `wait_for` の値を読むコードは `finalize.py` だけ（ループの `loop.py` は読まない）。手順書は `references/execution.md` 3.3 節（`:156`）と 3.4 節（`:167`）が値ごとの待ち方を書く
- 手順書の食い違い
  - review-fix-planning の SKILL.md:263（結論 2 の手順 7）: `wait_for` は待って同じ入力で再実行、`base_moved` は検証し直して再実行、`merge_parent` は補足を投稿して結論 3、それ以外の `stopped` は結論 3
  - pr-review-fix-loop の SKILL.md:68（サイクルの 3）: `wait_for`・`base_moved` の再実行は手順 7 のとおり計画の中で行う
  - pr-review-fix-loop の SKILL.md:109（「止まったとき」の「最終化の停止」）: 「finalize.py が `stopped`（mergeable の計算中、一時的な API の失敗など）で終わり、同じ HEAD のまま原因が解消したら、`cycle-end` に渡した `--round-dir` の記録・本文・検証記録で finalize.py を再実行する」。計画の中の再実行か、run が終わった後の回復かを書いていない。mergeable の計算中は `wait_for` で、手順 7 が計画の中で扱う。PR #240 は、これに従ってループの中で 1 回だけ再実行した
- テスト: `test_finalize.py` は 65 件。比較の失敗は `test_spec_commit_compare_request_failure_is_external_and_does_not_merge`（`:666-671`）が `external:` と書き込みなしを確かめる。偽の gh（`:102-231`）は失敗の標準エラーを常に `fake failure` で返す

## 設計

### 1. 比較の API の失敗を `wait_for: compare` にする（`finalize.py`）

- `check_spec_change` で、`run_gh` の失敗（`gh` の非 0 の終了）だけを捕まえ、`Stop(..., wait_for="compare")` を上げる。`stop_reason` は `external:` で始まり、GitHub の比較を取得できなかったことと、push の直後は比較が遅れることがあることを書く
- JSON の不正は今までどおり `CommentError`（`external:`、待たない）。応答の形の違いは今までどおり `environment:`（待たない）
- PR が open でもマージ済みでも同じに扱う。どちらも、比較を呼ぶ前に PR の head が S であることを `check_view` が確かめている
- 再実行は今までどおり最初から照合し直す。比較が成功すれば、マージ（open のとき）または関連 Issue の更新（マージ済みのとき）に進む
- `Stop` の docstring に `compare` を足す

### 2. `gh` の失敗の要点を結果の `error_detail` に残す（`finalize.py`）

- `failure_detail(error)` を足す。`CommentError` の文字列を、空白・改行を 1 つの空白にまとめ、印字できない文字を除き、GitHub のトークンの形（`ghp_`・`gho_`・`ghu_`・`ghs_`・`ghr_`・`github_pat_` で始まる英数字と `_` の並び）を `[REDACTED]` に置き換え、500 文字までに切る
- `Stop` に `detail` を足し、`finalize` が結果の `error_detail` に写す。`except poster.CommentError` の経路も `error_detail` を入れる
- `error_detail` を入れる停止: 比較の `wait_for: compare`、`except poster.CommentError` の `external:`、`check_merge_parent` の commit の取得の失敗（`merge_parent` 付きの停止）
- `stop_reason` は今の決まった文のまま（`gh` の標準エラーを入れない）
- 入れない停止: `round_target` の記録の照合の失敗（今も判断 ID だけを残す）、入力・コマンドの `environment:`（`OSError`・`ValueError`）

### 3. 手順書

- `references/execution.md`
  - 3.3 節: `--spec-commit` で、PR の head が S になった後に比較の API の呼び出しが失敗したら `wait_for: compare` で止まること。応答の形が違えば `environment:` で待たないこと
  - 3.2 節の手順 4: 比較の確認に、取得できなければ `wait_for: compare` を添える（`wait_for: head` と並べる）
  - 3.4 節: `wait_for` の待ち方に `compare` を足す（`mergeable`・`head` と同じく、少し間を置いて同じ入力で再実行する）。`error_detail`（`gh` の失敗で止まったときの要点。1 行・500 文字まで・トークンの形を伏せる）は利用者への報告に書き、PR のコメント（判断の記録の `stop_reason`・状況の本文・補足）には写さないこと（ネットワークの失敗では環境の情報が入りうる）
- review-fix-planning の SKILL.md の結論 2 の手順 7: 結果に `error_detail` があれば利用者への報告に書き、PR のコメントには写さないこと
- pr-review-fix-loop の SKILL.md
  - 「最終化の停止」: 計画の中の finalize.py の再実行と止まった後の結論は、review-fix-planning の結論 2 の手順 7 のとおりにすると書く（手順 7 の分岐を写して要約しない）。`base_moved` の再実行は計画の中の文に置く。run が `stopped` で終わった後の再実行（原因が解消したときの `--round-dir` での再実行、`merged: null`・`merge_parent` の読めないときの再実行、merge commit での再検証の後の再実行）は、どれも利用者の指示で行うと書く。例示の「mergeable の計算中」は `wait_for` なので外す。`merged`・`merge_parent` の扱いの中身は変えない
  - 「最終報告」: finalize の結果に `error_detail` があれば書く

### 4. テスト

- 偽の gh に、失敗の標準エラーを差し替える設定（`stderr`）を足す
- `test_spec_commit_compare_request_failure_is_external_and_does_not_merge` を、Issue の再現の順に置き換える: PR の head が S で比較だけが失敗 → `stopped`・`merged: false`・`wait_for: compare`・書き込みなし・`error_detail` に偽の gh の標準エラー → 比較が戻った同じ入力の再実行で `no_fix_needed`（書き込みはマージと Issue の close だけ）
- 1 件足す: `gh` の失敗（認証済みの login の取得）の標準エラーにトークンの形の文字列（実行時に組み立てる）を含めると、`error_detail` に標準エラーの要点が残り、トークンは結果のどこにも無く、`stop_reason` に標準エラーが入らない

### 5. 変えないもの

- 照合の順序と、ほかの停止（`wait_for: head`・`mergeable`・`ci`、`base_moved`、`merge_parent`）の条件
- `stop_reason` の文（比較の新しい停止を除く）と、判断の記録の形
- `loop.py`（`wait_for` を読まず、finalize の結果をそのまま残す）
- 投稿 helper（`upsert_pr_comment.py`）
- 結論 2 の手順 7 の「それ以外の `stopped` は結論 3」

## 受け入れ条件

1. PR の head が S になった後に比較の API の呼び出しが失敗すると、`stopped`・`wait_for: compare`・`merged: false` で、投稿もマージもしない。比較が戻った同じ入力の再実行は S をマージして `no_fix_needed` になる（Issue の対応の候補 1）
2. 比較の応答の形が違うときは、今までどおり `environment:` で待たずに止まる
3. `gh` の失敗で止まったとき、結果の `error_detail` に `gh` の標準エラーの要点が残る。`error_detail` は 1 行・500 文字までで、GitHub のトークンの形の文字列を含まない。`stop_reason` に `gh` の標準エラーは入らない（対応の候補 2）
4. review-fix-planning の結論 2 の手順 7、`references/execution.md` 3.3・3.4 節、pr-review-fix-loop の「最終化の停止」が、新しい停止と `error_detail` を書き、計画の中の再実行と run の後の回復を食い違わずに書く（対応の候補 3）
5. テストは偽の gh で実行して確かめ、AGENTS.md の「テストの採用基準」の S に当たるものだけを足す。文書の文言を照合するテストと GitHub Actions は足さない。README の「テスト」の入口（ワールドの行を除く）で、この変更による失敗が無い

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-241-1 比較の API の失敗は新しい値 `wait_for: compare` にする**
  - 選択: PR の head が S になった後の比較の API の失敗を、`wait_for: compare` の停止にする
  - 別案: (a) `wait_for: head` を使う、(b) helper の中で間を置いて比較を再試行する、(c) 停止はそのままにして手順書だけで再実行を認める
  - 理由: (a) の `head` は「push した S が PR の head に反映される前」で、この停止（head は S と確かめ済み）と意味が違い、報告を読み違える。`wait_for` の値を読むコードは無く、手順書は値ごとに待ち方を書いているので、値を 1 つ足すだけで済む。(b) は helper に待ち時間と回数を持ち込み、待つ期限の判断（monitoring-long-tasks）を司令塔から helper に移す。(c) は Issue の食い違いを残し、ループが手順 7 どおりなら `stopped` で終わる
- **D-241-2 待つのは `gh` の失敗だけで、HTTP の状態で分けない**
  - 選択: `run_gh` の失敗（非 0 の終了）だけを待てば進む停止にする。JSON の不正と応答の形の違いは待たない。PR が open でもマージ済みでも同じにする
  - 別案: 標準エラーの HTTP の状態（404 など）で、待つかを分ける
  - 理由: 比較を呼ぶ前に、`gh pr view` が成功し、PR の head が S と確かめているので、権限や認証の失敗はここではまず起きない。`gh` の標準エラーの形は API の仕様ではなく、照合に使うと壊れやすい。待っても解消しない失敗は、手順 7 の期限で結論 3 になる（マージは起きない）
- **D-241-3 `gh` の応答の要点は `stop_reason` ではなく、結果の `error_detail` に残す**
  - 選択: 結果に `error_detail` を足す。`stop_reason` は helper の決まった文のまま
  - 別案: Issue の対応の候補 2 の文言どおり、`stop_reason` に足す
  - `error_detail` を書く先は利用者への報告だけにし、PR のコメント（判断の記録・状況の本文・補足）には写さない。最初の版は「停止の報告に書く」だけで、公開の状況の本文に載せてよいかが曖昧だった（最後のブランチ全体のレビューの Minor 3。public の PR に環境の情報が載りうるので Important として扱った）
  - 理由: `stop_reason` は結論 3 の判断の記録に写され、PR のコメントに載る（usaturn/resoloop の PR は public）。記録の検査は `stop_reason` に制御文字・`<!--`・`-->` を禁じるので、`gh` の出力をそのまま足すと投稿が拒否されうる。結果ファイルとループの `planning.finalize.result` には `error_detail` がそのまま残るので、一時的な遅れか本当の失敗かを後から区別できる。Issue の目的（`gh` の応答を残す）は満たす
- **D-241-4 `error_detail` は 1 行・500 文字にまとめ、トークンの形を伏せる**
  - 選択: 空白をまとめ、印字できない文字を除き、GitHub のトークンの形を `[REDACTED]` に置き換えてから、500 文字に切る
  - 別案: (a) 伏せずにそのまま残す、(b) agent-runner と同じく、名前が資格情報を示す環境変数の値を伏せる
  - 理由: `gh` は失敗の出力にトークンを出さない（確かめた例: `gh: Not Found (HTTP 404)`）が、結果はループの記録や報告に写されるので、念のため伏せる。トークンの形で伏せると、環境変数・keyring のどちらから読んだトークンも伏せられる。`finalize.py` は単独のスクリプトとして読み込まれ、`tools.agent_runner` を import できない
- **D-241-5 `error_detail` を入れるのは `gh` の失敗の 3 か所**
  - 選択: 比較の `wait_for: compare`、`except poster.CommentError`、`check_merge_parent` の commit の取得の失敗
  - 別案: 比較の停止だけにする
  - 理由: Issue の「`gh` の応答が残らない」は、`except poster.CommentError` の経路すべてと、commit の取得の失敗を捨てている `check_merge_parent` にも当てはまる。どれも同じ関数で作れ、`stop_reason` は変わらない。`round_target` は記録の照合の失敗で、今も判断 ID だけを残している（問題の文にマーカーが入りうる）ので入れない
- **D-241-6 計画の中の再実行は手順 7 だけにし、run の後の回復は利用者の指示で行う**
  - 選択: pr-review-fix-loop の「最終化の停止」を、計画の中の再実行は手順 7 のとおり（`wait_for`・`base_moved`）、`--round-dir` での再実行は run が `stopped` で終わった後の回復で利用者の指示で行う、と書き直す。手順 7 の「それ以外の `stopped` は結論 3」は変えない
  - 別案: (a) 手順 7 に、`gh` の失敗の `external:` は原因の解消を読み取りで確かめて 1 回だけ再実行してよい、を足す、(b) 「最終化の停止」をそのままにする
  - 最初の版は「最終化の停止」の括弧書きで手順 7 の分岐を要約し、CI の失敗の結論 1 への切り替えが抜けていた。また「利用者の指示で」が、後に続く `merged: null`・`merge_parent` の再実行にかかるかが曖昧だった。最後のブランチ全体のレビュー（Minor 1・2。受け入れ条件 4 に関わるので Important として扱った）で分かったので、要約をやめ、run の後の再実行のすべてにかかるように直した
  - 理由: PR #240 の事象は D-241-1 で `wait_for` になり、手順 7 の待ち方で扱える。(a) は、あらゆる `external:` の停止に「原因が解消した」の判断を求め、何を確かめれば足りるかを停止ごとに決めることになる。run が終わるとロックは解放され、run の結果も確定するので、司令塔が自分の判断でループの外から再実行すると、別の run との競合や、run の記録と PR の状態の食い違いが起きうる。`merge_parent` の完了（「利用者の指示で」）とも同じ扱いになる。(b) は Issue の食い違いを残す
- **D-241-7 テストは 2 件（置き換え 1・追加 1）**
  - 選択: 設計 4 のとおり。比較の失敗の既存のテストを、Issue の再現の操作の順（失敗 → 待つ → 戻る → 再実行でマージ）に置き換え、トークンを伏せることを 1 件で確かめる。文書の変更は、文言を照合するテストを作らず、`git diff` の確認と最後のブランチ全体のレビューで確かめる
  - 別案: `failure_detail` を単体で直接テストする、`check_merge_parent` の経路の `error_detail` もテストする
  - 理由: 前者は実際に起きた気付けない不具合（修正不要の PR がマージされない）の再発防止、後者は秘密情報の漏れの防止で、どちらも AGENTS.md の S に当たる。伏せるテストは標準エラーの要点が残ることも確かめ、何でも伏せる実装では通らない。`finalize` を通して確かめると、結果のキーに写る経路まで確かめられる。`check_merge_parent` の経路は同じ関数と同じ写し方なので、代表の 1 件で足りる（D）
- **D-241-8 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の 2 Task を順に実装する
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `implement_task.py check` の `self` が true。Task は 2 つで、どちらも同じ停止と `error_detail` の仕様に依存し、Task 2（手順書）は Task 1 の実装の挙動をそのまま書く。子に渡す文脈がこの Spec のほぼ全部になる

## 既知の制限

- 比較の API が待っても戻らない（権限の変更、GitHub の長い障害など）ときは、手順 7 の期限を過ぎてから結論 3 になる。それまでの待ち時間は短くならない
- `error_detail` は `gh` の出力の先頭 500 文字で、長い出力（`GH_DEBUG` を付けた実行など）は途中で切れる

## PR #256 レビュー修正サイクル 1

- 対象 HEAD: `e16206d5792b2dc95107a154684a63494b660d2d`。実行許可は利用者の `/issue-to-pr #241 --merge` で、PR 修正ループ（run `6fa97d6738c84d96906839e9685f9502`）の中で review-fix-planning の完遂として行った。planner は `claude-opus-5-5`（claude-code）。サイクルは 1（PR に前の記録は無い）
- 4 レビュアーとも受け付けられ（却下 0・残した資源 0）、現行 HEAD を再レビューした。指摘（active findings・Unverified candidates）はどれも 0 件

| レビューファイル | モデル / ランタイム | レビュー HEAD | 再実行 | 推奨 |
| --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | `gpt-6.1-sol` / pi | `e16206d5792b` | はい | Approve |
| `SWE-2-Max.md` | `SWE-2 Max` / devin | `e16206d5792b` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | `deepseek/deepseek-v4.1-flash` / pi | `e16206d5792b` | はい | Approve |
| `Grok-4.7.md` | `Grok 4.7` / cursor | `e16206d5792b` | はい | Approve |

- 確認済みの一覧: `reviews/usaturn/create-reso-world/#256-fix-issue-241-finalize-compare-wait/verified/e16206d5792b.json`（review-verify の mode cycle。候補 0 件、confirmed・not_reproduced・unverified とも 0 件、`coverage.remaining` なし）。工程の記録は同じ場所の `e16206d5792b.planning.json`（状況コメントの投稿の後に作る）
- 分類: 解消済み 0 件、対応する 0 件、対応しない 0 件。対応する項目が無いので、守る条件と影響経路の表と設計の見直しは無い
- レビュアーが宣言していた未実施の範囲は、次のとおり閉じた
  - 本物の `gh` と GitHub の比較の API: 変更した分岐は runner が返す終了コードと標準エラーだけで決まる。偽の gh で失敗・成功の両側、マージ済み、JSON の不正、形の違いを 4 レビュアーが実行した。push の直後の遅れの事実は Issue #241 の記録（PR #240）にある
  - リポジトリ全体の一括検証: 下の検証で実行した
  - ruff（実行環境に無い）: `uvx ruff format --line-length 120 --check` と `uvx ruff check --line-length 120` を `finalize.py`・`test_finalize.py` に実行し、format は差分なし、check は base にもある `read_object` の TRY004 だけだった。両ファイルは `4e4f152` から `e16206d` まで変わっていない
- 結論: 2（修正不要としてマージする）。修正が無いので `run_roles.py` は実行していない（割り当ては implement `claude-opus`、self-review・fix-check `self` だが、使っていない）。自己レビューは 0 回
- 検証（head だけ）: issue-to-pr が HEAD `e16206d` で記録した検証。`bash .devcontainer/run-tests.bash` 0（23 PASS）、`bash scripts/check-layout.sh` 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` 0（1225 passed）。検証の前後で作業ツリーは clean。ログは `/workspaces/reso-world/tmp/agents/issue-241.ftivqlbo/verify-2/`。このときの base は `bdbe02b1bfdc8e884dfb836fc1083cd0cf3ae858`（HEAD の祖先）
- base の前進（このサイクルのやり直し 1 回目）: 状況コメントの投稿の直前（2026-10-24T16:59Z）に、main が `6b6fd9aedb11d6dcfea6e91f3ac1d50bee9feaf8`（PR #258 のマージ。agent_runner の devin 関連で、この PR と同じファイルを変えない）に進んでいた。投稿・push をせずに、`/tmp` の `mktemp` の隔離 worktree で head に `6b6fd9a` を merge した一時的なツリー（`8992caa`。競合なし、push しない）を作り、同じ 3 つを実行した: `bash .devcontainer/run-tests.bash` 0（23 PASS）、`bash scripts/check-layout.sh` 0、`uv run pytest tests/skills .agents/skills .agents/scripts tools` 0（1224 passed）。検証の前後で作業ツリーは clean。ログは `/workspaces/reso-world/tmp/agents/pr-256-review-fix.bx94e3uz/verify-merge-1/`。検証の後に隔離 worktree を消した。検証の記録の `base` は `6b6fd9a`、`commands` はこの実行
- この Spec の commit の後、PR の head がまだ `e16206d` のうちに記録付きの状況コメントを投稿し、base を確かめ直してから検査付きの push をして、`finalize.py --spec-commit` でマージする
