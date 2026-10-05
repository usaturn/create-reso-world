# PR #33 issue-22-integration のレビュー指摘の選別と修正設計

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/33
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/issue-22-integration`
- 指摘を検証した HEAD: `77aa7433c5f9c7a932a3cf8f0b83c02924fd5015`
- 入力: `reviews/#33-feat-issue-22-integration/` 配下の全 4 ファイル
- 作成日: 2026-10-05
- 経路: **bounded**（PR が追加・変更した文書 4 本に閉じた修正。コード・テスト・設定ファイルとインターフェースは変えない）
- 状態: **draft**。同日のユーザ依頼で「修正が必要なら推奨案を基本に修正し、検証・PR 全体の再レビューを完了してプッシュする」「同じ原因の関連箇所は PR 差分外も修正する」「後続のレビュー・修正で手戻りを発生させない」「確認作業をユーザへ返さない」ことが事前に指示されている。判断保留の 1 件は、この指示に基づいて推奨案を採用した
- 関連: Spec `docs/superpowers/specs/2026-10-05-issue-22-integration-design.md`、Plan `docs/superpowers/plans/2026-10-05-issue-22-integration.md`

## 結論

修正が必要である。GPT M-1（rebuild の確認表の R-4 のコマンドが、廃止した変数が残っているとき `MAAS_ANTHROPIC_TOKEN` の値をそのまま表示する）を、一時 HOME とダミー値で再現した。比較表自身の「認証情報の値は記録しない」と食い違い、利用者が結果を記録・共有する手順で秘密情報が漏れる。ほかの 5 件も現行 HEAD で再現した。

## レビュー入力

| ファイル | 対象 HEAD | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | `77aa7433c5f9` | Info 2 |
| `gpt-6.1-sol.md` | `77aa7433c5f9` | Medium 1、Low 1 |
| `SWE-2-Max.md` | `77aa7433c5f9` | Info 2 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `77aa7433c5f9` | Info 2 |

対象 HEAD はすべて現行 PR HEAD と一致する。

## 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 5 |
| 判断保留 | 1（推奨案を採用） |
| 対応しない | 0 |

重複（GPT L-1 と SWE I-2、SWE I-1 と DeepSeek I-2）は 1 件として数える。

