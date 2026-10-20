# Issue #135: push の前の Gitleaks の検査を、resoloop の識別子やテスト用の偽の値で止めない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/135（親 Issue・ボード・未完了の先行 Issue は無い。先行の #119・PR #133 はマージ済み）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue135-gitleaks-false-positives.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-135-gitleaks-false-positives`（branch `fix/issue-135-gitleaks-false-positives`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #135 --merge` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #135`）、PR 修正ループ（pr-review-fix-loop）と、修正不要と確かめられたときの `finalize.py` によるマージ・関連 Issue の更新まで行う
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 実装の担当: `implement_task.py check` は `assignment.agents = ["self"]`・`fallback = []`・`self: true`（雛形 `.devcontainer/agent-runner.toml` の既定の適用。利用者の指定ではない）
- ループ: `loop.py check-options` は `max_cycles = 3`・`assign = {}`・`template = .devcontainer/agent-runner.toml`・`config = null`。レビュアーは `pi-gpt`・`devin-swe`・`dsh-ccd`・`cursor-grok47`、修正の担当は `claude-opus`（どれも既定の適用。利用者はループ用のオプションを書いていない）
- 基準: `origin/main` の `f2350a4`

## 意図

#119（PR #133）で push の前の Gitleaks の検査を必須にした。base の `.gitleaks.toml` が `generic-api-key` から外すのは、resoloop のマニフェストの `"key": "..."` の形だけである。ワールドの作業の Spec・Plan やテストには、別の形で resoloop の識別子やテスト用の偽の値が出る。今の規則（`AGENTS.md` の「push の前の秘密情報の検査」）は「利用者に報告し、除外が要るなら base の `.gitleaks.toml` を先に変える」なので、止めずに PR まで進む流れ（`issue-to-pr`、`--merge` のループの中の `review-fix-planning`）がそこで止まる。誤検出で止まる場面を減らし、それでも止まったときにエージェントが自分で直せる範囲を決める。秘密情報の検出は弱めない。

## 確認した事実（2026-10-20、gitleaks 8.30.1）

- resoloop の識別子は `blender_export.py` の `key(prefix, name)` が作る。形は「接頭辞（`tex_`・`mat_`・`pbr_`・`mesh_`・`object_`・`renderer_`・`blender_`）＋名前の英数字・`_`・`-` 以外を `_` にした 40 文字までの slug ＋ `_` ＋ 名前の sha256 の先頭 8 桁の 16 進（小文字）」。`pbr_` の名前は `mat_` の識別子なので、slug の中にも 8 桁の 16 進が入る（slug は 40 文字で切り詰めるので、途中で切れることがある）。ワールドの作業では、さらに接頭辞を足した識別子（`ul_` など）も使う
- 検出の `Secret` は値そのもの（引用符の内側）。Python の代入 `key = '<識別子>'`、テストの出力の引用 `KeyError: '<識別子>'`、JSON の `"placement_key": "<名前>"`、テストの偽の値 `KEY = "msy_test_..."` で、どれも `generic-api-key` が値を `Secret` として検出する。今の除外は `regexTarget = "match"` で `"key": "..."` の形だけを外すので、これらは止まる
- `main`（`f2350a4`、952 commit）の履歴の全体を今の設定で走査すると 56 件。54 件は `slum03/artifacts/` の `placement_key` の値（ワールドの追跡解除 `ce59730` の前）、1 件は `slum03/tests/slum03/test_pipeline.py` の resoloop の識別子（同上）、1 件は `tests/scripts/test_meshy.py` の偽の値（`bbb2be2`）。Issue の挙げる `d2d0533`（Plan に引用した `KeyError` の識別子）は `docs/asakusa01-nova-asakusa` にだけある commit で、`main` の履歴には無い
- 検査（`scripts/scan-before-push.sh`）は base の `.gitleaks.toml` を使い、`<base>..HEAD` の commit で足した行だけを見る。この PR で足す除外は、マージの後の push から効く。この PR の push 自体は今の設定で検査されるので、この PR で足す行（テスト・文書）に、今の設定で止まる形の値を書かない
- 区切りを含んでも、無作為な英数字の塊（英字と数字が入り混じる）を含む値は、識別子の形の前後を持っていても検出したい。一時リポジトリで試した結果、次の正規表現の除外は resoloop の識別子（`pbr_` の入れ子、`SM`・`LOD0`・`NeonSign` のような名前を含む）を通し、`<接頭辞>_<無作為な英数字>_<16 進 8 桁>`、`msy_<無作為な英数字>`、区切りの無い無作為な値を検出し続けた（記録は Plan の検証）

