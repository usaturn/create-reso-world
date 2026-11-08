# PR #342（Issue #340）のレビュー修正: Claude Code が空とみなすキーでの起動の停止

## 管理・実行許可

- 状態: `completed`
- PR: https://github.com/usaturn/create-reso-world/pull/342（branch `feat/issue-340-ollama-launcher`、base `main`）
- 元の Spec: `docs/superpowers/specs/2026-11-08-issue-340-ollama-launcher-design.md`、Plan: `docs/superpowers/plans/2026-11-08-issue-340-ollama-launcher.md`
- 実行許可: 利用者の `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/340 --merge --implement claude-code_sonnet_default --assign implement=claude-code_sonnet_default --assign inspect=pi_openai-codex_gpt6-sol_max`。`--merge` の PR 修正ループ（pr-review-fix-loop）の中の review-fix-planning の完遂として、この PR の承認済みの実装修正、push、状況コメント、修正不要のときの `finalize.py` によるマージと関連 Issue の更新を行う
- planner: `claude-opus-5-5`（Claude Code、司令塔）。サイクル 1、レビュー対象の HEAD `23bebef050997cecbe1792ef93356ce027820547`

## レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | このサイクルで再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| `gpt-6.1-sol.md` | gpt-6.1-sol | pi（`pi_openai-codex_gpt6-sol_max`） | `23bebef05099` | はい | Approve |

- 確認済みの一覧: `reviews/usaturn/create-reso-world/#342-feat-issue-340-ollama-launcher/verified/23bebef05099.json`（V-1 confirmed）
- 修正の担当（`run_roles.py --phase implement`）: `claude-code_sonnet_default`（利用者の `--assign implement=…`）。self-review・fix-check: `self`（雛形の既定）

## 全指摘と分類

| ID | 区分 | 根拠 |
| --- | --- | --- |
| `gpt-6.1-sol#M-1@23bebef05099` | 対応する | 致命的（秘密情報の露出）: 保存済みの claude.ai の OAuth トークンが `https://ollama.com` 向けの Authorization に使われる。空に見えるクリップボードの内容（NBSP・BOM など）を貼り付けた場合や C ロケールのシェルで到達できる。(a) 再現した誤動作（V-1） |

解消済み 0 / 対応する 1 / 対応しない 0。

## 要件対応

- Issue #340 は「`OLLAMA_API_KEY` が未設定・空・空白だけなら…`claude` を起動しない。Claude Code は `ANTHROPIC_AUTH_TOKEN` が空か空白だけだと、保存済みの claude.ai の OAuth トークンを接続先へ送る」と求める。守るべきは Claude Code が空とみなす値すべてであり、元の Spec が入力の範囲を ASCII の空白・タブ・改行に限ったのは、要件を狭めていた（元の Spec の決定記録「キーの検査」と受け入れ条件 2 を、この修正に合わせて直す）
- Issue の除外範囲（`settings.json`、Ollama の CLI、agent-runner、Pi）とは関係しない
- 共有条件: ガードの判定の内容を zshrc.txt の関数とコメント、テストのコメント、README の 2 か所が同じに述べること。統合担当は planner で、差分の読み合わせと、偽の HOME での複数のロケール × 複数の文字の確認で確かめる

## 修正方針

- ガードを「空白を除いて空か」から「ASCII の英数字を 1 文字も含まなければ起動しない」（`[[ ${OLLAMA_API_KEY:-} != *[A-Za-z0-9]* ]]`）に変える
- 比べた案:
  - 点の修正（JavaScript の trim の空白の一覧を zsh のパターンに書く）: 一覧を写すので Claude Code・ECMAScript の側の変化に追従しない。C ロケールでは `$' '` などのマルチバイトの文字をパターンで扱えない
  - JavaScript（node）で trim の結果を判定する: 実行時に node への依存が増え、ランチャーが重くなる
  - 選んだ案（ASCII の英数字を要求する）: ASCII の英数字は trim で除かれないので、通る値は Claude Code が空とみなさない（条件が構造で成り立つ）。zsh の範囲は文字コードで比べるのでロケールに依らない。Ollama の API キーは英数字を含むので正しいキーは通る。英数字を含まない記号だけの値も止まるが、キーではない
- テストは関数を増やさず、`test_ollama_launcher_requires_key` の入力を ASCII の空白・NBSP・BOM を含む 1 つの値（`$' \xc2\xa0\xef\xbb\xbf'`、ロケールに依らないように UTF-8 のバイト列）に変える。空だけを止める書き方と `[[:space:]]` だけを除く書き方の両方の誤りを、この 1 件で捕まえる。正しく通る例は送り先のテストの `ccdol`・`claude-ollama`（`fake-ollama`）が受け持つ（「テストの採用基準」の S。組み合わせ別に増やすのは D）
- README の 2 か所、zshrc.txt とテストのコメント、元の Spec・Plan の記述を新しい判定に合わせる

## 守る条件と影響経路

守る条件: Claude Code が空と解釈する `OLLAMA_API_KEY`（JavaScript の `trim()` で空になる値）では、`ccdol`・`claude-ollama` は claude を起動しない。破れた前提: zsh の `[[:space:]]` が除く文字（ロケールで変わる）と JavaScript の `trim()` が除く文字が違うのに、`env` の前のガードが前者だけで判定していた。

