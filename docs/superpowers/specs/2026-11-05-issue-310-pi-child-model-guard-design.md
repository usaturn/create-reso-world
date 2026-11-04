# Issue #310 子 Pi が tier の model と違う model で要求を送る前に止める 設計

## 管理

- 状態: completed（PR #312 の pr-review-fix-loop のサイクル 1 で修正不要と判断。下の「PR #312 のレビューの判断」）
- Issue: https://github.com/usaturn/create-reso-world/issues/310（#307 の持ち越し。PR #308 で範囲外とした 2 点目）
- PR: https://github.com/usaturn/create-reso-world/pull/312
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
12. （全体レビューで判明）既存のセッションにメッセージがあると、Pi は `--models` で model を決めず、セッションの `model_change` の model を復元する。復元した model に資格情報が無ければ、設定の既定の model を使う（`dist/main.js` の `!hasExistingSession`、`dist/core/sdk.js`）。pi-superagents の fork の子（`--fork`。`createBranchedSession` で親のセッションを分岐する）は、親の model を引き継ぎ、tier の `--models` は効かない。照合の前は、fork の子は黙って親の model で動いていた
13. tier を使う同梱の agent（`sp-implementer`・`sp-review`・`sp-debug`・`sp-research`・`sp-recon`）の既定の session-mode は `lineage-only` で、子のセッションはヘッダーだけ（メッセージなし）で始まるので、`--models` で model が決まる（`seedLineageOnlySessionFile`）。`resumeSession` による再開は、前の実行のメッセージを持つ。この環境の親のセッションの記録では、fork の子は 4 件、lineage-only は 1,140 件だった
14. 拡張の `ctx.sessionManager` は `getBranch()` を持つ（`ReadonlySessionManager`）。`buildSessionContext()` は持たない

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

### D2a. 既存のセッションを引き継ぐ子（fork・再開）の扱い（全体レビューで追加）

- 選択した案: 既存のセッションを引き継ぐ子も、新しい子と同じく `ctx.model` を `--models` と照合し、違えば止める。止めるときは、`ctx.sessionManager.getBranch()` に `message` があれば、資格情報の理由ではなく「既存のセッションを引き継いでいるので Pi は `--models` を使わずセッションの model を使う」という理由と、対処（fork を使わずに実行し直す、tier の model を親に合わせる）を出す。`getBranch()` を読めなければ資格情報の理由を出す（止めることは変えない）
- 検討した別案: 既存のセッションでは照合しない（対象外にする）。fork の子は今までどおり親の model で動く。復元した model に資格情報が無く設定の既定に切り替わる場合（事実 12）も見逃す
- 選択理由: Issue の要件は「要求した model と解決した model を照合し、違えば止める」で、fork の子が tier と違う親の model で黙って動くのは、#305・#307・#310 で止めてきた「利用者が tier に選んでいない model で子が動く」と同じ種類の問題になる。tier を使う同梱の agent の既定（lineage-only）は新しいセッションで始まるので（事実 13）、止まるのは明示した fork と、tier を変えた後の再開だけで、どちらも理由と対処を出す。fork の使用は記録で 4 件と少ない
- 対価: fork を使う実行は、tier の model が親の model と違う tier の子で止まる（今までは親の model で動いていた）
- 委任指示: issue-to-pr の推奨案での委任（全体レビューの Important の指摘「扱いを明示的に決めて書く」への対応）

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
  - ランチャーの起動前の検査: tier はそろっているが `superagents.extensions` に照合の拡張が無い設定（キーが無い設定と、別の拡張だけを挙げた設定）では、bwrap に進まず終了コード 1 になること。通る例は BOM 付き・他のキーあり・絶対パスで挙げた設定。壊れると、照合が無いまま子が動く（S）
- 書かない:
  - setup が照合の拡張を置くこと・リポジトリの tier 設定が挙げること（F。欠けるとランチャーの起動前の検査が止める＝ L）
  - 照合の拡張のファイルが無いときにランチャーが止まること（L。ランチャーの検査が壊れても、pi-superagents が子の起動を `Extension path ... does not exist` のエラーで拒む）。全体レビューの指摘で、一度書いたテストから外した
  - 既存のセッションを引き継ぐ子で理由を出し分けること（止めること自体は新しい子と同じ規則で、理由の文言は止まった後に見えるので L）。一時的なテストで確かめた
  - glob・bare のパターン・thinking の接尾辞の個別の規則（同じ守りの組み合わせ＝ D）
  - Pi の API を読めないときに止まること（全ての子が止まるので気付ける＝ L）
