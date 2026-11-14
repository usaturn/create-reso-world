# Issue #429: Pi の表示用モデル名と pr-review の prepare に渡すモデルIDを区別する

## 管理・実行許可

- 状態: `completed`（PR #444 の PR 修正ループ 1 サイクル目で修正不要と確かめた。下の「結果」）
- 対象: https://github.com/usaturn/create-reso-world/issues/429
- 利用者の指示（2026-11-15、`/issue-to-pr` の引数）:

  ```text
  #429 --merge
  --spec-review pi_alibaba_qwen4-max_max
  --implement pi_alibaba_qwen4-max_max
  --assign implement=pi_alibaba_qwen4-max_max
  --assign inspect=devin_swe2_max,pi_opencode-go_deepseek4-flash_max,pi_openai-codex_gpt6-sol_xhigh
  ```

- 許可された範囲: issue-to-pr の委任により、通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで続ける。`--merge` により、PR 作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと関連 Issue の更新を行う。これは実行許可の記録であり、内容の承認（`approved`）ではない
- 作業場所: `/workspaces/reso-world/.worktrees/issue-429-pi-model-id`（branch `fix/issue-429-pi-model-id`、base `origin/main` `c8a2f58ffb65eced3e18993d97c439bb2d23197b`）。Spec・Plan はコードと同じ worktree・PR に入れる（`DOCS_SEPARATE=false`）

## 背景

Pi の `pi-model-name` スキルの同梱スクリプト `print-pi-model.sh` は、既定で `provider/model`（例: `openai-codex/gpt-6.1-sol`）を出す。`pr-review` の SKILL.md は「Pi の `MODEL_NAME` は pi-model-name スキルの手順で決める」と書き、`references/noninteractive.md` の prepare の例は `--model-name "$MODEL_NAME"` を渡す。一方、`review_run.py` の `observed_model()` は Pi では `--model-name` が生の `PI_MODEL` と完全一致することを要求する。

このため、手順どおりに既定出力を `--model-name` へ渡すと `--model-name does not match this runtime's PI_MODEL` で拒否される。review-fix-planning の自己レビューでは `run_roles.py` が枠を予約した後に起きるため、枠だけが残り、通常の手順では再実行できない（PR #428 で実際に発生）。

同じ `MODEL_NAME` という名前で、次の 2 種類の値を案内していることが原因である。

| 用途 | 値 | 例 |
| --- | --- | --- |
| 表示・記録（pr-review-fix-loop の `--controller-model`、review-fix-planning の状況コメントの `MODEL_NAME`、利用者への表示） | 既定出力 `provider/model` | `openai-codex/gpt-6.1-sol` |
| pr-review の `prepare --model-name` | 生の `PI_MODEL` 単体（`print-pi-model.sh --model` の出力）、または省略 | `gpt-6.1-sol` |

なお prepare は、Pi では実際の `PI_PROVIDER`・`PI_MODEL` を自分で読み、`reviewer` として返す。保存名・本文のモデルは prepare が返した値を使う（noninteractive.md の既存の規則）。

## 決定記録

### D1. 修正を文書だけにし、helper を変えない

- 選択した案: `review_run.py` の照合（生の `PI_MODEL` との完全一致）は変えず、文書で 2 種類の値を区別する
- 検討した別案: (a) `observed_model()` が `provider/model` 形式を受け、`PI_PROVIDER/PI_MODEL` と一致すれば許す。(b) `--model-name` を Pi では受け付けない
- 選択理由: (a) は Issue の対象外（「既定表示値との同一視・文字列の分割を追加しない」）であり、決定済み事項（照合を緩めない）に反する。(b) は既存の正常経路（`PI_MODEL` 単体を渡す）を壊し、他の caller の互換に影響する。文書の修正だけで、手順どおりの実行では照合失敗が起きなくなる
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（文書だけで足りるかの判断）による委任

### D2. Pi の prepare では `--model-name` の省略を推奨し、明示するなら `--model` の出力を使う

