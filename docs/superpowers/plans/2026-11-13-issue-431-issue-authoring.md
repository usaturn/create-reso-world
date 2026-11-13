# Issue #431: issue-authoring 移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. issue-to-pr の implement_task.py で指定担当へ逐次依頼する。

**Goal:** create-reso-world で新規 Issue 案・元本文を保持した整形案・実測値を扱う評価案を安全に作る。

**Architecture:** 指定コミットの shared format と3 helper を移植し、対象解決と実行環境だけを移植先に適合させる。投稿案の確認、hash、競合・秘密検査、journal、元本文の保存を維持する。

**Tech Stack:** Python >=3.14、pydantic >=2.12,<3、ルート uv.lock、pytest、GitHub CLI、既存 Gitleaks。

**Spec:** `docs/superpowers/specs/2026-11-13-issue-431-issue-authoring-design.md`

## 管理と実行許可

状態: draft。利用者の `$issue-to-pr #431 --merge ...` の実行許可に従う。内容承認とは区別する。Spec と同じ branch、PR に保存する。

## Global Constraints

- 移植元は `usaturn/agent-workspace` のコミット `6e71fae4d25f217b23ce2409517cf602437a3cbf`。実行時に移植元 checkout を必要としない。
- `projects.toml`・`repository-ownership`・`.agents/projects/<name>.md` は持ち込まない。
- 対象は `--repo owner/repo` で明示し、常設親と採用済み台帳を既存 resolver で確認する。不在・不一致・未登録を別対象へ切り替えない。
- 見出し・ラベル・metadata・実行記録・評価コメントは `.agents/issue-format.md` に定義する。
- 投稿案を提示した後の利用者の承認だけを publish の根拠にし、非対話では下書きで止める。
- Gitleaks の版は `.devcontainer/install_gitleaks.bash` の `GITLEAKS_VERSION` から読む。
- Python はルートの `uv run --locked` を使う。永続的な HOME 変更、実 GitHub 書込みの試験、CI 追加・有効化はしない。
- コミットするテストは S の代表例だけ。F/L は実コマンド・構造確認・diff で代える。追加テストには防ぐ損害と理由を記す。
- 元本文・管理ブロック・archive を削って整形を成功させず、未計測を 0・失敗・成功のいずれにも置き換えない。

## 受け入れ基準

動作環境は本 Dev Container とルート uv.lock。実入力は日本語を含む複数行、CRLF、コードフェンス・HTML コメント、目標が2件で1件だけ実測ありの評価。防御範囲は承認後改変、元 Issue の競合、秘密情報、未登録 repo、誤った Issue/PR、元本文の欠落、壊れた抽出記録。実 GitHub の書込み、world 作業、既存 Issue の一括移行は対象外。

Spec A1-A6 の本文とこの節を実装担当・Task レビュアー双方の brief に同じ形で渡す。Task 3 の統合担当が、対象解決→共有書式→draft→verify→publish 判定と評価コメントの共有入力を条件単位で確認する。

## Review Focus

- 移植元の repo 名・登録方式が残り、別対象を選ぶ経路: Task 1 の境界テスト。
- scanner が検出しないまま成功する経路、検出時の書込み: Task 2 の canary/secret テスト。
- 承認前後に本文・タイトル・ラベルや draft が変化する経路: Task 2 の改変・競合テスト。
- archive と管理対象のある本文が再整形で欠落する経路: Task 2 の復元テスト。
- コメント取得失敗・未計測を成功に数える経路: Task 2 の抽出テストと Task 3 の評価シナリオ。

## 実行方式・所有ファイル

実装担当は `--implement` 明示値の `pi_openai-codex_gpt6-terra_xhigh`。各 Task を implement_task.py で1つずつ実行し accept 後にレビューする。Task レビューは agent-runner の専用読み取り role で `claude-code_opus_default` に依頼する。PR 後の3レビュアーは利用者指定の inspect をそのまま使う。最終全体レビューは --merge の第1サイクルで代え、Task レビューを省かない。

ファイルは全て新規。既存 pyproject.toml、uv.lock、scripts/check-layout.sh は現状で足りるため変更予定なし。Spec/Plan の記録は controller が管理する。移植元の対象24ファイルは `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/upstream/` に Git blob hash 照合済みで置かれている。

### Task 1: 共有書式と対象の解決

**Files:** `.agents/issue-format.md`、`.agents/scripts/issue_format.py`、`.agents/scripts/tests/test_issue_format.py`。

