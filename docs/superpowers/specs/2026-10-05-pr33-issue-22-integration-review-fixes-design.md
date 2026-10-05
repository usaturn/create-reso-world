# PR #33 issue-22-integration のレビュー指摘の選別と修正設計

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/33
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `feat/issue-22-integration`
- 指摘を検証した HEAD: `77aa7433c5f9c7a932a3cf8f0b83c02924fd5015`
- 入力: `reviews/#33-feat-issue-22-integration/` 配下の全 4 ファイルと、修正後の PR 全体の独立した再レビュー（下記「再レビュー（1 回目）」〜「再レビュー（6 回目）」）
- 作成日: 2026-10-05
- 経路: **bounded**（PR が追加・変更した文書（比較表、`.devcontainer/README.md`、ルートの `README.md`、Issue #22 の Spec・Plan）と PR の本文に閉じた修正。コード・テスト・設定ファイルとインターフェースは変えない）
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

重複（GPT L-1 と SWE I-2、SWE I-1 と DeepSeek I-2）は 1 件として数える。修正後の再レビュー（1 回目）の 7 件は対応する 6、判断保留 1（推奨案を採用）、再レビュー（2 回目）の 8 件は対応する 8、再レビュー（3 回目）の 3 件は対応する 3、再レビュー（4 回目）の 5 件は対応する 5、再レビュー（5 回目）の 6 件は対応する 6、再レビュー（6 回目）の 1 件は対応する 1 である（下記）。

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

- Task 1 Step 4 の埋め込み文書を、最終版の `docs/maatlog-poc-porting.md` と同一にする。Step 5 の期待値を最終版の行数にする（F-5 の時点で 92 行、F-11 の後は 93 行、F-29 の後は 94 行、F-32・F-33 の後は 96 行）。全文の埋め込みなので機械的に揃えられ、値を表示する確認方法を Plan に残さない
- Task 2 Step 3 のパッチを、`01affb7` から最終版の `.devcontainer/README.md` への差分にする。Task 2 の Files に F-6 の見出しの改名を足す。Task 2 の受け入れ検査はこのパッチで通る
- Task 3 のパッチと、Task 2・3 の一時の検査スクリプトのうちルートの README の期待値は、既存の「実行時の変更」のとおり D-15 の前の版のまま残す
- 「実行時の変更」のガードの失敗の数を 20 か所（比較表 17、ルートの README 3）に揃える。PR #33 のレビュー修正の段落を足し、Task 1・2 を最終版に揃えたこと、Task 1 の時点の版の所在（`0132c84`）、計画のまま残した記述（Architecture、Global Constraints、Task 3、Task 3 Step 5 の参照の数、Task 4 Step 3 の 5 ファイル）と最終の値を書く

検証: Plan から Task 1 Step 4 の埋め込み文書を取り出して最終版と `diff` が空であること。Task 2 Step 3 のパッチが `01affb7` に当たり、結果が最終版の `.devcontainer/README.md` と一致すること。Plan の網羅の検査スクリプトが最終版で Step 5 の期待値（最終版は `rows: 96`）と `missing: 0` を返すこと。

### F-6 既存の `#####` の見出しを改名する（Opus I-2、推奨案を採用）

- 「Superpowers スキルの探索パス」配下の `##### 既存環境の更新` を `##### pi-superagents の版の更新` にする。節の内容（pi-superagents を v1.14.3 以降へ更新する手順）に合う名前で、新設の `## 既存環境の更新` と比較表・Spec・Plan の参照は変えずに済む
- Spec の 6 章（`.devcontainer/README.md` の既存の見出しは変えない）に、この改名だけを例外として理由とともに書く。Spec 2 章の変更内容にも足す

検証: `.devcontainer/README.md` の見出しに重複が無いこと。旧名の `#####` を見出しとして参照する箇所が無いこと（`git grep`）。`test-docs.bash`・`test-readme.bash` が通ること。

## 再レビュー（1 回目、`e4d72bb`）

