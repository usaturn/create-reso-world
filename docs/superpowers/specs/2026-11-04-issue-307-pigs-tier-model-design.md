# Issue #307 ランチャーを通さない Pi で同梱の既定 model に切り替わる経路を止める 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/307
- 実行許可: 利用者の指示 `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/307 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない

## 調査の結果

### 起きたこと

`worlds/tools` の親セッション `01a1a516`（2026-11-04 05:45 UTC 開始、`openai-codex/gpt-6.1-sol` / `xhigh`）で、子のモデルが途中から変わった。セッションのファイルの subagent の結果（`details.results[].model` / `thinking`）を時刻順に並べると次のとおり。

| 時刻（UTC） | ロール（tier） | 子の model / thinking |
| --- | --- | --- |
| 06:10〜08:26 | sp-implementer（balanced）、sp-debug（max） | `gpt-6.1-sol` / `xhigh`、`gpt-6.1-sol` / `max`（pigs の tier どおり） |
| 08:56 以降 | sp-implementer（balanced） | `glm-5.3-flash` / `high`（Issue の 7 件） |
| 08:56 以降 | sp-debug・sp-review（max） | `gpt-6.1-sol` / `high` |
| 13:30 | sp-research（cheap） | `minimax-m3` / thinking なし |

08:56 以降の 3 tier は、pi-superagents 1.14.4 の同梱の既定（`default-config.json`: cheap `opencode-go/minimax-m3`、balanced `opencode-go/glm-5.3-flash` / `high`、max `openai/gpt-5.6-sol` / `high`）と一致する。max の `openai/gpt-5.6-sol` は `openai` の資格情報が無いため、子 Pi が別のモデル（`gpt-6.1-sol`）を選んだと見られる。

### 原因

1. 08:37〜08:46 UTC に PC が負荷で落ちた（セッション中の利用者の発言「パソコンがCPU負荷に耐えきれなくなって落ちました」「piセッションは少し巻き戻っています」）
2. 08:46:35 UTC に Herdr のサーバーがセッションを復元した（`~/.config/herdr/herdr-server.log` の `session restore evaluated`）。Herdr の `[session] resume_agents_on_restore` は既定で有効で、ペインを作ってから約 2 秒で Pi が起動している。Herdr の Pi 連携（`~/.pi/agent/extensions/herdr-agent-state.ts`）はセッションのパスだけを報告し、再開コマンド（`resume_argv`）を報告しないので、Herdr は `pigs` ではなく Pi を直接起動して再開した
3. ランチャーを通らないので bwrap の mount が無く、pi-superagents は共有の bind 先 `~/.pi/agent/extensions/subagent/config.json` を読んだ。この実ファイルは 2026-09-12 に拡張が書いた同梱の既定の写しで、balanced は `opencode-go/glm-5.3-flash` / `high`
4. 親の model は再開したセッションのものを引き継ぐ（`model_change` は開始時の 1 件だけ）ので、親は pigs と同じ `gpt-6.1-sol` / `xhigh` に見えた

拡張は tier ごとに、ユーザー設定の上書きを同梱の既定の上に重ねる（`config-validation.ts` の `mergeModelTiers`）。ユーザー設定が無い・tier が欠けると、その tier は警告なく同梱の既定 model になる。導入済みの拡張のソースを一時ディレクトリへ複製し、設定の読み込み（`loadRuntimeConfigState`）とモデルの解決（`resolveEffectiveModel`）をファイルを変えずに実行した結果は次のとおり。

| 読む設定 | 結果 |
| --- | --- |
| 無い、または `{}` | 停止しない。balanced → `opencode-go/glm-5.3-flash` / `high` |
| 未知のトップレベルのキーを持つ設定 | 停止する（`blocked: true`。subagent ツールは子を起動せず、理由を返す）。拡張の移行処理が `superagents` を書き足しても、キーは残るので停止は続く |
| pigs の設定 | 停止しない。balanced → `openai-codex/gpt-6.1-sol` / `xhigh` |

Issue にある、導入済みの `pi-superagents-exec.zsh` と管理元のハッシュの差は、#305 で足した `pi_launcher_require_models`（pigt・pidid だけが呼ぶ）が導入済みに無いことによる。pigs の経路は通らないので、今回の切り替えとは関係しない。

## 目的

- ランチャーを通さずに起動した Pi（素の `pi`、Herdr の復元による再開）で、利用者が選んでいない同梱の既定 model へ子の要求を送らない
- ランチャーの tier 設定が欠けていても、欠けた tier を同梱の既定 model で黙って埋めない
- 起きたときに、どの設定を読んだか・子の実際の model を追えるよう、調べ方を残す

## 非目的・範囲外

- pi-superagents・Pi 本体・Herdr の変更（外部のパッケージ）
- Herdr の復元を、ランチャーを通した再開にすること（`resume_argv` の報告）。停止で安全は保てるので、利便性の改善として後続の Issue にする
- 子 Pi が tier の model を解決できないときの切り替えを、最初の要求の前に止めること（Issue の「子の要求モデルと実モデルを最初のモデル要求前に確認」）。親の tier の解決とは別の経路で、Pi の子プロセスの中の拡張が要る。後続の Issue にする
- 拡張の実行記録に設定のパス・ロールの出所を足すこと（拡張の変更になる）

## 避けたい結果

- 素の `pi` で、黙って同梱の既定 model の子が動き続ける
- setup が、利用者の既存の共有設定を退避せずに消す
- ランチャーの通常の起動（tier が揃った設定）を止めてしまう

## 設計

### A. 共有の bind 先に停止用の設定を置く

`scripts/setup_pi_superagents.zsh` は、共有の bind 先 `~/.pi/agent/extensions/subagent/config.json` に、未知のトップレベルのキー `launcherRequired_doNotRemove_restartPiViaLauncher` を持つ停止用の設定を置く。ランチャーを通さない Pi では、拡張が次を表示して subagent ツールを止める。

```text
pi-superagents is disabled because config.json needs attention.
Path: ~/.pi/agent/extensions/subagent/config.json

