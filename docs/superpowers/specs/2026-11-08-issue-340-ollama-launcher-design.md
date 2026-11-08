# Issue #340: Ollama Cloud の DeepSeek-V4.1-Flash-1017 で Claude Code を起動するランチャー（ccdol）

## 管理・実行許可

- 状態: `draft`（issue-to-pr の run。利用者の実行指示は実行許可として記録し、内容の承認とは扱わない）
- Issue: https://github.com/usaturn/create-reso-world/issues/340
- 移植元: usaturn/agent-workspace#852、PR usaturn/agent-workspace#855（マージコミット `08fe48278eeb2a796d439dbb8cce00cf0e83b2a2`）
- 利用者の指示（引用）:

  ```text
  /issue-to-pr https://github.com/usaturn/create-reso-world/issues/340 --merge \
        --implement claude-code_sonnet_default \
        --assign implement=claude-code_sonnet_default \
        --assign inspect=pi_openai-codex_gpt6-sol_max
  ```

- 許可された範囲: 推奨案の選択、Spec・Plan の作成、Plan の Task の runner 担当への依頼、検証（Issue が求める実 API での確認を含む）、commit・push・PR の作成、PR 修正ループ（pr-review-fix-loop）と、その中の `finalize.py` によるマージ・Issue の更新。個人設定・API キー・`settings.json` は変更しない
- 固定した base: usaturn/create-reso-world / origin / `refs/heads/main` / `25b7b5a020e5f67d74807534e1b3390a54c9c5b1`。親 Issue・handoff・要求 base は無い（`required-bases.txt` は空）。同じ Issue の PR・予約・branch・worktree は無い。#341 は Issue 本文のとおり別の節を変えるので並行できる

## 目的

