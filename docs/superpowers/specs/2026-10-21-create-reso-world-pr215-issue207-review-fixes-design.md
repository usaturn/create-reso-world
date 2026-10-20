# PR #215（Issue #207）のレビュー修正 1 回目

- 文書管理・対象: `usaturn/create-reso-world` の PR #215（`fix/issue-207-finalize-merged-state`）、closing Issue #207
- 状態: `completed`（結論 1: 修正して push。内容の承認は記録しない）
- 実行許可: 利用者の 2026-10-20 の `/issue-to-pr #207 --merge`。issue-to-pr が PR の作成後に PR 修正ループ（pr-review-fix-loop）を回し、その計画を review-fix-planning の完遂（修正が要れば修正して push、不要ならマージと関連 Issue の更新）で行う。採否・修正方針は確認を取らずに決めた planner の判断で、内容の承認は記録しない
- サイクル: 判断の記録の round 1（ループのサイクル 1）。前の記録は無い
- planner: claude-opus-5-5（claude-code）
- 現行 HEAD（`reviewed_head`）: `27f028c1953550e2b24001c67930b590e545a55f`、base: `f2350a4ed3c3799794cb2cf4fc8b4fc04bb86c8f`
- 入力: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#215-fix-issue-207-finalize-merged-state/`
- 確認済みの一覧: 同じディレクトリの `verified/27f028c19535.json`（review-verify の cycle、claude-opus-5-5 が作成。confirmed 2）
- 実装の Spec: `docs/superpowers/specs/2026-10-20-create-reso-world-issue207-finalize-merged-state-design.md`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| gpt-6.1-sol | gpt-6.1-sol | pi | 27f028c19535 | true | Approve |
| SWE-2-Max | SWE-2 Max | devin | 27f028c19535 | true | Approve |
| commandcode-deepseek-deepseek-v4.1-flash | deepseek/deepseek-v4.1-flash | dsh | 27f028c19535 | true | Approve |
| Grok-4.7 | Grok 4.7 | cursor | 27f028c19535 | true | Approve |

担当の割り当て（ループの `run_roles_options`、雛形 `.devcontainer/agent-runner.toml` の既定）: implement は `claude-opus`、self-review・fix-check は `self`。

## 全指摘と分類

| 判断 ID | 指摘 | 確認 | 区分 | 理由 |
| --- | --- | --- | --- | --- |
| `gpt-6.1-sol#M-1@27f028c19535` | 状況を投稿する helper（`upsert` の `_check_pull_request`）が MERGED を読んで止まっても、finalize の `merged` が false | confirmed（V-1。同じ head・別の head・create-reso-world で再現） | 対応する | 致命的: usaturn/resoloop の finalize（`--spec-commit` 無し）で、最初の確認から投稿までの間に人が手でマージすると、マージ済みの PR を未マージと報告する（手順のとおりに使うと誤った結果）。(a) 再現した誤動作、(b) この PR が足した `execution.md:165`・`finalize.py:6` の「最後に観測した状態」と食い違う |
| `SWE-2-Max#L-1@27f028c19535` | `--spec-commit` のマージ直前の確認で、検証した HEAD のままの MERGED を「別のHEADでマージされた」と報告する | confirmed（V-2） | 対応しない | 起きるには、finalize の 2 回の読み取りの数秒の間に Spec の commit を force push で外してマージする必要があり、通常の使い方で到達しない（手順は force push を禁じる）。`merged: true` と停止は正しく、違うのは停止理由の文だけ。見直す条件: PR の head を書き換える操作が最終化の手順に入ったとき |

解消済み: 0。対応する: 1。対応しない: 1。同じ条件の再発と設計の見直しのきっかけ: なし（V-1 の条件「最終化の途中で観測した MERGED を結果に残す」は、この PR のレビュー修正の commit `965270d` が直した条件（停止理由の区別・ループのテスト・abort の注記）と違う。V-2 は対応しないので数えない）。

## 対応する: V-1（`gpt-6.1-sol#M-1@27f028c19535`）

### 修正方針

