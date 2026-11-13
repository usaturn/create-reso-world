# Issue #365 残作業: agent-runner.toml のコメント文面を AW 現行に揃える

- 状態: `draft`
- 対象: https://github.com/usaturn/create-reso-world/issues/365 （親 #349、key `runner-catalog`）
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-365-comment-alignment`
- branch: `feat/issue-365-comment-alignment`
- base: `usaturn/create-reso-world` / `origin` / `refs/heads/main` / `bcff80ed97c70b31cb30afd3dfb6f9264594efb2`
- 実行許可: 利用者の 2026-11-14 の指示「https://github.com/usaturn/create-reso-world/issues/365 残作業を実行してください」。issue-to-pr の委任（通常の設計判断は推奨案で決め、検証・commit・push・PR 作成まで継続。質問・Spec/Plan 確認・実行方式の選択は追加で尋ねない）。`--merge` 指定は無く、PR 作成で終える。マージはしない。
- 実行方式: `superpowers:executing-plans`（implement は既定の `self`。同じファイルの逐次コメント編集で 1–2 Task の小変更のため inline）。

## 意図・現状・比較元

PR #432（merged 2026-11-13、merge commit `c120e59f`）でカタログの値・改名・並び・README 移行説明・スキル説明は完了した。残るのはコメントの文面差 3 点（TOML 冒頭の古い導入注記・roles の呼出元実ファイル名の省略・AW コメントの要約による文面差）と、個人設定の旧名参照の確認である。本 Spec は completed Spec（`2026-11-13-issue-365-runner-catalog-design.md`）から通常の実装を再開せず、この残作業を新しい範囲として扱う（Issue 本文「エージェントに任せる事項」の指示どおり）。

比較元は着手時に GitHub contents API で取り直した AW 現行 `.devcontainer/agent-runner.toml`:
- AW main commit `36c321cbda93a055849ed0165cfac2b064f8e3e3`（2026-11-13T14:35:55Z）
- blob `69e841dd229f1ca3cfcf0ba5d092b58bd45b5945`、11322 bytes、sha256 `9d0b6fbc9a5c76f4947e270a6934ec1965710fa463d1c43b17fedb39fc603c58`
- SESSION の `aw-agent-runner.toml` に保存。この run ではこの内容を比較基準として固定し、作業中の再取得による範囲拡大はしない。

着手時の再照合で判明した現状（旧 baseline の差分表は snapshot であり、現行と比べ直した）:
- CRW 現行 TOML は 21 agent。AW 現行は 27 agent（CRW の 21 + Antigravity CLI の `agy_*` 6）。`agy_*` は AW main が旧 baseline（`f65dd6a2`）から進んだ後に追加された新しい agent。
- 値の差は既知の意図的差分（Sol / OpenCode Go DeepSeek の `env = OPENCODE_API_KEY`、review の `after_run --project .`）だけ。agent の値・roles の値・並びは PR #432 で揃済み。
- 残るコメントの文面差: 冒頭注記、Devin、roles 期限、spec-review、design-review、after_run、inspect、issue.implement。これらは CRW が AW のコメントを要約した、または古い注記を残したもの。
- Ollama / alibaba / piaq のコメントは CRW が #408・#402・#401 で書き起こした CRW 固有の説明（key 導出・key ガード・env allowlist・現行 tier・duplicate_model 詳細）。AW の短いコメントの要約ではない。
- fix.assignments のコメント（codex 拒否注記）は CRW 固有。`run_roles.py:157` の `reject_codex_review_agents` が `fix` の `self-review`・`fix-check` への codex 割当を起動前に拒否する（`run_roles.py:311`）。AW の TOML にこのコメントは無い。
- 個人設定 `~/.config/agent-runner/config.toml`（966 bytes）は `schema_version = 1` とコメント例のみで、旧名（`claude-code_opus_default`・`pi_openai-codex_gpt6-sol_max`）の参照も定義も無い。移行は不要。
- 編集対象 4 ファイルの旧名参照は README の #305 履歴表と移行節のみ（受け入れで許可済み）。TOML・スキルに現行参照は無い。

## 範囲

変更する追跡ファイルは次の 2 つと、この Spec・Plan のみ。

1. `.devcontainer/agent-runner.toml`: コメントの文面のみ。agent / role / workflow の値・並び・`schema_version` は一切変えない。
2. `.devcontainer/README.md`: 個人設定の移行節の古い環境記述（1608 行付近）の更新と、`agy_*` agent を追加しない理由の追記。命名表・既定割当・Ollama agent の節（#408 所有）は変えない。

### 除外（変更しない）

- adapter・runner・監査・key 導出・exec・配置処理・runtime 文書・個人設定・共有認証。新しい agent・alias・自動移行・CI の追加。
- `agy_*` 6 agent の追加（対象外「新しい agent の追加」。CRW の `tools/agent_runner/adapters/` に agy adapter が無い）。
- #407 の Alibaba tier 修正の取り込み。過去の Spec・Plan・レビュー記録の agent 名書き換え。
- Ollama の agent 2 つ・`claude-ollama-exec`・`install_beforehand.bash`・`test-claude-ollama-exec.bash`・Ollama key 導出（#408 所有）。
- `claude-code_sonnet_*`・`[workflows.fix.assignments.implement]` の値（#353 完了済み・現行どおり）。

## 設計

### TOML コメント（AW 原文を基本に CRW の事実・規約を保持）

値は変えず、次のコメントだけを AW の文面に揃える。AW の Issue 参照は CRW の文書慣例で `usaturn/agent-workspace#N` と書く。