- launcherRequired_doNotRemove_restartPiViaLauncher: is not a supported config key.
```

キーの値には、理由と直し方（キーを消さず、ランチャーから起動し直す）を日本語で書く。ランチャーの中では bwrap がランチャーのディレクトリを重ねるので、この設定は見えない。

- 既存のファイルがこのキーを持つ JSON のオブジェクトなら、そのまま残す（拡張の移行処理が書き足した内容を含む）
- それ以外の既存のファイル（今回の同梱の既定の写しなど）は、ランチャー別の設定と同じ名前（`config.json.bak.YYYYMMDD-HHMMSS`、同じ秒なら `.1`, `.2`, …）で退避してから置き換える
- 通常と `--if-absent` のどちらでも行う。rebuild（`install_beforehand.bash` が `--if-absent` で呼ぶ）で既存の環境にも入れるため
- `config.json` が通常のファイルでない（ディレクトリ・symlink）ときは、触らずに止める
- ランチャーの中（共有の bind 先が `subagent.d/<launcher>` と同じディレクトリに見える。`-ef` で比べる）では、何も書かずに止める。そこへ書くとランチャーの設定を置き換え、本物の共有の bind 先は守られないまま成功と表示してしまう（ブランチ全体のレビューの指摘）

### B. 全ランチャーで tier が揃っているかを起動前に確かめる

`pi-superagents-exec.zsh` の `pi_superagents_exec` は、ランチャーの設定ファイルがあることを確かめた後、bwrap の引数を組む前（dry-run の前）に、`superagents.modelTiers` に `cheap`・`balanced`・`max` がそろい、それぞれの model が `provider/model` の形の文字列であることを確かめる。欠けていれば理由と直し方を出して止まる。tier の値は、拡張と同じく文字列か `{ "model": … }` のオブジェクトを受け付ける。thinking は確かめない（欠けても model は変わらない）。設定の中身はエラーに出さない。

pigt・pidid の起動前の検査（catalog と thinking の照合）はそのまま残す。

### C. README

`.devcontainer/README.md` の「pi-superagents のランチャー別 model tier」に、次を書く。

- 同梱の既定 model に切り替わる仕組みと、今回の経路（Herdr の復元）
- 停止用の設定（A）と、キーを消さないこと
- Herdr の復元の後は、復元された `pi` を終了し、ランチャーで再開する（`pigs --session <セッションファイル>`、または同じディレクトリで `pigs -c`）
- 調べ方: 子の model / thinking（`~/.pi/agent/run-history.jsonl`、`subagent-artifacts/<runId>_<agent>_<n>_meta.json`、セッションのファイルの subagent の結果）、親の `model_change`、Herdr の復元の時刻。同じ親セッションで cheap tier の子が `minimax-m3` になっていれば、共有の bind 先を読んでいる
- 範囲外の 2 点（後続の Issue）

あわせて、setup の作るもの（README の配置の一覧、setup の冒頭のコメント）を直す。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
| --- | --- | --- | --- | --- |
| ランチャーを通さない Pi の止め方 | 共有の bind 先に、未知のトップレベルのキーを持つ停止用の設定を置く（A） | (1) 中身を同梱と違う tier にする (2) `config.json` をディレクトリにする（EISDIR で止まる） (3) 不正な JSON を置く (4) pi-superagents をランチャーの中だけで読み込む | 拡張が正式に扱う検証の失敗で止まり、表示にキーの名前が出て理由が伝わる。(1) はどの model を選んでも利用者が選んでいない model になる。(2)(3) は表示が分かりにくい。(4) は Pi の package の登録を変える大きな変更になる | 推奨案で決定（issue-to-pr） |
| 既存の共有設定の扱い | キーが無ければ退避して置き換える。キーがあれば残す | (1) バイト列が違えば退避して置き換える (2) `--if-absent` では置き換えない | 拡張の移行処理が読み込みのたびに書き足すので、(1) は setup のたびに退避が増える。(2) では rebuild で今回の環境に入らない。README は共有の bind 先を空のまま使う前提で、既存の中身は拡張が書いた既定の写し | 推奨案で決定 |
| ランチャーの中での setup の実行 | 最初の書き込みの前に止める | (1) 停止用の設定だけを省いて続ける (2) 本物の共有の bind 先を探して書く | mount の下に隠れた本物の共有の bind 先は、ランチャーの中から見えない。(1) は守られていないのに成功で終わる。ランチャーの外で実行し直せば済む | 推奨案で決定（レビューの指摘への対応） |
| tier の検査の範囲 | 全ランチャーで cheap・balanced・max の model の有無と形を確かめる（B） | (1) pigt・pidid の catalog の検査を全ランチャーに広げる (2) 同梱の `default-config.json` の tier の一覧を読んで比べる | 欠けた tier が同梱の既定で埋まる経路だけを、JSON の読み取りで止められる。(1) は provider ごとの catalog の違いで通常の起動を誤って止める恐れがあり、#305 で新しい起動経路だけに限った決定を崩す。(2) は拡張の配置に依存する。同梱の既定の tier は今は 3 つで、予約の `reasoning` は未設定なら拡張が子を起動しない | 推奨案で決定 |
| Herdr の復元をランチャー経由にするか | 範囲外（後続の Issue） | ランチャーが `PI_SUPERAGENTS_LAUNCHER` を渡し、Pi の拡張が `resume_argv` を報告する | A で安全は保てる。Herdr の連携と報告の順序・上書きの動きを実機で確かめる必要があり、利用者の動いている Herdr に触れる | 推奨案で決定 |
| 子のモデルの照合（最初の要求の前） | 範囲外（後続の Issue） | agent-workspace の tier-guard 拡張を移植する | 今回の 7 件（balanced）は、要求した model と実際の model が一致していて、この照合では止まらない。子 Pi の中の拡張と、その検証の手間が要る | 推奨案で決定 |
| 実行記録の追跡 | README に調べ方を書く | ランチャーが起動の記録を残す | 拡張の記録（run-history・meta）に子の model と thinking があり、A で止まれば理由もセッションに残る。新しい記録のファイルは不要 | 推奨案で決定 |
| PR の Issue の指定 | `Refs #307` | `Closes #307` | 既存の環境（`~/.pi` は bind mount）への反映（setup か rebuild）と、素の `pi` で止まることの確認がマージの後に残る | issue-to-pr の規則 |

