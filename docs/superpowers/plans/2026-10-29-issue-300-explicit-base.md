# Explicit issue-to-pr base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 明示した origin の branch / SHA を分岐・検査・PR まで保持する。
**Architecture:** Issue 入力と対象 checkout の検証を分け、base の確定を helper に集約。scan は optional SHA pin を受け、後段の実 PR base の guard を保つ。
**Tech Stack:** Python stdlib / uv、Git、Bash、pytest、偽 gh / Gitleaks。
**Spec:** `docs/superpowers/specs/2026-10-29-issue-300-explicit-base-design.md`

状態: draft。実行許可は Spec のユーザ指示による。内容の承認は記録しない。
実行方式: SDD、3 Task を同期で直列実行。helper と scan は独立した責務、Task 3 が共有入力・順序・外部仕様の統合担当。
この run の base: `usaturn/create-reso-world` / `origin` / `main` / `5dc093cc2ed6855fb15353d70c1e8bb3b12d2151`。
SESSION: `/workspaces/reso-world/tmp/agents/issue-300.vmbh4kha`。
SDD: SESSION の `sdd/2026-10-29-issue-300-explicit-base/`。再生成キャッシュ以外を worktree に置かない。

## Global Constraints

- コード base は検証済み対象 repository の origin の完全な heads ref。未指定時 main。文書専用 base は create-reso-world / origin / main。
- base 移動・要求との矛盾・対象の不一致は停止。ブランチ新設、reset、force push、他者 worktree 変更は禁止。
- 後段の HEAD / 実 PR base / merge 第1親 / CI の guard を弱めない。
- 恒久テストは S のみ。文言・一覧・構文拒否だけの F/L や同じ守りの重複は増やさない。拒否には正常対照を残す。
- テストはローカル Git と偽 CLI。実 GitHub への試験書き込み、有料モデルのテスト起動、新しい Actions は禁止。

## 受け入れ基準（全 brief に同文を渡す）

動作環境は Linux Dev Container / uv / Git。実入力は `#N --base feat/plugin-v2`、等号形式、Issue 前の指定、未指定 main、非 ASCII branch、親/handoff が要求する branch。main と統合 branch に別の内容・履歴を用意し、同じ対象 repository / origin / ref / SHA が worktree・差分・scan・偽 gh PR 作成へ渡ることを観測する。存在しない branch、revision 式・別 ref、要求の矛盾、origin の取り違え、捕捉後の base 移動で誤った対象への書き込みを進めない。外部コードの文書は main に分離する。merge は既存の実 PR base guard と代表テストで照合する。対象外は新規統合 branch、別 Issue の実装、remote/repository 拡大、他者による同時更新を GitHub とローカルで一括ロックする保証。観測した移動は停止し、公開済み PR は自動で取り消さない。

## Review Focus / 要件対応

| 条件 | 担当 | 観測・証拠 |
|---|---|---|
| 入力と required base、対象 origin と SHA | Task 1 | 別履歴を持つ実 Git、異なる origin、禁止入力の正常対照 |
| SHA 固定 scan と base 設定 | Task 2 | 偽 Gitleaks の argv / GIT_ATTR_SOURCE、移動時に成功 SHA が出ない |
| 分岐→diff→scan→PR の同じ対象 | Task 3 | スキルの実行可能な手順を抽出して実行するローカルシナリオ |
| 外部コード / 文書の分離 | Task 3 | 独立した2 repository の branch / SHA / PR argv |
| 非 main の merge、安全 guard の維持 | Task 3 | finalize の代表正常例を非 main にし既存拒否例を維持 |

既存の world cwd / 対象 repository / options 拒否は既存テストを再実行。ループに base を新たに引数として渡さない。自然文の required base の抽出は controller の判断であり、helper は明示して渡された値だけを照合する。

### Task 1: 入力と origin base の確定

