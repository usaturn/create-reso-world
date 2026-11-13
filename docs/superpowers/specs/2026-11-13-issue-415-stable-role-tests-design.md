# Issue #415: 外部役割の書き込み例外テストの安定化

## 管理・実行許可

- 状態: `draft`。内容の承認を受けたとは扱わない。
- 対象: https://github.com/usaturn/create-reso-world/issues/415
- 利用者指示: `#415 --merge --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,claude-code_opus_xhigh`
- 追加指示: 「作業中 pi_alibaba_qwen4-max_max でうまくいかない場合は devin_swe2_max に変更してリトライして」。安全上の拒否・停止未確認は再試行しない。helper の順序・同一担当の制約を迂回しない。
- issue-to-pr の委任により推奨案を選び、検証・commit・push・PR・レビュー修正ループへ進む。マージはループの `finalize.py` だけが行う。
- repository: `usaturn/create-reso-world`。base: origin / `refs/heads/main` / `bcff80ed97c70b31cb30afd3dfb6f9264594efb2`。
- Spec・Plan はコードと同じ worktree・PR に含める。確認用コピーは作らない。

## 目的と原因

外部の self-review・fix-check に渡す例外一覧の安全検査を、実際の `git worktree add` と20秒の役割期限との競合から切り離す。誤失敗による検証スイート全体の再実行を避ける。

現状のテストは `run_roles.run()` → `run_workflow()` → 実 worktree 準備 → `FakeAdapter.prepare()` まで進んだ要求だけを数える。準備に期限を使い切ると要求が記録されず、件数だけの assertion から原因が分からない。

## 範囲・除外

コードの変更は `.agents/skills/review-fix-planning/tests/test_run_roles.py` だけ。次は変更しない。

- `tools/agent_runner/runner.py`、runner のテスト、`scripts/run_roles.py`。
- `exception_lines()` の抽出方法、`config()` の20秒期限、既存の役割別の許可範囲。
- #400 の安全指示の文言・行や段落の構造。
- 安全指示全文の一致テストや本文の複製は追加しない。
- 実モデルによるテスト再現は行わない。ワークフローで明示指定されたレビュー・実装担当の起動と、fake adapter のみの検証を区別する。

実 worktree 作成・期限・停止確認そのものの網羅は、既存の runner/workspace テストが担う。本変更で実装側の変更が必要なら着手前に停止し、#400 との結合方針の更新が必要であることを報告する。

## 設計

テスト内に明示適用する fixture を置き、`tools.agent_runner.runner.prepare_worktree` の束縛だけを async の偽物へ差し替える。空の作業ディレクトリと準備ログを作り、成功した `ProcessResult` を返す。実 Git の準備を役割期限から外す一方、以下は実処理を通す。

1. `run_roles` が実 Git の fixture から権限の例外パスを選ぶ。
2. runner が安全指示・writes 指示・例外見出しと一覧を組み立てる。
3. `FakeAdapter` が要求を記録し、偽のローカルプログラムを実行して receipt を回収する。
4. 外部2役割の同一の一覧、各行の役割限定、各パスの付与数を既存の期待値で照合する。

対象テストと、同じ要求件数・一覧を検査する直接関連テストにのみ fixture を適用する。autouse で全テストを置き換えず、改ざん・停止未確認・履歴などの検査を広く fake にしない。

`launch()` の返した batch を受け取り、外部役割が成功して必要な要求を残したかを照合してから一覧を比較する。失敗時の assertion には役割名・state・attempt の state/終了コード等、原因を特定できる診断を含める。成功しなかった役割を無視して合格にしない。

実 worktree 準備を除く fixture の Git 操作と小さいローカル subprocess は残る。OS の無期限停止まで保証するものではなく、Issue で確認された worktree 準備と役割期限の競合を解消する。

## 受け入れ基準

- 動作環境: Dev Container、uv の locked project、実 Git の一時 fixture、fake adapter のみ。
- 実入力: 外部2役割 `a`/`b`、片側が `self` の割当、既存の複数行の例外見出しと一覧。既存テストの非ASCIIパスも維持する。
- 防御範囲: 外部2役割に同じ一覧が渡ること、各行が役割を限定すること、役割ごとの許可パスの既存 assertion を弱めない。要求が欠ける・失敗する側は状態付きで失敗する。実 worktree 準備の成功そのもの、任意の安全指示文言、#400 の実装変更は対象外。
- `exception_lines()` は変更せず、#400 が維持する「安全指示1行 → writes1行 → 見出し・一覧 → 空行 → 本文」の構造に対応し続ける。
- 対象ファイルの単独実行、runner 全体、README の共通検証を成功させる。
- 対象ファイルの pytest とシェル共通検証を同時実行する確認を2回行い、対象テストの失敗0回を観測する。回数を結果に応じて増やして成功率を作らない。
- #400 は完了依存ではない。未マージなら現在版での成功と両変更が揃った実行の未確認を区別して記録する。結合確認がマージ後に残る場合は `Refs #415` とし、残項目を Issue へ報告する。

