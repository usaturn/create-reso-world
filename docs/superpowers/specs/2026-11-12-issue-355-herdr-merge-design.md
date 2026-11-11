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

### D1: ペイン名の表記 — `<repo>:#<N>` に変える（採用）

- 選択した案: issue-to-pr の 3 章のペイン名を `Issue#<N>` から `<repo>:#<N>`（`owner/repo` の repo 部分 + Issue 番号）に変える。loop.py の `--issue-number` ありのラベルも同じ `<repo>:#<N>`
- 検討した別案:
  - (a) CRW の `Issue#<N>` を維持し、loop.py も `Issue#<N>` にする → Issue の「インターフェース」が `--issue-number` ありのpane名を `<repo>:#<N>` と固定しており、満たさない
  - (b) issue-to-pr は `Issue#<N>` のまま、loop.py だけ `<repo>:#<N>` にする → loop の start が issue-to-pr の付けた名前を書き換え、「issue-to-pr が開始時に付けた名前を上書きしない」の満たし方が曖昧になる
- 選択理由: (採用案)だけが「`--issue-number` あり → `<repo>:#<N>`」の固定インターフェースと「Issue の識別を上書きしない」の両方を、同じラベルの冪等な rename で満たす。AW と表記が揃い、ペイン一覧でリポジトリの区別も付く
- 委譲指示: issue-to-pr 1 章の通常の設計判断委任。README への注記は Issue 本文の明示指示
- repo 部分の取り方: issue-to-pr は解決した Issue の repo（`issue.json` の `repo`）の repo 部分。loop.py は解決した PR の repository（`pr.repository`）の repo 部分（AW と同じ）。Issue と PR が同じ repo の通常ケースでは一致する。クロス repo（Issue が create-reso-world・PR が resoloop など）では repo 部分が異なるが Issue 番号は保たれ、AW と同じ挙動になる

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

### D4: 2 章 5 — 統合用 branch では `--merge` を適用しない

- 選択した案: target ブロック（`base-workflow:target`）の既存の手動マージ拒否の後に、`merge_requested=true` かつ `issue.json` の `base` が `main` でないとき、理由を `$SESSION/merge-disabled.txt` に書く処理を足す。本文では「`BASE` が統合用 branch（既定の `main` 以外）のときは `--merge` を適用しない。理由（ループと `finalize.py` は既定 branch へのマージと Issue の close を前提にする）を利用者に伝え、`--merge` が無い run として続ける。ループ用オプションは使わず、最終の全体レビューを行い、CI 必須の対象は CI green を確認して PR の作成で終える」と書く
- 判定の時点: worktree の前（target ブロック）。`issue.json` の `base` は解決済みの base（明示 `--base` か既定）なので、capture を待たずに判定できる。登録済み通常ツールと meshy は既存の case 文が `--merge` を終了コード 2 で拒否するので、この分岐に到達するのは parent / fork の明示 `--base` だけ
- `issue.json` の `merge` は非 null のまま（resolve_issue.py は変えない）。run の扱いは `merge-disabled.txt` の有無で「`--merge` なし」に切り替わる
- 5 章の「`--merge` のとき: PR の作成後のループ」の冒頭に「2 章 5 で `--merge` を適用しないと決めた run はループを始めない。この節を使わず `--merge` が無い run と同じく PR の作成で終える。ここで改めて判断しない」を足す。5 章の完了報告などの「`--merge` のとき」は適用された run を指すことを明確にする
- 検討した別案: capture の後に判定 → worktree 作成前に伝えるべき理由が遅れ、ループ用オプションの検査（check-options）も無駄に走るため不採用。`--merge` を終了コード 2 で拒否 → Issue が「止めずに続ける」を明示しているため不採用
- 選択理由: Issue の明示指示。AW #703 と同じ挙動を CRW のブロック構造に置く
- 委譲指示: 通常の設計判断委任