`upsert_pr_comment.py` の `_check_pull_request` が、照合した PR の応答を持つ `CommentError` の派生（`PullRequestStateError`、属性 `view`）で拒否するようにし、finalize は投稿の段階でそれを受けたら `observe_merged(error.view, merged)` で観測を残してから、今までどおり停止する。停止理由（`external: status posting の取得・検査・書込みに失敗した`）・書き込みの抑止・`upsert` を CLI から使う側の挙動（`CommentError` として扱われる）は変えない。

検討した別案:

1. 投稿の前に `merged` を `null` にし、投稿が通ったら `false` に戻す（観測を受け取らない）。投稿だけの失敗まで未確認になり、helper が実際に読んだ MERGED も `null` で報告する。Issue の「観測済みの MERGED を失わない」に届かない
2. 投稿の失敗の後に finalize が PR を読み直す。読み直しも失敗しうるうえ、helper が既に読んだ状態を捨てる
3. finalize の runner を包んで `gh pr view` の出力を横から読む。`view_pr` の照合（URL・repository・番号）の前の生の出力を観測にすることになる

選択理由: 照合済みの応答をそのまま渡せば、読み取りを増やさず、別の PR の応答を拾わない。`CommentError` の派生なので、既存の受け手は変わらない。

### 守る条件と影響経路

守る条件: finalize が最終化の途中で（直接でも、呼んだ helper の中でも）対象の PR の状態を読んだら、その観測を結果の `merged` に残す（MERGED を読んだら、その後どこで止まっても `true`）。破れた前提: 「PR の状態の読み取りは finalize が直接呼ぶ `view_pr` の 3 か所だけ」という前提が、投稿の境界（`poster.upsert` の中の `_check_pull_request`）で破れていた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 観測を残す | `finalize` の最初の `view_pr` → `observe_merged` → `check_view` | 既に満たす（2756989） | 別の head の MERGED で `merged: true` | `test_merged_with_another_head_keeps_the_merge` | 7a741fa で passed（review-fix-planning のテスト 346 passed） |
| 観測を残す | `finalize` → `poster.upsert` → `_check_pull_request` → `view_pr`（OPEN でない・head が違う・記録の PR が違う） | 修正する | 投稿の直前の MERGED（同じ head・別の head）で `stopped`・`merged: true`・`issues: []`・書き込み 0 件 | `test_manual_merge_before_posting_keeps_the_merge` | 7a741fa で passed。修正前（27f028c）と、観測の 1 行を外した対照で 2 件とも失敗。fix-check の C-2 で 5 通り（実際の gh と同じ欄だけを返す fake を含む）holds |
| 観測を残す | 同じ経路で CLOSED（未マージ）・OPEN のまま head が違う | 修正する（同じ変更で観測を渡す） | `merged: false` のまま | `test_closed_before_posting_is_not_merged`、fix-check の C-3 | 7a741fa で passed・holds |
| 観測を残す | `finalize` のマージ直前の `view_pr` | 既に満たす（2756989） | 投稿の後の別の head の MERGED で `merged: true` | `test_manual_merge_with_another_head_after_posting_keeps_the_merge` | 7a741fa で passed |
| 観測を残す | `finalize` のマージ後の `view_pr` | 既に満たす（2756989） | 確認の失敗で `null`、再実行で `true` | `test_failed_confirmation_after_the_merge_is_unconfirmed_and_the_rerun_recovers` | 7a741fa で passed |
| 投稿の拒否を変えない | `upsert` を CLI（状況コメントのスニペット）から呼ぶ経路 | 既に満たす（派生は `CommentError` のまま） | 終了コード・メッセージが変わらない | `test_upsert_pr_comment.py`、fix-check の C-5、自己レビューの CLI の再現 | 7a741fa で passed。CLOSED・MERGED・head の移動で終了コード 64、メッセージは 27f028c と同じ |
| 観測を残す | `--spec-commit` の経路（投稿しない） | 対象外 | `upsert` を呼ばない | — | 対象外: 投稿しない |
| 観測を残す | `check_base`（ブランチ）・`view_issue`（Issue）・`list_comments`・`authenticated_login` | 対象外 | PR の状態を読まない | — | 対象外: PR の状態ではない |
| 実際の状態を保存する | `loop.py` の `cycle_end` | 既に満たす（738c2a7） | finalize の値によらず `pull.merged` を保存 | `test_finalize_stopped_keeps_the_real_merge` | 7a741fa で passed（`pytest tests/skills .agents/skills` 1512 passed） |

