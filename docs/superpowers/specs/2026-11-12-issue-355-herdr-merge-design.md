# issue-to-pr の Herdr ペイン終了状態と --merge の改良（#355 herdr-merge）設計

- 状態: draft
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/355 （親 #349 のボードの子、key: `herdr-merge`）
- 対象リポジトリ: usaturn/create-reso-world（PR の base: main）
- 移植元: usaturn/agent-workspace の #824・#678・#703・#710（比較時点 AW `0eea76aa`。参照実装は現行 AW main の `issue-to-pr/SKILL.md`・`pr-review-fix-loop/SKILL.md`・`loop.py` を読んだ）
- 先行: #353（issue-review-steps）は `state_reason=completed` で close（2026-11-10T19:05:52Z）、PR #376 は main にマージ済み（`50f0e6a9`）。#355 の claim・open PR・既存 worktree は着手時に無し

## 管理・実行許可

- 利用者の指示（2026-11-12、原文）:
  > `/issue-to-pr #355 --merge --design-review pi_openai-codex_gpt6-sol_xhigh --spec-review pi_alibaba_qwen4-max_max --implement pi_alibaba_qwen4-max_max --assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`
  > `pi_alibaba_qwen4-max_max を動かす為に、ANTHROPIC_AUTH_TOKEN を MAAS_ANTHROPIC_TOKEN として渡してください。`
  > `途中でメインがマージされたら、追随して作業を止めずに続行してください。`
- 許可された範囲: issue-to-pr スキルの通常の委任（推奨案での設計判断、検証・commit・push・PR 作成の継続）と `--merge`（ループの `finalize.py` によるマージと関連 Issue の更新まで）。設計レビュー・Spec レビュー・実装・ループの担当は上記の明示指定
- この run 限りの追加委任（スキルの既定を上回る部分はここに記録し、スキル本文には書かない）:
  1. **key の受け渡し**: `pi_alibaba_qwen4-max_max` を起動するすべての runner 起動（Spec レビュー・実装 Task・ループの inspect/fix）で、`MAAS_ANTHROPIC_TOKEN="${ANTHROPIC_AUTH_TOKEN}"` をワンショットの環境前置で渡す。値はログ・文書・コミットに出さない。`with_keys.py` は既存の環境値を上書きしないので、前置で届ける
  2. **main への追随**: 捕捉した base（origin/main）が作業中に進んだ場合、issue-to-pr の既定（移動を観測したら停止）に代えて、新 SHA の再捕捉 → feature branch の新 base への rebase → 検証のやり直し → 記録の更新、の順で追随して続行する。旧/新 SHA と再検証の結果は記録・報告に残す。push 前の Gitleaks 検査と実 PR の base/head 照合は省略しない。この委任はこの run 限りで、#378（base 前進時の続行の一般化）の先取り実装はしない
- 内容の承認（`approved`）ではない。Spec・Plan は draft のままコミットし、この PR で公開する

## 意図と背景

Issue 起点の issue-to-pr の run が、Herdr のペイン名だけでは「終わったのか・障害で止まったのか・まだ動いているのか」を区別できない。また `--merge` の run は実装スキルの最終ブランチ全体レビューとループ 1 サイクル目のレビューが重複し、統合用 branch に向けた run ではループと `finalize.py` が既定 branch へのマージと Issue の close を前提にするため `--merge` を適用してはいけない。既存 open PR で止まるときの再開案内も、統合用 branch の PR にループ（マージまで進む）を案内してはいけない。

AW ではこれらが #824（ペイン名の終了状態）・#678（--merge とループ）・#703（統合 base での --merge 無効化）・#710（既存 PR の案内の base 分岐）で入っている。この子はそれを CRW の新しい構造（`--base`・pinned SHA・`DOCS_SEPARATE`・opt-in レビュー・runner 実装）の上に移植する。

## 受け入れ条件（Issue の「受け入れ」の写し）

1. Issue 起点の run で、マージ成功時は `:END`、予期しない障害の停止時は `:Glitch`、PR 作成だけ・通常の待機・想定された停止では名前を維持する
2. rename に失敗しても、元の停止理由・マージ結果を隠さず、pane 名が未更新であることを報告する。別 pane を探さない
3. `--issue-number` なしの loop 単独起動は、従来どおり `PR#<番号>` にする
4. `--issue-number` ありの loop は、issue-to-pr が付けた Issue の識別を上書きしない
5. `--merge` のとき、最終のブランチ全体レビューを行わず、loop の 1 サイクル目で代える。Task ごとのレビューは残す。deferred の minor を PR 本文に一覧で書く
6. 統合用 branch の run では `--merge` を適用せず、理由を利用者に伝え、`--merge` なしの run として PR 作成で終える
7. 既存 open PR で止まるとき、統合用 branch の PR にはループを案内しない
8. `--issue-number` が `loop_args` に入らない
9. 退行防止: `test_loop_herdr_pane.py`・`test_loop_check_options.py`・`test_base_workflow.py` の既存ケースが通る

