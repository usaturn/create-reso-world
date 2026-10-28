# Issue #290 ctx7 を常に npm の最新版で導入する Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**状態:** draft（`/issue-to-pr #290 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge` による実行許可。内容の承認ではない）

**Goal:** `.devcontainer/install_ctx7.bash` が `ctx7@latest` を導入し、PATH 上の `ctx7` の実体が npm のグローバルの `ctx7/` の下にあることを確かめる形にし、文書を合わせる。

**Architecture:** 版の変数と版の一致の検査を消し、`npm root -g` と `command -v ctx7` を `readlink -f` で実体にそろえて前方一致で比べる。判定を通った後にだけ `ctx7 --version` を実行し、その出力をログに出す。テストは偽の npm・偽の `ctx7` で、正しく通る例と PATH の前のほうの別の `ctx7` の拒否を 1 件ずつ確かめる。

**Tech Stack:** bash（Dev Container の postCreate）、npm、Markdown

**Spec:** `docs/superpowers/specs/2026-10-28-create-reso-world-issue290-ctx7-latest-design.md`

## Global Constraints

- 導入は `npm install -g ctx7@latest`。`ctx7 setup`・`ctx7 upgrade` は実行しない。`ctx7` は `--version` 以外で呼ばない
- 失敗はすべて `[install_ctx7] ERROR: <理由>` を stderr に出して終了コード 1。成功のメッセージ `[install_ctx7] Context7 CLI <版> installed at <PATH 上のパス>.` は、すべての確認を通った後にだけ出す
- PATH の判定は版ではなく実体の場所で行い、パッケージの中のファイル名を仮定しない
- `postCreateCommand` と `install_beforehand.bash` の呼び出しの位置は変えない
- 対象外: 他の固定版ツール、MCP・Pi 拡張・`npx`、起動時・定期の更新、Node.js の版、zsh の `update`
- テストは AGENTS.md の「テストの採用基準」に従う。F のテストを足さない

## Review Focus

1. npm のグローバルの位置が symlink の下にある（nvm の `current` など）とき、正しい `ctx7` を拒否しないこと（両側を `readlink -f`）。Task 2 の一時的な実行で確かめる
2. `<root>/ctx7-other/` のような、名前が `ctx7` で始まる別のディレクトリの実行ファイルを受け入れないこと（`ctx7/` の末尾の `/` まで比べる）。Task 2 の一時的な実行で確かめる
3. 新しい版が動かず `ctx7 --version` が失敗・空の出力のとき、成功と報告しないこと。Task 2 の一時的な実行で確かめる
4. `npm install -g` の失敗と、導入後に PATH に `ctx7` が無いときに止まること。Task 2 の一時的な実行で確かめる
5. PATH の前のほうの別の `ctx7` を実行しないこと（判定を `--version` の前に置く）。Task 1 の実装の順で守り、Task 2 の一時的な実行で、拒否のときに別の `ctx7` が呼ばれないことを確かめる

1〜5 はどれも、壊れると非 0 の終了・postCreate の失敗として現れるか、Task 1 のテストと同じ守りの重なり（D）なので、コミットするテストにしない（Spec の「テストの要否」）。

## 受け入れ基準

（Spec の「受け入れ基準」と同じ）

- 動作環境: Ubuntu 26.04 LTS の Dev Container（Node.js v24.22.1、npm のグローバルは nvm の `/usr/local/share/nvm/versions/node/v24.22.1`）。テストは同じコンテナの bash で、偽の npm と偽の `ctx7` を使い、ネットワークを使わない
- 実入力: 着手時のコンテナの `ctx7` 0.8.0（実体 `$(npm root -g)/ctx7/dist/index.js`、PATH 上は `$(npm prefix -g)/bin/ctx7` の symlink）に対する `bash .devcontainer/install_ctx7.bash`。拒否の入力は、PATH の前のほうのディレクトリに置いた別の `ctx7`、`npm` の非 0、導入後に PATH に `ctx7` が無い（npm は 0 で終わるが何も置かない）
- 防御範囲:
  - 対象: PATH 上の `ctx7` の実体が npm のグローバルの `ctx7/` の下に無いもの（別のディレクトリの実行ファイル・symlink）を拒否する。`npm install -g` の失敗、PATH に無い、`ctx7 --version` の失敗・空の出力で止まる。どの拒否でも成功のメッセージを出さない
  - 対象外（拒否しない）: PATH 上の `ctx7` が symlink で、実体が npm のグローバルの `ctx7/` の下にあるもの。パッケージの中のファイル名の違い。npm のグローバルの位置に symlink が入っていること
  - 対象外（検査しない）: 導入した版が npm の latest と一致するか
