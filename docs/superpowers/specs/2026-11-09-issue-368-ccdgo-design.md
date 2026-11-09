# Issue #368: ccdu を ccdgo に置き換える

## 管理・実行許可

- 状態: `completed`（コード変更とレビュー修正判断の完了。作成時は draft、実行許可で進めており内容承認は未取得。実 API の未確認項目は下記のまま残る）
- 対象: https://github.com/usaturn/create-reso-world/issues/368
- 利用者の指示: `/skill:issue-to-pr` に Issue URL と `--implement pi_opencode-go_deepseek4-flash_max --merge --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=claude-code_opus_default,devin_swe2_max,pi_opencode-go_deepseek4-flash_max` を指定。
- 許可範囲: 通常の設計判断、指定担当による実装、ローカル検証、commit、検査後の push、PR、指定ループの finalize によるマージ。設定・契約・実資格情報・他者の作業は変更しない。
- コード/文書: 同一 worktree・同一 PR。base: `usaturn/create-reso-world`, `origin`, `refs/heads/main`, `04b4196973cb1353d4a53e039d3ccb43db818831`。親 Issue・要求 base・未完了依存・競合 PR・予約は確認時点で無し。
- 移植元: agent-workspace PR #868、merge `234eac9d8d3c713de9d6f09f67dd66b7a954a1de`。移植元の実 API の結果は本 checkout の実測と区別する。

## 意図・変更範囲

提供が終わった union-alpha 用の `claude-opencode-union` / `ccdu` を、OpenCode Go の tier 別モデルを使う `claude-opencode-go` / `ccdgo` に置き換える。元の構造と隔離を維持し、空白キーによる保存済み OAuth の第三者送信を防ぐ。

変更ファイルは `.devcontainer/zshrc.txt`、`.devcontainer/test-herdr-migration.bash`、`.devcontainer/README.md`。正式な Spec・Plan を同じブランチへ追加する。

## ランチャーの仕様

- 共有 `cc_launcher_unsets` は変更しない（コメントの旧名だけ更新）。
- キーは `${OPENCODE_GO_CLAUDE_API_KEY:-${OPENCODE_API_KEY:-${OPENCODE_GO_API_KEY-}}}`。未設定・空を飛ばし、最初の非空値を選ぶ。選んだ値が `*[A-Za-z0-9]*` に一致しなければ、値を出さず、3 変数の案内を stderr に出し `return 1`。空白だけの優先値を下位のキーへ読み替えない。
- 接続先は `https://opencode.ai/zen/go`。選択したキーを `ANTHROPIC_API_KEY` と `ANTHROPIC_AUTH_TOKEN` の両方へ渡す。
- tier: Fable `hy4[1m]`、Opus `deepseek-v4.1-flash[1m]`、Sonnet `muse-spark-1.3-contributor[1m]`、Haiku `glm-5.3-flash[1m]`。
- `ENABLE_CLAUDEAI_MCP_SERVERS=false`、`CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536`。
- `CLAUDE_CODE_MAX_CONTEXT_TOKENS`・`CLAUDE_CODE_SUBAGENT_MODEL`・`ANTHROPIC_CUSTOM_HEADERS` は設定しない。
- `claude --model opus "${opts[@]}" "$@"`。短縮名 `ccdgo` だけ `--dangerously-skip-permissions` を付ける。長い名前では付けない。引数の境界、子の終了コード、親の環境を維持する。

## ドキュメント

ツール一覧、プロバイダ表と説明、Pi の旧注記、API トークン節を現行名に更新する。Ollama 節の後に OpenCode Go の節を置き、モデル表、地域・プライバシーの前提、起動例、両認証変数の理由、Yes/No と警告、/logout の勧め、/status、1M・effort・出力上限、auto mode の 400 と再試行、MissingSessionID 対策を書く。

既存の `~/.zshrc` と既に起動したシェルには旧関数が残るため、rebuild または該当ブロックの手動置換と新しいシェルへの切替を案内する。移行案内では旧名を示してよい（旧名の単なる全削除という受け入れ文言と、旧関数の処置の説明を両立させる）。過去の記録を変更しない。ここで除外する過去の記録は `docs/maatlog-poc-porting.md` と既存 `docs/superpowers/`。README の #125 の説明は現行の注記として更新する。

