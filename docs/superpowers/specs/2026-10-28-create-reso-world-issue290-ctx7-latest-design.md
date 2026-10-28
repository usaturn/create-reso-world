# Issue #290: ctx7 の版の固定をやめ、セットアップで常に npm の最新版を導入する

## 管理・実行許可

- 文書管理: usaturn/create-reso-world
- 対象: usaturn/create-reso-world #290（https://github.com/usaturn/create-reso-world/issues/290）
- 状態: completed（内容の承認は未取得。実行許可に基づく完了記録。PR #294 の修正ループのサイクル 1 は結論 2（修正不要）。マージと Issue の更新の結果は状況コメントと完了報告にある）
- 指示: `/issue-to-pr #290 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge`
- 許可: 通常の設計判断を推奨案で決め、検証・commit・push・PR 作成と、PR 修正ループ（`finalize.py`）によるマージまで行う。実行の許可であり、内容の承認ではない
- 設計時の base: `origin/main` の `640fae1e185b7e48421a5033e481ac7f7f57bc4b`
- 関連文書: Plan `docs/superpowers/plans/2026-10-28-create-reso-world-issue290-ctx7-latest.md`

## 意図

`find-docs` スキルが使う Context7 CLI（`ctx7`）は、#162 で `.devcontainer/install_ctx7.bash` の版の変数に固定して導入している。固定した版は、版を上げる PR と Rebuild が済むまで古いままになる（着手時のコンテナは 0.8.0、npm の latest は 0.8.2、`engines.node` は `>=22.13.0`、コンテナの Node.js は v24.22.1）。

ResoLoop と同じく、セットアップ（postCreate）と明示的な再実行で、常に npm の最新版を入れる形にし、版を上げるためだけの PR を不要にする。「常に最新」は、セットアップ時点とスクリプトの実行時点の最新を指す。

## 目的・非目的

目的:

- `install_ctx7.bash` が `npm install -g ctx7@latest` で導入し、導入した版（`ctx7 --version` の出力）をログに残す。版の比較はしない
- 導入後に止める条件（`npm install -g` の失敗、PATH に `ctx7` が無い、PATH の前のほうに別の `ctx7` がある）を維持し、どれも `[install_ctx7] ERROR: ...` を出して非 0 で終わる
- 文書（`.devcontainer/README.md`・`README.md`・`find-docs` の SKILL.md・`install_beforehand.bash` のコメント）を、版を固定しない運用に合わせる

非目的（Issue の「対象外」のとおり）: 他の固定版ツール（`meshy-cli@0.4.0`・`FLUX_SDK_VERSION`・Gitleaks の SHA-256）、Context7 の MCP Server・Pi 拡張の復活と `npx` 経由の導入、コンテナ起動時や定期実行による更新の監視、Node.js の版の固定・引き上げ。zsh の `update` に `ctx7` を加えることも、定期の更新に当たるので行わない。

避けること（動いても失敗とみなす）: PATH の前のほうにある別の `ctx7` を黙って使うこと。失敗を成功として報告すること。`ctx7 setup`・`ctx7 upgrade` を実行すること（`ctx7 setup` は共有の `~/.claude`・`~/.codex` などへ書き込む）。

## 設計

### 1. `.devcontainer/install_ctx7.bash`

次の順に処理する。どの失敗も `fail`（`[install_ctx7] ERROR: <理由>` を stderr に出して終了コード 1）で止め、成功のメッセージを出さない。

1. `npm install -g ctx7@latest`。失敗したら止める
2. `npm root -g` で npm のグローバルの `node_modules` を求める。失敗・空なら止める
3. `command -v ctx7` で PATH 上の `ctx7` を求める。無ければ止める
4. 2 と 3 をそれぞれ `readlink -f` で実体のパスにし、3 の実体が `<2 の実体>/ctx7/` の下に無ければ止める（PATH の前のほうに別の `ctx7` がある）。メッセージには PATH 上のパスと実体、npm のグローバルの `ctx7` のディレクトリを入れる。パッケージの中のファイル名（`dist/index.js` など）は仮定しない
5. 4 を通った後に `ctx7 --version` を実行する。失敗・空の出力なら止める（新しい版が Node.js の版などで動かないとき、postCreate の失敗として現れる）
6. `[install_ctx7] Context7 CLI <版> installed at <PATH 上のパス>.` を出す

4 を 5 の前に置くのは、PATH の前のほうにある別の `ctx7` を実行しないためである。`ctx7` は `--version` 以外で呼ばない。`ctx7 setup`・`ctx7 upgrade` は実行しない。冒頭のコメントは、版を固定しないこと、更新はこのスクリプトか Rebuild で行うこと、`ctx7 setup` を実行しない理由に直す。