## 編集範囲と所有

変更してよい（Issue 本文の「変更してよい」に従う）:

- `.agents/skills/issue-to-pr/SKILL.md` の 2 章 5（target ブロックを含む）・2 章 6 の既存 open PR 案内・3 章・4 章 8（新設）・5 章。および 4 章 8 と整合させるための「Task の実装を runner の担当に依頼する」節の最終レビューの 1 文
- `.agents/skills/issue-to-pr/scripts/resolve_issue.py`（境界のコメントのみ。後述 D8）
- `.agents/skills/pr-review-fix-loop/SKILL.md` の起動節（`--issue-number` と Herdr の項）
- `.agents/skills/pr-review-fix-loop/scripts/loop.py` の Herdr 節・start・CLI の start 引数（reconcile・診断・collect は触らない）
- `.agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py`・`test_loop_check_options.py`
- `.agents/skills/issue-to-pr/tests/test_base_workflow.py`
- `README.md` の「エージェントで作業する」の issue-to-pr 項への注記（D1 で表記を変えるため。Issue 本文が「変える場合は README に書く」と明示的に許可。ルート README.md は未完了の子の所有ではない: #353 は完了済み、#365 の所有は `.devcontainer/README.md`）
- この Spec・Plan（`docs/superpowers/`）

変更してはいけない・移植しない:

- `--hold-action` の受け付け
- AW の「rename に失敗したら停止する」規則（CRW の「rename を省いて続け、最終報告に書く」を残す）
- AW の `<repo>:#<N>` の無条件強制ではなく、Spec で決めた表記（D1）
- `loop.py` の reconcile・診断・collect（`loop-reconcile`・`review-eval-hooks` が所有）
- `finalize.py`（`loop-reconcile` が所有）
- `pr-review` の保存・workspace
- `issue-to-pr/SKILL.md` の 1 章・4 章 1〜7（`issue-review-steps` が所有。完了済みだが編集しない）
- `tools/agent_runner`・`review-fix-planning`・`.devcontainer/agent-runner.toml`・`.devcontainer/README.md`（この子の所有ではない）

## 決定記録

### D1: ペイン名の表記 — `<repo>:#<N>` に変える（採用。設計レビュー D2 を反映）

- 選択した案: issue-to-pr の 3 章のペイン名を `Issue#<N>` から `<repo>:#<N>`（`owner/repo` の repo 部分 + Issue 番号）に変える。repo 部分は**解決した Issue の repo**（`issue.json` の `repo`）。loop.py は issue-to-pr から `--issue-number N` と `--issue-repository OWNER/REPO`（表示用の Issue の repo。D6）を受け取り、**開始時と同じ Issue の repo と番号でラベルを再現する**。PR の repo から再導出しない
- 検討した別案:
  - (a) CRW の `Issue#<N>` を維持し、loop.py も `Issue#<N>` にする → Issue の「インターフェース」が `--issue-number` ありのpane名を `<repo>:#<N>` と固定しており、満たさない
  - (b) issue-to-pr は `Issue#<N>` のまま、loop.py だけ `<repo>:#<N>` にする → loop の start が issue-to-pr の付けた名前を書き換え、「issue-to-pr が開始時に付けた名前を上書きしない」の満たし方が曖昧になる
  - (c) issue-to-pr も loop も PR の対象 repo（TARGET_REPO）からラベルを作る → 名前一貫性は保たれるが、クロス repo（create-reso-world の #203 を resoloop で実装するなど）では `resoloop:#203` という別の Issue を示す表示になる。設計レビュー D2 で「番号だけ同じでも repo が変われば別の Issue を示す」と指摘され、不採用
  - (d) loop が `--issue-number` のとき rename を省いて開始時の名前を維持する → 「start の pane 名を `<repo>:#<N>` にする」のインターフェースを満たさず、`herdr_pane` の結果が skipped になって起動時の rename 結果と区別できないため不採用
- 選択理由: (採用案)だけが「`--issue-number` あり → `<repo>:#<N>`」の固定インターフェースと「Issue の識別を上書きしない」の両方を、クロス repo でも同じラベルの冪等な rename で満たす。AW と表記が揃い、ペイン一覧でリポジトリの区別も付く
- 委譲指示: issue-to-pr 1 章の通常の設計判断委任。README への注記は Issue 本文の明示指示
- 引き継ぎ: `ISSUE_PANE_LABEL` は run の間保持し、`:END`/`:Glitch` の更新にも同じラベルを使う。loop の `run.json` の `herdr_pane` は start 時点の結果（同じラベル）を保存する。`--issue-repository` は表示用で、マージ権限・対象 Issue の推測には使わない

### D2: `:END`/`:Glitch` の分類と更新条件（AW の表を移植、CRW の失敗時続行を維持）

