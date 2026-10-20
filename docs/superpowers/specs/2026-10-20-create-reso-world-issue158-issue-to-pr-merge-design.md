# Issue #158: issue-to-pr に `--merge`（PR の作成後のレビュー修正ループ）を入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/158（親 #116、ボード `review-automation-board`、子のキー `issue-to-pr-merge`）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue158-issue-to-pr-merge.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-158-issue-to-pr-merge`（branch `feat/issue-158-issue-to-pr-merge`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #158` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #158`）まで行う。利用者の指示に `--merge` は無いので、PR の作成後のループとマージは行わない（ボードの D-21）。下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 予約: `refs/heads/agent-claims/issue-158`（SHA `9b42a2ca7751c08320be3d233fac979ba7bd63c3`、セッション `f0bbdf2e-c246-4e50-96c4-85b58921d9ab`、2026-10-20T03:26:06Z）。記録: https://github.com/usaturn/create-reso-world/issues/158#issuecomment-6282623751
- 基準: 移植先 `origin/main` の `d29c93c`。移植元 usaturn/agent-workspace の `a47b2065`（#116 の基準）。移植元の `main`（`6e7b16e`、2026-10-19T18:10Z）でも `.agents/skills/issue-to-pr/` は `a47b2065` と差分が無い（2026-10-20 に clone して確認）
- 方針: #116 の「着手するエージェントへの注意（利用者決定: 2026-10-18）」に従う。この子に関係するのは、`tools/workspace`・`projects.toml` を入れず、`resolve_issue.py` は #114・#157 の移植先の版を土台にすること、ループの中の判断（現行 HEAD で到達できる致命的な指摘だけを直す、三択の結論、修正後の自己レビューは最大 1 回）は review-fix-planning のまま変えないこと
- builder check（brainstorming の読み合わせ、2026-10-20、model sonnet）: 「重要な未確定事項は残っていない」。設計の前提（`resolve_issue.py`・`loop.py`・`finalize.py`・review-fix-planning の専用の worktree・README の「テスト」が review-fix-planning の検証を含むこと・ボードと #156 の決定）をリポジトリの実物と突き合わせ、食い違いは無かった。利用者に確かめる必要のある点は無い

## 意図

`/issue-to-pr <Issue> --merge [ループ用のオプション]` で、PR を作った後に PR 修正ループ（#156 の pr-review-fix-loop）を回し、修正不要と確かめられたら、マージと関連 Issue の更新まで進めるようにする。`resolve_issue.py` の `FUTURE_OPTIONS` による拒否を無くす（#116 の完了の条件 6）。`--merge` が無い run は今と同じく PR の作成で終わる。

## 確認した事実（2026-10-20）

- 先行の #156・#157 は `completed` で close。PR #193（`b65ef0c`）・#185（`d581f06`）は `main`（`d29c93c`）に含まれる。#158 に open PR・予約・worktree・branch は無かった
- 今の `resolve_issue.py` は `uv run --no-project` で動き、pydantic を使わない。`--implement` を受け付け（値は agent 名の形）、出力に `implement` を持つ。`FUTURE_OPTIONS`（`--merge`・`--max-cycles`・`--hold-action`・`--assign`・`--template`・`--config`・`--fresh-review`）は「#116 で入れる予定」で終了コード 2
- `loop.py` の `check-options` と `start` は、同じ定義のオプション（`--max-cycles`（int、既定 3）・`--assign`（append）・`--template`（既定は雛形）・`--config`）を受け付け、`start` だけが `--fresh-review` を持つ。`--hold-action` は無い（#156 の D-4。argparse が終了コード 2 で拒否する）。`check_options` は範囲（1〜10）、`--assign` の形（役割は `inspect`・`implement`・`self-review`・`fix-check` の各 1 回、`inspect` に `self` は不可、fix の役割は 1 担当）、設定の割り当て（`inspect` は runner の担当、codex の `inspect` の拒否、`run_roles.py` が拒否する fix の割り当て）を検査する。`--template`・`--config` は `loop.py` の cwd を基準に `resolve()` する
- 実環境（雛形と今の個人設定）で `loop.py check-options` を引数なしで実行すると `status: ok`。`assignments` は review の `inspect` が `pi-gpt`・`devin-swe`・`dsh-ccd`・`claude-opus`、fix は `implement` が `claude-opus`、`self-review`・`fix-check` が `self`
- `loop.py start` が扱う PR は、Git 操作の対象の checkout を `CODE_ROOT` なしで決められるものだけ（create-reso-world と、`external/resoloop` の usaturn/resoloop・orange3134/resoloop）。usaturn/resoloop-meshy などは終了コード 2（`arguments`）で止まる（#156 の D-3）
- `finalize.py` がマージしてよいのは usaturn/create-reso-world と usaturn/resoloop の、open で draft でない PR だけ（`MERGEABLE_REPOSITORIES`）。usaturn/resoloop は PR の checks の成功を確かめ、実行中なら `wait_for: ci` で返す。検証の記録（`--checks-file`）は `{"head", "commands"}` の 2 項目だけで、`commands` の各要素は `argv` と `exit_code`（0）
- review-fix-planning の結論 2 の手順 1 は、専用の worktree で検証し、実際のコマンドと終了コードを検証の記録に残す。専用の worktree は、PR の head ブランチを checkout した clean な worktree（HEAD が PR の head）があればそれを使う。issue-to-pr の feature worktree はこの条件に当たる
- pr-review-fix-loop の SKILL.md は `disable-model-invocation: true`。「issue-to-pr が利用者の明示した `--merge`（#158 で入る）で PR を作った後に呼ぶ」「issue-to-pr の `--merge` は、worktree を作る前に `check-options` を呼ぶ」と書いてある
- 移植元の issue-to-pr の `--merge`: 1 章の節、2 章の `check-options`、4 章の 6（最終の全体レビューを行わず、ループの 1 サイクル目で代える）、5 章の検証の記録・draft にしない・CI を待たない・予約の解放の時点・「`--merge` のとき: PR の作成後のループ」の節と結果の表。`resolve_issue.py` は `--hold-action` をループ用のオプションに含め、`--fresh-review` を理由付きで拒否し、`--template`・`--config` を起動したときの cwd を基準に絶対パスにする
- 関係する open の Issue: #187（runner の監査が並行作業と消えた worktree の登録で止まる。ループの `run_roles.py` も対象）、#196（結論 2 の検証の後に `main` が進むと、`finalize.py` が検証していない組み合わせをマージする）。どちらも #158 の範囲外