**Interfaces:** 移植元の `load_rules(repository: str, *, root: Path = ROOT) -> Rules`、`check_issue`、`write_metadata`、`compose_comment`、`extract_block` とモデルを維持する。`Rules.repository` は検証した正規化 repo、`Rules.name` は説明用の名前。`root` は書式を読む作業ツリーで、採用済み台帳の親ではない。既存 `agent_tmp.resolve_main_root(anchor)`、`superpowers_context.resolve_context('review-workspace', ...)`、通常ツールの `load_active_registry`/identity を使用する。meshy は検証済み親の external/resoloop-meshy だけを code_root として共通 resolver に渡し、返却先が固定パスの常設 checkout であることと origin=usaturn/resoloop-meshy を呼び出し側で確認する。resolver は変更しない。任意 CODE_ROOT を追加しない。

**テスト:** S。誤対象・metadata の欠落・壊れたブロックの成功扱いを防ぐ。移植元3テストを適合させ、対象解決の正常系/未登録拒否を代表1件で検証する。meshy 固定経路の正常系と、別 checkout・origin 不一致の拒否も実入力で確認する（誤対象への書込み防止）。共通 resolver の個別組合せの重複テストは作らない。

- [ ] 移植元テストと対象解決のテストを先に配置し、create-reso-world の正常系・未登録拒否・metadata 保持の期待結果が実装前に満たされないことを確認する。 import 不在だけで S の証拠とはせず、移植後の環境適合前の失敗も確認する。
- [ ] 共有書式と helper を移植し、登録方式を上記インターフェースへ置換する。ラベルの説明・例を移植先の領域に合わせ、既存スキルが新書式に対応済みとの記述を避ける。
- [ ] `uv run --locked pytest .agents/scripts/tests/test_issue_format.py -q` を実行し、正常系と拒否の両側が通ることを確認する。CLI `labels --repo usaturn/create-reso-world` で表を読み込めることを確認する。
- [ ] `git diff --check`、該当 Python の構文検査を行い、明示パスだけを commit: `feat: port shared issue format and repository resolution`。

### Task 2: 投稿・整形・抽出 helper と保護テスト

**Files:** `.agents/skills/issue-authoring/scripts/publish_issue.py`、`reshape_issue.py`、`extract_issues.py`、`.agents/skills/issue-authoring/tests/test_publish_issue.py`、`test_reshape_issue.py`、`test_extract_issues.py`、`.claude/skills/issue-authoring`。

**Interfaces:** Task 1 の shared format の API を使用する。移植元 helper の CLI と出力 status を維持する。`Scanner.pin_file` の既定は移植先 install_gitleaks.bash。リンクは `../../.agents/skills/issue-authoring`。追加依存は不要。

**テスト:** S。誤投稿・漏洩・競合上書き・本文や記録の消失を防ぐ既存テストを移植する。秘密検出時に書込0件、hashを変えない正常な投稿、元本文復元、壊れた metadata と正常 Issue を同時に保持する観測を揃える。1つの守りは代表1件で、文言・一覧・help の固定テストは作らない。

- [ ] テストを先に移植し、fake GitHub と fake scanner を create-reso-world に合わせる。秘密の見本は実行時に生成し、ソースに検出される値を残さない。
- [ ] helper を移植し、Gitleaks の pin ファイル・実行例を適合させる。canary、redact、設定上書き排除、draft hash、競合、非対話、journal、再送防止を維持する。Task 1 のファイル変更が必要なら勝手に範囲を広げず結果に理由を返す。
- [ ] `uv run --locked pytest .agents/scripts/tests/test_issue_format.py .agents/skills/issue-authoring/tests -q` を実行。改変・競合・秘密・非対話で書込0件、承認済み相当の正常入力では期待する fake 書込が生じることを確認する。
- [ ] 相対リンクを作り、明示パスを stage して `bash scripts/check-layout.sh`、`git diff --check`、構文検査を実行する。
- [ ] commit: `feat: port issue publishing reshaping and extraction helpers`。

### Task 3: 3 モードの手順・シナリオ・統合確認

**Files:** `.agents/skills/issue-authoring/SKILL.md`、`agents/openai.yaml`、`references/authoring.md`、`references/reshaping.md`、`references/evaluation.md`、`evals/` の移植対象一式と今回の評価手順。Task 1/2 の helper は読み取りのみ。

**Interfaces:** Task 2 の実 CLI で create/update/comment を保存し、reshape prepare/build/verify、extract の出力を読む。未計測は `EvaluationResult.achieved=null`、actual/gap に理由を持たせる。手順の実行例はルート `uv run --locked`。入力と出力 directory を分ける。

**テスト:** 新しい固定文言テストは不要（F/L）。スキルの無し/ありの行動比較と実 helper の操作結果で検証する。データ保存・未計測を守る既存の S テストは Task 2 に置き、同じ守りを docs 用テストで重ねない。

