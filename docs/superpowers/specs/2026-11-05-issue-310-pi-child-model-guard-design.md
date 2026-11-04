# Issue #310 子 Pi が tier の model と違う model で要求を送る前に止める 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/310（#307 の持ち越し。PR #308 で範囲外とした 2 点目）
- 実行許可: 利用者の指示 `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/310 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- 許可された範囲: create-reso-world の `.devcontainer/`・`scripts/setup_pi_superagents.zsh`・`.devcontainer/README.md`・テスト・この Spec と Plan の変更。pi-superagents・Pi 本体は変えない（Issue の範囲外）
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` の `main`（`refs/heads/main`）`edd4ffd622efcc72b7a79d48201d3e07959f8de8`。親 Issue・handoff の base の要求は無い

## 目的

pi-superagents が子 Pi に渡した tier の model（`--models <provider>/<id>:<thinking>`）を子 Pi が使えないとき、子 Pi は警告だけを出して別の model を選び、そのまま要求を送る。利用者が選んでいない model（費用・能力・送り先の provider が違う）で子が動き、親には成功として返る。子 Pi の中で、Pi が実際に使う model と要求された model を最初の要求の前に照合し、違えば止める。止めた理由は、資格情報やタスクの本文を出さずに、子の stderr と pi-superagents の実行記録で追えるようにする。

## 確かめた事実（2026-11-05、Pi 1.5.0・pi-superagents 1.14.4）

Pi 本体（`/usr/local/share/nvm/versions/node/v24.22.1/lib/node_modules/@earendil-works/pi-coding-agent`）と、導入済みの pi-superagents（`~/.pi/agent/npm/node_modules/@teelicht/pi-superagents`）のソースを読み、実際の Pi で確かめた。実験は、一時ディレクトリの `PI_CODING_AGENT_DIR` に偽の provider（`baseUrl` がローカルの偽の HTTP サーバー）を定義し、`env -i` で資格情報の環境変数を渡さずに行った。