### 全指摘一覧

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| GPT M-1 | 比較表の R-4 の確認方法 `zsh -ic 'env' \| grep -E ...` が、残った変数の値まで表示する。Plan の埋め込み文書にも同じコマンドがある | 対応する (a)(b) | 一時 HOME の `.zshrc` に `zshrc.txt` の秘密情報の読み込みだけを置き、ダミーの `MAAS_ANTHROPIC_TOKEN` を `env` に書いて実行すると、exit 0 で `MAAS_ANTHROPIC_TOKEN=<ダミー値>` が出た。親プロセスから継承した場合も同じ。比較表 201 行の「認証情報の値は記録しない」と食い違う |
| GPT L-1 / SWE I-2 | R-7 の dry-run は、ランチャーの前提（認証など）の確認が dry-run の分岐より先に走る。前提が無いと argv が出ないのに、期待する結果は「9 本とも」としている | 対応する (b) | 前提の無い一時 HOME では argv を出すのは `pigo`・`pigod`・`pigou` の 3 本だけで、残る 6 本は exit 1。ダミーの OAuth とキーを与えると 9 本とも argv を出す。前提は `piga`・`pigs`・`pigl` が Codex OAuth、`pixg` が xAI OAuth、`piccg`・`piccd` が `COMMANDCODE_API_KEY` と `models.json` の commandcode の定義、`pigou` が `union-alpha` の定義、9 本に共通で `bwrap`・共通ヘルパ・ランチャー別の設定（`pi-superagents-exec.zsh` 109〜126 行）。dry-run の分岐は 143 行 |
| Opus I-1 | `.devcontainer/README.md` の「rebuild しない場合」が、`--if-absent` 付きの `setup_pi_superagents.zsh` を「エージェント向けツールの導入」にあるとして案内するが、その節にあるのは `--if-absent` なしのコマンドである | 対応する (b) | 参照先の 18 番（197 行）は `--if-absent` なし。`--if-absent` 付きは「pi の TUI モードと Herdr のスクロール履歴」（613 行）にだけある。`setup_pi_superagents.zsh` は両方のモードで共通ヘルパを毎回置き直し、ランチャーは配置しない。手順 4 の `--if-absent` なしの実行でヘルパも更新されるので、rebuild しない場合に追加で要るのはランチャー 9 本の `install -m 0755` だけである。参照先の 8 番の `cp .devcontainer/pi-models.json ~/.pi/agent/models.json` は既存の定義を上書きするので、節全体をなぞると独自のモデル定義が消える |
| DeepSeek I-1 | 「API トークン」の `OPENCODE_GO_API_KEY` の項が、旧名を引き継ぐランチャーとして `pigs`・`pixg` だけを挙げている | 対応する (b) | 同じ条件の引き継ぎは `pigo`・`pigod`・`pigou`・`pigs`・`pixg` の 5 本にある（`pigo:35`・`pigod:35`・`pigou:40`・`pigs:32`・`pixg:32`）。ダミー値で 9 本を実行し、旧名だけのときに 5 本の子プロセスへ値が届くことを確かめた。README のほかの箇所には `pigo`・`pigod`・`pigou` の引き継ぎの記述が無く、直前の項（`auth.json` に資格情報が無ければ `OPENCODE_API_KEY` が要る）と合わせると、旧名だけの環境では 3 本が動かないと読める。Spec 4.3 節に同じ列挙がある |
| SWE I-1 / DeepSeek I-2 | Plan の Task 1 Step 4 の埋め込み文書が D-15 の行を含まない旧版で、Step 5 の期待値が `rows: 91`（実物は 92 行）。「実行時の変更」がこれに触れていない | 対応する (b) | 埋め込み文書と実物の差分は D-15 の行 1 行だけで、Plan の検査スクリプトの結果は埋め込み版が 91 行、実物が 92 行。「実行時の変更」は Task 3 のパッチと検査スクリプトだけを旧版としており、Task 1 の埋め込み文書と期待値、Architecture（「新規 1、変更 2」）、Global Constraints（テストファイルを変えない）、Task 4 Step 3（5 ファイル）の食い違いに触れていない。ガードの失敗の数も 858 行（比較表 17 行とルートの README 3 行）と 865 行（21 行）で食い違う。`9ebeb29` の親で数えると 20 か所である |
| Opus I-2 | `.devcontainer/README.md` に見出し「既存環境の更新」が 2 つある（新設の `##` と、「Superpowers スキルの探索パス」配下の既存の `#####`）。比較表は名前だけで参照している | 判断保留 → 推奨案を採用 | 変更前（`01affb7`）の同名の見出しは 1 つだけ。既存の `#####` を見出しとして参照する箇所とアンカーのリンクは 0 件で、テスト（`test-docs.bash`・`test-readme.bash`）も見出し名に依存しない。誤動作ではないが、1 行の改名で参照の曖昧さが消える |

## 修正方針

### F-1 R-4 の確認方法で値を表示しない（GPT M-1）

- `docs/maatlog-poc-porting.md` の R-4 の確認方法を `zsh -ic 'env' 2>/dev/null | grep -oE '^(PI_DISTILL_[A-Z_]+|PI_EXTENSIONS_LOCALE|MAAS_ANTHROPIC_TOKEN)='` にする（表の中では `|` を `\|` と書く）。rebuild 前の値を取ったときの Plan の Task 1 Step 8 と同じ形で、残っていれば変数名だけが出る。期待する結果に「値は出ない」を足す
- 「確認項目と記録」の冒頭の「認証情報の値は記録しない」に、確認方法のコマンドも値を表示しないことを足す
- Plan の埋め込み文書は F-5 で最終版に揃える

検証: 一時 HOME とダミー値で、新しいコマンドが変数名だけを出し値を出さないこと、変数が無いときは何も出ないことを確かめる。比較表から確認方法のセルを取り出して実行する。

### F-2 R-7 の前提を書く（GPT L-1 / SWE I-2）

- R-7 の確認方法に、dry-run でも argv を出す前に各ランチャーの前提を確かめることと、ランチャーごとの前提を書く。9 本に共通の前提（`bwrap`・共通ヘルパ・ランチャー別の設定）は rebuild で配置されることも書く
- 期待する結果を「前提がそろったランチャーは…」にし、前提の無いランチャーは「前提が未設定のため未確認」と記録すると書く
- rebuild 前の列は、確かめたのが `pigo`・`pigs`・`pixg` の 3 本であることが分かる書き方にする（他の 6 本も `--tui-mode` を持っていたと読まれないため）

検証: 書いた前提が `pi-superagents-exec.zsh` とランチャー 9 本の該当行と一致することを照合する。ランチャーとテストは変えない。

