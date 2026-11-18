# Issue #467: 使用中のエージェント定義と Pi ラッパーを agent-workspace の現行構成に揃える

## 管理

- 状態: completed（PR #468 の修正ループ 1 サイクル目で修正不要と確認。実行許可は上記のまま。内容の承認ではない）
- Issue: https://github.com/usaturn/create-reso-world/issues/467（統合元 #466 は closed）
- 実行許可: 利用者が issue-to-pr を明示して起動した（2026-11-18。引数は `#467 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_opencode-go_deepseek4-flash_max --implement devin_swe2_max --assign implement=devin_swe2_max --assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_xhigh`）。推奨案で設計を決め、実装・検証・commit・push・PR 作成と、`--merge` の PR 修正ループ（マージは `finalize.py` だけ）まで進める許可である。内容の承認（`approved`）ではない
- 作業 base: `usaturn/create-reso-world` `main` `9d5b25af7532083884855744bb0d64d8121ea512`（Issue の基準値と同じ）
- 参照元: `usaturn/agent-workspace` `main` `bab7dd2b08a79dd66514e88bd2cfef7093424ae1`（2026-11-18 に取り直した。Issue の基準値と同じ。上流 #1069 の PR #1076、#1082 の PR #1090 を含む）

## 意図

create-reso-world と agent-workspace は同じ agent 名・Pi ラッパー名を使うのに、選ぶモデルと推論強度がずれている。runner の TOML だけを直しても、ラッパーの親 Pi と子 Pi の tier が古いまま残る。この Issue では、create-reso-world が今使っている構成に限って、参照元の最終構成（Sol・Astra の新モデル、DeepSeek V4.1 Flash の既定 `high` と Pi の明示的な `max`、Devin SWE-2 の 3 段）に揃える。参照元のファイルの丸ごとの置き換えはせず、create-reso-world 固有の処理（tier の設定分離、子 Pi の実モデル照合、Herdr の再開、`OPENCODE_API_KEY`、`--project .`）は残す。

## 目標・非目標

目標:

- runner の対象定義・親 Pi・子 Pi・Claude Code のランチャーが、下の「変更の内容」と一致する
- DeepSeek V4.1 Flash の通常の既定値が、runner・親 Pi・子 Pi・Claude Code の対象経路で `high` になる。Pi の OpenCode Go と Command Code には `_max` が明示的な選択肢として残り、runner の `max` 指定がラッパーの既定値で打ち消されない
- Devin SWE-2 の `max`・`high`・`medium` の 3 定義が共通の `model_key = "swe-2"` で解決できる
- 既存環境（更新前の tier、個人設定の上書き）への反映手順と、参照元との残す差の理由が README で分かる

非目標（Issue の対象外を引き継ぐ）:

- agent-runner 本体・runtime・レビューの仕組みの同期、#436 の Antigravity（`agy_*` の 6 定義）
- Command Code GOAT の通常配置・既定レビューへの復活、DSH・Grok Build の再導入
- DeepInfra と Claude Code 用の DeepSeek `max` 定義の追加、他モデルの effort の一括変更
- #407 の Alibaba／Claude Code の tier 説明の修正
- 過去の Spec・Plan・レビュー・評価記録の書き換え（`.agents/` の評価記録・テストの値に残る `gpt-6.1-sol` などを含む）
- 自動同期の仕組み・CI の新設、サービスの契約・課金・キー発行

失敗とみなすもの（動いても）: runner の `_max` 指定が実際には `high` で動く、DeepSeek 以外のモデル（DeepSeek V4 Flash 0731・GLM・Muse Spark など）の effort が変わる、共有の認証情報・他リポジトリの tier・利用者の個人設定をリポジトリが書き換える、キー未設定を別 provider への切り替えで隠す。

## 現状（2026-11-18 の差分）

参照元と変更先の `.devcontainer/` を突き合わせた結果。

| 対象 | create-reso-world | 参照元 |
| --- | --- | --- |
| runner の Sol（Pi・Codex）・Astra | `gpt-6.1-sol`・`gpt-6-astra` | `gpt-6.2-sol`・`gpt-6.2-astra` |
| 親 Pi の `pigs`・`piga` | `--model gpt-6.1-sol`・`--model gpt-6-astra` | `gpt-6.2-sol`・`gpt-6.2-astra` |
| 子 Pi の GPT 7 枠 | `piga.json`（balanced Sol・max Astra）、`pigt.json`（balanced Sol）、`pigs.json`（balanced・max Sol）、`pigl.json`（balanced・max Sol） | 同じ枠が `gpt-6.2-*` |
| runner の DeepSeek | `pi_commandcode_deepseek4-flash_max`・`pi_opencode-go_deepseek4-flash_max`・`claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` が `max`、`pi_deepinfra_deepseek4-flash_high` が `high` | Pi は `_high` と `_max` を併存、Ollama は `_high`、DeepInfra は `_high` のみ |
| 親 Pi の DeepSeek | `pigod`・`piccd` が `--thinking max`、`pidid` が `high` | 3 本とも `high` |
| 子 Pi の DeepSeek | 12 枠中 9 枠が `max`（`piccd` 2・`piccg` 1・`pigo` 1・`pigod` 2・`pigs` 1・`pixg` 2）、`pidid` 3 枠が `high` | 全枠 `high` |
| Claude Code の DeepSeek | `ccdd`・`ccddg`・`ccdgo`・`ccdol`・`claude-ollama-exec` が `CLAUDE_CODE_EFFORT_LEVEL=max` | 複数モデルの 3 関数は `--effort max` と `modelSettings.<DeepSeek>.maxEffortLevel = "high"`、Ollama は `--effort high` |
| 既定のレビュアー | `workflows.review.assignments.inspect` の 3 人目が `pi_opencode-go_deepseek4-flash_max` | `pi_opencode-go_deepseek4-flash_high` |
| Devin | `devin_swe2_max`・`devin_swe2_medium` | `devin_swe2_high` を加えた 3 定義 |
| `pigs` の cheap | `opencode-go/deepseek-v4.1-flash`、runner の env は `OPENCODE_API_KEY` | `opendesign-go/deepseek-v4.1-flash`、env は `OPENDESIGN_GO_API_KEY` |