- 選択した案: 3 章に「ペイン名の終了状態（Issue 起点の run だけ）」の節を足す。更新は `HERDR_ENV=1` で、かつ開始時の rename が成功して確定した `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL` があるときだけ。表:
  - 対応 PR のマージ成功を確認（finalize の `merged: true`、ループの `no_fix_needed` でマージ済みなど）→ 確認した時点で `${ISSUE_PANE_LABEL}:END`
  - 予期しない障害で中断 → 停止報告の前に `${ISSUE_PANE_LABEL}:Glitch`
  - PR 作成だけの完了・マージ未実施・通常の工程区切り/待機・想定された停止 → 名前を維持
- 分類の定義（AW を CRW の停止条件に合わせる）:
  - 予期しない障害: 必要なツール/API の失敗、担当の起動・結果形式の失敗（設計レビュー・Spec レビューの失敗を含む）、全レビュアーの失敗、資源の停止未確認、解消できない検証失敗、後片付けなどの実行障害。helper の `stopped`・`error` の値だけで決めず `stage`・`reason` と実際の原因で分類する。マージ後に関連 Issue の更新などが失敗して中断する場合は `Glitch` を優先し、報告ではマージ成功と未完了の後続処理を分ける
  - 想定された停止: 不正入力・設定の事前拒否、競合・claim/ロック、Issue の closed 化、未完了依存、明示承認待ち、許可されない操作・安全境界での停止、Spec/設計レビューの `decide` の `stop`、builder check の利用者判断、PR の HEAD 移動、base の捕捉後の移動（この run の追随委任は run 限りの例外で、スキル本文の分類は変えない）、実行予算・サイクルの上限。CI 待ちなどの待機や、run を中断せず再試行・回復する一時的な失敗も `Glitch` にしない
- 開始時の rename が失敗・スキップだった run は、終了状態の更新もしない（ラベルが確定していないため）。別 pane を探さず、rename の再帰的な再試行もしない。rename 自体の失敗は、元の停止理由・マージ結果と別に「pane 名が未更新であること」を報告する。この表示処理で既存の停止・回収・マージ権限を変更しない
- 検討した別案: AW の「rename 失敗で停止」をそのまま移植 → Issue が明示的に禁止。開始時 rename の失敗後も終了状態の更新を試みる → 確定していないラベルで pane を改名し、利用者が手動で付けた名前を上書きしうるため不採用
- 選択理由: Issue の「変更してはいけない」に従い CRW の続行規則を残しつつ、AW の終了状態の分類をそのまま使える形で移植する
- 委譲指示: 通常の設計判断委任

### D3: 4 章 8 — `--merge` のときは最終ブランチ全体レビューをループ 1 サイクル目で代える（新設）

- 選択した案: 4 章に項目 8 を足す。「`--merge` が適用される run は、実装スキルの最終のブランチ全体レビュー（全 Task の後のブランチ全体のレビュー）を行わず、ループの 1 サイクル目で代える。Task ごとのレビューは残す。最終レビューに回すはずだった minor の指摘（ledger の `deferred`）は PR 本文に一覧で書く。`--merge` が無い（適用されないを含む）run は最終レビューを省かない」
- 整合編集: 「Task の実装を runner の担当に依頼する」節の「すべての Task を取り込めたときの最後の全体レビューと PR は、`self` のときと同じ」を、4 章 8 に従う形に書き換える（PR は同じ・最終レビューは 4 章 8 のとおり）。停止時の「止まった Task の後の Task・最後の全体レビュー・PR には進まない」はそのまま残す
- 項目番号: CRW の 4 章は現在 1〜5。Issue とボードが「4 章 8」を正規の参照先として固定しているため、6・7 を作らず 8 を足す（AW の番号に合わせる）
- 検討した別案: 6 として追加 → ボードの他 Issue（#378 など）の「4 章 8」参照とずれるため不採用
- 選択理由: Issue の明示指示。重複レビューのコストを削りつつ、ループが必ず 1 サイクル目のレビューを行うので検査は減らない
- 委譲指示: 通常の設計判断委任
- この run への適用: この run は PR 作成まで現行（親 checkout の）スキルに従うため、最終ブランチ全体レビューを行う。新規則はマージ後の run から効く（「実行方式」の節）

### D4: 統合用 branch では `--merge` を適用しない（2 章 5 に規則を書く。判定は check-options より前。設計レビュー D1 を反映）

