# Issue #305: agent 命名統一・追加とモデル識別

## 管理・実行許可

- 状態: `draft`。内容の承認は受けていない。
- 対象: usaturn/create-reso-world、Issue https://github.com/usaturn/create-reso-world/issues/305
- 利用者指示: `/skill:issue-to-pr` に続く `https://github.com/usaturn/create-reso-world/issues/305 --merge`。
- 実行許可: 通常判断を推奨案で決め、Spec/Plan のコミット、実装、検証、push、PR 作成、指定されたレビューループへ継続する。マージは同ループの finalize.py のみ。
- CODE_ROOT = DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-305-agent-catalog`
- branch: `feat/issue-305-agent-catalog`。base は `code-base.json` に捕捉した origin / refs/heads/main の SHA。親・要求 base・未完了依存は無し。
- 移植元: agent-workspace PR #842、マージコミット `5b5d7455a1f9bd7b1bd72e342dabb7816c89f914`。DeepInfra の前提 #748 も同コミットのファイルで参照する。

## 意図と範囲

雛形の名前から runtime/provider/model/effort を読み取れ、新しいモデルを選択できるようにする。同じモデルを provider 別名で選んでも多様なレビュアーであると誤認させない。既存設定の意味・認証・権限・実行手順は変えず必要差分だけ移植する。

個人設定・過去の reviews/evals/provenance・完了済み Spec/Plan・ワールド・外部リポジトリを変更しない。alias、自動正規化、レビュアー構成変更、rebuild、Actions、新しい有料試行の無制限追加は対象外。

## 名前と割り当て

命名は `<runtime>_<provider>_<model>_<effort>`。段内は `-`、provider 未指定は省略。model は系列・メジャー版・tier の小文字、マイナー版・日付・ベンダー接頭辞を省く。effort 未指定は `default`。個人設定には命名を強制しない。

| 旧名 | 新名 |
| --- | --- |
| claude-opus | claude-code_opus_default |
| devin-swe | devin_swe2-max_default |
| pi-deepseek | pi_commandcode_deepseek4-flash_max |
| pi-gpt | pi_openai-codex_gpt6-sol_max |
| pixg | pi_xai_grok4_xhigh |
| pi-go-glmf | pi_opencode-go_glm5-flash_max |
| pigod | pi_opencode-go_deepseek4-flash_max |
| pi-gemf | pi_google-vertex_gemini3-flash_high |
| codex | codex_openai_gpt6-sol_default |
| cursor | cursor_auto_default |
| cursor-grok47 | cursor_grok4_xhigh |

既存11 agent は名前と参照以外を維持する（DeepSeek 2 agent への任意の model_key 追加を除く）。特に Sol の effort=`max`、Sol/pigod の env=`OPENCODE_API_KEY`、after_run の `uv --project .` を保持する。

review.inspect は従来の3担当の新名、fix.implement は `claude-code_opus_default`。self-review/fix-check/issue.implement の `self` は保持する。

| 追加名 | runtime / command | provider / model | effort |
| --- | --- | --- | --- |
| pi_openai-codex_gpt6-terra_xhigh | pi / pigt | openai-codex / gpt-6.1-terra | xhigh |
| pi_openai-codex_gpt6-astra_xhigh | pi / piga | openai-codex / gpt-6-astra | xhigh |
| claude-code_sonnet_default | claude-code / claude | 未指定 / sonnet | 未指定 |
| pi_google-vertex_gemini4-argon_high | pi / pigema | google-vertex / gemini-4-argon | high |
| pi_deepinfra_deepseek4-flash_high | pi / pidid | deepinfra / deepseek-ai/DeepSeek-V4.1-Flash-1017 | high |

追加 env は HOME/PATH、Argon は既存 Vertex の環境変数群、DeepInfra は DEEPINFRA_TOKEN。資格情報の実値は保存・表示しない。

## 同一モデル比較

`Agent.model_key: Nonblank | None = None` を追加。比較集合は model があれば `{model}`、key もあれば `{model, model_key}`。同じ役割の agents/fallback の候補間、および exclude_same_model_as の役割間で積集合があれば `duplicate_model` とする。

同じ model はキーが片方だけ／互いに異なる場合も拒否する。未知モデルを推測しない。キー無しで model の違う正常構成は通す。CommandCode/OpenCode Go/DeepInfra の3 DeepSeek agent に `model_key = "deepseek-v4.1-flash"` を付ける。

## 起動経路と配置

- pigt は piga 同様の OAuth 検査・共通ヘルパ・引数保持方式。親 Terra/xhigh、子 cheap=Luna/xhigh、balanced=Sol/xhigh、max=Terra/max。
- pidid は PI_CODING_AGENT_DIR の既存解釈を再利用し、DeepInfra provider と exact model の登録、認証、専用 tier 設定の前提が不足したら起動しない。親と全 tier は上表の DeepInfra model/high。別モデルに切り替えない。
- ローカルに存在しない upstream tier-guard 拡張は参照しない。必要な fail-closed 検査はローカルのヘルパ／ランチャーに限定して実装する。pigt も、使用する親子のモデルカタログ不足を検出し更新手順を案内する。
- モデル確認は公開メタデータのみを読み、キー解決や外部認証問い合わせを起こさない。Pi の bundled/保存済みカタログと models.json の実際の読み方を確認して実装する。既存ランチャーの挙動は変えない。
- pidid のユーザー所有 tier 編集は保持する。上記モデル/high は初期設定であり、利用者が明示編集した有効な tier はその値で起動してよい。全 tier のモデルと thinking が解決できなければ停止し、個人設定の内容を黙って雛形に戻したり別モデルを推測したりしない（builder check の確認点に対する通常判断）。
- install_beforehand.bash と setup_pi_superagents.zsh に両ランチャーを登録。新規 models.json は雛形から、既存はそのまま。
- setup_pi.zsh の既存 provider 更新 helper、他 provider 保持、バックアップ、mode、パス解釈を維持し、pidid・共通ヘルパ・未配置 tier を配置する。明示 setup 以外で利用者環境を更新しない。

## DeepInfra の値と根拠

2026-10-31 に Context7 と公式ページを確認した。

- Pi 連携: https://docs.deepinfra.com/integrations/pi
- 対象モデル: https://deepinfra.com/deepseek-ai/DeepSeek-V4.1-Flash-1017/api
- Reasoning: https://docs.deepinfra.com/chat/reasoning
- 公開 metadata: https://api.deepinfra.com/v1/openai/models?filter=with_meta&sort_by=pi
- Pi のインストール済み models-configuration.md（schema）、models.md（カタログ構成）を実装の参照にする。

OpenAI Chat Completions 互換、baseUrl=`https://api.deepinfra.com/v1/openai`、api=`openai-completions`、apiKey=`$DEEPINFRA_TOKEN`、authHeader=true。対象モデル metadata は context_length/max_tokens=1048576、vision/reasoning 対応、標準価格 input=0.2/output=0.6/cacheRead=0.006、割引は別項目0.51。料金は標準値を使い README で変動する表示用値と説明する。cacheWrite=0。