確認した前提:

- runner の Pi adapter は `[*command, --print, ..., --provider P, --model M, --thinking E, ...]` を組み立てる（`tools/agent_runner/adapters/pi.py`）。ラッパーは自分の既定引数の後ろに `"$@"` を置くので、runner の `--thinking` はラッパーの既定より後ろに来る。Pi 1.5.2 の `parseArgs` は後ろの `--thinking` を採る（`['--thinking','high',...,'--thinking','max']` → `max`。共通ヘルパーの起動前の検査も同じ parser を使い、既存テスト `test_effective_parent_options_are_checked` が後ろの値で検査・起動することを確かめている）
- runner の Claude Code adapter は `--effort E` を渡す（`tools/agent_runner/adapters/claude_code.py`）。Claude Code 2.1.327 を 127.0.0.1 の受け口サーバーにつないで確かめた（記録は `tmp/agents/issue-467.vk70s9bd/spike-claude-effort.txt`）: `modelSettings.<ID>.maxEffortLevel = "high"` は独自のモデル名にも効き、`[1m]` を外した ID で `[1m]` 付きの割り当てにも効く。他のモデルは `--effort max` のまま。後ろの `--effort` と `--settings` が効く。親の `CLAUDE_CODE_EFFORT_LEVEL=max` は `--effort high` に勝つ
- 設定に残せる `effortLevel` は `low`・`medium`・`high`・`xhigh` だけで `max` を持てない（Claude Code 2.1.327 の settings のスキーマ）。複数モデルのランチャーで「DeepSeek だけ `high`、他は `max`」にする方法は、上限（`maxEffortLevel`）しかない
- Pi の保存済みカタログ（`~/.pi/agent/models-store.json`、2026-11-18 07:16 更新）に `openai-codex/gpt-6.2-sol`・`gpt-6.2-astra` がある。Pi 1.5.2 の組み込みカタログには無い。起動前にカタログと親・子の model を照合するのは `pigt`・`pidid` だけで（共通ヘルパーの `pi_launcher_require_models`）、カタログに無ければ起動を止めて `pi update --models` を案内する。`pigs`・`piga`・`pigl` の親は照合されない。子の Sol・Astra は、子 Pi の実モデル照合（`pi-superagents-model-guard.ts`）が、解決できない model での要求を送る前に止める。そのため README の既存環境の更新に、カタログの更新（`pi update --models`）と確認（`pi --list-models gpt-6.2-sol`）を書く
- Codex CLI 0.170.0 のモデルキャッシュに `gpt-6.2-sol`、Devin 3000.14 の `devin models` に `swe-2-high` がある

## 方式の比較

1. **採用: 対象の値だけを手で移す。** agent の `model`・`effort`・追加定義、ラッパーの `--model`・`--thinking`、tier の `model`・`thinking`、Claude Code のランチャーの effort の渡し方を参照元に合わせ、ファイルの構成・共通ヘルパー・setup・env は create-reso-world のものを残す。差分が小さく、固有の処理を失わない
2. 不採用: 参照元のファイルを丸ごと写し、固有の部分を戻す。`agy_*`・OpenDesign Go・`pi-superagents-tier-guard.ts`・`tools/devenv`・`OPENCODE_GO_API_KEY` を取り込んでから消すことになり、戻し忘れが「設定分離・実モデル照合・資格情報の扱いを維持する」に反する
3. 不採用: 差分を検出する同期スクリプトを作る。Issue の対象外（自動同期基盤）

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」の順に書く。