F-1〜F-6 を当てた `e4d72bb` について、PR 全体を独立したレビュー担当（サブエージェント）が再レビューした。F-1〜F-6 はすべて解消していた（判断は Approve）。新たな指摘は Low 1 件と Info 6 件で、ユーザ指示（再レビューで問題が見つかったら解消するまで修正・検証を繰り返す）に従い、次のとおり選別した。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR1 L-1 | R-3 の期待する結果「`pnpm` のコマンドが無い」は rebuild 後も満たされない | 対応する (b) | Node の feature（v2.1.0 の `src/node/install.sh`）は、yarn が無いと `corepack enable` を実行し、`pnpm`・`pnpx`・`yarn`・`yarnpkg` の shim を Node の bin に置く。`pnpmVersion: "none"` が止めるのは npm での pnpm の導入だけ。現行コンテナの `yarn` は corepack の shim で、`corepack enable --install-directory <一時>` が 4 つの shim を作ることを確かめた |
| RR1 I-1 | R-7 の「rebuild 前」の「argv に `--tui-mode` が無い」は不正確。確認方法が `--tui-mode fullscreen` を渡すので、argv に `--tui-mode` は必ず 1 つある | 対応する (b) | Plan の Task 1 Step 8 の期待値も「`--tui-mode` の数は各 1」。Issue #22 の Spec の 3.5 節も同じ書き方 |
| RR1 I-2 | rebuild の手順 4 が、利用者の設定を変える操作として R-8 と R-11 だけを挙げ、R-6 の `cleanup_pi_mcp.py` の再実行を挙げていない | 対応する (b) | Plan の Task 1 Step 8 は R-6 の再実行を「利用者の設定を変えるので実行しない」としている。再実行は pi 専用の状態ファイルの削除や `-builtin:mcp` の除去を行いうる |
| RR1 I-3 | Spec・Plan に最終版との食い違いが残る | 対応する (b) | Spec 8 章の `git diff --stat origin/main` と「4 ファイルと Spec・Plan」は、`origin/main` が進んだ後とレビュー修正の Spec の追加で成り立たない。Spec 4.6 節の R-9 の「短い名前だけが権限確認を省略する」は比較表の R-9 では確かめていない（`test-herdr-migration.bash` が検査する）。Plan の「PR #33 のレビュー修正」の「参照の数（22）は最終版でも同じ」は、Plan に埋め込んだ計画時の検査スクリプトが最終版で失敗することに触れておらず誤解を招く。Task 4 Step 4 の PR の本文の項目（3 ファイル、D-1〜D-14）も計画時のまま |
| RR1 I-4 | 比較表の節の単位の記録に粗い箇所がある | 対応する (b) | 移植元の `.devcontainer/README.md` の「pi のモデル定義とランチャー」「モデル定義の正」に当たる行が無く、Spec 4.1 節の「どの子も扱わなかった節は #22 の行にする」に反する（差分は setup スクリプトのパスと、移植先にだけある `pigou` の説明だけ）。比較表の「`.devcontainer/README.md` の Claude Code の節」は、移植元に該当する節が無い（#21 の Spec は「Claude Code の案内」）。Spec 4.2 節の「npm への一本化と既存環境の移行」は移植元の見出し「npm への一本化（#147）と既存環境の移行」と違う |
| RR1 I-5 | 「rebuild しない場合」が、古い `~/.zshrc` に残る `ccda`（`claude-alibaba`）の関数と `update()` の Grok Build の行の削除に触れていない | 判断保留 → 推奨案を採用 | #18 より前の `zshrc.txt` に `function claude-alibaba ccda` と `update_if_present grok grok update` がある。トークンを消せば `ccda` は `:?` で止まり、`update_if_present` は無いコマンドを飛ばすので実害は無いが、1 文で旧い定義が残らない |
| RR1 I-6 | push の後、PR の本文の検証の HEAD（`77aa743`）と関連文書が古くなる | 対応する (b) | PR の本文に、修正後の HEAD での検証とレビュー修正の Spec が無い |

### F-7 R-3 は pnpm の npm パッケージの有無で確かめる（RR1 L-1）

比較表の R-3 を、`command -v dsh grok`、`npm ls -g --depth=0 pnpm`、`readlink -f "$(command -v pnpm)"`、VS Code の「ポート」で確かめる形にする。期待する結果は、`dsh`・`grok` が無いこと、npm の大域パッケージに `pnpm` が無い（`(empty)`）こと、corepack の shim は残ってよい（`readlink -f` が `corepack/dist/pnpm.js` を指す）こと、3080 を転送しないこと。rebuild 前の列に、現行の `pnpm` が npm の大域パッケージ（`pnpm@12.4.1`）であることを書く。Issue #22 の Spec 4.6 節の R-3 にも shim が残ることを書く。

検証: 現行コンテナで `npm ls -g --depth=0 pnpm` が `pnpm@12.4.1`、存在しないパッケージでは `(empty)` と exit 1 になること、`readlink -f "$(command -v pnpm)"` が `lib/node_modules/pnpm/pnpm` を指すことを確かめる。

### F-8 R-7 の rebuild 前の書き方を直す（RR1 I-1）