## 設計

### 入力の解析（`resolve_issue.py`）

利用者の引数の語を左から読み、Issue の参照・`--implement`・`--merge`・ループ用のオプションに分ける。

| 語 | 扱い |
| --- | --- |
| `--merge` | 値を取らない（`--merge=…` は拒否）。1 回だけ。書く位置は問わない |
| `--max-cycles N` | ループ用。値は ASCII の数字だけ（範囲は `check-options` が確かめる） |
| `--assign ROLE=AGENT[,AGENT]` | ループ用。複数可。ROLE は英小文字と `-`、AGENT は agent 名の形（`[A-Za-z0-9][A-Za-z0-9_.-]*`）をカンマでつないだもの（役割の名前・担当の存在・数は `check-options` が確かめる） |
| `--template PATH`・`--config PATH` | ループ用。空でなく、制御文字を含まない。`~` を展開し、起動したときの cwd を基準に絶対パスにする |
| `--implement AGENT` | 今のまま。ループ用のオプションに入れない |
| `--hold-action` | 理由付きで拒否（このリポジトリの review-fix-planning に判断保留が無く、ループも受け付けない） |
| `--fresh-review` | 理由付きで拒否（作ったばかりの PR には再利用するレビューが無い） |
| ほかの `-` で始まる語 | 未知のオプションとして拒否 |

- 値は次の語か `--opt=value` で書ける。次の語が無い・`-` で始まる・空の値は拒否する
- ループ用のオプションは `--merge` と一緒のときだけ受け付ける（位置は `--merge` の前でも後でもよい）
- 出力の JSON に `merge` を足す。`--merge` が無ければ `null`、あれば `{"loop_args": [...]}`。`loop_args` は利用者が書いた順のループ用のオプションで、`--opt=value` は 2 語に分け、パスは絶対パスにする。既定値は足さない。繰り返しも書いた順のまま渡す（`--max-cycles` は argparse で後の値が効き、`--assign` の同じ役割の重複は `check-options` が拒否する）
- 拒否はどれも、Issue を読む前（`gh` を呼ぶ前）に終了コード 2 と `issue-to-pr:` で始まる理由で止まる。`FUTURE_OPTIONS` は無くす

### worktree の前の検査（SKILL.md の 2 章）

1. `resolve_issue.py`（今のまま `--no-project`）
2. `merge` が `null` でなければ、`PARENT_ROOT` の `loop.py check-options <loop_args の各要素>` を `uv run --project "$PARENT_ROOT" --locked` で実行する。終了コード 0 なら `options`・`assignments` を Spec の決定記録に写し、2 なら `reason`（argparse の拒否は stderr）を伝えて止まる
3. `implement_task.py check`（今のまま。ループの `--template`・`--config`・`--assign implement=` は使わない）
4. `TARGET_REPO` が usaturn/resoloop-meshy で `merge` があれば止まる（ループも `finalize.py` も扱えない）
5. 既存の open PR で止まるときは、`--merge` があっても既存の PR をループに乗せない。続けるかは利用者が決める（ループは `/pr-review-fix-loop <PR の URL>`）
6. 統合用の branch の指定は、今と同じく止まる（Issue の制約）