- **D1 同期の方式**: 上の方式 1。/ 別案: 方式 2・3。/ 理由: 上記。/ Issue が「具体的な編集方法」を委任。
- **D2 OpenDesign Go**: 採用しない。`pigs` の cheap は `opencode-go/deepseek-v4.1-flash` のまま `thinking` だけ `high` にし、`pigs` の runner の env は `OPENCODE_API_KEY` を維持する。`piodg`・`pi_opendesign-go_*`・`claude-code_opendesign-go_*`・`claude-opendesign-go-exec` も追加しない。/ 別案: `pigs` の cheap だけに OpenDesign Go を入れる、単独の Pi 経路も入れる。/ 理由: 採用すると `opendesign-go` の provider（`pi-models.json` と既存 `models.json` の setup）、`OPENDESIGN_GO_API_KEY` の受け渡し、`pi-opendesign-go-reasoning.ts` の配置と子 Pi での読み込み、思考内容が黙って落ちないことの確認が増える。維持なら tier の 1 枠の値の変更で済み、実装が簡易にならないので、利用者の採用条件に当たらない。/ Issue が条件付きで委任（簡易になる場合だけ採用）。
- **D3 Pi の DeepSeek の runner 定義**: `pi_opencode-go_deepseek4-flash_high`・`pi_commandcode_deepseek4-flash_high` を足し、既存の `_max` を明示選択用に残す。`_high` と `_max` は `runtime`・`command`・`model`・`model_key`・`provider`・`env` を同じにし、`effort` だけを分ける。`env` は今の `_max` と同じ（OpenCode Go は `OPENCODE_API_KEY`、Command Code は `COMMANDCODE_API_KEY`）。`_high` を `_max` の直前に置く（参照元の並び）。/ 別案: `_max` を `_high` に改名する（#466 当初の案）。/ 理由: Issue の決定（2026-11-18 の更新指示）で、既定の `high` と明示選択の `max` を両立する。/ 利用者の決定。
- **D4 Ollama の runner 定義**: `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` を `claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high`（`effort = "high"`）に改名する。旧名は残さない。/ 別案: `_max` を残して `_high` を足す。/ 理由: Issue の第 3 項「Claude Code 用の `max` 定義は追加しない」「Ollama のように `_high` へ移す定義」。どの既定割当にも入っていないので、雛形の参照の更新は不要。/ 利用者の決定。
- **D5 既定のレビュアー**: `workflows.review.assignments.inspect` の 3 人目を `pi_opencode-go_deepseek4-flash_high` にする。他の割当（`claude-code_opus_xhigh`・`devin_swe2_max`、fix・issue の `self`）は変えない。/ 理由: Issue の第 3 項。/ 利用者の決定。
- **D6 親 Pi の DeepSeek**: `pigod`・`piccd` の `--thinking max` を `high` にする。`pidid` は `high` のまま。DeepSeek 以外を親に使う `pigo`・`piccg`（Muse Spark）・`piaq`（Qwen）・`pixg`（Grok）の親の値は変えない。コメントの「`--thinking max` は受理される」を `high` の説明に直す。/ 理由: Issue の第 3 項。runner の `_max` は後ろの `--thinking max` で上書きされる（確認した前提）。/ 利用者の決定。
- **D7 子 Pi の DeepSeek**: 12 枠中の `max` の 9 枠を `high` にする（`piccd.json` の balanced・max、`piccg.json` の max、`pigo.json` の max、`pigod.json` の balanced・max、`pigs.json` の cheap、`pixg.json` の cheap・balanced）。DeepSeek 以外の枠（Muse Spark・Grok・Qwen・GPT・Gemini）の `thinking` は変えない。親に `_max` を選んでも子の tier は変えない。/ 理由: Issue の第 3 項。/ 利用者の決定。
- **D8 GPT のモデル**: Sol を `gpt-6.2-sol`、Astra を `gpt-6.2-astra` にする。対象は runner の `pi_openai-codex_gpt6-sol_xhigh`・`pi_openai-codex_gpt6-astra_xhigh`・`codex_openai_gpt6-sol_default`、親の `pigs`・`piga`、子の 7 枠。agent 名（`gpt6-sol`・`gpt6-astra`）、Terra（`gpt-6.1-terra`）・Luna（`gpt-6-luna`）、`thinking` は変えない。runner のコメントの「実測既定モデルは gpt-6.1-sol」は、参照元に合わせて「model は runner が -m で渡す。Codex CLI のモデル一覧に gpt-6.2-sol がある（2026-11-18）」にする。/ 理由: Issue の第 2 項。/ 利用者の決定。
- **D9 Devin**: `devin_swe2_high`（`model = "swe-2-high"`、`model_key = "swe-2"`、`runtime = "devin"`、`command = ["devin"]`、`env = ["HOME", "PATH"]`）を `devin_swe2_max` と `devin_swe2_medium` の間に足し、コメントを「3 つは同じ model_key」に直す。既定割当は変えない。/ 理由: Issue の第 3 項。/ 利用者の決定。
- **D10 複数モデルの Claude Code ランチャー**: `ccdd`・`ccddg`・`ccdgo` は `CLAUDE_CODE_EFFORT_LEVEL=max` をやめ、`env` に `-u CLAUDE_CODE_EFFORT_LEVEL` を足し、`claude --effort max --settings '{"modelSettings":{"<DeepSeek V4.1 Flash の ID>":{"maxEffortLevel":"high"}}}' --model opus ...` で起動する。ID は `ccdd` が opus の `deepseek-ai/DeepSeek-V4.1-Flash`、`ccddg` が fable の `deepseek-ai/DeepSeek-V4.1-Flash`、`ccdgo` が opus の `deepseek-v4.1-flash`（`[1m]` を外す）。`--settings` の JSON はランチャーの局所変数から組み立て、モデル名を二重に書かない。/ 別案: (a) `CLAUDE_CODE_EFFORT_LEVEL=high` にする（他モデルも `high` になり、DeepSeek V4 Flash 0731 などの一括変更に当たる）、(b) 設定の `modelSettings.<ID>.effortLevel = "high"` で既定だけを変える（他モデルを `max` にする手段が `--effort max` か環境変数しかなく、どちらも DeepSeek の既定を上書きする。`effortLevel` は `max` を持てない）。/ 理由: 他モデルを `max` に保ちながら DeepSeek だけを `high` にできる唯一の方法で、参照元と同じ。上限は利用者が後ろの `--settings` で外せ、後ろの `--effort` で上限以下の値も選べる（確認した前提）ので、利用者の明示的な上書きを禁止しない。/ Issue が方法を委任。
- **D11 Ollama の Claude Code**: `ccdol` と `claude-ollama-exec` は 4 つの tier すべてが DeepSeek V4.1 Flash 1017 なので、`CLAUDE_CODE_EFFORT_LEVEL=max` をやめ、`env` に `-u CLAUDE_CODE_EFFORT_LEVEL` を足し、`claude --effort high ... "$@"` を既定にする（後ろの `--effort` が効く）。`ccdol` は `claude-ollama-exec` を呼ばない今の構成を保つ（参照元は呼ぶが、モデル・effort だけが Issue の対象で、実装方式の置き換えは要らない）。`claude-ollama-exec` の `exec env` の `-u` は、親の認証情報を外す既存の項目を変えず、`-u CLAUDE_CODE_EFFORT_LEVEL` を 1 つ足す（`ccdol` も同じく足す。Spec レビュー S4 の採用）。/ 別案: `CLAUDE_CODE_EFFORT_LEVEL=high`（後ろの `--effort` が効かなくなり、利用者の明示的な上書きを禁止する）。/ 理由: 参照元と同じで、確認した前提のとおり親の環境変数を外さないと `--effort` が負ける。/ Issue が方法を委任。
- **D12 Alibaba の Claude Code**: `ccda`・`claude-alibaba-exec` は Qwen なので変えない。/ 理由: 対象外（#407）。
- **D13 setup の表示**: `scripts/setup_pi_opencode_go.zsh` の共通の `THINKING="max"` を、ランチャーごとの `LAUNCHER_THINKING=(max high)`（`pigo`・`pigod` の順）に分け、完了時の表示に各ランチャーの `--thinking` を出す。`scripts/setup_pi_commandcode_goat.zsh` は `PICCG_THINKING="max"`・`PICCD_THINKING="high"` に分ける。setup がランチャーの本文で検証するのは、`setup_pi_opencode_go.zsh` が `--model` だけ、`setup_pi_commandcode_goat.zsh` が `--provider`・`--model`・`--models` で、どちらも `thinking` の値は表示だけに使う（2026-11-18 に確認。Spec レビュー 2 回目の S1 で書き分けた）。/ 理由: 表示が実際の起動引数とずれると、既存環境の確認を誤らせる。参照元と同じ。/ 委任。
- **D14 README**: `.devcontainer/README.md` の現行の値を述べる箇所（下の「変更の内容」の README の項）を新しい値に直し、新しい節「agent-workspace の現行構成との同期（#467）」に、DeepSeek の推論強度・`max` の agent・DeepInfra に `_max` を置かない理由・Claude Code の上限と外し方・Pi で `/model` を切り替えたときの thinking・既存環境の更新・個人設定の確認・参照元との残す差を書く。#305・#337・#341 などの当時の変更記録の表と、移植元・実機の観測の記録は書き換えない。/ 理由: Issue の受け入れ条件（意図的な除外と既存環境の反映手順が分かる）。/ 委任。
- **D15 テスト**: S の恒久テストを 2 つだけ足す（Spec レビュー S1・S2 の採用）。設定値の写し（モデル名・effort の一覧）は F なので足さない。既存テストの期待値は、変更で壊れるものがあれば合わせる。
  - (a) `.devcontainer/test-pi-superagents.bash` に、runner の明示した `--thinking` がラッパーの既定に打ち消されないことのテストを 1 つ足す。代表は `pigod`（`piccd` は同じ形なので D として足さない）。`PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` で runner と同じ argv（`--print --mode json --no-session --no-approve --provider opencode-go --model deepseek-v4.1-flash --thinking <値>`）を渡し、Pi に渡る引数を Pi 自身の `parseArgs` で解析して、実効の thinking が `max` のときは `max`、`high` のときは `high` になることを確かめる（通る例と、既定と違う値の両方）。壊れると runner の `_max` が黙って `high` で動き、エラーにならない（S）。既存の `test_effective_parent_options_are_checked` は共通ヘルパーを `pidid` で直接呼ぶもので、ラッパーの引数の順序は確かめない
  - (b) `.devcontainer/test-herdr-migration.bash` に、`ccdd`・`ccddg`・`ccdgo`・`ccdol` と `claude-ollama-exec` が、親シェルで export された `CLAUDE_CODE_EFFORT_LEVEL` を子の `claude` に渡さないことのテストを 1 つ足す（偽の `claude` で子の環境を記録する。`ccda` は自分で `max` を代入するので対象外）。base ではランチャーの代入が親の値を上書きしていたので漏れなかったが、この変更で代入をやめるため、`-u` が抜けると親の値が `--effort` の既定に黙って勝つ（S。回帰の防止）。5 つの入口は別々に `-u` を持つので、1 つのテストで全部を回す
  - 別案: 恒久テストを足さず、実行の確認だけにする（当初の案）。/ 理由: Spec レビューの指摘のとおり、(a) は既存のテストと守りが違い（D ではない）、(b) は今回の変更で新しくできる漏れの経路で、どちらも壊れてもエラーにならない。/ 委任（AGENTS.md「テストの採用基準」）。値の確認（Claude Code が実際に送る effort、子 Pi の tier）は、一時 HOME・偽 CLI・受け口サーバーの実行で行い、結果を PR に書く
