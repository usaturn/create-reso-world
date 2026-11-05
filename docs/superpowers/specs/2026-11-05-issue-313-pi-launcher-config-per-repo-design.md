# Issue #313 ランチャー別の設定をリポジトリごとの場所に分ける 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/313（PR #312・#310 の持ち越し）
- 実行許可: 利用者の指示 `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/313 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- 許可された範囲: create-reso-world の `.devcontainer/`（ヘルパ・README・テスト）・`scripts/setup_pi_superagents.zsh` と、ランチャー別の設定の場所を表示する setup（`scripts/setup_pi_commandcode_goat.zsh`・`scripts/setup_pi_opencode_go.zsh`）・`tools/devenv_migration/tests/`・この Spec と Plan の変更。usaturn/agent-workspace のリポジトリは変えない（Issue の範囲外）。利用者の `~/.pi` は変えない（setup の実行は、マージの後の利用者の確認）
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` の `main`（`refs/heads/main`）`2fa03f195f76b0fcc87f0cab0f7d5e333637659c`。親 Issue・handoff の base の要求は無い

## 目的

共有の `~/.pi`（Dev Container の bind mount。usaturn/agent-workspace の Dev Container とも共有）で、2 つのリポジトリの setup が同じ場所 `~/.pi/agent/extensions/subagent.d/<launcher>/config.json` にランチャー別の tier 設定を書き合っている。agent-workspace の setup が書いた設定では、このリポジトリのランチャーが #312 の起動前の検査（`pi_launcher_require_model_guard`）で止まり、このリポジトリの setup を実行し直すと直るが、agent-workspace の setup をもう一度実行すると、また止まる（往復）。どちらの setup を最後に実行したかに関係なく、このリポジトリのランチャーが、このリポジトリの tier 設定と子 Pi の model の照合（#310）で動くようにする。

## 確かめた事実（2026-11-05）

1. 共有の `~/.pi/agent/extensions/subagent.d/pigt/config.json` は 2026-11-04 22:40:50 に、`superagents.extensions` に agent-workspace の拡張 `~/.pi/agent/extensions/subagent.d/pi-superagents-tier-guard.ts` だけを挙げた内容に置き換わっていた。同じ時刻に `pi-superagents-tier-guard.ts` も置かれていた（中身は agent-workspace の main `da6faec0a0c609266f4cbc26aefa10e875ae4136` の `.devcontainer/pi-superagents-tier-guard.ts` と同じ）。ほかの 12 のランチャーの設定は `superagents.extensions` を持たない（#310 より前の内容）。このリポジトリの照合の拡張 `subagent.d/pi-superagents-model-guard.ts` はまだ置かれていない（#310 のマージの後の setup の実行待ち）
2. agent-workspace の main（上の SHA）は、このリポジトリと同じ 13 の名前のランチャー（`pigo`〜`pigema`）を持ち、setup（`scripts/setup_pi_superagents.zsh`）が `~/.pi/agent/extensions/subagent.d/<launcher>/config.json` に tier 設定を書き（通常は退避してから置き換え、`--if-absent` は無いものだけ）、`subagent.d/pi-superagents-tier-guard.ts` を毎回置き直す。13 の tier 設定の `modelTiers` は、このリポジトリの `.devcontainer/pi-superagents/<launcher>.json` と同じで、`superagents.extensions` だけが違う（agent-workspace の拡張を挙げる）。共有の bind 先 `subagent/config.json` には書かない（ディレクトリを作るだけ）
3. agent-workspace の共通ヘルパ（`.devcontainer/pi-superagents-exec.zsh`）は `subagent.d/<launcher>/` を共有の bind 先へ重ねる。起動前の検査（`pi_superagents_require_tier_models`）は、tier の provider の auth.json の key がコマンド（`!command`）のときだけ、tier 設定が agent-workspace の拡張を挙げていることを求める。そうでなければ、このリポジトリの setup が書いた設定（このリポジトリの照合の拡張を挙げる）でも起動する。今の auth.json に `!command` の key は無い（provider の名前と key の種類だけを見た）。ソースを読んで確かめ、agent-workspace のヘルパは実行していない
4. このリポジトリのヘルパ（`.devcontainer/pi-superagents-exec.zsh`）は、`pi_superagents_exec` の `launcher_dir`（bind 元と、起動前の検査の対象）と、`pigt`・`pidid` の起動前の検査（`pi_launcher_require_models`）の読み先で、それぞれ `${HOME}/.pi/agent/extensions/subagent.d/<launcher>` を組み立てている
5. pi-superagents が読むのは `~/.pi/agent/extensions/subagent/config.json` だけで、`subagent.d/` はこのリポジトリ（と agent-workspace）の取り決めである。Pi の拡張の自動探索は `~/.pi/agent/extensions/*.ts` と、`index.ts`（または manifest）を持つ直下のサブディレクトリだけを読む（#310 の Spec の事実 9）。`subagent.d/` は `index.ts` を持たないので、その下のディレクトリ・ファイルは親の Pi に読み込まれない
6. このリポジトリの setup は、ランチャーの中（共有の bind 先にランチャーのディレクトリが重なっている状態）で実行されると、`subagent.d/*/` のどれかが共有の bind 先と同じ実体かを見て、何も書かずに止まる（#307）