- 選択した案:
  - **判定の時点**: input ブロック（`base-workflow:input`）の `resolve_issue.py` の直後。`issue.json` の `merge` が非 null かつ `base` が `main` でないとき、理由を `$SESSION/merge-disabled.txt` に書く。`base` は解決済み（明示 `--base` か既定）なのでこの時点で判定できる
  - **2 章 3 の呼出条件**: `loop.py check-options` は「`merge` が非 null で、かつ `merge-disabled.txt` が無い」ときだけ実行する。無効化された run はループ設定の検査を起動しない（存在しない `--config` などのループ設定の不備で、使わないループの設定に通常の PR 作成が依存して止まることを防ぐ）。`implement_task.py check`・`review_design.py check`・`review_spec.py check` はループ用オプションではないので従来どおり実行する
  - **2 章 5 の本文**: 「`BASE` が統合用 branch（既定の `main` 以外）のときは `--merge` を適用しない（判定と記録は 2 章 3 の input ブロック）。理由（ループと `finalize.py` は既定 branch へのマージと Issue の close を前提にする）を利用者に伝え、`--merge` が無い run として続ける。ループ用オプションは使わず、最終の全体レビューを行い、CI 必須の対象は CI green を確認して PR の作成で終える」と書く
  - **target ブロック**: 既存の手動マージ拒否（meshy・登録済み通常ツール）は「`merge_requested=true` かつ `merge-disabled.txt` が無い」ときだけ適用する。無効化済みの run は `--merge` なしとして続行する（対象・権限の確認は維持）
- `issue.json` の `merge` は非 null のまま（resolve_issue.py は変えない）。run の扱いは `merge-disabled.txt` の有無で「`--merge` なし」に切り替わる
- 5 章の「`--merge` のとき: PR の作成後のループ」の冒頭に「`merge-disabled.txt` がある run（統合用 branch の子）はループを始めない。この節を使わず `--merge` が無い run と同じく PR の作成で終える。ここで改めて判断しない」を足す。5 章の完了報告などの「`--merge` のとき」は適用された run を指すことを明確にする
- 検討した別案:
  - target ブロック（2 章 5）で初めて判定する（初版の設計）→ その前の 2 章 3 の check-options がループ設定の不備で停止し、「ループ用オプションを使わず続行」を満たせない。設計レビュー D1（blocking）で指摘され、判定を input ブロックへ移した
  - capture の後に判定 → worktree 作成前に伝えるべき理由が遅れるため不採用
  - `--merge` を終了コード 2 で拒否 → Issue が「止めずに続ける」を明示しているため不採用
- 選択理由: Issue の明示指示（規則は 2 章 5 に書く）と、ループ設定に依存しない続行（判定は check-options より前）を両立する。AW #703 と同じ挙動
- 委譲指示: 通常の設計判断委任
- 検証: test_base_workflow.py の統合 base + `--merge` のケースで `merge-disabled.txt` が input ブロックの後に存在し、フローが PR 作成まで進むこと。check-options のスキップは司令塔の振る舞いなので、スキルの本文のレビューで確認する（シェルブロックのテストでは検証できない）

### D5: 2 章 6 — 既存 open PR で止まるときの案内を base で分ける

- 選択した案: 既存の案内文を「base が既定 branch なら `/pr-review-fix-loop <PR の URL>`、それ以外（統合用 branch など）ならループを案内せず `/pr-review <PR の URL>`（マージしない）」に分ける。PR の URL を使う既存の注意は残す
- 検討した別案: 常に `/pr-review` のみ案内 → 既定 base の PR でループ再開の案内が消え、後退するため不採用
- 選択理由: Issue の明示指示（AW #710）。統合用 branch の PR はループがマージまで進めてしまうため案内しない
- 委譲指示: 通常の設計判断委任

### D6: loop.py の `--issue-number` と `--issue-repository`（どちらも start 専用。設計レビュー D2 を反映）

- 選択した案:
  - `start` の引数に `--issue-number N`（`type=int`）を足す。`_add_option_arguments`（start と check-options の共通定義）には入れないので、check-options は argparse が終了コード 2 で拒否する
  - `start` の引数に `--issue-repository OWNER/REPO`（表示用の Issue の repo）を足す。これも start 専用で、check-options は拒否する。`--issue-number` と一緒に渡されたときだけ有効にし、`--issue-number` が無いのに `--issue-repository` だけがある場合は `LoopError(2, "arguments")` で拒否する（黙って無視しない）。形式は `owner/repo`（`/` をちょうど 1 つ含み、両側が空でない）。違反は `LoopError(2, "arguments")`
  - `start(..., issue_number: int | None = None, issue_repository: str | None = None)`。先頭の検証（controller の検証と同じ場所、ロック取得の前）で `issue_number is not None and issue_number < 1` なら `LoopError(2, "arguments", "--issue-number は正整数にする")`
  - `rename_pane(number: int, *, repository: str, issue_number: int | None = None, issue_repository: str | None = None) -> HerdrPane`。ラベルは `issue_number` があれば `f"{(issue_repository or repository).rsplit('/', 1)[-1]}:#{issue_number}"`、無ければ `f"PR#{number}"`。呼び出しは `rename_pane(pr.number, repository=pr.repository, issue_number=issue_number, issue_repository=issue_repository)`
  - issue-to-pr は `--issue-number N` と `--issue-repository <Issue の repo>` を一緒に渡すので、クロス repo でも開始時と同じ `<Issue の repo>:#<N>` になる（D1）。`--issue-number` のみ渡す呼び出し（AW 互換）は PR の repo の repo 部分を使う
  - `run.json` の `herdr_pane` は start 時点の結果を保存する（既存のまま）。終了時の更新は loop では行わない（issue-to-pr の担当）
  - `HerdrPane` モデル・`Options` モデル・check-options の出力は変えない
