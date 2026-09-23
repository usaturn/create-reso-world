---
name: review-fix-planning
description: レビュー結果が格納されたディレクトリ（例 `reviews/ブランチ名/`、`docs/reviews/main/`、`reviews/#<PR番号>-<ブランチ>/` を指す `#番号`）を渡されて、修正計画・対応方針・指摘の取捨選択を求められたときに使う。「レビュー結果を確認して修正計画をたてて」「妥当な指摘だけ拾って直したい」「指摘のどれに対応するか決めたい」「複数モデルのレビューをまとめて」などの依頼が該当する。承認済みの review-fix 作業を実装する／対象ブランチへ反映させる依頼も該当する
allowed-tools: Read, Grep, Glob, Skill, Bash(git *), Bash(gh *), Bash(mktemp *), Bash(rm *), Bash(test *), Bash(uv run *), Bash(./scripts/ci/*), Write(docs_draft/superpowers/**), Edit(docs_draft/superpowers/**)
---

# レビュー指摘の選別と修正計画

複数モデルのレビュー結果から、**現行 HEAD でまだ生きている指摘だけ**を選び、Spec と承認を経て修正計画にする。

**中核原則: レビューは過去の HEAD に対する助言である。現行コードで再現しない指摘は指摘ではない。**

## 第1引数の解決

第1引数が `#<番号>`（例 `#300`）のとき、手順に入る前にレビューディレクトリへ解決する:

- 親リポジトリルートの `reviews/` 直下と、`public/reviews/`（`usaturn/maatlog` の PR レビューが置かれる場所）の直下にあるディレクトリだけを見る。再帰せず、その階層のファイルは候補にしない。
- ディレクトリ名が `#<番号>-` で開始されるものを一致とする（`#<番号>` の直後にハイフンが続くもの。例 `reviews/#300-fix-issue-299-pr-review-budget/`）。
- 1 件だけ一致したら、そのディレクトリをレビューディレクトリとする。
- 0 件なら、`reviews/` と `public/reviews/` の直下に一致するディレクトリが無い旨を報告して停止する。
- 複数一致したら、候補のディレクトリ名を列挙して停止し、フルパスでの指定を求める。

`#<番号>` 以外の第1引数は従来どおりレビューディレクトリのパスとして扱う。

## 手順

依頼が承認済み Spec の実装完了／PR への反映のみで、新しい選別を求めていないなら、手順 1–7 を再実行しない。レビュー対象のブランチ／PR を `git` / `gh` で確認してから **実装後** の反映手順だけを実行する。

それ以外は、各項目を TodoWrite のタスクにしてから開始する。

1. **範囲を固定する** — 解決したレビューディレクトリ配下の全ファイルを読む。各ファイル冒頭の「対象 HEAD」を記録する。複数世代が混在するのが普通である。レビュー成果物は gitignore 対象で未コミットのことがある（本リポジトリの `reviews/` がそうである）が、指定ディレクトリ内であれば Git の追跡状態にかかわらず正規の入力である。
2. **現行 HEAD を特定する** — レビュー対象のブランチ／PR の現在の先端を `git` / `gh` で確認する。対象 PR のリポジトリもここで確定する: `PR_REPO` にその `owner/name` を設定し、`MAIN_ROOT` を `pr-review` と同じ規則で解決する — `usaturn/maatlog-poc` なら親の toplevel `$TOPLEVEL`（親 checkout で `git rev-parse --show-toplevel`）、`usaturn/maatlog` なら検証済み public submodule の `$TOPLEVEL/public`（`git -C "$TOPLEVEL/public" remote get-url origin` が `.gitmodules` の `submodule.public.url` と一致すること）、それ以外は推測せず停止する。`upsert_pr_comment.py` などのスキル helper は親リポジトリにだけ存在するため、`$MAIN_ROOT` ではなく `$TOPLEVEL` から解決する。
3. **各指摘を現行 HEAD の「コミット済み」内容で検証する** — `git show <HEAD>:<path>` で読む。指摘された path の `REVIEWED_HEAD` にある committed source/test blob は検証根拠として許可する。挙動の指摘は、path と reviewed HEAD を別引数にした隔離 worktree で再現する:

   ```bash
   REPRO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX")"
   WT="$REPRO_ROOT/worktree"
   git -C "$MAIN_ROOT" worktree add --detach "$WT" "$REVIEWED_HEAD"
   test "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$MAIN_ROOT" rev-parse "$REVIEWED_HEAD^{commit}")"
   ```

   `WT` はメイン checkout 外の一意な一時 path とする。SHA が一致しなければその worktree を根拠に使わず停止する。再現しないものは「解消済み」に落とす。

   **検証対象の source/test を working tree のファイルから読まない。** 手元の作業ツリーには誰かの未コミット変更が入っていることがあり、「もう直っている」という誤判定を生む。実際にこの誤判定は起きている。これは検証根拠の制約であり、入力であるレビュー成果物の読み取りには適用しない。

   **閉じ込め:** このセッションが検証のために作る一時ファイル（HEAD メモ、ログ、pytest 出力、スクラッチ）はすべて `$REPRO_ROOT` 配下に置く。`${TMPDIR:-/tmp}` 直下へ `review-fix-planning-*`、`review-fix-planning-*.txt`、ハイフン区切り名（`review-fix-planning-wt` / `review-fix-planning-head` / `review-fix-planning-repro-root`）を作らない。そのルートに置いてよいのは `mktemp` が返したディレクトリだけである。

   **teardown（手順 3 の終わり）:** `$WT` を使う検証がすべて終わったら、このセッションの worktree を外し、続けて親ディレクトリを消す。Spec 作成や承認待ちまで残さない。あとで再検証が必要なら新しい `mktemp` を作る。消したディレクトリは再利用しない。

   ```bash
   git -C "$MAIN_ROOT" worktree remove --force "$WT" && rm -rf -- "$REPRO_ROOT"
   ```

   `worktree remove` が失敗したら親を `rm -rf` しない（git の worktree 登録が欠けたパスを指す）。停止し、`$WT` と `$REPRO_ROOT` の完全パスを報告する。残りは `.devcontainer/cleanup-workspace.bash` に委ねる。`worktree remove` 無しで `rm -rf` だけを組み立てない。
4. **下記「分類の仕様」に従って全指摘を 4 区分に振り分ける。**
5. **`superpowers:brainstorming` を呼ぶ** — 選別結果を持って経路（spike / bounded / architectural）を判定させ、その経路の作法で設計を詰める。
6. **Spec を書く** — 経路に関わらず必ず書く（下記「Spec は経路に関わらず必須」）。
7. **承認を得て停止する** — Spec を提示し、ユーザが明示的に「進めて」と言うまで実装に入らない。実装せず止まる場合の **作業終了前の PR 投稿** は任意であり、commit / push まで完了したターンのみ必須である。実装が終わったら **実装後** に従う。

## 実装後

この節は、ユーザが Spec を明示承認し、対応する項目を実装し終えたあとだけ実行する。計画は手順 7 で止まる。後続の依頼が、その承認済み実装を PR に反映するだけの場合もこの節を実行する。実装に入ったら、下記の手順の各段をタスクにする。

**PR への反映 — この順で行う:**

1. **実装に関連したテスト** だけを走らせる。Spec の各「対応する」項目に書いた検証方法、変更ファイルをカバーするテスト、今回の Fix で追加したテスト。
2. 失敗したら直す。commit しない。
3. `git fetch origin` し、レビュー対象ブランチの先端を確認する。関連テストが通ったら、レビュー対象ブランチ（既存 PR の head）へ commit する。`main` ではない。新しい `*-review-fixes` ブランチでもない。
4. そのブランチを **既存 PR** へ `git push` する。push の成功を確認する。reject されたら rebase または merge し、関連テストを再走してから再度 push する。新しい PR を開かない。`finishing-a-development-branch` のメニューを出さない。
5. 完了報告の前に **作業終了前の PR 投稿** を実行する。

レビュー対象ブランチに open な PR が無いなら、作らず停止して報告する。ユーザが作れと言うまで作らない。コメントの投稿もしない。

**この節が commit / push の常設指示である。** 二度目の「commit」「push」を待たない。「進めて」は実装の承認であり、この手順が PR への反映である。

**commit / push の条件にしないもの:** レビュー対象リポジトリの full verifier（`usaturn/maatlog` では `./scripts/ci/verify.sh full`、`usaturn/maatlog-poc` では `./scripts/ci/verify-devenv.sh`。既存 PR の CI がまだ走る）、スイート全体、`superpowers:verification-before-completion` のフルスイート、`superpowers:finishing-a-development-branch`。

例: Spec の検証が `uv run pytest tests/theme/test_rail.py` —— アプリケーションの変更なので、レビュー対象 PR は `usaturn/maatlog` の #142 で、`MAIN_ROOT` は検証済み `public/` checkout。そのファイルと、変更した CSS をカバーするテストが通る。`feature/issue-102-author-right-rail` に commit し、`git -C "$MAIN_ROOT" push origin HEAD` で公開 PR へ反映する。status comment の `PR_REPO` は `usaturn/maatlog`。先に `./scripts/ci/verify.sh full` は走らせない。`feature/issue-102-review-fixes` は開かない。push 後、同じ PR にレビュー状況・作業判断・作業結果のコメントを作成または更新する。

親の開発環境 PR も同じ規則が親経路で成立する: `PR_REPO=usaturn/maatlog-poc`、`MAIN_ROOT` は親の toplevel で、親の full verifier は `./scripts/ci/verify-devenv.sh` であり、これも反映の条件にしない。

## 作業終了前の PR 投稿

この節の目的は後続エージェント・レビュアーへの永続的な記録に限る。完了通知待ちの停止（stall）対策ではない。stall は監視側（Monitor / PID）の課題である。

コメントは単体で読めること。PR だけを読む読み手が Spec 無しで判断を理解できるように書く。

**commit / push まで完了したターンのみ必須である。** commit / push まで実装したターンは push 後に1回投稿する。承認待ちで止まるだけのターンの投稿は任意である。同じエージェントの既存コメントがあれば更新し、無ければ新規作成する。他エージェントのコメントは読んでよいが編集しない。

レビュー対象ブランチに open な PR が無い場合は投稿しない。PR を作ることもしない。チャットで報告して止まる。

**リポジトリ:** レビュー対象 PR を持つ `owner/name` を `PR_REPO` にする。ヘルパーは作業ディレクトリから推測しないため、PR 番号だけで別リポジトリへ投稿されることはない。

**モデル識別子:** ランタイムが提示する正確な識別子を `MODEL_NAME` にする。ファイル名や系列名から推測しない。取得できなければ投稿せず確認する。

**コメントは日本語で書く。** 次の3見出しだけをこの順で使う。Spec 全文は貼らない。早期停止では分かる範囲を書き、未実施の節は `未実施` とする。PR への反映のみの依頼でも、承認済み Spec の要旨をレビュー状況と作業判断にまとめる。再検証はしない。

```markdown
## review-fix-planning（<MODEL_NAME>）

対象 PR: #<N>（`<branch>`） / 現行 HEAD: `<sha>`

### レビュー状況
- 入力: `<review-dir>`（読んだファイルと各対象 HEAD）
- 分類: 解消済み N / 対応する N / 判断保留 N / 対応しない N

### 作業判断
- 対応する: 各 ID と (a)–(d) と一行
- 判断保留: あるなら一行。ユーザが選んだ結果
- 対応しない: 全件を ID と一行理由で記載する（件数要約のみにしない）
- 解消済み: 件数と代表根拠

### 作業結果
- このターン: 計画のみ | push 済み | 途中停止
- Spec: `<path>`（gitignore 対象でローカルにしか無い）または未作成
- commit / push: `<sha>` またはしていない
- 次: 承認待ち | 完了 | 停止理由
```

```bash
TOPLEVEL="$(git rev-parse --show-toplevel)"   # 親 checkout で実行する
HELPER="$TOPLEVEL/.agents/skills/review-fix-planning/scripts/upsert_pr_comment.py"
uv run --no-project python "$HELPER" --pr "$PR_NUMBER" --repo "$PR_REPO" --model-name "$MODEL_NAME" <<EOF
## review-fix-planning（$MODEL_NAME）

対象 PR: #$PR_NUMBER（\`$HEAD_BRANCH\`） / 現行 HEAD: \`$HEAD_SHA\`

### レビュー状況
...
### 作業判断
...
### 作業結果
...
EOF
```

ヘルパーは `<!-- review-fix-planning:agent:<sanitized> -->` を付与し、そのマーカーを持つコメントだけを更新する。`gh pr comment --edit-last` は使わない。同じ GitHub アカウントを共有する別エージェントのコメントを上書きしてしまう。ヘルパーが失敗したら stderr を報告して止まる。代替の `gh` 呼び出しを組み立てない。自エージェントのマーカーを持つコメントが複数ある場合も停止する。

## 分類の仕様

全指摘をこの 4 区分のいずれかに置き、区分ごとの件数を出す。どの指摘もいずれか 1 つに属する。

| 区分 | ここに入れてよいもの |
|---|---|
| **解消済み** | 現行 HEAD のコードで検証し、再現しないと確認できたもの。根拠（コミット・該当行）を 1 行添える |
| **対応する** | 次の 4 つのいずれかを満たすものだけ:<br>(a) 現行 HEAD で再現を確認した誤動作<br>(b) 現行 HEAD で事実誤認と確認できた記述（コード内コメント・ドキュメント）<br>(c) 理由なく削除された回帰ガードの復元<br>(d) ユーザがその指摘を名指しで依頼した |
| **判断保留** | 上記を満たさないが、**修正が数行で済み潜在バグを消す**もの。これに限る。1 行で提示してユーザに選ばせる |
| **対応しない** | それ以外すべて。理由を 1 行書く |

**「対応しない」が既定である。** (a)〜(d) を満たさないものは全てここに入る。ドキュメント追記もテスト追加も対応である — 軽いから足しておく、をしない。

既定で「対応しない」に入る典型:

- **仕様・設計の是非**（「どちらの挙動が正しいか」）— 判断保留にしてユーザに問わない。「対応しない」に置き、論点を Spec に 1 行残す
- **第三者テーマ・外部利用者の互換性のみに影響するもの** — 公式の経路が一貫していれば対応しない
- 将来の保険、性能の過剰近似、Info 級の記載漏れ

リポジトリの方針ファイル（CLAUDE.md 等）が既に決着させている論点は「対応しない」に置き、その方針を根拠として引く。

## Spec は経路に関わらず必須

`superpowers:brainstorming` は bounded / spike 経路では Spec 不要と書いているが、**このスキルではユーザ指示が優先し、3 経路すべてで Spec を書く。**

- 配置: CLAUDE.md の規定に従う（本リポジトリでは `$TOPLEVEL/docs_draft/superpowers/` — 常に親側。`docs_draft/` は親でだけ gitignore 対象なので、`MAIN_ROOT` が `public/` のとき `$MAIN_ROOT` 配下へ置いてはならない）
- 命名: `YYYY-MM-DD-<topic>-review-fixes-design.md`
- 必須の中身:
  - 全指摘の一覧と 4 区分の振り分け（1 件も落とさない）
  - 「解消済み」「対応しない」それぞれの根拠 1 行
  - 「対応する」項目ごとの修正方針と検証方法
  - brainstorming が判定した経路名

## スコープ

解決したレビューディレクトリと、そのレビューが対象とするブランチ／PR だけを扱う。

- **他の worktree やブランチの未コミット差分を読みに行かない。** 見つけても計画に取り込まない
- レビューに挙がっていない問題を新たに探しに行かない
- 実装は承認後。計画フェーズでプロダクトコードを編集しない
- 実装後はレビュー対象の既存 PR に載せる。第二の PR を開かない
- PR への反映後は、レビュー状況・作業判断・作業結果をレビュー対象の既存 PR へ投稿する。実装せず止まるターンの投稿は任意である。第二の PR を開かない

## 合理化とその実態

| 言い訳 | 実態 |
|---|---|
| 「bounded だから Spec は要らない」 | ユーザ指示がスキルに優先する。3 経路すべてで書く |
| 「計画を全文提示したので承認は不要」 | 提示は承認ではない。明示的な「進めて」を待つ |
| 「ドキュメント 1 行なら過剰対応ではない」 | ドキュメントも対応。(a)〜(d) を満たさなければ「対応しない」 |
| 「要設計判断だがテストを 1 本足すだけなら」 | テスト追加も対応。判断が要るなら判断を仰ぐ |
| 「別 worktree に既に差分があったので活かす」 | 誰の何か分からない差分は範囲外。指定された範囲だけを見る |
| 「4 モデルが指摘しているので当然対応する」 | 票数ではなく現行 HEAD での再現が根拠 |
| 「brainstorming は自分で設計できるので省く」 | 経路判定と承認ゲートを持つのは brainstorming 側 |
| 「working tree を見たら直っていたので解消済み」 | それは誰かの未コミット差分かもしれない。`git show <HEAD>:<path>` で確かめる |
| 「必須テンプレートの仕様を直せば根本解決する」 | 第三者互換の作り込み。方針ファイルが決着させているなら対応しない |
| 「仕様の是非なのでユーザに聞こう」 | 判断保留は潜在バグの数行修正だけ。仕様論点は「対応しない」＋ Spec に 1 行 |
| 「進めては実装許可であり commit/push の許可ではない」 | この節が commit/push の指示である。関連テストが通ったら PR へ反映する |
| 「関連テストでは足りない。CLAUDE.md は verify.sh full が入口」 | ローカルの commit / push 条件は実装に関連したテスト。full verify は既存 PR の CI |
| 「ユーザが commit と打つまで commit しない」 | このワークフローではこの節がその指示である |
| 「finishing-a-development-branch のメニューを出す」 | 出さない。既存 PR に push する |
| 「レビュー修正は別 PR。#144 がそうだった」 | レビュー対象の既存 PR に push する。`*-review-fixes` の追加 PR はしない |
| 「すでに review-fixes ブランチがある。捨てるのは無駄」 | サンクコスト。レビュー対象 PR の head ブランチに載せる |
| 「チャットに計画を書けば十分」 | PR への記録も反映作業の一部である。計画のみのターンの投稿は任意である |
| 「実装していないので投稿不要」 | 計画のみの投稿は任意である。commit / push まで完了したターンのみ必須である |
| 「push したのでコメントは不要」 | PR に結果を残すことも反映の一部である |
| 「--edit-last で十分」 | 同じ GitHub アカウントを共有する別エージェントのコメントを上書きする。自エージェントのマーカーを持つコメントだけを更新する |

## Red flags — 止まって手順に戻る

- Spec ファイルのパスを言えない
- 「対応する」に入れた項目の再現手順を言えない
- 解決した review directory 外から持ち込んだ finding / review artifact、または未コミットの source/test ファイルが検証根拠になっている（解決した review directory 内のレビュー成果物は追跡状態にかかわらず正規の入力である）
- ユーザの「進めて」を受け取らないまま実装を始めようとしている
- Fix / 対応する に置いた finding ごとに、(a)〜(d) のどれを満たすかと根拠を示せない
- 「解消済み」の根拠が working tree のファイルである
- 判断保留に仕様・設計の質問が入っている
- `./scripts/ci/verify.sh full` や `./scripts/ci/verify-devenv.sh` を commit/push の条件として走らせようとしている
- レビュー修正のために新しい PR を開こうとしている、または `*-review-fixes` ブランチへ push しようとしている
- `finishing-a-development-branch` のメニューを出そうとしている
- 実装に関連したテストが通ったあと、二度目の「commit」「push」を待っている
- 実装に関連したテストが失敗したまま commit しようとしている
- `${TMPDIR:-/tmp}` 直下へ `review-fix-planning-*` を書こうとしている
- `worktree remove` を飛ばして `rm -rf` だけしようとしている
- 手順 3 のあと `$REPRO_ROOT` を残そうとしている
- mktemp ではなくハイフン区切り名（`review-fix-planning-wt` / `-head` / `-repro-root`）を使おうとしている
- commit / push まで完了したターンなのに、レビュー対象に open な PR があるのに status comment を投稿せず終了しようとしている
- `gh pr comment --edit-last` を使おうとしている
- 他エージェントの PR コメントを編集しようとしている
- 自エージェントのマーカーが既にあるのに新規コメントを作ろうとしている