### PR の作成まで（4・5 章）

- 4 章は変えない。`--merge` のときも、実装スキルの最後のブランチ全体のレビューを行う（D-158-9）
- Plan の実行予算に、ループの段階（目安はサイクルの上限 ×（レビューの期限 45 分＋計画・修正））を含める
- 検証の記録: `--merge` のときは、最後の commit の後に 2 章の表の入口で検証し、検証した HEAD、その時点の `git status --porcelain` が空だったこと、各コマンドの argv と終了コード、ログの完全パスを `PARENT_ROOT/tmp/agents/` のセッションディレクトリに残す。`finalize.py` の `--checks-file` の形のファイルも同じ場所に作る。形は書き写さず、review-fix-planning の `references/execution.md` の 3 章を参照する（`d29c93c` では `head`・`commands` の 2 項目。open の PR #203（#196）が `base` を足す）
- PR は draft にしない（`finalize.py` は draft を拒否する）
- usaturn/resoloop の PR でも、`--merge` のときは CI を待たずにループへ進む（マージの前に `finalize.py` が CI の成功を確かめ、実行中なら `wait_for: ci` で待つ）
- ボードの子の予約は、ループの `finish` の後、その結果を子 Issue に書いてから解放する

### PR の作成後のループ（5 章の新しい節「`--merge` のとき: PR の作成後のループ」）

1. Herdr のタスクを `PR #<番号> レビュー・マージ` に変える（ペインの名前は `start` が `PR#<番号>` に変える）
2. `PARENT_ROOT` の pr-review-fix-loop の SKILL.md をファイルとして読む（Skill ツールでは起動できない）。このセッションが司令塔である
3. `PARENT_ROOT` の `loop.py start "<コードの PR の URL>" --controller-model <正確なモデル ID> --controller-runtime <ランタイム> <loop_args の各要素>`。feature worktree の `loop.py` は使わない。文書の PR（`TARGET_REPO` が create-reso-world でないとき）はループに乗せず、マージしない
4. サイクル・終わり方・止まったとき・監視は、pr-review-fix-loop の SKILL.md に従う
5. 検証の記録の再利用: 1 サイクル目で修正不要となり、サイクルの HEAD が記録した HEAD と同じなら、review-fix-planning の結論 2 の手順 1 の検証の記録として使ってよい。条件は、同じ HEAD、検証のときに未 commit の変更が無い、すべての終了コードが 0、ログが残っていること。確かめられなければ計画の中で検証し直す。結論 2 の手順 2（base が進んだときの merge の検証）は省かない
6. 結果の表（移植元と同じ 4 行: `no_fix_needed`・`fixes_pushed`（`cycle_limit`）・`stopped`・ループのエラー）で報告し、run ID、`<review_dir>/loop/<run_id>/` の完全パス、サイクルごとの結果、ループの段階の所要時間を書く

### SKILL.md の変更箇所

| 箇所 | 変更 |
| --- | --- |
| frontmatter の `argument-hint` | `--merge` とループ用のオプションを足す |
| 1 章の冒頭の段落 | 「マージはしない」を、`--merge` のときのループの `finalize.py` を除く、に変える |
| 1 章の「オプションは `--implement` だけ」の段落 | 受け付けるオプションと、拒否されたら止まることに書き換える |
| 1 章の `### --merge`（新しい節） | 有効な条件、ループ用のオプション、`--hold-action`・`--fresh-review`、`--assign implement=` と `--implement` の区別、使える `TARGET_REPO`、実行予算、`--merge` の無い run |
| 2 章の 3 | `INPUT` の例、出力の `merge`、`check-options` |
| 2 章の 5・6 | resoloop-meshy での停止、既存の PR をループに乗せない |
| 5 章 | 検証の記録、draft にしない、CI を待たない、マージの例外、予約の解放の時点、完了の報告 |
| 5 章の `### --merge のとき: PR の作成後のループ`（新しい節） | 上の 1〜6 |
| 停止時の報告 | `check-options` の終了コード 2、resoloop-meshy、ループの停止・エラーと報告する項目 |
| ランタイムごとの違い | `--merge` の書き方、`--controller-model`・`--controller-runtime` |

4 章（#157 の節を含む）、2 章の表、`--implement` の節は変えない。