## 決定記録

### D1. 往復をなくす方法

- 選択した案: C。このリポジトリのランチャー別の設定の場所を `~/.pi/agent/extensions/subagent.d/create-reso-world/<launcher>/config.json` に移す。ヘルパの bind 元・起動前の検査、setup の配置先をそろって変える。agent-workspace が書く `subagent.d/<launcher>/` は、このリポジトリのランチャーも setup も読まず、書かない
- 検討した別案:
  - A. このリポジトリのランチャーが agent-workspace の拡張も同等として受け付ける: agent-workspace の拡張は `ctx.scopedModels` に名指しの model があるかだけを見るので、bare のパターンの部分一致（#310 の Spec の事実 10）と、既存のセッションを引き継ぐ子が `--models` と違うセッションの model で動く場合（同じく事実 12・D2a）を通す。往復は止まるが、このリポジトリのランチャーの守りが、最後に setup を実行したリポジトリで変わる
  - B. 2 つのリポジトリで照合の拡張のパスと中身をそろえる: どちらかを定義元にして、もう片方の setup も同じものを置く必要があり、agent-workspace の変更が要る（Issue の範囲外）。このリポジトリだけでそろえると、A と同じく弱い方の拡張に合わせるか、同じファイルを互いに上書きし合う（#310 の D1 で退けた案）
  - D. 今のまま（止まったら setup を実行し直す）とし、README に往復を書く: 止まり方は案内付きで安全だが、agent-workspace の setup を実行するたびにこのリポジトリのランチャーが止まり、Issue の問題が残る
- 選択理由: このリポジトリの変更だけで、agent-workspace の setup の実行がこのリポジトリのランチャーに届かなくなる。このリポジトリのランチャーの守り（tier 設定と #310 の照合）は、どちらの setup を最後に実行したかで変わらない。agent-workspace のランチャー（事実 3）は、これまでどおり `subagent.d/<launcher>/` の自分の setup の設定を読み、このリポジトリの setup に書き換えられなくなる
- 委任指示: issue-to-pr の推奨案での委任

### D2. 照合の拡張の置き場所

- 選択した案: 照合の拡張は今の `~/.pi/agent/extensions/subagent.d/pi-superagents-model-guard.ts` のまま変えない。13 の tier 設定の `superagents.extensions` もそのまま
- 検討した別案: `subagent.d/create-reso-world/` の下に移す
- 選択理由: このファイルの名前を使うのはこのリポジトリだけで、取り合いが無い（agent-workspace は別の名前のファイルを置く。事実 2）。移すと、13 の tier 設定と、README の手順で `superagents.extensions` に手で足した利用者の設定が、どれも照合の検査で止まる
- 委任指示: issue-to-pr の推奨案での委任

### D3. 既存の環境の移行

- 選択した案: 旧位置（`subagent.d/<launcher>/config.json`）の内容は写さない。setup は、通常と `--if-absent` のどちらでも、新しい位置に設定が無ければリポジトリの tier 設定を置く（rebuild の `--if-absent` で移行が済む）。旧位置のファイルは読まず、退避もせず、消さない。新しい位置に設定を置いた setup の実行で旧位置に設定があったときは、旧位置を読まなくなったことと、旧位置で tier を編集していたら新しい位置に写すことを、1 回だけ表示する。ランチャーは、新しい位置に設定が無ければ、今までどおり setup の実行を案内して起動しない
- 検討した別案:
  - 旧位置の設定がこのリポジトリの照合の拡張を挙げていれば写す: 旧位置は 2 つのリポジトリの setup が書き合うので、利用者が編集したものか、どちらかの setup が書いたものかを決められない。今の環境の旧位置はどれもこのリポジトリの照合の拡張を挙げておらず（事実 1）、写しても照合の検査で止まる
  - 旧位置を消す・移す: agent-workspace のランチャーが読むファイルであり、このリポジトリが消してよいものではない