比較表の R-7 の「rebuild 前」と Spec 3.5 節を、「ヘルパが付ける `--tui-mode regular` が無い（`--tui-mode` は利用者が渡した 1 つだけ）」にする。

### F-9 R-6 の再実行も利用者の了承を要る操作にする（RR1 I-2）

比較表の手順 4 を「R-6 の `cleanup_pi_mcp.py` の再実行、R-8、R-11 は…利用者が行うか、利用者の了承を得てから行う」にする。

### F-10 Spec・Plan の食い違いを直す（RR1 I-3）

- Spec 8 章を `git diff --stat origin/main...HEAD` にし、変更の範囲にこの Spec を含める
- Spec 4.6 節の R-9 を、比較表の R-9 が確かめる内容（3 つの alias と 6 つの関数）にし、短い名前だけが権限確認を省略することは R-12 の `.devcontainer/test-herdr-migration.bash` が fake CLI の argv で検査すると書く
- Plan の「PR #33 のレビュー修正」の節を書き直し、計画時の節名の参照の検査が最終版で失敗すること（実際に使った版では 22 件すべてが通ること）、Task 4 Step 3 の比べ方と最終の 7 ファイル、Task 4 Step 4 の PR の本文の項目を書く

### F-11 比較表の節の単位の行を直す（RR1 I-4）

- 比較表の「Dev Container・シェル・文書の共有ファイル」に、移植元の `.devcontainer/README.md` の「pi のモデル定義とランチャー」「モデル定義の正」の行（既存維持、#22）を足す。Spec 4.2 節にも同じ行を足す
- 比較表の Claude Code の README の行の移植元のパスを「なし」にし、理由に移植元にランチャーの節が無いことと #21 の Spec の行の名前を書く。判断（適応）は変えない
- Spec 4.2 節の見出しを移植元の「npm への一本化（#147）と既存環境の移行」にする
- 比較表の #19 の README の行（pi の拡張・MCP・pi-distill の節）の移植元のパスに、当たる移植元の節名「pi-distill の撤去（#508）」「setup スクリプトを使う場面」を補う。補うのはパスの列だけで、判断と理由は変えない（比較表の「読み方」と Spec 4.1 節の規則）

検証: Plan の網羅の検査で `rows: 93`（F-29 の後は 94、F-33 の後は 96）・`missing: 0`。移植元の `.devcontainer/README.md` の `##`・`###` の見出しが、比較表のいずれかの行に当たること。

### F-12 古い `~/.zshrc` の定義を消す（RR1 I-5、推奨案を採用）

`.devcontainer/README.md` の「rebuild しない場合」の Claude Code のランチャーの項に、古い `~/.zshrc` に残る `ccda`（`claude-alibaba`）の関数と `update()` の Grok Build の行も削除すると書く。`test-readme.bash` が `.devcontainer/` に禁じる語（`function claude-alibaba`、`ccda ()`、Grok の更新コマンドなど）は使わない。

### F-13 PR の本文を更新する（RR1 I-6）

push の後、PR の本文の検証の HEAD と結果を修正後の HEAD に更新し、レビュー修正の Spec を関連文書に足す。比較表の行数を最終版の行数（96 行）にする。

## 再レビュー（2 回目、`cc77914`）