### D5: 2 章 6 — 既存 open PR で止まるときの案内を base で分ける

- 選択した案: 既存の案内文を「base が既定 branch なら `/pr-review-fix-loop <PR の URL>`、それ以外（統合用 branch など）ならループを案内せず `/pr-review <PR の URL>`（マージしない）」に分ける。PR の URL を使う既存の注意は残す
- 検討した別案: 常に `/pr-review` のみ案内 → 既定 base の PR でループ再開の案内が消え、後退するため不採用
- 選択理由: Issue の明示指示（AW #710）。統合用 branch の PR はループがマージまで進めてしまうため案内しない
- 委譲指示: 通常の設計判断委任

### D6: loop.py の `--issue-number`（start 専用）

- 選択した案:
  - `start` の引数に `--issue-number N`（`type=int`）を足す。`_add_option_arguments`（start と check-options の共通定義）には入れないので、check-options は argparse が終了コード 2 で拒否する
  - `start(..., issue_number: int | None = None)`。先頭の検証（controller の検証と同じ場所、ロック取得の前）で `issue_number is not None and issue_number < 1` なら `LoopError(2, "arguments", "--issue-number は正整数にする")`
  - `rename_pane(number: int, *, repository: str, issue_number: int | None = None) -> HerdrPane`。ラベルは `issue_number` があれば `f"{repository.rsplit('/', 1)[-1]}:#{issue_number}"`、無ければ `f"PR#{number}"`。呼び出しは `rename_pane(pr.number, repository=pr.repository, issue_number=issue_number)`
  - `run.json` の `herdr_pane` は start 時点の結果を保存する（既存のまま）。終了時の更新は loop では行わない（issue-to-pr の担当）
  - `HerdrPane` モデル・`Options` モデル・check-options の出力は変えない
- 検討した別案: `--issue-number` を check-options と共通にする → Issue が「start 専用・check-options は受け付けない」を固定しているため不採用。PR 本文や現在のペイン名から Issue 番号を推測する → 誤った対象の表示につながるため不採用（明示引数だけ）
- 選択理由: Issue の「インターフェース」の固定仕様。AW の実装と同じ形
- 委譲指示: 通常の設計判断委任

### D7: pr-review-fix-loop SKILL.md の起動節

- 選択した案: 起動節に `--issue-number N` の説明を足す（issue-to-pr から呼ぶときだけ、入力解決・所有者確認済みの Issue 番号を渡す。表示用の内部コンテキストで、マージ権限や対象 Issue の推測には使わない）。Herdr の項を「単独起動は `PR#<PR番号>`。`--issue-number` があるときだけ `<repo>:#<Issue番号>`（解決済み PR の `owner/repo` の repo 部分）。Issue 起点の `:END`/`:Glitch` の更新は呼出元の issue-to-pr の 3 章が担当し、loop 単独起動の終了時の名前は変えない」に書き換える
- frontmatter の `argument-hint` は変えない（`--issue-number` は利用者が手動で渡すオプションではないため）
- 検討した別案: argument-hint に追加 → 利用者の手動指定を招くため不採用
- 選択理由: Issue の明示指示。AW の起動節と同じ内容
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
  - `--issue-number 0`（負の値も同類の代表）→ 終了コード 2・`arguments`、ロックも run も作らず herdr も呼ばない（S: 無効な識別子がもっともらしいラベル `repo:#0` になる・拒否がロック取得の後だと拒否された start がロックを残して次の run を妨げる）
  - rename 失敗（fake が非 0 終了）→ start は成功し、`herdr_pane.state=failed` と `reason`・warnings が残る（S: 表示の失敗を成功と報告しない・run を不当に止めない）
  - 既存のハングテスト（timeout で start が戻る）は残す
  - 非整数（`abc`）の拒否は argparse の usage（L）なのでコミットするテストにしない。実行で確かめる