- 既存のテストの調整: tier の欠けを確かめるテスト（`test_incomplete_tiers_fail_closed`）の設定にも照合の拡張を足し、照合の検査ではなく tier の検査で止まることを確かめ続ける。ランチャーを起動する Python のテスト（`tools/devenv_migration/tests/test_pi_vertex_launchers.py`・`test_pi_provider_setup.py`）の準備にも、照合の拡張の記載とファイルを足す（新しい起動前の検査が、準備の足りない設定を止めたため）
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

1. ランチャーの tier 設定で起動した子 Pi が、`--models` の model と違う model を選ぶとき（資格情報が無い、ID の誤り、同じ ID の別の provider、部分一致、既存のセッションの model の引き継ぎ）、最初の要求の前に終了コード 1 で終わる。pi-superagents の実行記録（`run-history.jsonl` の error、`meta.json` の error、親の結果）に、照合の拡張の出力が残る
2. 要求どおりの model に解決できる子 Pi は、今までどおり動く
3. 止めたときの出力は、要求された model・Pi が選んだ model・理由を含み、例外の内容・資格情報・タスクの本文を含まない
4. 13 のランチャーのリポジトリの tier 設定が照合の拡張を挙げ、`setup_pi_superagents.zsh` が通常と `--if-absent` のどちらでも照合の拡張を置く
5. tier 設定が照合の拡張を挙げていない、または照合の拡張のファイルが無いとき、ランチャーは起動せずに直し方を案内する
6. `.devcontainer/README.md` に、照合の仕組み・止まったときの見方・既存の環境での手順・#305 の検査との関係・対象外を書く
7. 検証の入口（`README.md` の「テスト」。ワールドの行を除く）がすべて通る

### 動作環境・実入力・防御範囲

- 動作環境: Dev Container（Ubuntu 26.04 LTS）、Pi 1.5.0、pi-superagents 1.14.4、Node.js 24、zsh、bwrap。子 Pi は pi-superagents が `--mode json -p` で起動する
- 実入力: 子 Pi の argv の `--models` は、tier 設定の `model` と `thinking` から pi-superagents が作る 1 件（`openai-codex/gpt-6.1-sol:xhigh`、`deepinfra/deepseek-ai/DeepSeek-V4.1-Flash-1017:high`、`commandcode/meta/muse-spark-1.3-contributor:max` のように、ID が `/` を含むものがある）。ランチャーの tier 設定は利用者が編集しうる JSON（BOM、`superagents` の他のキー、拡張が書き足すキーを含む）
- 防御範囲: 対象はランチャーから起動した Pi の pi-superagents の子で、`--models` を渡されたもの（既存のセッションを引き継ぐ fork・再開の子を含む。D2a）。対象外は、`--models` の無い子（tier を使わない agent）、`--model` で起動した Pi、thinking の違い（事実 8）、要求の時点で起きる資格情報のエラー（事実 7。別の model には切り替わらない）、ランチャーを通さない Pi（#307 の停止用の設定が pi-superagents を止める）、agent-workspace の setup が共有の `~/.pi` のランチャー別の設定を置き換えること

## 対象外

- pi-superagents・Pi 本体の変更（Issue の範囲外）
- thinking の照合（持ち越し候補。Pi は対応しない thinking を黙って下げる。事実 8）
- 共有の `~/.pi` を agent-workspace と使い合うときの、ランチャー別の設定の取り合い（agent-workspace の setup が置き換えた設定は、このリポジトリのランチャーが D4 の検査で止め、setup の実行を案内する）

## 全体レビューの判断

base `edd4ffd6` から `5d123b3c` までを、新しいサブエージェント（Opus、読み取りだけ）がレビューした（判定 With fixes）。

- Important: 既存のセッションを引き継ぐ子（fork）を、資格情報の問題という誤った理由で止める。扱いが Spec・README に無い → 採用。D2a のとおり止めることを明示し、理由と対処を出し分け、README に書いた
- Minor: 照合の拡張のファイルが無い場合のテストは L に当たり書きすぎ → 採用。テストから外した（ヘルパの検査は、早く分かりやすく止めるために残す）
- Minor: ヘルパの BOM を外す正規表現が見えない U+FEFF の文字になっている → 採用。追加した箇所を `﻿` にした（既存の `pi_launcher_require_tiers` の同じ書き方は範囲外として変えない）
- 見送りの判断: `superagents.extensions` の相対パスの解決基準の違い（運用で使わず、ずれても起動の拒否か pi-superagents のエラーになる）、「素の pi で `pi --list-models`」の案内が子の環境と違う provider があること（確かめ方の入口として残す）、子の中での `session_start` の再発火（print モードの子では起きない）。どれも変えない

