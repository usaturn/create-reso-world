# Issue #347: DeepInfra ランチャーのキー検査

## 管理・実行許可

- 状態: `completed`（コードとレビュー判断の完了。実行指示は内容の承認ではない）。
- 対象: https://github.com/usaturn/create-reso-world/issues/347
- 利用者の指示: `#347 --merge --spec-review pi_deepinfra_deepseek4-flash_high --implement pi_deepinfra_deepseek4-flash_high --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_max --assign implement=pi_deepinfra_deepseek4-flash_high`。
- 許可範囲: 通常の設計判断、指定担当による Spec レビュー・実装、ローカル検証、commit、検査後の push、PR、および指定ループの finalize によるマージ。実キー・実 API、他者の作業や設定は変更しない。
- コードと文書は同じ worktree・PR。base は `usaturn/create-reso-world` の `origin` / `refs/heads/main` / `05989c35e66b8c6f3e6026c3beb19227d8812d8d`。親 Issue・未完了の依存・競合 PR・予約は確認時点で無し。

## 目的と範囲

`claude-deepinfra` / `ccdd` と `claude-deepinfra-glm` / `ccddg` が、Claude Code で未設定と解釈されるキーで起動すると、保存された claude.ai OAuth が第三者に送られるおそれがある。起動前にこれを防ぐ。Issue の後続コメント（https://github.com/usaturn/create-reso-world/issues/347#issuecomment-6742265150）に従い、撤去済みの `ccdu` と、既に保護された後継 `ccdgo` の仕様変更は対象外。

変更対象は `.devcontainer/zshrc.txt`、`.devcontainer/test-herdr-migration.bash`、`.devcontainer/README.md` と、この Spec・Plan。

## 仕様と検証

- 両 DeepInfra 関数は `DEEPINFRA_TOKEN` が未設定・空、または ASCII 英数字を 1 文字も含まない場合、値を出さない固定文を stderr に出して非 0 で戻り、`claude` を起動しない。ASCII 空白、NBSP、BOM を含む値も拒否する。`ccdol` / `ccdgo` と同じ `[[ ${DEEPINFRA_TOKEN:-} != *[A-Za-z0-9]* ]]` の判定を使う。
- 有効なキーは従来どおり `ANTHROPIC_AUTH_TOKEN` へ渡す。接続先、モデル、env の除去、MCP、引数、終了コード、短縮名だけの権限省略、親の環境は変えない。
- README の第三者プロバイダの説明と API トークン節を実際の判定に合わせる。`pidid` に同じ検査があるとは書かない。
- 回帰テストは S: 失敗しても起動が成功したように見え、保存済み OAuth が誤送信され得る。隔離 HOME/PATH と stub Claude で、ASCII 空白・NBSP・BOM を含む代表入力を別々の関数本体である `ccdd` と `ccddg` に与え、非 0・値を表示しない・Claude 未起動を確認する。通常名は同じ関数本体を使うため重複して試さず、正常系は既存の接続先・env テストを使う。組合せの重複や README の固定文言テストは追加しない。
- 実キー・実通信は使わず、`bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` を実行する。Codex の `CODEX_THREAD_ID` が隔離 HOME の cleanup fixture に継承されると、その fixture が実セッションの記録を探して失敗するため、必要なら検証コマンド単位で `env -u CODEX_THREAD_ID` を使い、元の失敗と切り分けを記録する。

## 決定記録

| 選択 | 別案 | 理由・委任または停止条件 |
| --- | --- | --- |
| 両 DeepInfra 関数に既存ランチャーと同じガードを追加 | 4 ランチャーを共通関数へまとめる | 既存の安全境界を変えず最小範囲で直す。issue-to-pr の通常判断 |
| 実行テストで両関数の代表入力を確認 | 入力の全組合せ、文言固定テスト | OAuth の誤送信を防ぐ S、正常系は既存テスト。AGENTS.md の S/D 基準 |
| `ccdgo` は変更しない | 旧 Issue 本文どおり優先順位を変える | 後続コメントと #368 の決定が旧案を置き換えている |
| Spec レビューと実装を `pi_deepinfra_deepseek4-flash_high` に依頼、fallback なし | 自分で代行 | 利用者指定。失敗を成功扱いや暗黙の担当変更にしない |
| マージループ inspect は `devin_swe2_max`、`pi_openai-codex_gpt6-sol_max`、implement は指定 Pi | 別担当へ変更 | 利用者指定。`check-options` 成功。最大 3 サイクル、self-review と fix-check は既定 self |

## Spec レビュー

- review-1: `pi_deepinfra_deepseek4-flash_high`、実観測 `deepinfra / deepseek-ai/DeepSeek-V4.1-Flash-1017 / high`、fallback なし、391.817 秒、review ID `87e38fbc6a66471f854c29bccbc250d5`、reviewed SHA-256 `defb16f749016e2187e34152489b795a08fabd332220c595346534df42ea81c8`。
- S1（minor）採用: 別名は同じ関数本体であり、回帰テストは両方の本体を短縮名で代表し、通常名の正常系は既存テストに任せる。
- outside_changes はなし。unprotected_changes は既に欠落していた他の 6 worktree 登録で、対象 worktree は保護されていた。`review.json` に理由と完全パスを記録。

## PR #395 レビュー修正判断（サイクル 1）

- 実行許可は上記 `--merge`。planner は `gpt-6.1-terra`（codex）、対象 HEAD `f9f4d2594acef4cbd73c8fccc3f426a49484621f`。結論 2: 修正不要。全指摘・未確認候補は 0、解消済み 0 / 対応する 0 / 対応しない 0。設計見直しなし。

| レビュー | モデル | runtime | HEAD | このサイクルで再実行 | 結果 |
| --- | --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max | devin | `f9f4d2594ace` | はい | Approve、accepted |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `f9f4d2594ace` | はい | Approve、accepted |

- 確認済み一覧: `reviews/usaturn/create-reso-world/#395-fix-issue-347-deepinfra-key/verified/f9f4d2594ace.json`。工程の記録は同じ `verified/f9f4d2594ace.planning.json` に保存する。
- 受け入れ条件の確認: 無効値の拒否・正常値の認証と環境隔離・README を同じ HEAD の差分とレビュー実行で照合。全体の shell 27 件・layout・pytest 1442 件の再実行は exit 0。検証前後 clean、base `05989c35e66b8c6f3e6026c3beb19227d8812d8d`。最初の pytest 時間依存失敗も検証記録に保存。実キー・実 API は対象外。
- 修正担当は指定 `pi_deepinfra_deepseek4-flash_high`、自己レビュー・fix-check は既定 self。修正不要のため、このサイクルでそれらの呼び出しは 0 回。
- 判断の記録は PR #395 のサイクル 1 の状況コメントに保存する。マージ・Issue 更新はこの時点では行っていない。
