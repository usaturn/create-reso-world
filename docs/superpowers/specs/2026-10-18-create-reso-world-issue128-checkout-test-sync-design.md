# Issue #128: 中断テストの checkout 起動待ち

## 管理・実行許可

- 文書管理・実装対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/128
- 状態: `draft`。内容の承認は受けていない。
- 調査基準: `50e4a6bcbbc3e04fc20802e74997b9b00afbe6c2`（origin/main）
- 利用者の指示: `issue-to-pr` スキルを明示して `#128`。
- 許可: スキルの「通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続する指示」に従う。マージ・リリース・他者の作業の変更はしない。
- Plan: `docs/superpowers/plans/2026-10-18-create-reso-world-issue128-checkout-test-sync.md`

## 意図と原因

create の中断後に git の子が生き残る状態を検証する既存の 2 テストが、子の起動前に create を kill することがある。journal の `worktree-add` は子 git の起動前に記録されるため、この記録だけでは、生き残る checkout が存在することを保証しない。起動前の中断を helper が `vanished` と返すのは正しい。

変更対象は `.agents/skills/pr-review/tests/test_pr_review_workspace.py` の待ち合わせだけ。既存の `stalling_git_env` は実際の `git worktree add` が成功した後、自身の PID を `stalled-git.pid` に書き、同じ PID のまま `sleep 60` に移る。子は journal の lock fd を引き継ぐ。このシグナルを待てば、テストが作りたい状態を明示的に同期できる。

## 設計

1. テスト用の `wait_for_stalled_git(tmp_path: Path) -> None` を既存の待機ユーティリティの近くに追加する。
2. `time.monotonic()` による期限 30 秒・ポーリング間隔 0.05 秒を既存の `wait_for_phase` に合わせる。`stalled-git.pid` がファイルになったら返し、期限切れは何を待っていたか分かる AssertionError にする。固定時間 sleep の追加や成功するまでのテスト再実行では代用しない。
3. `test_killed_create_reports_its_last_phase_and_leftovers` と `test_abandon_waits_for_a_checkout_that_outlives_create` で、`wait_for_phase(..., "worktree-add")` の後、kill の前に新しい待機を呼ぶ。
4. 既存の kill・inspect・abandon の assertion と finally の cleanup は維持する。SIGTERM を検証する別のテストは、生き残る子を前提としないため変更しない。

PID ファイルはテスト専用の新しい tmp_path に作る。PID の読み取りやプロセス検査を新しい待機へ追加しない。ここで必要なのは wrapper が checkout 完了後まで進んだ事実であり、running の判定自体は既存の inspect assertion が検査する。

## 受け入れ条件・検証

- helper の journal 記録と子 git 起動の間に `time.sleep(0.5)` を挿入した隔離コピーで、変更前の 2 テストが期待する競合の失敗を示し、修正後の 2 テストが成功する。
- 通常条件と遅延条件で inspect が生き残る子を `running` と判定し、子の終了後は `vanished` となり、abandon が安全に片付けるという既存 assertion が通る。
- 新しい待機の期限切れは隔離した実行検査で確認する。文言一致の回帰テストは追加しない。
- `uv run pytest .agents/skills/pr-review` と README の非ワールド向け 3 コマンドが成功する。
- helper 本体は変更しないことを git diff で確認する。新しいテスト・SKILL.md の文面検査は追加しない。
- 最後に独立レビュアーがブランチ全体を読み取り専用で確認する。

隔離コピーとログは親 checkout の `tmp/agents/issue-128.6jfkkfsu/` にのみ置き、worktree 内に追跡しない作業物を置かない。テストが生成する再生成可能なキャッシュは除く。

## 対象外・編集禁止

- `pr_review_workspace.py`、スキル手順、ランチャー、インストーラー、CI、他の worktree、ローカルワールド。
- 起動前に kill した状態の仕様変更、待機時間を延ばすだけの対策、`running` assertion の緩和、テストの無条件再試行。
- #116 の移植方針決定。#116 は未着手で、この Issue の先行条件ではない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| 同期点 | wrapper の既存 PID ファイルを待つ | journal の記録だけ、固定 sleep、helper の起動記録を追加 | checkout 成功後の到達点を既に提供し、helper を変えずに競合をなくせる | issue-to-pr の通常設計判断の委任。helper 変更が必要なら範囲を見直す |
| 検証方法 | 隔離コピーで 0.5 秒遅延の RED/GREEN | 負荷をかけて偶然の失敗を待つ | 原因の窓だけを確実に広げ、最小の変更を比較できる | 予期しない外部操作・安全失敗で停止 |
| 実行方式 | executing-plans による inline | Task ごとの実装子 | 変更が 1 ファイルの 1 Task。独立した設計確認と最終レビューだけ委譲する | issue-to-pr の実行方式選択に従う |

## 調査・実行記録

- Issue 本文・全コメント・親/依存・open PR 全ページ・予約 ref・branch/worktree を確認。同じ Issue の先行作業なし、親 Issue なし、blocked_by は空。#115 は完了済み。
- 基準版の `uv run pytest .agents/skills/pr-review -q`: 190 passed、終了コード 0、27.87 秒。
- 既知の競合なので基準版が通常条件で成功しても、遅延条件による再現を省略しない。
