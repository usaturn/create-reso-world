# Issue #187: 隔離した担当の checkout 監査と消えた worktree の回収

## 管理・実行許可

- 状態: `draft`
- 対象: usaturn/create-reso-world、https://github.com/usaturn/create-reso-world/issues/187
- 利用者の指示: `$issue-to-pr https://github.com/usaturn/create-reso-world/issues/187 --merge`
- 実行許可: 通常の設計判断を推奨案で決め、実装、検証、commit、秘密情報検査、push、PR 作成、最大 3 サイクルのレビュー修正ループとその finalize によるマージまで進める。文書の内容の承認とは扱わない。
- CODE_ROOT / DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-187-checkout-audit`
- PARENT_ROOT: `/workspaces/reso-world`

## 意図と原因

runner の fingerprint は checkout の変化を検出するが、書き込み元は特定できない。このため、無関係なセッションの編集と、消えた worktree の登録が、担当の成果の受け取りを妨げる。担当が試行の外へ書けないと確認できる場合に限って必須監査を狭め、ほかの担当では従来の拒否を保つ。

## 仕様

1. trusted adapter の capability `confined_writes` は既定 false とし、プロセス全体を bubblewrap で囲う既存の DSH adapter だけ true にする。設定ファイルや prompt から解除できる監査除外リストは作らない。Codex の workspace-write/read-only という名前だけでは、監査を限定する根拠にしない。
2. 対象 workflow の全外部担当と全 fallback の adapter が隔離を保証する場合に限り、必須監査を main checkout と依頼元 checkout に限定する。自分の試行は既存の成果検査で検証する。外部担当がいない構成、未対応 adapter、保証を持たない担当との混在は全登録を必須監査にする。
3. 全登録の snapshot と終了後の比較は続ける。必須対象の診断は既存の `checkout_audit` / `outside_changes` に返し、それ以外の診断は新しい `unrelated_checkout_audit` に返す。どのパスが変わったかは残し、書き込み元を断定しない。必須対象の監査不能は成功にせず、監査対象の登録を取得できない場合も止める。
4. 起動前の判定も同じ policy を使う。issue-to-pr の implement_task、review-verify の dispatch、review-fix-planning の run_roles をそろえる。fallback と role の投影後の設定を使い、予約・有料起動より前に判定する。DSH の既存の self-review 制限等は変更しない。
5. 回収手順は、移動と消失を分け、所有する run の停止・登録との対応・rebuild の時点・ロック・未保存の内容を照合する。移動には個別 repair、消失には所有者が確認した 1 件だけの remove を案内する。一括 prune、force、postStart の自動回収は行わない。今回存在する他セッションの登録も削除しない。

## 受け入れ条件

- C1: 隔離担当の実行中に別の linked worktree が編集されても、必須監査は成功し、その変化は無関係な checkout の診断として残る。
- C2: 隔離担当では無関係な消えた worktree の登録が起動を妨げず、main・依頼元の監査不能や変化は拒否を保つ。
- C3: 非隔離担当、非隔離 fallback、外部担当のない構成では、従来の全登録監査を維持する。
- C4: DSH の実プロセスを使う偽 CLI が、main、依頼元、隣の checkout、共有 .git、host の /tmp に書けない。試行内の許可された出力は作れる。実モデルや実認証情報は使わない。
- C5: 3 つの受け取り入口で起動前と結果判定が一致し、既存の停止確認・成果検査を維持する。
- C6: 消失登録の回収手順を使い捨て Git リポジトリで確かめ、対象外の登録を残す。手順への参照が存在する。

## 対象外

全 adapter の sandbox 化、監査できない必須対象の許容、無関係なセッションの書き込み元の推定、既存の登録の掃除、rebuild 自体の実行、有料モデルによる隔離評価は行わない。非隔離担当では Issue の A 案の制限が残る。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| D: 隔離を保証できる DSH だけ限定監査 | A: 全て直列運用、B: controller の除外指定、C: 無条件に限定 | 並行作業を安全に許容できる範囲を明確にする。B/C は書き込みの見逃しを防げない | 通常の設計判断の委任。隔離の対照試験が通らなければ公開しない |
| E: 所有者の照合と個別回収の手順 | F: 起動時の自動回収 | prunable だけでは所有権・停止・消失を確認できない | 他者の登録は削除しない |
| self による inline 実装 | Task ごとの外部担当 | 設定検査で agents=[self], fallback=[], self=true。同じ監査 API の逐次変更が中心 | 雛形の既定の適用。利用者の担当指定ではない |
| PR 作成後に既定のレビュー修正ループ | PR 作成のみで終了 | 利用者が --merge を明示した | check-options 成功。max_cycles=3、assign={}、template=PARENT_ROOT/.devcontainer/agent-runner.toml、config=null |

ループの解決済み担当は review.inspect=[pi-gpt, devin-swe, dsh-ccd, cursor-grok47]、fix.implement=[claude-opus]、fix.self-review=[self]、fix.fix-check=[self]（全 fallback=[]）。これらは設定の既定の適用であり、利用者の明示指定ではない。

## PR #210: 1 回目のレビュー修正

対象 HEAD は `b3251620d40cf8428c25b4167c96c2b12792f2bd`。現行の Spec はこの文書だけ、Plan は同日の issue-187 Plan であり、同じテーマの追加文書は作らない。実行許可は既存の --merge 指示のレビュー修正を使う。判断担当は gpt-6.1-sol / codex。

4 レビュアーの入力は同一 HEAD で、候補 JSON の validate / check-pair は成功。`verified/b3251620d40c.json` の V-1 は挙動の再現、V-2 は文書の静的照合で confirmed。関連 17 テストも成功（3.64 秒）。

| 出典 | 分類 | 理由と見直す条件 |
| --- | --- | --- |
| gpt-6.1-sol#M-1@b3251620d40c | 対応する | 通常の `dispatch.py --assign self` が、残る未使用 DSH fallback の保証で全登録監査不能を回避し exit 0 になる。手順どおりの操作で誤った拒否結果になるため (a)。実 loader / dispatcher の 4 条件で再現 |
| SWE-2-Max#I-1@b3251620d40c、commandcode-deepseek-deepseek-v4.1-flash#I-1@b3251620d40c | 対応しない | 監視・fix-check・issue-to-pr の限定条件の説明漏れ。共通 interfaces.rst と実行時の必須拒否は存在し、説明漏れによる危険な操作は再現していない。該当説明だけに従って誤操作が成立する証拠、または利用者の名指し指示があれば見直す |

原因は、起動される外部一次担当の有無を調べず、起動されない fallback も候補に含めたことである。全一次担当が self なら fallback の capability を確認せずに全登録監査を選び、外部一次担当がある場合の全候補と全 fallback の隔離保証確認を保つ。設定 loader の fallback 継承を変える案は、他の通常の上書き挙動を変えるため採らない。以前のレビュー修正はなく、再発・回帰による設計見直しの条件には該当しない。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 全 self は fallback に関係なく全登録必須 | load_config の担当上書き → workflow_checkout_scope → require_auditable_workflow | 修正する | DSH fallback 1 件・2 件でも消失登録を拒否 | 実 loader に self 上書き、未使用 fallback を保持して preflight を実行 | 修正前は通過（RED 3 件失敗、0.54 秒）。修正後は `test_self_override_does_not_use_retained_fallback_as_confinement_evidence` が成功 |
| 出力先の作成前に監査不能を拒否 | dispatch.py --assign self → preflight → 出力保存 | 修正する | exit 1 / environment、出力先なし、登録と内容を保持、外部コマンドなし | 実 CLI main と使い捨て Git の状態・出力先・試行数を比較 | 修正前は exit 0 / state=self、試行 0、出力先あり（RED）。修正後は `test_self_assignment_keeps_all_registrations_with_a_retained_dsh_fallback` が成功 |
| 外部一次担当があれば保証確認を維持 | 共通 policy → runner 起動 → 3 入口の結果判定 | 既に満たす | 隔離された一次担当 + self の混在は限定、非隔離 fallback は全登録 | 既存 policy と 3 入口のテスト、混在ケース | `test_confined_primary_keeps_targeted_scope_with_a_retained_fallback` と関連 1351 件が成功（163.92 秒） |
| self を起動担当として扱わない入口の既存制限 | implement_task の self 拒否、run_roles self-review の DSH fallback 拒否 | 既に満たす | 既存の拒否を保ち、監査のために制限を緩めない | 各入口の既存テスト | 関連 1351 件に含めて成功 |
| 残る登録の回収は所有者の照合が必要 | 実在する他セッションの登録 | 対象外 | 削除・repair・prune しない | helper が監査不能で止まれば環境停止として記録 | 利用者の指示を受け、`/tmp/pr-review-190-60a7527d/worktree` と `/tmp/pr-review-193-d26990b1/worktree` の登録だけを `git worktree remove --force` で個別に remove した。登録は 19 件で、事前監査が成功することを確認 |

テストは実 loader / policy / dispatcher を実行し、拒否と正常側・状態保持を検査するため必要。追加したテストは 4 件（policy の parametrize 2 ケース、限定監査の維持 1 件、dispatcher 1 件）。文面やモデル名を写すテストは追加しない。修正対象は `tools/agent_runner/checkout_policy.py` と、挙動テスト（`test_checkout_policy.py`、`review-verify/tests/test_dispatch.py`）に限定した。

検証は修正後 HEAD で、関連 1351 件（163.92 秒）、全体 pytest 3501 件（1494.82 秒）、Dev Container 33 件、`scripts/check-layout.sh`、`git diff --check` が成功した。初回の RED は新規テスト 3 件が失敗し、対照 1 件は成功した。`rstcheck` は環境に無く、RST は変更していないため未実行。自己レビューと fix-check は `run_roles.py` の起動前監査が既存の checkout_missing 2 件で通らないため未実施だったが、利用者の指示を受けて prunable な登録 2 件を個別に remove し、起動前監査が 19 登録で成功することを確認した。利用者の判断により、この回は自己レビュー・fix-check・マージを行わない。M-1 の修正・検証・commit・push までを完了とし、PR は未マージのまま残す。