- 検討した別案:
  - `--issue-number` を check-options と共通にする → Issue が「start 専用・check-options は受け付けない」を固定しているため不採用
  - PR 本文や現在のペイン名から Issue 番号・repo を推測する → 誤った対象の表示につながるため不採用（明示引数だけ）
  - repo を引き継がず PR の repo から再導出する（初版の設計）→ クロス repo で開始時の Issue 識別を別の repo の表示で上書きする。設計レビュー D2（blocking）で指摘され、`--issue-repository` の追加で修正した
- 選択理由: Issue の「インターフェース」の固定仕様（`--issue-number N`・正整数・start 専用・`<repo>:#<N>`）を保ちつつ、受け入れ条件「issue-to-pr が付けた Issue の識別を上書きしない」をクロス repo でも満たす。`--issue-repository` は表示用の内部コンテキストの受け渡しで、マージ権限や対象 Issue の推測には使わない
- 委譲指示: 通常の設計判断委任（受け入れ条件を満たすためのインターフェースの詳細化。Issue の要件自体は変えない）

### D7: pr-review-fix-loop SKILL.md の起動節

- 選択した案: 起動節に `--issue-number N` と `--issue-repository OWNER/REPO` の説明を足す（issue-to-pr から呼ぶときだけ、入力解決・所有者確認済みの Issue 番号と Issue の repo を渡す。表示用の内部コンテキストで、マージ権限や対象 Issue の推測には使わない。`--issue-repository` は `--issue-number` と一緒に渡す）。Herdr の項を「単独起動は `PR#<PR番号>`。`--issue-number` があるときだけ `<repo>:#<Issue番号>`。repo 部分は `--issue-repository` があればその Issue の repo、無ければ解決済み PR の `owner/repo` の repo 部分。PR 本文や現在のペイン名から Issue を推測しない。Issue 起点の `:END`/`:Glitch` の更新は呼出元の issue-to-pr の 3 章が担当し、loop 単独起動の終了時の名前は変えない」に書き換える。check-options の項に `--issue-number`・`--issue-repository` を受け付けないことを 1 文足す
- frontmatter の `argument-hint` は変えない（どちらも利用者が手動で渡すオプションではないため）
- 検討した別案: argument-hint に追加 → 利用者の手動指定を招くため不採用
- 選択理由: Issue の明示指示。AW の起動節の内容に、Issue の repo の引き継ぎ（D1・D6）を足す
- 委譲指示: 通常の設計判断委任

### D8: resolve_issue.py はコメントのみ（挙動は変えない）

- 選択した案: `LOOP_OPTIONS` の近くに「`--issue-number` は issue-to-pr の入力オプションではなく、loop.py の start に司令塔が渡す表示用の別引数。loop_args には入れない」のコメントを足す
- 根拠: 現行の resolve_issue.py は未知のオプション（`--issue-number` を含む）を終了コード 2 で拒否し（`parse` のオプション検査）、`loop_args` は `LOOP_OPTIONS`（`--max-cycles`・`--assign`・`--template`・`--config`）だけから作る。つまり「`--issue-number` が loop_args に入らない」は既に成立している。挙動を変える必要はない
- 検討した別案: `--issue-number` を明示拒否の `REFUSED_OPTIONS` に足す → 未知オプションとして既に拒否されており、拒否理由の個別化は表示だけの改善で必須ではないため不採用（最小変更）
- 選択理由: Issue の「変更してよい」の注記は境界の確認であり、既存挙動が満たしている。コメントで境界を文書化する
- 委譲指示: 通常の設計判断委任
- 検証: `resolve_issue.py -- '#355 --merge --issue-number 1'` が終了コード 2 になることを実行で確かめる（テストは書かない。理由: 拒否はメッセージ付き非 0 終了で気付ける L）

### D9: テストの方針（AGENTS.md のテストの採用基準）