- 選択理由: 今の 13 の旧位置の `modelTiers` は、リポジトリの tier 設定と同じなので（事実 2）、リポジトリの tier 設定を置いても model は変わらない。tier を編集していた利用者には、setup の出力で写す必要を伝える（#305 の「利用者が明示編集した tier は受け入れる」を、利用者の手で引き継げるようにする）
- 委任指示: issue-to-pr の推奨案での委任

### D4. setup の、ランチャーの中での実行の拒否

- 選択した案: 共有の bind 先と同じ実体かを見るディレクトリに、新しい位置（`subagent.d/create-reso-world/*/`）と旧位置（`subagent.d/*/`）の両方を含める
- 検討した別案: 新しい位置だけを見る
- 選択理由: 更新の前にランチャーから起動した Pi（旧位置を重ねている）や、agent-workspace のランチャーの中で setup を実行すると、停止用の設定が旧位置のランチャーの設定を置き換え、本物の共有の bind 先は守られないまま成功と表示される（#307 と同じ不具合）。旧位置も見れば、どちらでも止まる
- 委任指示: issue-to-pr の推奨案での委任

### D5. ヘルパの場所の組み立て

- 選択した案: ヘルパに、ランチャー名から設定のディレクトリを組み立てる関数を 1 つ置き、`pi_superagents_exec`（bind 元・起動前の検査）と `pi_launcher_require_models`（`pigt`・`pidid` の起動前の検査）の両方が使う
- 検討した別案: 2 か所の文字列をそれぞれ書き換える
- 選択理由: 2 か所がずれると、検査した設定と子 Pi に重ねる設定が別のファイルになり、検査が守らない設定で子が動く。組み立てを 1 か所にすれば、ずれない
- 委任指示: issue-to-pr の推奨案での委任

### D6. 文書と表示

- 選択した案: `.devcontainer/README.md` のランチャー別の設定の場所（配置の一覧、Plannotator の確認先、bind の図、照合の節の agent-workspace の段落）を新しい位置に直し、場所を分けた理由（共有の `~/.pi` を agent-workspace と使い合う）と既存の環境の移行（D3）を書く。`scripts/setup_pi_commandcode_goat.zsh`・`scripts/setup_pi_opencode_go.zsh` が表示する設定の場所も直す。`docs/maatlog-poc-porting.md` の R-8 のコマンドは、#17 の移植の記録なので変えない
- 選択理由: 利用者がランチャー別の設定を探す・編集する場所が変わるので、表示と文書が旧位置を指すと、agent-workspace の設定を編集してしまう
- 委任指示: issue-to-pr の推奨案での委任

### D7. agent-workspace の側の挙動の確認

- 選択した案: agent-workspace の main のソースを読んで、このリポジトリの setup が書いた設定での挙動を事実 3 に記録し、agent-workspace のコードは実行しない。C の後は、このリポジトリの setup は agent-workspace のランチャーが読む設定を書かないので、このリポジトリの setup が agent-workspace のランチャーの挙動を変えることは無くなる
- 検討した別案: agent-workspace のヘルパを一時 HOME で実行して確かめる（C の後は、このリポジトリの setup が書いた設定を agent-workspace のランチャーが読む経路が無くなるので、確かめる対象が残らない）
- 委任指示: issue-to-pr の推奨案での委任。agent-workspace のリポジトリの変更は Issue の範囲外

### D8. テスト

テストの採用基準（`AGENTS.md`）の S に当たるものだけを書く。

- 書く:
  - setup が旧位置を書き換えないこと: 一時 HOME の旧位置 `subagent.d/pigt/config.json` に agent-workspace の形の設定を置いて setup（通常の、置き換える方）を実行し、旧位置のバイト列が変わらず、旧位置に退避のファイルが増えず、新しい位置にリポジトリの tier 設定が置かれること（通る例）。壊れると、このリポジトリの setup が agent-workspace のランチャーの設定を黙って書き換え、往復が戻る（S: 別の対象の上書き）
