# PR #27 pi 移行の追加点検・修正方針

## 目的と範囲

`usaturn/create-reso-world` PR #27（`feat/issue-19-pi-migration`）の現行 HEAD `6449b0fbf55b5872eab9269d7aa492967346dd97` を対象とする。base は `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`。ユーザはレビュー全件と PR 全体・差分外の関連箇所の調査、妥当な不具合の推奨案による修正と push を明示している。確認待ちを再挿入せず、修正があった場合は push までとし、今回はマージしない。`pr-review` は使用しない。

経路は bounded。既存の cleanup と setup の入力処理・失敗伝播を修正し、移行の目的や API は変えない。検証専用 worktree は固定 HEAD で作成・再現後に撤去し、実装には新しい隔離 worktree を使用する。メイン checkout の未追跡文書は触らない。

## 入力レビューの全件分類

入力は `reviews/#27-feat-issue-19-pi-migration/` の4ファイル。最新の対象 HEAD はすべて `6449b0fbf55b`。Claude、DeepSeek、GPT の履歴上の旧 HEAD は `6f0cd9ee9d04`。

| 指摘 | 分類 | 現行 HEAD の根拠 |
| --- | --- | --- |
| Claude L-1 | 解消済み | README:179–181 と cleanup:111 は、利用者の disable entry も毎回除去する仕様・共有設定への影響を正確に説明する。 |
| Claude I-1 | 解消済み | README:435–442 は rebuild 前の旧 export 削除と4変数の unset を区別して案内する。 |
| GPT I-1 | 解消済み | API トークン節から廃止した Distillation 用要件は削除済み。 |
| DeepSeek I-1 | 対応しない | pi-model-name の旧変数は主モデルの根拠にしない否定例で、Issue #19 が保持を明記している。機能不具合はない。 |
| SWE-2-Max | 指摘なし | 未検証候補は下記に整理する。 |

分類: 解消済み3 / 対応する0 / 判断保留0 / 対応しない1。以下の追加調査による5件は別枠で対応する。

## 追加調査の対応項目

2担当の読み取り専用点検と、別担当の隔離再現を実施した。controller も再現スクリプトを再実行し、終了コード0で全5件の根拠と既存49テストの成功を確認した。実 pi 1.0.2、npm 11.19.0、zsh 5.9 を使用し、実認証・ネット接続・利用者の実 agent directory は使用していない。

| ID | 分類 | 再現・原因 | 修正と検証 |
| --- | --- | --- | --- |
| R2-1 | 対応する (a) | settings-only の `npm: pi-distill ` 等を実 pi は受理するが cleanup は見逃し、登録が残る。unpinned 登録は update、exact pin は通常の resolve で再導入対象になる。 | `npm:` の payload を JavaScript trim 相当で正規化して名前・version 境界を判定する。fake pi の identity も同じ入力範囲を受理する。5対象・文字列/object/pinned/scoped・U+FEFF・類似名保持・update の回帰を追加する。 |
| R2-2 | 対応する (a) | Python json.loads は `NaN`・`Infinity`・`-Infinity` を受理し、実 pi が読めない settings/manifests でも cleanup が成功して状態を変更する。 | 全 metadata の読み込みで非標準定数を拒否し、保存でも非有限値を書かない。settings と4マニフェストで、非ゼロ終了・pi 呼出しなし・変更前バイト列保持を検査する。 |
| R2-3 | 対応する (a) | `NODE_ENV=production`、omit 設定、prefix `.npmrc` により実 npm uninstall が宣言済み dev/optional の保持対象まで削除する。cleanup は成功を返す。 | pi 子プロセスだけに `npm_config_include="dev\n\noptional\n\npeer"` を設定して omit より include を優先させる。npm は環境変数配列を改行2つで分割する。単改行・カンマ・空 omit は再現試験で不適切と確認済み。実 npm のオフライン fixture で保持対象の実体・元バイト列、対象の撤去、設定保持を検査する。 |
| R2-4 | 対応する (a) | setup は mkdir、cp、Python 同期、検証の失敗後も成功表示・終了0になる。backup 失敗でも既存モデルを上書きする。 | standalone zsh に `set -e` を追加し、失敗を伝播する。破損JSON、backup失敗、mkdir失敗、書込み/検証失敗に対する非ゼロ終了と成功表示なしを固定する。backup失敗では元モデルを保持する。 |
| R2-5 | 対応する (a) | `PI_CODING_AGENT_DIR='~/.pi-custom/agent'` が cwd の文字列 `~` 配下に書き込まれ、実 pi の読み込み先とずれる。 | exact `~` / `~/` だけを HOME に明示展開し、eval は使わない。デフォルト・絶対パス・tilde・空白入りパス・非展開の `~other` と独自provider保持を確認する。 |