**Files:** Modify `.agents/skills/issue-to-pr/scripts/resolve_issue.py`; Create `.agents/skills/issue-to-pr/scripts/resolve_base.py`; Modify `.agents/skills/issue-to-pr/tests/test_resolve_issue.py`; Create `.agents/skills/issue-to-pr/tests/test_resolve_base.py`.
**Interfaces:** resolve_issue 出力 `base: str`（main 既定）, `base_explicit: bool`。resolve_base CLI `--checkout ROOT --repo OWNER/REPO [--base BRANCH] [--required-base BRANCH ...] [--expected-sha SHA]`; success JSON `{repo,remote,branch,ref,sha}`、failure exit 2 / stderr。`remote=origin`。枝の文字列検証は共通関数にしてよい。

- [ ] S テストを先に追加。`test_base_selection_preserves_explicit_input` は main と明示入力を実 resolver で通し、既存 merge/implement に混ざらないことを確認（単なる argparse エラーテストは不要）。
- [ ] `test_resolve_exact_origin_branch` はローカル bare remote と偽 git（remote get-url の応答だけを対応する GitHub URL にし、他は実 Git へ渡す）を用い、main と非 ASCII の統合 branch の実 Git SHA を独立に比較。`test_rejects_wrong_target_and_required_base` は origin / push URL 不一致と required の未指定・矛盾で取得前に止まることを、正常対照とともに確認。
- [ ] `test_base_cannot_select_other_ref_or_revision` は tag のみ・不存在・危険な ref を branch として扱わず変更が残らないことを確認。`test_base_movement_rejected` は取得後に remote を進め、expected SHA で拒否、保持されるローカル feature を確認。環境 GIT_* の取り違えは実装 module の代表 S テストで検証。
- [ ] RED を記録してから最小実装。--branch が @{-1} を展開するため、literal refs/heads の規則と branch の規則を照合する。checkout root・追跡対象・repo allowlist・origin fetch/push URL・完全一致 remote ref・commit の照合を行う。Git エラーに認証情報を含む URL をそのまま表示しない。
- [ ] `uv run --locked pytest -q .agents/skills/issue-to-pr/tests/test_resolve_issue.py .agents/skills/issue-to-pr/tests/test_resolve_base.py` と `git diff --check` を実行。環境隔離は既存 conftest を尊重。ログは SESSION に置く。
- [ ] 明示ファイルを stage して `feat: resolve explicit issue base from verified origin` で commit。

### Task 2: scan の base SHA pin

**Files:** Modify `scripts/scan-before-push.sh`, `tests/scripts/test-scan-before-push.bash`.
**Interfaces:** `bash scripts/scan-before-push.sh [-C ROOT] [--base origin/BRANCH] [--expected-base-sha SHA]`。指定時は fetch した SHA と一致し、検査後も remote の同じ refs/heads を確認。未指定の既存挙動は維持。

- [ ] S の代表テストを追加し RED。安定した非 main branch で実 Git 履歴と偽 Gitleaks を使い、範囲と設定が main でないことを確認。捕捉後に base が動いたケースと検査中に動くケースで標準出力 SHA が空、成功にならないことを確認（異なる操作順の guard）。
- [ ] 最小実装。expected SHA は完全 SHA、文字列のまま revision として解釈しない。既存の範囲・base 設定・除外禁止・版チェックを保持。remote / branch を option として解釈しない。
- [ ] `bash tests/scripts/test-scan-before-push.bash`、`bash -n scripts/scan-before-push.sh`、`git diff --check`。ログを SESSION に保存。
- [ ] `fix: bind pre-push secret scan to expected base SHA` で commit。

### Task 3: スキル手順・通し検証・merge 照合

**Files:** Modify `.agents/skills/issue-to-pr/SKILL.md`, `.agents/skills/issue-to-pr/evals/validation.md`; Create `.agents/skills/issue-to-pr/tests/test_base_workflow.py`; Modify 必要な代表例のみ `.agents/skills/review-fix-planning/tests/test_finalize.py`。呼出手順の同じ入口を示す現行ファイルに限り最小の例修正を許可（履歴 Spec/Plan は変えない）。
**Interfaces:** Task 1/2 の CLI と JSON。スキルに実行可能なシェルブロックを置き、テストはそれを取り出して実行する（ソースの文言照合ではない）。入力変数は quoted 引数と Bash array で扱い eval しない。

