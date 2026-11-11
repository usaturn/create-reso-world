# Issue #402: Token Plan の qwen4-max-preview で Pi を起動する piaq と runner agent の取り込み

## 管理・実行許可

- 状態: `draft`
- 対象: usaturn/create-reso-world #402（https://github.com/usaturn/create-reso-world/issues/402）
- 利用者の指示（2026-11-11）:

  ```text
  /issue-to-pr #402 --merge
  --spec-review devin_swe2_max
  --design-review pi_openai-codex_gpt6-sol_xhigh
  --implement devin_swe2_max
  --assign implement=devin_swe2_max
  --assign inspect=pi_xai_grok4_xhigh,pi_openai-codex_gpt6-sol_xhigh
  途中でメインがマージされたら、追随して作業を止めずに続行してください。
  ```

- 許可された範囲: issue-to-pr による推奨案での設計・Spec・Plan・実装・検証・commit・push・PR 作成と、`--merge` による PR 修正ループと `finalize.py` のマージ。これは実行許可であり、この Spec の内容の承認（`approved`）ではない
- 2 回目の指示（2026-11-11 22:0x、Task 2 の `failed` で止まった後）:

  ```text
  /issue-to-pr #402 --merge
  --spec-review pi_xai_grok4_xhigh
  --design-review pi_openai-codex_gpt6-sol_xhigh
  --implement pi_xai_grok4_xhigh
  --assign implement=pi_xai_grok4_xhigh
  --assign inspect=pi_xai_grok4_xhigh,pi_openai-codex_gpt6-sol_xhigh
  途中でメインがマージされたら、追随して作業を止めずに続行してください。
  ```

  既存の worktree・branch が残っていたので進め方を利用者に尋ね、「Task 2 から続ける」の回答を得た。設計レビューと Spec レビューは 1 回目の run の結果を使い、やり直さない（今回の `--spec-review`・`--design-review` の担当は使わない）。Task 2 以降の実装は `pi_xai_grok4_xhigh`（`--implement` の明示。fallback なし）、PR 修正ループは inspect が `pi_xai_grok4_xhigh`・`pi_openai-codex_gpt6-sol_xhigh`、fix の implement が `pi_xai_grok4_xhigh`（`--assign` の明示）、self-review・fix-check は `self`、サイクルの上限 3（既定の適用）
- base の追随: 作業中に `origin/main` が進んだら、利用者の指示に従い、止まらずに feature branch へ `origin/main` を merge（rebase・force push はしない）し、検証をやり直してから続ける。旧・新の SHA と取り込んだ差分は SESSION の記録と PR 本文に書く
- 担当（2 章の検査の結果）:
  - Plan の Task の実装: `devin_swe2_max`（`--implement` の明示。fallback なし）
  - 設計レビュー: `pi_openai-codex_gpt6-sol_xhigh`（`--design-review` の明示。fallback なし）
  - Spec レビュー: `devin_swe2_max`（`--spec-review` の明示。fallback なし）。Spec レビューがあるので builder check は行わない
  - PR 修正ループ: inspect は `pi_xai_grok4_xhigh`・`pi_openai-codex_gpt6-sol_xhigh`、fix の implement は `devin_swe2_max`（どちらも `--assign` の明示）。self-review・fix-check は `self`、サイクルの上限 3（どちらも既定の適用）

## 目的

usaturn/agent-workspace#928（PR #931、マージコミット `4c425ab1dd3afe55192e752d179af566b0650a23`）の、Alibaba Cloud Model Studio の Token Plan の `qwen4-max-preview` で Pi を起動するランチャー `piaq` と、runner agent `pi_alibaba_qwen4-max_max` を取り込む。ファイルを丸ごと置き換えず、本リポジトリの key の置き場所（`MAAS_ANTHROPIC_TOKEN` をファイルに置かない）・setup の形（`pi-provider-setup.py`）・key の判定（`ccda` と同じ）・テストの形を保つ。

## 現状の観測（2026-11-11、base `65b7800c82101f102d3549830a864ddce4127474`）