- `test_loop_herdr_pane.py`（fake herdr が呼び出しを記録する）:
  - `--issue-number` なしの start → ラベル `PR#<番号>`、現在のペイン（`HERDR_PANE_ID`）への rename が 1 回だけ、`run.json` の `herdr_pane` が start 時点の結果（S: 別の対象を選ばない・記録の取り違え防止。単独起動の既存挙動の退行防止）
  - `--issue-number` ありの start → ラベル `<repo>:#<Issue番号>`、同じペインへの 1 回だけ。fake が記録した呼び出し全体を検査し、別 pane を触らないこと（S: Issue の識別を PR 番号で上書きしない・誤った対象の操作防止）
  - `--issue-number` + `--issue-repository`（PR の repo と異なる Issue の repo）の start → ラベルは引き継いだ Issue の repo の repo 部分 + Issue 番号になり、PR の repo から再導出しない（S: クロス repo で開始時の Issue 識別を別の Issue の表示で上書きしない。設計レビュー D2 の退行防止）
  - `--issue-number 0`（負の値も同類の代表）→ 終了コード 2・`arguments`、ロックも run も作らず herdr も呼ばない（S: 無効な識別子がもっともらしいラベル `repo:#0` になる・拒否がロック取得の後だと拒否された start がロックを残して次の run を妨げる）
  - `--issue-repository` の形式違反（`/` なし）と `--issue-number` なしの `--issue-repository` → 終了コード 2・`arguments`、ロックも run も作らない（S: 黙って無視・誤ったラベルになるのを防ぐ。代表 1 件ずつ）
  - rename 失敗（fake が非 0 終了）→ start は成功し、`herdr_pane.state=failed` と `reason`・warnings が残る（S: 表示の失敗を成功と報告しない・run を不当に止めない）
  - 既存のハングテスト（timeout で start が戻る）は残す
  - 非整数（`abc`）の拒否は argparse の usage（L）なのでコミットするテストにしない。実行で確かめる
- `test_loop_check_options.py`: `check-options --issue-number 355` が終了コード 2 で拒否され、GitHub・親 checkout に触れないこと（S: 事前検査が start と異なるオプション集合を黙って受け付けると、検査の通ったオプションが start の記録に現れない「もっともらしいが誤った事前検査」になる。拒否のテストには正しく通る既存ケースが残る）。`--issue-repository` も同様に拒否されることを同じテストの representative として足す
- `test_base_workflow.py`: 既存の `--base=統合/プラグイン #42 --merge` のパラメータケースに、`SESSION/merge-disabled.txt` が理由付きで存在し（input ブロックの後の時点で）、`issue.json` の `merge` が非 null のままフローが PR 作成まで進むことの検査を足す。既定 base + `--merge`（`#42 --merge`）のケースを足し、`merge-disabled.txt` ができないことを確かめる（S: 統合 base でループがマージと Issue close まで進む損害の防止。何でも無効化する実装で通らないよう正しく通る例を残す）
- `resolve_issue.py` の `--issue-number` 拒否・非整数の拒否は L のためテストを書かず、実行で確かめる
- SKILL.md の文言そのものを写すテストは F なので書かない（`test_pr_review_fix_loop_skill_contract.py` の frontmatter 検査は F∩S の既存テストとして残す）

### D10: README への注記

- 選択した案: `README.md` の「エージェントで作業する」の issue-to-pr 項に、ペイン名が `Issue#<N>` から `<repo>:#<N>` に変わったこと（#355）と、マージ成功で `:END`・予期しない障害の停止で `:Glitch` が付くことを 1〜2 文で注記する
- 検討した別案: `.devcontainer/README.md` に書く → この子は `.devcontainer/README.md` を所有せず（#365 の所有）、ルート README の issue-to-pr 項が既存の説明場所なので不採用
- 選択理由: Issue 本文の「変える場合は、既存の利用者の見慣れた表記との差を README に書く」
- 委譲指示: Issue 本文の明示指示

## 設計レビューの記録（1 回目）

