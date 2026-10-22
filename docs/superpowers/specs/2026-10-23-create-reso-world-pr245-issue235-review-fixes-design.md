# PR #245（Issue #235）のレビュー修正: サイクル 1

## 管理

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/245（`feat/issue-235-script-tests`、base `main`）。閉じる Issue: #235
- 状態: completed
- 実装の Spec・Plan: `docs/superpowers/specs/2026-10-23-create-reso-world-issue235-script-tests-design.md`・`docs/superpowers/plans/2026-10-23-create-reso-world-issue235-script-tests.md`（どちらも draft）
- 実行許可: 2026-10-23（JST）、利用者が `/issue-to-pr #235 --merge` で着手を指示した。issue-to-pr の `--merge` により、PR の作成後に PR 修正ループ（pr-review-fix-loop、run `447944ba887042c88970b3d02d7005ee`）を回し、その計画の工程として review-fix-planning を完遂で実行する。完遂は、この PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う。内容の承認（`approved`）ではない
- planner: claude-sonnet-5-5（claude-code）で振り分けと実装の依頼まで行い、自己レビューの準備の途中で利用者がモデルを claude-opus-5-5 に切り替えた。以後（自己レビュー・修正・記録・投稿）は claude-opus-5-5（claude-code）。判断の記録の planner は投稿した claude-opus-5-5。サイクル: 1（この PR に判断の記録は無かった）
- DOC_ROOT・CODE_ROOT（専用の worktree）: `/workspaces/reso-world/.worktrees/issue-235-script-tests`（PR の head ブランチを checkout 済み、未コミットの変更なし、HEAD は PR の head と一致したので再利用した。片付けの対象にしない）
- 修正と自己レビューの担当（ループの `planning.run_roles_options` は `--template /workspaces/reso-world/.devcontainer/agent-runner.toml`）: `implement` は `claude-opus`、`self-review`・`fix-check` は `self`（どれも雛形の既定）。自己レビューの回数: 1（`run_roles.py --phase self-review` の呼び出し 1 回）
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#245-feat-issue-235-script-tests/verified/5e9bc8c99e89.json`（親の main checkout の下）。工程の記録: 同じ場所の `5e9bc8c99e89.planning.json`

## レビュアーの構成

ループの `review` が agent-runner の workflow `review` の role `inspect` で 4 人を並行に起動した。4 人とも 1 回目で受け付けられた（`rejected`・`retained` なし）。

| レビューファイル | モデル | ランタイム | 担当 | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | pi-gpt | `5e9bc8c99e89` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | devin-swe | `5e9bc8c99e89` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | pi-deepseek | `5e9bc8c99e89` | はい | Approve |
| `Grok-4.7.md` | Grok 4.7 256K Extra High | cursor | cursor-grok47 | `5e9bc8c99e89` | はい | Approve |

## 指摘の一覧と振り分け

指摘は 7 件（Medium 6・Low 1）。確認済みの一覧（review-verify）が、7 件を 7 件にまとめ（new-world の symlink 系は 3 つのガードに分けた）、全て `confirmed`（`not_reproduced`・`unverified` は 0）とした。どれも `introduced`（原因は `d0ef1f5`）。分類: 解消済み 0 / 対応する 4 / 対応しない 1（確認済みの 7 件は、元の指摘 7 件に対し、判断は 5 件にまとめた）。

| 判断 | 元の指摘 | 確認済み | 分類 | 根拠 |
| --- | --- | --- | --- | --- |
| F-1 | `gpt-6.1-sol#M-1`・`SWE-2-Max#M-1`・`deepseek-deepseek-v4.1-flash#M-2` | V-1・V-2・V-3 | 対応する | `new-world.sh` の `AGENTS.md` の symlink の枝、`parent_ok`、`worlds/` の検査は別の分岐で、残したテストは 3 つとも外しても通る（base のテストは失敗する）。外すと `--apply`・新規作成が、リンク先（プロジェクトとリポジトリの外の利用者のファイル）へ書く。#235 が「残す S」に挙げた「symlink の先に書かない」で、致命的（誤った対象への操作）。(c)（旧場面 24・30・34 を D・L として消した回帰ガード）に当たる |
| F-2 | `gpt-6.1-sol#M-2` | V-5 | 対応する | `check-layout.sh` の `CLAUDE.md` の内容の比較を外しても、残したテストは通る。通すと、プロジェクトの規約と安全ルール（`AGENTS.md`）を読まないまま作業が進む。指示ファイルの読み込み指定は `AGENTS.md` の F∩S。(c)（旧場面 25 を F として消した） |
| F-3 | `deepseek-deepseek-v4.1-flash#M-1` | V-4 | 対応する | `check_local_skill_links` の行き先・非 symlink の検査を外しても通る（ルート側は別の関数）。古い、または別のスキルを静かに使う。(c)（旧場面 37b・37c を D として消した） |
| F-4 | `Grok-4.7#M-1` | V-6 | 対応する | main を checkout した sync が、止まる前に origin の main を上流へ進めることの確認を外した（旧場面 21・26）。push を省く実装でも通る。fork の main が上流と食い違ったまま、止まったことだけが報告される。(c) |
| S-1 | `deepseek-deepseek-v4.1-flash#L-1` | V-7 | 対応しない | Spec の棚卸しの表に `test-new-world.bash` の旧場面 38 の行が無い。事実として正しいが、表の記載漏れで致命的ではない（データ・誤った対象・誤った結果は起きない）。見直す条件: 旧 38 に当たるテストが S と判断されたとき。同じ表を F-1 の修正で更新するので、旧 38 の行（D）も足した |

