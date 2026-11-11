# Issue #397: Alibaba Cloud Model Studio の Token Plan のランチャー（ccda）を取り入れる

## 管理・実行許可

- 状態: `draft`（issue-to-pr の実行許可で進める。内容の承認は得ていない）
- 対象: https://github.com/usaturn/create-reso-world/issues/397
- 利用者の指示（2026-11-11）: `/issue-to-pr #397 --merge --spec-review pi_opencode-go_deepseek4-flash_max --implement pi_opencode-go_deepseek4-flash_max --assign implement=pi_opencode-go_deepseek4-flash_max --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_xhigh`。1 回目は `pi_openai-codex_gpt6-sol_xhigh` が設定に無く停止し、PR #398 で設定に入った後、「最初からやり直してください」で再開した
- 許可範囲: 通常の設計判断、指定担当による実装、ローカル検証、Issue が許す実 API の確認（4 tier を各 1 回）、commit、検査後の push、PR 作成、PR 修正ループの `finalize.py` によるマージ。契約・キーの発行・利用者の settings・他者の作業は変更しない
- コード/文書: 同じ worktree・同じ PR（`DOCS_SEPARATE=false`）。base: `usaturn/create-reso-world`、`origin`、`refs/heads/main`、`0c4952ec824f65de900c58caa2b3ffe267e53ce7`。親 Issue・要求 base・未完了の依存・競合 PR・予約は確認時点で無し
- 移植元: usaturn/agent-workspace#923、PR #925（マージコミット `4bf1355630c8fc6b3c264ad82c3ac44f1fead4a5`）。移植元の実測は、この checkout の実測と区別して書く

## 意図

#17・#18 で除外した `claude-alibaba` / `ccda` を、移植元 #923 の新しいモデルの割り当てで取り入れる。Dev Container の Claude Code から Alibaba Cloud Model Studio の Token Plan の Qwen モデルを使えるようにする。本リポジトリのランチャー・テストの形（インラインの英数字ガード、`expected_unsets` の完全一致）を保ち、移植元のファイルで置き換えない。

守る損害は 2 つ。(1) キーが空・空白だけのまま起動すると、Claude Code が保存済みの claude.ai の OAuth トークンを `maas.aliyuncs.com` へ送る。(2) 親シェルの `MAAS_ANTHROPIC_TOKEN` が他のランチャーの子へ、他のプロバイダのキーが `ccda` の子へ届く。

## ランチャーの仕様（`.devcontainer/zshrc.txt`）

