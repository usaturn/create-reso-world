# Issue #429 実装計画: Pi の表示用モデル名と prepare に渡すモデルIDを区別する

- 状態: `draft`
- Spec: `docs/superpowers/specs/2026-11-15-issue-429-pi-model-id-design.md`
- 実行許可: Spec の「管理・実行許可」のとおり（issue-to-pr、`--merge`）。内容の承認ではない

## 実行方式と理由

`implement_task.py check` の `self` が false（`--implement pi_alibaba_qwen4-max_max`）なので、issue-to-pr の「Task の実装を runner の担当に依頼する」で、Task 1 を runner の担当に依頼する。変更は 4 つの文書の短い書き換えで互いに依存するため、1 Task にまとめる（同じ用語を揃えて書く必要があり、分けると表現がずれる）。Task 2 の検証は司令塔が自分で行う。`--merge` が適用されるので、最終のブランチ全体レビューはループの 1 サイクル目で代える。

## 受け入れ基準

- 動作環境: Dev Container（Ubuntu 26.04）の worktree で、uv 経由で実行する。Pi の実 CLI・実モデル・GitHub は使わず、`PI_PROVIDER`・`PI_MODEL` を合成値にした fake 環境で確かめる
- 実入力: `PI_PROVIDER=openai-codex`・`PI_MODEL=gpt-6.1-sol` の環境での `print-pi-model.sh` の既定出力 `openai-codex/gpt-6.1-sol`、`print-pi-model.sh --model` の出力 `gpt-6.1-sol`、`--model-name` の省略、不一致値 `different-fixture-model`、`PI_PROVIDER` または `PI_MODEL` の欠落
- 期待する結果: 文書の手順どおりの 2 経路（省略、`--model` の出力）で `observed_model('pi', …)` が `('gpt-6.1-sol', 'openai-codex')` を返す。既定出力をそのまま渡すと拒否され、その誤用が文書に明記されている。不一致値と欠落は拒否される。表示・controller 用の値（`provider/model`）と prepare に渡す値（`PI_MODEL` 単体か省略）が 4 つの文書で区別され、互いに矛盾しない
- 予約: `run_roles.py` の予約・回数制限・失敗時に枠が残る挙動は変えず、手順どおりの値では照合失敗が起きないことを私有 fixture で確かめる。`.pi/APPEND_SYSTEM.md` のペルソナ節は変えない
- 防御範囲: 対象は Pi ランタイムの `prepare` のモデル名の受け渡し手順。対象外（変えない）: `review_run.py` などの helper とテスト、照合の緩和（`provider/model` との同一視・分割・requested 値への fallback）、予約済み自己レビューの自動回復、過去の記録の書き換え、ほかのランタイムの model-name 経路、pr-review-fix-loop・review-fix-planning の本文

## Task 1: 4 つの文書で 2 種類の値を区別する

- 担当ファイル:
  - `.agents/skills/pr-review/SKILL.md`
  - `.agents/skills/pr-review/references/noninteractive.md`
  - `.agents/skills/pi-model-name/SKILL.md`
  - `.pi/APPEND_SYSTEM.md`
- 内容:
  1. `pr-review/SKILL.md` の「Pi の `MODEL_NAME`」の行（43 行付近）: `PI_PROVIDER`・`PI_MODEL` の確認と欠落時の扱いは残したうえで、Pi の `prepare` は `--model-name` を省く（helper が実際の `PI_PROVIDER`・`PI_MODEL` を読む）か、`print-pi-model.sh --model` の出力（`PI_MODEL` 単体）だけを渡すことを書く。pi-model-name の既定出力 `provider/model` は表示・`--controller-model`・状況コメント用の値で、`--model-name` に渡すと `--model-name does not match this runtime's PI_MODEL` で拒否され、自己レビューでは予約した枠だけが残ることを書く。保存名・本文のモデルは prepare が返す `reviewer` を使うこと（既存の規則）に触れてよい
  2. `noninteractive.md`: 入力の表の `--model-name` の行と、prepare の例の直後の「Codexはmodel-nameを省き、Piも現在envから読むときは省く」の説明を、上と同じ区別が分かる形に直す。例の `--model-name "$MODEL_NAME"` は Pi 以外の runtime の値であることが分かるようにする（例のコードブロック自体は残してよい）
  3. `pi-model-name/SKILL.md`: 「入口ごとの使い分け」の短い節（表）を足す。既定出力 `provider/model` → 利用者への表示、pr-review-fix-loop の `--controller-model`、review-fix-planning の状況コメントの `MODEL_NAME`。`--model` の出力（`PI_MODEL` 単体）または省略 → pr-review の `prepare --model-name`。Quick Reference の `PI_MODEL` の備考「`MODEL_NAME` の正本」は、2 つの用途を混同させるので、用途が分かる表現に直す（「正本」という語は使わない）。When to Use の「レビューや成果物へ `MODEL_NAME` を記録する」も、使い分けの節を参照する形にしてよい
  4. `.pi/APPEND_SYSTEM.md` の「モデル名の抽出」: pr-review の prepare では `--model-name` を省くか `--model` の出力を渡し、既定出力 `provider/model` を渡さないことを 1 項目足す。変えるのは「## モデル名の抽出」節だけで、`## Response Persona` 以降は 1 バイトも変えない（`tests/scripts/test-instructions.bash` が sha256 で凍結している）