- **D16 Spec・設計レビュー**: 利用者の指定どおり、設計レビュー（`pi_openai-codex_gpt6-sol_xhigh`）→ Spec レビュー（`pi_opencode-go_deepseek4-flash_max`）の順に行い、builder check は行わない。/ 利用者の指定。

## 変更の内容

### `.devcontainer/agent-runner.toml`

- `pi_openai-codex_gpt6-sol_xhigh`: `model = "gpt-6.2-sol"`（env は `OPENCODE_API_KEY` のまま）
- `pi_openai-codex_gpt6-astra_xhigh`: `model = "gpt-6.2-astra"`
- `codex_openai_gpt6-sol_default`: `model = "gpt-6.2-sol"`、コメントを D8 のとおりに直す
- `devin_swe2_high` を足す（D9）
- `pi_commandcode_deepseek4-flash_high`・`pi_opencode-go_deepseek4-flash_high` を足す（D3）
- `claude-code_ollama_opus_max`・`claude-code_ollama_sonnet_max` → `claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high`、`effort = "high"`（D4）。前のコメントの「既存の DeepSeek V4.1 Flash 系 3 agent」の列挙を、Pi の `_high`・`_max` を含む現在の名前に直す
- `workflows.review.assignments.inspect` の 3 人目を `pi_opencode-go_deepseek4-flash_high`（D5）
- DeepInfra の定義の前に、`_max` を置かない理由のコメントを足す（DeepInfra の reasoning_effort の上限は high で、`pidid` の起動前の検査が runner の後ろの `--thinking max` を未対応の thinking として止める。素の Pi は high に丸める。実装中の訂正: 当初は「Pi は --thinking max を high に丸める」と書いていたが、`pidid` は起動前の検査（`pi_launcher_require_models`）を通るので、Task 4 のレビューの指摘で直した）
- `after_run` の `--project .`、`issue.implement` の `self`、`roles`、他の agent は変えない

