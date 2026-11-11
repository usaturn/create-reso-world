# PR #405 レビュー修正（サイクル 1）: with_keys の設定の読み込みと checkout の一致

## 管理・実行許可

- 状態: `completed`（結論 1。作成時は `draft`）
- 対象: https://github.com/usaturn/create-reso-world/pull/405（`feat/issue-401-runner-key-wrapper`）、Issue #401。元の Spec は `docs/superpowers/specs/2026-11-11-issue-401-runner-key-wrapper-design.md`、Plan は `docs/superpowers/plans/2026-11-11-issue-401-runner-key-wrapper.md`
- 実行許可: issue-to-pr の `--merge`（利用者の 2 回目の指示 `/issue-to-pr #401 --merge ... --assign implement=pi_xai_grok4_xhigh --assign inspect=pi_xai_grok4_xhigh,pi_openai-codex_gpt6-sol_xhigh`）による PR 修正ループ（pr-review-fix-loop）の完遂。この PR の承認済み実装修正と、修正不要時の `finalize.py` によるマージ・関連 Issue の更新の実行許可として扱う
- サイクル: 1、現行 HEAD `d480c833a771c254c36460292964ab64992f8bee`、base `030fa7917b2d6d73f586feede902bd09fdf92a2a`
- planner: `claude-opus-5-5`（claude-code）
- 確認済みの一覧: `reviews/usaturn/create-reso-world/#405-feat-issue-401-runner-key-wrapper/verified/d480c833a771.json`（confirmed 3）

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `d480c833a771` | はい | Needs manual verification |
| `grok-4.7.md` | grok-4.7 | pi | `d480c833a771` | はい | Approve |

## 指摘の一覧と振り分け

| 判断 ID | 出典 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `gpt-6.1-sol#M-1@d480c833a771` | gpt-6.1-sol M-1 | 対応する | 下記 F1 |
| `gpt-6.1-sol#M-2@d480c833a771` | gpt-6.1-sol M-2、grok-4.7 M-1 | 対応する | 下記 F2 |
| `grok-4.7#I-1@d480c833a771` | grok-4.7 I-1 | 対応しない | 元の Spec の解析規則・診断の記述が、最終レビューの修正（`d2d39f31`）の後の実装・README より古い。Spec は設計の記録で、実装と README（利用者が読む説明）は一致しているので、そのとおりに進めて誤った結果になる経路が無い。致命的でない |

| `claude-opus-5-5-commit-334b1436ad4102f1d5483debc58a571a6a14550e#I-1@334b1436ad41` | 自己レビュー（self-review）I-1 | 対応しない | grok-4.7#I-1 と同じ（元の設計の Spec・Plan の記述が修正前のまま）。利用者が読む手順・README は揃っている。致命的でない |
| `fix-check#V-1@334b1436ad41` | 自己レビュー（fix-check）V-1 | 対応しない | 同上 |

件数: 解消済み 0 / 対応する 2 / 対応しない 3（うち 2 件は自己レビューの指摘）。

## 要件対応（元の Spec・PR の約束との照合）

| 条件（元の Spec・PR） | 今回の修正方針 | 観測する結果 | 検証方法 |
| --- | --- | --- | --- |
| 補う名前は runner の実効設定の全 agent の `env` の和集合（D2）。通常のシェルからの起動は今と同じに動く（目標） | F1: 名前の収集で担当の参照・重複の検査をしない | 後段が上書き後に受け付ける設定で wrapper が止まらない。補う名前の集合は変わらない | 下の F1 の表 |
| wrapper と helper・runner は同じ設定から名前を決める（D2、README・interfaces の「同じ checkout」） | F2: 手順の wrapper を後段と同じ checkout のものにする。別 checkout のときは `--template` を渡す規則を書く | 後段の雛形にだけある名前も補われる | 下の F2 の表 |
| 今の環境の値を上書きしない・allowlist の外を渡さない・実行しない・値を出さない（テスト 1） | 変えない | 既存のテストが通る | `uv run --locked pytest tools/agent_runner -q` |

共有条件: F1 と F2 はどちらも「wrapper が補う名前 = 後段が実際に使う設定の agent.env の和集合」という同じ条件に関わる。統合担当は controller（planner）で、修正後の HEAD で両方の再現（確認済みの一覧の V-1・V-2 と同じ入力）を流して確かめる。

## F1: 担当の上書きの前の検査で止まる（gpt-6.1-sol#M-1）