- 書き方: 日本語表現は AGENTS.md の「日本語表現」に従う（「正本」「契約」を使わない）。既存の文体（体言止め・短文）に合わせる。上の 4 ファイル以外を変えない
- テストの要否: 書かない。文書の文言の固定値テストは AGENTS.md の F に当たり、照合・拒否の挙動は変えない（既存テストが守る）。代わりの検証は Task 2
- 検証（担当が実行する）: `git diff --stat` が上の 4 ファイルだけ、`bash scripts/check-layout.sh` が成功、`bash tests/scripts/test-instructions.bash` が成功、`uv run --locked pytest .agents/skills/pi-model-name/tests -q` が成功
- commit メッセージ: `docs: distinguish Pi display model name from pr-review prepare model id (#429)`

## Task 2: fake の Pi 環境での確認（司令塔）

- 担当ファイル: なし（記録は SESSION の下）
- 内容: Issue の再現スクリプトと同じ形で、`PI_PROVIDER=openai-codex PI_MODEL=gpt-6.1-sol` と `fixture-provider/fixture-model` の環境で、既定出力・`--model` の出力・省略・不一致値の `observed_model('pi', …)` を実行する。`PI_PROVIDER`・`PI_MODEL` をそれぞれ欠いた環境で省略経路が拒否されることも確かめる。改訂した文書の手順（省略、`--model` の出力）がどちらも成功することを、文書の該当箇所と照合する
- 予約の既存挙動: 既存テストの私有 Git fixture と実 `reserve_review()` を使い、一時的な実行で「予約 → `observed_model('pi', <既定出力>)` の照合失敗 → 予約 1 件のまま・review state 未作成 → 同じ fixture の再予約は拒否」を確かめ、続けて改訂した手順の値（省略、`--model` の出力）では照合が成功することを同じ環境で確かめる。一時的なファイルは SESSION の下に置き、実予約・過去の記録に触れない
- 既存テスト: `uv run --locked pytest .agents/skills/pr-review/tests .agents/skills/pi-model-name/tests .agents/skills/review-fix-planning/tests/test_run_roles.py -q`、`bash tests/scripts/test-instructions.bash`、`bash scripts/check-layout.sh`
- テストの要否: 書かない（一時的な実行で確かめ、結果を PR に書く）

## 実行予算

- Issue 全体の能動時間の予算: 4 時間（Issue の見積もり上限）。phase の目安: Spec・Spec レビュー 45 分、Plan 15 分、Task 1 の依頼と取り込み 45 分、Task 2 の確認 20 分、PR 作成 15 分、ループ 3 サイクル ×（レビュー 45 分＋計画・修正 30 分）
- worker の期限: `implement` の役割の期限 90 分。無進捗の打ち切りは runner の既定に従う
- 再試行の上限: Task 1 の `retry`・`rejected` は合わせて 2 回まで（初回を含めて 3 回）。Task のレビュー指摘の修正の依頼は 2 回まで
- checkpoint: Task 1 の取り込み後（差分が 4 ファイルに限られるか）、Task 2 の後（受け入れ基準の全項目）
- 縮小・切り出し・方法変更の候補: `.pi/APPEND_SYSTEM.md` の変更を落とす（Pi の pr-review は SKILL.md を読むので、pr-review 側の修正だけでも手順どおりの実行で照合失敗は起きない）

## contingency（代替策）

- Task 1 の担当が `failed` で止まったら、その Task で止まる（司令塔が引き取らない）
- 担当の変更が 4 ファイルの外に及んだら取り込まず（`rejected`）、範囲を明示して依頼し直す
- Task 2 で、文書の手順どおりの経路が拒否されると判明したら（helper の前提が Spec と違う）、文書側の記述を実際の挙動に合わせる最小修正を ledger に残して続ける。helper の変更が必要になる場合は意味が変わるので止まる
- base が前進したら issue-to-pr の 2 章 6 の前進追随に従う