## 根拠と検証境界

- ctx7 `/websites/code_claude` の認証仕様を確認: `ANTHROPIC_AUTH_TOKEN` は保存済みログインより即時優先、API キーは対話で承認が必要。両変数のヘッダーと Go の応答は移植元 PR #868 の実測を参照する。
- 自動テストは stub の Claude と隔離した HOME だけ。実キー・課金 API・共有 Claude のログインを使用しない。
- 既存の env 隔離テストへ異なる 3 キーと両認証変数の検証を組み込み、代表 1 件の空白優先キー拒否を追加する。キー fallback の追加組合せと引数・モデル設定は一時 stub/差分で確かめ、専用の固定値テストをコミットしない。
- README の出典は取得済みの移植元 PR 本文・同 merge の README。controller が保存した `tmp/agents/issue-368.2pe62w37/source-pr.json`・`source-readme.md` を利用できる。
- この run での対話 `/status`・`/model`、4 tier の実通信、streaming・thinking・Read/Bash の会話継続・サブエージェントは未実施として PR に確認手順を残す。移植元の成功をこの checkout の検証成功に読み替えない。既存コンテナへの反映後に人間が確認するため `Refs #368` とし、Issue を自動 close しない。
- ルート README の 3 検証入口を実行する。GitHub Actions は無効のままで CI を追加しない。

## 対象外・編集禁止

#347 の ccdd/ccddg の守り・共通判定関数、runner の agent 登録、Pi のランチャー、Claude のユーザ/プロジェクト settings、契約・キー作成・地域/プライバシー設定、過去の Spec・Plan は変更しない。#347 に先行依存は無く、この run の開始時には open PR・同番号の作業 branch は無い。

## 決定記録

| 選択した案 | 検討した別案 | 理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| 既存関数を最小置換し ccdol と同じ英数字ガード | 移植元の共通 graph 判定を丸ごと導入 | #347 と分離し、NBSP/BOM も拒否する既存規則を保つ | issue-to-pr の通常判断。安全境界の変更は停止 |
| 同じキーを API key と Bearer 両方へ渡す | API key のみ / Bearer のみ | 前者は保存済みログイン、後者は Go の 401 の問題がある | Issue の明示仕様。片方を外して成功扱いにしない |
| 最初の非空値を選んでから検査 | 英数字を含む最初の値を選ぶ | 空白値を黙って飛ばすと意図と別のキーを使う | Issue の決定 |
| S/F∩S の実行テストだけ追加・更新 | モデル一覧・文言の固定値テスト | 秘密送信と権限省略の損害を守り、F/L/D を増やさない | AGENTS.md の基準 |
| 指定 runner に Task ごとに逐次依頼 | self / 同時実装 | implement check は `self=false`、fallback 無し | 利用者 `--implement`。担当失敗は代行せず停止 |
| PR 後の最大 3 サイクル | 既定値を利用者指定と記録 / 無制限 | check-options の既定 `max_cycles=3` | inspect 3 担当、implement は利用者指定。self-review/fix-check は既定 self |
| 実 API 未確認を明記し反映後に確認 | 移植元の実測を再検証扱い | 課金/認証状態を自動テストへ持ち込まず、Issue の未確認時の報告手順を使う | 未確認を成功にしない。ログ・PR と Issue コメントに残す |

## PR #369 のレビュー修正判断（サイクル 1）

- planner: `openai-codex/gpt-6.1-sol`（pi、環境変数で確認）。実行許可は上記 issue-to-pr の `--merge`。
- 対象 HEAD: `35ab77747874a97a2b0ed3ec50bd785c7e601fd6`。base は当初の `04b4196973cb1353d4a53e039d3ccb43db818831` のまま、対象 HEAD の祖先。
- 結論: **2 修正不要**。全指摘・未確認候補は 0 件。解消済み 0 / 対応する 0 / 対応しない 0、前の判断・設計見直し・修正する影響経路は無し。