F-7〜F-12 を当てた `cc77914` について、PR 全体を新しい独立したレビュー担当が再レビューした。F-1〜F-12 はすべて解消していた。新たな指摘は Medium 1 件と Info 7 件で、判断は Request changes（Medium の 1 件）。次のとおり選別した。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR2 M-1 | 確認表のセルのコマンドを Markdown のソースから写すと、`\|` がそのままシェルに渡る。R-4 では `zsh -ic 'env' '\|' grep …` になり、環境変数の値がすべて表示される | 対応する (a)(b) | 一時 HOME の `env` にダミー値を置き、セルの文字列をそのまま実行すると、ダミーの `DEEPINFRA_TOKEN`・`MAAS_ANTHROPIC_TOKEN` の値が出た（exit 0）。エージェントやエディタが読むのはソースで、比較表の「確認方法のコマンドも値を表示しない」と食い違う。R-2・R-5 も同じ書き方（値は出ないがエラーになる） |
| RR2 I-1 | Spec が変更するファイルを「いずれも #22 の『編集してよいファイル』」とし、「この PR は文書だけを変える」と書くが、テストの例外の 1 行がある | 対応する (b) | Issue #22 の「編集してよいファイル」に `tests/skills/test_legacy_references.py` は無い（D-15 で足した）。比較表の手順 1、Spec の冒頭の「経路」・4.6 節・D-10 に「文書だけ」がある |
| RR2 I-2 | Spec の冒頭のレビュー修正の参照が「F-1〜F-6」のまま | 対応する (b) | F-7・F-8・F-10・F-11 も Spec を変えた |
| RR2 I-3 | 比較表と Spec 4.2 節の「public/ checkout の検査と復旧」が、移植元の見出し（`public/` にバッククォートがある）と違う | 対応する (b)、表記の規則で解消 | 網羅の検査は「移植元のパス」の列のバッククォートの中をパスとして読むので、`public/` に付けると移植元に無いパスとして失敗する。この列で見出しを引くときはバッククォートを省く規則を比較表の「読み方」に書き、同じ列の「Codex で `CLAUDE.md` を…」からもバッククォートを省いて揃えた |
| RR2 I-4 | 比較表の「指示文・MCP の読み込み」が、pi のスキルの読み込みに project trust が要ることを書いていない | 対応する (b) | 導入済みの Pi 1.0.2 の `docs/security.md`（Resources protected by project trust）に、cwd と祖先のプロジェクトの `.agents/skills` が trust の対象とある。`AGENTS.md` などの指示文は trust に関係なく読む。同じ原因で、ルートの `README.md` の pi の項目、`.devcontainer/README.md` の「既存環境の更新」の手順 4、Spec 4.3・4.5 節も、trust の後に読まれるものにスキルを挙げていない |
| RR2 I-5 | rebuild しない場合、`MAAS_ANTHROPIC_TOKEN` が使用中のシェルに残る | 対応する (b) | 「rebuild しない場合」が参照する「組み込み MCP と廃止した拡張」の `unset` は `PI_DISTILL_*` と `PI_EXTENSIONS_LOCALE` だけで、`env` から消しても使用中のシェルと子プロセスには値が残る |
| RR2 I-6 | 「API トークン」の `CONTEXT7_API_KEY` が Codex の用途だけを書いている | 対応する (b) | `.agents/skills/find-docs/SKILL.md` の Authentication が、この変数を `env` に置くよう README を案内している（無くても動き、あるとレート制限が上がる）。Spec 4.3 節は変数ごとに使うものと無いときの挙動を書く方針 |
| RR2 I-7 | 比較表の「移植元の `main` は 2026-10-05 時点で `e1f042e`」は、同じ日の後の時刻に移植元が進んでいる | 対応する (b) | 移植元の `main` は 03:52 UTC に `90428f7` へ進んだ（変わったのは `CLAUDE.md` だけ）。Spec の冒頭の「基準」は「02:55 UTC 時点」と時刻まで書いている |

再レビューの補足（指摘ではない）: 利用者の現在の `~/.pi/agent/models.json` の `opencode-go` に `union-alpha` の定義が無いので、rebuild 後の R-7 で `pigou` は案内を出して終了し、「前提が未設定のため未確認」になる見込み。移植の前からの状態で、表の書き方どおりの扱いである。

### F-14 確認のコマンドを表の外のコードブロックに置く（RR2 M-1）

- 比較表の確認表の「確認方法」の列はコマンドを書かず、確かめる内容と「R-n のコマンド」の参照にする
- 表の下に「確認のコマンド」の節を置き、読み取り専用のコマンド（R-2〜R-7 の一覧・R-9・R-10・R-12）と、利用者の設定を変えるコマンド（R-6 の cleanup の再実行、R-8）を別のコードブロックに分ける。後者には「利用者が行うか、利用者の了承を得てから実行する」と書く。R-8 は `diff` で tier を比べ、一致すれば何も出ない形にする
- 節の冒頭に、表のセルにコマンドを書かない理由（セルの `\|` を写すとシェルが別のコマンドとして実行し、R-4 では値がすべて表示される）を書く
- 手順 4 を「下の表の各項目を『確認のコマンド』で確かめ」にする。Spec 4.6 節にも、コマンドを表の外に置き、2 つのブロックに分けることを書く
- Plan の Task 1 Step 4 の埋め込み文書は最終版に揃える（F-5）

検証: コードブロックの R-4 の行をそのまま一時 HOME とダミー値で実行し、変数名だけが出て値が出ないこと。読み取り専用のブロックの R-2・R-3・R-5・R-6 の一覧・R-9 を現行コンテナで実行し、エラーにならず「rebuild 前」の列と同じ値が出ること（R-9 は一時 HOME）。R-8 の `diff` は、リポジトリの tier の設定どうしを比べて何も出ないことを確かめる（利用者の設定は変えない）。

### F-15 変更範囲の書き方を直す（RR2 I-1）