- 受け入れの確認:
  1. 既存コンテナで `bash .devcontainer/install_ctx7.bash` を実行すると 0.8.0 から最新（確認時は 0.8.2）に入れ替わり、`ctx7 --version` が最新を示す
  2. `git grep -n CTX7_CLI_VERSION -- ':!docs/superpowers'` が空（`rg` は既定で隠しディレクトリを検索しないので使わない）
  3. `npm install -g` の失敗、PATH に `ctx7` が無い、PATH の前のほうに別の `ctx7` がある、のいずれも `[install_ctx7] ERROR: ...` を出して非 0 で終わり、成功のメッセージを出さない
  4. `bash .devcontainer/test-install-ctx7.bash` と `bash .devcontainer/run-tests.bash` が通る
  5. `.devcontainer/README.md` の「動作確認」のコマンドが通る（`ctx7 setup` を実行していない）
  6. Rebuild でも同じ結果になる（マージの後の確認。PR は `Refs #290`）

## 要件の照合（Spec → Task）

| Spec の条件 | 担当 Task | 観測する結果 | 検証 |
| --- | --- | --- | --- |
| `ctx7@latest` の導入、`--version` 以外で呼ばない | Task 1 | 偽の npm の記録、偽の `ctx7` の呼び出しの記録 | `test-install-ctx7.bash` |
| PATH の前のほうの別の `ctx7` の拒否 | Task 1 | 非 0、ERROR 行、成功のメッセージ無し | `test-install-ctx7.bash` |
| 拒否・停止の残り（npm の失敗、PATH に無い、`--version` の失敗、名前の前方一致、symlink の位置） | Task 2（統合） | 非 0、ERROR 行、成功のメッセージ無し／正しい形は 0 | 一時的な実行（コミットしない） |
| 0.8.0 から最新への入れ替え、動作確認 | Task 2（統合） | `ctx7 --version`、`ctx7 library`・`ctx7 docs` の終了コード | 実機での実行 |
| 文書の更新、`CTX7_CLI_VERSION` の除去 | Task 2 | `git grep`・`rg` の結果、`git diff` | `git grep`・`rg`・`git diff`・`run-tests.bash`・`check-layout.sh` |
| Rebuild での確認 | — | — | マージの後（PR 本文・Issue のコメントに残す） |

共有する条件: 「拒否のときに成功のメッセージを出さない」と「`ctx7` を `--version` 以外で呼ばない」は、Task 1 の実装と Task 2 の文書（トラブルシュートの ERROR の文言）の両方に関わる。Task 2 で、文書の ERROR の例が Task 1 の実際のメッセージと合うことを確かめる。

## 実行方式

`superpowers:executing-plans`（inline）。`implement_task.py check` の `self` が true（雛形の既定の適用）で、Task は 2 つ、Task 2 の文書は Task 1 の実際のメッセージに依存する逐次の変更のため。作業領域は `PARENT_ROOT` の `tmp/agents/issue-290.*/sdd/2026-10-28-create-reso-world-issue290-ctx7-latest/`。

## 検証の入口

worktree のルートで、ルートの `README.md` の「テスト」のコマンド（ワールドの行を除く）:

```bash
bash .devcontainer/run-tests.bash
bash scripts/check-layout.sh
uv run pytest tests/skills .agents/skills .agents/scripts tools
```

## 実行予算

- 全体の能動時間の予算: 240 分（実装・検証・PR が 60 分、PR 修正ループがサイクルの上限 3 ×（レビューの期限 45 分＋計画・修正 15 分）= 180 分）。根拠: Task 2 つの小さな変更で、同じ形の #291 の run の実績
- phase の目安: 準備（Spec・Plan）15 分、Task 1 15 分、Task 2 20 分、全体の検証・PR 10 分、ループ最大 180 分
- worker: 実装は inline で、別の worker を起動しない。ループのレビュアーの期限は pr-review-fix-loop の設定（45 分）に従う
- 再試行の上限: 同じ失敗の再試行は 1 回まで（`.agents/execution-budget.md` の既定）
- checkpoint: Task 2 の後（PR の前）、予算の 50%（120 分）・100%、ループのサイクルの境界
- 縮小・切り出し・方法変更の候補: 実機の `npm install -g` がネットワークで失敗したら、受け入れの確認 1・5 をマージの後の確認に回し、PR 本文と Issue に書く（実装と偽のテストは続ける）。`ctx7` の最新版が壊れていたら、導入はそのまま止まる（設計どおり）ので、その事実を報告して止まる