- 選択した案: pr-review の SKILL.md と noninteractive.md で、Pi の prepare は `--model-name` を省くのを基本にし、明示する場合は `print-pi-model.sh --model` の出力（生の `PI_MODEL`）だけを渡すと書く。既定出力 `provider/model` を渡すと拒否されることも書く
- 検討した別案: 明示を必須にして `--model` の出力を渡す例だけを示す
- 選択理由: 省略しても prepare が実際の `PI_PROVIDER`・`PI_MODEL` を読んで検査し（欠落は拒否）、値の取り違えが起きない。review-fix-planning の自己レビューの prompt（`execution.md` の `prompt["self-review"]`）も `--model-name` を渡さない形であり、それと揃う。明示経路も既存の挙動として残す
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（`--model` の出力を使うか、省略を勧めるか）

### D3. pi-model-name スキルに、入口ごとの使い分けを足す

- 選択した案: `pi-model-name/SKILL.md` に、既定出力（表示・`--controller-model`・状況コメントの `MODEL_NAME`）と `--model` の出力（pr-review の `prepare --model-name`）の使い分けを短い表で足す。Quick Reference の「`PI_MODEL` が `MODEL_NAME` の正本」の記述は、2 つの用途を混同させるので書き直す
- 検討した別案: pr-review 側だけを直す
- 選択理由: 取り違えの起点は pi-model-name の既定出力をそのまま使うことであり、取得側にも入口ごとの使い分けがあれば、ほかの入口から読んだときも同じ誤りを防げる
- 委任指示または停止条件: Issue の「エージェントに任せる事項」（pi-model-name に使い分けを足すか）

### D4. `.pi/APPEND_SYSTEM.md` の「モデル名の抽出」も合わせる

- 選択した案: Pi のシステムプロンプトに足される「pr-review の `MODEL_NAME` は pi-model-name の手順で決める」を、prepare では `--model-name` を省くか `--model` の出力を渡すことが分かる形に直す
- 検討した別案: 変えない
- 選択理由: Pi のエージェントが最初に読む指示であり、ここが既定出力を pr-review の値と案内したままだと、pr-review 側を直しても同じ取り違えが起きうる
- 委任指示または停止条件: 推奨案での委任。Issue の作るもの（必要なら pi-model-name 側の手順にも書く）の範囲
- 編集の境界: 変えるのは「## モデル名の抽出」節だけで、`## Response Persona` 以降の利用者所有の節は 1 バイトも変えない（`tests/scripts/test-instructions.bash` が sha256 で凍結している）

### D5. 固定値テストを足さず、fake の Pi 環境での実行で確かめる

- 選択した案: 文書の文言を写すテストは書かない（AGENTS.md「テストの採用基準」の F）。不一致・欠落の拒否は既存テストで守られているかを確かめ、手順の確認は fake の Pi 環境での一時的な実行で行い、結果を PR に書く
- 検討した別案: 文書の例を取り出して実行するテストを足す
- 選択理由: 今回の変更は文書だけで、拒否の挙動は変えない。拒否（S の安全境界）は既存の `review_run.py` のテストで守られているかを確かめ、無い組み合わせだけを一時的な実行で確かめる。Issue の決定済み事項（固定値テストを増やさない）に従う
- 委任指示または停止条件: Issue の決定済み事項

### D6. 担当の割り当て（helper の検査結果）

- Plan の Task の実装: `implement_task.py check --implement pi_alibaba_qwen4-max_max` → `agents: [pi_alibaba_qwen4-max_max]`、`fallback: []`、`self: false`（利用者の `--implement` による指定）
- Spec レビュー: `review_spec.py check --spec-review pi_alibaba_qwen4-max_max` → `agents: [pi_alibaba_qwen4-max_max]`、`fallback: []`（利用者の `--spec-review` による指定。個人設定の fallback は空）。設計レビューは指定が無いので行わず、builder check は Spec レビューで代える
- PR 修正ループ（`loop.py check-options`）: `max_cycles: 3`（既定の適用）。`review.inspect` は `devin_swe2_max`・`pi_opencode-go_deepseek4-flash_max`・`pi_openai-codex_gpt6-sol_xhigh`（利用者の `--assign inspect=` による指定）。`fix.implement` は `pi_alibaba_qwen4-max_max`（利用者の `--assign implement=` による指定）。`fix.self-review`・`fix.fix-check` は `self`（既定の適用）
- 実行方式: `self: false` なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task を 1 つずつ runner の担当に依頼する
- `--merge` は base が `main` なので適用する。実装スキルの最終のブランチ全体レビューはループの 1 サイクル目で代える

### D7. Spec レビューの記録（1 回目）