### テスト

`tests/test_resolve_issue.py` を、`resolve_issue.py` を実際に起動して確かめる形のまま直す。

- 既存の成功の場合の出力に `"merge": None` を足す。`FUTURE_OPTIONS` の拒否の検査（`#116` の照合）は、受け付けと新しい拒否の検査に置き換える
- `--merge` とループ用のオプションが書いた順で `loop_args` に入る（`--opt=value` の分割、繰り返し、`--merge` の前に書いたループ用のオプション、範囲外の数も形が合えば通す）
- `--template`・`--config` が起動したときの cwd と `~` から絶対パスになる
- Issue を読む前の拒否（`gh` を呼ばない）: `--merge` の無いループ用のオプション、`--merge` の重複・値、`--hold-action`・`--fresh-review`、値の欠落・空・形の誤り、制御文字を含むパス、未知のオプション、Issue の数の誤り
- `resolve_issue.py` → 本物の `loop.py check-options` の 2 段（一時の雛形）: 両方を通る・1 段目で止まる・2 段目で止まる（範囲外の `--max-cycles`、設定に無い担当、codex の `inspect`）
- `--implement` はループ用のオプションと別に返る（`--merge` の後ろに書いた場合、`--assign implement=` を含む）。`resolve_issue.py` → `implement_task.py check` の 2 段に `--merge` を含む場合を足す

### 評価（evals）

`evals/scenarios.json` の (b)・(w)（今は「`--merge` は止まる」を期待）を新しい振る舞いに直し、`--merge` の場面を足す。変更前（`origin/main` の SKILL.md）と変更後で、Claude Code の Agent ツールのサブエージェント（model `sonnet`）に各 3 回答えさせ、`evals/validation.md` に記録する（writing-skills の振る舞いの比較。#157 と同じ方法）。

### 実環境での確認

本物の Issue と実際の雛形・個人設定で、`resolve_issue.py -- "#158 --merge"`（読み取りだけ）→ `loop.py check-options`（PR・ロック・GitHub に触れない）の 2 段を実行し、結果を記録する。PR の作成後のループとマージは、利用者が `--merge` を書いて指示した run だけで行う（Issue の受け入れ、ボードの D-21）。この run では行わない。

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-158-1 `resolve_issue.py` は移植先の版に足す**
  - 選択: #114・#157 の版（`--no-project`、pydantic を使わない、対象の 3 リポジトリを固定値で持つ）に、`--merge` とループ用のオプションの解析を足す
  - 別案: 移植元の版（pydantic、`tools.workspace`、`<name>#N`）を写す
  - 理由: #116 の注意書き（`tools/workspace` を入れない）とボードの D-5。#157 の D-157-3 と同じ
- **D-158-2 受け付けるループ用のオプションは `check-options` と同じ 4 つ**
  - 選択: `--max-cycles`・`--assign`・`--template`・`--config`。`--hold-action` と `--fresh-review` は理由付きで拒否する
  - 別案: (a) `--hold-action` をループに渡し、argparse の拒否で止める、(b) `--hold-action` を黙って外す、(c) 移植元のとおりループ用のオプションとして受け付ける
  - 理由: #156 の D-4（loop は `--hold-action` を持たない。判断保留が無いので、受け付けると致命的でない指摘まで直るように見える）と #156 からの申し送り（外すか扱いを決める）。(a) は理由が伝わらない（argparse の usage だけ）。(b) は「利用者が書いたものだけを渡す」に反し、利用者の指定を黙って落とす。`--fresh-review` は移植元と同じ理由（作ったばかりの PR に再利用するレビューが無い）
  - 停止条件: 拒否されたら止まって理由を伝える。オプションを外して続けない
- **D-158-3 値の形は `resolve_issue.py` が確かめ、意味は `check-options` が確かめる**
  - 選択: 上の表の形（数字、`ROLE=AGENT[,AGENT]`、制御文字を含まないパス）を Issue を読む前に確かめる。範囲・役割の名前・担当の存在と数・設定による拒否は `check-options`（`start` と同じ関数）に任せる
  - 別案: (a) 移植元のとおり空の値だけを拒否する、(b) 意味まで `resolve_issue.py` で確かめる
  - 理由: 値は次のコマンド（`check-options`・`start`）の引数になる。`--max-cycles`・`--assign` は、#157 の D-157-3（`--implement` の値を agent 名の形に限り、シェルの特殊文字を含む値を通さない）と同じ扱いにする。形は runner と loop の規則の範囲なので、正しい値を拒まない。パスは形を決められないので、制御文字だけを拒み、シェルの特殊文字（`'`・`$`・`` ` `` など）は通す。SKILL.md は各要素を 1 つの引数として渡すと定める（最後の全体レビューの Minor 1。入力は利用者自身のもので、権限の境界はまたがない）。(b) は `start` と同じ関数で検査する仕組み（#156）を二重にし、食い違いの元になる