Dev Container の Claude Code から、Ollama Cloud の Anthropic 互換 API（`https://ollama.com`）経由で `deepseek-v4.1-flash:1017` を使えるようにする。移植元のファイルを丸ごと置き換えず、本リポジトリのランチャー（`ccdd`・`ccddg`・`ccdu`）とテスト（`expected_unsets` の完全一致の照合）の形を保ったまま、差分を取り込む。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| ランチャーの形 | `zshrc.txt` に `function claude-ollama ccdol ()` を `ccdd` と同じ形で足す。`ccdol` だけが `--dangerously-skip-permissions` を付け、`claude --model opus "${opts[@]}" "$@"` で起動する | 実行ファイル化して agent-runner に登録する（移植元 #860） | Issue が指定し、#860 は対象外と明記している。既存の 3 関数と同じ形にすると、共通の unset と既存テストの形がそのまま使える | Issue の指定のとおり。推奨案で決定 |
| キーの検査 | `[[ ${OLLAMA_API_KEY:-} != *[A-Za-z0-9]* ]]`（ASCII の英数字を 1 文字も含まない）なら、値を出さない固定文のエラーを標準エラーに出して `return 1`。`claude` を起動しない | `${OLLAMA_API_KEY:?...}`、`[[ -z $OLLAMA_API_KEY ]]`、空白（`[[:space:]]`）を除いて空かを見る判定 | Claude Code は `ANTHROPIC_AUTH_TOKEN` を trim して空なら未設定とみなし、保存済みの claude.ai の OAuth トークンを接続先へ送る。trim は NBSP・BOM などの Unicode の空白も除くので、空だけ・`[[:space:]]`（ロケール依存）だけを見る判定では足りない（Issue。PR #342 のレビュー修正で、当初の `[[:space:]]` の判定から変えた。経緯は `2026-11-08-issue-340-ollama-launcher-review-fixes-design.md`） | Issue の指定のとおり |
| 認証の経路 | `ANTHROPIC_AUTH_TOKEN="$OLLAMA_API_KEY"`（Bearer）。`ANTHROPIC_API_KEY` は共通の unset で外したままにする | `ANTHROPIC_API_KEY`（`x-api-key`） | cloud endpoint は `x-api-key` だけでは受け付けない（Issue・移植元） | Issue の指定のとおり |
| モデルと実行時の設定 | 4 つの tier すべてに `deepseek-v4.1-flash:1017[1m]`、`CLAUDE_CODE_EFFORT_LEVEL=max`、`CLAUDE_CODE_MAX_OUTPUT_TOKENS=65536`、`ENABLE_CLAUDEAI_MCP_SERVERS=false` | 無印の `deepseek-v4.1-flash`、`:cloud`・`:1017-cloud`、`[1m]` を一部の tier だけに付ける | 版を固定し、直接接続で使える名前にする。`[1m]` は変数ごとに読まれるので 4 つすべてに付ける（Issue） | Issue の指定のとおり |
| 認証情報の漏れの防止 | `cc_launcher_unsets` と `expected_unsets` の両方に `OLLAMA_API_KEY` を足す（既存の F∩S の更新）。`zshrc.txt` とテストのコメントのランチャー名も 4 つにする | 共通の一覧に足さず、`ccdol` だけで扱う | 足さないと `ccdd`・`ccddg`・`ccdu` の子に Ollama の key が渡る。既存の完全一致の照合が、一覧の追加漏れも捕まえる | Issue の指定のとおり |
| テスト | `test_cc_launcher_env_unsets` と `test_cc_launcher_destination_and_exit_status` の対象に `ccdol`（後者は `claude-ollama` も）を足し、空白だけの `OLLAMA_API_KEY` で `claude` を起動しないテストを 1 件足す | model ID・effort・出力上限・README の文言を照合するテスト、空・未設定・改行などの入力を網羅するテスト | 足すのは S（資格情報の送り先・漏れ・誤った認証の送信）と、既存の F∩S の更新だけにする。空白だけの 1 件で、空だけを止める書き方の誤りも分かる。正しく通る例は送り先のテストの `ccdol` が持つ。固定値と網羅は「テストの採用基準」の F・D | テストの採用基準に従う |
| 引数の受け渡し | 既存の 3 関数と同じ `"$@"` にし、空白・改行を含むプロンプトと `-p` が分割・欠落しないことは、統合の確認で一時的な確認（偽の `claude`）と実 API の実行で確かめる。テストは足さない | 引数の受け渡しのテストをコミットする | 壊れると応答やエラーで分かる（L）。既存の 3 関数にもテストは無く、移植元も足していない | テストの採用基準に従う |
| README | `.devcontainer/README.md` のツールの表・第三者プロバイダの表・「3 つのプロバイダ関数」の数・「API トークン」節を更新し、「Claude Code の起動と更新」の直後に `### Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）` の節を足す。中身は Issue が挙げる項目（起動、`/status`、`settings.json` の `env` の優先、1M のコンテキストと `CLAUDE_CODE_AUTO_COMPACT_WINDOW`、effort と出力上限、対応していない機能、`-p` の `unrecognized_model`）に限る | 移植元の「動作の確認」の節も写す、別の文書に分ける | 既存の第三者プロバイダの説明と同じ場所にあると見つけやすい。本リポジトリでの実 API の確認の結果は PR 本文に書き、README に日付つきの記録を残さない（Issue の README の項目に無い） | 推奨案で決定 |
| キーの置き場所の案内 | `OLLAMA_API_KEY` は「秘密情報」の節の env ファイルの例に足さず、使うシェルで export するよう案内する。「秘密情報」節の例外の文（`MESHY_API_KEY` の次）と「API トークン」節の冒頭にも、env ファイルに書かないことを書く。起動例は、`MESHY_API_KEY` と同じく非表示入力（`read -rs`）してから export する形にする | env ファイルに書くよう案内する、起動例を `export OLLAMA_API_KEY="..."` にする | Issue の指定。利用者はホストに API キーを置かない。「秘密情報」節が「それ以外の API トークンは env に置く」と定めたままだと案内が食い違う（Task 2 のレビュー）。平文の export は端末の表示と Herdr の pane のスクロールバックに値を残す（ブランチ全体のレビュー） | 実行中の裁定で追加（Plan の「完了」）。Issue の「使うシェルで export する」は変えない |
| 実 API の確認 | 統合の確認で司令塔が行う。回数は、`-p` の 1 回（ストリーミング・thinking・Read と Bash の結果を受けた継続・サブエージェントを 1 回で確かめる）と、対話の起動で `/status` を見る 1 回。一時的なエラーは 1 回だけやり直す。中身は一時ディレクトリの無害なファイルだけにする | 実 API を使わない、runner の担当に任せる、反復して確かめる | Issue が実 API での確認を求めている。費用のかかる確認は Issue・Plan に書いた回数に限る（AGENTS.md）。対話の `/status` には Herdr の pane が要り、runner の担当は使えない | 確かめられなかったときは、その旨と確認手順を PR に書き、PR の Issue の指定を `Refs #340` にする |
| 実装方式 | `implement_task.py check --implement claude-code_sonnet_default` の結果（`self: false`、担当 `claude-code_sonnet_default`、`fallback` は空）に従い、Plan の Task を 1 つずつ runner の担当に依頼する。統合の確認は司令塔が行う | このセッションが実装する | 利用者が `--implement` で担当を指定した（`self` 以外は issue-to-pr の 4 章のとおり runner に依頼する） | 依頼が `failed`、再試行の上限に達した `retry`・`rejected` なら止まり、自分で引き取らない |
| PR 作成後 | PR 修正ループを `loop.py start` で回す。`check-options` の結果は、`max_cycles` 3（既定の適用）、`review.inspect` が `pi_openai-codex_gpt6-sol_max`（利用者の指定）、`fix.implement` が `claude-code_sonnet_default`（利用者の指定）、`fix.self-review`・`fix.fix-check` が `self`（既定の適用）、`fallback` はどれも空 | ループを回さない、独自にマージする | `--merge` の指示。マージは `finalize.py` だけが行う | ループの停止・エラーでは止まって報告する |
| PR の Issue の指定 | 実 API の確認がすべて済めば `Closes #340`。済まなければ `Refs #340` とし、ループの後に残りを Issue にコメントする | 常に `Refs #340` | 受け入れ条件の実 API の確認は、マージの前に worktree の関数で確かめられる。Rebuild は受け入れ条件に無い | 確認の結果で決める |

