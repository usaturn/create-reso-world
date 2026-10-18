# Issue #128: 中断テストの checkout 起動待ち

## 管理・実行許可

- 文書管理・実装対象: `usaturn/create-reso-world`
- Issue: https://github.com/usaturn/create-reso-world/issues/128
- 状態: `completed`。実装と PR #142 のレビュー選別・受け入れ検証が完了。内容の明示承認（`approved`）とは区別する。
- PR: https://github.com/usaturn/create-reso-world/pull/142
- レビュー検証 HEAD: `bbbd91cc9d893f6e07ca3d03ee6fc7fc089f0a9e`。
- 初回実装の調査基準: `50e4a6bcbbc3e04fc20802e74997b9b00afbe6c2`（origin/main）。
- 初回実装の指示: `issue-to-pr` スキルを明示して `#128`。その時点の許可は検証・commit・push・PR 作成までで、マージ・リリース・他者の作業の変更は含まなかった。
- 今回の指示: `review-fix-planning` を明示して `#142 --hold-action skip`。計画のみの指定がないため、同スキルの完遂（必要なら修正して既存 PR へ push、不要なら検証・最終コメント・マージ・関連 Issue 更新）を実行する。`--hold-action` はこのスキルには未定義であり、停止条件や安全確認を省く許可には使わない。
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

### 実装・検証結果（2026-10-18）

- 実装: `a483c40`。テストファイルに 13 行追加のみ。PID 待機 1 関数と既存 2 テストの呼び出し。helper 本体・既存 assertion・cleanup は不変。
- 遅延コピーの RED: 2 failed、終了 1。1 件目は `vanished` と `running` の不一致、2 件目は `abandon` が `still running` のエラーを出さないことを再現（0.77 秒）。
- 同じ遅延コピーの GREEN: 2 passed、終了 0（2.19 秒）。通常条件: 2 passed、終了 0（0.81 秒）。
- 待機ユーティリティの隔離実行: ファイル無しで時計だけを進めると AssertionError、ファイル有りで即時正常終了。実行は終了 0。永続するメタテストは追加していない。
- `uv run pytest .agents/skills/pr-review -q`: 190 passed、終了 0（29.59 秒）。
- `bash .devcontainer/run-tests.bash`: 32/32 PASS、終了 0。実 API の opt-in は `PI_CODEX_LIVE_CHECK=0`・`PI_XAI_LIVE_CHECK=0`、uv は offline。
- `bash scripts/check-layout.sh`: PASS、終了 0。
- `uv run pytest tests/skills .agents/skills .agents/scripts`: 625 passed、終了 0（167.37 秒）。通常条件の最終全体検証は再試行なし。
- `git diff --check`: 終了 0。追加の固定文言テストなし。private Actions は確認対象外。
- ログ・隔離コピーは `/workspaces/reso-world/tmp/agents/issue-128.6jfkkfsu/` に保存して検証した。要点は本節へ転記済みで、終了時に不要を確認して削除する。残存する場合は最終報告に絶対パスを記載する。

### レビュー・公開（初回実装時の記録）

- 読み取り専用の独立したブランチ全体レビュー: `50e4a6b..a34554c`。Critical / Important / Minor / 判断を見送った項目はいずれも 0。再レビュー・追加修正は不要だった。子はテストを実行していない。
- PR: https://github.com/usaturn/create-reso-world/pull/142 （base `main`、head `fix/issue-128-checkout-test-sync`）。マージ未実施。
- 公開直前に Issue の OPEN、コメント・依存・open PR 全ページ・予約 ref・branch を再確認。自身の branch 以外に同 Issue の作業はなかった。
- 初回 push は Gitleaks で 4 commits を検査し、検出なしの `a34554c2a63a72cae3972b74a42982cceeb61b5b` をそのまま送信。この結果追記の push も再検査する。
- 所要: 約 15 分（03:38〜03:53 JST の目安）。準備・設計 4 分、再現・実装 1 分、全体検証 6 分、レビュー・結果確認 2 分、公開・記録 2 分。controller の壁時計で数え、子の概算時間は加算していない。
- 実装・受け入れ検証・PR 作成は完了。この時点の文書の状態は実行許可と内容の承認を区別して `draft` のまま。