## 採用しない追加候補・未検証項目

- 同時実行時の設定ロック: README:205 が cleanup 前の pi 終了を要求する。指定の運用条件では再現せず、今回新たなロック実装は行わない。停止要件は維持する。
- 保持拡張が撤去 helper に依存する場合: 実体の強制削除より、残留を理由付きで停止する既存仕様を維持する。
- バックアップの追加失敗テスト、実ローダーの恒久テスト化だけの提案: 対応する不具合の再現と直接関係しない追加提案は採用しない。
- 実 API キーでの Google MCP 呼出しと Dev Container rebuild は未検証。後者は #22 の担当。unpinned update の再導入確認は実 pi の dispatch とオフライン npm 境界 double であり、registry 接続の end-to-end 成功とは扱わない。
- slum03 の resoloop スキル未同期は #19 が記録する既存失敗。関連スキル・版・ワールドは変更しない。

## 検証と公開

不具合の修正対象は `.devcontainer/cleanup_pi_mcp.py`、`.devcontainer/setup_pi.zsh`、`.devcontainer/tests/fake_pi_packages.py`、`.devcontainer/tests/test_pi_mcp_cleanup.py` と今回の文書のみ。既存安全策、バックアップ、mode、独自設定・認証・MCP保持を維持する。

各回帰を修正前に失敗させ、最小修正後に成功させる。全 cleanup suite、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills` と差分検査を行う。既知の layout 失敗は原因を照合して明記する。独立した修正後点検の後、変更を1コミットにまとめて既存 PR の head に push し、最終ステータスコメントを更新する。

## 最終検証と main の並行更新

回帰9件を追加し、修正前に5グループすべてが期待する原因で失敗することを確認した。修正後の全 cleanup 58件、差分検査、zsh構文検査は成功した。controller の全体 bash は24/25本成功、スキルは267件成功・1件スキップ。失敗は既知の slum03 未同期だけで、固定した pristine main `c40a3bd` の直接 layout と個別 layout テストでも同じ失敗を再現した。Task の独立点検は仕様適合・品質とも承認、追加不具合なし。

最終点検中に #26 が main にマージされ、main が `128bd2dc79aab64706c9efa5f9af660c55ca915f` へ進んだ。動く origin/main を二者比較した最初の資料には、PR にない Claude の後退が混じった。固定した元 merge-base に対する実 PR 差分では後退がないことを確認し、誤検出として取り下げた。

ただし最新 main と PR の README に実際の競合があったため、最新 main を `--no-commit` で統合した。README の Claude 起動節を main から丸ごと保持し、pi 移行の見出しと本文を本 PR から保持する解決だけを加えた。Claude の指示・テスト・#21文書は `128bd2d` と同一で、zsh の差分も旧 pi 用 export4行・コメント2行の削除だけである。最新 main を取り込む変更は、5修正と同じ1コミットにまとめる。

統合後も全体 bash 24/25、スキル267件成功・1件スキップ、差分検査が成功した。唯一の失敗は同じ slum03 未同期。競合解決と先行指摘の限定再点検は承認され、新規の統合不具合はなかった。

active LSP 検査では、既存 real-npm fixture の型推論に2件の指摘があり、元 HEAD の同一行にあることを照合した。変更箇所の実行回帰はなく、LSP 全ファイル clean とは報告しない。

所要時間と主要作業の内訳、公開結果は PR コメントに記録する。再現調査担当は20分14秒、controller の独立再実行は33秒、実装担当は15分42秒だった。
