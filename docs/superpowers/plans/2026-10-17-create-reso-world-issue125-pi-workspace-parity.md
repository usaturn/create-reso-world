# pi workspace parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #125 の pi 関連ファイルを agent-workspace の現行版へそろえ、共有拡張の登録が消える不具合を解消する。

**Architecture:** Spec の固定 SHA のファイルをコピーし、pi 導入節だけを置き換える。setup と pytest は移植元と同じ配置にする。host networking・既存のワールド運用・現行の subagent 制限は保つ。

**Tech Stack:** bash / zsh、Node.js、Python（uv）、pytest、bubblewrap、pi、VS Code Dev Containers。

**Spec:** `docs/superpowers/specs/2026-10-17-create-reso-world-issue125-pi-workspace-parity-design.md`

## Global Constraints

- 状態 `draft`。実行許可は `/skill:issue-to-pr #125`、内容の承認ではない。確認待ちにせず PR まで実行し、マージしない。
- SOURCE: `usaturn/agent-workspace` `715d98168ab60011a98a42476ffea2759d4866d7`。snapshot は `/workspaces/reso-world/tmp/agents/issue-125.srg4whc3/source`。
- DOC_ROOT / CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-125-pi-workspace-parity`。base `76f1098af9f07388f4c10d55786ea9d726654171`。
- `PLANNOTATOR_REMOTE=0`、`PLANNOTATOR_PORT=19432-19441`、`forwardPorts` は 8000 と 19432〜19441。host network と uv の設定は維持。
- 利用者の HOME・ADC・バックアップを変更しない。本物の install / remove・モデル通信・rebuild は行わない。
- コピー対象・削除対象・例外は Spec D-1〜D-9。非 pi の導入処理と凍結済み Spec / Plan は変更しない。
- テストで source bash の削除変数には `${VAR:?}` と引用・`--` を付ける。文書や設定値だけを写したテストは作らない。

## Review Focus

- 登録済み context7 / Plannotator を rebuild 相当の再実行で失わない → Task 1 の追加状態遷移テスト。
- custom agent dir・BOM・manifest のみ残存・削除後の再一覧失敗 → Task 1 の移植元 MCP テスト。
- ADC の保存パス・明示パス・相対 agent dir と子の cwd の違い・OAuth 非消費 → Task 1 の移植元 Vertex テスト。
- readonly auth overlay で settings / sessions / lock の永続化を阻害しない → Task 1 の実 bwrap テスト。
- host network での待ち受けと port range、文書の stale path → Task 2 の実拡張の offline probe・構造と参照の検査（設定値を転記したテストは追加しない）。

---

## 実行方式・予算・記録

- 方式: `executing-plans`。2 Task が導入節・setup の参照を共有するため inline で順に変更する。調査・builder check は独立委譲済みで、最後に `sp-review` の branch review を1回行う。モデルは tool の役割設定に従い、一時 override を指定しない。
- 能動時間予算: 100分（準備20、実装30、全検証・review30、公開20）。2026-10-17T16:06:36Z に計測開始。ユーザー待ちは無し。
- ledger: `/workspaces/reso-world/tmp/agents/issue-125.srg4whc3/budget.jsonl`。実装の brief / BASE / Ruling / 検証は同ディレクトリの `progress.md`。worktree 内に未コミットの作業記録を作れないため、SDD helper の `.superpowers/sdd/` の代わりにここへ記録する。
- worker: 同期 role API は途中停止不可。レビュー・builder は1件ずつ同期で待ち、出力の session path と終了を確認する。目安10分、保存枠2分、無進捗5分。ただし停止 API が無いため、これは強制停止の宣言ではなく報告・checkpoint の目安。実装と検証も foreground で終わるまで待ち、timeout で kill しない。
- retry: 同一の信頼性失敗は1回まで。安全失敗は0回で全停止。レビュー dispatch の引数不足は修正済みだが、同じ不備のまま起動し直さない。
- checkpoint: 準備・Task 1・Task 2・レビュー・PR の各境界、50% / 100%、worker失敗直後。100%で延長せず停止報告。
- contingency: 実 bwrap / pi内部APIの不整合は `systematic-debugging` で固定SHAと環境を比較し、原因を特定して差分例外に記録する。解消できない失敗は公開せず停止。実機操作が必要な確認は当初から利用者向けchecklistとし、成功扱いしない。無関係な source 機能を取り込んで解消しない。

### Task 1: ランチャー・setup・pi 導入節・回帰テストの共通化

**Files:**
- Copy: Spec の11ランチャー・共通ヘルパ・tier・モデル・setup4本・MCP/settings。
- Modify: `.devcontainer/install_beforehand.bash`。
- Copy tests: `.devcontainer/test-pi-superagents.bash`・`test-pi-openai-codex.bash`、`tools/devenv_migration/tests/test_pi_mcp_adapter_migration.py`・`test_pi_vertex_launchers.py`。
- Create: `.devcontainer/test-pi-migrations.bash`、`tools/devenv_migration/tests/test_pi_shared_packages.py`。
- Delete: Spec の pigou / cleanup / pi_json / 旧setup / 旧cleanupテスト。

**Interfaces:**
- Consumes: SOURCE の固定SHA、既存 `step` / `fail` / `ensure_user_writable_dir`。
- Produces: `scripts/setup_pi_superagents.zsh [--if-absent]`、11本の launcher、導入節の `install_pi_extensions` / `remove_pi_mcp_adapter` / `remove_pi_distill` / `remove_pi_lens`。Task 2 が文書からこれらを参照する。

**テスト要否:** 必要。shell の入出力・共有設定保持・認証overlay・処理の失敗が対象。移植元の既存テストを先にコピーし、RED を確認してから実装する。

- [x] 移植元の2 pytest と2 bash を持ち込む。bash の削除ガードを適用し、設定値転記だけの `test_opencode_go_tiers_use_opencode_go` の定義・呼び出し・専用 `tier_model` を省く（他で使わない場合）。既存の構造と共有設定の保護検査は維持する。
- [x] 追加テスト `test_rebuild_preserves_shared_packages` を書く。登録済み/未登録の2条件で fake pi が list / install / remove を JSON に保存し、実 pi 節を隔離 HOME・fake npm・fake zsh で二度実行する。context7 / Plannotator の登録が残り、他パッケージも消えないことを検査する。fake remove は旧 cleanup が呼ぶ context7 撤去も再現し、失敗前の出力に秘密を含めない。
- [x] `uv run --no-project --with pytest python -m pytest -q tools/devenv_migration/tests/test_pi_mcp_adapter_migration.py::test_cleanup_accepts_bom_and_preserves_other_settings tools/devenv_migration/tests/test_pi_vertex_launchers.py::test_launch_reaches_pi_without_adc_preserving_args_cwd_environment_and_exit tools/devenv_migration/tests/test_pi_shared_packages.py`。Expected: 未実装の remove 関数・pigem ファイルと旧cleanupによる登録削除を理由に FAIL。依存の import error だけを RED の証拠にしない。
- [x] コピー対象を移植元から配置し、モードを維持。旧ファイルは明示パスで削除する。source pi 節（Installing pi → Installing DeepSeek Harness の前）を target pi 節（Installing pi → Installing the shared skills の前）へ置換する。STEP_TOTAL=30。uv の導入順を旧cleanupのためとする古いコメントだけ修正する。
- [x] 新入口 `.devcontainer/test-pi-migrations.bash` を作る。rootへcd後に `uv run --no-project --with pytest python -m pytest -q` で新規ディレクトリの3ファイルを実行する。100755 を設定する。
- [x] 新入口と移植した bash2本を実行。Expected: PASS（実モデルのlive checkは無効のまま）。差分の元ファイル比較、shell構文、`git diff --check` を確認する。
- [x] 明示ファイルだけ stage・commit。`progress.md` に BASE・RED/GREEN・例外と所要を記録する。

### Task 2: Dev Container・指示・文書の統合とブランチ公開

**Files:**
- Modify: `.devcontainer/devcontainer.json`、`.devcontainer/README.md`、`.pi/APPEND_SYSTEM.md`、`README.md`、`docs/maatlog-poc-porting.md`、このPlanの実行記録。

**Interfaces:**
- Consumes: Task 1 の setup4本・11 launcher・MCP設定・テスト入口。
- Produces: ローカル検証済みbranch、Spec / Planを含む `main` 宛てPR、利用者向けの実機checklist。

**テスト要否:** 設定・文書だけの新規テストは不要。既存検査・構文と参照先・全差分照合・必要なら実拡張のoffline probeで代える。

- [x] `containerEnv` と forwardPorts に Spec の値を追加し、host network・UV・8000・mountを維持する。
- [x] `.pi/APPEND_SYSTEM.md` の「サブエージェントの起動」の冒頭2項目を現行APIの説明へ。その他の制限・ペルソナは保持する。
- [x] source README の「pi のモデル定義とランチャー」から次の DSH 節の直前を取り込み、Plannotator local mode・Windows転送・既存設定・共有先・source Issue番号・テスト入口・このrepoに無いTypeSafe参照を調整する。旧cleanupの節を現在の撤去説明へ置換し、上部のrebuild/手動導入手順のsetup参照とlauncher数も直す。無関係な節は保持する。
- [x] ルート README のpi MCP説明をcontext7も含むものへ更新。`docs/maatlog-poc-porting.md` は過去の確認結果を消さず、#125が変更した決定と現行手順を明記し、実行可能な手順を新しいものへ更新する。
- [x] `git grep` で凍結Spec/Plan以外の旧setup / cleanup / pigou参照を確認する。歴史の説明は明示して残し、実行手順に古い参照を残さない。
- [x] 全検証: `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts`。Expected: 全て終了0。移植元との一致ファイル・差分例外を記録する。
- [x] 実 Plannotator を隔離・offlineで確認できるなら loopback / port fallback / HTTP review submission を確認。Windows・rebuild・実モデルは未検証のままchecklistへ。
- [ ] 明示ファイルをcommit後、`sp-review` に `Review scope: branch`、upstream `code-reviewer.md`、base/head・Spec/Plan・Review Focus・検証・Rulingを渡す。レビューは読み取り専用、テストは実装担当が実行する。Important/Critical は1回の修正passで対処し再発テストが必要なら RED→GREEN、文書のみなら参照と差分検査を実施する。
- [ ] Issue状態・競合・remote予約を再確認。secret scanの返したSHAをそのままbranchへpushし、`gh pr create --repo usaturn/create-reso-world --base main --head feat/issue-125-pi-workspace-parity`。本文に `Closes #125`、決定理由・方式理由・検証・時間内訳・例外・未検証を記す。
- [ ] #125に実機checklistをコメント。Spec/Planはdraftのまま結果を追記してコミットし（公開前に行う）、実行許可と承認を区別する。Herdrをcompletedにし、PR・branch/worktree・文書の絶対パス・所要を報告する。