1. pi-superagents は子 Pi を `pi --mode json -p ... --models <model>:<thinking> --no-extensions --extension <path>...` で起動し、stdin を `ignore` にする（`src/execution/child-runner.ts`・`pi-args.ts`）。`resolveSubagentExtensions` は常に配列を返すので `--no-extensions` が必ず付き、子が読み込む拡張は tier 設定の `superagents.extensions`（と、セッションを持つ子に足される pi-superagents 自身）だけになる。挙げたローカルのパスが無いと、子を起動せずにエラーを返す（`findMissingSubagentExtensionPath`）
2. Pi は `--models` を、資格情報のある（使える）model の中からだけ解決する（`resolveModelScope` は `getAvailable` を使う）。解決できないパターンには `Warning: No models match pattern "..."` を stderr に出すだけで続ける。解決できるものが無いと、Pi は既定の選び方（保存済みの既定、無ければ使える model の先頭）で model を選ぶ。bare のパターンは部分一致でも解決する（`model` が `fakeok/model-b` に解決された）
3. 不具合を再現した。`--models openai/gpt-5.6-sol:high`（`openai` の資格情報なし）で、Pi は偽の provider の `fakeok/model-a` に要求を送り、終了コード 0 で終わった。最初の実験は `env -i` を使わず、親の環境の `GOOGLE_CLOUD_API_KEY` が子に渡ったため、`google-vertex/gemini-3.1-pro-preview` に実際に要求が送られた（"say hi" の 1 件。Pi の見積もりで約 $0.0035）。親の環境にある別の provider の資格情報が、黙ってフォールバック先になる
4. 拡張の `session_start` では、`ctx.model` が最初の要求に使う model、`ctx.scopedModels` が `--models` の解決結果、`ctx.modelRegistry.getAll()` が資格情報の有無によらない全 model を返す（`dist/core/extensions/types.d.ts`・`runner.js`）。print モードの Pi は `session_start` を待ってから最初の要求を送るので、ここで `process.exit(1)` すると要求は 1 件も送られない（偽のサーバーへの要求 0 件で確かめた）
5. print モードの Pi には、拡張から終了コード付きで実行を止める API が無い（`ctx.shutdown` は終了コードを選べず、ハンドラの例外は報告されるだけで続く）。`process.exit(1)` を使う
6. pi-superagents は、子の終了コードが 0 でないとき、子の stderr を `result.error` にする。これは `~/.pi/agent/run-history.jsonl`（`finishRun` の error）、`subagent-artifacts/<runId>_<agent>_<n>_meta.json` の `error`、親のセッションの subagent の結果に残る。終了コードが 0 のときの stderr は捨てられる
7. `auth.json`・`models.json` の key の `!command` が失敗する場合、Pi 1.5.0 はその model を使えるものとして選び、要求の時点で `API key auth failed for provider ...` のエラーになる。別の model には切り替わらない（偽の provider の `apiKey: "!false"` で確かめた）
8. `--models fakeok/model-a:max` で、`ctx.thinkingLevel` は `high` だった。Pi は model が対応しない thinking を黙って下げる
9. Pi の拡張の自動探索は `~/.pi/agent/extensions/*.ts` と、`index.ts`（または manifest）を持つサブディレクトリだけを読む（`dist/core/extensions/loader.js` の `discoverExtensionsInDir`）。`~/.pi/agent/extensions/subagent.d/*.ts` は親の Pi に読み込まれない
10. usaturn/agent-workspace の setup が置いたと見られる `~/.pi/agent/extensions/subagent.d/pi-superagents-tier-guard.ts` がある（同リポジトリの #765・#773）。共有の `~/.pi` の `subagent.d/pigt/config.json` は 2026-11-04 22:40 に、この拡張を `superagents.extensions` に挙げた内容へ置き換わっていた。この拡張は `ctx.scopedModels` に名指しの model があるかを見るので、bare のパターンが部分一致で別の model に解決された場合（事実 2）は通す。この拡張を Pi 1.5.0 で試し、事実 3 の要求を送る前に止めることを確かめた
11. このリポジトリの 13 のランチャーの tier 設定（`.devcontainer/pi-superagents/<launcher>.json`）は `superagents.extensions` を持たない。`setup_pi_superagents.zsh --if-absent`（rebuild の経路）は既存のランチャー別の設定を置き換えない

## 決定記録

### D1. 照合の方法

- 選択した案: このリポジトリが持つ Pi の拡張（`.devcontainer/pi-superagents-model-guard.ts`）を、`setup_pi_superagents.zsh` が `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` に置き、各ランチャーの tier 設定の `superagents.extensions` に挙げる。子 Pi の `session_start` で照合し、違えば理由を stderr に書いて終了コード 1 で終わる
- 検討した別案:
  - agent-workspace の拡張を同じパス・同じ名前で移植する: 共有の `~/.pi` で 2 つのリポジトリの setup が同じファイルを互いに上書きし、どちらの版が動くかが最後に setup を実行した側で変わる
  - agent-workspace の拡張をそのまま挙げる: 他のリポジトリが置くファイルに頼る。このリポジトリの setup では配置も更新もできず、bare のパターンの部分一致を通す（事実 10）
  - ランチャーの起動前に資格情報を解決して確かめる: `!command` の実行や OAuth の解決をランチャーで重ねることになり、子 Pi の実行時の環境（起動後の `/logout`、環境変数の違い）を見られない。Pi の解決処理（`getAvailable`・部分一致）を写すことになる
- 選択理由: 子 Pi の中で、Pi 自身の解決の結果を見るので、資格情報・catalog・部分一致のどれで別の model になっても同じ方法で捉えられる。pi-superagents・Pi 本体を変えない（Issue の範囲外の条件）。拡張は `subagent.d/` に置くので親の Pi には読み込まれない（事実 9）
- 委任指示: issue-to-pr の推奨案での委任