## PR #142 の review-fix-planning（2026-10-18）

### 範囲と入力

- 担当: `openai-codex/gpt-6.1-sol`（pi の bash ツールが提示した `PI_PROVIDER` / `PI_MODEL`）。
- 入力ディレクトリ: `/workspaces/reso-world/reviews/#142-fix-issue-128-checkout-test-sync/`。配下の全 4 ファイルを全文読んだ。
- 全レビューの対象 HEAD は `bbbd91cc9d89`。取得した `pull/142/head` と PR API の現行 HEAD `bbbd91cc9d893f6e07ca3d03ee6fc7fc089f0a9e` が一致し、全対象 HEAD がその祖先であることを確認した。
- `PARENT_ROOT`: `/workspaces/reso-world`。`CODE_ROOT` / `DOC_ROOT`: `/workspaces/reso-world/.worktrees/issue-128-checkout-test-sync`。既存 worktree が clean かつ現行 HEAD と一致したため再利用した。このセッションが作った worktree ではないので片付けない。
- 文書の候補をリポジトリ・Issue #128・PR #142・checkout の待ち合わせというテーマで照合し、この Spec と冒頭の Plan に確定した。回ごとの別 Spec は作らない。

### 全指摘の分類

| 入力ファイル | 対象 HEAD | 解消済み | 対応する | 対応しない | 根拠 |
| --- | --- | ---: | ---: | ---: | --- |
| `SWE-2-Max.md` | `bbbd91cc9d89` | 0 | 0 | 0 | 報告された指摘なし |
| `deepseek-deepseek-v4.1-flash.md` | `bbbd91cc9d89` | 0 | 0 | 0 | 報告された指摘なし |
| `claude-opus-5-5.md` | `bbbd91cc9d89` | 0 | 0 | 0 | 報告された指摘なし |
| `grok-4.7.md` | `bbbd91cc9d89` | 0 | 0 | 0 | 報告された指摘なし |
| 自己確認 | `bbbd91cc9d89` | 0 | 0 | 0 | PR が導入した致命的な欠陥なし |
| **合計** | | **0** | **0** | **0** | 指摘の総数は 0 件 |

Opus の「反証済みで報告しない候補」は正式な指摘ではない。空の PID ファイルの理論上の窓に関して、今回追加した待機は PID を読まず、既存 cleanup が読むまでに親の終了待ちと inspect が入ることを確認した。今回の通常・遅延検証で誤動作はなく、到達条件を伴う致命的な欠陥は確認していない。将来の保険としての追加修正やテストは行わない。

### 確認範囲と判断

- PR の全差分、変更ファイル 3 件の全文（テスト 1,806 行・Spec・Plan）を確認した。検証根拠は現行 HEAD と clean の一致を確認した専用 worktree、および Git のコミット済み blob である。他の worktree の未コミット差分は見ていない。
- `stalling_git_env` の全 3 呼出元、新待機の全 2 呼出元、`wait_for_phase` の lock-wait 経路、SIGTERM テスト、kill・finally の cleanup と既存 assertion を確認した。
- helper の `git`、`CreateJournal`、`interruption_signals`、`create` / `create_session`、lock 継承、`creator_running` / `attempt_report` / `inspect_attempt`、`finished_creator` / `abandon_attempt` と削除対象の確認処理を読んだ。checkout 後の marker、継承する journal fd と別 session、子の終了後の `vanished` は既存の検査と一致する。
- helper 本体は差分なし。変更はテストの待ち合わせ 13 行のみで、既存の assertion と cleanup は不変。実際に起きた不具合の再発防止であり、AGENTS.md のテスト採用基準に適合する。文書・文言の固定値を検査するテストは追加しない。
- 「対応する」は 0 件のため、修正方針・影響経路の修正表・失敗時の修正検証は不要。以前のレビュー修正コミットもなく、設計の見直しのきっかけはない。新たな設計選択や PR の保証を狭める必要もない。