### Task 3: F-1 の安全修正（利用者の明示指示による再開）

**Files:** `.devcontainer/test-pi-openai-codex.bash`、新規 `.devcontainer/tests/pi-launcher-install.bash`、新規 `tools/devenv_migration/tests/test_pi_installer_isolation.py`、既存 `.devcontainer/test-pi-migrations.bash`、Spec/Plan。

**テスト要否:** 必要。切り出したshellの実行範囲・失敗分岐・filesystem/network隔離を実行して確かめる。文言検査は書かない。

- [x] RED: 実Codexテストをread-only root/private tmp/network namespaceと外部コマンド拒否stubの内側でのみ実行する回帰テストを追加。旧版がfake npxに到達して失敗することを観測し、実download/cleanupは行わない。
- [x] helperで開始/終端の存在・重複・順番を検証し、揃ったときだけbufferを出力。終端はtargetのshared-skills。抽出したlauncher配置/tier setupだけを専用HOMEでbwrap隔離して実行。Codexテストはhelperを呼ぶ。
- [x] 欠落・重複・逆順で出力/実行無し、正しい範囲の実行、範囲外のtail不実行、書込拒否/network不通をbehavioral fixtureで検証。入口へ新pytestを加える。
- [x] GREENと全体検証を同期実行。最初のREDと安全修正後の実行結果は別ログへ保存する。危険な旧版を隔離無しで再実行しない。
- [ ] F-1修正をcommitし、停止を挟んだ安全修正なので差分に限定した独立re-reviewで境界を確認する。元のbranch review全体をやり直さない。
- [ ] Issue/競合を再確認し、scan済SHAのpushと元のPR計画を続行する。実機未検証と過去の安全停止/影響不明もPRに明記する。