input は text/image。reasoning=true、supportsDeveloperRole=false、thinkingFormat=deepseek。maxTokens=65536 はサービス最大値ではなくリクエスト当たりの運用上限。公式 Pi 連携もこの値を任意上限として扱う。thinkingLevelMap は minimal/low→low、medium→medium、high→high、xhigh/max→null。親子は high を指定し、未確認の max/xhigh は API へ送らない。実機1回で実際の疎通を確認する。

## 文書と移行

README に命名・比較・追加 agent・認証・ランチャー・tier・新旧環境 setup を記載し、TOML 冒頭から命名節を参照する。interfaces.rst の完全一致のみという説明も更新する。現在使う例と #243 の移行先、review-fix の既定名は更新するが、削除対象を説明する旧名と凍結履歴は維持する。

個人設定は自動変更しない。旧名の agents 定義があれば独自定義として残ること、旧定義を削除して agents/fallback 参照を新名に変更する手順、参照だけの設定では更新が必要であることを説明する。現環境の個人設定は旧名参照だけを持つためマージ後に手動移行が必要。PR 後のループは親 checkout の旧雛形と既存設定で実行し、勝手に --config/--assign を補わない。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- |
| 移植方法 | ローカル構成への限定差分 | ファイル一括置換 | 認証・effort・after_run・バックアップを維持 | issue-to-pr の通常判断 |
| 識別 | model と任意 key の和集合 | key に置換／自動正規化 | 従来の重複拒否を弱めない | Issue の明示要件 |
| ランチャー | ローカル helper に最小の前提検査 | upstream 拡張一式の導入 | 存在しない guard を参照せず別モデルを防ぐ | 意図しない外部送信は停止 |
| DeepInfra | #748 を同時導入 | 別 Issue 化 | 存在しない起動経路を残さない | 公式資料と実機を確認 |
| 個人設定 | 手順のみ、無変更 | 自動移行／alias | 利用者所有物を保護 | 無断変更禁止 |
| 実装方式 | SDD で独立3 Taskを逐次委譲、統合は司令塔 | 全部 inline | runner、起動経路、割り当て・文書の境界を分離 | implement check は既定 self |
| PR後のループ | check-options の既定適用 | モデル独自のassign/config補完 | 利用者が書いた順の引数だけを渡す | max_cycles=3、既定assignはセッション記録参照 |

## 検証・受け入れ基準

動作環境は Dev Container。個人設定なしと変更前雛形の写しを重ねた環境で check/list が成功する。既存11 agent の起動値を意味比較し、model_key 以外の差がない。新5 agent が起動経路・認証手順を持ち、pigt/pidid を隔離HOMEで新規・既存環境に配置して既存値を保持できる。

実入力は `--assign inspect=pi_openai-codex_gpt6-sol_max,devin_swe2-max_default,pi_commandcode_deepseek4-flash_max`、プロンプトは改行と日本語を含む。新5 agent各1回＋既存3 agent構成review1回、計8担当が実機の上限。認証・利用制限・接続失敗は未確認として記録し追加試行しない。停止・想定外書き込み・秘密出力も確認する。環境更新が必要なら bwrap のプロセス内 overlay 等で公開設定だけ重ね、実HOMEは更新しない。

防御対象は明示 model/key の集合の一致、pidid/pigt の起動前提、利用者設定保持。キー無しかつ異なる model を未知の同一モデルと推測することは対象外。正常構成も受け付ける。

S の代表テストだけを追加・拡張し、命名表や文言の写しのテストは書かない。検証入口は README.md のテスト3コマンド（ワールド除外）および Issue 指定の runner/launcher 検査。正式検証・最終全体レビュー・gitleaks・base/head 再照合の後に公開する。CI は停止中の private repository なので確認不要。
