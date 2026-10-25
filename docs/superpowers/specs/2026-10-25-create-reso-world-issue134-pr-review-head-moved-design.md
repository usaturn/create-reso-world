# Issue #134: pr-review で保存しなかった試行の再レビューと片付けを決める

- 状態: draft
- 文書管理リポジトリ: `usaturn/create-reso-world`（`docs/superpowers/`）
- 対象: `usaturn/create-reso-world` / [Issue #134](https://github.com/usaturn/create-reso-world/issues/134)
- 検証したコードの HEAD: `origin/main` `c1fdc560696ab3ce3392b07ece3089989bf25902`（2026-10-25T04:23Z ごろの着手時）
- 関連 Plan: `docs/superpowers/plans/2026-10-25-create-reso-world-issue134-pr-review-head-moved.md`
- 関連: PR #130（発生元）、#39（`inspect`・`abandon`。Spec `docs/superpowers/specs/2026-10-05-issue-39-pr-review-create-interruption-design.md`）、#153・PR #182（新しい入口 prepare・complete。Spec `docs/superpowers/specs/2026-10-18-create-reso-world-issue153-pr-review-v2-design.md`）、PR #190 のレビューで残った試行（Issue のコメント）
- 実行許可: 利用者の `/issue-to-pr #134 --merge --max-cycles 3`。通常の設計判断を推奨案で決め、実装・検証・commit・push・PR の作成と、PR 修正ループ（サイクルの上限 3）、その結論に従う `finalize.py` のマージまでを許可する。本 Spec の内容の承認（`approved`）ではない

## 目的

pr-review の新しい入口（`review_run.py` の prepare → complete）で、PR の HEAD が動くなどして保存しなかったときに、次に何をするかを決める。再レビューの可否と上限、残った試行（セッション・worktree・固定した PR の ref）の片付け、`abandon` を使える条件（スキルと helper で一致させる）、未保存の draft の扱いと最終報告の内容を、スキルと helper に書く。

## 着手時の確認

Issue の本文は PR #182 より前の手順（`create` → HEAD の照合 3 地点 → `save` → `cleanup`）で書かれている。PR #182 の後の現行の経路を確かめた。

1. HEAD の照合は 3 か所にある
   - prepare の中で、fetch した `pull/<N>/head` が解決時の head と違えば止まる（`review_target.py` の `fetch_pull_head`。worktree はまだ無い）
   - prepare の中で、worktree を作った後に API の head が解決時の head と違えば止まる（`pr_review_workspace.py` の `create_from_target`、`PR head changed after fetch`）。どちらも create の失敗で、journal は `failed`、セッションは「調査のために残す」（#39 の D-7）。`session.json` は無い
   - complete の保存ロックの中で、worktree の commit・API の head・保存先と候補の保存先のフィンガープリントを照合し、違えば保存しない（`verify_state`、`PR head changed during review`）。このときは本文の draft と候補の draft が書かれている
2. 差分は、prepare が固定した merge-base と reviewed commit から、固定した worktree で作る（`diff_command`）。旧手順の「差分取得後（2/3）」の照合に当たるものは無く、途中で PR の HEAD が動いても、読む差分は変わらない
3. 保存しなかった試行を片付ける経路が無い
   - `cleanup` は保存の成功を要求する（`require_saved_review`）
   - `abandon` は試行 ID で試行を探すが、prepare は試行 ID を内部で作り（`uuid4`）、結果に返さない
   - `abandon` は review-backup に既存レビューの写し以外があると拒否する。prepare は成功するとすぐに候補の雛形（`<model>.findings.json`）を書くので、prepare の後の試行は、レビュアーが何も書いていなくても `abandon` で消せない
   - スキルは「旧 create の inspect/abandon は互換 API」とし、新入口の失敗には使わない（SKILL.md の実行時の共通規則）
   - repo-cleanup-after-merge は version 8 のセッションを消さない（同スキルの手順 5）
   - `abandon` は `--repo` の checkout の保存ロックを取る。version 8 の保存と cleanup は親の checkout の保存ロックを取るので、親と別の checkout の試行では、保存と排他にならない
4. PR 修正ループのレビュアーへの依頼は、prepare の reviewed_head がサイクルの HEAD と違えば、レビューせずに `fail` で終えるよう指示している（`loop.py` の依頼文の 3）。`fail --state` は実行記録を `failed`（review）にするだけで、セッション（worktree・候補の雛形・固定した ref）は残る。PR #190 のレビューで残った試行（Issue のコメント）も、片付ける経路が無いまま残っている
5. ループは、レビュアーが返した HEAD がサイクルの HEAD と違う成果を受け付けない（`rejected_stage: head`）。サイクルの途中で PR の HEAD が動いたら `head_moved` で run を止め、新しい run を始める（pr-review-fix-loop の SKILL.md）
6. 非対話のレビュアーは補助委譲をしない。対話のレビュアーの補助委譲は、停止と停止確認の手段を確かめられたランタイムだけで起動でき、今はどのランタイムも条件を満たさない（`.agents/monitoring-runtimes.md` の「PR レビュー委譲の起動可否」）
7. この Spec の builder check（Agent ツールのサブエージェント、model `sonnet`、読み取りだけ）は「計画に要る未決の点は無い」と返した。前提として挙げた 4 点（PR の番号はセッションのディレクトリ名と journal で照合する、`--discard-draft` は利用者の明示の指示だけ、fetch の不一致の試行では ref が新しい head を指すので `repinned` で残す、理由の文頭 `PR head changed` を保つ）は、D3・D4・D7 と変更の内容 6・9 のとおり

## 変更の内容

### helper

1. `review_run.py prepare` が試行 ID を作って create に渡し、結果（成功と、セッションを残した失敗）に `attempt_id` を返す。`session.json` の `run_context` に、試行 ID と、書いた候補の雛形のファイル名と SHA-256 を記録する
2. `complete`・`fail` の結果にも `attempt_id` を返す（`run_context` に無い古いセッションは null）
3. `pr_review_workspace.py abandon` に `--session-dir <dir>` を足す。`--attempt-id` と一緒に使い、`--repo`・`--pr-repo`・`--pr-number`・`--temp-root` の代わりに試行を指定する。journal の試行 ID・セッションのパス・PR の番号が指定と合わなければ拒否する
4. `abandon` の消してよい中身に、prepare が書いたまま変わっていない候補の雛形（`run_context` の SHA-256 と一致するもの）を加える。本文の draft があるか、候補の draft が雛形から変わっていれば、今までどおり拒否する
5. `abandon --discard-draft` を足す。その試行の本文の draft と候補の draft も消してよいものとして扱う。ほかの想定外のものがあれば拒否する
6. `abandon` は、version 8 の checkout の試行で、固定した PR の ref（`refs/pr-review/repos/<owner>/<repo>/<N>`）を、試行の head を指したままのときだけ消す（cleanup と同じ compare-and-delete）。所有 Git の試行の ref は、セッションと一緒に消える。試行の head は state の `pr_head`、state が無ければ journal の開始の記録の `pr_head`（create が新しく記録する）から取る。どちらも無ければ ref を残し、そのことを返す
7. version 8 の試行の `abandon` は、保存・cleanup と同じ親の checkout の保存ロックを取る
8. `review_run.py fail` に `--abandon` を足す（`--state` が要る）。実行記録を `failed`（review）にした後、4 の条件で試行を消す。消せたら `cleanup: success`・`cleanup_details`（abandon の結果）・`retained_paths: null`、消せなければ `cleanup: failed`・`cleanup_details.error`・`retained_paths` を返す
9. HEAD の不一致で止まったときの理由に、固定した head と観測した head（12 桁）を入れる（`create_from_target`・`verify_state`）

### スキル

1. SKILL.md に「保存しなかったとき」の節を足す。HEAD の照合の地点、再レビューをしないこと、片付け（`fail --abandon`・`abandon`）、報告の内容を書く。実行時の共通規則の「削除は cleanup だけ」「inspect/abandon は互換 API」と、手順 5 の失敗の扱いを、この節に合わせて直す
2. `references/noninteractive.md` の fail の説明と結果の表に、`--abandon`・`attempt_id`・fail の `cleanup` を足す
3. `references/time-budget.md` の打ち切りの保存拒否の項目をこの節に合わせ、検証シナリオの S15 を直し、prepare の後に止める場面と prepare の中の HEAD の不一致の場面を足す

## 対象外

- 自動の再レビュー（D1）
- レビューの途中の HEAD の照合（D2）
- prepare の失敗（create の途中の HEAD の不一致を含む）の自動の片付け（D6）
- repo-cleanup-after-merge で version 8 の試行を `abandon` で片付けること。同スキルは今と同じく version 8 を消さない（持ち越し候補）
- PR 修正ループ（`loop.py`）の変更。依頼文の「fail で終える」は、pr-review のスキルが `fail --abandon` にする（D5）
- `review_target.py` の `fetch_pull_head` の理由の文（すでに解決時の head と fetch した head を含む）
- 既に残っている試行（PR #190 の試行など）の片付け。利用者の指示があれば、新しい `abandon --session-dir` で扱える

## 受け入れ条件

1. 保存しなかった試行（prepare の失敗、prepare の後の fail、complete の拒否）ごとに、残すか消すか、誰が消すかがスキルに書かれている（Issue の受け入れ基準 1）
2. 再レビューの可否（自動では行わない）と上限（0 回）、新しい HEAD のレビューの始め方がスキルに書かれている（受け入れ基準 2）
3. `abandon` を使える条件が、スキルの記述と helper の判定で一致する。prepare の後に何も書いていない試行は消せ、未保存の draft がある試行・試行 ID が合わない試行は消さない（受け入れ基準 3。Issue のコメントの残る作業 2）
4. 保存しなかったときの報告の内容（拒否した照合と理由、本文と候補の draft の完全パスと有無、試行の扱い、`attempt_id`・`session_dir`、次の操作）がスキルに書かれ、HEAD の不一致の理由に 2 つの head が入る（受け入れ基準 4。残る作業 3）
5. 旧 3 地点と現行の照合の対応がスキルに書かれ、採用した分岐（prepare の中の HEAD の不一致・prepare の後の fail・complete の HEAD の不一致・`abandon`・`--discard-draft`・新しいセッションでの保存）を、`gh` を使わないローカルの fixture で実行して確かめる（残る作業 4、Issue の「検証」）
6. `fail --abandon` の結果の `cleanup`・`retained_paths` が、実際に消したか残したかと一致する
7. README の「テスト」の 3 つ（ワールドの行を除く）が終了コード 0

## 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 再レビューを自動では行わない（上限 0 回）。HEAD の不一致で止まったら、同じ実行の中で prepare を呼び直さない（complete はもともと 1 回）。新しい HEAD のレビューは、対話では利用者が改めて依頼し、非対話では呼び出し元が新しい prepare から始める | (a) Issue の案 A: 調査期限まで余裕があれば、新しい試行で 1 回だけやり直す。(b) prepare の中の不一致に限り、対話で 1 回だけやり直す | 現行の照合は prepare（レビュー前）と complete（レビュー後）にしか無く、complete で止まった時点では予算の大半を使っている。全体差分のやり直しは自動延長に当たり、時間予算の規約（自動延長・再委譲をしない）に反する。(b) はやり直しが安いが、HEAD が動くのは作者が push を続けている最中が多く、すぐやり直しても再び動きうる。非対話の主な呼び出し元の PR 修正ループは、サイクルの HEAD と違う成果を受け付けず、HEAD が動いたら新しい run を始めるので（着手時の確認 5）、レビュアーのやり直しは予算を使うだけになる。規則を 1 つにでき、「失敗の後に prepare を再実行しない」既存の規則も保てる | 委任: `/issue-to-pr #134 --merge --max-cycles 3` の推奨案での決定。Issue の案 B |
| D2 | 旧 3 地点を次のとおり対応させ、途中の照合は足さない。1/3（create の直後）→ prepare の 2 つの照合。2/3（差分取得後）→ 対応するものは無い。3/3（draft・save の直前）→ complete の保存ロックの中の照合 | レビューの途中（差分を読んだ後など）に `verify` で HEAD を確かめ、動いていたら早めに止める | 差分は固定した commit から作るので、途中で HEAD が動いても読んだ差分は変わらない（着手時の確認 2）。途中の照合を足しても、保存の前の照合は省けない。D1 で再レビューを自動で行わないので、早く気付いても使い道が無く、API の呼び出しと手順が増えるだけになる（Issue の決めること 4 への答え） | 委任: 推奨案での決定 |
| D3 | `abandon` を使える条件を、スキルと helper で次に揃える。(1) helper が作った試行で、指定の試行 ID が journal と一致する、(2) 作った処理（create・prepare）が終わっている、(3) セッションに helper が書いたものしか無い（journal、state、worktree、所有 Git、既存レビューの写し、prepare が書いたまま変わっていない候補の雛形）、(4) worktree が他の理由でロックされていない。スキルはさらに、(5) 停止を確認できない補助 worker が worktree を使っていないことを条件にする。未保存の draft（本文の draft がある、または候補の draft が雛形から変わった）があれば拒否する | (a) 今の `abandon` のまま（雛形があると拒否）とし、新入口の試行には使わない。(b) 新入口用の別のサブコマンドを作る。(c) 候補の draft の内容（coverage・findings が空）で、書いていないことを判定する | (a) では prepare の後に止めた試行が片付かない（着手時の確認 3・4）。(b) は同じ条件を 2 か所に持つことになり、Issue の「スキルと helper で一致」から外れやすい。(c) は coverage だけを書きかけた候補を見落とす。prepare が書いた内容の SHA-256 と比べれば、書き換えの有無を正確に判定できる。(1)(2)(4) は今の `abandon` の条件のまま | 委任: 推奨案での決定。Issue の決めること 2・残る作業 2 |
| D4 | 新入口の試行は `abandon --session-dir <dir> --attempt-id <id>` で指定する。prepare が試行 ID を作り、prepare・complete・fail の結果に `attempt_id` を返す。`session_dir` は失敗の結果の `retained_paths` にある | (a) 今の指定（`--repo`・`--pr-repo`・`--pr-number`・`--attempt-id`・`--temp-root`）を結果から組み立てさせる。(b) `--session-dir` だけで指定する（試行 ID を求めない）。(c) `--state` で指定する | (a) は、所有 Git の試行で `--repo` がセッションの中の Git になるなど、5 つの値を正しく組み立てる必要があり、誤りやすい。(b) は、並行する別のレビュアーの、雛形だけを持つ進行中の試行を、パスの誤りで消しうる（ループは同じ PR に 4 人のレビュアーを並行に起動する）。試行 ID は呼び出し元だけが知るので、#39 で入れた「自分の試行を見分ける」守りを保てる。(c) は、prepare が create の途中で止まった試行（`session.json` が無い）を指定できない | 委任: 推奨案での決定 |
| D5 | prepare の後にレビューせずに止めるとき（依頼の HEAD と違う、続けられないなど）は、draft を書いておらず、停止を確認できない補助 worker がいなければ、`fail --abandon` で止める。結果の `cleanup`・`retained_paths` に、消したか残したかを返す。既定（フラグ無し）は今と同じく残す | (a) `fail` を常に片付けにする。(b) `fail` の後に、別の呼び出しで `abandon` する | (a) は、停止を確認できない補助 worker が worktree を使っているときにも消してしまう（SKILL.md の「停止を確認できない worker が WT を使用中なら complete / cleanup を呼ばず」）。(b) は、非対話の最後の JSON が `fail` の結果なので、消した worktree やセッションを `retained_paths` に載せたまま返すことになり、ループの `retained` の報告と食い違う。complete が保存の後に cleanup するのと同じく、止める処理が自分の作ったものを片付ける | 委任: 推奨案での決定 |
| D6 | prepare の失敗と complete の拒否で残った試行は、レビュアーは消さずに残し、`attempt_id`・`session_dir` と完全パスを報告する。利用者が不要と判断したら `abandon --session-dir … --attempt-id …` で消せる | (a) prepare の失敗のうち HEAD の不一致だけは、prepare が自分の試行を片付ける。(b) 対話のときは、レビュアーが報告の前に `abandon` してよい | prepare の失敗は helper の失敗で、#39 の D-7 は「調査のために残す」としている。(a) は、HEAD の不一致を他の fetch の失敗と見分けるために、共有の `review_target.py` の終了コードの仕様を変える必要がある。HEAD の不一致は prepare の数秒〜数分の間にしか起きず、まれである。(b) は対話と非対話で規則が分かれる。complete の拒否では draft が書かれているので、D3 の条件で消えない | 委任: 推奨案での決定。Issue の決めること 3（draft がある場合は残す） |
| D7 | 未保存の draft は、セッションの review-backup に置いたまま保管する。保存先（`reviews/`）にも他の場所にも写さない。消すのは、利用者がその試行を消すよう指示したときの `abandon --discard-draft` だけで、レビュアーは自分の判断で付けない | (a) draft を別の場所に写して残し、セッションは消す。(b) helper の経路を作らず、利用者の手での削除に任せる | (a) は新しい保存場所の規則が要り、レビューディレクトリを読む review-fix-planning・review-verify・ループに、未保存のものを読ませるおそれがある。(b) は worktree の登録と固定した ref を手で消すことになり、pr-review の「拒否を手動削除で代行しない」と repo-cleanup-after-merge の「未対応の回収コマンドや手動削除を組み立てない」に反する | 委任: 推奨案での決定。Issue の決めること 3・残る作業 3 |
| D8 | 保存しなかったときの報告に、拒否した照合と理由（HEAD の不一致なら固定した head と観測した head、保存先の変化なら別の保存で保存先が変わったこと）、本文と候補の draft の完全パスと有無、試行の扱い（消した・残した、と理由）、`attempt_id` と `session_dir`、次の操作（新しい HEAD のレビューは新しい prepare から、draft が不要になったら利用者の指示で `abandon` できること）を含める。helper は HEAD の不一致の理由に 2 つの head を入れる | 報告の項目をスキルに書かず、helper の結果の JSON だけに任せる | 非対話では結果の JSON が報告そのもので、`retained_paths`・`attempt_id`・理由が揃えば、呼び出し元が次の操作を決められる。対話では、利用者が draft をどうするか決めるのに、有無と完全パスと次の操作が要る。モデルは追加の API の呼び出し無しに新しい head を知れないので、helper が観測した値を理由に入れる | 委任: 推奨案での決定。Issue の受け入れ基準 4 |
| D9 | テストは `.agents/skills/pr-review/tests/test_review_run.py` に 2 件足す。(1) `abandon --session-dir` が、prepare のままの試行を消し（worktree の登録と固定した ref を含む）、本文の draft がある・候補を書き換えた・試行 ID が違う・`--discard-draft` でも想定外のファイルがある試行を消さない。`--discard-draft` では draft だけを持つ試行を消す。(2) `fail --abandon` の `cleanup`・`retained_paths` が、消したときと残したときで実際と一致する | prepare・complete の HEAD の不一致の分岐、試行 ID が結果にあること、理由の文、スキルの文面を確かめるテスト | (1) は壊れると、未保存のレビューや別の試行のセッションを、エラー無しに消す（`AGENTS.md` の S。データの消失・誤った対象の削除）。拒否の条件はそれぞれ別の判定で、正しく通る例（prepare のまま、`--discard-draft`）を含める。(2) は壊れると、残した試行を報告しない、または消したものを残したと報告する（S。誤っているがもっともらしい結果）。complete の HEAD の不一致で保存しないことは、既存の `test_port_routing.py::test_moving_live_head_keeps_drafts_then_fresh_session_continues` と `test_review_run.py::test_complete_preserves_failure_as_failed_result` が守る。prepare の中の不一致は、保存の前の照合で必ず止まるので重複（D）。試行 ID が結果に無ければ `abandon` が止まる（L）。文面は F。採用した分岐は、`gh` を使わないローカルの fixture の一時スクリプトで実行して確かめる（受け入れ条件 5）。守りは `pr_review_workspace.py` の判定だが、雛形の SHA-256 を書くのが prepare なので、prepare から試行を作る fixture を持つ `test_review_run.py` に置く | `AGENTS.md` の「テストの採用基準」 |
| D10 | SKILL.md と参照文書の変更は、`superpowers:writing-skills` に従い、変更前（`origin/main`）と変更後で振る舞いを比べる。Claude Code の Agent ツールの新しいサブエージェント（model `sonnet`）に、3 つの場面（complete で HEAD の不一致、prepare の後に依頼の HEAD と違う、残った試行の片付けを頼まれた）をまとめた 1 つの問いを渡し、版ごとに 3 回答えさせる。結果は Plan の「完了」と PR 本文に書く | (a) 場面ごとに別の起動にする。(b) 比較を省き、文面の確認だけにする | 判断の手順は文面の書き方で外れやすく、固定文言のテストでは代えられない（issue-to-pr の 4 章の 5）。本物のモデルを起動する確認なので、回数と対象を Plan に書いた 6 回に限る（`AGENTS.md` の「エージェント運用」）。(a) は回数が 3 倍になる | 委任: 推奨案での決定 |
| D11 | `--merge` のループは `check-options` の結果のままにする。サイクルの上限 3 は利用者の指定。雛形 `.devcontainer/agent-runner.toml`、`--config` なし、inspect は `claude-opus`・`devin-swe`・`pi-deepseek`・`cursor-grok47`、修正は `claude-opus`、自己レビューと fix-check は `self` で、どれも雛形と個人設定の既定の適用 | ループ用のオプションを足す | 利用者が書いたループ用のオプションは `--max-cycles 3` だけで、ほかは足さない | 委任: `/issue-to-pr #134 --merge --max-cycles 3`。`check-options` は終了コード 0 |
| D12 | Plan の Task の担当は `self` にする | 別の担当に依頼する | `implement_task.py check` は `agents: [self]`、`fallback: []`、`self: true`。雛形と個人設定の既定の適用で、利用者は `--implement` を書いていない | 委任: `/issue-to-pr #134 --merge --max-cycles 3`。`check` は終了コード 0 |