- Pi は 1.5.2（移植元と同じ）。組み込みの provider に `alibaba` は無い
- 共有の `~/.pi/agent/models.json`（usaturn/agent-workspace と使い合う bind mount）には、移植元の `setup_pi_alibaba.zsh` が入れた `providers.alibaba` が既にあり、移植元の `pi-models.json` の `providers.alibaba` と JSON として同一だった
- `pi --list-models qwen4-max-preview` は、`MAAS_ANTHROPIC_TOKEN` がある環境では `alibaba qwen4-max-preview 991.8K 65.5K` を出し、key を外すと `No models matching` になる（Pi は key を解決できない provider をモデル一覧から外す）
- `~/.local/bin` に `piaq` は無い。`subagent.d/piaq/`（旧位置。移植元の setup が書く）はあるが、本リポジトリの位置 `subagent.d/create-reso-world/piaq/` は無い
- `ccda`（`.devcontainer/zshrc.txt` の関数）の key の判定は `[[ ${MAAS_ANTHROPIC_TOKEN:-} != *[A-Za-z0-9]* ]]`。移植元の `piaq` は `[[:graph:]]` で、本リポジトリより緩い
- `zshrc.txt` の ccd 系のランチャー関数（`ccdd`・`ccddg`・`ccdgo`・`ccdol`・`ccda`）は、`cc_launcher_unsets` の `env -u` で、自分が起動する子から `MAAS_ANTHROPIC_TOKEN` を外す（`ccda` は自分の子に `ANTHROPIC_AUTH_TOKEN` として渡し直す）。シェルのセッション全体から unset する仕組みは無い。そのため、これらのランチャーで起動したエージェントのセッション（以下「ランチャー起動セッション」）の中には key が無い
- agent-runner の子の環境は、runner が agent の `env` の allowlist に挙げた変数だけで組み立てる（`zshrc.txt` は読み込まれない）。runner を起動したシェルに key が無ければ、allowlist に挙げても子には届かない
- 本リポジトリのランチャー別の tier 設定は `scripts/setup_pi_superagents.zsh` が `LAUNCHERS` から `subagent.d/create-reso-world/<launcher>/config.json` に置き、tier の拡張は `pi-superagents-model-guard.ts`（移植元の `pi-superagents-tier-guard.ts` ではない）
- provider の setup（`setup_pi.zsh`・`setup_pi_commandcode_goat.zsh`・`setup_pi_opencode_go.zsh`）は `pi-provider-setup.py` で `providers.<name>` だけを置き換え、変更があるときだけ `models.json.bak.*` へ退避する。tier 設定には触れない。テストは `tools/devenv_migration/tests/test_pi_provider_setup.py`
- #401（open、PR 未作成）は `claude-code_alibaba_opus_max`（`provider = "alibaba"`、`model_key = "qwen4-max-preview"`）を `pi_deepinfra_deepseek4-flash_high` の後に足す予定。#365（open）は `agent-runner.toml` の追従

## 決定記録

### D1. 接続方式とモデルの定義

- 選択した案: 移植元の `providers.alibaba` を値ごとそのまま `.devcontainer/pi-models.json` に足す（OpenAI 互換 `https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1`、`api: "openai-completions"`、`authHeader: true`、`apiKey: "$MAAS_ANTHROPIC_TOKEN"`、`compat`（`thinkingFormat: "qwen"` ほか）、モデル `qwen4-max-preview`・`qwen3.8-flash`（`contextWindow` 991808・`maxTokens` 65536・`thinkingLevelMap` 恒等））
- 検討した別案: Anthropic 互換 API、Pi 組み込みの `qwen-token-plan` の上書き、値の調整
- 選択理由: Pi の版が移植元と同じ 1.5.2 で、移植元の実測（PR #931 の「Spec の決定と理由」）がそのまま当てはまる。共有の `~/.pi` に移植元が同じ provider 名で同じ定義を入れているので、値を変えると 2 つのリポジトリの setup が互いの定義を書き換え合い、そのたびに退避ファイルが増える。同一の値なら、どちらの setup も「already up to date」で何もしない
- 委任指示: 「移植元の接続方式・`contextWindow`・`maxTokens`・thinking の値をそのまま使うかの確認」は Issue がエージェントに任せている

### D2. `piaq` の形

