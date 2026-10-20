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