### D2. 照合する値と一致の規則

- 選択した案: `session_start` の `ctx.model`（最初の要求に使う model）を、子 Pi の argv の `--models`（最後の指定。カンマで分け、空白を除く）のパターンと照合する。どれかのパターンに一致すれば通し、どれにも一致しなければ止める。パターンごとの一致は次のとおり（大文字小文字は区別しない）
  - 末尾の `:<thinking level>`（`off`・`minimal`・`low`・`medium`・`high`・`xhigh`・`max`）を外す
  - glob（`*`・`?`・`[`）を含むパターンは一致しないものとする（どの model を求めたかを決められないため）
  - 最初の `/` の前が Pi の知っている provider（`ctx.modelRegistry.getAll()` の provider）なら、provider と ID の両方が一致すること（`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017` は provider `deepinfra`、ID `deepseek-ai/DeepSeek-V4.1-Flash-1017`）
  - それ以外（bare の ID、知らない provider）は、パターン全体が `ctx.model` の ID と一致すること
  - `--models` が無ければ何もしない。`ctx.model` が無い・Pi の API から読めない・途中で例外が起きたときは止める
- 検討した別案:
  - agent-workspace と同じく `ctx.scopedModels` に名指しの model があるかを見る: bare のパターンの部分一致を通す（事実 2・10）。解決結果に要求の model があっても、Pi が選ぶのは別の model になりうる
  - thinking も照合する: Issue の範囲は model。Pi は対応しない thinking を下げるが（事実 8）、`pigt`・`pidid` は起動前に thinking の対応を確かめている（#305）。範囲外とし、持ち越し候補に書く
- 選択理由: 照合する値を「最初の要求に使う model」にすると、フォールバックも部分一致も同じ規則で捉えられる。provider を名指ししたパターンは provider まで一致させるので、同じ ID を持つ別の provider（OpenRouter の `openai/...` など）への切り替えも止まる
- 委任指示: issue-to-pr の推奨案での委任

### D3. 止めたときの出力と記録

- 選択した案: 止めるときだけ、`[pi-superagents-model-guard]` で始まる数行を stderr に書き、終了コード 1 で終わる。書くのは、要求された model（`--models` の値）、Pi が選んだ model（`provider/id`。無ければ「なし」）、理由、主な原因と確かめ方。例外の内容、資格情報、タスクの本文は書かない（拡張はタスクを読まない）。通したときは何も書かない
- 検討した別案: 通したときも 1 行書く（終了コード 0 の stderr は pi-superagents が捨てるので記録に残らない。事実 6）
- 選択理由: pi-superagents は終了コード 1 の子の stderr を `run-history.jsonl`・`meta.json`・親の結果に残す（事実 6）ので、追加の記録の仕組みが要らない。通したときは要求された model で動いたことになり、実際の model は今までどおり実行記録（`details.results[].model`）に残る
- 委任指示: issue-to-pr の推奨案での委任

### D4. 拡張を読み込ませていない設定の扱い（既存の環境）

- 選択した案: 共通ヘルパ（`pi_superagents_exec`）が、tier の検査の後に、ランチャーの tier 設定の `superagents.extensions` に照合の拡張（`~/` を `HOME` で展開して `${HOME}/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` になる要素）があり、そのファイルが通常のファイルとして在ることを確かめる。無ければ起動せず、`zsh scripts/setup_pi_superagents.zsh`（ランチャー別の設定を退避してから置き換える）か、`superagents.extensions` への追記を案内する。`setup_pi_superagents.zsh` は通常と `--if-absent` のどちらでも、照合の拡張を毎回置き直す（共通ヘルパと同じ）
- 検討した別案:
  - `--if-absent` でも既存のランチャー別の設定に `superagents.extensions` を書き足す: 利用者の設定を JSON として読み直して書き戻すことになり、退避・書式・壊れた設定の扱いが増える。#305 の「利用者が明示編集した tier は受け入れる」と同じく、利用者の設定には手を入れず、ランチャーが止まって案内する方を選ぶ
  - 何もしない（案内だけを README に書く）: rebuild（`--if-absent`）では既存の設定に拡張が入らず、照合が無いまま子が動く。気付けない