- `function claude-alibaba ccda ()` を `ccdgo` の後（`cod` の前）に置く。構造は `ccdol` と同じ（キーの確認 → `env "${cc_launcher_unsets[@]}" ... claude --model opus "${opts[@]}" "$@"`）
- キーの確認: `[[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]` なら、値を出さずに固定文を stderr に出し `return 1`。案内文は `${funcstack[1]}: MAAS_ANTHROPIC_TOKEN is not set, empty, or has no letters or digits; create a key in the Model Studio console and export it in this shell`。他のランチャーと同じ 4 行の理由のコメントを付ける
- 子に設定する値

  | 変数 | 値 |
  | --- | --- |
  | `ANTHROPIC_BASE_URL` | `https://token-plan.ap-southeast-1.maas.aliyuncs.com/apps/anthropic` |
  | `ANTHROPIC_AUTH_TOKEN` | `"$MAAS_ANTHROPIC_TOKEN"`（Bearer。`ANTHROPIC_API_KEY` は設定しない） |
  | `ANTHROPIC_DEFAULT_FABLE_MODEL`・`ANTHROPIC_DEFAULT_OPUS_MODEL` | `qwen4-max-preview` |
  | `ANTHROPIC_DEFAULT_SONNET_MODEL`・`ANTHROPIC_DEFAULT_HAIKU_MODEL` | `qwen3.8-flash` |
  | `ENABLE_CLAUDEAI_MCP_SERVERS` | `false` |
  | `CLAUDE_CODE_EFFORT_LEVEL` | `max` |
  | `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `65536` |

- model ID に `[1m]` を付けない（`/v1/models` が 404 で、1M のコンテキストの根拠が無い）
- 短縮名 `ccda` だけ `--dangerously-skip-permissions` を付ける。引数の境界・子の終了コード・親シェルの環境は他のランチャーと同じく保つ
- `cc_launcher_unsets` に `-u MAAS_ANTHROPIC_TOKEN` を足し（`OPENCODE_GO_API_KEY` の後）、前のコメントのランチャー一覧に `ccda` を足す
- 関数の前のコメントに、出典（#397、移植元 agent-workspace#923）、Bearer だけを渡す理由、`[1m]` を付けない理由を書く

## テスト（`.devcontainer/test-herdr-migration.bash`）

AGENTS.md の「テストの採用基準」に従い、S と F∩S だけを足す。既存のテストに入力を足すことを優先し、新しいテストは代表の 1 件にする。

1. `test_cc_launcher_env_unsets`（F∩S・S）: `expected_unsets` に `MAAS_ANTHROPIC_TOKEN` を足す（完全一致の照合）。`env_args` に `MAAS_ANTHROPIC_TOKEN=fake-maas` を置き、`POLLUTED_` の除外の `case` に足す。ランチャーの 2 つのループに `ccda` を足し、入力元のキーの不在の確認に `MAAS_ANTHROPIC_TOKEN` を足す。`ccda.log` の `ANTHROPIC_AUTH_TOKEN=fake-maas` を確かめる。これで `MAAS_ANTHROPIC_TOKEN` が `ccdd`・`ccddg`・`ccdgo`・`ccdol` の子に残らないこと（`^MAAS_ANTHROPIC_TOKEN=` の不在）も確かめる
2. `test_cc_launcher_destination_and_exit_status`（F∩S）: 対象に `ccda`・`claude-alibaba` を足し、`MAAS_ANTHROPIC_TOKEN=fake-maas` を渡す。Python の判定に Alibaba の分岐を足し、送り先・`ANTHROPIC_AUTH_TOKEN == fake-maas`・`ANTHROPIC_API_KEY is None` を確かめる。省略のフラグの短縮名の一覧に `ccda` を足す。MCP の無効化は既存の共通の assert で確かめる。上のコメントの短縮名の一覧も更新する
3. `test_alibaba_launcher_requires_key`（S）: `test_ollama_launcher_requires_key` と同じ形。`MAAS_ANTHROPIC_TOKEN=$' \xc2\xa0\xef\xbb\xbf'`（ASCII の空白・NBSP・BOM）で `ccda probe` が非 0 で終わり、stub の `claude` が起動しないことを確かめる。損害（ガードが外れても起動は成功し、claude.ai の認証情報が `maas.aliyuncs.com` に送られる）と、この 1 件で `-z` だけの判定と `[[:space:]]` の判定の両方の誤りが分かることをコメントに書く。末尾の実行の一覧に足す

テストにしないもの: モデル ID・effort・出力上限の値（F。実 API の確認で代える）、README の文言（F）、通常名 `claude-alibaba` のキーの確認（同じ関数本体なので D）、案内文が値を出さないこと（固定文で、値を展開しない。#347 で DeepInfra に代表のテストがある。D）。

## ドキュメント

### `.devcontainer/README.md`

- ツールの表（Claude Code の行）の起動名に `ccda` を足す
- 46 行目の「`ccda`（`claude-alibaba`）も置かない」を削る（Grok Build の記述は残す）
- 「秘密情報」: `OLLAMA_API_KEY` と同じく、`MAAS_ANTHROPIC_TOKEN` も env ファイルに書かず、使うシェルで export する例外として書く。理由は、env ファイルの変数はすべてのシェルに export され、ランチャーを通さない `claude`・pi などにも渡るため。「撤去した `ccda` が使っていた `MAAS_ANTHROPIC_TOKEN` は、もう使わない」「子プロセスから外さない」の段落は、今の挙動（`ccda` だけが読み、他のランチャーの子からは外す）に書き換える
- 「既存環境の更新」: 2026-10 の移行の手順として残しつつ、#397 の後に読んでも利用するキーや新しい `ccda` を消させないように書き換える。
  - 冒頭の「除外したツール（Grok Build・`ccda`）」は、`ccda` は #397 で新しい割り当てで戻したと注記する
  - 手順 2 の「`MAAS_ANTHROPIC_TOKEN` を削除し」は、「env ファイルに `MAAS_ANTHROPIC_TOKEN` があれば env ファイルからは外す（`ccda` を使うなら、使うシェルで export する。「API トークン」）」にする
  - rebuild しない場合の `unset MAAS_ANTHROPIC_TOKEN` の項目は、env ファイルから外した値が使用中のシェルに残ることだけを書き、`ccda` を使うシェルでは外さなくてよいと書く
  - 「古い `~/.zshrc` に残る `ccda`（`claude-alibaba`）の関数…も削除する」は、「古い `~/.zshrc` に残る 2026-10 以前の `ccda`（`claude-alibaba`）の関数は、`zshrc.txt` の新しい関数に置き換える」にする（Grok Build の行の削除は残す）
- 「Claude Code の起動と更新」: 第三者プロバイダの表に `claude-alibaba` / `ccda` の行（接続先 Alibaba Cloud Model Studio Token Plan、opus `qwen4-max-preview`、fable `qwen4-max-preview`、認証 `MAAS_ANTHROPIC_TOKEN`）を足し、sonnet・haiku が `qwen3.8-flash` で `[1m]` を付けないことと、キーの英数字の判定を書く。詳しい節への参照を足す。「4 つのプロバイダ関数」を「5 つ」にする
- 「API トークン」: 冒頭の「`OLLAMA_API_KEY` は書かない」に `MAAS_ANTHROPIC_TOKEN` を足し、`MAAS_ANTHROPIC_TOKEN` の項目を足す（`ccda`・`claude-alibaba` だけが読む、env ファイルには書かず使うシェルで export する、子には `ANTHROPIC_AUTH_TOKEN` としてだけ渡り `ANTHROPIC_API_KEY` には入れない、他のランチャーの子には渡らない、英数字が無ければ値を出さずに止める、キーは Model Studio のコンソールで作る）。`OLLAMA_API_KEY` の項目の「`ccdd`・`ccddg`・`ccdgo` の子には渡さない」に `ccda` を足す
- 新しい節「Alibaba Cloud Model Studio の Token Plan で Claude Code を起動する（#397）」を、OpenCode Go の節の後（「## 非対話エージェントのランナー（agent-runner）」の前）に `###` で置く。移植元の README の節を、本リポジトリの書き方（ccdol・ccdgo の節）に合わせて取り込む。内容: 概要と短縮名・通常名の違い、項目の表、tier とモデルの表と応答の `model` が `qwen4.0-max-preview` であること、`[1m]` を付けない理由、前提（Token Plan の契約、キーは Model Studio のコンソール）、起動の手順（`read -rs` で非表示入力して export、ccdol と同じ形）、Rebuild の要否（#397 より前のコンテナには新しい関数が無い）、キーの確認と終了コード 1、`cc_launcher_unsets`、`/status` で確かめる項目、`settings.json` の `env` がシェルの値より優先されること、移植元の実測（2026-11-11、Claude Code 2.1.322。移植元の結果と明記）、確かめていないこと、`-p` で出る `[claude-code:unrecognized_model]` の通知。判定の説明は本リポジトリの「ASCII の英数字を 1 文字も含まない」に合わせる（移植元の「見える ASCII 文字」は使わない）