## テスト採用基準

既存の例外一覧検査は、read-only の担当へ誤った書き込み権限を与える損害を防ぐ S / F∩S として維持する。安定化と診断文のためだけの新しい恒久テストは作らない（L）。必要な対照や診断確認はセッション領域の一時検証で行い、テストのためのテストをコミットしない。

## 決定記録

### D1: 実 worktree 準備だけを置き換える

- 選択した案: 局所 fixture で runner の `prepare_worktree` を差し替える。
- 検討した別案: 20秒を延長する、`run_workflow` 全体を偽物にする、例外一覧の生成関数だけを直接検査する。
- 選択理由: 延長は負荷との競合を残す。全体の置換や直接検査はプロンプトへの配線を検査できなくする。局所置換なら実際の一覧生成と付与を保持できる。
- 委任指示または停止条件: 通常設計判断の委任。実装側の変更が必要なら停止。

### D2: 状態付き診断と既存の検査範囲

- 選択した案: batch の役割結果を一覧照合前に検査し、失敗時に state を出す。同じ要求件数に依存する直接関連テストにも局所 fixture を適用できる。
- 検討した別案: 件数 assertion のみ、全テストを autouse で高速化する。
- 選択理由: 前者は原因が分からず、後者は本来検査する経路まで変える。安全検査の意味を保つ範囲に限定する。
- 委任指示または停止条件: 通常設計判断の委任。許可範囲を弱める変更は不可。

### D3: 担当・レビュー・公開

- 選択した案: Spec レビューと Plan の実装は明示指定 `pi_alibaba_qwen4-max_max`。両方の check 結果は `self=false`、fallback は個人設定から保持された空配列。builder check は Spec レビューで代替する。
- 検討した別案: 司令塔の inline 実装、無指定の設計レビュー。
- 選択理由: 利用者の明示した担当を優先する。設計レビューは指定がないので起動しない。
- 委任指示または停止条件: Qwen の信頼性の失敗時は停止確認後、明示指示の範囲で Devin を検討する。ただし Spec 再レビューの同一担当制約・安全拒否は迂回しない。
- ループ: 利用者指定の inspect 3担当。初期 implement は Qwen だったが、下記の利用枠超過後は追加指示により Devin へ変更する。サイクル上限3は既定の適用、self-review/fix-check の `self` は既定、fallback はいずれも空。最終ブランチ全体レビューは `--merge` のループ1回目で行う。Task ごとのレビューは省略しない。

## 調査と検証の記録

- Issue 本文・全コメント（0件）・native blockers（0件）・parent（不在）を確認。競合する #415 の PR・branch・claim はなし。#400 は open で、本文の結合方針どおり並行可能。
- 独立した読み取り専用調査で、runner の import 済み `prepare_worktree` の束縛を差し替える既存 runner テストの前例と、残すべきプロンプト生成経路を確認した。
- 変更前: `uv run --project . --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q`、18 passed in 2.90s、終了0。
- ローカル記録: `/workspaces/reso-world/tmp/agents/issue-415.gjerrhip/`。まだ安定化の実装・結合検証はしていない。
- 初回 Spec レビューは helper による外部実行、指定・実担当とも `pi_alibaba_qwen4-max_max`、観測値 `qwen4-max-preview` / `alibaba` / `max`。66.161秒、`response_failed`、CLI終了0だが429 `insufficient_quota` で結果未取得。review_id `8ca2b79569854cc1a4e4aabc59207c00`、reviewed SHA-256 `e831398b523032ec6c0cb1ae1d78787c3f91bde191dc6f95167a5a25b0f943cf`、reflected は未作成。成功・指摘0件とは扱わない。
- 全試行の停止確認済み、outside_changesなし。unprotected_changes は6件の既存の消えたレビュー用worktree登録で、このrunでは変更・削除しない。`review-1/` の記録と `qwen-failure.json` に保存。cleanup は試行worktreeとrunner-dirを回収、retainedなし。
- 利用者の追加指示により、Spec レビューの再試行・以降の実装とレビュー修正の担当は `devin_swe2_max` へ変更する。check はいずれも `self=false`、fallbackは空。失敗レビューは helper の `next_round()` が回数に数えず、停止確認済みなので新規の初回レビューを許可する。完了済みレビューの担当変更や再レビュー制約の迂回ではない。