- [ ] writing-skills / skill-creator を読む。旧手順（追加ガイダンス無し）のシナリオを実行して停止または main 固定になる証拠を SESSION に残す。有料モデルによる行動比較ではなく、実行手順の比較として報告する。
- [ ] 統合 S テストの RED。main と異なる統合 branch、別 repository の文書 main を用意し、branch 元・diff・scan の範囲・PR argv が一致することを実 Git と偽 gh / Gitleaks で観測する。危険例・base 移動で公開が進まないことも、担当 helper の既存 S テストと重複しない境界で確認する。
- [ ] 最小限の SKILL.md 更新。オプション、出力、required base の判断と根拠、取得結果保存、worktree/diff/scan/PR の値、再確認の順、PR 作成後の照合と公開済み資源保持、外部文書 main 分離、実 PR base の検証記録と finalize 連携、停止報告を一貫させる。Issue resolver に loop_args として --base を渡さない。
- [ ] finalize の代表正常テストを main と異なる実 PR base に変えて、同じ branch と SHA が merge guard を通ることを確認。既存 stale base/head/第1親の拒否ケースを再実行し、守りの重複テストを追加しない。
- [ ] 新手順で同じシナリオを通す。evals/validation.md に旧/新の観測・限界を記録。skill-efficiency-check は警告を理由なく全体改稿する根拠にしない。
- [ ] `uv run --locked pytest -q .agents/skills/issue-to-pr .agents/skills/review-fix-planning/tests/test_finalize.py`、skill の参照確認、`git diff --check`。`feat: carry pinned base through issue-to-pr workflow` で commit。

## 実行予算

能動時間360分。準備20、Task 1 35、Task 2 20、Task 3 35、全体検証・公開25、ループ3×（レビュー45＋修正20）=195、余裕30。実機モデル起動は本番レビューの指定3名×上限3サイクルと、SDD の調査1・builder check1・各実装/レビュー1・最終レビュー1（修正時は該当スキル上限）のみ。テストにはモデルを起動しない。
共有 worktree の実装・検証は同期で待ち、期限による kill をしない。調査/レビューも今回は同期 tool で完了待ち、目安10分、kill を宣言しない。runner の本番 inspect は45分の既定期限。無進捗は monitoring-long-tasks / pi の同期制限どおりに扱う。信頼性失敗は同一原因1回まで再試行、安全失敗は即停止。checkpoint は各 Task 境界、公開前、50%/100%、失敗直後。

## contingency（代替策）

最初の RED が API 前提違いなら意味を保つ fixture 修正を ledger に記録。必要なら自然文の大規模手順追加ではなく helper への移動を選ぶ。base 移動は勝手に再確定せず停止し、差分と必要な再検証を報告。必要な helper が後段で非 main を扱えなければ最小修正を計画へ反映し、main に置換しない。未検証条件を残して PR 完了やマージ成功にしない。予算100%で停止し handoff。

## 統合・公開（controller）

- [ ] Task ごとのレビュー後、Spec→Task→証拠を条件単位で照合。最後の whole-branch review と必要な1回の修正。
- [ ] README の3入口: `bash .devcontainer/run-tests.bash`; `bash scripts/check-layout.sh`; `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`。最後の commit の clean HEAD と各 argv / exit / log、finalize checks-file を SESSION に記録。
- [ ] Issue / 競合を再確認し、親 checkout の scan-before-push.sh が返す SHA だけを push。PR は main 宛て、Closes #300。Spec/Plan はこの PR に含める。
- [ ] 親 checkout のループを指定 inspect で実行し、finalize 以外では merge しない。private Actions は待たない。結果・関連 Issue の観測 state・時間・残存資源を報告。