### `docs/maatlog-poc-porting.md`

移植時点の記録なので、表と R-4・R-9 は書き換えない。「### Grok Build・`ccda`」の表の後に 1 文の注記を足す: `ccda` の除外は #397 で見直し、移植元 #923 の新しい割り当てで取り入れた。この表と R-4・R-9 は移植時点の記録として残す。

## 受け入れ基準

- 動作環境: Dev Container の zsh（`~/.zshrc` は `.devcontainer/zshrc.txt` の写し）。自動テストは stub の `claude` と隔離した HOME で、実キー・課金 API を使わない
- 実入力: ランチャーの後ろの引数（`-p`・空白を含むプロンプト・`--model sonnet`・`--output-format json`）がそのまま `claude` に渡る。tier を指定しなければ opus（`qwen4-max-preview`）で起動する。キーの入力は ASCII の空白・NBSP（U+00A0）・BOM（U+FEFF）だけの値を含む
- 防御範囲:
  - 対象: `MAAS_ANTHROPIC_TOKEN` が未設定・空・ASCII の英数字を含まないとき、値を表示せず非 0 で止まり `claude` を起動しない。親シェルの `ANTHROPIC_*`・各プロバイダのキー（`MAAS_ANTHROPIC_TOKEN` を含む）が `ccda`・`ccdd`・`ccddg`・`ccdol`・`ccdgo` の子に届かない（`ccda` の子の `ANTHROPIC_AUTH_TOKEN` はこのキー）。`ccda` だけが `--dangerously-skip-permissions` を付け、`claude-alibaba` は付けない。送り先は Token Plan の URL で、`ENABLE_CLAUDEAI_MCP_SERVERS=false`
  - 対象外（反例）: 利用者が `env` などで直接 `claude` を起動した場合の漏れ、`~/.claude/settings.json` の `env` による上書き、英数字を 1 文字でも含む誤ったキー（API が 401 を返す）、ステータスライン