Spec 2 章の「変更するファイル」に、`tests/skills/test_legacy_references.py` を除いて #22 の「編集してよいファイル」であることを書く。比較表の手順 1、Spec の冒頭の「経路」・4.6 節・D-10 の「文書だけ」を「文書とテストの例外の 1 行だけ（導入スクリプトと設定ファイルを変えない）」にする。

### F-16 Spec の冒頭のレビュー修正の参照から範囲を外す（RR2 I-2）

「（PR #33 の F-1〜F-6）」を「（PR #33。この Spec を変えた修正もそこに記録した）」にし、修正が増えても食い違わないようにする。Plan の「PR #33 のレビュー修正」の節も、修正の ID の範囲を書かずにこの Spec を参照する。

### F-17 移植元の見出しの引き方を揃える（RR2 I-3）

比較表の「読み方」に、移植元のパスの列で見出しを「」で引くときはバッククォートを省く規則と理由を書く。同じ列の「Codex で `CLAUDE.md` を指示ファイルとして読む」からバッククォートを省き、Spec 4.2 節も同じにする。

検証: 網羅の検査が `missing: 0` のままであること（`CLAUDE.md` は `CLAUDE.md` の 2 行で当たる）。

### F-18 pi のスキルも trust の後に読まれると書く（RR2 I-4）

比較表の「指示文・MCP の読み込み」の pi の行に、スキルは project trust が必要で、`AGENTS.md` は trust に関係なく読むことを書く。ルートの `README.md` の pi の項目、`.devcontainer/README.md` の「既存環境の更新」の手順 4、Spec 4.3・4.5 節に、trust の後に読まれるものとしてプロジェクトのスキル（`.agents/skills`）を足す。ルートの `README.md` の pi の項目の書き出し（Plan の受け入れ検査が見る部分）は変えない。

### F-19 rebuild しない場合に `MAAS_ANTHROPIC_TOKEN` も外す（RR2 I-5）

「rebuild しない場合」の廃止した環境変数の項に、2 で `env` から消した `MAAS_ANTHROPIC_TOKEN` も使用中のシェルでは `unset MAAS_ANTHROPIC_TOKEN` で外すと書く。`test-readme.bash` が禁じる `-u MAAS_ANTHROPIC_TOKEN` の形は使わない。

### F-20 `CONTEXT7_API_KEY` の `find-docs` での用途を書く（RR2 I-6）

「API トークン」の `CONTEXT7_API_KEY` の項と Spec 4.3 節に、共有の `find-docs` スキルが使う Context7 の CLI もこの変数を使い、無くても動くがレート制限が低くなることを書く。

### F-21 移植元の `main` の時点に時刻を書く（RR2 I-7）

比較表の「基準」を「2026-10-05 02:55 UTC 時点で `e1f042e`」にする（Spec の冒頭の「基準」と同じ）。

## 再レビュー（3 回目、`ac127ca`）

F-14〜F-21 を当てた `ac127ca` について、PR 全体を新しい独立したレビュー担当が再レビューした。F-1〜F-21 はすべて解消し、修正による新しい不整合は無かった（判断は Approve）。指摘は Info 3 件で、次のとおり選別した。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR3 I-1 | 「確認のコマンド」の R-9 は `zsh -ic` で `~/.zshrc` を読むので、herdr のペインの外の端末から実行すると、末尾の `herdrstart` が herdr を前面で起動する | 対応する (a) | `.devcontainer/zshrc.txt` の `herdrstart` は、`HERDR_SOCKET_PATH`・`HERDR_ENV` が無く、標準入力と標準出力が端末のときに herdr を起動する。一時 HOME と偽の `herdr` で、端末を与えて R-9 の行を実行すると herdr が先に起動した。R-4 は出力をパイプに流すので起動しない。Plan の Task 1 Step 8 にも同じ R-9 のコマンドがある |
| RR3 I-2 | Issue #22 の Spec の冒頭が、存在しない「5.1 節」を参照している | 対応する (b) | 5 章は判断事項の表だけで、移植元の `main` の差分を取り込まない判断は D-1 にある。初版から残っていた |
| RR3 I-3 | この Spec の「全体の検証」が、1 回目の時点の記述（F-1〜F-6、再レビュー 1 回目）のまま | 対応する (b) | F-7 以降と 2 回目以降の再レビューが反映されていない |

### F-22 R-9 のコマンドで herdr を起動しない（RR3 I-1）

比較表の「確認のコマンド」の R-9 の行と、Plan の Task 1 Step 8 の R-9 の行に `</dev/null` を足す。`herdrstart` は標準入力が端末でなければ何もしないので、出力（alias と関数の判定）は変わらない。比較表には理由をコメントで書く。Plan の「PR #33 のレビュー修正」の節にも記録する。