- helper: `review_spec.py`（外部担当）。担当: 明示値 `pi_alibaba_qwen4-max_max`、fallback なし。`actual_agent` も `pi_alibaba_qwen4-max_max`、`identity` は model `qwen4-max-preview`・provider `alibaba`・effort `max`
- `review_dir`: `/workspaces/reso-world/tmp/agents/issue-429.j_exehwb/2026-11-15-issue-429-pi-model-id-design.spec-review/review-1`、`review_id`: `1d160cda82cd49658b1d1447c8acb8ea`、reviewed の Spec SHA-256: `caa612fe62add38c36f25fc29ef870393f1ea37a57d64b9a8ff33c6b34028562`、`elapsed_seconds`: 620、`outside_changes`: なし、`unprotected_changes`: ほかの作業の worktree 7 件（このレビューの対象外。記録だけ）
- 採否: S1（important、予約の既存挙動の確認が検証に無い）を採用し、検証と受け入れ基準に追記。S2（minor、`.pi/APPEND_SYSTEM.md` のペルソナ節の凍結）を採用し、D4 の編集の境界と検証に追記
- 再レビュー（2 回目）: 同じ担当（`actual_agent` `pi_alibaba_qwen4-max_max`、model `qwen4-max-preview`）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-429.j_exehwb/2026-11-15-issue-429-pi-model-id-design.spec-review/review-2`、`review_id`: `bafc75a9e360410bab3a8dcec968b5cf`、reviewed の Spec SHA-256: `9a227c8bde359b3d1e3c78422f5169d86dc23b3d805ef10f2f4050550a3e579b`、`elapsed_seconds`: 324、指摘 0 件、`outside_changes`: なし、`unprotected_changes`: ほかの作業の worktree 6 件（記録だけ）

## 変更するファイル

- `.agents/skills/pr-review/SKILL.md`（Pi の `MODEL_NAME` の行）
- `.agents/skills/pr-review/references/noninteractive.md`（`--model-name` の行、prepare の例の後の説明）
- `.agents/skills/pi-model-name/SKILL.md`（入口ごとの使い分け、Quick Reference）
- `.pi/APPEND_SYSTEM.md`（「モデル名の抽出」）

変えないもの: `review_run.py` などの helper、テスト、ほかのランタイム（Claude Code・Codex・agent-runner）の model-name 経路、pr-review-fix-loop・review-fix-planning の手順（`--controller-model`・状況コメントの `MODEL_NAME` は既定出力 `provider/model` のままでよく、本文を変える必要が無い）。

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）の worktree で、uv 経由で実行する。Pi の実 CLI・実モデル・GitHub は使わず、`PI_PROVIDER`・`PI_MODEL` を合成値にした fake 環境とローカル fixture で確かめる
- 実入力:
  - `PI_PROVIDER=openai-codex`・`PI_MODEL=gpt-6.1-sol` の環境での `print-pi-model.sh` の既定出力 `openai-codex/gpt-6.1-sol`
  - `print-pi-model.sh --model` の出力 `gpt-6.1-sol`
  - `--model-name` の省略
  - 不一致値 `different-fixture-model`
  - `PI_PROVIDER` または `PI_MODEL` の欠落
- 期待する結果:
  - 改訂した文書の手順どおりの 2 経路（省略、`--model` の出力を渡す）で `observed_model('pi', …)` が `('gpt-6.1-sol', 'openai-codex')` を返す
  - 既定出力をそのまま渡すと従来どおり拒否され、その誤用が文書で明記されている
  - 不一致値と、`PI_PROVIDER`・`PI_MODEL` の欠落は従来どおり拒否される
  - 文書の中で、表示・controller 用の値（`provider/model`）と prepare に渡す値（`PI_MODEL` 単体か省略）が区別され、互いに矛盾しない
- 防御範囲: 対象は Pi ランタイムの `prepare` のモデル名の受け渡し手順。対象外（変えない反例）は、照合の緩和（`provider/model` との同一視・文字列の分割・requested 値への fallback）、予約済み自己レビューの自動回復・自動再予約、過去の記録の書き換え、ほかのランタイムの model-name 経路、#375・#409・#427 の文字種・記録出力の問題
- 予約の扱い: `run_roles.py` の予約・回数制限・失敗時に枠が残る挙動は変えない。手順どおりの実行では照合失敗が起きないので、予約だけが残る状態に至らない
- テスト: 新しいテストを足さない。拒否の挙動は既存テスト（`.agents/skills/pr-review/tests/`・`pi-model-name/tests/`）、予約・再予約の拒否は `review-fix-planning/tests/test_run_roles.py`、ペルソナ節の凍結は `tests/scripts/test-instructions.bash` の実行で確かめる。手順と予約の扱いは fake 環境・私有 fixture の一時的な実行で確かめる

## 検証

- fake 環境で Issue の再現スクリプトと同じ形の確認を、上の実入力すべてについて実行し、結果を PR に書く
- `PI_PROVIDER`・`PI_MODEL` の欠落の拒否を同じ形で確かめる
- 既存テスト: `uv run --locked pytest .agents/skills/pr-review/tests .agents/skills/pi-model-name/tests -q`
- 予約の既存挙動（Issue の目標値 2）: 次の両方を行う。実予約・過去の記録には触れない
  - 予約・再予約の拒否を守る既存テスト `uv run --locked pytest .agents/skills/review-fix-planning/tests/test_run_roles.py -q` を実行する
  - 既存テストの私有 Git fixture と実 `reserve_review()` を使い、一時的な実行で「予約 → `observed_model('pi', <既定出力>)` の照合失敗 → 予約 1 件のまま・review state 未作成 → 同じ fixture の再予約は拒否」を確かめる。続けて、改訂した手順の値（省略、`--model` の出力）では照合が成功することを同じ環境で確かめる。一時的な実行のファイルは SESSION の下に置き、commit しない
- 利用者所有の節: `bash tests/scripts/test-instructions.bash` が成功する（`.pi/APPEND_SYSTEM.md` のペルソナ節が変わっていない）
- 配置の検査: `bash scripts/check-layout.sh`
- `git diff` で、変更が上の 4 ファイルと Spec・Plan に限られることを確かめる

## 結果（review-fix-planning、PR #444 サイクル 1）

- planner: `claude-opus-5-5`（claude-code）。対象 HEAD `b02478020c71d407d7af74ea49704236a22f7e38`、base `main` `c8a2f58ffb65eced3e18993d97c439bb2d23197b`（検証の時点の先端で、HEAD の祖先）
- レビュアーの構成（pr-review-fix-loop の run `e073b6bebf5e44f09e0e1c0fdb44cbc9`、全員このサイクルで実行・受け付け）:

  | レビューファイル | 担当 | モデル | ランタイム | 所要 | Merge recommendation |
  | --- | --- | --- | --- | --- | --- |
  | `SWE-2-Max.md` | `devin_swe2_max` | SWE-2 Max | devin | 257 秒 | Approve |
  | `deepseek-v4.1-flash.md` | `pi_opencode-go_deepseek4-flash_max` | deepseek-v4.1-flash | pi | 678 秒 | Approve |
  | `gpt-6.1-sol.md` | `pi_openai-codex_gpt6-sol_xhigh` | gpt-6.1-sol | pi | 393 秒 | Approve |

- 分類: 解消済み 0 / 対応する 0 / 対応しない 0（どのレビュアーも active な指摘・Unverified candidates が 0 件）
- 確認済みの一覧（review-verify mode cycle、司令塔が実行）: `reviews/usaturn/create-reso-world/#444-fix-issue-429-pi-model-id/verified/b02478020c71.json`。confirmed 0 / not_reproduced 0 / unverified 0。隔離 worktree で文書の 2 経路の受理、既定出力・不一致値・欠落の拒否、照合失敗後も予約が 1 件のまま残り再予約が拒否されることを確かめ（一時テスト 5 passed）、同じ条件を述べる文書（`loop.py` のレビュアー依頼文、issue-to-pr・pr-review-fix-loop の `--controller-model`）に食い違いが無いことを照合した。参考として、`deepseek-v4.1-flash` のレビュアーは自分の prepare に `PI_MODEL` 単体を渡して成功している
- 検証（PR の head の worktree、前後とも `git status --porcelain` は空）: `bash .devcontainer/run-tests.bash`（27 件 PASS）、`uv run --locked pytest tests/skills .agents/skills -q`（902 passed）、`bash scripts/check-layout.sh`（PASS）。すべて終了 0
- 自己レビュー: 修正が無いため行っていない（結論 2）
- 結論: 2（修正不要でマージ）。未確認の事項: 実 Pi CLI・実モデルでの prepare（有料モデルの起動が必要で、Issue #429 の評価方法の対象外）