- helper: `review_design.py review`（external）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-355.puoplwnc/2026-11-12-issue-355-herdr-merge-design.design-review/review-1`
- `review_id`: `0d07f48e94594eac8f10a0110ed27df4`。reviewed の Spec SHA-256: `a5ec968b79b97db21e5e27f1401025f0063d8c560b6e740b44c18d98a0adee73`（コミット `66b766a8` の版）
- 担当: 明示 `--design-review pi_openai-codex_gpt6-sol_xhigh`。`requested_agent` / `actual_agent` ともに `pi_openai-codex_gpt6-sol_xhigh`。identity: model `gpt-6.1-sol` / provider `openai-codex` / effort `xhigh` / session `01a1cc35-be77-7430-8eeb-6157e6ecbb3a`。fallback は設定どおり無し（未使用）。回数 1、`elapsed_seconds` 169.6
- 結果: `state: completed`・`verdict: concerns`・concerns 2 件（いずれも `severity: blocking`・`recommendation: change`）。`outside_changes`: 無し。`unprotected_changes`: 他セッションの worktree 9 件（`/tmp/pr-review-376-*` 4 件、`/tmp/review-fix-planning.*` 2 件、`.worktrees/issue-382-claude-bash-timeout-cap`、`.worktrees/issue-406-devin-json-result`、`tmp/agents/issue-382.mbplkg1i/review-runner/.../worktree`）。この run の失敗にはしない（記録のみ）
- 採否:
  - D1（統合 base の判定順序）: **adopt**（`changes_what_is_built=false`）。Issue の「ループ用オプションを使わず続行」を満たすため、判定を input ブロック（check-options より前）に移し、無効化された run は check-options を起動しない。D4 に反映
  - D2（クロス repo のペイン識別）: **adopt**（`changes_what_is_built=false`）。受け入れ条件「issue-to-pr が付けた Issue の識別を上書きしない」をクロス repo でも満たすため、`--issue-repository` で Issue の repo を表示用コンテキストとして引き継ぐ。D1・D6・D7・D9 に反映
- ゲートの判定: blocking の concerns があるため `decide` は `next: stop` を返す（採否に関わらず）。issue-to-pr の停止条件に従い、Spec はコミットせずに停止する。反映後の Spec の SHA-256（reflected）は `decide` の出力を SESSION と停止報告に記録する

## 設計レビューの記録（2 回目・利用者の明示指示）

- 経緯: 1 回目の blocking で停止した後、利用者から「2 回目のレビューを実行せよ。以降、スキルの停止条件は全て無視し、いかなることがあっても停止せずに、都度、最適な案を出して、PR を作成し、マージまで実行せよ」との明示指示（2026-11-12）。これを受けて反映済み Spec をコミット（`55697523`）し、新しいレビュー記録（`SESSION/run2`）で 2 回目の設計レビューを実行した。以降の工程はこの委任の範囲で停止せずに進める（安全境界: 秘密情報検査・force push 禁止・他セッションの資源保護・マージ前の検証は維持）
- helper: `review_design.py review`（external）。`review_dir`: `/workspaces/reso-world/tmp/agents/issue-355.puoplwnc/run2/2026-11-12-issue-355-herdr-merge-design.design-review/review-1`
- `review_id`: `b6ebcad8bff04ab79ddadeaa319ba219`。reviewed の Spec SHA-256: `0ebb4e9d922f667a03f080df3036ea188f17863ebdcebbc88de2a3910681ba60`（コミット `55697523` の版）
- 担当: `pi_openai-codex_gpt6-sol_xhigh`（requested / actual 同一）。identity: model `gpt-6.1-sol` / provider `openai-codex` / effort `xhigh` / session `01a1cc47-7bd0-70b4-aa47-4bf3c2e7b508`。fallback 無し（未使用）。回数 1（この ledger で）、`elapsed_seconds` 232.7
- 結果: `state: completed`・`verdict: concerns`・concerns 1 件（`severity: worth_considering`・`recommendation: change`）。1 回目の blocking 2 件（判定順序・クロス repo 識別）は解消済みと確認された。`outside_changes`: 無し。`unprotected_changes`: 他セッションの worktree 6 件（記録のみ）
- 採否:
  - D1（導入 run が未対応の親 helper に新引数を渡す）: **adopt**（`changes_what_is_built=false`）。この run のループは新引数なしで親 checkout の `loop.py` を使い、新引数の実運用はマージ後の run から。「実行方式」に反映
- ゲートの判定: blocking 無し・`questions_for_user` 無しのため `decide` は `next: continue`。反映後の Spec をコミットして Spec レビューへ進む

## 設計の詳細（ファイル別）

### `.agents/skills/issue-to-pr/SKILL.md`

- 2 章 3: input ブロックの `resolve_issue.py` の直後に `merge-disabled.txt` の書き込みを足す（D4）。`check-options` の呼出条件を「`merge` が非 null で `merge-disabled.txt` が無いとき」にする。理由の利用者への伝達もこの時点で行う
- 2 章 5: 統合用 branch で `--merge` を適用しない規則と、適用しない run の扱い（ループ用オプション不使用・最終全体レビュー・CI green・PR 作成で終える）を書く（D4）。target ブロックの手動マージ拒否は `merge-disabled.txt` が無いときだけ適用する
- 2 章 6: 既存 open PR の案内を base で分ける（D5）
- 3 章: 開始時の rename を `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL`（`<repo>:#<N>`、解決した Issue の repo の repo 部分）の保持に変える。CRW の「現在 pane が分からない・rename が失敗したときは、別の pane を推測せず、rename を省いて続け、最終報告に書く」は残す。成功したときだけ両変数が確定し、終了状態の更新に使えることを書く。「ペイン名の終了状態」の節（表・分類・失敗時の報告）を足す（D2）
- 4 章: 項目 8 を足す（D3）。runner 節の最終レビューの 1 文を整合させる
- 5 章: 「`--merge` のとき: PR の作成後のループ」の冒頭に、適用しない run はループを始めないことを書く（D4）。ループの `start` には `--issue-number N` と `--issue-repository <Issue の repo>` を渡すことを書く（D1・D6）。「`--merge` のとき」の各記述は適用された run を指すことを明確にする。完了報告にペイン名の更新結果（`:END`/`:Glitch`/維持・rename 失敗の理由）を含めることを書く
- 1 章・4 章 1〜7・2 章のそれ以外の節は変えない