検証: 一時 HOME に `zshrc.txt` を置き、偽の `herdr` を PATH に入れ、`script` で端末を与えて R-9 の行を実行する。`</dev/null` 無しでは偽の `herdr` が起動し、有りでは起動せずに alias と関数の判定だけが出ること。

### F-23 Issue #22 の Spec の節の参照を直す（RR3 I-2）

「差分は 5.1 節のとおり取り込まない」を「差分は 5 章の D-1 のとおり取り込まない」にする。

### F-24 この Spec の「全体の検証」を直す（RR3 I-3）

「F-1〜F-6 の個別の検証」を「F-1 以降の各修正の個別の検証」にし、再レビューの結果の参照を各回の節にする。

## 再レビュー（4 回目、`b984a64`）

F-22〜F-24 を当てた `b984a64` について、PR 全体を新しい独立したレビュー担当が再レビューした。F-1〜F-24 はすべて解消し、修正による新しい食い違いは無かった（判断は Approve）。指摘は Low 1 件と Info 4 件で、次のとおり選別した。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR4 L-1 | trust の後に読まれるものの列挙から `.pi/APPEND_SYSTEM.md` が抜けている（ルートの `README.md` の pi の項目、`.devcontainer/README.md` の「既存環境の更新」の手順 4、Spec 4.3 節） | 対応する (b) | 導入済みの Pi 1.0.2 の `docs/security.md` の Resources protected by project trust に `.pi/SYSTEM.md` と `.pi/APPEND_SYSTEM.md` がある。`AGENTS.md` が pi 固有の注意の置き場として案内するファイルで、trust が無いと読まれないことに利用者が気づけない。RR2 I-4（スキルの抜け）と同じ原因の残り。比較表の「指示文・MCP の読み込み」は正しい |
| RR4 I-1 | 比較表の `test-herdr-agent-task.bash` の行の理由が「移植先が新しい」だけで、移植元にだけあるコメントの言い換えに触れていない | 対応する (b) | 移植元 `1f2aadb` との差分は here-string の変更と、45 行目のコメント（移植元「CLI の仕様」、移植先「CLI の契約」）だけ。Spec 4.2 節も同じ理由 |
| RR4 I-2 | Plan の Task 1 Step 8 のコマンドが比較表の「確認のコマンド」と違う（R-3・R-5・R-7・R-10）ことが、Plan の末尾の節に書かれていない | 対応する (b) | Step 8 の R-3 は `command -v pnpm` で判定する（RR1 L-1 で不十分とした方法）。R-5・R-10 は出力を絞り、R-7 は 3 本だけ。末尾の節は R-9 の `</dev/null` しか記録していない |
| RR4 I-3 | この Spec が Issue #22 の Spec の冒頭の「基準」「経路」を「1 行目」と書いている | 対応する (b) | Issue #22 の Spec の 1 行目は表題で、指している内容は 5 行目（基準）と 6 行目（経路） |
| RR4 I-4 | 比較表に、移植元の `install_beforehand.bash` の汎用の手順（`~` 配下の書き込み可能なディレクトリ、apt の設定、基本パッケージ、ロケール、Herdr の補助スクリプト、作業領域の掃除、`~/.zshrc` への連結）を名前で扱う行が無い | 対応する (b) | Spec 4.1 節の「どの子も扱わなかった節は #22 の行にする」に反する（ファイル単位の網羅は通る）。移植元と移植先の各手順の本体を比べた違いは、ディレクトリの一覧（#18 の撤去と移植先の秘密情報の置き場）、移植先だけの `blender`、移植元の重複した `apt update`、移植元だけが置く herdr-pr-review と cleanup の symlink、コメントの Issue 番号だけ |

### F-25 trust の後に読まれるものに `.pi/APPEND_SYSTEM.md` を足す（RR4 L-1）

ルートの `README.md` の pi の項目、`.devcontainer/README.md` の「既存環境の更新」の手順 4、Spec 4.3 節に、`.pi/APPEND_SYSTEM.md`（pi 固有の指示）を足す。ルートの `README.md` の pi の項目の書き出しは変えない。

### F-26 Herdr のテストの行の理由を補う（RR4 I-1）

比較表と Spec 4.2 節の `test-herdr-agent-task.bash`・`test-herdr-status.bash` の行の理由に、移植元のコメントの言い換えは取り込まないこと（テストは #22 の編集範囲外）を足す。

