# Issue #337: Command Code GOAT の既定経路停止

## 管理・実行許可

- 状態: `completed`（内容承認とは区別し、下記の追加実行指示による確認・検証を完了）
- Issue: https://github.com/usaturn/create-reso-world/issues/337
- 利用者指示: `/skill:issue-to-pr` と `https://github.com/usaturn/create-reso-world/issues/337 --merge --assign inspect=claude-code_opus_default,devin_swe2-max_default,pi_opencode-go_deepseek4-flash_max`
- 許可範囲: 推奨案の選択、Spec/Plan、実装、非課金の検証、commit/push/PR、指定レビュー修正ループ内の finalize によるマージ。個人設定・キー・契約は変更しない。
- 固定 base: usaturn/create-reso-world / origin / refs/heads/main / `0d58ac76b3c364ec431a292c8bc41e58f57e933b`。親 Issue・要求 base・依存・既存 PR・予約なし。

## 目的と制約

契約終了した Command Code GOAT を通常の起動・レビューから外す。再契約用の provider、agent、ランチャー、tier、手動 setup、既存の安全テストは残す。通常配置は11本、手動再有効化用は2本と区別する。

## 決定記録・検討した別案

| 項目 | 選択した案 | 検討した別案 | 理由・委任または停止条件 |
| --- | --- | --- | --- |
| 既定レビュー | Sol/max、Devin、OpenCode Go DeepSeek/max | Command Code を fallback に残す／人数を減らす | 3人とDeepSeekを維持。同じ model_key の併記は duplicate_model。Issueの明示案を採用 |
| 配置 | postCreate の piccg/piccd install だけを除去 | provider/agent/tier/ソース削除 | 再契約時の明示利用を守る。LAUNCHERSと全ランチャーテストは変更しない |
| 説明 | README、setupと残すランチャーの自動配置コメントを整合 | READMEだけ直す | 実行処理は変えず古い案内を残さない。#305の過去表は維持 |
| 移行 | 利用者による割当・キーexport見直しを文書化 | 個人設定や実ファイルを自動削除 | 利用者所有の情報を守る。共有 ~/.pi と他のキーには触れない |
| 検証 | 既存テスト、設定読込、隔離HOMEの配置、無キーversion | 固定一覧の新規テスト／課金API | F/L の新規テストは追加しない。version成功は認証成功を意味しない |
| 実装方式 | self、executing-plans、2 Taskを直列 | Taskごとの実装委譲 | 小さく相互に関係する設定・文書変更。checkの既定 self、fallback=[]。指定ではなく既定の適用 |
| PR後 | inspectは利用者指定3人、最大3サイクル | 独自マージ／レビュアー変更 | check-options成功。max_cycles=3、fix.implement=claude-code_opus_default、self-review/fix-check=selfは既定の適用。失敗時は規定どおり停止 |

## 要件・防御範囲

1. 雛形単独と実際の個人設定を重ねた check/list が成功し、割当上書きが無ければ第三担当が `pi_opencode-go_deepseek4-flash_max`。commandcode agent 定義は残す。Sol/max、OPENCODE_API_KEY、model_key は変更しない。
2. 新しいHOMEで配置ブロックを実行すると通常11本を配置し、piccg/piccdは配置しない。他のインストーラ処理は実行しない。
3. pigod の version 経路を OPENCODE_API_KEY / OPENCODE_GO_API_KEY / COMMANDCODE_API_KEY を外して確認する。auth.json の内容・キー値は出力しない。実モデル応答と認証の有効性は対象外。
4. 全13本の既存ランチャー分離・引数・tierテストを維持する。
5. READMEは通常導入、配置、現在のレビュー、DSH移行、tier、token、再有効化とRebuild後の再実行を説明する。個人設定・共有モデル/auth/tierの自動変更をしない。
6. マージ後の実Rebuildは利用者による確認として残す。PRは `Refs #337` とし、残項目をIssueコメントへ記す。

## 非対象

有料モデルによる動作確認、失効・発行・契約操作、Rebuild、既存実行ファイル削除、過去のレビュー/Spec/Planの書換え、無関係なenv改名。`.devcontainer/zshrc.txt` の除外ガードを保つ。

## PR #338: 司令塔自身による確認と結論（2026-11-08）