### `.agents/skills/pr-review-fix-loop/scripts/loop.py`

- `rename_pane` のシグネチャとラベル（D6）。`start` の `issue_number`・`issue_repository` 引数と先頭検証（正整数・`owner/repo` 形式・`--issue-repository` は `--issue-number` と一緒）。`dispatch` の start への受け渡し。CLI の start への `--issue-number`・`--issue-repository` 追加（`_add_option_arguments` には入れない）
- Herdr 節の docstring を新しいラベル規則に合わせる
- reconcile・診断・collect・finalize 連携・`Options`・`HerdrPane` モデルは変えない

### `.agents/skills/pr-review-fix-loop/SKILL.md`

- 起動節: `--issue-number`・`--issue-repository` の説明と Herdr の項の書き換え（D7）。`check-options` の項に両引数を受け付けないことを 1 文足す

### `.agents/skills/issue-to-pr/scripts/resolve_issue.py`

- `LOOP_OPTIONS` の近くのコメントのみ（D8）

### テスト・README

- D9・D10 のとおり

## 実行方式

- 実装: `--implement pi_alibaba_qwen4-max_max`（`implement_task.py check` 終了コード 0、`self=false`、fallback なし）。superpowers:subagent-driven-development の形で、Task を 1 つずつ `implement_task.py run` で runner の担当に依頼する（並行しない）。runner 起動は `with_keys.py` 経由 + `MAAS_ANTHROPIC_TOKEN` の環境前置
- 設計レビュー: `pi_openai-codex_gpt6-sol_xhigh`（`review_design.py check` 終了コード 0）。Spec レビュー: `pi_alibaba_qwen4-max_max`（`review_spec.py check` 終了コード 0）。設計レビュー → Spec レビュー → Plan の順で、builder check は行わない
- ループ（`--merge`）: `loop.py start` に `--assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`（利用者が書いた順）を渡す。`--controller-runtime claude-code`・`--controller-model` は現在の正確なモデル ID。ループは親 checkout の `loop.py` を使う（feature worktree のものは使わない）
- **この run では新引数を渡さない**（設計レビュー 2 回目 D1 を反映）: 親 checkout の `loop.py` はこの PR の変更前なので、`--issue-number`・`--issue-repository` を渡すと拒否される。新引数の検証は fake 環境のテストで行い、実運用での受け渡しはマージ後の run から始める。この run のループ中のペイン名は従来の `PR#<番号>` になる。マージ成功の確認後に、司令塔がこの PR で入れる 3 章の規則に従って `create-reso-world:#355:END` へ手動で更新する（導入 run 限りの適用）
- この run の最終ブランチ全体レビュー: 現行スキルに従い行う（D3 の「この run への適用」）
- 検証の入口（対象 repo の規則）: `uv run pytest <関連テスト>`、`bash scripts/check-layout.sh`。create-reso-world は Actions 無効なので CI 確認は不要
- 隔離: テストは fixture が一時 HOME・GIT_* を隔離する。手動の fake Herdr 確認は `env HOME=<一時> HERDR_ENV=1 HERDR_PANE_ID=<fake> PATH=<fake herdr 先頭>` のワンショットで、実 Herdr の別 pane は操作しない

## 検証

- `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py .agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`
- `uv run pytest .agents/skills/issue-to-pr/tests/test_base_workflow.py`
- 退行: `uv run pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/issue-to-pr/tests`（全体）
- `bash scripts/check-layout.sh`
- 手動（fake Herdr）: start・マージ成功・障害・通常停止の 4 ケースのペイン名を、fake の `herdr`（呼び出しを記録して成功/失敗を返す）で確認する。実 Herdr の別 pane は操作しない
- 実行確認（L の代替検証）: `resolve_issue.py` が `--issue-number` を終了コード 2 で拒否すること（着手時に確認済み: 「未知のオプションです: --issue-number」）、`loop.py start --issue-number abc` が argparse の usage で終了コード 2 になること、`check-options --issue-number 1`・`check-options --issue-repository usaturn/create-reso-world` が終了コード 2 になること

## 依存と後続

- 先行 #353 は完了・マージ済み（上記）。この子は `issue-to-pr/SKILL.md` の指定節と `loop.py` の Herdr 節だけを編集する
- 後続: #356（loop-reconcile）はこの子の完了後に `loop.py` の reconcile・診断を編集する。#365（runner-catalog）は `.devcontainer/agent-runner.toml` などを編集する（この子は触らない）。#378 は #353・#355 の完了後に `issue-to-pr/SKILL.md` の 2 章 6・5 章の base 前進時の続行を編集する
- ボードの運用: claim（`refs/heads/agent-claims/issue-355`）・成果の公開（復元 manifest）・解放は planning-parallel-issues に従う。`--merge` の claim 解放はループの finish の後