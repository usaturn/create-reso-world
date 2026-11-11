# Issue #396: monitoring の期限超過テストの時間依存をハンドシェイクで解消する

- 状態: `draft`
- 日付: 2026-11-12
- Issue: https://github.com/usaturn/create-reso-world/issues/396
- 対象リポジトリ: usaturn/create-reso-world（base: `main`、捕捉 SHA `ae4b6e71361314fb3de6008f8d31b830fec90f3c`）
- 実装対象: `.agents/skills/monitoring-long-tasks/tests/fake_worker.py`（テスト用 fake CLI）

## 管理・実行許可

利用者の指示（2026-11-12、原文）:

> /issue-to-pr #396 --merge
> --spec-review pi_alibaba_qwen4-max_max
> --implement pi_alibaba_qwen4-max_max
> --assign implement=pi_alibaba_qwen4-max_max
> --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh
> pi_alibaba_qwen4-max_max を動かす為に、 ANTHROPIC_AUTH_TOKEN を MAAS_ANTHROPIC_TOKEN として渡してください。
> 途中でメインがマージされたら、追随して作業を止めずに続行してください。

許可された範囲:

- issue-to-pr スキルの通常の委任（推奨案での設計判断、検証・commit・push・PR 作成の継続）。Spec・Plan は `draft` のままコミットし、内容の承認（`approved`）にはしない。確認用のコピーは作らない
- `--merge`: PR 作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` によるマージと関連 Issue の更新まで行う。マージはループの中の `finalize.py` だけが行う
- `pi_alibaba_qwen4-max_max` を起動するすべての runner 起動（Spec レビュー・Task 実装・ループのレビューと修正）で、このセッションの `ANTHROPIC_AUTH_TOKEN` の値を `MAAS_ANTHROPIC_TOKEN` として子に渡す。値はログ・文書・コミットに書かない
- 作業中に `origin/main` が進んだら（他の PR のマージ）、停止せずに追随する: base を再捕捉し、feature branch を新しい base に rebase し、検証をやり直して続行する。この run に限り issue-to-pr の「捕捉後の base 移動で停止」を利用者が明示的に解除した。rebase が競合して解消できないときは停止する（別の停止条件であり、この委任では解消しない）

## 意図と問題

`test_undeclared_stop_never_signals`（`.agents/skills/monitoring-long-tasks/tests/test_task_watch_process.py`）は、`--stop none`（停止を宣言していない対象には決してシグナルを送らない）という安全の守りを端到端で確かめるテストである。worker が期限（0.3 秒）後も生存している間に watcher が `hold/deadline` を観測し、その後 worker が正常終了して `completed` になることを要求する。

現在の fake worker（`undeclared` モード）は固定 1.5 秒の sleep の後に終了する。負荷などで watcher の次の観測が worker の終了より遅れると、`decide()` は終了優先の仕様どおり期限判定より先に `completed` を返し、`hold/deadline` の event が一度も記録されない。その結果、シグナルを送っていない正常な結果でも `events.jsonl` に `hold/deadline` があることを要求する assertion が失敗する（PR #395 の検証で実際に発生。全体再実行に約 11 分）。

このテストは `--stop none` の守りを確かめる唯一の端到端テストである（`test_task_watch_core.py` の単体テストは `stop="none"` を扱わない）。assertion を弱めて vacuous に通すことは、守りの弱化に当たる。

## 受け入れ条件（Issue 本文から）

1. worker が期限後も生存している状態を、固定秒数のスケジューリングに依存せず確かめた上で、`--stop none` の `hold/deadline` とシグナルを送らない条件を検査できる
2. worker が観測前に正常終了した場合は、完了を優先する既存仕様と矛盾しない。プロセスの回収漏れや、停止確認の守りを弱めない
3. 通常の単独実行と他の検証と並行した実行でテストが安定することを確認し、リポジトリのテスト採用基準に従う
4. #345 の速度改善とは別に現状の誤失敗を扱い、同 Issue の並列化検討にも結果を参照できるようにする

## 設計（推奨案）

### worker と watcher のハンドシェイク（fake worker のみの変更）

`fake_worker.py` の `undeclared` モードを次のとおり変更する:

1. 今までどおり SIGTERM ハンドラー（`got-term` を書く）を取り付ける
2. 固定の `time.sleep(1.5)` をやめ、`state/events.jsonl` に `decision == "hold"` かつ `reason == "deadline"` の event が現れるまで短い間隔（既存の `INTERVAL` = 0.05 秒）でポーリングし、現れたら `return 0` で正常終了する
3. 読み取りは完全な行だけを対象にし、書きかけの末尾行（JSON として解析できない行）は読み飛ばす
4. 既存の `signal.alarm(60)` はそのまま残す。watcher が `hold/deadline` を記録しない不具合では worker が 60 秒後に SIGALRM で終了し、テストは `completed` 以外の結果で失敗する（失敗が可視化される）

`state` ディレクトリは fake worker の argv[4] で既に受け取っており、`finalize-late` モードが `state/finalize.requested` を読む前例がある。`events.jsonl` は追記専用で、一度記録された `hold/deadline` は消えない。

テスト本体（`test_task_watch_process.py`）の assertion・deadline 0.3 秒・poll 0.05 秒は変更しない。

### この設計が受け入れ条件を満たす理由

- 条件 1: worker は watcher が `hold/deadline` を記録するまで終了しない。`hold/deadline` は `decide()` が「未終了かつ elapsed >= deadline」のときだけ返す判定なので、worker が期限後も生存していたことが記録によって保証される。スケジューリングの遅延が何秒あっても、worker の終了が観測より先に回ることはない
- 条件 2: `task_watch.py`（`decide()`・`_run()` を含む）は一切変更しない。観測前に終了したら `completed` を優先する既存仕様はそのまま（単体テスト `test_exit_is_completed_only_with_zero_and_declared_result` がカバー）。回収（`_wait_group_empty`）・停止確認（`_wait_stopped`）の守りも変更しない
- 条件 3: 後述の検証（遅延の決定的再現・反復実行・並行負荷）で確認する
- 条件 4: 変更はテスト用 fake worker に閉じ、#345 の並列化とは独立。検証結果を PR 本文・Issue コメントに残し #345 から参照できるようにする

### 編集禁止・対象外

- `task_watch.py`・`SKILL.md`・`test_task_watch_core.py`・`test_task_watch_process.py` の変更（テスト本体の assertion 弱化を含む）
- 他のテストモード（`heartbeat`・`ignore-term`・`finalize-late` など）の挙動変更
- #345 の並列化・速度改善そのもの
- 新しいコミット対象テストの追加（下記のテスト採用基準の分類による）
- ワールドのプロジェクト・他リポジトリの変更

### テスト採用基準による分類

- 既存の `test_undeclared_stop_never_signals` は **S**（停止を宣言していない対象へのシグナル送信は、壊れてもエラーにならず危険な操作が進む損害。実際に起きた誤失敗の再発防止でもある）。修正後も S の守りを維持する
- fake worker のハンドシェイク自体はテスト基盤であり、壊れたときはテストの失敗・alarm による終了として可視化される（**L**）。新しいコミット対象テストは書かない。遅延の再現ハーネスはセッションディレクトリの一時スクリプトで行い、コミットしない

## 検証計画

1. ベースライン: worktree で `uv run pytest .agents/skills/monitoring-long-tasks -q -p no:cacheprovider`（実装前に 25 passed を確認済み）
2. RED（修正前の決定的再現）: 一時スクリプトで watcher を起動直後に SIGSTOP し、旧 worker の sleep 1.5 秒より長い 2 秒待って SIGCONT する。旧コードでは `hold/deadline` が記録されず完了すること（誤失敗の再現）を確認する
3. GREEN: 同じ遅延再現を修正後のコードで実行し、`hold/deadline` が記録され、`completed`・`deadline_exceeded=true`・`stop=null`・`got-term` なしになることを確認する
4. 安定性: 修正後の単体テストを 30 回反復実行して全件成功を確認する
5. 並行負荷: 全体テスト `env -u CODEX_THREAD_ID uv run pytest tests/skills .agents/skills .agents/scripts tools -q -p no:cacheprovider` を、シェルテスト（`tests/` 配下の bash テスト）または CPU 負荷と並行させて実行し、全件成功を確認する（PR #395 の失敗は並行実行時に発生した）
6. レイアウト: `bash scripts/check-layout.sh`

検証の記録（HEAD・`git status --porcelain`・argv・終了コード・ログの完全パス）はセッションディレクトリに残し、`--merge` のループで再利用する。

## 決定記録

### D1: 修正方式 — worker と watcher のハンドシェイク

- 選択した案: fake worker が `hold/deadline` event の記録を待って終了する（上記設計）
- 検討した別案:
  - (a) `events.jsonl` の assertion をやめ、`decide()` の単体テストで `hold/deadline` を確かめる → 端到端の非 vacuous 性が失われ、worker が期限前に終了してもテストが通るようになる。S の守りの弱化なので不採用
  - (b) sleep を長くする・deadline を短くするなどの時間調整 → 確率が下がるだけで固定秒数への依存が残る。Issue の条件 1 が明示的に排除しているので不採用
  - (c) テストプロセスが `hold/deadline` を観測してから解放ファイルを書き、worker がそれを待つ → 同期の登場人物が増える。worker が直接 `events.jsonl` を読む案と保証は同じで、より単純な (選択案) を採用
- 選択理由: `task_watch.py` を変更せずに「期限後も生存」を決定的に保証でき、既存の assertion をそのまま維持できる。`finalize-late` モードの state 読み取りという前例にならう
- 委任指示: issue-to-pr の推奨案委任。停止条件: 意味を変える仕様変更（`decide()` の変更など）が必要になったら停止

### D2: worker が待つ対象 — `events.jsonl` の `hold/deadline`

- 選択した案: `state/events.jsonl` をポーリングし、`hold`/`deadline` の行を探す
- 検討した別案: `status.json` の `decision`/`deadline_exceeded` を待つ → アトミックに置き換わるファイルで同样に可能だが、`events.jsonl` は追記専用で一度書いたら消えず、テストが assertion する対象そのものなので、待つ対象と検査対象が一致するこちらを選ぶ
- 選択理由: assertion と同じ記録を待つため、ハンドシェイクがテストの非 vacuous 性を直接保証する
- 委任指示: 推奨案委任。停止条件: なし（実装の詳細）

### D3: 実行方式 — runner 担当による SDD（Task を 1 つずつ依頼）

- 選択した案: `implement_task.py check` の `self=false` のため、`superpowers:subagent-driven-development` の形で Task を `pi_alibaba_qwen4-max_max` に 1 つずつ依頼する
- 検討した別案: 司令塔（self）による実装 → 利用者が `--implement pi_alibaba_qwen4-max_max` を明示しているので不採用。失敗を理由に self へ引き取らない
- 選択理由: 利用者の明示指定
- 委任指示: `--implement pi_alibaba_qwen4-max_max`。停止条件: 再試行上限・`failed`・安全の失敗

### D4: Spec レビュー — `pi_alibaba_qwen4-max_max`（外部 runner）

- 選択した案: `--spec-review pi_alibaba_qwen4-max_max` の明示指定どおり外部 runner で Spec レビューを行う。builder check は行わない（Spec レビューが代わる）。設計レビューは指定がないため行わない
- 検討した別案: self での builder check → 明示指定に反するので不採用
- 選択理由: 利用者の明示指定
- 委任指示: `--spec-review pi_alibaba_qwen4-max_max`。停止条件: レビュー失敗（`state: failed`・`status: incomplete`・版不一致など）、`important` 採否の再レビュー上限超過

### D5: ループの構成（`--merge`）

- 選択した案: `loop.py check-options` の結果どおり。`--assign implement=pi_alibaba_qwen4-max_max`（利用者指定）、`--assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`（利用者指定）。`max_cycles=3` は既定の適用（利用者の指定ではない）。`self-review`・`fix-check` は `self`（既定）。fallback はすべて `[]`（個人設定で保たれた値）
- 検討した別案: なし（利用者の指定と既定に従う）
- 選択理由: 利用者の明示指定と既定
- 委任指示: `--merge` とループ用 `--assign`。停止条件: pr-review-fix-loop の停止条件

### D6: runner へのキーの受け渡し

- 選択した案: runner を起動するコマンドの環境で `MAAS_ANTHROPIC_TOKEN` にこのセッションの `ANTHROPIC_AUTH_TOKEN` の値を設定して渡す（`with_keys.py` は今の環境に値があればそれを子に届ける）。値は表示・記録しない
- 検討した別案: env ファイルへの書き込み → リポジトリの規約（env ファイルに key を置かない）に反するので不採用
- 選択理由: 利用者の明示指示（「ANTHROPIC_AUTH_TOKEN を MAAS_ANTHROPIC_TOKEN として渡してください」）
- 委任指示: 利用者の 2026-11-12 の指示。停止条件: キーが無効で runner が認証失敗したときは停止（値を推測・再取得しない）

### D7: base 移動への追随

- 選択した案: 作業中に `origin/main` が進んだら、base を再捕捉して feature branch を rebase し、検証をやり直して続行する
- 検討した別案: issue-to-pr の既定（base 移動で停止）→ 利用者が明示的に解除したので不採用
- 選択理由: 利用者の明示指示（「途中でメインがマージされたら、追随して作業を止めずに続行してください」）
- 委任指示: 利用者の 2026-11-12 の指示。この run に限る。停止条件: rebase の競合が解消できないとき、移動が fast-forward でないとき、追随後の検証が失敗したとき

## 成果物

- 変更: `.agents/skills/monitoring-long-tasks/tests/fake_worker.py`（`undeclared` モードのハンドシェイク化）
- 文書: 本 Spec と Plan（`docs/superpowers/plans/2026-11-12-issue-396-monitoring-deadline-test.md`）。コードと同じ PR に含める（create-reso-world 自身の変更のため文書専用 PR は出さない）
- PR: usaturn/create-reso-world の `main` 向け。`Closes #396`（マージ後に確認が必要な項目は残らない。安定性の確認はローカル検証で完了する）