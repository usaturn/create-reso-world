# Issue #183 / PR #182: DSH成果受け渡しの修正計画

- 状態: completed（修正・検証と公開準備を完了）。2026-10-19の「Issue #183を解決する形でPR#182を修正」の実行許可に基づく。
- Spec: `docs/superpowers/specs/2026-10-19-create-reso-world-issue116-dsh-native-write-policy-design.md`。
- CODE_ROOT=DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-153-pr-review-v2`。PARENT_ROOT=`/workspaces/reso-world`。
- 旧公式API待ちの計画は上記SpecのB+G案へ変更する。新たな有料モデル起動、設定変更、mergeは行わない。

## 実行予算

review-fix-planningの修正でありIssue予算ledgerの対象外。目安90分（設計15、並行実装30、統合/実DSH確認20、1回の自己レビュー/回帰/公開25）。実装担当は共有worktree内へ書くため強制中断しない。検証は同期で終了コードを待つ。信頼性の同一失敗は原因を修正して再実行し、状態/成果を監視する。模擬provider実DSHの各試行には90秒の期限を設け、完了・停止を確認する。付随調査を増やさずSpecの必要条件を優先する。

## Task 1: DSH全体の隔離とrunner回収（担当runner）

- [x] 旧版で兄弟metadata書込・diskreceipt・任意grant・非canonical outputのREDを確認。
- [x] 共通固定path、outerbwrap/private tmp/PID namespace、必要RO mount、perattempt RWだけを実装。
- [x] DSHの外部sandbox_write_pathsを拒否。diskreceiptを採用しない。停止/redactionは維持。
- [x] native相当のfake CLI、innerbash、/tmp配置、子孫停止/timeout、secret処理を同期pytestで確認。
- テスト必要: OS境界、停止、入力/結果処理の実行挙動を守るため。実DSHはコミットするテストに使わない。

## Task 2: 子outboxと親保存（担当helper）

- [x] 旧版で固定draft照合前書込のREDを確認。
- [x] 固定scratch/session、子記録、親lock無しsnapshot、native outboxをprepare/completeへ接続。
- [x] 親は固定state/pathと安全file読込、digest/Identity/Request/HEADを照合し同じbytesを親専用sessionのbackupへ保存。子Gitは一切実行せずtrusted bundleから親Gitを作り直す。
- [x] 正式run記録/cleanupを親に限定し、失敗の記録/残存先も維持。
- [x] symlink/FIFO/hardlink/別attempt/任意draft、停止未確認、digest変化、HEAD変更、正常pair/cleanupを検証。
- テスト必要: 保存・削除・パスの安全条件と後退防止。文書は構造・参照・diffで検証。

## Task 3: 証跡・統合・実物native確認（担当controller/検証補助）

- [x] producer拒否全文、call/result対応、両outboxへのnative成功証跡を検証する関数をTDDで追加。一般adapter分類は変えない。
- [x] fake正常/拒否・readエラー回復・不正/不足ログ・shellだけの成果の採用拒否を検証。
- [x] localhost模擬provider + network namespace + 実DSHでwrite/read/edit→complete→親save/cleanupを確認。新fixtureを使い旧失敗記録を触らない。
- [x] Task1の固定path/RWとTask2の実操作が一致することを統合で確かめる。正式run記録、外側state/exit/stop/payload/pair/cleanupを記録。
- テスト必要: 拒否履歴とnative証拠の解析。実DSHは手動検証のみ、追跡テストはfakeだけ。

## Task 4: 回帰・自己レビュー・公開（担当controller）

- [x] 関連pytest、`uv run --locked pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run --locked python -m tools.agent_runner --config .devcontainer/agent-runner.toml check`、diff確認。
- [x] 反証/PR全体/検出力の自己レビューを1回。致命的指摘を修正し影響する検証だけ再実行。再レビューしない。
- [x] ガードを外した隔離コピーで中心となる負例が失敗することを確認。
- [x] Spec/Planの証拠とPR説明を確定。秘密検査済SHAのpushと関連Issue投稿の結果は、コミット後のPR状況コメント・最終報告へ記録する。
- テスト追加不要: このTaskは前3Taskの実行証拠と構造/参照/公開結果を照合する。

## 実行記録

着手時にPR HEAD `0d1cd19`を確認し、最新main `5adc16c`と旧DSH計画commit `5f33749`をmergeした。子担当はtools/agent_runnerとpr-reviewで分離。共通pathと秘密値置換の範囲はcontrollerが接続を確認する。


### 実行中に確定した検証

- runner: agent_runner全体997 passed（75.44秒）。fresh PID namespaceの子孫PIDテストはhost PIDを取得するよう直し、変更した停止関連11 passed（5.24秒）。DSH関連258 passed。実物のnamespace/RO/RWを使ったfake CLIで検証した。
- 証跡: native成果2枚、readエラー回復、拒否履歴、欠落/重複/不正ログ、リンクを使ったログ差し替えを18 passedで検証した。新関数が無い旧版ではREDだった。最終追加のJSONL Unicode区切り負例はRED→LFのみで分割する修正後19 passed（0.06秒）。
- 実DSH: 0.2.0-rc.2を追加network namespace内のlocalhost模擬providerで1回起動。4.24秒。native write/read/edit/read/write全てcompleted、runner success / exit0 / stop_confirmed=true、子staged→親payload.success、正式pair/実行記録success、cleanup success。範囲外変更・秘密値残存・残存PIDなし。子session/promotion session/worktree/HOMEの削除とedit後の本文保存を実確認。有料モデルの判断品質・元の並行受入は未検証。
- ガード対照: `/tmp/review-fix-planning.atgOPe` の使い捨てworktreeへ差分を写し、outer attemptをRWへ変えた版で1負例FAIL。単一linkガードを除いた版は元fixtureでは別のdigest拒否で隠れたため、有効staged bytesをhardlinkするfixtureへ直した。修正fixtureの正常版PASS→単一linkガード除去で誤採用を検出してFAIL。両ガード復元後2 PASS、使い捨てworktreeとディレクトリは削除済み。
- 親は子のGitを実行しない。hook/core.fsmonitor/.git pointerの3条件を毒入れしても親側コマンド呼出しが子Gitを使わないことと正式保存成功を確認。outboxは各1回読んだbytesを保存し、読込後の差し替えを採用しない。cleanup失敗は正式pairとrunのfailed_at=cleanupを保持する。

- 実DSH確認後の変更は親cleanupの呼出順・link負例fixture・JSONLのU+2028/U+2029扱い。native実行・隔離・成果pathは同じであり実DSHの証拠を引き継ぐ。変更した親処理はhelper全体回帰、Unicode扱いは上記19件で検証する。


### 自己レビュー後の修正（同じ1回の指摘への対応）

- R1はrunner担当: /tmp親入力のnative/bash可視性とROをRED/GREENで確かめる。
- R2/R3はhelper担当: JSON構造の単一異常・同batch継続と、Codex親/DSH子Identityの分離をRED/GREENで確かめる。親のglobal環境を変更しない。
- controllerは経路表/証拠を統合し、最終変更に関係する回帰を通す。再レビューはしない。PR全体担当は最初のレビューの未読部分のみ読み終える。

- 自己レビュー前の全体回帰: `uv run --locked pytest tests/skills .agents/skills .agents/scripts tools` は2821 passed（702.87秒、exit0）。shell33 PASS、layout/config PASS。最後のR1/R2/R3変更に影響するrunner/helperは修正後に全体を再検証し、無関係な移行/他skillの証拠はこの回帰を引き継ぐ。

- R1最終: runner全体1016 passed（88.24秒）。追加受入18件はnative/inner両方のsnapshot/bundle/.gitignore読込、書込拒否、実require_parent_root、host/tmp兄弟不変、不正descriptor/リンク/FIFO/親rootの拒否、一般prompt維持を確認。RO mountを外す対照ではparent_visible=Falseを再現した。

- 最終コードの実DSH確認を、R1/R2/R3とJSONL変更に合わせて1回追加（合計2回、有料モデル呼び出し0）。5.4148秒、watcher5.987秒。/tmpのfresh snapshotへのnative readとinnerbash prepare、write/read/editと候補保存、raw U+2028/U+2029、合成Codex親環境下のDSH子Identity保存を確認。runner success/exit0/stop_confirmed=true→staged→親payload.success・run_record.success・正式pair・cleanup成功。外部変更/秘密値残存/残存PIDなし。主要14fileは起動前後のSHA256一致。検証記録は `/workspaces/reso-world/tmp/agents/issue-183-native-check.nzp5v2y6/integration-result-r2.json`。

- R2/R3最終: helper全体333 passed（368.76秒）。不正first/正常second、正常2attempt、有効Codex親rollout、既存cleanup失敗・通常Codexモデル照合を含む。最後の自己レビューは反証・PR全体・検出力の1回で3件採用、すべて対応。PR全体担当は同じ回の未読部分を読み終え、追跡28ファイル（削除は旧全文）と新規3ファイルを確認した。修正後の再レビューはしていない。

- 最終shell回帰33 PASS、layout/config/構文/diff確認すべて成功。実DSH証跡用の一時/tmp snapshotは保存copyとのSHA一致確認後に削除し、残す証跡を親の `tmp/agents/issue-183-native-check.nzp5v2y6/` にまとめた。

### 所要

修正着手06:13 UTC、検証・公開準備完了06:53 UTC、約40分（並行時間は二重加算しない）。主な経過は設計・並行実装約15分、統合回帰・自己レビュー約12分、指摘修正・最終検証約13分。担当内訳: runner実装10分/対照3分/追加修正8分、helper実装・検証21分/追加修正・検証10分、native準備・初回12分/最終確認6分、自己レビューは反証8分・全体15分・検出力7分。レビュー修正の再レビューは行っていない。