### F-3 「rebuild しない場合」の参照を直す（Opus I-1）

`.devcontainer/README.md` の「既存環境の更新」の「rebuild しない場合」のランチャーの項を、「エージェント向けツールの導入」の 9〜17 の `install -m 0755` で 9 本を置き直すこと、同じ節の 8 の `models.json` のコピーは既存の定義を上書きするので行わないこと、共通ヘルパは手順 4 の `setup_pi_superagents.zsh` が更新することに書き換える。

検証: 参照先の番号と内容を README で照合する。Plan の Task 2 の受け入れ検査（`check_readme_integration.bash devcontainer`）と `test-readme.bash` が通ること。

### F-4 `OPENCODE_GO_API_KEY` の引き継ぎを 5 本にする（DeepSeek I-1）

- `.devcontainer/README.md` の「API トークン」の項を「OpenCode Go を使う `pigo`・`pigod`・`pigou`・`pigs`・`pixg` は、`OPENCODE_API_KEY` が空のときだけ…」にする。「`OPENCODE_GO_API_KEY` は旧名」の文は保つ
- Spec 4.3 節の同じ列挙も 5 本にする
- 引き継ぎの検査を 5 本に広げるテストの追加は、Spec の D-11（テストを追加しない）の範囲外なので行わない

検証: 5 本のランチャーの引き継ぎの行と照合する。

### F-5 Plan の記録を最終版と揃える（SWE I-1 / DeepSeek I-2、GPT M-1 の Plan の箇所、Opus I-1 と DeepSeek I-1 の Plan の箇所）

- Task 1 Step 4 の埋め込み文書を、最終版の `docs/maatlog-poc-porting.md` と同一にする。Step 5 の期待値を `rows: 92` にする。全文の埋め込みなので機械的に揃えられ、値を表示する確認方法を Plan に残さない
- Task 2 Step 3 のパッチを、`01affb7` から最終版の `.devcontainer/README.md` への差分にする。Task 2 の Files に F-6 の見出しの改名を足す。Task 2 の受け入れ検査はこのパッチで通る
- Task 3 のパッチと、Task 2・3 の一時の検査スクリプトのうちルートの README の期待値は、既存の「実行時の変更」のとおり D-15 の前の版のまま残す
- 「実行時の変更」のガードの失敗の数を 20 か所（比較表 17、ルートの README 3）に揃える。PR #33 のレビュー修正の段落を足し、Task 1・2 を最終版に揃えたこと、Task 1 の時点の版の所在（`0132c84`）、計画のまま残した記述（Architecture、Global Constraints、Task 3、Task 3 Step 5 の参照の数、Task 4 Step 3 の 5 ファイル）と最終の値を書く

検証: Plan から Task 1 Step 4 の埋め込み文書を取り出して最終版と `diff` が空であること。Task 2 Step 3 のパッチが `01affb7` に当たり、結果が最終版の `.devcontainer/README.md` と一致すること。Plan の網羅の検査スクリプトが最終版で `rows: 92`・`missing: 0` を返すこと。

### F-6 既存の `#####` の見出しを改名する（Opus I-2、推奨案を採用）

- 「Superpowers スキルの探索パス」配下の `##### 既存環境の更新` を `##### pi-superagents の版の更新` にする。節の内容（pi-superagents を v1.14.3 以降へ更新する手順）に合う名前で、新設の `## 既存環境の更新` と比較表・Spec・Plan の参照は変えずに済む
- Spec の 6 章（`.devcontainer/README.md` の既存の見出しは変えない）に、この改名だけを例外として理由とともに書く。Spec 2 章の変更内容にも足す

検証: `.devcontainer/README.md` の見出しに重複が無いこと。旧名の `#####` を見出しとして参照する箇所が無いこと（`git grep`）。`test-docs.bash`・`test-readme.bash` が通ること。

## 全体の検証

worktree のルートで実行する。

- `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest -q tests/skills .agents/skills`（基準は `77aa743` で PASS、27/27、516 passed・1 skipped）
- F-1〜F-6 の個別の検証
- Plan の一時の検査スクリプト（網羅、README の受け入れ検査、節名の参照）を最終版に対して実行する
- PR 全体の独立した再レビュー。指摘があれば直して再レビューを繰り返す

## 範囲外

- ランチャー・`pi-superagents-exec.zsh`・テストの変更（dry-run の前提の挙動、引き継ぎの検査の拡張）
- PR の「マージの条件」（利用者の rebuild と「rebuild 後」の列の記録）。このレビュー修正では変えない