- 実 API: `ccda -p "1+1 の答えを数字だけで答えて" --model <tier> --output-format json` を fable・opus・sonnet・haiku で 1 回ずつ実行し、終了コード 0 で、`modelUsage` のモデルが表のとおりになる。指定のモデルが無い・応答しないときは別のモデルに替えずに止まり、実際のエラーを報告する
- `bash .devcontainer/run-tests.bash` と `bash scripts/check-layout.sh` が通る

## 対象外・編集禁止

ステータスライン（移植元の `scripts/setup_claude_statusline.py`）、移植元の `cc_launcher_require_key` への置き換え、agent-runner（`.devcontainer/agent-runner.toml`）への agent の追加、Pi・Codex など他のランタイムからの Token Plan の利用、既存のランチャーのモデルの割り当て、Alibaba 側のアカウント・キー・契約、利用者の `~/.zshrc`・`settings.json`・env ファイル、過去の Spec・Plan。

## 決定記録

| 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- |
| インラインの `*[A-Za-z0-9]*` の判定 | 移植元の `cc_launcher_require_key`（`[[:graph:]]`） | 本リポジトリの判定の方が厳しく、他のランチャーと揃う | Issue の明示。判定を緩めない |
| `ANTHROPIC_AUTH_TOKEN` だけを渡す（Bearer） | `ANTHROPIC_API_KEY` も渡す（ccdgo の形） | 移植元の実測で Bearer が 200。API キーだけだと承認まで claude.ai の OAuth が送られうる。Issue の表のとおり | Issue の明示 |
| `[1m]` を付けない | 付ける | 1M の根拠が無い（`/v1/models` が 404） | Issue の明示 |
| キーは env ファイルに書かず、使うシェルで export する | env ファイルに書く | env ファイルの変数はすべてのシェルに export され、ランチャーを通さない `claude`・pi にも渡る。`OLLAMA_API_KEY` と同じ扱い | Issue の「エージェントに任せる事項」の推奨案 |
| 既存のテストに `ccda` と `MAAS_ANTHROPIC_TOKEN` の入力を足し、キーの確認は代表 1 件を新設 | ランチャーごとに新しいテストを作る / 案内文の値の不表示も検査する | S・F∩S だけを守り、D を増やさない | AGENTS.md のテストの採用基準 |
| 「既存環境の更新」は 2026-10 の手順として残し、キーと新しい `ccda` を消させない文に書き換える | 手順を丸ごと削る | 2026-10 の移行がまだの環境の手順を失わない | Issue の「エージェントに任せる事項」 |
| `docs/maatlog-poc-porting.md` は表を保ち、注記を 1 文足す | 注記しない / 表を書き換える | 移植時点の記録を保ちつつ、読んだ人が今の状態を誤らない | Issue の「必要なら注記を足す」 |
| 新しい節は OpenCode Go の節の後に `###` で置く | 移植元と同じ `##` | 本リポジトリでは ccdol・ccdgo の節が「エージェント向けツールの導入」の中の `###` | 通常の設計判断 |
| 実装は `pi_opencode-go_deepseek4-flash_max` に Task ごとに順に依頼（2 Task） | self で実装 / 1 Task にまとめる | `implement_task.py check` が `self=false`・fallback 無し（`--implement` は利用者の指定）。コードとテスト、文書で担当ファイルが分かれる | 担当の失敗は代行せず停止 |
| Spec レビューは `pi_opencode-go_deepseek4-flash_max`（`--spec-review` は利用者の指定、fallback 無し）。builder check は行わない | builder check を併用 | issue-to-pr の規定（Spec レビューが builder check に代わる） | Spec レビューの失敗・`stop` で停止 |
| PR 修正ループは inspect `devin_swe2_max`・`pi_openai-codex_gpt6-sol_xhigh`、implement `pi_opencode-go_deepseek4-flash_max`（利用者の指定）。サイクルの上限 3、self-review・fix-check は `self`（既定の適用） | — | `check-options` の結果 | ループの停止・エラーで停止 |
| 実 API の確認は controller が実装の後に 4 tier を各 1 回行う | 実行しない / 担当に任せる | Issue が各 1 回を許す。このシェルにキーがある（値は表示しない）。費用の回数を controller が管理する | モデルが無い・応答しないなら別モデルに替えず停止して報告 |
| PR 本文は `Refs #397` | `Closes #397` | Rebuild 後のコンテナでの `/status`・対話起動は、マージの後でなければ確かめられない | マージの後に Issue へ確認項目をコメントする |