- 既存のテストの調整（S のまま、場所だけを新しい位置にする）:
  - 各ランチャーの bind 元が自分の設定のディレクトリであること（`test_launchers_wrap_pi_with_their_own_config`）。新しい位置を求める。D5 の 2 か所のずれで、検査した設定と違う設定を重ねる場合もここで気付く（`pigt`・`pidid` は起動前の検査も新しい位置の設定を読んで通る）
  - ランチャーの中での setup の拒否（`test_setup_refuses_inside_a_launcher`）。新しい位置のディレクトリを重ねる
  - そのほか、一時 HOME に設定を置くテストと準備（`make_home`・`model_home`、退避・`--if-absent`・停止用の設定のテスト、`tools/devenv_migration/tests/` の 2 ファイル）
- 書かない:
  - 旧位置を重ねたランチャーの中での setup の拒否（D4。同じ守りの別の組み合わせ＝ D）。一時的な確認で確かめる
  - agent-workspace の setup が旧位置を書き換えた後も、このリポジトリのランチャーが起動すること（ランチャーが旧位置を読むように壊れると、照合の検査が止める＝ L）。一時的な確認で確かめる
  - 旧位置があるときの表示、README、ほかの setup の表示（F・L）
- 委任指示: issue-to-pr の推奨案での委任

### D9. 実行方式

- 選択した案: `superpowers:executing-plans`（このセッションが inline で実装する）
- 検討した別案: `superpowers:subagent-driven-development`（Task ごとにサブエージェント）
- 選択理由: Task は 2 つで順番に依存し（ヘルパ・setup・テスト → 文書と表示）、変更は場所の文字列と小さな分岐に限られる。最後のブランチ全体のレビューはサブエージェントに依頼する
- 委任指示: issue-to-pr の推奨案での委任

### D10. 担当とループのオプション