- `test_loop_check_options.py`: `check-options --issue-number 355` が終了コード 2 で拒否され、GitHub・親 checkout に触れないこと（S: 事前検査が start と異なるオプション集合を黙って受け付けると、検査の通ったオプションが start の記録に現れない「もっともらしいが誤った事前検査」になる。拒否のテストには正しく通る既存ケースが残る）
- `test_base_workflow.py`: 既存の `--base=統合/プラグイン #42 --merge` のパラメータケースに、`SESSION/merge-disabled.txt` が理由付きで存在し、`issue.json` の `merge` が非 null のままフローが PR 作成まで進むことの検査を足す。既定 base + `--merge`（`#42 --merge`）のケースを足し、`merge-disabled.txt` ができないことを確かめる（S: 統合 base でループがマージと Issue close まで進む損害の防止。何でも無効化する実装で通らないよう正しく通る例を残す）
- `resolve_issue.py` の `--issue-number` 拒否・非整数の拒否は L のためテストを書かず、実行で確かめる
- SKILL.md の文言そのものを写すテストは F なので書かない（`test_pr_review_fix_loop_skill_contract.py` の frontmatter 検査は F∩S の既存テストとして残す）

### D10: README への注記

- 選択した案: `README.md` の「エージェントで作業する」の issue-to-pr 項に、ペイン名が `Issue#<N>` から `<repo>:#<N>` に変わったこと（#355）と、マージ成功で `:END`・予期しない障害の停止で `:Glitch` が付くことを 1〜2 文で注記する
- 検討した別案: `.devcontainer/README.md` に書く → この子は `.devcontainer/README.md` を所有せず（#365 の所有）、ルート README の issue-to-pr 項が既存の説明場所なので不採用
- 選択理由: Issue 本文の「変える場合は、既存の利用者の見慣れた表記との差を README に書く」
- 委譲指示: Issue 本文の明示指示

## 設計の詳細（ファイル別）

### `.agents/skills/issue-to-pr/SKILL.md`

- 2 章 5: target ブロックの手動マージ拒否の後に `merge-disabled.txt` の書き込みを足す（D4）。ブロックの後に、適用しない run の扱い（理由の伝達・ループ用オプション不使用・最終全体レビュー・CI green・PR 作成で終える）を書く
- 2 章 6: 既存 open PR の案内を base で分ける（D5）
- 3 章: 開始時の rename を `ISSUE_PANE_ID`・`ISSUE_PANE_LABEL`（`<repo>:#<N>`、解決した Issue の repo の repo 部分）の保持に変える。CRW の「現在 pane が分からない・rename が失敗したときは、別の pane を推測せず、rename を省いて続け、最終報告に書く」は残す。成功したときだけ両変数が確定し、終了状態の更新に使えることを書く。「ペイン名の終了状態」の節（表・分類・失敗時の報告）を足す（D2）
- 4 章: 項目 8 を足す（D3）。runner 節の最終レビューの 1 文を整合させる
- 5 章: 「`--merge` のとき: PR の作成後のループ」の冒頭に、適用しない run はループを始めないことを書く（D4）。「`--merge` のとき」の各記述は適用された run を指すことを明確にする。完了報告にペイン名の更新結果（`:END`/`:Glitch`/維持・rename 失敗の理由）を含めることを書く
- 1 章・4 章 1〜7・2 章のそれ以外の節は変えない

### `.agents/skills/pr-review-fix-loop/scripts/loop.py`

- `rename_pane` のシグネチャとラベル（D6）。`start` の `issue_number` 引数と先頭検証。`dispatch` の start への受け渡し。CLI の start への `--issue-number` 追加（`_add_option_arguments` には入れない）
- Herdr 節の docstring を新しいラベル規則に合わせる
- reconcile・診断・collect・finalize 連携・`Options`・`HerdrPane` モデルは変えない

### `.agents/skills/pr-review-fix-loop/SKILL.md`