| 守る条件 | 経路 | 判定 | 観測する結果 | 確かめる方法 | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| 上記 | `ccdol` → ガード → `env` → `claude` | 修正する | NBSP・BOM・U+202F・U+3000・U+2028 だけのキーで終了コード 1、claude を起動しない（3 つのロケール）。`fake-ollama` は起動 | 変更したテスト、ガードを戻した変異の対照、偽の HOME での確認 | `0665a44d`: 担当が入力だけを変えた RED（`ccdol must fail…` で非 0）→ 修正後 0。ガードを元の `[[:space:]]` 版・`[[ -z $OLLAMA_API_KEY ]]` に戻すとどちらも非 0、戻して 0。planner の偽の HOME の確認（`guard-probe-after.tsv`）で ja_JP.utf8・C.UTF-8・C のどれでも U+00A0・U+FEFF・U+202F・U+3000・U+2028・U+200B・ASCII の空白・タブと改行・空・未設定が rc=1・起動なし、`fake-ollama` が rc=0・起動 |
| 上記 | `claude-ollama`（同じ関数の本体） | 修正する | 同上 | 同上（両方の名前で確認） | 同じ関数の本体で、ガードは `$funcstack[1]` に依らない（`0665a44d` の zshrc.txt:175-183）。送り先のテストの `claude-ollama`（`fake-ollama`）は `run-tests.bash` で PASS |
| 上記 | `ccdd`・`ccddg`・`ccdu` の `${…:?}`・`:-` | 対象外 | ― | ― | base にある別の仕組み（空だけを止める）で、この PR が入れたものではない。マージの後の持ち越し候補 |
| 上記 | README・コメント・元の Spec・Plan の記述 | 修正する | 新しい判定と同じ内容 | 差分の読み合わせ | `23bebef0..0665a44d` の差分で zshrc.txt のコメント、テストのコメント、README の 2 か所が「英数字を 1 文字も含まなければ起動しない」と同じに述べることを確かめた。元の Spec・Plan は Spec の commit で直す |

同じ条件の再発と設計の見直し: きっかけに当たらない（このサイクルが最初のレビュー修正）。

## 結論・検証・自己レビュー

- 修正: `run_roles.py --phase implement`（`claude-code_sonnet_default`、観測したモデル `claude-sonnet-5-5`、52 秒、stop_confirmed）が commit `0665a44d` を作り、planner が差分を確かめて fast-forward で取り込んだ
- 検証（`0665a44d`、作業ツリー clean）: `bash .devcontainer/run-tests.bash` 0（27 本 PASS）、`bash scripts/check-layout.sh` 0、push の前の秘密情報の検査 0（検出なし）
- 修正後の自己レビュー（`run_roles.py --phase self-review` の 1 回。self-review・fix-check とも `self` で、司令塔がサブエージェント（claude-opus-5-5）に任せた）:
  - self-review（観点 2、PR 全体の再レビュー、`reviews/usaturn/create-reso-world/#342-feat-issue-340-ollama-launcher/claude-opus-5-5-commit-0665a44da69e7250f2ae8d8de9e5f746ff823579.md`）: Critical・High・Medium・Low 0 件、Info 1 件（I-1: 元の Spec の決定記録「キーの検査」と Plan の持ち越しが古いガードのまま）。偽の HOME で 5 つのロケールを試し、trim で空になる値（U+1680・U+2000〜U+200A・U+2029・U+205F を含む）はすべて止まり、ASCII の英数字を含む値は起動した。Merge recommendation は Approve
  - fix-check（観点 1・3、`verified/0665a44da69e.fix-check.json`）: 修正は対応済み。node の trim が除く 25 の符号位置の 1 文字だけの値・未設定・空・テストの入力・混合の値は 4 つのロケールで止まり、英数字を含む値は起動して `ANTHROPIC_AUTH_TOKEN` に同じバイト列が渡る。テストは、ガードを `[[:space:]]` 版・`[[ -z ]]` 版・ガード無しに置き換えると 3 つのロケールで失敗し、別の拒否理由に隠れていない。新しい指摘は V-1（README の止める条件の書き方が実装より狭く読める）と V-2（元の Spec・Plan が修正前の記述のまま）
  - 自己レビューの指摘の判定: `fix-check#V-1@0665a44da69e` は対応しない（致命的ではない。実装は README の書き方より広く止めるので、書いてあるとおりに使っても誤った結果にならない）。`fix-check#V-2@0665a44da69e` と `claude-opus-5-5-commit-0665a44da69e7250f2ae8d8de9e5f746ff823579#I-1@0665a44da69e` は同じ問題で致命的ではないが、経路表の「元の Spec・Plan の記述」の行として予定していたとおり、この Spec の commit で元の Spec の決定記録・受け入れ条件 2 と Plan の「完了」節を直した
  - 自己レビューの後の変更は文書（この Spec と元の Spec・Plan）だけで、再レビューしていない。コードとテストは `0665a44d` から変えていないので、`0665a44d` の検証（run-tests・check-layout）の結果を引き継ぐ
- 正しいキーが通ること: この run の実 API の確認に使った実際の `OLLAMA_API_KEY` が ASCII の英数字を含む（新しいガードを通る）ことを、値を出さずに真偽だけで確かめた
- 未確認の事項: 保存済みの OAuth が選ばれる段階の実行（実資格情報・実通信を使わない。静的な読み取りとレビュアーの抽出実行に依る）
- 結論: 1（修正して push する）