### 2. `.devcontainer/test-install-ctx7.bash`

偽の npm と偽の `ctx7` で、ネットワークを使わずに `install_ctx7.bash` を実行する。版の変数の読み取りと、版の一致の検査はやめる。

- 偽の npm は、`install -g` の引数を記録し、偽の npm のグローバルの `node_modules` の `ctx7/` の下に偽の `ctx7` を置き、npm のグローバルの bin にそこへの symlink を置く。`root -g` にはその `node_modules` を返す。偽の `ctx7` のファイル名は実物と違う名前にし、インストーラがファイル名を仮定しないことも同じ実行で確かめる
- 正しく通る例: 終了コード 0、`npm install -g ctx7@latest` を要求したこと、`ctx7` を `--version` だけで呼んだこと
- 拒否の代表 1 件: PATH の前のほうに別の `ctx7` を置くと、非 0 で終わり、`[install_ctx7] ERROR: ` の行があり、成功のメッセージが無い

### 3. 文書とコメント

- `.devcontainer/install_beforehand.bash`: step の表示を `Installing the latest Context7 CLI (ctx7)` にし、コメントの「版の固定と導入後の確認」を「最新版の導入と導入後の確認」にする。呼び出しの位置と `postCreateCommand` は変えない
- `.devcontainer/README.md`: ツール一覧の行、「既存環境の更新」の postCreate の説明、「Context7 CLI（ctx7）」の「導入」「更新」「動作確認」「トラブルシュート」を、最新版の導入と PATH の実体の確認に合わせる。「更新」は「`bash .devcontainer/install_ctx7.bash` を実行するか Rebuild Container する。版を上げる PR は要らない」とし、`Update available` の案内（`ctx7 upgrade`・`npm install -g ctx7@latest`）に従わず、このスクリプトで更新する理由（PATH の実体を確かめるため）を書く。「エージェント向けツールの導入」の手順 21（`bash .devcontainer/install_ctx7.bash`）は変えない
- `README.md`: 「postCreate が固定した版で入れる」を「postCreate が npm の最新版を入れる」にする
- `.agents/skills/find-docs/SKILL.md`: 前提の節で、セットアップが `install_ctx7.bash` で npm の最新版を入れると書く。`Update available` を自分で追わない理由を「版は `bash .devcontainer/install_ctx7.bash` の再実行か Rebuild で変わる（利用者が行う）」に直す

## 受け入れ基準

動作環境: Ubuntu 26.04 LTS の Dev Container（Node.js v24.22.1、npm のグローバルは nvm の `/usr/local/share/nvm/versions/node/v24.22.1`）。テストは同じコンテナの bash で、偽の npm と偽の `ctx7` を使い、ネットワークを使わない。

実入力:

- 実際の導入: 着手時のコンテナの `ctx7` 0.8.0（実体 `$(npm root -g)/ctx7/dist/index.js`、PATH 上は `$(npm prefix -g)/bin/ctx7` の symlink）に対して `bash .devcontainer/install_ctx7.bash` を実行する
- 拒否の入力: PATH の前のほうのディレクトリに置いた別の `ctx7`（実行可能なファイル）。npm の失敗（`npm` が非 0）、導入後に PATH に `ctx7` が無い（npm は 0 で終わるが何も置かない）

防御範囲:

- 対象: PATH 上の `ctx7` の実体が npm のグローバルの `ctx7/` の下に無いもの（別のディレクトリの実行ファイル・symlink）を拒否する。`npm install -g` の失敗、PATH に無い、`ctx7 --version` の失敗・空の出力で止まる。どの拒否でも成功のメッセージを出さない
- 対象外（拒否しない）: PATH 上の `ctx7` が symlink で、実体が npm のグローバルの `ctx7/` の下にあるもの（通常の導入の形）。パッケージの中のファイル名の違い。npm のグローバルの位置に symlink が入っていること（両側を `readlink -f` で比べる）
- 対象外（検査しない）: 導入した版が npm の latest と一致するか（導入の後に新しい版が出ることがあり、比較しない）

受け入れの確認:

1. 既存コンテナで `bash .devcontainer/install_ctx7.bash` を実行すると 0.8.0 から最新（確認時は 0.8.2）に入れ替わり、`ctx7 --version` が最新を示す
2. リポジトリの `docs/superpowers/` の外に `CTX7_CLI_VERSION` が残っていない（`git grep -n CTX7_CLI_VERSION -- ':!docs/superpowers'` が空。`rg` は既定で `.devcontainer/`・`.agents/` のような隠しディレクトリを検索せず、変更の前でも空になるので使わない）
3. `npm install -g` の失敗、PATH に `ctx7` が無い、PATH の前のほうに別の `ctx7` がある、のいずれも `[install_ctx7] ERROR: ...` を出して非 0 で終わり、成功のメッセージを出さない
4. `bash .devcontainer/test-install-ctx7.bash` と `bash .devcontainer/run-tests.bash` が通る
5. `.devcontainer/README.md` の「動作確認」のコマンドが通る（`ctx7 library react ...`・`ctx7 docs /react/react ...`。`ctx7 setup` を実行していない）
6. Rebuild でも同じ結果になる（postCreate のログに導入した版が出る）。マージの後でなければ確かめられないので、PR は `Refs #290` にし、PR 本文と Issue のコメントに残す

## テストの要否

AGENTS.md の「テストの採用基準」と Issue の「テストの要否」に従う。

- S（書く）: PATH の前のほうの別の `ctx7` を黙って使わないこと、`ctx7` を `--version` 以外で呼ばないこと（`ctx7 setup` が共有の場所へ書き込んでも、導入は成功するので気付けない）。`test-install-ctx7.bash` で代表の 1 件ずつを確かめ、正しく通る例を 1 件残す
- `ctx7@latest` の要求は、偽の npm で実行した引数を確かめる（実行の結果の照合で、F ではない）。版の固定に戻ると、エラーにならずに古い版のまま残るので、正しく通る例の実行で一緒に確かめる
- 書かない: 版の文字列を写す F のテスト。`npm install -g` の失敗、PATH に無い、`--version` の失敗で止まる経路（非 0 の終了と postCreate の失敗として現れる L）。この 3 つは一時的な実行で確かめ、コミットしない
- 文書の更新は、`git grep`・`rg`（ファイルを明示）による参照の確認と `git diff` で確かめる

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- |
| 導入の指定 | `npm install -g ctx7@latest` | `npm install -g ctx7`（版の指定なし） | Issue の方針 1 のとおり。`latest` の dist-tag を明示し、意図をログとテストで読めるようにする | 推奨案の委任 |
| PATH の判定 | `command -v ctx7` と `npm root -g` をそれぞれ `readlink -f` で実体にし、`<root>/ctx7/` の前方一致で比べる | `npm prefix -g` の `bin/ctx7` とパスを比べる / 版の一致で比べる | Issue の方針 2 のとおり実体で判定し、ファイル名を仮定しない。nvm の `current` のような symlink を含む位置でも両側を実体にそろえる。版の一致は「常に最新」で使えない | 推奨案の委任 |
| 判定と `--version` の順 | PATH の判定を先にし、通ったときだけ `ctx7 --version` を実行する | 先に `--version` を実行する（変更前の順） | PATH の前のほうの別の `ctx7` を実行しない。拒否の理由がパスで明らかになる | 推奨案の委任 |
| `--version` の失敗と空の出力 | 止める | ログに残すだけで続ける | 新しい版が Node.js の版などで動かないことを、postCreate の失敗として早く出す（Issue の「リスクと扱い」）。成功のメッセージに版を出す前提も守る | 推奨案の委任 |
| 以前の版の表示 | 出さない（導入した版だけ） | ResoLoop のように `(was X)` を出す | 以前の版を知るには導入の前に PATH 上の未確認の `ctx7` を実行することになる。Issue は導入した版のログだけを求める | 推奨案の委任 |
| テストの範囲 | 正しく通る例 1 件と、PATH の前のほうの別の `ctx7` の拒否 1 件 | 3 つの停止条件をすべてテストにする | Issue の「テストの要否」と AGENTS.md の基準。npm の失敗・PATH に無いは L | 推奨案の委任 |
| 受け入れ条件 2 の範囲 | `docs/superpowers/` を除いて `git grep` が空 | リポジトリ全体で空にする（#162 の Spec・Plan を書き換える） | #162 の Spec・Plan は完了した記録で、書き換えない（AGENTS.md「完了した文書も削除しない」）。この Issue の Spec・Plan も変更の対象として変数名を書く。Issue の意図（コードと運用の文書に固定の版が残らない）は保たれる | 推奨案の委任。意味の変更ではなく、記録を守るための範囲の明示 |
| `docs/maatlog-poc-porting.md` の 7 行目 | 変えない | 「最新版で入れる」に直す | #162 の時点の変更を記した移植の記録で、Issue の変更範囲に無い | 推奨案の委任 |
| `find-docs` の SKILL.md の検証 | 文言の差し替えだけなので、`writing-skills` の無し/ありの比較はしない | 比較を行う | スキルの新設ではなく、前提の説明と理由の 2 か所の更新。手順（`Update available` に従わない、自分で `npm install` しない）は変えない | 推奨案の委任 |
| 実行方式 | `superpowers:executing-plans`（inline） | `superpowers:subagent-driven-development` | `implement_task.py check` の `self` が true（雛形の既定の適用）。変更は 1 つのスクリプトとそのテスト、文書の数か所で、Task が少なく逐次で済む | 推奨案の委任 |
| PR の Issue の指定 | `Refs #290` | `Closes #290` | 受け入れ条件 6（Rebuild）がマージの後でなければ確かめられない | issue-to-pr の規則 |
| ループの設定 | `check-options` の結果のとおり。`--assign inspect=pi-gpt,devin-swe,pi-deepseek` は利用者の指定。サイクルの上限 3、`fix` の担当（`implement`: claude-opus、`self-review`・`fix-check`: self）、雛形 `.devcontainer/agent-runner.toml` は既定の適用 | — | 利用者が書いたものだけを渡す | issue-to-pr の規則 |
| Plan の Task の担当 | `self`（`implement_task.py check` の `assignment` は `agents: ["self"]`、`fallback: []`。雛形の既定の適用で、`--implement` の指定なし） | — | 利用者の指定が無い | issue-to-pr の規則 |