## 受け入れ基準

- 動作環境: この Dev Container（Ubuntu 26.04、zsh、Node.js 24、bwrap）、Pi 1.5.0、pi-superagents 1.14.4。テストは一時の `HOME` で行い、利用者の `~/.pi` を変えない
- 実入力:
  - 共有の bind 先に、今回の環境と同じ同梱の既定の写し（balanced `opencode-go/glm-5.3-flash`）があるときの `setup_pi_superagents.zsh --if-absent`
  - `balanced` が無いランチャーの設定（`{"superagents":{"modelTiers":{"cheap":…,"max":…}}}`）での起動
  - リポジトリの `.devcontainer/pi-superagents/<launcher>.json` そのままの設定での起動
- 防御範囲:
  - 対象: ランチャーを通さない Pi が共有の bind 先を読む経路（素の `pi`、Herdr の復元）、ランチャーの設定の tier の欠け
  - 対象外: 子 Pi が設定した model を解決できないときの切り替え（pigt・pidid の起動前の検査を除く）、Herdr の復元の再開コマンド、`PI_CODING_AGENT_DIR` だけを変えた起動（拡張は `os.homedir()` を見るので変わらない）
  - 反例として通すもの: tier が揃ったリポジトリの設定でのランチャーの起動、文字列の形の tier、停止用のキーを持つ既存の共有設定（拡張が書き足したもの）