### 今回の実行検証

| 検証 | 結果 |
| --- | --- |
| 隔離 worktree の helper の `journal.record("worktree-add")` 直後だけに 0.5 秒の遅延を追加し、基準版 `50e4a6b` のテスト 3 件を実行 | 2 failed / 1 passed、exit 1、0.90 秒。`vanished` / `running` の不一致と `still running` 拒否が起きない失敗。SIGTERM は成功 |
| 同じ遅延条件で現行 HEAD のテスト 3 件を実行 | 3 passed、exit 0、1.79 秒。2 件の修正効果と SIGTERM の既存挙動を確認 |
| 専用 worktree: `uv run pytest .agents/skills/pr-review -q -p no:cacheprovider` | 190 passed、exit 0、27.09 秒 |
| 専用 worktree: `bash .devcontainer/run-tests.bash` | 32/32 PASS、exit 0 |
| 専用 worktree: `bash scripts/check-layout.sh` | PASS、exit 0 |
| 専用 worktree: `uv run pytest tests/skills .agents/skills -q -p no:cacheprovider` | 589 passed、exit 0、263.17 秒 |
| `git diff --check` | exit 0 |
| 最新 base の確認 | `origin/main` は `50e4a6bcbbc3e04fc20802e74997b9b00afbe6c2` で現行 head の祖先。base 統合ツリーの再検証は不要 |
| CI | private の create-reso-world であることを API で確認。AGENTS.md に従い確認対象外 |

実 API の live check は `PI_CODEX_LIVE_CHECK=0` / `PI_XAI_LIVE_CHECK=0`、uv は offline。pytest の `--basetemp`・`TMPDIR` とログを `/tmp/review-fix-planning.3EKv5D/` に閉じ込めた。テストの再試行はしていない。意図した RED は検出力の証拠であり、検証の信頼性失敗ではない。今回コード修正はしていないため、失敗時の安全ガードを外す対照は対象外である。

同期の sp-recon に独立調査を依頼したが、応答が空で成果と終了コードを得られなかった。成功扱いにせず、調整役が全確認を実施した。修正後の自己レビューは結論 1 のみの手順なので未実施。未確認の指摘・未読ファイルはない。

### 結論と終了前の記録

- **結論 2: 修正不要としてマージする。** 入力の指摘と自己確認の致命的な欠陥はいずれも 0 件で、現行 head の必要な検証はすべて成功した。
- open・非 draft・許可対象の `usaturn/create-reso-world` であることを再確認した。文書コミット前に PR の head を再照合し、Spec 1 ファイルだけのコミットを Gitleaks 検査後に既存 head へ送る。最終状況コメントの後、`--match-head-commit` で検証した先端だけをマージし、関連 Issue #128 を更新する。これらの外部操作の結果は PR コメントと完了報告へ記録し、本 Spec に記録だけの追加コミットは作らない。
- 再現・検証終了後に marker にある PID の生存を確認し、生き残ったプロセスはなかった。隔離 worktree を `git worktree remove --force` で解除してから親一時領域を削除済み。ログの要点は上の表へ転記した。確認用コピー・新しいテスト・新しい PR は作らない。
- 所要の計測区間: 11:02:33 JST の PR/context 確認から必須検証終了 11:12:41 まで 10 分 8 秒。うち再現・一括検証は 11:04:15〜11:12:41 の 8 分 26 秒。初期のスキル確認およびその後の記録・公開時間はこの区間に含めず、総所要は完了報告に記載する。