1. **冒頭**: AW の 2 行を基本にする。1 行目「汎用の非対話エージェント実行ツール。資格情報の値は書かない。」。2 行目は AW の「agent 名の規則: …参照。」の形に、CRW の実節名「agent の命名と同一モデルの比較」（README の `agent-catalog-names` アンカー）を当てる。CRW の install_beforehand 説明（個人設定は雛形に重ねて読む / install_beforehand.bash は個人設定が無いときに agent-runner-personal.toml を置き雛形は写さない）の 2 行は保持する。古い #150・#151・#153・#155・#157 の注記と interfaces.rst 参照（README の agent-runner 節が案内する）は落とす。
2. **Devin**: AW の 2 行（「Devin の SWE-2 は…名の effort の段に置く。」「2 つは同じ model_key で同じモデルとして扱う（同じ役割に並べられない）。」）。
3. **roles 期限**: AW の 2 行に `usaturn/agent-workspace#616` を付け、呼出元の実ファイル名を名指しする（「fix-check は呼び出し側（review-verify の dispatch.py・review-fix-planning の run_roles.py）が 1800 秒に切り詰める。」）。両ファイルは CRW に実在する。
4. **spec-review**: AW の 3 行に `usaturn/agent-workspace#848・#853` を付ける。
5. **design-review**: AW の 3 行に `usaturn/agent-workspace#861` を付ける。
6. **after_run**: AW の 1 行「PR レビューの後処理。ランナーの観測値を実行記録へ追記する。」。CRW の追加注記（個人設定は書き換えない / after_run = [] の caller は attach-runner を明示実行）は個人設定の例コメントと README が案内するので TOML からは落とす。`--project .` の値は維持。
7. **inspect**: AW の 4 行を基本に `usaturn/agent-workspace#565` を付け、#337 の経緯行（Command Code GOAT は契約終了のため既定から外す）を保持する。AW の 4 行目「#616 で利用者が個人設定で使っている構成に合わせた」は AW 固有の出自記述で、CRW の実個人設定には割り当ての上書きが無く事実と合わないため削除し、4 行目は「下の 3 人は指定が無いときの既定値で、性能の順位ではない。」とする（D9）。
8. **issue.implement**: AW の 5 行に `usaturn/agent-workspace#679` を付ける。`self` の値は維持。
9. **fix.assignments**: CRW のコメント（run_roles.py が使う担当・self の説明・codex 拒否注記）を保持する。参照 `#116` だけを `usaturn/agent-workspace#116` に直す。AW に無いコメントだが、CRW 固有の拒否挙動を説明する理由がコメント本文にある。

### 揃えない差分（理由をコメントか README に残す）