- **D-158-4 出力は `merge.loop_args`**
  - 選択: `merge` は `null` か `{"loop_args": [...]}`。書いた順、`--opt=value` は 2 語、パスは絶対パス、既定値を足さない
  - 別案: オプションごとの辞書にする
  - 理由: #158 の本文の「決める: `merge.loop_args`（利用者が書いた順のループ用のオプション）」と移植元の形。辞書にすると順序と繰り返しの情報が落ち、`start` に渡す列を組み立て直すことになる
- **D-158-5 パスは起動したときの cwd を基準に絶対パスにする**
  - 選択: `~` を展開し、`resolve_issue.py` を起動した cwd（利用者が `/issue-to-pr` を書いた checkout）を基準に絶対パスにする
  - 別案: 書かれたまま渡す
  - 理由: `check-options` と `start` は `PARENT_ROOT` の `loop.py` を別の時点・別の cwd で起動しうるので、相対パスの意味が変わる。スラッシュコマンドの引数はシェルを通らないので、`~` も helper が展開する（移植元と同じ）
- **D-158-6 `check-options` は worktree の前に `PARENT_ROOT` の `loop.py` で実行する**
  - 選択: 2 章の 3 で、`resolve_issue.py` の後、`implement_task.py check` の前に、`uv run --project "$PARENT_ROOT" --locked python "$PARENT_ROOT/.agents/skills/pr-review-fix-loop/scripts/loop.py" check-options <loop_args の各要素>`
  - 別案: PR の作成の後、`start` で初めて検査する
  - 理由: 設定の誤りで、実装と PR の作成の後にループが始まらない事態を防ぐ（移植元・#156 の `check-options` の目的）。`implement_task.py` と同じく `PARENT_ROOT` の project で動かす（ボードの D-7）
- **D-158-7 usaturn/resoloop-meshy の `--merge` は worktree の前に止まる**
  - 選択: `TARGET_REPO` が usaturn/resoloop-meshy で `--merge` があれば、2 章の 5 で止まり、理由（ループが `CODE_ROOT` 無しで checkout を決められない、`finalize.py` がマージしてよい範囲の外）を伝える
  - 別案: (a) `--merge` を適用せずに続ける（移植元の統合用の branch の扱い）、(b) PR を作ってから `start` の拒否で止まる
  - 理由: (a) は利用者が明示したマージの指示を黙って変える。この版は未対応の指定（統合用の branch）で止まる方針で、それに合わせる。(b) は実装と PR を作った後に止まり、作業が無駄になる
  - 停止条件: 止まって理由を伝え、`--merge` を外して指示し直せることを案内する
- **D-158-8 既存の open PR は `--merge` があってもループに乗せない**
  - 選択: 今の「止まって報告」に、既存の PR をループに乗せないこと、ループで続けるかは利用者が `/pr-review-fix-loop <PR の URL>` で決めることを足す
  - 別案: 既存の PR でループを始める
  - 理由: 作った人が分からない PR を、マージまで進めるループに乗せない（移植元と同じ）。案内に PR の URL を使うのは今の規則と同じ
- **D-158-9 `--merge` でも最後のブランチ全体のレビューを省かない**
  - 選択: 4 章を変えず、実装スキルの最後のブランチ全体のレビューを行ってから PR を作る
  - 別案: 移植元のとおり、ループの 1 サイクル目で代え、minor の指摘を PR 本文に並べる
  - 理由: #158 の「変えてよいもの」に 4 章が無い。create-reso-world の PR では、結論 1 の後のサイクルで同じ HEAD の再利用が働かず、修正のたびに全レビュアーを起動し直す（#156 の D-19）。PR の前に 1 つのサブエージェントで欠陥を見つけるほうが、レビュアーの起動の回数を減らせる
- **D-158-10 検証の記録を残し、1 サイクル目の修正不要に限って再利用する**
  - 選択: 「設計」の「検証の記録」と、ループの節の 5 のとおり
  - 別案: (a) 再利用しない（結論 2 で毎回検証し直す）、(b) 移植元の文をそのまま写す
  - 理由: 記録した検証は、review-fix-planning が専用の worktree として使う feature worktree で、同じ HEAD に対して、同じ入口（README の「テスト」は review-fix-planning の環境の変更の検証を含む）で実行したもので、結論 2 の手順 1 の根拠になる。再利用の条件を明記し、手順 2（base が進んだときの merge の検証）は省かないことも書く。(b) は移植元の置き場所と記録の形が移植先と違う。記録の形は書き写さず、review-fix-planning の `execution.md` の 3 章を参照する（open の PR #203 が記録に `base` を足し、`finalize.py` が 3 項目を求める。#158 とはファイルが重ならないので、書き写すと #203 が先にマージされたときに黙って誤りになる）