### Pi のラッパーと tier

- `.devcontainer/pigs`: `--model gpt-6.2-sol`
- `.devcontainer/piga`: `--model gpt-6.2-astra`
- `.devcontainer/pigod`: `--thinking high` とコメント
- `.devcontainer/piccd`: `--thinking high`
- `.devcontainer/pi-superagents/{piga,pigt,pigs,pigl}.json`: GPT の 7 枠（D8）
- `.devcontainer/pi-superagents/{piccd,piccg,pigo,pigod,pigs,pixg}.json`: DeepSeek の 9 枠（D7）
- `superagents.extensions`（`pi-superagents-model-guard.ts`）と共通ヘルパー・setup の配置処理は変えない

### Claude Code

- `.devcontainer/zshrc.txt` の `ccdd`・`ccddg`・`ccdgo`（D10）と `ccdol`（D11）。関数の前のコメントに、DeepSeek の上限・既定の理由を 1〜2 行で書く
- `.devcontainer/claude-ollama-exec`（D11）。冒頭のコメントの呼び出し元の名前を `_high` に直す

### setup

- `scripts/setup_pi_opencode_go.zsh`・`scripts/setup_pi_commandcode_goat.zsh` の thinking の表示（D13）

### テスト

- `.devcontainer/test-pi-superagents.bash` と `.devcontainer/test-herdr-migration.bash` に D15 の (a)・(b) を 1 つずつ足す。各テストの前のコメントに、防ぐ損害（S）を書く

### `.devcontainer/README.md`

現行の値を述べる箇所を直す（当時の記録は除く）。