## contingency（代替策）

- 最初の RED で、偽の npm・偽の `ctx7` の前提（`npm root -g` の呼び方、`readlink -f` の結果）が実際と違うと分かったら、Spec の意味（実体の場所で判定、ファイル名を仮定しない）を保つ最小の修正をして、ledger に残して続ける
- 実機の導入で、`npm root -g` の実体と `command -v ctx7` の実体の関係が想定（`<root>/ctx7/` の下）と違ったら、実装を変えずに止まり、観測した実体のパスを報告する（判定の意味が変わるため）
- `ctx7 library`・`ctx7 docs` が quota で失敗したら、`CONTEXT7_API_KEY` の有無を確かめ、受け入れの確認 5 を未確認として報告する。成功と書かない

---

### Task 1: `install_ctx7.bash` の最新版の導入と実体の確認

**Files:**
- Modify: `.devcontainer/install_ctx7.bash`（全体）
- Modify: `.devcontainer/test-install-ctx7.bash`（全体）

**テストの要否:** 要る（S）。PATH の前のほうの別の `ctx7` を黙って使わないこと、`ctx7` を `--version` 以外で呼ばないこと（`ctx7 setup` が共有の場所へ書き込んでも導入は成功する）は、壊れてもエラーにならない。正しく通る例を 1 件残し、`ctx7@latest` の要求もその実行の記録で確かめる。npm の失敗・PATH に無い・`--version` の失敗は L なのでテストにしない。

**Interfaces:**
- Produces: エラーの形 `[install_ctx7] ERROR: <理由>`（stderr、終了コード 1）、PATH の判定の失敗の理由に `is not the npm global ctx7` を含める。成功の行 `[install_ctx7] Context7 CLI <版> installed at <PATH 上のパス>.`。Task 2 の文書はこの 2 つを引用する

- [ ] **Step 1: テストを書き直す（RED）**

`test-install-ctx7.bash` を次の形にする。冒頭のコメントは、確かめること（`ctx7@latest` を要求する、`ctx7` を `--version` 以外で呼ばない、PATH の前のほうの別の `ctx7` を受け入れない）と理由に直す。版の変数の `sed` の読み取りは消す。

- 偽の npm（`$tmp/bin/npm`）: 引数を `$CALLS` に `npm <args>` で記録する。`root -g` なら `$NPM_ROOT` を出して 0。それ以外（install）は `$NPM_ROOT/ctx7/bin/fake-cli` に偽の `ctx7` を置き、`$NPM_BIN/ctx7` からその実体への symlink を張る
- 偽の `ctx7`: 引数を `ctx7 <args>` で記録し、`--version` のときだけ版（`9.9.9`）を出す
- 別の `ctx7`（`$tmp/shadow/ctx7`）: 引数を `shadow <args>` で記録し、版を出す
- `PATH="$tmp/bin:$NPM_BIN:/usr/bin:/bin"`。`run` は、偽の導入物（`$NPM_ROOT/ctx7`・`$NPM_BIN/ctx7`）と `$CALLS` を空にしてから `env "$@" bash "$installer"` を実行する

アサーション:

```bash
run || fail "installer failed: $(cat "$tmp/output")"
grep -qxF 'npm install -g ctx7@latest' "$CALLS" || fail "installer did not install ctx7@latest: $(cat "$CALLS")"
[ "$(ctx7_calls)" = 'ctx7 --version' ] || fail "installer ran ctx7 for more than its version: $(ctx7_calls)"

if run PATH="$tmp/bin:$tmp/shadow:$NPM_BIN:/usr/bin:/bin"; then fail 'installer accepted a ctx7 that comes before the npm global one on PATH'; fi
grep -qF '[install_ctx7] ERROR: ' "$tmp/output" || fail "no ERROR line for the other ctx7: $(cat "$tmp/output")"
! grep -qF 'installed at' "$tmp/output" || fail "installer reported success for the other ctx7: $(cat "$tmp/output")"
printf 'PASS: install_ctx7.bash installs ctx7@latest and rejects another ctx7 first on PATH\n'
```

- [ ] **Step 2: RED を確かめる**

Run: `bash .devcontainer/test-install-ctx7.bash`
Expected: `FAIL: installer did not install ctx7@latest: ...`（変更前のインストーラは `ctx7@0.8.0` を要求する）で非 0

- [ ] **Step 3: `install_ctx7.bash` を書き直す**