- **D-158-11 `--merge` のときは PR を draft にしない**
  - 選択: 5 章に明記する
  - 理由: `finalize.py` が draft を拒否する。#158 の本文の制約
- **D-158-12 `--merge` のときは CI を待たずにループへ進む**
  - 選択: usaturn/resoloop の PR でも、PR の作成後に CI を待たない。マージの前に `finalize.py` が CI の成功を確かめる
  - 別案: 今のとおり CI の成功を待ってからループを始める
  - 理由: レビューと CI を並行に進められる。CI の失敗は、review-fix-planning が PR の変更による致命的な指摘として結論 1 で直す。`--merge` の無い run は今のまま CI の成功を待つ
- **D-158-13 ループは `PARENT_ROOT` の `loop.py` で始め、pr-review-fix-loop の SKILL.md をファイルとして読む**
  - 選択: 「設計」のループの節の 1〜4
  - 別案: feature worktree の `loop.py` を使う、Skill ツールで pr-review-fix-loop を起動する
  - 理由: `loop.py` は置き場所から `tool_root` を決め、レビュアーはそこのスキルを読む。PR で変えているスキル・helper でレビューさせない（移植元、#156 の SKILL.md）。pr-review-fix-loop は `disable-model-invocation: true` で、Skill ツールでは起動できない
  - 委任指示: `--controller-model` は現在提示されている正確なモデル ID、`--controller-runtime` は Claude Code なら `claude-code`、Pi なら `pi`
- **D-158-14 文書の PR はループに乗せない**
  - 選択: `TARGET_REPO` が usaturn/resoloop のとき、ループに乗せるのはコードの PR だけ。create-reso-world の文書の PR はマージせず、URL と状態を報告する
  - 別案: 文書の PR も別のループで回す、`finalize.py` でマージする
  - 理由: ループと `finalize.py` は 1 つの PR を扱う。文書だけの PR に全レビュアーを起動する費用に見合わない。マージは利用者が行う
- **D-158-15 予約はループの `finish` の後に解放する**
  - 選択: ボードの子で `--merge` のときは、ループの `finish` の後、その結果を子 Issue に書いてから予約を解放する
  - 別案: 今のとおり PR の作成の後に解放する
  - 理由: ループが修正を push している間に、別のセッションが同じ子を予約して作業を始めるのを防ぐ（移植元と同じ）
- **D-158-16 ループの結果は移植元の表で報告する**
  - 選択: `no_fix_needed`（マージした。関連 Issue は finalize の結果の state）、`fixes_pushed`（`cycle_limit`。未完了・未マージ。続けるなら `/pr-review-fix-loop <PR の URL>`）、`stopped`（`stop_reason`。`merged: true` なら分けて書く）、ループのエラー（`stage`・`reason`・`next`・残した資源の完全パス）
  - 理由: 移植元と同じ。pr-review-fix-loop の「最終報告」と食い違わない
- **D-158-17 `--merge` は利用者が書いたときだけ有効**
  - 選択: 利用者のメッセージ（スラッシュコマンドの引数を含む）に `--merge` という語があるときだけ。自然文の「マージまで」は扱わない。モデルが自分でスキルを選んだ run で補わない
  - 理由: #158 の本文の制約。マージは取り消せない外部操作
- **D-158-18 `--merge` の無い run は変えない**
  - 選択: PR の作成で終わり、最終報告の 1 行の案内（`/pr-review <PR の URL>`）も今のまま
  - 別案: 移植元のとおり `/pr-review-fix-loop <PR>` を案内する
  - 理由: #158 の受け入れ（`--merge` が無い run は今と同じ）。ループはマージまで進むので、`--merge` を書かなかった利用者にマージを伴う入口を勧めない
- **D-158-19 テストは「テストの採用基準」に合うものだけ**
  - 選択: 「設計」の「テスト」のとおり。`resolve_issue.py` と `loop.py check-options` を実際に起動して確かめる。拒否の理由の文言は照合しない（拒否したオプションの名前が理由に出ることだけを確かめる）
  - 別案: 移植元のテストを写す
  - 理由: 移植元のテストは `projects.toml`・`<name>#N` を前提にしている。`AGENTS.md` の作らない型（文書の文言の照合）を避ける