- 「Ollama Cloud の DeepSeek-V4.1-Flash-1017（ccdol）」: effort の表の行（`effort（CLAUDE_CODE_EFFORT_LEVEL） | max`）と「effort と出力上限」（`--effort high` が既定、後ろの `--effort` が効く、親の `CLAUDE_CODE_EFFORT_LEVEL` は外す）、agent-runner の表・例の Ollama の agent 名を `_high` にする。`duplicate_model` の列挙は、Ollama の 2 agent を `_high` の名前に置き換え、Pi の DeepSeek は `pi_commandcode_deepseek4-flash_high`・`_max`、`pi_opencode-go_deepseek4-flash_high`・`_max`、`pi_deepinfra_deepseek4-flash_high` を列挙する（残す `_max` も同じ `model_key` であることが分かるように。Spec レビュー 2 回目の S2）
- 「Claude Code の起動と更新」: `ccdd`・`ccddg`（DeepInfra）と `ccdgo` の DeepSeek の上限（`--effort max` と `--settings` の `maxEffortLevel`、上限の外し方）を、ランチャーの対応表の後に書く。「OpenCode Go のモデルで Claude Code を起動する（#368）」の表の `effort（CLAUDE_CODE_EFFORT_LEVEL） | max` の行と「effort と出力上限」も、`--effort max`（DeepSeek は上限で `high`）に直す（Spec レビュー 2 回目の S3）。「移植元 PR #868 で確認したこと」の観測の記録は書き換えない
- 「agent の命名と同一モデルの比較」: 既定の `review.inspect`、追加 agent の表の Astra のモデル、`model_key` の説明（Pi の `_high`・`_max`、Ollama の `_high`、Devin の 3 定義）、Ollama の agent 名
- 「旧担当からの個人設定の移行」「Command Code GOAT の契約終了後の移行」「Devin の agent 名の変更（#341）」の現行の推奨先・定義名
- 「モデル定義の管理」の `pigod`・`piccd` の `--thinking` の説明
- 「ChatGPT Pro の GPT-6 ランチャー」のモデル表と `pi --list-models` の例（`pi update --models` を先に案内する）
- 「API トークン」の agent 名の表
- 「pi-superagents のランチャー別 model tier」の表のモデルと、表の下の thinking の説明（`pigs` の cheap と `pixg` の cheap・balanced を `high` にする。Spec レビュー S3 の採用）
- 新しい節「agent-workspace の現行構成との同期（#467）」（「Devin の agent 名の変更（#341）」の後）:
  - DeepSeek V4.1 Flash の推論強度: 対象の経路と既定 `high`、Claude Code の上限と外し方、Ollama の既定、Pi で `/model` を切り替えたときは Pi の `modelThinkingLevels` が決めること（リポジトリはユーザ設定を書き換えない）
  - `max` の agent: Pi の 2 経路の `_max` は既定の割当に入らず、`--assign` か個人設定で選ぶ。`_high` と同じ `model_key` なので同じ役割に並べると `duplicate_model`。DeepInfra に `_max` を置かない理由（`pi-models.json` の `thinkingLevelMap` が `max` を `null` にしており、`pidid` の起動前の検査が `max` を未対応の thinking として止めるので、`_max` を作っても起動しない。素の Pi は対応する最大の `high` に丸める。上の agent-runner.toml の項と同じ実装中の訂正）
  - 既存環境の更新: Rebuild で `zshrc.txt`・`install_beforehand.bash` が置くラッパー（`pigod`・`pigs`・`piga`・`claude-ollama-exec` など）が更新される。`piccd`・`piccg` は Rebuild で更新されないので、使う場合だけ `zsh scripts/setup_pi_commandcode_goat.zsh` を再実行する。子 Pi の tier は Rebuild（`--if-absent`）では更新されないので、ランチャーの外のシェルでリポジトリのルートから `zsh scripts/setup_pi_superagents.zsh` を実行する（既存の設定は `config.json.bak.*` に退避される）。tier を手で編集している場合は、退避した設定と見比べて必要な編集を戻す。モデルカタログは `pi update --models` で更新し、`pi --list-models gpt-6.2-sol` などで確かめる
  - 個人設定の確認: (1) 旧モデル（`gpt-6.1-sol`・`gpt-6-astra`）・Ollama の旧 `_max` 名を `grep` で探すコマンド。(2) この Issue で値を変えた・足した agent（`pi_openai-codex_gpt6-sol_xhigh`・`pi_openai-codex_gpt6-astra_xhigh`・`codex_openai_gpt6-sol_default`・`pi_opencode-go_deepseek4-flash_high`・`pi_opencode-go_deepseek4-flash_max`・`pi_commandcode_deepseek4-flash_high`・`pi_commandcode_deepseek4-flash_max`・`claude-code_ollama_opus_high`・`claude-code_ollama_sonnet_high`・`devin_swe2_high`）の `[agents.*]` 節が個人設定にあるかを探し、あればその節の `model`・`effort`・`provider`・`env` を雛形の同じ節と見比べるコマンド（Spec レビュー 2 回目の S4）。(3) 見つかったときの直し方: 雛形と同じ値か、意図しない値なら節を消して雛形を継承する。意図して変えている値だけを残す。割当の旧名は `_high` へ書き換える。`check` は未知の agent 名を拒否するが、同名の節の上書きは `list` に出ないので、(2) で見ないと気付けないことを書く
  - 参照元との残す差: OpenDesign Go（D2）、`agy_*`（#436）、Command Code の通常配置外（#337）、`pi-superagents-model-guard.ts` とリポジトリ別の tier の配置（#310・#313）、`OPENCODE_API_KEY`（#365）、`after_run` の `--project .`、DSH・Grok Build を入れないこと

## 受け入れ基準

### 動作環境

- 既存の Ubuntu Dev Container（Pi 1.5.2、Claude Code 2.1.327、Codex CLI 0.170.0、Devin 3000.14）
- 新規の環境（tier・個人設定が無い）と、更新前の tier・個人設定の上書きがある環境を区別する。確かめるのは一時 HOME での新規配置と、更新前の tier が残る場合の案内（起動前の検査の結果と README の手順）
- 実サービスへの要求はしない。外部 API の実応答は未確認として扱う

### 実入力

- runner の雛形: `uv run --project . --locked python -m tools.agent_runner --template .devcontainer/agent-runner.toml --config <空の個人設定> check`・`list`。`--assign inspect=pi_opencode-go_deepseek4-flash_high,pi_opencode-go_deepseek4-flash_max` のように同じ `model_key` を並べた設定は `duplicate_model` で拒否される
- runner の Pi の argv: `pigod --print --mode json --no-session --no-approve --provider opencode-go --model deepseek-v4.1-flash --thinking max`（`_max`）と `--thinking high`（`_high`）を、共通ヘルパーの `PI_SUPERAGENTS_LAUNCHER_DRY_RUN=1` と Pi の `parseArgs` で解析し、実効の thinking がそれぞれ `max`・`high` になる。runner の引数なしの直接起動は `high`
- 子 Pi の tier: setup で一時 HOME に配置した `config.json` の DeepSeek の枠がすべて `high`、DeepSeek 以外の枠は変更前と同じ
- Claude Code: 受け口サーバー（127.0.0.1）に向けた `zshrc.txt` と `claude-ollama-exec` の写しで、`ccdd`（opus）・`ccddg`（fable）・`ccdgo`（opus）の DeepSeek が `high`、`ccdd` の fable（GLM-5.3）と sonnet（DeepSeek V4 Flash 0731）・`ccddg` の opus（GLM-5.3-Flash）・`ccdgo` の sonnet（Muse Spark）が `max`。`ccdol`・`claude-ollama-exec` は `high`、後ろの `--effort max` で `max`、親の `CLAUDE_CODE_EFFORT_LEVEL=max` があっても `high`。プロンプトは改行と日本語を含む 1 件（例: `確認\n日本語の行`）