- Plan の Task の担当: `implement_task.py check` の結果 `assignment: {agents: ["self"], fallback: []}`・`self: true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用（利用者の `--implement` の指定は無い）。個人設定 `/home/vscode/.config/agent-runner/config.toml` は読み込まれたが、`workflows.issue` の `implement` を変えていない
- ループのオプション: 利用者の指定は無い（`loop_args: []`）。`check-options` の結果は既定の適用で、`max_cycles: 3`、レビュアー `cursor_grok4_xhigh`・`devin_swe2-max_default`・`pi_commandcode_deepseek4-flash_max`、修正の担当 `claude-code_opus_default`、自己レビュー・修正の確認は `self`
- 委任指示: 利用者の指示 `--merge`

## 受け入れ基準

1. このリポジトリのランチャーは、`~/.pi/agent/extensions/subagent.d/create-reso-world/<launcher>/` を共有の bind 先へ重ね、起動前の検査（tier・照合の拡張・`pigt`・`pidid` の model）も同じディレクトリの `config.json` を読む
2. `setup_pi_superagents.zsh` は、通常と `--if-absent` のどちらでも、新しい位置にランチャー別の設定を置き（通常は既存を退避してから置き換え、`--if-absent` は無いものだけ）、旧位置 `subagent.d/<launcher>/` のファイルを書かず、退避せず、消さない。agent-workspace の `subagent.d/pi-superagents-tier-guard.ts` にも触らない
3. このリポジトリの setup の後に、旧位置が agent-workspace の形の設定に置き換わっても、このリポジトリのランチャーは起動前の検査を通る（往復が無い）
4. 新しい位置に設定を置いた setup の実行で旧位置に設定があったとき、旧位置を読まなくなったことと、tier を編集していたら写すことを表示する。新しい位置に設定が無いランチャーは、今までどおり setup の実行を案内して起動しない
5. setup は、新しい位置と旧位置のどちらのランチャーのディレクトリを重ねた中でも、何も書かずに止まる
6. 照合の拡張の場所と 13 の tier 設定の内容は変わらない
7. `.devcontainer/README.md` に、新しい位置、分けた理由、既存の環境の移行を書き、ほかの setup の表示も新しい位置を指す
8. 検証の入口（`README.md` の「テスト」。ワールドの行を除く）がすべて通る

### 動作環境・実入力・防御範囲

- 動作環境: Dev Container（Ubuntu 26.04 LTS）、zsh、bwrap、Node.js 24、Pi 1.5.0、pi-superagents 1.14.4。`~/.pi` は host の `~/.pi` の bind mount で、usaturn/agent-workspace の Dev Container とも共有する
- 実入力: 旧位置の `subagent.d/<launcher>/config.json` は、agent-workspace の setup が書いた設定（`superagents.extensions` に `~/.pi/agent/extensions/subagent.d/pi-superagents-tier-guard.ts` だけ、tier はこのリポジトリと同じ）、このリポジトリの以前の setup が書いた設定、`superagents.extensions` の無い古い設定、利用者が tier を編集した設定のどれか。新しい位置は、無い（移行前）か、このリポジトリの setup が書いた設定か、利用者が編集した設定
- 防御範囲: 対象は、このリポジトリのランチャー（`.devcontainer/<launcher>` と `~/.local/bin/<launcher>`）、共通ヘルパ、`setup_pi_superagents.zsh`（`install_beforehand.bash` からの `--if-absent` と、provider の setup からの呼び出しを含む）。対象外は、agent-workspace のランチャー・setup・拡張の挙動（Issue の範囲外）、共有の bind 先 `subagent/config.json` の停止用の設定（agent-workspace の setup は書かない。事実 2）、`~/.pi/agent/extensions/` 直下の拡張（`herdr-launcher-resume.ts` など。ランチャー別の設定ではない）

## 対象外

- usaturn/agent-workspace のリポジトリの変更（Issue の範囲外）。agent-workspace の側で同じ取り合いを避けるかは、agent-workspace の Issue で決める
- 旧位置の設定の削除・自動の移行（D3）
- 利用者の環境での setup の実行と、実際の資格情報での確認（マージの後の利用者の確認）

## 全体レビューの判断

base `2fa03f19` から `24ec12a4` までを、新しいサブエージェント（Opus、読み取りだけ）がレビューした（判定 With fixes。Critical・Important は 0、Minor 4。「直さずにマージしても安全」）。受け入れ基準 1〜7 と Review Focus 1〜5 は満たす（一時 HOME の最小再現を含む）、8 はレビューの時点では検証の途中だったので確かめられない、とされた（8 はその後の検証で満たした）。Minor は executing-plans の規則と、致命的な指摘だけを直す方針により直さず、持ち越し候補にする。

- Minor 1: `pigt`・`pidid` は、新しい位置に設定が無い移行の直後に、設定の有無の検査より前に model の起動前の検査が走るので、「設定が見つかりません」ではなく「model catalog / models.json / tier config を解決できません」と出る。終了コード 1 で、案内の 3 行目に `zsh scripts/setup_pi_superagents.zsh --if-absent` も出るので、受け入れ基準 4 は満たす。直さない（移行の手順は README と Issue のコメントで、setup を先に実行するよう伝える）
- Minor 2: provider の setup（`setup_pi_opencode_go.zsh`・`setup_pi_commandcode_goat.zsh`）はヘルパだけを新しくし、ランチャー別の設定を置かない。#310 の前からある形で、ランチャーは「設定が見つかりません」と setup の案内で止まる（L）。直さない
- Minor 3: `.devcontainer/README.md` の「子 Pi の model の照合」の、#310 より前からの環境の移行の段落は、#313 の移行（新しい位置に設定が無ければ `--if-absent` でも置かれる）と併せて読むと分かりにくい。誤りではないので直さない
- Minor 4: `.devcontainer/test-pi-superagents.bash` の `model_home` の JS は、`LAUNCHER_CONFIG_ROOT` を使わずに新しい位置を書く。場所を変えればテストが失敗するので気付ける（L）。直さない
- レビュアーが判断の対象外にしたもの（旧位置で tier を編集していた利用者への注意が 1 回だけであること、旧位置を重ねた中での拒否をテストにしないこと、更新の前に起動した Pi のセッション、`docs/maatlog-poc-porting.md` の R-8）は、どれも Spec の D3・D8・D6 で決めたとおりで、変えない

## マージの後でなければ確かめられない項目

- 利用者の環境で、ランチャーの外のシェルで `zsh scripts/setup_pi_superagents.zsh`（または rebuild）を実行し、新しい位置に 13 の設定が置かれ、旧位置が変わらないこと。その後に使っているランチャー（`pigt` など）が起動前の検査を通って起動すること
- agent-workspace の setup をもう一度実行した後も、このリポジトリのランチャーが起動すること