- 冒頭の agent 名参照は CRW の実節名「agent の命名と同一モデルの比較」を当て、install_beforehand の説明 2 行を保持する（設計項目 1。AW の節名「agent の命名規則」は CRW の README に存在しない。install_beforehand 説明は Issue 差分表が保持を指示）。
- Sol / OpenCode Go DeepSeek の `env = OPENCODE_API_KEY`（Pi の正式名・旧名からの引き継ぎ。README 記載済み）。
- review の `after_run --project .`（CRW に tools/devenv が無い。README 記載済み）。
- `[workflows.issue.assignments.implement]` の `self`（#391 の利用者決定）。
- Ollama / alibaba / piaq の CRW 固有コメント（#408・#402・#401 の key 導出・key ガード・env allowlist・現行 tier・duplicate_model 詳細。README の各 agent 節が理由を案内）。completed Spec の「意図的に揃えない箇所」を継承する。
- fix.assignments の codex 拒否注記（CRW の run_roles.py の挙動。コメント本文が理由）。
- inspect の 4 行目から AW 固有の出自記述「#616 で利用者が個人設定で使っている構成に合わせた」を削除（CRW の実個人設定に割り当て上書きが無く事実と合わないため。D9）。
- `agy_*` 6 agent の不在（対象外の新しい agent 追加。agy adapter 不在。README に理由を追記）。
- AW の Issue 参照を `usaturn/agent-workspace#N` と書く（CRW の文書慣例）。

### README

- 移行節の「この環境の既存個人設定は旧名の参照だけを持つため、マージ後に利用者による移行が必要であり、本変更では触らない。」（PR #432 時点の記述）を、着手時に確認した現行の状態（旧名の参照・定義は無く移行不要。実効 check/list で確認）に更新する。移行手順そのもの・履歴は残す。
- 命名節の exec agent 案内の近くに、AW の `agy_*`（Antigravity CLI）agent を追加しない理由（#365 の範囲は新しい agent の追加を含まない・agent_runner に agy adapter が無い）を短く追記する。

### 個人設定

実個人設定は変更しない（防御範囲）。着手時に旧名参照が無いことを確認済みなので、移行作業は発生しない。雛形単独（SESSION の空 config）と実効（実個人設定を重ねた）の `check`・`list` を実行して確認する。成功は設定の検査であり、認証や実サービス起動の成功を意味しない。

## 決定記録

| ID | 選択した案 | 検討した別案 | 理由 / 委任指示・停止条件 |
|---|---|---|---|
| D1 | 要約・古い注記のコメントを AW 原文に揃え、CRW の実ファイル名・参照規約・#337 経緯を保持 | ファイル全面置換、コメント現状維持 | 全面置換は key・after_run・#408 説明・codex 拒否注記を壊す。現状維持は残作業 3 点を解消しない。Issue「エージェントに任せる事項」が修正範囲と順序の決定を委任 |
| D2 | Ollama / alibaba / piaq の CRW 固有コメントは保持 | AW の短いコメントへ置換 | #408・#402・#401 の key 導出・tier・duplicate_model 説明は CRW の事実。completed Spec の「意図的に揃えない箇所」を継承。防御範囲「#408 の値を変更しない」 |
| D3 | `agy_*` 6 agent は追加せず README に理由を記録 | AW に合わせて agy agent を追加 | 対象外「新しい agent の追加は対象外」。CRW に agy adapter が無く run は unsupported になる。委任「AW 現行と差分表が食い違う場合は仕様の意味を保つ最小修正で進め判断と根拠を記録」。意味（除外範囲）は変わらない |
| D4 | fix.assignments の codex 拒否注記は保持し参照だけ規約どおり直す | AW に合わせてコメント削除 | CRW の run_roles.py:157/311 に拒否が実在する CRW 固有の説明。削除は有効な文書を失う。理由がコメント本文にある |
| D5 | 冒頭は AW 2 行 + install_beforehand 説明、古い注記は落とす | 古い注記・interfaces.rst 参照を保持 | Issue 差分表「AW の文面を基本にし install_beforehand の説明は残す。古くなった #150・#151・#153 の注記は落とす」。interfaces.rst は README が案内 |
| D6 | 個人設定は移行不要を確認し README の古い環境記述を更新 | 自動移行・alias・記述の現状維持 | 実個人設定に旧名参照が無いことを確認済み。防御範囲「実個人設定を変更しない」。古い記述は現行と不一致 |
| D7 | 新規恒久テスト無し。check/list・pytest・install-beforehand・layout・AW 差分比較で検証 | コメント固定値テスト | Issue「新しい恒久テストは追加しない（F / L）」。コメント文面は F。S の duplicate_model・env 境界は既存テストが守る |
| D8 | executing-plans で inline 実装（self） | subagent-driven-development / runner 担当 | implement は既定の self。同じファイルの逐次コメント編集で 1–2 Task の小変更。issue-to-pr 4 章の表どおり |
| D9 | inspect の AW 4 行目から AW 固有の出自記述「#616 で利用者が個人設定で使っている構成に合わせた」を削除 | AW 原文をそのまま写す / 行ごと削除 | CRW の実個人設定には割り当て上書きが無く、そのまま写すと存在しない上書きを根拠にする誤ったコメントが残る（S の「もっともらしいが誤った結果」）。節見出し「CRW の事実・規約を保持」と roles 期限で CRW 実ファイル名を要求した前例に沿う。builder check の質問 1 への裁定（委任範囲内の文面決定。利用者承認ではない） |