- 確認中に PR が持ち込んだ致命的な欠陥は、上のほかには見つからなかった（自己確認の指摘なし）
- 設計の見直しのきっかけ: なし（以前のレビュー修正が無い。自己レビューでの再発は、自己レビューの後に確かめる）

## 守る条件と影響経路

**守る条件:** 別の関数・別の分岐として実装された S のガードは、同じ性質（symlink の先に書かない、リンクの行き先、指示ファイルの読み込み、sync の push）を守っていても別の守りであり、代表のテストが 1 件ずつ残る（D の「同じ守り」は、同じ実装の値違いに限る）。破れた前提と境界: 旧テストの整理で、「同じ性質なら同じ守り」と扱い、実装が別の分岐の最後の代表を D・F・L として消した（`d0ef1f5`）。

| 守る条件（ガード） | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` の symlink の先へ追記しない | `new-world.sh` の `AGENTS.md` の枝 | 修正する | `--apply` が終了コード 1・`CONFLICT: AGENTS.md is a symlink`、プロジェクトとリンク先が不変 | `test-new-world.bash` の新 13。枝を外した写しで失敗する | 通る。枝を外すと新 13 が失敗（N1） |
| 途中のディレクトリの symlink の先に書かない | `parent_ok` | 修正する | 終了コード 1・`.claude is not a directory`、プロジェクトとリンク先が不変 | 新 14（リンク先の `settings.json` を消して差が出る状態にする）。`-L` の判定を外した写しで失敗する | 通る。外すと新 14 が失敗（N2） |
| `worlds/` が symlink なら何も作らない | `new-world.sh` の `worlds/` の検査 | 修正する | 終了コード 3・`resoloop` を呼ばない・リンク先が空のまま | 新 15。検査を外した写しで失敗する | 通る。外すと新 15 が失敗（N3） |
| プロジェクトの `CLAUDE.md` は `@AGENTS.md` を読み込む | `check-layout.sh` の `CLAUDE.md` の比較 | 修正する | `worlds/demo: CLAUDE.md must be exactly @AGENTS.md` で失敗 | `test-check-layout.bash` の新 7 の `p-claude`。比較を外した写しで失敗する | 通る。外すと失敗（N4） |
| プロジェクト側のスキルのリンクは `../../.agents/skills/<name>` だけ | `check_local_skill_links` の行き先・非 symlink | 修正する | `has unexpected target`・`is not a symlink` で失敗 | 新 7 の `p-target`・`p-realdir`。各検査を外した写しで失敗する | 通る。外すとどちらも失敗（N5・N6） |
| 対応するスキルの無いリンク | `check_local_skill_links` の `has no matching` | 対象外 | — | — | L: 読み込んでも見つからないだけで損害にならない（旧 17・37a） |
| main 上で止まる sync も、先に origin の main を上流へ進める | `resoloop-fork.sh` の `do_sync`（未コミット・分岐したローカル main） | 修正する | `origin.git` の main が上流の先端（`v3`・`v4`）と一致 | `test-resoloop-fork.bash` の新 8 の 2 つの確認。main 上で push を省いた写しで失敗する | 通る。省くと新 8 が失敗（N7） |
| `check-layout.sh` の `.pi`・`sp-implementer.md` の行き先、必須ファイル | 新 7 の `p-file`・`p-pi` | 既に満たす | 同じ分岐の値違い（旧 30・39・41b） | 新 7・8 | D のまま（同じ分岐に値だけが違う） |
| `new-world.sh` の前提の欠落（`uv`・ルートの `settings.json`・`jq`） | 前提の検査（旧 15・28・45） | 対象外 | — | — | L: 終了コード 3 とメッセージで止まり、`resoloop init` の前なので何も作らない（作られても `check-layout.sh` の宙吊りの検査で気付く）。代表の新 5（`.pi`）がある |
| （自己レビュー）マニフェストの `"key"` の allowlist は、区切りの無い無作為な値を除外しない | `.gitleaks.toml` の 1 つ目の allowlist（`scan-before-push.sh` が base の設定で使う） | 修正する | `scan-before-push.sh` が `"key": "<無作為な値>"` で検出して止まる | `test-scan-before-push.bash` に 1 件足し、allowlist を `.*` に広げた写しで失敗する | 通る。広げると失敗（P1） |
| （自己レビュー）main を checkout 中のきれいなローカル main を fast-forward する | `do_sync` の `merge --ff-only` の分岐（detached の `branch -f` とは別） | 修正する | `updated: local main`、HEAD が上流の先端で main のまま、追跡ファイルの変更が無い | `test-resoloop-fork.bash` の新 8 に足し、分岐を何もしない処理にした写しで失敗する | 通る。外すと失敗（P2） |
| （自己レビュー）`.claude/skills/<name>` の通常ファイルは symlink とみなさない | `check-layout.sh` の `rec_mode != 120000` の条件 | 修正する | `.claude/skills/foo is not a symlink` で失敗 | `test-check-layout.bash` の新 5 に `skills-regular` を足し、条件を外した写しで失敗する | 通る。外すと失敗（P3） |
| `new-world.sh` の `parent_ok` の通常ファイルの条件（旧 22・23） | `parent_ok` | 対象外 | — | — | 欠けても `mkdir` のエラーで終了 1、プロジェクトは不変（fix-check V-4。L） |
| `context`・`review_copy` の D の組み合わせ | `_require_origin` の共有、push URL の検査 | 既に満たす | 同じ関数・同じ分岐の値違い（Spec の表） | `test_superpowers_context.py` ほか | 別の関数に分かれているものは無い（`select_push_remote` の後ろの宛先は残した） |

## 修正方針

- 推奨案: 消した 7 場面を、base の旧場面から今のファイルの補助関数に合わせて戻す（new-world の 13〜15、check-layout の `p-claude`・`p-target`・`p-realdir`、fork の新 8 の 2 つの確認）。`scripts/` のコードは変えない（ガードは実装と一致している）。Spec の表と決定記録（D-235-9）を、D は同じ実装の値違いに限る形へ直す
- 他の案: (1) 全ての旧場面を戻す（#235 の趣旨に反する。D に当たるものまで戻る）、(2) 同じ性質を 1 つの場面にまとめる（異常が複数入り、別の拒否理由で通る。失敗時の検証の 3 に反する）、(3) `scripts/` 側のガードを 1 つの関数にまとめて 1 件で確かめる（コードの変更で、#235 の範囲外）。推奨案は、範囲が最小で、ガードごとの検出力を保つ
- 検証: 3 つのテストの単独の実行、守る処理を 1 つだけ外した使い捨てのコピー 7 件（Spec の「変異の確認」のサイクル 1）、`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`

## 実行した検証と結果

- 実装: `run_roles.py --phase implement`（担当 `claude-opus`、run の出力 `/workspaces/reso-world/tmp/agents/review-fix-planning-pr245.uwe35r_0/implement-run`、所要 346 秒）が runner の worktree に commit `15bb163` を作った。停止を確かめ（runner の `state: success`、担当のプロセスは残っていない）、差分が 3 つのテストのファイルだけ（58 行の追加・2 行の削除）であることを確かめてから、専用の worktree へ cherry-pick した（`8476840`）。Spec の表の更新は planner が `f48a125` で commit した
- 関連テスト（`8476840`）: `bash tests/scripts/test-new-world.bash`・`test-check-layout.bash`・`test-resoloop-fork.bash` がどれも終了コード 0
- ガードを外した対照（失敗時の検証の 4。planner が、追跡ファイルだけを写した `mktemp -d` の写しで、ガードを 1 つずつ外した。担当も同じ 7 件を独立に実行し、同じ結果を報告した）: N1〜N7 の 7 件とも、戻した場面が失敗した（Spec の「変異の確認」のサイクル 1 の行）。負例には異常を 1 つだけ入れ、状態はプロジェクトとリンク先の `snapshot`（種類・mode・リンク先・ハッシュ）全体で比べている
- 変更の種類に応じた検証（`f48a125`、環境の変更）: `bash .devcontainer/run-tests.bash` が終了コード 0（`PASS: 28 test(s)`）、`bash scripts/check-layout.sh` が終了コード 0（`PASS: check-layout`）。ログ: `/workspaces/reso-world/tmp/agents/review-fix-planning-pr245.uwe35r_0/verify/`
- push の前の検査（push はしていない）: `scan-before-push.sh -C <専用の worktree> --base origin/main` が `481a047..f48a125` の 5 commit で検出なし
- 計測（`8476840` の後）: 33 件・9 本・1842 行（戻す前は 1786 行）
- 自己レビュー後の修正（`cbc3de0`・`9abd900`）: `test-check-layout.bash`・`test-resoloop-fork.bash`・`test-scan-before-push.bash`（18 リポジトリ）が終了コード 0。ガードを外した写し P1〜P3 で、足した確認がどれも失敗した。`9abd900` で `bash .devcontainer/run-tests.bash` が終了コード 0（`PASS: 28 test(s)`）、`bash scripts/check-layout.sh` が終了コード 0。ログ: `/workspaces/reso-world/tmp/agents/review-fix-planning-pr245.uwe35r_0/verify2/`。計測: 33 件・9 本・1856 行
- 全体の pytest（`uv run pytest tests/skills .agents/skills .agents/scripts tools`）は、修正（テストと文書だけ。Python のファイルは変えていない）の後には再実行していない。修正前の `5e9bc8c` で 3636 passed

## 自己レビュー

`run_roles.py --phase self-review` を 1 回呼んだ（工程の記録に `pre_push_review` を予約。self-review・fix-check とも `self` なので、司令塔が 2 つのサブエージェント（claude-opus-5-5、claude-code）に同時に任せた。1 回と数える）。対象は修正後の `f48a125`。

- self-review（PR 全体の再レビュー。`claude-opus-5-5-commit-f48a125209431fedf5ecf7c5ca5d67ac6cce429b.md`、Approve）
  - M-1（Medium、検証済み）: D-235-9 の基準で見ても、別の条件だけが守る S のテストが 3 か所消えたまま。(1) `.gitleaks.toml` の 1 つ目の allowlist（マニフェストの `"key"`）の狭さを確かめていたのは消した `test-ci.bash` だけ（広げても残したテストが通り、`scan-before-push.sh` が無作為な値を通す）、(2) main を checkout 中の `merge --ff-only` の分岐（旧 26 の前半）、(3) `check-layout.sh` の `rec_mode != 120000` の条件（旧 34）。→ 対応する。(1) は秘密情報の漏れ、(2) は更新したと報告して main が動かない誤った結果、(3) は通常ファイルの `.claude/skills/<name>` でスキルが静かに欠ける。どれも (c)
  - I-1（Info）: Spec の表の一部の「D」の表記が D-235-9 の定義と合わない（消す判断は L として成り立つ）→ 対応しない（表記だけで致命的でない。見直す条件: 表を使って再分類するとき）
- fix-check（`verified/f48a12520943.fix-check.json`・`.statement-candidates.json`・`.fix-check.md`）: 主張 20 件のうち holds 16・violates 4。戻した 7 つのガードは、外した写しで全て検出された。fix-check 自身の指摘はどれも Low の目安
  - V-1（preexisting）: 新 14 のリンク先の snapshot の比較は書き込みを検出せず、検出はメッセージの照合だけ → 対応しない（ガードの欠落は今も検出される。見直す条件: 新 14 がメッセージの照合を失うとき）
  - V-2（preexisting）: `p-target` は行き先違いと宙吊りの 2 つの異常を持ち、比較を `[ -e ]` に置き換えた変異が生き残る → 対応しない（今の実装の欠落は検出される。置き換えは別の実装の変更で、致命的な見逃しではない。見直す条件: `check_local_skill_links` の行き先の判定を変えるとき）
  - V-3（文書）: Spec の表の「34 の通常ファイルの `worlds/` は `check-layout.sh` が失敗する」は事実と違う（`mkdir` が失敗して終了 1） → 対応しない（L の分類は変わらず、誤った結果にならない。見直す条件: 表を直すとき）
  - V-4: 旧 22・23（`parent_ok` の通常ファイルの条件）と旧 34（`rec_mode`）は同じ if の別の条件 → 旧 34 は self-review の M-1 (3) として直した。旧 22・23 は対応しない（欠けても `mkdir` のエラーで終了 1、プロジェクトは不変で、気付けない損害は観測されていない。見直す条件: 途中の通常ファイルで書き込みが起きる経路が見つかったとき）

自己レビュー後の修正（M-1 の 3 か所。planner が直した。`cbc3de0`・`9abd900`）は再レビューしていない。修正の検証: 3 本のテストが通り、ガードを外した写し（P1〜P3）で、足した確認がどれも失敗した。

## 結論

結論 1: 修正して push する。対応する 4 件（F-1〜F-4）と、自己レビューの M-1 を直した。push する HEAD と検証の結果は状況コメントに書く。

### PR の説明の既知の制限

「対応しない」とした指摘のうち、実在する制約（V-1・V-2・V-4 の旧 22・23）は、PR の本文の「既知の制限」に書き足す。