- 起動節: `--issue-number` の説明と Herdr の項の書き換え（D7）。`check-options` の項に `--issue-number` を受け付けないことを 1 文足す

### `.agents/skills/issue-to-pr/scripts/resolve_issue.py`

- `LOOP_OPTIONS` の近くのコメントのみ（D8）

### テスト・README

- D9・D10 のとおり

## 実行方式

- 実装: `--implement pi_alibaba_qwen4-max_max`（`implement_task.py check` 終了コード 0、`self=false`、fallback なし）。superpowers:subagent-driven-development の形で、Task を 1 つずつ `implement_task.py run` で runner の担当に依頼する（並行しない）。runner 起動は `with_keys.py` 経由 + `MAAS_ANTHROPIC_TOKEN` の環境前置
- 設計レビュー: `pi_openai-codex_gpt6-sol_xhigh`（`review_design.py check` 終了コード 0）。Spec レビュー: `pi_alibaba_qwen4-max_max`（`review_spec.py check` 終了コード 0）。設計レビュー → Spec レビュー → Plan の順で、builder check は行わない
- ループ（`--merge`）: `loop.py start` に `--assign implement=pi_alibaba_qwen4-max_max --assign inspect=pi_alibaba_qwen4-max_max,claude-code_sonnet_xhigh`（利用者が書いた順）と `--issue-number 355`（この子が新設する start 専用引数。司令塔が解決済みの Issue 番号を渡す）を渡す。`--controller-runtime claude-code`・`--controller-model` は現在の正確なモデル ID。ループは親 checkout の `loop.py` を使う（feature worktree のものは使わない）
- この run の最終ブランチ全体レビュー: 現行スキルに従い行う（D3 の「この run への適用」）
- 検証の入口（対象 repo の規則）: `uv run pytest <関連テスト>`、`bash scripts/check-layout.sh`。create-reso-world は Actions 無効なので CI 確認は不要
- 隔離: テストは fixture が一時 HOME・GIT_* を隔離する。手動の fake Herdr 確認は `env HOME=<一時> HERDR_ENV=1 HERDR_PANE_ID=<fake> PATH=<fake herdr 先頭>` のワンショットで、実 Herdr の別 pane は操作しない

## 検証

- `uv run pytest .agents/skills/pr-review-fix-loop/tests/test_loop_herdr_pane.py .agents/skills/pr-review-fix-loop/tests/test_loop_check_options.py`
- `uv run pytest .agents/skills/issue-to-pr/tests/test_base_workflow.py`
- 退行: `uv run pytest .agents/skills/pr-review-fix-loop/tests .agents/skills/issue-to-pr/tests`（全体）
- `bash scripts/check-layout.sh`
- 手動（fake Herdr）: start・マージ成功・障害・通常停止の 4 ケースのペイン名を、fake の `herdr`（呼び出しを記録して成功/失敗を返す）で確認する。実 Herdr の別 pane は操作しない
- 実行確認（L の代替検証）: `resolve_issue.py` が `--issue-number` を終了コード 2 で拒否すること、`loop.py start --issue-number abc` が argparse の usage で終了コード 2 になること、`check-options --issue-number 1` が終了コード 2 になること

## 依存と後続

- 先行 #353 は完了・マージ済み（上記）。この子は `issue-to-pr/SKILL.md` の指定節と `loop.py` の Herdr 節だけを編集する
- 後続: #356（loop-reconcile）はこの子の完了後に `loop.py` の reconcile・診断を編集する。#365（runner-catalog）は `.devcontainer/agent-runner.toml` などを編集する（この子は触らない）。#378 は #353・#355 の完了後に `issue-to-pr/SKILL.md` の 2 章 6・5 章の base 前進時の続行を編集する
- ボードの運用: claim（`refs/heads/agent-claims/issue-355`）・成果の公開（復元 manifest）・解放は planning-parallel-issues に従う。`--merge` の claim 解放はループの finish の後