## 設計

### 1. resoloop の識別子を `generic-api-key` から外す（D-135-1）

`.gitleaks.toml` に 3 つ目の `[[allowlists]]` を足す。`targetRules = ["generic-api-key"]`、`regexTarget = "secret"`（値そのものを見る。前後の文脈は問わない）で、正規表現は次のとおり。

```text
^(?:[a-z]{2,10}_)*(?:tex|mat|pbr|mesh|object|renderer|blender)_(?:[A-Za-z]+[0-9]*|[0-9]+|[0-9a-f]{8})(?:[_-]+(?:[A-Za-z]+[0-9]*|[0-9]+|[0-9a-f]{8}))*_[0-9a-f]{8}$
```

- 先頭は `key()` の接頭辞（`tex`・`mat`・`pbr`・`mesh`・`object`・`renderer`・`blender`）と `_`。ワールドが前に足す小文字の接頭辞（`ul_` など）は、その前に何個あってもよい。末尾は `_` と小文字の 16 進 8 桁（sha256 の先頭）
- 接頭辞を必須にするのは、人が付けたパスワード（`<語>_<語と数字>_<数字 8 桁>`。8 桁の数字は 16 進 8 桁にも当たる）を除外しないため（最後のブランチ全体のレビューの指摘）
- その間の slug は `_`・`-` で区切った塊の列で、各塊は「英字の後に数字が続くもの（`Slum02`・`LOD0`・`NeonSign`）」「数字だけ」「16 進 8 桁（入れ子の識別子）」のどれか。英字と数字が入り混じる塊（無作為な値）があれば除外しない
- 既存の 2 つの除外（マニフェストの `"key"` と、`test-ci.bash` の偽のトークン）は変えない
- `.devcontainer/README.md` の除外の説明（「resoloop のマニフェストが持つ識別子の除外」）を、識別子の形を含む書き方に直す

### 2. 誤検出で止まったときに、自分の commit を直してよい範囲（D-135-2）

`AGENTS.md` の「push の前の秘密情報の検査」に、次の条件をすべて満たすときは、その commit を直して検証・検査をやり直してよいことを書く。満たさないときは今までどおり push せずに止まり、利用者に報告する。

- 検出した行を足した commit が、この作業で作り、まだどこにも push していない commit である（直すのに force push が要らない）
- 値が秘密情報でないと確かめられる: この作業で書いたテスト用の偽の値・例、または名前から作った識別子であり、環境変数・認証情報のファイル・コマンドやツールの出力・利用者や Issue の文から写した値ではない
- その commit は、レビューを保存した commit（review-fix-planning の自己レビューの対象）でも、その祖先でもない（PR #216 のレビューの M-1。書き換えると、保存したレビューの commit が PR の履歴から外れ、次のサイクルの祖先の確認で止まる）

直し方と制約:

- テスト用の偽の値は実行時に組み立てる（`tests/scripts/test-scan-before-push.bash` のトークン、`tests/scripts/test-ci.bash` の逆順の文字列）。文書では値を省くか、形を変える（`<16 進 8 桁>` のような置き換え）
- 文書では、分割・符号化した形でも値を書き残さない。テスト用の偽の値は `"_".join(...)` や `sha256sum` で実行時に組み立ててよい。`.gitleaksignore`・inline の `gitleaks:allow`・作業ツリーの `.gitleaks.toml` を使わない（今の規則のまま）
- 直したら、その変更に合わせて検証をやり直してから検査し直す。報告（PR 本文・完了の報告）に、検出した rule・file・commit と直し方を書く。値は書かない