- 致命的である理由: 個人設定の `workflows.*.assignments` に、雛形から外した古い agent 名や同じモデルの重複が残っている利用者が、文書化された `--implement`・`--assign` で置き換えて helper・runner を起動すると、wrapper が終了コード 2 で止まり、issue-to-pr・PR 修正ループ・review-fix-planning・review-verify の主要な処理が止まる（雛形の agent の改名・撤去は #351 などで実際に起きている）。(a) 再現した誤動作（確認済みの一覧 V-1）
- 原因: `with_keys.py` の `needed_names` が `load_config(template, personal)` を担当の上書きなしで呼び、`Config` の検証（参照・重複）まで行う。後段は上書きを適用した最終形で検証する（interfaces.rst）。名前の収集に要らない検査を前段で行っている
- 修正方針: env 名の収集は、雛形と個人設定を後段と同じ規則で重ねた `agents` の `env` だけを読み、`workflows`（担当）の参照・重複の検査をしない。設定ファイルを読めない・`agents` の形が壊れているときは、今と同じく分類名だけを出して終了コード 2。担当・fallback の検証は後段に任せる

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| wrapper は後段が上書き後に受け付ける設定を拒否しない | `with_keys.needed_names`（全呼出元: issue-to-pr の 3 helper、`loop.py review`、`run_roles.py`、`dispatch.py`、CLI `run`） | 修正する | 古い担当名・重複モデルの個人設定で、wrapper 経由の `implement_task.py check --implement self` が 0 | 確認済みの一覧 V-1 と同じ 3 入力（retired・dup・self）を修正後の HEAD の隔離 worktree で実行 | `334b1436` の隔離 worktree: retired 0・dup 0・self 0（修正前 `d480c833` は retired 2 invalid_reference・dup 2 duplicate_model・self 0） |
| 補う名前の集合は変わらない | 同上 | 既に満たす（集め方だけを変える） | `test_with_keys.py` が通る、雛形だけの実行で同じ名前を補う | `uv run --locked pytest tools/agent_runner -q` | `334b1436`: 終了コード 0 |
| 壊れた設定は今と同じく止まる | 同上 | 修正する（形の誤りの扱いを保つ） | 構文の壊れた個人設定で終了コード 2、値を出さない | 一時 HOME の壊れた TOML で手動実行 | `334b1436`: 終了コード 2、`agent-runner configuration error: invalid_toml`（値なし） |

## F2: wrapper と後段で既定の雛形の checkout が違う（gpt-6.1-sol#M-2・grok-4.7#M-1）

- 致命的である理由: worktree を cwd・`SKILL_DIR` にして手順どおりに起動すると（雛形の agent を追加・変更する作業中の worktree が実在する。この PR 自体がそうだった）、後段の雛形にだけある agent の key は env ファイルにあっても届かず、ランチャー起動セッションで key を届けるというこの PR の目的が果たせない。README・interfaces の「同じ checkout の雛形を使う」は事実と違い、そのとおりに進めると誤った結果になる。(a) 再現（確認済みの一覧 V-2）、(b) 事実誤認の記述
- 原因: 手順が親の `$PARENT_ROOT/tools/agent_runner/with_keys.py` を `--template` なしで使い、wrapper の既定の雛形は自身のファイルの checkout、後段は自身のファイル（helper）か cwd（`python -m`）の checkout で決まる。起動の形が 2 つの checkout を組み合わせている
- 修正方針: 手順の wrapper のパスを後段と同じ checkout にする。`python -m tools.agent_runner`（リポジトリのルートを cwd にする）の例は `tools/agent_runner/with_keys.py`（cwd の相対パス）、`$SKILL_DIR/scripts/...` の helper（issue-to-pr・review-verify）は `$SKILL_DIR/../../../tools/agent_runner/with_keys.py` のように helper と同じ checkout から導く。`$TOPLEVEL` の helper（execution.md）と `loop.py`（ROOT）は既に同じなので変えない。README・interfaces・各手順の説明に「wrapper は後段と同じ checkout のものを使う。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す」と書き、「同じ checkout」の説明を成り立つ条件付きにする

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| wrapper が補う名前は、実際に起動する後段が読む雛形の agent.env から決まる | issue-to-pr SKILL.md の `review_design.py review`・`implement_task.py run`（と Spec レビューの段落） | 修正する | wrapper のパスが `$SKILL_DIR` と同じ checkout から導かれる | `git diff` と、修正後の HEAD の隔離コピーで V-2 と同じ入力（feature 側にだけある名前）を流す | `334b1436` の git archive の隔離コピーで `$SKILL_DIR/../../../tools/agent_runner/with_keys.py`（cwd は /tmp）が FEATURE_ONLY_TOKEN を補った。stderr に値なし |
| 同上 | review-verify `references/fix-check.md` の `dispatch.py` | 修正する | 同上 | `git diff` | `334b1436` の diff で `$SKILL_DIR/../../../tools/agent_runner/with_keys.py` に変わったことを確認 |
| 同上 | `AGENTS.md`・`.agents/monitoring-runtimes.md`・`tools/agent_runner/interfaces.rst`・`.devcontainer/README.md` の CLI `run` の例 | 修正する | cwd の相対パスの wrapper | `git diff`、V-2 の入力で cwd の wrapper が補う | `334b1436` の隔離コピーを cwd にした `tools/agent_runner/with_keys.py` が FEATURE_ONLY_TOKEN を補った。stderr に値なし |
| 同上 | review-fix-planning `references/execution.md`（`$TOPLEVEL` の wrapper と helper） | 既に満たす | 同じ `$TOPLEVEL` | `git show` で確認（確認済みの一覧 V-2 の statement_sites） | `334b1436` でも変更なし（`$TOPLEVEL` の wrapper と helper） |
| 同上 | `loop.py` の `review` の `next`（`ROOT` の wrapper と helper、保存した template を渡す） | 既に満たす | 同じ `ROOT`、template を明示 | 既存の pytest | `334b1436`: `uv run --locked pytest .agents/skills/issue-to-pr .agents/skills/pr-review-fix-loop .agents/skills/review-verify -q` 終了コード 0 |
| 「同じ checkout」の説明が事実と一致する | README・interfaces・手順の説明 | 修正する | 条件付きの記述 | `git diff`、`bash .devcontainer/test-readme.bash` | `334b1436`: test-readme 0。README・interfaces は「両方が同じ checkout のときだけ」の条件付きに変わった |