## PR #294 の修正ループ（review-fix-planning）

### サイクル 1（HEAD `73b59c4d8aa7ce502fb50fccc8686f55b8ac5cef`）

- 実行許可: `/issue-to-pr #290 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge`（修正不要と確かめたら、`finalize.py` によるマージと関連 Issue の更新まで行う）
- planner: claude-opus-5-5（claude-code）。ループの run は `/workspaces/reso-world/reviews/usaturn/create-reso-world/#294-fix-issue-290-ctx7-latest/loop/2e7e2c04d6f14538b5b597563da83cfd`
- 入力: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#294-fix-issue-290-ctx7-latest/`。確認済みの一覧は同じディレクトリの `verified/73b59c4d8aa7.json`（review-verify、mode cycle）

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi | `73b59c4d8aa7` | はい | Approve |
| `SWE-2-Max.md` | SWE-2 Max | devin | `73b59c4d8aa7` | はい | Approve |
| `deepseek-deepseek-v4.1-flash.md` | deepseek/deepseek-v4.1-flash | pi | `73b59c4d8aa7` | はい | Approve |

分類: 解消済み 0 / 対応する 0 / 対応しない 1

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| `deepseek-deepseek-v4.1-flash#L-1@73b59c4d8aa7`（受け入れ条件 2 の範囲を `docs/superpowers/` の外に限定し、`docs/superpowers/` に `CTX7_CLI_VERSION` が 16 件残る） | 対応しない | 事実は確かめた（確認済みの一覧 V-1）。コードと運用の文書には 0 件で、実行時の影響は無く致命的ではない。残るのは #162 の完了した Spec・Plan（11 件）とこの Issue の Spec・Plan（5 件）で、完了した記録は書き換えない（AGENTS.md「完了した文書も削除しない」）。範囲の決め方は仕様の是非で、「決定記録」の「受け入れ条件 2 の範囲」に理由を残している。見直すのは、利用者が Issue #290 の条件 2 を `docs/superpowers/` を含むリポジトリ全体と明示したとき |

要件対応: この Spec の「受け入れ基準」と PR 本文の約束（受け入れ条件 1〜5 の確認、6 はマージ後）を、確認済みの一覧の coverage と照合した。修正が無いので、共有条件の統合担当と影響経路の表は不要。

結論: 2（修正不要としてマージする）。自己レビューは修正が無いので行っていない。

検証: 修正が無く、issue-to-pr で記録した同じ HEAD の検証を再利用した（`--merge` の検証の記録の再利用の条件: 同じ HEAD、未 commit の変更なし、すべて終了コード 0、ログが残っている）。base は `origin/main` の `640fae1e185b7e48421a5033e481ac7f7f57bc4b`（HEAD の祖先）で、マージした一時的なツリーでの検証は要らない。

| コマンド | 終了コード | 結果 |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 0 | `PASS: 24 test(s)` |
| `bash scripts/check-layout.sh` | 0 | `PASS: check-layout` |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools` | 0 | `1237 passed` |