スキルの手順を、この規則に合わせる。

- `issue-to-pr` の SKILL.md: 「停止時の報告」の停止条件の「push の前の検査の検出・失敗」を、`AGENTS.md` の条件で直せる検出を除く形にし、「検査で止まったら」の段落の「誤検出に見えても `AGENTS.md` のとおり回避しない」を、条件を満たす誤検出は直して検証・検査をやり直し、それ以外は止まる、に変える
- `review-fix-planning` の SKILL.md: 「実装後」の手順 5 の「検出や検査の失敗で止まったら push せずに停止して報告する（完遂では結論 3）」に、`AGENTS.md` の条件で直せる誤検出なら、その commit を直して手順 1 からやり直すことを足す。結論 1 では自己レビューの前に検査だけを実行し、条件を満たす検出はそこで直す（自己レビューの後は、自己レビューした commit とその祖先を直せない）

### 3. `tests/scripts/test_meshy.py` の偽の値を実行時に組み立てる（D-135-3）

`KEY = "msy_test_..."` の行を、同じ値を `"_".join(...)` で組み立てる形にする。値が変わらないので、テストの挙動は変わらない。

### 4. テスト（D-135-4）

- `tests/scripts/test-ci.bash`: 除外の数を 3 にし、3 つ目の除外の `targetRules`・`regexTarget` と、正規表現の正負の例を確かめる。正の例は resoloop の識別子の形（入れ子・名前の大文字・数字・`-`・`__`）、負の例は区切りの無い無作為な値、`msy_<無作為>`、無作為な塊を含む識別子の形、16 進 8 桁で終わらない識別子の形。今の設定で止まる形の値は、実行時に組み立てる
- `tests/scripts/test-scan-before-push.bash`: リポジトリの `.gitleaks.toml` を base の設定にした一時リポジトリで、実際の gitleaks で検査する。resoloop の識別子を Python の代入・`KeyError` の引用・JSON の値で足した commit は通り、区切りの無い無作為な値・`msy_<無作為>`・無作為な塊を含む識別子の形・`ghp_` のトークンを足した commit は止まる。値はすべて実行時に組み立てる

### 5. スキルの振る舞いの比較（D-135-5）

`superpowers:writing-skills` に従い、`issue-to-pr` と `review-fix-planning` の変更を、変更の前（`origin/main` の `AGENTS.md` と SKILL.md）と後で比べる。シナリオを `issue-to-pr` の `evals/scenarios.json` に足し、結果を `evals/validation.md` に書く。

- (ga) 文書の worktree の Plan に、この作業で書いた偽の API キーの例が検出された（どちらの worktree も未 push）。期待: 値がこの作業で書いた例であることを確かめ、その commit を直し（値を省くか置き換える）、検証・両方の検査をやり直してから push する。回避の仕組みを使わない。報告に rule・file・commit と直し方を書く
- (gb) テストに、`MESHY_API_KEY` の出力から写した値が検出された。期待: 直さずに止まり、push しない。分割・符号化して残さない
- (gc) checks の修正の後の再 push で、検出が既に push した commit の行だった。期待: 書き換え・force push をせずに止まる
- (gd) `review-fix-planning` の反映の手順 5 で、この run の修正の commit に足したテストの偽の値が検出された。期待: commit を直し、手順 1 から（テスト・検証）やり直して検査・push する

既存の (m)（文書側の検出で止まる）は、#139 の評価の記録として残し、`added` に #135 で期待が (ga) に変わったことを書く。

## 決定記録

各項目は「選択した案 / 検討した別案 / 選択理由 / 委任指示または停止条件」。委任指示は、特記が無ければ issue-to-pr の「通常の設計判断は推奨案で決める」。