## テスト

AGENTS.md の「テストの採用基準」により、テストは足さない。F1 は壊れると wrapper の終了コード 2 とメッセージで止まる（L）。F2 は key が届かず agent が認証エラーで止まる（L）。確かめは確認済みの一覧と同じ再現を修正後の HEAD で流して行う。

## 同じ条件の再発と設計の見直し

この PR のサイクル 1 で、以前のレビュー修正の回は無い（判断の記録・Spec に記録が無い）。きっかけには当たらない。

## 結論・検証・自己レビュー

- 結論: 1（修正して既存 PR へ push）
- 修正の担当: `run_roles.py --phase implement`、`--template /workspaces/reso-world/.devcontainer/agent-runner.toml --assign implement=pi_xai_grok4_xhigh`（ループの `run_roles_options`）。runner が観測した担当は `xai` の `grok-4.7`（xhigh）、1256 秒、停止を確認。commit `334b1436ad4102f1d5483debc58a571a6a14550e`（変更 7 ファイル。テストの追加なし）を差分を確かめてから fast-forward で取り込んだ
- 実行した検証（`334b1436`、専用の worktree）: `uv run --locked pytest tools/agent_runner -q` 0、`uv run --locked pytest .agents/skills/issue-to-pr .agents/skills/pr-review-fix-loop .agents/skills/review-verify -q` 0、`bash .devcontainer/test-readme.bash` 0、`bash .devcontainer/run-tests.bash` 0、`bash scripts/check-layout.sh` 0、push の前の検査（`scan-before-push.sh`、13 commit）検出なし。F1・F2 の再現は上の表のとおり
- 自己レビュー: `run_roles.py --phase self-review` の 1 回（工程の記録に `pre_push_review` を予約）。割り当ては self-review・fix-check とも `self`（雛形の既定）で、司令塔が 2 つのサブエージェント（claude-opus-5-5）で同時に実行した
  - self-review（観点 2）: pr-review の非対話の入口で `334b1436` の PR 全体を再レビュー。Approve、active 1 件（`claude-opus-5-5-commit-334b1436ad4102f1d5483debc58a571a6a14550e#I-1@334b1436ad41`、Info: 元の Spec・Plan の本文が修正前の記述のまま）。保存: `reviews/usaturn/create-reso-world/#405-feat-issue-401-runner-key-wrapper/claude-opus-5-5-commit-334b1436ad4102f1d5483debc58a571a6a14550e.md`
  - fix-check（観点 1・3）: 主張 10 件すべて holds。F1・F2 とも修正前の HEAD で失敗し修正後で通る（検出力あり）。壊れた設定は修正後も終了コード 2。新しい指摘 `fix-check#V-1@334b1436ad41`（元の Spec・Plan の記述が修正前のまま）。保存: `verified/334b1436ad41.fix-check.json`
- 自己レビューの指摘の判定: I-1 と fix-check#V-1 は同じ内容（元の設計の Spec・Plan の記述が古い）。grok-4.7#I-1 と同じ理由（Spec・Plan は設計の記録で、利用者が読む README・interfaces・手順は修正後の形に揃っており、そのとおりに進めて誤った結果になる経路が無い）で「対応しない」。自己レビュー後の修正は無く、2 回目の自己レビューはしていない
- 未確認: 実プロバイダ・ランチャー起動セッションでの実機の観測（マージの後の確認。PR は Refs #401）。ruff・rstcheck は環境に無く実行していない