- 選択理由: #307 の tier の欠け（`pi_launcher_require_tiers`）と同じく、前提が欠けた設定ではランチャーが起動を止める。既存の環境は、案内の 1 コマンドで直る
- 委任指示: issue-to-pr の推奨案での委任

### D5. #305 の「新しい tier-guard 拡張は追加しない」との関係

- 選択した案: `.devcontainer/README.md` の該当の文を、#305 の起動前の検査（`pigt`・`pidid` の catalog・thinking・設定のメタデータの検査。認証を解決しない）はそのまま残し、子 Pi が実行時に資格情報を解決できないときの切り替えは、全ランチャーで子 Pi の中の照合の拡張（#310）が止める、という関係に書き換える
- 検討した別案: 文を消すだけにする（#305 の検査の範囲と、拡張を足した理由が分からなくなる）
- 選択理由: #305 の決定は、ローカルに無い外部の拡張に頼らず、起動前の検査をランチャーに限ることだった。今回の拡張はこのリポジトリが持ち、起動前には見られない実行時の解決を見るので、#305 の検査と重ならない
- 委任指示: issue-to-pr の推奨案での委任

### D6. テスト

テストの採用基準（`AGENTS.md`）の S に当たるものだけを書く。

- 書く:
  - 照合の拡張（実際の Pi・偽の provider・ローカルの偽のサーバー、`env -i` で資格情報を持ち込まない）: 名指しの provider に資格情報が無く、Pi が同じ ID を持つ別の provider の model を選ぶとき、終了コード 1 で、偽のサーバーへの要求が 0 件で、stderr に要求された model と選ばれた model が出ること。通る例として、要求どおりに解決できる model では偽のサーバーに要求が届くこと。壊れると、子が黙って別の model・別の provider に要求を送る（S）。Pi の更新で `session_start` の前に要求を送るようになったときも、このテストが気付く
  - 照合の拡張の例外の経路: `ctx` の読み取りが資格情報らしい文字列を含む例外を投げても、stderr にその文字列が出ず、終了コード 1 で止まること。壊れると、秘密が `run-history.jsonl` などの実行記録に残る（S）
  - ランチャーの起動前の検査: tier はそろっているが `superagents.extensions` に照合の拡張が無い設定では、bwrap に進まず終了コード 1 になること。通る例は既存のテスト（テスト用の設定に照合の拡張を足す）。壊れると、照合が無いまま子が動く（S）
- 書かない:
  - setup が照合の拡張を置くこと・リポジトリの tier 設定が挙げること（F。欠けるとランチャーの起動前の検査が止める＝ L）
  - glob・bare のパターン・thinking の接尾辞の個別の規則（同じ守りの組み合わせ＝ D）
  - Pi の API を読めないときに止まること（全ての子が止まるので気付ける＝ L）
- 既存のテストの調整: tier の欠けを確かめるテスト（`test_incomplete_tiers_fail_closed`）の設定にも照合の拡張を足し、照合の検査ではなく tier の検査で止まることを確かめ続ける
- 委任指示: issue-to-pr の推奨案での委任

### D7. 実行方式

- 選択した案: `superpowers:executing-plans`（このセッションが inline で実装する）
- 検討した別案: `superpowers:subagent-driven-development`（Task ごとにサブエージェント）
- 選択理由: Task は順番に依存し（拡張 → ランチャーの検査と設定 → 文書）、`test-pi-superagents.bash`・README を複数の Task で触る。Pi 1.5.0・pi-superagents 1.14.4 の内部の確かめた事実を子に渡しきるのが重い。最後のブランチ全体のレビューはサブエージェントに依頼する
- 委任指示: issue-to-pr の推奨案での委任

### D8. 担当とループのオプション