- 追加実行指示: 利用者「自身でレビューをして問題がなければ、PRに状況を投稿してマージをしてください。」。停止済み担当の再試行ではなく、司令塔自身のコード確認・検証と、問題がない場合の状況投稿・既定の `finalize.py` によるマージを許可する具体的な指示として扱う。内容承認SHAを新たに作らない。
- planner / 確認担当: `openai-codex/gpt-6.1-sol`（Pi、self）。対象HEAD `4b1ed1045d5c334688b74dd747be5e790ed16cdc`、base `main` / `0d58ac76b3c364ec431a292c8bc41e58f57e933b`。判断の記録はサイクル2。
- 結論: **2・修正不要**。追加のコード変更なし。全8変更ファイル（README 1747行を含む）の全文、固定baseからの全差分、設定の統合・同一モデル判定、通常配置と手動setup、ランチャー・tier・既存安全テストを司令塔自身が確認した。致命的な自己発見もない。
- 全指摘の分類: 解消済み0 / 対応する0 / 対応しない0。現行HEADの保存候補にactive・未検証候補・継続指摘はいずれもない。以前の判断の記録のdecisionsも空。安全停止の記録自体を削除・変更・成功扱いしない。

### レビュアーの構成と安全停止の扱い

| レビューファイル | モデル / runtime | 対象HEAD | 現行HEADの成果 / 今回の起動 | 扱い |
| --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max / devin | `4b1ed1045d5c` | Update / 起動なし | 直近runner成功、候補pairの整合を確認。指摘0 |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash / pi | `4b1ed1045d5c` | Update / 起動なし | 直近runner成功、候補pairの整合を確認。過去のガード解除後の検査は根拠にしない。指摘0 |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `4b1ed1045d5c` | Update / 起動なし | 本文は確認したが、直近runnerはawaiting_approvalで権限拒否後の別構文による実行を記録。正常完了・安全性・マージ可否の根拠に採用しない |

今回の判断は票数やApproveではなく、司令塔の現行コードの読解と下記の新しい実行証拠に基づく。workerを再起動せず、権限拒否の迂回や `AGENT_RUNNER_DEPTH` の解除もしない。今回の確認はreview-fix-planningの現行内容の自己確認であり、修正後の `run_roles.py --phase self-review` ではない。コード修正がないため同helper・implement・fix-checkの呼び出しは0回。

### 要件対応と今回の検証

統合担当は全条件ともplanner自身。検証は未コミット変更のない対象HEADで同期実行し、baseがHEADの祖先であることを確認した（未検証のmergeツリーは含まない）。

| 要件 / 共有条件 | 確認方法 | 実行結果 |
| --- | --- | --- |
| 新しい既定3人とCommand Code定義の維持 | PR雛形単独・実個人設定overlayのcheck/list、load_configの実効割当 | 4 CLI全exit0。両設定でSol/max・Devin・OpenCode Go、fallback空、Command Code定義を保持 |
| 明示再有効化とDeepSeek併記の境界 | load_configでCommand Codeだけの明示選択と、同じ役割へのOpenCode Goとの併記 | 前者は受理、後者はduplicate_modelで拒否。検査全体exit0 |
| 通常11本と手動2本の区別 | インストーラの実配置ブロックだけを隔離HOMEで実行 | 通常11本のみ、piccg/piccdなし。全配置ファイルがソースと同一、mode755 |
| 無キー起動・安全ガードの維持 | 3APIキーを外したpigod --version、既存全13ランチャー検査を含むrun-tests | version1.5.0、shell27件PASS。versionを認証・モデル応答の証明にはしない |
| 説明・手動setupと利用者所有部分 | READMEとsetup/ランチャー全文・全差分・関連処理の読解、構文/diff検査、layout | 説明は配置・再有効化経路と整合。全検査exit0。個人設定は読取のみで共有設定・キーを変更しない |
| 実環境への反映 | Issue/PRの対象外と照合 | 実Rebuild・実認証・有料モデル応答・個人設定/キー実移行は未実施。利用者の残作業として維持 |

13検証コマンドは全exit0。環境変更の規定検証 `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を新たに実行した。全体pytestは今回の変更種類の必須条件ではないため再実行していない。テスト追加はF/Lに当たるため行わず、既存の安全テストを削除・変更していない。

- 確認済み一覧: `reviews/usaturn/create-reso-world/#338-fix-issue-337-commandcode-defaults/verified/4b1ed1045d5c.json`（Devin/DeepSeekの候補を入力とし、Opusは合格根拠から除外。候補0、対象内の残る未確認なし）。
- 工程の記録: 同じ `verified/4b1ed1045d5c.planning.json` に投稿後の結果を保存する。自己レビューの予約枠は使用しない。
- 検証ログ・argv・終了コード: 親checkoutの `tmp/agents/pr-338-self-finalize.thjsrj6y/validation.json` と `check-01.log`〜`check-13.log`。今回の実Rebuild等を実施済みとは扱わない。
- 残す制約は元の要件・除外範囲と一致する。追加の設計変更・対応指摘・影響経路の修正はない。投稿・push・マージ・Issue更新の結果は、このSpecに追記せずPRコメントと完了報告へ残す。