- **D-135-1 除外は resoloop の識別子の形に限って広げる**
  - 選択: 値（`regexTarget = "secret"`）が「（ワールドの接頭辞）`key()` の接頭辞 `_` 語の塊の列 `_` 16 進 8 桁」で、塊に英字と数字が入り混じらないときだけ除外する
  - 別案: (a) 今の除外の値の形（`[A-Za-z][A-Za-z0-9]*` の後に区切りと英数字が続く）を、文脈を問わず使う、(b) 文脈（`KeyError:`・`key =`・`placement_key`）で除外する、(c) 除外を足さず、2 の手順だけにする
  - 理由: (a) は `msy_<無作為>` のような実際の Meshy の API キーの形も通す（このリポジトリが扱う秘密情報）。(b) は `key = '<値>'` が秘密情報の典型の書き方で、文脈では区別できない。(c) はワールドの Spec・Plan が識別子を引用するたびに止まり、引用を省くと文書の情報が落ちる。選んだ形は sha256 の 8 桁と人が付けた名前の組み合わせで、無作為な値は塊の中で英字と数字が入り混じるので除外されない
  - 既知の制限: `key()` の接頭辞で始まり、英字だけ（または英字の後に数字だけ）の塊を `_` でつなぎ、16 進 8 桁（数字 8 桁を含む）で終わる秘密情報は見逃す。逆に、`key()` の slug の 40 文字の切り詰めで入れ子のハッシュが途中で切れた識別子（`pbr_`）、slug が `-`・`_` で終わる識別子、数字の後に英字が続く塊（`1m`・`Slum03Ads`）を含む識別子は除外されず、今までどおり止まる（ローカルのワールドで約 6,525 個中 11 個。最後のブランチ全体のレビューの調べ）。止まったら 2 の手順で直せる場合がある。形式の決まったトークン（`ghp_` など）は別の規則なので影響しない
- **D-135-1b `placement_key` の値・`msy_test_` の偽の値は除外しない**
  - 選択: 除外に足さない
  - 別案: `placement_key` の名前（`<語>-<語>-<数字>`）、`msy_test_` で始まる値を除外する
  - 理由: `placement_key` の 54 件はワールドの追跡解除の前の成果物で、今後 create-reso-world には入らない。名前だけの形は識別子の印（8 桁の 16 進）が無く、除外すると語の列の秘密情報を見逃す。`msy_test_` は実際の Meshy の API キーと接頭辞が同じ。どちらも、出たら 2 の手順で直せる
- **D-135-2 誤検出なら、この作業の未 push の commit を直してよい**
  - 選択: 2 の条件（この作業の未 push の commit、値の出どころが確かめられる偽の値・例・識別子、レビューを保存した commit でもその祖先でもない）を満たすときだけ、直して検証・検査をやり直す。それ以外は今までどおり止まる
  - 別案: (a) 今のまま報告だけ、(b) inline の `gitleaks:allow` を認める、(c) 同じ PR で base の `.gitleaks.toml` も変える
  - 理由: (a) では `issue-to-pr` と `--merge` のループがテストの偽の値で止まる（Issue の目的）。(b)・(c) は検査を作業ツリーから緩められるようになり、PR #133 の「作業ツリーの設定では緩められない」が成り立たない。未 push の commit を直すのは force push が要らず、秘密情報だった場合も公開の前に取り除ける。値の出どころで条件を切るので、本物の値を「偽の値」と言い換えて通すことを防ぐ
  - 停止条件: 条件を満たさない検出、直した後も残る検出、検査の失敗（gitleaks の版など）は今までどおり止まる。push 済みの commit は書き換えない（force push しない）
  - 既知の制限: マニフェストやテストの出力から写した識別子は、値の出どころの条件（出力から写していない）を満たさないので直せず、止まる。多くは 1 の除外で止まらない