### 防御範囲

- 対象: 上の「変更の内容」の agent・ラッパー・tier・ランチャー。DeepSeek V4.1 Flash の判定は provider のモデル ID と Claude Code の別名の割り当てで行う（`opus`・`sonnet` という名前では判定しない）
- 対象外の反例（変えないことを確かめる）: DeepSeek V4 Flash 0731、GLM、Muse Spark、Hy4、gpt-oss、Qwen、Grok、Gemini の effort・thinking。`pigo`・`piccg`・`piaq` の親の `--thinking max`。`ccda`・`claude-alibaba-exec`。Terra・Luna のモデル。`cc_launcher_unsets` の一覧。共通ヘルパー・`pi-superagents-model-guard.ts`・setup の配置処理。利用者の `~/.pi`・`~/.config/agent-runner`（検証は一時 HOME と空の個人設定で行う）
- 残す `_max`: Pi の OpenCode Go・Command Code の `_max` は雛形に残り、`check`・`list` で解決できる

## 検証

- `check`・`list`（上の実入力）と、`duplicate_model` の拒否の 1 件
- D15 の 2 つのテスト。(b) は変更の前（親の値ではなくランチャーが代入した `max` が子に届く）に失敗し、変更の後に通ることを確かめる。(a) は base でも引数の順序が正しいので通る。ラッパーの `"$@"` を既定の引数より前に動かした一時的な写しで失敗することを確かめる（写しは commit しない）
- `bash .devcontainer/run-tests.bash .devcontainer/test-pi-superagents.bash .devcontainer/test-herdr-migration.bash`（関連する既存テスト）と、変更が他に影響しないことを確かめるための `bash .devcontainer/run-tests.bash`（全体）
- `uv run --project . --locked pytest tools/agent_runner -q`（雛形の名前を参照するテストが無いことの確認を兼ねる）
- `scripts/check-layout.sh`
- 一時 HOME と偽 CLI での親引数・子 tier の確認、受け口サーバーでの Claude Code の確認（上の実入力）
- `git grep` で、現行の設定・ラッパー・README の現行の記述に旧モデル（`gpt-6.1-sol`・`gpt-6-astra`）・Ollama の旧 `_max` 名・DeepSeek の `max` の取り残しが無いこと（当時の記録・評価記録は除く）
- 参照元と採用／除外表・実ファイルの突き合わせ（PR 作成前に 1 回）

## 担当とループの設定（helper の検査結果）

- Plan の Task の実装: `--implement devin_swe2_max`（利用者の指定）。`assignment` は `agents = ["devin_swe2_max"]`、`fallback = []`（個人設定に fallback なし）、`self` は false
- 設計レビュー: `--design-review pi_openai-codex_gpt6-sol_xhigh`（利用者の指定）、`fallback = []`
- Spec レビュー: `--spec-review pi_opencode-go_deepseek4-flash_max`（利用者の指定）、`fallback = []`
- PR 修正ループ（`check-options` の結果）: `max_cycles = 3`（既定の適用）、`assign.implement = ["devin_swe2_max"]`・`assign.inspect = ["devin_swe2_max", "pi_openai-codex_gpt6-sol_xhigh"]`（利用者の指定）、`fix.self-review`・`fix.fix-check` は `self`（雛形の既定の適用）、`template` は `.devcontainer/agent-runner.toml`（既定の適用）
- レビューと担当の runner は、親 checkout（`/workspaces/reso-world`、`main` の `9d5b25af`）の雛形を使う。この PR の雛形の変更（`_high` の追加、Ollama の改名）は、マージされるまで runner の担当の選択に影響しない

## レビュー記録

### 設計レビュー 1 回目

- helper: `review_design.py`（外部担当）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-467.vk70s9bd/2026-11-18-issue-467-agent-workspace-sync-design.design-review/review-1`、`review_id`: `aca87ba83d79459bacef3bdceb929e3c`
- reviewed の Spec の SHA-256: `70929637e5ab43316df47ceacff8c01d65f2bfefe2a82ae41242919030a656a3`（commit `e31e38f7`）
- 担当: `requested_agent` と `actual_agent` は `pi_openai-codex_gpt6-sol_xhigh`（利用者の明示値。`fallback` は無く、使っていない）。identity は provider `openai-codex`・model `gpt-6.1-sol`・effort `xhigh`（親 checkout の雛形と `pigs` は、この PR のマージ前なので `gpt-6.1-sol` のまま）。`elapsed_seconds` は 184.5
- 結果: `verdict: sound`、`concerns` 0 件、`questions_for_user`・`incomplete` なし。採否に含める指摘は無い
- `outside_changes`: なし。`unprotected_changes`: `/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*` の 6 つの worktree（他の作業の prunable な登録で、この run は触れていない）
- レビューと別の訂正（controller）: 「確認した前提」の Pi のカタログの照合の記述を、実装（照合は `pigt`・`pidid` だけ）に合わせて直した。設計の決定は変えていない

### Spec レビュー 1 回目

- helper: `review_spec.py`（外部担当）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-467.vk70s9bd/2026-11-18-issue-467-agent-workspace-sync-design.spec-review/review-1`、`review_id`: `de3209fff40f453d8d9949b862c286c4`
- reviewed の Spec の SHA-256: `3e68f784443ec107f3590d581c4413953e11604ad3c7534be5324f8aca05196d`（commit `7281b3f2`）
- 担当: `requested_agent` と `actual_agent` は `pi_opencode-go_deepseek4-flash_max`（利用者の明示値。`fallback` は無く、使っていない）。identity は provider `opencode-go`・model `deepseek-v4.1-flash`・effort `max`。`elapsed_seconds` は 1127.0
- `outside_changes`: なし。`unprotected_changes`: 設計レビューと同じ `/tmp` の 6 つの worktree（他の作業のもの）
- 採否:
  - S1（important、D15 の Pi の `_max` とラッパーの既定）: 採用。既存のテストは共通ヘルパーを `pidid` で直接呼ぶだけで、ラッパーの引数の順序を確かめない。D15 (a) のテストを足す
  - S2（important、D15 の Claude Code の親の `CLAUDE_CODE_EFFORT_LEVEL`）: 採用。この変更で代入をやめるので、`-u` が抜けると親の値が黙って漏れる新しい経路になる。D15 (b) のテストを足す
  - S3（minor、README の tier の thinking の説明）: 採用。D14 の README の項に足した
  - S4（minor、D11 の `-u` の一覧の書き方）: 採用。既存の項目を変えずに `-u CLAUDE_CODE_EFFORT_LEVEL` を足すと明記した

