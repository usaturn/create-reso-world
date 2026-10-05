# PR #35 issue-22-rebuild-record のレビュー指摘の選別

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/35
- リポジトリ: `usaturn/create-reso-world`
- 対象ブランチ: `docs/issue-22-rebuild-record`
- 指摘を検証した HEAD: `ea1adf48cef2c3bf3d87760537fe2672f674679a`
- 入力: `reviews/#35-docs-issue-22-rebuild-record/` 配下の全 4 ファイル
- 作成日: 2026-10-05
- 経路: **bounded**（既存の記録とテストに対するレビュー指摘の選別。実装の対象は無い）
- 状態: **completed**（2026-10-05）。同日のユーザ依頼が「致命的な指摘のみ修正する」ことと、修正が不要な場合の扱い（必要な確認・検証を完了し、最終ステータスコメントを投稿してマージし、関連 Issue を更新する）を事前に指示している。選別の結果、修正対象は無く、この文書はその範囲の記録である

## 結論

修正は不要である。4 つのレビューの active な指摘は Info 1 件だけで、致命的な指摘は無い。未検証候補 1 件は現行の環境で再現し、記録どおりであることを確かめた。PR の HEAD に現在の `main`（`7139054`）をマージした状態でも、テスト一式が通る。

## レビュー入力

| ファイル | 対象 HEAD | 指摘 |
| --- | --- | --- |
| `SWE-2-Max.md` | `ea1adf48cef2` | Info 1（I-1）、未検証候補 1 |
| `claude-opus-5-5.md` | `ea1adf48cef2` | 0 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `ea1adf48cef2` | 0 |
| `openai-codex-gpt-6.1-sol.md` | `ea1adf48cef2` | 0 |

対象 HEAD はすべて、選別時点の PR の HEAD（`gh pr view 35 --json headRefOid`）と一致する。4 つとも Approve である。

## 分類結果

| 区分 | 件数 |
| --- | --- |
| 解消済み | 1 |
| 対応する | 0 |
| 判断保留 | 0 |
| 対応しない | 1 |

### 全指摘一覧

| 元レビュー / ID | 指摘 | 区分 | 根拠 |
| --- | --- | --- | --- |
| `SWE-2-Max.md` / I-1（Info） | 節の一覧の検査を削除した後も、`tests/scripts/test-instructions.bash` の先頭コメント（2 行目）と PASS の表示（72 行目）が「仕様 5.2・5.3 のとおり」のままで、検査の範囲より強い主張になっている | **対応しない** | 2 行目と PASS の表示は削除前（`e21121e`）と同じ文言で、削除前から仕様 5.2・5.3 の全項目を検査してはいなかった（例: 5.2 の「曖昧なら質問」、5.3 のプロジェクトの `CLAUDE.md`）。検査の出典を示す見出しであり、この PR で誤った記述が生まれたのではない。(a)〜(d) のいずれにも当たらない Info 級の表現の改善で、固定値の検査の見直しは #36 で扱う |
| `SWE-2-Max.md` / 未検証候補 | R-11 の記録「`google-dev-knowledge: connected, 3 tools (codemode, project)`」は、`3 tools` に対して括弧内の名前が 2 つで、出力の写しか確かめられない | **解消済み** | 括弧内はツール名ではなく公開の方式（`codemode`）と設定の範囲（`project`）である（pi 1.0.3 の `dist/extensions/mcp/cli.js` の出力の形式）。`/workspaces/reso-world` と `slum02/` で `pi mcp list` を実行し、どちらも同じ行と `tools: search_documents, answer_query, get_documents` を出した |

## 検証の根拠

ソースとテストは、`ea1adf4` のコミット済みの内容と、それを detached で展開した一時 worktree で確かめた。rebuild 後の環境の値（mount、拡張、退避、`pi mcp list` など）は、現在のコンテナで読み取り専用のコマンドを使って照合した。メインの checkout や他の worktree の未コミットの変更は根拠にしていない。

### 変更したテスト