| レビューファイル | モデル / runtime | HEAD | このサイクルで再実行 | 結論・loop の受取 |
| --- | --- | --- | --- | --- |
| `SWE-2-Max.md` | SWE-2 Max / devin | `35ab77747874` | yes | Approve、accepted |
| `deepseek-v4.1-flash.md` | deepseek-v4.1-flash / pi | `35ab77747874` | yes | Needs manual verification（実 API）、accepted |
| `claude-opus-5-5.md` | claude-opus-5-5 / claude-code | `35ab77747874` | yes | 保存済み本文は Approve。ただし runner は awaiting_approval・exit0 で rejected。停止確認済み。保存された同 HEAD の本文・候補を補助入力として読み、accepted の人数には加えない |

全レビュー本文と候補一覧を読み、候補一覧の validate/check-pair は 3 件とも成功した。失敗したレビュアーを「成功・指摘なしの担当」として扱っていない。成立した 2 担当と controller の現行版確認を根拠とする。

### 要件・検証の対応と共有条件

共有するキー選択→認証変数→CLI→README の意味の統合は controller が担当した。3 つのコード/文書ファイルと新規 Spec/Plan の全文、関連する run-tests.bash/test-readme.bash を読み取り専用担当が精読し、controller が同じ clean HEAD を照合して採用した。PR 起因の致命的欠陥は無し。既存 README の test-readme の説明のずれは今回の原因と無関係で、本 PR の修正に含めない。

| 条件 | 担当・観測結果 | 根拠 |
| --- | --- | --- |
| キー選択・拒否・両認証・隔離・権限 | Task 1 実装後に controller が正常側/拒否側と引数・親環境を確認 | `verification-1.log`、`verification-5.log` と integration probe。全て exit0 |
| tier/上限と README | Task 1 と Task 2 controller の仕様/差分・出典照合 | モデル一覧/文言の固定値テストは追加していない |
| 全体回帰 | 最後の実装 commit、clean な同 HEAD で実行 | `run-tests.bash`: 27 PASS / 0、`check-layout.sh`: PASS / 0、pytest: 1354 passed / 0 |
| 実 API | 未実施のまま反映後の確認へ | README と PR の手順。移植元の成功を本 checkout の成功に読み替えない |

検証 argv・終了コード・実ログは `/workspaces/reso-world/tmp/agents/issue-368.2pe62w37/verification.json` と `verification-1.log`〜`verification-8.log`。継承した VIRTUAL_ENV を uv が無視して worktree の環境を使う警告はあるが、検証の失敗は無い。HEAD・clean 状態・全コマンドの exit0・ログの存在・同じ祖先 base を確かめ、issue-to-pr の再利用条件によりこのサイクルの checks に採用した。Spec だけの追記はコード/設定/検証前提を変えない。

- 確認済みの一覧: `reviews/usaturn/create-reso-world/#369-feat-issue-368-ccdgo/verified/35ab77747874.json`。confirmed/not_reproduced/unverified はいずれも 0。実通信等は coverage.remaining に明記。
- 工程の記録の保存先: 同ディレクトリの `35ab77747874.planning.json`（投稿後に記録）。
- 修正担当の割り当て: `pi_opencode-go_deepseek4-flash_max`。このサイクルでは修正不要のため呼び出し無し。
- 修正後自己レビュー/fix-check: 既定 self、呼び出し **0 回**（修正無し）。Task/branch の初回レビューとは区別する。
- マージ・Issue 更新はまだ実施済みとは記録しない。後続の状況コメントと finalize の結果を基準にする。`Refs #368` を維持し、実 API の残りを Issue へコメントする。

## 受け入れ基準（実装・レビュー共通）

動作環境は Linux Dev Container の zsh/bash、隔離 HOME と stub の Claude。実入力は非 ASCII・連続空白・改行を含む `-p` のプロンプトと追加オプション、互いに異なる偽の 3 キー、親の汚染した認証変数、ASCII 空白+NBSP+BOM の優先キーと有効な下位キー。未設定・空は既定順に解決し、非空で英数字の無い値は下位へ切り替えず起動前に拒否する。許可された子には選んだ接続先と同じキーの両認証変数だけが渡り、元のキー・親の認証情報は残らない。短縮名だけ権限確認を省略し、引数と終了コードを保つ。model/tier/上限は仕様どおり設定し、不要な指定は残さない。対象外は他ランチャーの仕様変更・実資格情報・過去の記録。README は現行挙動と移植元の実測、本 checkout で未確認の実 API 項目を区別する。