再開の実行予算: 元の100分のうち前run約46分と再開準備約6分を差し引き48分。準備/修正15分、回帰/全体検証15分、限定review/公開18分。ledgerは同sessionの`recovery-budget.jsonl`。旧budget.jsonlの安全失敗を消さず保存し、利用者が明示許可した異なる安全な検証方法だけを別runで記録する。新しい安全失敗は即停止、信頼性は1回まで。任意sp-reconは結果無しで返ったため成功扱いせず、同じ呼出しを繰り返さずcontrollerの読み取り調査へ変更した。

## 実行記録

準備: parent無し、競合無し、先行修正マージ済み。基準検証は bash 32本・layout・pytest 625件すべて終了0。Spec builder-checkの指摘3件を解決し、Specを `0a9e734` にコミット。Task 1 を `a24dc66` にコミット。Task 2 は文書・設定を反映し、全検証成功（bash32本、layout、pytest625件、migrations149件）。Plannotator は設定範囲が占有中だったため一時ポートでloopback・fallback・日本語Markdown・合成承認を検証（45123占有→45124、終了0）。初回branch reviewでF-1を検出して安全停止。その後、利用者の明示指示によりTask3を実行。隔離した実テストのRED→GREENと8件の回帰、全体32bash/layout/625pytestの再検証を確認した。安全修正差分の限定re-reviewと公開は未実施。