- **D-158-20 振る舞いの比較は Claude Code の sonnet で行う**
  - 選択: #157 と同じ方法（対照は `origin/main` の SKILL.md、比較は変更後、各 3 回）
  - 理由: 移植先の既存の評価（#114・#139・#157）と同じ
- **D-158-21 この Issue の実装の方式は inline（`superpowers:executing-plans`）**
  - 選択: 自分で実装する。サブエージェントは、この Spec の builder check、振る舞いの比較、最後のブランチ全体のレビューにだけ使う
  - 別案: `superpowers:subagent-driven-development`
  - 理由: Task は `resolve_issue.py` → 評価の対照 → SKILL.md → 評価の比較 → 統合と 1 本の流れでつながり、同じファイル（SKILL.md・scenarios.json）を順に変える。移植元・#156・#157 の文脈がこのセッションにあり、子に渡しきれない（issue-to-pr の 4 章の 4 の表の条件）。`implement_task.py check` は `self: true`（雛形の既定の適用）
- **D-158-22 実機のループは行わない**
  - 選択: この run では PR の作成後のループとマージを行わない。実環境での確認は、worktree の前の 2 段（本物の Issue・雛形・個人設定）に限る
  - 別案: 使い捨ての PR でループを回す
  - 理由: 利用者の指示に `--merge` が無い（ボードの D-21、#158 の受け入れの「利用者の指示があるときだけ」）。ループ自体の実機の確認は #156 で済んでいる
  - 停止条件: なし（未実施として PR と #158 に書く）

## 最後の全体レビューと修正（2026-10-20）

最後のブランチ全体のレビュー（`superpowers:executing-plans` の最後のレビュー、Claude Code の opus、`d29c93c..c5de6cb`）の結論は「修正すれば可」。Critical は無い。指摘を影響の大きさで格付けし直し、次のとおり扱った（エージェントの判断）。

| 指摘 | 格付け | 扱い |
| --- | --- | --- |
| Important 1: 「Skill ツールで呼ぶときは `--merge` を付けない」と 1 章の「利用者が書いたときだけ有効」が食い違う | Important | 直した。Claude Code の項を、利用者のメッセージから `INPUT` を切り出して args に渡し、書かれていないものは足さない、に変えた |
| Minor 2: ループが終わるまで feature worktree を clean に保つ指示が無い | Important に格上げ（review-fix-planning が結論 3 で止まり、レビュアーの 1 サイクルを無駄にする） | 直した。ループの節の冒頭に、review-fix-planning の手順の外で feature worktree を変えないこと、記録の置き場所を書いた |
| Minor 4: ループの節が pr-review-fix-loop の一部の節だけに従うように読め、最終報告の項目が足りない | Important に格上げ（利用者が受け取る報告が欠け、従う範囲があいまい） | 直した。pr-review-fix-loop の SKILL.md 全体に従い、報告はその「最終報告」の項目に結果の区分を加える、とした |
| Minor 1: パスの値がシェルの特殊文字を通す。D-158-3 の理由の記述が事実と違う | Minor（入力は利用者自身のもので、権限の境界をまたがない） | 持ち越し（PR に書く）。D-158-3 の理由の記述は実態に合わせて直した |
| Minor 3: 検証の後に commit を足したときの記録の取り直しが書かれていない | Minor（同じ HEAD の条件で再利用されないだけで、安全側に止まる） | 持ち越し（PR に書く） |

直した 3 件は、評価の場面 (mj)・(mk)・(ml) を足し、直す前（`c5de6cb`）に 3 回取って外れることを確かめ（(mj) は 3 回とも食い違いを指摘、(mk)・(ml) は 0/3）、直した後の 3 回で 3/3 を確かめた（`evals/validation.md`）。

あわせて、5 章の検証の記録の形を書き写さず、review-fix-planning の `references/execution.md` の 3 章を参照する文面に変えた。open の PR #203（#196）が記録に `base` を足し、`finalize.py` が 3 項目を求めるため（D-158-10）。

## 実施した検証（2026-10-20）

- 正式な検証（HEAD `e6405ef`、作業ツリーは clean）: `bash .devcontainer/run-tests.bash` PASS 33、`bash scripts/check-layout.sh` PASS、`uv run pytest tests/skills .agents/skills .agents/scripts tools` 3445 passed・1 skipped（skip は stale-git-lock-recovery の、他の git プロセスを除外できないときに skip する設計のテスト）。どれも終了コード 0。ベースライン（`d29c93c`）は 3409 passed
- 実環境の 2 段（本物の #158）、TDD の RED・GREEN、評価（対照・比較・取り直し・最後の全体レビューの修正の RED・GREEN）の詳細は、Plan の「完了」と `evals/validation.md`
- 受け入れ条件 8（実機のループ）は未実施。利用者の指示に `--merge` が無い