## 受け入れ基準

- **動作環境**: Ubuntu Dev Container、uv / Python の既存 locked 環境。リポジトリルート（worktree）から検証コマンドを実行できること。実 API・実モデルは起動しない。
- **実入力**: `.devcontainer/agent-runner.toml` の日本語複数行 TOML コメント、AW 現行ファイル（blob `69e841dd`）、旧名参照の無い実個人設定（`schema_version = 1` とコメント例のみ）、SESSION の空の一時 config。
- **防御範囲**: 実個人設定・key・ログイン・履歴・#408 の値（Ollama 定義・exec・key 導出）を変更しない。alias と自動移行は対象外。`check` の成功を認証や実サービス起動の成功と表示しない。`[workflows.issue.assignments.implement]` の `self`・`after_run` の `--project .`・`env` の `OPENCODE_API_KEY` を変えない。過去の Spec・Plan・レビュー記録の agent 名を書き換えない。agent / role / workflow の値・並び・`schema_version` を変えない。
- TOML のコメントが AW 原文を基本に揃い、CRW の差異（実ファイル名・参照規約・#337 経緯・codex 拒否注記・install_beforehand 説明・AW 固有の出自記述の削除）には理由がある。Ollama / alibaba / piaq のコメントと値は base から変わらない。
- `agy_*` agent は追加されず、README に追加しない理由がある。
- README の移行節の環境記述が現行の個人設定（旧名参照なし）と一致する。命名表・既定割当・Ollama 節は変わらない。
- 雛形単独（空 config）と実効（実個人設定）の `check`・`list` が成功し、既定割当に `duplicate_model` が無い。旧 Opus 名への現行参照が履歴・移行説明以外に無い。
- Issue 指定の検証コマンドが成功する。新規固定値テストは追加しない。
- ボードの子なので PR は `Refs #365` とし、マージ後に完了状態を記録する（この run はマージしない）。

## 検証入口

worktree を cwd にして:
- 雛形単独: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config <SESSION の空 config> check` / `list`
- 実効: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml check` / `list`（実個人設定を重ねる。読み取り専用）
- `uv run pytest tools/agent_runner/tests`
- `bash .devcontainer/test-install-beforehand.bash`
- `bash scripts/check-layout.sh`
- AW 現行との差分比較（`diff -u`）で、残る差分がすべて「揃えない差分」であることを確認する。
- 実 API を呼ばない。一時 config・ログは SESSION 内だけに置く。

## 依存・先行の証拠（着手時に再確認）

- #353・#408・#359・#347: closed completed（2026-11-14 再確認）。必要な変更は base に含まれる。
- #407: open だが claim・open PR は無く、直列化（#365 → #407）により本 Issue が先。tier 修正は取り込まない。
- 親 #349: open（ボード）。本 Issue は native Sub Issue（key `runner-catalog`）。
- 競合: 本 Issue の open PR 無し。前回 claim は PR #432 マージ後に解放済み。issue-365 の worktree・branch（local/remote）は残っていない。
- claim: `refs/heads/agent-claims/issue-365` / `e49e6e27e7e0de9be2aa65e3b0a2ced2473e8a4b`（base `bcff80ed` の tree から作った session-unique 空 commit）。着手コメント https://github.com/usaturn/create-reso-world/issues/365#issuecomment-6861318401 。
- 権限: write/triage あり、rulesets なし、main の branch protection は "Branch not protected"（404）、Actions enabled=false。