Spec の「設計」の 1 の順（install → `npm root -g` → `command -v ctx7` → 両側を `readlink -f` にして `case "$ctx7_real" in "$root_real"/ctx7/*)` で判定 → `"$ctx7_path" --version` → 空白を除いて空なら止める → 成功の行）。冒頭のコメントは、版を固定しないこと、postCreate と rebuild せずに最新へ上げるときに実行すること、`ctx7 setup`・`ctx7 upgrade` を実行しない理由を書く（#290）。判定の失敗の理由は `"${ctx7_path} (${ctx7_real}) is not the npm global ctx7 under ${root_real}/ctx7/. Another ctx7 may come first on PATH."`

- [ ] **Step 4: GREEN を確かめる**

Run: `bash .devcontainer/test-install-ctx7.bash`
Expected: `PASS: install_ctx7.bash installs ctx7@latest and rejects another ctx7 first on PATH`、終了コード 0

- [ ] **Step 5: 構文の確認**

Run: `bash -n .devcontainer/install_ctx7.bash && bash -n .devcontainer/test-install-ctx7.bash`
Expected: 出力なし、終了コード 0（ShellCheck はコンテナに無い）

- [ ] **Step 6: Commit**

```bash
git add .devcontainer/install_ctx7.bash .devcontainer/test-install-ctx7.bash
git commit -m "fix(devcontainer): ctx7 を版を固定せず npm の最新版で導入する (#290)"
```

### Task 2: 文書の更新と統合の確認

**Files:**
- Modify: `.devcontainer/install_beforehand.bash:208-209`（step の表示とコメント）
- Modify: `.devcontainer/README.md`（33 行目の一覧、82 行目の postCreate の説明、「Context7 CLI（ctx7）」の「導入」「更新」「動作確認」「トラブルシュート」）
- Modify: `README.md:120`
- Modify: `.agents/skills/find-docs/SKILL.md:26,34`

**テストの要否:** 不要。文書・コメントの文言は F で、壊れても L（`rg`・`git diff` で確かめる）。拒否・停止の残りの経路は L か Task 1 のテストと同じ守り（D）なので、一時的な実行で確かめてコミットしない。

**Interfaces:**
- Consumes: Task 1 のエラーの形と成功の行

- [ ] **Step 1: 文書とコメントを直す**

Spec の「設計」の 3 のとおり。`.devcontainer/README.md` の「更新」は番号の手順をやめ、「`bash .devcontainer/install_ctx7.bash` を実行すると npm の最新版に入れ替わる（Rebuild Container でもよい）。版を上げる PR は要らない。入れ替えの後に下の『動作確認』を行う」とする。`Update available` の段落は「この案内（`ctx7 upgrade`・`npm install -g ctx7@latest`）には従わず、`install_ctx7.bash` で更新する。導入の後に PATH 上の `ctx7` の実体を確かめるため」にする。「動作確認」の `ctx7 --version` のコメントは「`install_ctx7.bash` が最後に表示した版」にする。トラブルシュートの ERROR の行は Task 1 の `... is not the npm global ctx7 ...` に合わせ、確かめ方に `readlink -f "$(command -v ctx7)"` と `npm root -g` の比較を書く。`Update available` の行は「従わない。`bash .devcontainer/install_ctx7.bash` で更新する」にする。「導入」の `ctx7 setup` の説明（0.8.0 で確かめた書き込み先）は残す。

- [ ] **Step 2: 参照の確認**

Run: `git grep -n CTX7_CLI_VERSION -- ':!docs/superpowers'; rg -n '固定した版|pinned' .devcontainer/README.md README.md .agents/skills/find-docs/SKILL.md .devcontainer/install_beforehand.bash .devcontainer/install_ctx7.bash | rg -i 'ctx7|context7'`
Expected: どちらも出力なし（1 つ目の終了コード 1）

- [ ] **Step 3: 停止の経路の一時的な確認（コミットしない）**

`PARENT_ROOT` のセッションディレクトリの下に、Task 1 のテストと同じ偽の npm を使う一時的なスクリプトを置き、次を実行して、それぞれの終了コードと出力を ledger に残す。