- 削除した検査（`e21121e` の `tests/scripts/test-instructions.bash:15-29`）は、AGENTS.md の `## ` の見出しを仕様 5.2 の 11 節と完全一致で比べていた。`77426d1` までは一致し、PR #34 のマージ（`cb35c96`）で `## GitHub Actions` が加わってから `main` で失敗していた
- 削除後も、仕様 5.2 の各節の内容は文言の有無で検査が残る（`test-instructions.bash:16-49`）。無くなったのは「リポジトリ概要」「日本語表現」「環境」の 3 節の有無と、節の順序だけである
- `## リポジトリ境界` から `## ResoLoop の版管理` までの切り出し（35 行）は、間に `## GitHub Actions` が入っても `| それ以外 |` の行を 1 行だけ取り出す。見出しの追加・移動・削除を 6 通り試し、すべて PASS した。失敗するのは `## リポジトリ境界` の改名・削除のように、検査の目的どおりの場合だけである
- `bash -n` と `bash tests/scripts/test-instructions.bash` は PR の HEAD で成功した

### 記録（`docs/maatlog-poc-porting.md`）

- R-1〜R-12 のうち、リポジトリのコード・設定で裏付けられる記述をすべて照合し、矛盾は無かった（`STEP_TOTAL=25` と最後の手順、mount 12 件、`forwardPorts: [8000]`、撤去する 5 つの拡張、退避の条件と名前、`pi-superagents-exec.zsh` の `--tui-mode regular`、`pigou` の `union-alpha`、setup の `cmp` による退避、alias 3 つと関数 6 つ、プラグイン 5 つ、`.pi/mcp.json`、R-12 の失敗の原因）
- 「実認証のスモークテスト（別枠）」の項目を Claude Code の MCP に絞った変更は、R-11 と合っている
- PR 本文の「#17 を閉じる根拠」は、#17 の受け入れ条件で未チェックだった 4 項目に対応し、R-5〜R-8・R-11・R-12 と既存のテストで裏付けられる

### 現在の `main` とのマージ

`origin/main`（`7139054`。PR #37 が AGENTS.md の「## 基本方針」に 1 行を足した）に PR の HEAD をマージした一時 worktree で、次を実行した。マージは衝突なし。

| コマンド | 結果 |
| --- | --- |
| `bash tests/scripts/test-instructions.bash` | PASS（終了コード 0） |
| `bash scripts/check-layout.sh` | PASS（終了コード 0） |
| `bash .devcontainer/run-tests.bash` | 27/27（終了コード 0） |
| `uv run pytest -q -rs tests/skills .agents/skills` | 516 passed・1 skipped（終了コード 0） |

実行後の `git status --porcelain` は空だった。現在の `main` 単独では `test-instructions.bash` が失敗するので、このマージで直る。

## PR 差分外の同じ原因

別の PR が文書の見出しを変えると、固定値の一覧と比べる検査が壊れる、という同じ原因の箇所をリポジトリ全体で探した。

- `tests/scripts/test-docs.bash:13-22`: README.md の `## ` の見出しを順序を含めて完全一致で比べる。現在の `main` とのマージ結果では通る
- `tests/scripts/test-instructions.bash:67-70`: `.pi/APPEND_SYSTEM.md` のペルソナ節の sha256。エージェントによる書き換えを防ぐ意図した検査で、現在は通る

どちらも現在は失敗せず、#36 の候補に挙がっている。致命的ではないので、この PR では変えない。

## 指摘以外の気付き

- PR 本文と #22 の追記（2026-10-05 10:00 UTC）は、`main` の失敗を「#34 を含まない `01affb7` を基点にした PR #33 と、#34 の両方をマージした `e21121e` で初めて失敗した」と説明している。実際には、PR #34 のマージ（`cb35c96`）の時点で `main` は失敗していた（PR #33 は 2 つのファイルを変えていない）。リポジトリに入る記録（R-12）は「PR #34 が節を足したが、検査を更新していなかった」と正しく書いているので、この PR の変更は直さない。正しい経緯は PR のステータスコメントと Issue の更新に書く

## 修正方針と検証方法

「対応する」は 0 件であり、実装の対象と追加のテストは無い。実装計画の文書は作らない。

この文書を PR #35 の head ブランチへコミットして push した後、新しい HEAD を現在の `main` とマージした状態で、上の 4 つのコマンドを再実行する。

## 次の段階

ユーザの事前の指示どおり、次を行う。

1. この文書を `docs/issue-22-rebuild-record` にコミットし、PR #35 へ push する
2. PR #35 に選別結果のステータスコメントを投稿する
3. PR #35 をマージする（#17 が閉じる）
4. 関連 Issue（#17・#22・#36）に、マージの結果と上の気付き・I-1 の扱いを書く