### F-27 Plan の Step 8 のコマンドの扱いを書く（RR4 I-2）

Plan の「PR #33 のレビュー修正」の「計画の時点の記述のまま残す」に、Task 1 の Step 8 のコマンドが比較表の「確認のコマンド」と違う点（R-3・R-5・R-7・R-10）と、rebuild 後の確認には比較表のコマンドを使うことを足す。

### F-28 Issue #22 の Spec の冒頭の参照を直す（RR4 I-3）

この Spec の「Spec の 1 行目」「Spec 1 行目」を、指している「冒頭の『基準』」「冒頭の『経路』」にする。

### F-29 `install_beforehand.bash` の汎用の手順の行を足す（RR4 I-4）

比較表の「Dev Container・シェル・文書の共有ファイル」と Spec 4.2 節に、移植元の `install_beforehand.bash` の汎用の手順の行（既存維持、#22）を足し、理由に上の違いを書く。

検証: Plan の網羅の検査で `rows: 94`（F-33 の後は 96）・`missing: 0`。移植元と移植先の `install_beforehand.bash` の `step` の名前を突き合わせ、すべての手順がいずれかの行に名前で当たること。

## 再レビュー（5 回目、`2e90573`）

F-25〜F-29 を当てた `2e90573` について、PR 全体を新しい独立したレビュー担当が再レビューした。F-1〜F-29 はすべて解消していた（判断は Approve）。指摘は Info 6 件で、うち 4 件は前の回で直した指摘と同じ種類の残りだった。そのため指摘の箇所だけでなく、種類ごとにリポジトリ全体を洗い出してから直した（洗い出しの結果は各 F-n）。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR5 I-1 | 読み取り専用のブロックの R-5 の `pi list` は、プロジェクトの trust をまだ決めていない環境では確認画面を出す | 対応する (a) | `.agents/skills` を持つ一時ディレクトリで端末を与えると、`pi list` は「Trust project folder?」で止まり（`timeout` で exit 124）、`pi list --no-approve` は確認を出さずに一覧を出して exit 0 で終わった。`~/.pi/agent/trust.json` は変わらない。`pi list --help` に `--no-approve`（このコマンドではプロジェクトの trust の対象のファイルを無視する）がある |
| RR5 I-2 | Plan の「PR #33 のレビュー修正」が、Task 3 のパッチと最終版の違いに F-25 の `.pi/APPEND_SYSTEM.md` を含めていない。Step 8 と確認のコマンドの違いの列挙も足りない | 対応する (b) | Task 3 のパッチを当てた結果と最終版のルートの `README.md` を比べた。Step 8 は R-4 に `sort`、R-9 に `2>&1` があり、R-6 の一覧が無い |
| RR5 I-3 | `zshrc.txt` の `cc_launcher_unsets` のコメントで、移植元だけが「正本」を「基準」に言い換えたことが記録されていない | 対応する (b) | 同じ種類の差分を、移植元と移植先の両方にある追跡ファイル（スキル・レビュー系ツールを除く）で洗い出した。移植先に残る「正本」「契約」の行のうち、移植元が言い換えたのは `zshrc.txt`（「基準」）、`test-herdr-migration.bash`（「基準」）、`test-pi-superagents.bash`（「元ファイル」）、`test-herdr-agent-task.bash`（「仕様」。RR4 I-1）の 4 ファイルだった。`CLAUDE.md` とルートの `README.md` は移植元と構成が違い、言い換えではない |
| RR5 I-4 | `zshrc.txt` の汎用の設定と、移植元の `.devcontainer/README.md` の冒頭の説明に、名前で当たる行が無い | 対応する (b) | Spec 4.1 節の規則（どの子も扱わなかった節は #22 の行にする）。`zshrc.txt` を比べた違いは、関数の `require_command` の呼び出し（比較表の移植先にだけある補助の行）と bun の補完のパスだけ。README の冒頭は MaatLog の親子リポジトリと `public/` submodule（Playwright の導入）の説明 |
| RR5 I-5 | 「API トークン」の `CONTEXT7_API_KEY` に、Claude Code と Cursor の Context7 の MCP サーバーが挙がっていない | 対応する (b) | `.mcp.json` と `.cursor/mcp.json` が起動する `@upstash/context7-mcp` は、受け取った環境の `CONTEXT7_API_KEY` を読む。各変数の使い先をリポジトリ全体で洗い出し、ほかの変数の記述は使い先と一致していた。Claude Code と Cursor が stdio のサーバーへ環境変数を渡すかは確かめていないので、「受け取った環境にあれば使う」と書く |
| RR5 I-6 | R-11 で確かめる範囲が、Spec（ルートと各ワールド）と比較表（ルートと `slum02/`）で違う | 対応する (b) | 4 つのワールドは同じ `.pi -> ../.pi` を持ち、`check-layout.sh` が検査する |