- 選択した案: `.devcontainer/piccd` と同じ形の zsh ランチャーにする。ヘルパ `pi-superagents-exec.zsh` を探して source し、`pi_agent_directory` で models.json の場所を決め、provider `alibaba` とモデル `qwen4-max-preview` の定義の有無を確かめ、key を確かめてから `pi_superagents_exec piaq --provider alibaba --model qwen4-max-preview --models qwen4-max-preview --thinking max "$@"` を呼ぶ
  - models.json が無い・provider が無い・モデルが無いときは、`zsh scripts/setup_pi_alibaba.zsh` を案内して終了コード 1。`alibaba` は組み込みに無いので、models.json が無ければ解決できない（移植元と同じ。`piccd` は models.json が無いときに素通りするが、`piaq` は止める）
  - models.json が読めない・壊れている・python3 が無いときは判定せず Pi に委ねる（`piccd` と同じ）
  - key の判定は `ccda` と同じ `*[A-Za-z0-9]*`。未設定・空・ASCII の英数字を 1 文字も含まない値（NBSP・BOM・全角空白だけなど）では、値を表示せず、`MAAS_ANTHROPIC_TOKEN` を export するよう案内して終了コード 1。Pi を起動しない
  - 判定の順は、定義の確認 → key の確認（移植元・`piccd` と同じ）
- 検討した別案: 移植元の `piaq` をそのまま写す（`[[:graph:]]` の判定、独自の PI_DIR の展開）
- 選択理由: Issue が `ccda` と同じ判定を求めている。PI_DIR の展開はヘルパの `pi_agent_directory` に一元化されており、二重に書かない
- 委任指示: Issue の「対応内容」2 に従う

### D3. tier 設定

- 選択した案: `.devcontainer/pi-superagents/piaq.json` を足す。cheap は `alibaba/qwen3.8-flash`、balanced・max は `alibaba/qwen4-max-preview`、全 tier `thinking: "max"`。`extensions` は本リポジトリの `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts`。`scripts/setup_pi_superagents.zsh` の `LAUNCHERS` に `piaq` を足す
- 検討した別案: 移植元の `piaq.json` をそのまま写す（`pi-superagents-tier-guard.ts` を挙げる）
- 選択理由: 本リポジトリのヘルパは、tier 設定が model guard を挙げていないと起動前に止まる。tier の model は model guard の照合（子 Pi の catalog に在ること）に通る必要があり、実環境で確かめる（受け入れ基準）

### D4. 既存環境への反映（setup）

- 選択した案: 新しい `scripts/setup_pi_alibaba.zsh` を、`setup_pi_commandcode_goat.zsh` と同じ形で作る
  1. 前提（python3・pi・`pi-models.json`・ヘルパ・`piaq` の元ファイル、`piaq` が `--model qwen4-max-preview` を使うこと）を確かめる
  2. `python3 .devcontainer/pi-provider-setup.py "$PI_DIR" .devcontainer/pi-models.json alibaba` で `providers.alibaba` だけを置き換える（ほかの provider を保ち、変更があるときだけ更新前に退避する。key は要らない）
  3. `pi-superagents-exec.zsh` と `piaq` を `~/.local/bin` に置く。tier 設定には触れない（`setup_pi_superagents.zsh` が置く。既存の provider の setup と同じ分担）
  4. `MAAS_ANTHROPIC_TOKEN` が `ccda` と同じ判定で有効なときだけ、`pi --list-models` の provider・model の列で `alibaba/qwen4-max-preview`・`alibaba/qwen3.8-flash` を確かめ、無ければ終了コード 1。key が無いときは、確認を省いたことと、key を export して `piaq` を使うことを表示して終了コード 0
  5. 最後に、tier 設定のために `zsh scripts/setup_pi_superagents.zsh --if-absent` を実行するよう表示する（フラグ無しだと既存の全ランチャーの tier 設定を退避して上書きするので、`piaq` の設定だけを新しく置く `--if-absent` を案内する。`install_beforehand.bash`・README の既存環境の案内と同じ）