| 入力 | 期待 |
| --- | --- |
| 偽の npm が非 0 | 非 0、`[install_ctx7] ERROR: npm install -g ctx7@latest failed.`、`installed at` 無し |
| 偽の npm が 0 で何も置かない | 非 0、`ctx7 is not on PATH after the install.`、`installed at` 無し |
| 偽の `ctx7` の `--version` が非 0 / 空の出力 | 非 0、ERROR 行、`installed at` 無し |
| `$NPM_ROOT/ctx7-other/` の下の実行ファイルへの symlink を `$NPM_BIN/ctx7` に置く | 非 0、`is not the npm global ctx7` |
| `$NPM_ROOT` を symlink 経由のパスで返す（実体は別の場所） | 0、成功の行 |
| PATH の前のほうの別の `ctx7` | 非 0、別の `ctx7` の呼び出しの記録が無い |

- [ ] **Step 4: 実機の導入と動作確認（統合）**

Run（worktree のルートで）:

```bash
ctx7 --version                                  # 前: 0.8.0
npm view ctx7@latest version
bash .devcontainer/install_ctx7.bash; echo "exit=$?"
ctx7 --version                                  # 後: npm の latest と同じ
readlink -f "$(command -v ctx7)"; npm root -g
ctx7 library react "How to clean up useEffect with async operations"; echo "exit=$?"
ctx7 docs /react/react "useEffect cleanup" | head -20; echo "exit=${pipestatus[1]:-${PIPESTATUS[0]}}"
```

Expected: インストーラの終了コード 0 と `[install_ctx7] Context7 CLI <latest> installed at ...`、`ctx7 --version` が latest、`ctx7 library`・`ctx7 docs` が終了コード 0。`ctx7 setup` は実行しない。

- [ ] **Step 5: 全体の検証**

Run: 「検証の入口」の 3 つのコマンド
Expected: すべて終了コード 0。`run-tests.bash` は `PASS: <N> test(s)`

- [ ] **Step 6: Commit**

```bash
git add .devcontainer/install_beforehand.bash .devcontainer/README.md README.md .agents/skills/find-docs/SKILL.md
git commit -m "docs: ctx7 を npm の最新版で導入する運用に合わせる (#290)"
```

## 実施の記録

- 実行方式: `superpowers:executing-plans`（inline、claude-opus-5-5）。作業領域と ledger は `PARENT_ROOT` の `tmp/agents/issue-290.izc14zd1/sdd/2026-10-28-create-reso-world-issue290-ctx7-latest/progress.md`（コミットしない）
- Task 1（`9362b5a`）: RED は、変更前のインストーラが偽の `ctx7` の版（9.9.9）を固定の 0.8.0 と比べて止まる失敗だった（Plan の Expected の文言と違うが、版の固定が残っていることによる正しい RED）。GREEN の後、一時的な変異（PATH の判定を消す、`ctx7@0.8.0` に戻す、`ctx7 setup` を呼ぶ）をテストが検出することを確かめた
- Task 2（`6f06794`）: 停止の経路の一時的な確認（npm の失敗、何も置かない、`--version` の失敗・空、`ctx7-other`、別の `ctx7` が先 → 非 0・成功の行なし・別の `ctx7` は呼ばれない。npm の root が symlink 経由・通常 → 0）。実機で 0.8.0 → 0.8.2（npm の latest）、`ctx7 library`・`ctx7 docs` は終了コード 0。Plan の Step 5 と Step 6 は、`--merge` の検証の記録のために commit を先にした
- 受け入れ確認 2: `git grep -n CTX7_CLI_VERSION <rev> -- ':!docs/superpowers'` が base（`640fae1`）で 13 件、HEAD で 0 件。最初に Plan に書いた `rg` のコマンドは隠しディレクトリを検索せず、変更の前でも空になる誤りだった（最終レビューの指摘）ので、`git grep` に直した
- 最終レビュー（新しい文脈の Opus）: Critical 0・Important 0・Minor 5、マージ可。Minor のうち検証のコマンドの誤りだけを直し、残りは見送った
  - 拒否の例が、別の `ctx7` を呼ばないことまでは確かめていない（判定の前に `--version` を呼ぶ形に壊れても通る）。呼ばれるのは `--version` だけで、その後に拒否されるので S に当たらない
  - `.devcontainer/README.md` の「動作確認」のコメントが `dist/index.js` を決め打ちしている
  - トラブルシュートの表に `--version printed nothing.` の行が無い（「導入」の節には含まれる）
  - `ctx7 --version` の出力が複数行だと、空白の除去で版の表示がつながる（0.8.2 は 1 行）
- 持ち越し候補: 上流に壊れた版が出ると、postCreate の後続の手順も止まる。一時的に版を指定する手段か、警告して続ける形を、起きたときに別の Issue で検討する
- マージの後の確認: Rebuild で同じ結果になる（postCreate のログに導入した版が出る）