- Plan の Task の担当: `implement_task.py check` の結果 `assignment: {agents: ["self"], fallback: []}`・`self: true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用（利用者の `--implement` の指定は無い）。個人設定 `/home/vscode/.config/agent-runner/config.toml` は読み込まれたが、`workflows.issue` の `implement` を変えていない
- ループのオプション: 利用者の指定は無い（`loop_args: []`）。`check-options` の結果は既定の適用で、`max_cycles: 3`、レビュアー `cursor_grok4_xhigh`・`devin_swe2-max_default`・`pi_commandcode_deepseek4-flash_max`、修正の担当 `claude-code_opus_default`、自己レビュー・修正の確認は `self`
- 委任指示: 利用者の指示 `--merge`

## 受け入れ基準

1. ランチャーの tier 設定で起動した子 Pi が、`--models` の model と違う model を選ぶとき（資格情報が無い、ID の誤り、同じ ID の別の provider、部分一致）、最初の要求の前に終了コード 1 で終わる。pi-superagents の実行記録（`run-history.jsonl` の error、`meta.json` の error、親の結果）に、照合の拡張の出力が残る
2. 要求どおりの model に解決できる子 Pi は、今までどおり動く
3. 止めたときの出力は、要求された model・Pi が選んだ model・理由を含み、例外の内容・資格情報・タスクの本文を含まない
4. 13 のランチャーのリポジトリの tier 設定が照合の拡張を挙げ、`setup_pi_superagents.zsh` が通常と `--if-absent` のどちらでも照合の拡張を置く
5. tier 設定が照合の拡張を挙げていない、または照合の拡張のファイルが無いとき、ランチャーは起動せずに直し方を案内する
6. `.devcontainer/README.md` に、照合の仕組み・止まったときの見方・既存の環境での手順・#305 の検査との関係・対象外を書く
7. 検証の入口（`README.md` の「テスト」。ワールドの行を除く）がすべて通る

### 動作環境・実入力・防御範囲

- 動作環境: Dev Container（Ubuntu 26.04 LTS）、Pi 1.5.0、pi-superagents 1.14.4、Node.js 24、zsh、bwrap。子 Pi は pi-superagents が `--mode json -p` で起動する
- 実入力: 子 Pi の argv の `--models` は、tier 設定の `model` と `thinking` から pi-superagents が作る 1 件（`openai-codex/gpt-6.1-sol:xhigh`、`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017:high`、`commandcode/meta/muse-spark-1.3-contributor:max` のように、ID が `/` を含むものがある）。ランチャーの tier 設定は利用者が編集しうる JSON（BOM、`superagents` の他のキー、拡張が書き足すキーを含む）
- 防御範囲: 対象はランチャーから起動した Pi の pi-superagents の子で、`--models` を渡されたもの。対象外は、`--models` の無い子（tier を使わない agent）、`--model` で起動した Pi、thinking の違い（事実 8）、要求の時点で起きる資格情報のエラー（事実 7。別の model には切り替わらない）、ランチャーを通さない Pi（#307 の停止用の設定が pi-superagents を止める）、agent-workspace の setup が共有の `~/.pi` のランチャー別の設定を置き換えること

## 対象外

- pi-superagents・Pi 本体の変更（Issue の範囲外）
- thinking の照合（持ち越し候補。Pi は対応しない thinking を黙って下げる。事実 8）
- 共有の `~/.pi` を agent-workspace と使い合うときの、ランチャー別の設定の取り合い（agent-workspace の setup が置き換えた設定は、このリポジトリのランチャーが D4 の検査で止め、setup の実行を案内する）

## マージの後でなければ確かめられない項目

- 既存の環境で `zsh scripts/setup_pi_superagents.zsh` を実行し、ランチャーを起動し直した後に、使っているランチャーの子 Pi が照合で止まらずに動くこと（実際の資格情報と model で、要求を送る確認。費用がかかるので、この run では偽の provider で確かめる）