- 検討した別案: 既存の `setup_pi.zsh`（DeepInfra 専用で `DEEPINFRA_TOKEN` を必須にする）に足す。移植元の `setup_pi_alibaba.zsh` をそのまま写す（独自の退避・置き換え、tier 設定の配置）
- 選択理由: Issue が `pi-provider-setup.py` の形を求めている。key を必須にすると、ファイルに key を置かない方針の下で setup の実行が不必要に難しくなる。Pi は key の無い provider をモデル一覧から外すので、key が無いときの一覧の確認は必ず失敗し、意味を持たない
- 委任指示: Issue の「setup スクリプトを新しく作るか、既存の setup に足すか」はエージェントに任せている

### D5. 新規コンテナへの配置

- 選択した案: `.devcontainer/install_beforehand.bash` の Pi ランチャーの配置に `piaq` を足す（毎回上書き）。models.json は今までどおり「無い場合のみ」雛形を置くので、新規のコンテナでは `alibaba` が入り、既存の models.json では D4 の setup で反映する。tier 設定は既存の `setup_pi_superagents.zsh --if-absent` が置く

### D6. runner agent

- 選択した案: `.devcontainer/agent-runner.toml` に `[agents.pi_alibaba_qwen4-max_max]`（`runtime = "pi"`・`command = ["piaq"]`・`model = "qwen4-max-preview"`・`provider = "alibaba"`・`effort = "max"`・`env = ["HOME", "PATH", "MAAS_ANTHROPIC_TOKEN"]`）を足す。`[workflows]` は変えない。場所は `pi_google-vertex_gemini4-argon_high` の後（`pi_deepinfra_deepseek4-flash_high` の前）にし、#401 が `pi_deepinfra_deepseek4-flash_high` の後に足す行と重ならないようにする。前のコメントに、`piaq` を呼ぶこと、key を export したシェルから使うこと（子に渡るのは `env` の allowlist に挙げた変数だけで、runner を起動したシェルに key が無ければ届かない。ccd 系のランチャーは自分の子から key を外すので、ランチャー起動セッションの中には key が無く、本リポジトリでは env ファイルからも補わない。その場合 `piaq` は key の案内を出して終了コード 1 で止まる）、`model` が #401 の `claude-code_alibaba_opus_max` の `model_key` と同じで同じ役割に並べられないことを書く
- 検討した別案: 移植元と同じく `claude-code_alibaba_opus_max` の直後に置く（本リポジトリにはまだ無い）
- 選択理由: #401 と #365 のどちらが先にマージされても、差分の取り直しが小さい

### D7. README

- 選択した案: `.devcontainer/README.md` の次の節を更新する
  - 「pi のモデル定義とランチャー」: `piaq` の行（provider・モデル・thinking・key）
  - 「pi-superagents のランチャー別 model tier」: `piaq` の tier
  - 「API トークン」: `MAAS_ANTHROPIC_TOKEN` を `piaq` も使うこと、ファイルに置かず使うシェルで export すること
  - 「非対話エージェントのランナー（agent-runner）」: `pi_alibaba_qwen4-max_max` と使い方（key を export した通常のシェルから。Rebuild 前は `piaq` が無いので setup が要る）
  - 「Alibaba Cloud Model Studio の Token Plan で Claude Code を起動する（#397）」: Pi からも同じ Token Plan を使えること（`piaq`）と、既存環境への反映（`zsh scripts/setup_pi_alibaba.zsh` と `zsh scripts/setup_pi_superagents.zsh`）。ランチャー起動セッションの `with_keys.py` では key を補えないこと
  - ランチャーの本数・一覧を挙げるほかの箇所も合わせて更新する（冒頭の「通常ランチャー 11 本」、既存環境の更新の「通常の 11 本の pi ランチャー」、「エージェント向けツールの導入」の手動 install の手順、「13 本分を維持（通常配置は 11 本）」、「pi の TUI モードと Herdr のスクロール履歴」の列挙など。`piaq` で通常配置は 12 本、tier 設定は 14 本になる）。本数は実装の時点の README とコードを数えて合わせる
  - 実機の観測（Task の最後に書く）
- 委任指示: 「README の節の構成」はエージェントに任せている

### D8. テスト

AGENTS.md の「テストの採用基準」の S だけを、それぞれ代表 1 件で書く。