## PR #312 のレビューの判断

- 実行許可: `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/310 --merge` による pr-review-fix-loop（run `b9b5e104991e4c0e835ffee8bb190965`）の中で、review-fix-planning を完遂として行った
- サイクル: 1。planner: `claude-opus-5-5`（claude-code）。前のサイクルの判断: なし
- レビューディレクトリ: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#312-fix-issue-310-pi-tier-model-guard/`。確認済みの一覧: `verified/1e680eb3329e.json`（review-verify の mode cycle。confirmed 2 / not_reproduced 0 / unverified 0）。工程の記録: `verified/1e680eb3329e.planning.json`
- 修正と自己レビューの担当（ループの割り当て）: implement `claude-code_opus_default`、self-review `self`、fix-check `self`。対応する項目が無いので `run_roles.py` は呼んでいない（自己レビューの回数 0）

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| Grok-4.7.md | Grok 4.7 | cursor | 1e680eb3329e | はい（Initial） | Approve（Medium 1） |
| SWE-2-Max.md | SWE-2 Max | devin | 1e680eb3329e | はい（Initial） | Approve（Low 1） |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | 1e680eb3329e | はい（Initial） | Approve（指摘 0） |

分類: 解消済み 0 / 対応する 0 / 対応しない 2

- 対応しない `Grok-4.7#M-1@1e680eb3329e`: 正確な ID が Pi の知っている provider 名で始まる（commandcode の `meta/muse-spark-1.3-contributor` など）のに provider 名を付けずに渡すと、Pi は要求どおりに解決するが照合が止める。隔離 worktree と実際の Pi（`env -i`・偽 provider）で再現した（確認済みの一覧の V-1）。止まり方は終了コード 1・要求 0 件・理由付きで、別の model へは送らない。このリポジトリの tier 設定は provider から書くので当たらず、上書きでも provider から書けば通る。同じ規則が、名指しの provider が使えないときに同じ ID 文字列を持つ別の provider へ黙って切り替わるのを止めている（D2）ので変えない。致命的ではない。README の「正確な ID か `provider/id` で指定する」の不足は、PR 本文の既知の制限に条件と回避方法を書いた
- 対応しない `SWE-2-Max#L-1@1e680eb3329e`: provider の ID に `/` を含む、glob の文字を含む正確な ID、thinking の level でない接尾辞（`:HIGH`・打ち間違い）で、Pi は要求どおりに解決するが照合が止める。同じく再現した（V-2）。止まり方は V-1 と同じで別の model へは送らず、このリポジトリの 13 の tier 設定はどれにも当たらない。致命的ではない。条件と回避方法を PR 本文の既知の制限に書いた
- 要件対応: 受け入れ基準 1〜7 は、Spec の実入力（provider から書いた tier の `model` と小文字の level）では満たしたまま。対応しない 2 件は実入力の外で、止まる側（要求を送らない側）に寄っているので、基準 1 と 3 の守り（別の model への要求を止める、理由を出す）を弱めない
- 結論: 2（修正不要）。検証は、PR の作成の前の最後の検証の記録を使った（同じ HEAD `1e680eb3329e4ea2679e09eb402814a603bb3ff0`、実行の前後とも作業ツリーが clean、`bash .devcontainer/run-tests.bash`・`bash scripts/check-layout.sh`・`uv run pytest tests/skills .agents/skills .agents/scripts tools` の終了コードがすべて 0、ログは `/workspaces/reso-world/tmp/agents/issue-310._0ihrq92/verify-1e680eb3/`）。取り直した base の先端 `edd4ffd622efcc72b7a79d48201d3e07959f8de8` は検証の記録の base と同じで head の祖先なので、一時的な merge での検証は要らない
- 自己レビュー: 対応するコードの修正が無いので行っていない

## マージの後でなければ確かめられない項目

- 既存の環境で `zsh scripts/setup_pi_superagents.zsh` を実行し、ランチャーを起動し直した後に、使っているランチャーの子 Pi が照合で止まらずに動くこと（実際の資格情報と model で、要求を送る確認。費用がかかるので、この run では偽の provider で確かめる）