- [ ] controller がスキル無しの現行 HEAD で、同じ3モードの依頼を1つの外部評価に渡す。実 GitHub 書込み禁止、入力は固定 fixture と fake CLI、結果は SESSION。保存された案の有無と観測した挙動を記録する。
- [ ] 指定元の手順・agent 定義・評価シナリオを移植し、repository-ownership/projects.toml/個別 project 文書に依存する手順を既存境界へ置換する。未実装のモードや過去の評価を今回の成功と記さない。
- [ ] 後片付けは agent_tmp mkdir と AGENTS.md のガードを使い、存在しない agent_tmp rm を案内しない。承認待ち・途中停止・非対話の保存物を消さない。
- [ ] 日本語複数行の新規案、元本文と管理対象を含む整形差分、実測1件/未計測1件の評価案を、fake GitHub で実 helper から各1件作成して記録する。controller が条件 A1-A6 と保存物を照合する。
- [ ] controller がスキルありで同じ3モードの依頼を1回評価する。実 helper の結果、案の保存、未計測、承認待ちと fake 書込0件を確認し、無しの結果と比較する。実行例・参照・相対リンクも確認する。
- [ ] `uv run --locked pytest .agents/scripts/tests/test_issue_format.py .agents/skills/issue-authoring/tests -q`、`bash scripts/check-layout.sh`、`git diff --check` を実行し、commit: `docs: add issue authoring workflows and validation scenarios`。

## 要件・Task・検証の対応

| 条件 | 担当 | 証拠 |
|---|---|---|
| A1:3モードの案 | Task 2/3、controller統合 | 実CLIの保存物・preview・差分 |
| A2:承認/改変/競合/秘密/非対話 | Task 2 | fake GitHubの書込記録、正常系/拒否のテスト |
| A3:情報保持 | Task 1/2 | 元本文復元、管理対象保持、verify |
| A4:未計測 | Task 1/3 | evaluationモデル、評価案の actual/gap/achieved |
| A5:ルート実行と配置 | 全Task、controller | 必須検証とログ |
| A6:対象解決 | Task 1 | 共通resolverの親正常系/未知拒否 |

## 必須検証と公開

最後の commit 後、clean な HEAD で `uv run --locked pytest -q`、`bash scripts/check-layout.sh`、`git diff --check` を実行する。argv・終了コード・ログ・HEAD・固定 base を checks.json に記録する。必須コマンドは Plan commit 直後に SESSION/verify-cmds.json と resolve_base.py に固定する。Actions は無効のまま。scan-before-push と base 再照合後に PR を作り、`Closes #431` を使う。実環境での3モードの fake 検証で完了し、rebuild後や実投稿を完了条件に追加しない。

## 実行予算

全体の能動時間は480分。準備・設計/Specレビュー60分、3 Taskと各レビュー180分、統合・公開30分、最大3サイクルのPRループ210分を目安にする。workerの期限は実装90分、設計/Spec各30分、Taskレビュー/PR inspect各45分。モデルを暗黙変更しない。

Taskの NEEDS_CONTEXT/BLOCKED/rejected は文脈を補って同一担当へ1回まで再依頼。failed と安全の失敗は即停止。レビュー修正は SDD の上限内で行い、未解決の重大問題を成功としない。Spec再レビューは helper が要求したときのみ最大1回。スキルの行動評価は Terra で無し/あり各1回（1回に3モード）、結果形式・起動失敗の再試行はしない。新規実モデルの追加評価は具体的な失敗があっても最大1回とし、理由を ledger に記録する。

runner が期限と停止確認を管理する。予約枠は末尾5分を保存用に見込み、無進捗は10分ごとに確認、2回変化がなければ報告する。追加の途中停止は宣言していないため生存中のworkerを独自にkillしない。検証コマンドには途中停止を適用しない。

記録は `/workspaces/reso-world/tmp/agents/issue-431.0zsmult7/budget.jsonl` と同 SESSION の `sdd/2026-11-13-issue-431-issue-authoring/progress.md`。phase境界・50%・100%・失敗直後に checkpoint。runner cleanup前にidentity、所要時間、verdict、accept、検証を保存する。成果記録・レビュー ledger を最終報告まで保持し、残すパスを報告する。

## contingency（代替策）

- 初回の環境差は元の意味を保つ最小修正で対応し、担当範囲を変える必要があれば controller が記録して同じ担当へ再依頼する。
- 共通 resolver が想定と違う場合は無効化・独自許可リストで迂回せず原因を確認する。対象の意味や安全境界を変更する必要があれば停止する。
- 共通設定を変えずに既存 pytest と layout を使う。構造上不足すると分かった場合だけ必要最小限の変更を計画へ記録する。
- 実モデル失敗を self 実装や fake 成功で置換しない。残りは未完了として報告する。
- base 前進は issue-to-pr の未push条件付き復帰と必須再検証だけで追随する。push後の移動は停止する。