- T1（`.devcontainer/test-pi-superagents.bash`）: `piaq` は全角空白だけの key では Pi を起動せず（ヘルパの dry-run の出力が出ない・終了コード 1・出力に key の値が無い）、同じ環境で英数字を含む key なら Pi まで届く（dry-run の argv が `bwrap` で始まる）。防ぐ損害: 空白だけの key のまま起動すると、誤った認証のまま進み、エラーで分からない。陽性の対照が無いと、ヘルパが別の理由で Pi の前に止まってもテストが通る（移植元の Task 1 のレビューで実際に空振りした）。既存の `run_launcher`・`test_launchers_wrap_pi_with_their_own_config` は tier 設定の一覧からランチャーを集めるので、`piaq` も自動で対象になる。そのために必要な環境（`MAAS_ANTHROPIC_TOKEN` の偽の値、`alibaba` の定義を持つ models.json）をテスト側で与える
- T2（`tools/devenv_migration/tests/test_pi_provider_setup.py`）: `test_update_preserves_other_providers_and_private_permissions` を setup のスクリプトで引数化し、`setup_pi_opencode_go.zsh` に `setup_pi_alibaba.zsh` を加える。防ぐ損害: 新しい setup がほかの provider を消す・退避しないと、データが失われてもエラーにならない。偽の `pi` の `--list-models` は、引数化した provider を出すようにする
- 書かないもの: ランチャー名・モデル名・README の文言・設定の値を写すテスト、models.json に定義が無いときの案内（メッセージ付きの非 0 で止まる L）、runner の env allowlist（既存の守りで、変えない）、他のランチャーの子に key が渡らないこと（`test-herdr-migration.bash` の既存の検査）
- 偽の key の値は実行時に組み立てるか、明らかな偽の値（`dummy-...`）にする。実 key を写さない

## 受け入れ基準

- 動作環境: Dev Container（Pi 1.5.2）。新規のコンテナ（`install_beforehand.bash` の配置と、models.json の雛形）と、`~/.pi/agent/models.json` を既に持つ既存のコンテナ（`setup_pi_alibaba.zsh` で反映）。agent-runner は個人設定が無い環境と、個人設定（`~/.config/agent-runner/config.toml`）を重ねる環境
- 実入力: `MAAS_ANTHROPIC_TOKEN` を export した通常のシェル（ランチャー起動セッションの外）からの `piaq -p "1+1 の答えを数字だけで答えて"` と対話起動。agent-runner の最小の依頼（改行と日本語を含む短いプロンプト、`--assign inspect=pi_alibaba_qwen4-max_max`）
- 防御範囲（対象）:
  - `MAAS_ANTHROPIC_TOKEN` が未設定・空・ASCII の英数字を含まない（NBSP・BOM・全角空白だけを含む）とき、`piaq` は値を表示せずに終了コード 1 で終わり、Pi を起動しない
  - models.json・provider・モデルの定義が無いとき、`piaq` は setup の案内を出して終了コード 1
  - setup は既存の models.json のほかの provider を保ち、変更するときは更新前に退避する。2 回目は何も変えない
  - key の値が models.json・ランチャーの出力・Pi のセッション記録・agent-runner の result とログに出ない
  - agent-runner の子には `env` に挙げた変数だけが渡る（既存の allowlist のまま）
- 防御範囲（対象にしない反例）:
  - 既存の Pi ランチャー（`piccd`・`pidid` など）と `ccda` の接続先・認証・モデルは変わらない。`pi-models.json` のほかの provider の定義を変えない
  - ランチャー起動セッションから key を補って新しい agent を使う経路（本リポジトリでは `MAAS_ANTHROPIC_TOKEN` をファイルに置かないため）
  - 他のランチャーの子に `MAAS_ANTHROPIC_TOKEN` が渡らないこと（`test-herdr-migration.bash` の既存の検査が引き続き通る）
- 完了条件:
  - `bash .devcontainer/run-tests.bash`・`uv run pytest tools/devenv_migration/tests/test_pi_provider_setup.py`・agent_runner のテスト・`bash scripts/check-layout.sh` が通る
  - 実機の観測（`piaq -p` の終了コード・セッション記録の provider・model・thinking、対話起動、agent-runner の `check`・`list`・最小の依頼の state と `identity`、`setup_pi_alibaba.zsh` の実行結果、tier の model guard の照合）を README と PR に書く。本物の API を呼ぶ確認は `piaq -p`・対話起動・runner の依頼の各 1 回に限る。保存物に key の値を含むファイルが無いことを確かめて書く