## Plan の実装の担当

`implement_task.py check`（`--implement` なし）の結果: `assignment` は `agents: ["self"]`・`fallback: []`、`self: true`。雛形 `.devcontainer/agent-runner.toml` の既定の適用で、個人設定に `workflows.issue` は無い（利用者の指定ではない）。

## 受け入れ条件

1. `uv run pytest .agents/skills/issue-to-pr` が通る
2. `--merge` が無い run は今と同じ: 出力の `merge` が `null`、ほかの項目は変わらない、SKILL.md の `--merge` の無い流れ（PR の作成で終わる、`/pr-review` の案内）が変わらない
3. `resolve_issue.py` が `--merge` とループ用のオプションを受け付け、`FUTURE_OPTIONS` が無い。`--hold-action`・`--fresh-review`・`--merge` の無いループ用のオプションは理由付きで止まる
4. `resolve_issue.py` → `loop.py check-options` の 2 段が、テストと実環境（`#158 --merge`）で通る
5. SKILL.md が `--merge` の流れ（2 章の検査、検証の記録、draft にしない、CI、ループの起動と結果の報告、予約の解放、停止）を述べ、pr-review-fix-loop の SKILL.md・review-fix-planning の結論 2 と食い違わない
6. SKILL.md の振る舞いの比較（変更前・変更後）を `evals/validation.md` に記録する
7. `uv run pytest tests/skills .agents/skills .agents/scripts tools`、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh` が通る
8. 実機のループ（PR の作成 → ループ → 結果の報告）は、利用者が `--merge` を書いて指示した run で行う。この run では未実施として PR と #158 に書く

## 防御範囲

- 受け付ける入力: `#N --merge`、`--merge #N`、`#N --merge --max-cycles 2`、`#N --merge --max-cycles=2`、`#N --max-cycles 2 --merge`、`#N --merge --assign inspect=claude-opus,devin-swe --assign implement=self`、`#N --merge --template sub/a.toml --config '~/c d.toml'`、`#N --implement codex --merge`、`#N --merge --max-cycles 2 --implement codex`、`#N --merge --max-cycles 0`（形は合う。`check-options` が止める）
- Issue を読む前に終了コード 2: `#N --max-cycles 2`（`--merge` 無し）、`#N --merge --merge`、`#N --merge=yes`、`#N --merge --hold-action skip`、`#N --merge --fresh-review`、`#N --merge --max-cycles`、`#N --merge --max-cycles x`、`#N --merge --max-cycles -1`、`#N --merge --assign inspect`、`#N --merge --assign 'inspect=a;b'`、`#N --merge --template`、`#N --merge --template=`、`#N --merge --template --config x`、改行を含むパス、`#N --merge --foo`、`#N extra --merge`、`--merge`（Issue 無し）
- `check-options` の終了コード 2: 範囲外の `--max-cycles`、設定に無い担当、codex の `inspect`、存在しない `--template`
- 対象にしない: PR の作成後のループの実機、`finalize.py` によるマージ（この run では行わない）、統合用の branch（今と同じく止まる）、usaturn/resoloop-meshy の `--merge`（止まる）

## 範囲外

- `implement_task.py` とそのテスト（#157）、`.agents/skills/pr-review-fix-loop/`（#156）、`.agents/skills/review-fix-planning/`（#155）、`tools/`
- #187（runner の監査が並行作業・消えた worktree の登録で止まる）、#196（結論 2 の検証の後に `main` が進む）
- pr-review-fix-loop の SKILL.md の「（#158 で入る）」の記述の更新（#156 の担当の範囲。#116 に申し送る）
- 親 #116 の実行マップ・公開台帳の更新（調整役）

## 既知の制限（PR に書く）

- `--merge` のループは、runner の監査（#187）で、同じ親の checkout で並行作業があると `run_roles.py` の担当の結果を受け取れず止まることがある。`finalize.py` は検証の後に `main` が進んだことを確かめない（#196）
- usaturn/resoloop の `--merge` では、create-reso-world の文書の PR はループに乗らず、マージは利用者が行う
- create-reso-world の PR では、結論 1 の後のサイクルで同じ HEAD の再利用が働かず、レビュアーを起動し直す（#156 の D-19）

## 実装者に任せること

- `resolve_issue.py` の内部の構成と拒否の文面（拒否の条件と出力の形は上のとおり）
- テストの関数の分け方と名前
- SKILL.md の文面の細部（上の変更箇所と決定に従う）
- 評価の指示文の文面（場面と期待は `scenarios.json` に書く）