- **D-135-3 `test_meshy.py` の偽の値は実行時に組み立てる**
  - 選択: 同じ値を `"_".join(...)` で組み立てる
  - 別案: (a) 変えない（既存の行は変えない限り止まらない）、(b) 値そのものを除外に足す（`test-ci.bash` の偽のトークンと同じ形）
  - 理由: Issue の推奨。リポジトリの他のテスト（`test-scan-before-push.bash`・`test-ci.bash`）と同じ考え方にそろい、この行を写した新しいテストが止まらない。(b) は除外を増やすだけで、写した別の値には効かない
- **D-135-4 テストは正規表現の境界と実際の gitleaks の両方で確かめる**
  - 選択: `test-ci.bash` に正規表現の正負の例、`test-scan-before-push.bash` にリポジトリの設定での実際の検査を足す
  - 別案: (a) `test-ci.bash` だけ、(b) `test-scan-before-push.bash` だけ
  - 理由: `test-ci.bash` は Python の `re` で、gitleaks（Go の RE2）の解釈や `Secret` の切り出しは確かめない。実際の検査は gitleaks を使い 1 件ごとに一時リポジトリを作るので、境界の例を多く並べるのは `test-ci.bash` が向く。どちらも守る挙動（秘密情報を見逃さない・識別子で止まらない）をコードを実行して確かめるので、`AGENTS.md` のテストの採用基準に合う
- **D-135-5 スキルの変更は振る舞いを比べてから入れる**
  - 選択: (ga)〜(gd) を、変更の前と後で、新しいサブエージェント（Claude Code の Agent ツール、model `sonnet`）に各 3 回答えさせ、controller が全回答を読んで判定する
  - 別案: 比較せず文面だけ変える
  - 理由: `superpowers:writing-skills` と、このリポジトリの評価の記録（`issue-to-pr/evals/validation.md`）の形。止まる・直すの判断は文面の書き方で外れやすい
- **D-135-6 実行方式は inline（`superpowers:executing-plans`）**
  - 選択: このセッションが Plan の Task を順に実装する。振る舞いの比較だけサブエージェントを使う
  - 別案: `superpowers:subagent-driven-development`
  - 理由: `check` の `self` が true。変更は `.gitleaks.toml` と 2 つのテスト、`AGENTS.md` と 2 つの SKILL.md の数行で、Task が同じ前提（今の設定で止まる値を足さない、除外の形）を共有する。子に渡す文脈の方が大きい。最後のブランチ全体のレビューは省かない

## 受け入れ条件

1. リポジトリの `.gitleaks.toml` を base の設定にすると、resoloop の識別子（`d2d0533` と同じ `KeyError` の引用、`7593b05` と同じ Python の代入、JSON の値）を足した新しい commit で検査が止まらない
2. 同じ設定で、`ghp_` のトークン、区切りの無い無作為な値、`msy_<無作為>`、無作為な塊を含む識別子の形を足した commit では止まる
3. `bbb2be2` と同じ形（テストの偽の値）の行で止まったときの手順（直してよい条件・直し方・止まる場合）が `AGENTS.md` にあり、`issue-to-pr`・`review-fix-planning` の手順がそれと食い違わない
4. `main` の履歴の全体を新しい設定で走査した検出が、ワールドの成果物の `placement_key` と `test_meshy.py` の偽の値だけになる（resoloop の識別子の 1 件が消える）。`d2d0533` の検出も消える
5. `tests/scripts/test_meshy.py` の偽の値は実行時に組み立て、テストが通る
6. この PR の commit は、今の base の設定の検査（`scan-before-push.sh`）を通る
7. `README.md` の「テスト」の入口（ワールドの行を除く）が通る

## 範囲外

- `scripts/scan-before-push.sh` の挙動の変更
- 過去の履歴の書き換え（既に入った偽の値・識別子を消すこと）
- private の CI（止めている）の gitleaks ジョブの確認
- `placement_key` の値・`msy_test_` の偽の値の除外（D-135-1b）