## 対象外

- `keys.env`・`~/.zshrc` による key の補い、`MAAS_ANTHROPIC_TOKEN` をファイルに置く方針への変更、key の永続保存
- `ccda` の変更、#401 の範囲（`with_keys.py`・`claude-alibaba-exec`・`claude-code_alibaba_opus_max`）
- 既定の役割の割り当て（`[workflows]`）の変更
- `qwen4-max-preview` 以外を主モデルにするランチャー（tier の `qwen3.8-flash` は除く）
- 移植元の旧位置の tier 設定（`subagent.d/piaq/`）の変更・削除

## builder に任せる事項

- `piaq` のメッセージの文面、コメントの量
- T1・T2 のテストの補助関数の形（既存の形に合わせる）
- README の各節での記述の位置と量

## レビュー記録

### 設計レビュー（1 回目）

- 方式: issue-to-pr の `review_design.py`、外部担当
- 担当: `--design-review pi_openai-codex_gpt6-sol_xhigh`（明示。fallback なし）。runner が観測した agent は `pi_openai-codex_gpt6-sol_xhigh`、identity は model `gpt-6.1-sol`・provider `openai-codex`・effort `xhigh`。fallback は使っていない
- `review_id`: `01be30a6ebbf4fe8921eeb7b1b41af0e`、reviewed の Spec の SHA-256: `f4375a7b26be09e23f11dd6c11d2c4f35cbf4104611646bbff872de3b235a9ae`、所要 122 秒
- 結果: `verdict: sound`、concerns 0 件、利用者への問い 0 件。採否の対象は無い
- `outside_changes`: なし。`unprotected_changes`: 他の作業の使い捨ての worktree（`/tmp/pr-review-376-*`・`/tmp/review-fix-planning.*`）6 件。このレビューの対象外で、記録だけ残す
- 記録の場所（commit しない）: `tmp/agents/issue-402.ht7fd2ih/2026-11-11-issue-402-piaq-token-plan-design.design-review/review-1/`

### Spec レビュー（1 回目）

- 方式: issue-to-pr の `review_spec.py`、外部担当
- 担当: `--spec-review devin_swe2_max`（明示。fallback なし）。runner が観測した agent は `devin_swe2_max`、identity は model `SWE-2 Max`（provider・effort は観測なし、CLI 3000.12.43）。fallback は使っていない
- `review_id`: `951e8b3229a84ec88cca1f2c284e69ae`、reviewed の Spec の SHA-256: `ab13053a40b495e8e3f6b832151015185fc8912269abd4d5b5dd38e17d9c185d`、所要 858 秒
- 結果: findings 3 件（すべて minor）。すべて採用
  - S1（現状の観測・D6）: unset はセッション全体ではなく ccd 系のランチャー関数の子だけで、runner の子は env allowlist で決まる → 「現状の観測」と D6 のコメントの説明を 2 つの仕組みに分けて書き直した（`zshrc.txt` の `cc_launcher_unsets` で確認）
  - S2（D4）: setup の最後の案内に `--if-absent` が無く、既存の tier の編集を上書きしうる → 案内を `--if-absent` 付きにした
  - S3（D7）: README のランチャーの本数・一覧を挙げるほかの箇所が更新の対象から漏れている → D7 に追記した
- `outside_changes`: なし。`unprotected_changes`: 設計レビューと同じ、他の作業の使い捨ての worktree 6 件（記録だけ）
- 記録の場所（commit しない）: `tmp/agents/issue-402.ht7fd2ih/2026-11-11-issue-402-piaq-token-plan-design.spec-review/review-1/`
- 2026-11-11 21:33 ごろの利用者の指示「devin_swe2_maxに対しては、JSONだけを返却してくださいと必ず指示をしてください。」により、以後の `devin_swe2_max` への依頼の prompt に、JSON だけを返す指示を必ず入れる（このレビューは指示の前に起動済みで、helper の依頼文の JSON の指示だけだった）