## 受け入れ条件と防御範囲

Issue の「受け入れ条件・検証」を、そのまま本 run の条件にする。

1. `OLLAMA_API_KEY` を export したシェルで `ccdol` を起動すると、`/status` が `Anthropic base URL: https://ollama.com`、`Model: opus (deepseek-v4.1-flash:1017[1m])`、`Auth token: ANTHROPIC_AUTH_TOKEN` を示す
2. `OLLAMA_API_KEY` が未設定・空・空白だけ（NBSP・BOM などの Unicode の空白を含む。Claude Code が trim して空とみなす値）のとき、key の値を表示せずに非 0 で止まり、`claude` を起動しない
3. 親シェルの `ANTHROPIC_*`・各プロバイダの key（`OLLAMA_API_KEY` を含む）が、`ccdol`・`ccdd`・`ccddg`・`ccdu` の子に届かない。`OLLAMA_API_KEY` は `ccdol` の `ANTHROPIC_AUTH_TOKEN` に入れた分以外では子に残らない
4. 空白・改行を含むプロンプトや `-p` などの追加引数が、分割・欠落せずに `claude` に渡る
5. README の文言・model ID・環境変数の一覧を写すだけのテストを足さない（`expected_unsets` は既存の F∩S として更新する）
6. `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` が通る
7. 実 API で、通常の応答、ストリーミング、thinking、ツール（Read・Bash など）の結果を受けた会話の継続、サブエージェントの起動を確かめる。自動のテストは実 key や課金 API に依存させない。確かめられなかったときは、その旨と確認手順を PR に書く

防御範囲:

- 対象: `ccdol`・`claude-ollama` の送り先・認証の経路・省略フラグ・MCP の無効化、`OLLAMA_API_KEY` の空白だけ（Unicode の空白を含む）の値での起動の停止、4 つのランチャーの子への親シェルの認証情報の漏れ
- 対象外の反例として、正しい key（テストの偽の値）では `ccdol` が `claude` を起動し、`ANTHROPIC_AUTH_TOKEN` に key が入ること（送り先のテスト）。`claude-ollama` は省略フラグを付けないこと
- 対象外: `.claude/settings.json`・`~/.claude/settings.json` での接続先の切り替え、Ollama の CLI・ローカルの daemon・`ollama launch claude`、agent-runner への登録、Pi 向けのランチャー、`settings.json` の `env` がシェルの値より優先される挙動そのもの（README で案内するだけ）、1M に近い長さの会話の確認

## 編集してよい範囲

- `.devcontainer/zshrc.txt`（`cc_launcher_unsets` とそのコメント、`claude-ollama`・`ccdol` の追加）
- `.devcontainer/test-herdr-migration.bash`（ランチャーのテストの対象・入力・コメントと、キーの検査のテストの追加）
- `.devcontainer/README.md`（上の決定記録の節だけ）
- この Spec と対応する Plan

それ以外（`docs/maatlog-poc-porting.md` などの過去の記録、過去の Spec・Plan、`settings.json`、個人設定）は変えない。

## 動作環境

Ubuntu 26.04 LTS の Dev Container の zsh。`zshrc.txt` は `install_beforehand.bash` が `~/.zshrc` に連結する。テストは `zsh -f` で `zshrc.txt` を読み、偽の `claude` を PATH の先頭に置いて、実 key・課金 API を使わない。実 API の確認は、Herdr の pane の対話 zsh（利用者の `~/.zshrc` が `OLLAMA_API_KEY` を export しているシェル）に、worktree の `zshrc.txt` から取り出した `cc_launcher_unsets` と `ccdol` を読み込んで行う。Claude Code は 2.1.319（移植元の確認と同じ版）。