### Spec レビュー 2 回目（再レビュー）

- helper: `review_spec.py`（外部担当、同じ担当）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-467.vk70s9bd/2026-11-18-issue-467-agent-workspace-sync-design.spec-review/review-2`、`review_id`: `e63ef144234d4d3d8f72038fa810e861`
- reviewed の Spec の SHA-256: `869285038afa2c831cd65d7fdd4e8969ffd303d7d6f55a532e6c63a52e4dfb0c`（commit `bf49930e`）
- 担当: `requested_agent` と `actual_agent` は `pi_opencode-go_deepseek4-flash_max`。identity は provider `opencode-go`・model `deepseek-v4.1-flash`・effort `max`。`elapsed_seconds` は 1673.9
- `outside_changes`: なし。`unprotected_changes`: 1 回目と同じ `/tmp` の 6 つの worktree
- 採否:
  - S1（minor、D13 の setup の検証範囲）: 採用。スクリプト別に書き分けた
  - S2（minor、README の `duplicate_model` の列挙）: 採用。Pi の `_high`・`_max` の両方を列挙すると README の項に書いた
  - S3（minor、OpenCode Go の effort の表の行）: 採用。README の項に表の行と DeepInfra 側の上限の説明を明記した
  - S4（important、個人設定の上書きの確認）: 採用。値を変えた・足した agent の `[agents.*]` 節を探して雛形と見比べる手順を README の項に足した

## PR 修正ループ（review-fix-planning）

### サイクル 1（HEAD `67be70df506efc73fadd8e3126493472c7c1e0f0`）

- loop run: `d2a876862b654b42b91b4b1cf9cd92ab`。planner: claude-opus-5-5（claude-code）。実行許可は、利用者の `--merge` による issue-to-pr の PR 修正ループ（判断の基準・三択の結論は review-fix-planning のとおり。マージは `finalize.py` だけ）
- レビュアーの構成（利用者の `--assign inspect=devin_swe2_max,pi_openai-codex_gpt6-sol_xhigh`）:

| レビューファイル | モデル（観測） | ランタイム | レビュー HEAD | このサイクルで再実行 | 結果 | Merge recommendation |
|---|---|---|---|---|---|---|
| `SWE-2-Max.md` | SWE-2 Max | devin | `67be70df506e` | はい | 受け付け、指摘 0 件 | Approve |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `67be70df506e` | はい | 受け付け、Low 1 件（L-1） | Approve |

- 確認済みの一覧: `reviews/usaturn/create-reso-world/#468-feat-issue-467-agent-workspace-sync/verified/67be70df506e.json`（confirmed 1、unverified 0、remaining なし）
- 分類: 解消済み 0 / 対応する 0 / 対応しない 1
  - 対応しない `gpt-6.1-sol#L-1@67be70df506e`: README（と Plan）の個人設定の確認 (2) の grep は、引用符・空白の無い `[agents.<名前>]` しか見つけない。隔離 worktree で確かめると、runner が上書きとして受け入れる TOML の別の書き方 7 つ（引用符付き 2 種、空白入り 2 種、字下げ、インライン表、ドット区切りのキー）を見落とす。ただし、個人設定の雛形（`agent-runner-personal.toml`）・README の例・`install_beforehand.bash` が置く設定はすべて引用符・空白の無い形で、agent 名も引用符の要らない文字だけなので、その書き方の個人設定は実在しない。手順のとおりに使って誤った結果になる発生条件に、実在する構成から到達しない（網羅の粗さ）。見直す条件: 引用符付き・ドット区切りのキー・インライン表で agent を上書きする雛形・手順・利用例が現れたとき、または利用者が指定したとき
- 要件対応: Spec の受け入れ基準（動作環境・実入力・防御範囲）の各条件は、PR 作成前の検証（PR 本文の「検証結果」）で確かめ済み。L-1 は確認手順の網羅の範囲で、受け入れ条件「個人 override の確認方法がある」は、引用符・空白の無い形（実在する構成）で満たす
- 結論: 2（修正不要）。自己レビューは結論 1 だけで行うので未実施
- 検証: 同じ HEAD の clean な worktree で記録した必須検証（`bash .devcontainer/run-tests.bash` 27 本 PASS、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools -q` 1614 passed、空の個人設定での runner の `check`・`list`）がすべて終了コード 0。base `9d5b25af` は head の祖先なので、merge したツリーでの検証は不要