### 検証

- 関連するテスト: `uv run pytest -q .agents/skills/review-fix-planning/tests`
- 変更の種類に応じた検証（スキルの変更）: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`
- テストの採用基準: 書く。マージ状態の報告は取り消せない操作の復旧の判断に使う値で、偽の `gh` で経路を確かめる（`AGENTS.md`「テストの採用基準」）

## 対応しない: V-2（`SWE-2-Max#L-1@27f028c19535`）

上の表の理由のとおり。論点（2 回目の確認でも検証した HEAD のマージを区別するか）は、PR の既知の制限に書く。

## 結果

- 結論: 1（修正して push）
- 修正: 担当 claude-opus（runner、`run_roles.py --phase implement`、attempt `05724a170bb446e6a68618f0316538bb`、468 秒、`stop_confirmed: true`）が `63fdfb5` を作り、司令塔が差分（担当ファイル 3 つだけ）を確かめて cherry-pick した（`7a741faa39456e32d49d8e3a3b78a210a1b94f77`、ツリーは同じ）。runner の終了コード 1 は、実行中に別のセッションの PR #216・#217 のレビュー用 worktree が消えたことによる `outside_changes` で、この担当の領域ではない
- 実行した検証（`7a741fa`、2026-10-20 16:15〜16:39Z、作業ツリーは前後とも clean）: `uv run pytest -q .agents/skills/review-fix-planning/tests` → 0（346 passed）、`bash .devcontainer/run-tests.bash` → 0（33 PASS）、`bash scripts/check-layout.sh` → 0、`uv run pytest tests/skills .agents/skills` → 0（1512 passed）。修正前の RED（担当の報告）と、観測の 1 行を外した対照（司令塔、隔離 worktree）で、新しいテストの MERGED の 2 件が失敗することを確かめた
- 自己レビュー: `run_roles.py --phase self-review` の 1 回（枠は工程の記録の `pre_push_review` に予約済み）。self-review・fix-check ともに担当は `self` で、司令塔のサブエージェント（claude-opus-5-5、claude-code）2 つが並行で行った。自己レビュー後の修正は無く、再レビューもしていない
  - self-review（観点 2 と観点 1）: `claude-opus-5-5-commit-7a741faa39456e32d49d8e3a3b78a210a1b94f77.md`、Approve。Info 2 件
  - fix-check（観点 1 と観点 3）: `verified/7a741faa3945.fix-check.json`。主張 13 件のうち holds 12、unchecked 1（C-12: 確認担当の隔離環境での全体の検証。司令塔の FIX_WT での実行は全部 0）。confirmed 2 件（文書）
- 自己レビューの指摘の判定（どれも致命的ではないので対応しない）

| 判断 ID | 指摘 | 区分 | 理由 |
| --- | --- | --- | --- |
| `claude-opus-5-5-commit-7a741faa39456e32d49d8e3a3b78a210a1b94f77#I-1@7a741faa3945` | 投稿 helper の中の確認で別の head の MERGED を読むと、停止理由が投稿の失敗の文になり `execution.md:160` と合わない | 対応しない | `merged: true` は正しく、再実行で正しい停止理由になる。停止理由の文で分岐する手順は無い。修正の前と同じ停止理由。見直す条件: 停止理由で次の操作を分ける手順を足すとき |
| `claude-opus-5-5-commit-7a741faa39456e32d49d8e3a3b78a210a1b94f77#I-2@7a741faa3945` | #207 の Spec・Plan の「変更しないもの」と「3 回の読み取り」が、`upsert_pr_comment.py` の変更と合わない | 対応しない | 変更はこの Spec に記録した。実装の Spec・Plan を手順として読み直して誤る経路は無い。見直す条件: 同じ Spec を基に upsert の API を変えるとき |
| `fix-check#V-1@7a741faa3945` | I-2 と同じ（Spec 112 行・Plan 23 行） | 対応しない | I-2 と同じ問題。`revisit_when` に I-2 を書く |
| `fix-check#V-2@7a741faa3945` | I-1 と同じ（`execution.md:160`） | 対応しない | I-1 と同じ問題。`revisit_when` に I-1 を書く |

- PR の説明の既知の制限に、V-2（L-1）と I-1 の停止理由の制限を書き足した