### F-30 R-5 は `pi list --no-approve` にする（RR5 I-1）

比較表の確認表の R-5 と「確認のコマンド」の R-5 を `pi list --no-approve` にし、プロジェクトの trust の確認を出さないことをコメントに書く。

### F-31 Plan の末尾の説明を直す（RR5 I-2）

Task 3 のパッチの説明に `.pi/APPEND_SYSTEM.md` を足す。Step 8 と確認のコマンドの違いを、判定の方法・出力の形・対象・`--no-approve` の有無でまとめて書く（R-9 の `</dev/null` は F-22 で両方にあるので違いではない。F-36 で直した）。

### F-32 移植元だけのコメントの言い換えを 1 行で記録する（RR5 I-3）

比較表と Spec 4.2 節に、上の 4 ファイルのコメントの言い換えの行（除外、#22）を足す。理由は、#22 の編集範囲外で動作に関わらないことと、移植先の `AGENTS.md` にも同じ規則があるので別の作業で言い換えること。F-26 で Herdr のテストの行に書いた文は、この行を参照する文にする（子の行の理由は変えない規則なので、#20・#21 の行には書かない）。

### F-33 `zshrc.txt` の汎用の設定と README の冒頭の行（RR5 I-4）

比較表と Spec 4.2 節に、`zshrc.txt` のほかの行で扱わない設定の行（既存維持、#22）を足す。`public/` の行の移植元のパスに、README の冒頭の説明を足す。

### F-34 `CONTEXT7_API_KEY` の使い先を足す（RR5 I-5）

「API トークン」と Spec 4.3 節に、Claude Code（`.mcp.json`）・Cursor（`.cursor/mcp.json`）の Context7 の MCP サーバーも、受け取った環境にこの変数があれば使うことを書く。

### F-35 R-11 の範囲を揃える（RR5 I-6）

比較表の R-11 の確認方法と Spec 4.6 節の R-11 を、「ルートと、ワールドの代表として `slum02/`（4 つのワールドは同じ `.pi -> ../.pi` を持ち、`check-layout.sh` が検査する）」にする。

検証（F-30〜F-35）: Plan の網羅の検査で `rows: 96`・`missing: 0`。Plan の埋め込み文書・パッチが最終版と一致。読み取り専用のブロックを写して実行し、R-5 が確認を出さないこと。

## 再レビュー（6 回目、`f92e92d`）

F-30〜F-35 を当てた `f92e92d` について、PR 全体を新しい独立したレビュー担当が再レビューした。F-1〜F-35 はすべて解消していた（判断は Approve）。指摘は Info 1 件で、F-31 で入れた記述の誤りだった。

| ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| RR6 I-1 | Plan の「PR #33 のレビュー修正」が、Step 8 と確認のコマンドの違いに「R-9 の `</dev/null` の有無」を挙げているが、F-22 で両方に `</dev/null` を足したので違いではない。直後の項目（Step 8 の R-9 に後から `</dev/null` を足した）とも矛盾する | 対応する (b) | Plan の Step 8 の R-9 と比較表の「確認のコマンド」の R-9 は、どちらも `</dev/null` を持つ。違いは Step 8 の `2>&1` だけで、これは「出力の形」に含まれる。R-7 も Step 8 は `--tui-mode` の個数だけを出すので「出力の形」の違いにあたる |

### F-36 Plan の Step 8 の違いの記述を直す（RR6 I-1）

Plan の該当の項目から「R-9 の `</dev/null` の有無」を外し、「出力の形」に R-7 を足す。F-31 の方針の文も同じく直す。

## 全体の検証

worktree のルートで実行する。

- `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、`uv run pytest -q tests/skills .agents/skills`（基準は `77aa743` で PASS、27/27、516 passed・1 skipped）
- F-1 以降の各修正の個別の検証（各 F-n の「検証」）
- Plan の一時の検査スクリプト（網羅、README の受け入れ検査、節名の参照）を最終版に対して実行する
- PR 全体の独立した再レビュー。指摘があれば直して再レビューを繰り返す（各回の結果は上の「再レビュー（n 回目）」）

## 範囲外

- ランチャー・`pi-superagents-exec.zsh`・テストの変更（dry-run の前提の挙動、引き継ぎの検査の拡張）
- PR の「マージの条件」（利用者の rebuild と「rebuild 後」の列の記録）。このレビュー修正では変えない
