# Issue #337: Command Code GOAT の既定経路停止

## 管理・実行許可

- 状態: `draft`（内容承認は受けていない）
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
