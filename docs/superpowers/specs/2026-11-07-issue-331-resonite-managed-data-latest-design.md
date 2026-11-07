# Issue #331 Resonite managed data の最新版を latest リンクと環境変数で指す 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/331（関連: #326 / PR #327、#283）
- 実行許可: 利用者の指示 `/issue-to-pr #331 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- Issue の本文の「今回の依頼は Issue の作成まで。実装は別途指示を待つ」の「別途指示」は上の指示とみなす。Windows・Resonite の操作、WSL 側の実データの変更、rebuild は許可に含めない（対象外。rebuild 後の確認は利用者が行う）
- 許可された範囲: `.devcontainer/copy-resonite-managed-data.bash`・`.devcontainer/test-copy-resonite-managed-data.bash`・`.devcontainer/devcontainer.json` の `containerEnv`・`.devcontainer/README.md` の managed data の記述・この Spec と Plan
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` の `main`（`refs/heads/main`）`afa86e0967ec71135a37365fd15933e819acf6e1`。親 Issue・handoff の base の要求は無い
- ループの設定: `loop.py check-options`（利用者の指定なし）で、サイクルの上限 3（既定の適用）、レビュアー・担当は agent-runner の設定どおり（既定の適用）
- Plan の Task の担当: `implement_task.py check` で `self`（雛形 `.devcontainer/agent-runner.toml` の既定の適用）

## 目的

利用者は常に最新の Resonite を使う。Resonite を更新するたびに `--library-path`・`RESONITE_MANAGED_DATA_PATH`・`.resoloop.json` の指定先を手で切り替える手間と、切り替え忘れで古い版の DLL のまま作業する危険を無くす。コピーのスクリプトが照合に成功した最新の版へ `latest` を付け替え、コンテナは常に `latest` を指す。

## 確かめた事実（2026-11-07、このコンテナ）

1. 共有フォルダはコンテナに `ro` で mount され、`2026.11.6.1136` の版のフォルダがある。`RESONITE_MANAGED_DATA_PATH` は未設定
2. 一時ディレクトリに `2026.11.6.1136 -> <共有フォルダの版>`、`latest -> 2026.11.6.1136`（相対）を作り、`RESONITE_MANAGED_DATA_PATH=<一時>/latest` で `resoloop doctor`（resoloop 0.2.0）の `flux-sdk`・`resonite-managed-data` が `pass`（3321 Froox nodes）、`resoloop flux check`・`flux build` が終了コード 0 で `.brson` ができた。相対 symlink を flux-sdk がたどれる
3. `RESONITE_MANAGED_DATA_PATH` が存在しないパス（`.../latest`）を指すと、doctor の `resonite-managed-data` は `warning` で `Configured path failed the Flux-SDK check/build probe: <パス>. at FluxSDK.CLI.Main.main(...)`、suggestion は `Correct RESONITE_MANAGED_DATA_PATH or omit it to retry Flux-SDK auto-discovery.`
4. `initialize.bash` は共有フォルダ自体がリンク・ファイルのときだけ止まり、中身は見ない。中の `latest` の symlink は今のままで許される
5. `.devcontainer/run-tests.bash` は `.devcontainer/test-*.bash` を拾う。`scripts/check-layout.sh` の mount の照合は `mounts` だけを見て、`containerEnv` は見ない

## 決定記録

### D1. `latest` の付け替えをコピーのスクリプトに入れる

- 選択した案: `copy-resonite-managed-data.bash` が、コピーと照合が成功して `SHA256SUMS` を置いた後にだけ、共有フォルダの直下の `latest` を相対 symlink `latest -> <版>` にする
- 検討した別案: 別のスクリプトに分ける（利用者が実行する手順が増え、付け替え忘れが残る）。`initialize.bash` で起動時に最新を選ぶ（rebuild のたびにしか変わらず、照合の結果を見られない）
- 選択理由: Issue の方針 1 のとおり。照合の成功と付け替えを同じ実行の中で順に行える
- 委任指示: issue-to-pr の推奨案での委任

### D2. 付け替える条件（版の比較）

- 選択した案: 共有フォルダの直下にある、symlink でない実ディレクトリで、名前が版の規則に合い（`latest` を除く）、通常のファイルの `SHA256SUMS` を持つものを「照合済みの版」とする。今回の版を加えた照合済みの版を `LC_ALL=C sort -V` で並べ、最後（最も新しい）が今回の版のときだけ付け替える。そうでなければ `latest` を変えず、`latest` が指す先は変えなかったことと、最も新しい照合済みの版を表示して終了コード 0 で終わる（コピーと照合は成功しているため）
- 検討した別案: 今の `latest` の指す先とだけ比べる（`latest` が無い・壊れているときの扱いが別になり、照合していない版を指す `latest` に引きずられる）。`--force` で古い版へも付け替える（固定したいときは `--library-path` で足り、YAGNI）
- 選択理由: 古い版を後からコピーしても戻さない、照合していない・中断した版（`SHA256SUMS` が無い）を最新とみなさない、の 2 つを同じ規則で満たす
- 委任指示: issue-to-pr の推奨案での委任

### D3. 途中の状態を残さない付け替え

- 選択した案: 共有フォルダの直下に `mktemp -u` 相当の一意の一時名（`.latest.XXXXXXXX`。版の名前は英数字で始まるので重ならない）で `ln -s -- <版> <一時名>` を作り、`mv -T -- <一時名> <root>/latest` で置き換える（rename(2) なので、`latest` は常に旧か新のどちらかを指す）。失敗したら一時名を消す
- 検討した別案: `ln -sfn`（unlink と symlink の 2 段で、間に `latest` が無い時間ができる）
- 選択理由: Issue の「途中の状態を残さない」のとおり
- 委任指示: issue-to-pr の推奨案での委任

### D4. `latest` が symlink 以外・版の名前が `latest` のとき

- 選択した案:
  - `--version` が大文字・小文字によらず `latest` なら、引数の誤り（終了コード 2）として何も作らずに止まる
  - `latest` が存在して symlink でない（実ディレクトリ・ファイルなど）なら、コピーを始める前（版のフォルダを作る前）に終了コード 1 で止まる。付け替えの直前にももう一度確かめ、そのときに symlink 以外なら上書きせず、コピーと照合は済んだが `latest` を変えなかったことを表示して終了コード 1 で終わる
  - 既にある `latest` の symlink は、指す先によらず（壊れている、外を指すなどを含む）付け替えの対象にする（書くのはこのスクリプトだけで、書く値は検査済みの版の名前）
- 検討した別案: `latest` の実ディレクトリを消して作り直す（利用者が置いたものを壊す）
- 選択理由: Issue の受け入れ基準「何も変えずに止まる」のとおり。事前の確認で版のフォルダも作らない
- 委任指示: issue-to-pr の推奨案での委任

### D5. 既にコピーした版に `latest` を作る方法

- 選択した案: オプション `--relink-latest --version <版>`（`--source` は取らない）。既にある版のフォルダが実ディレクトリで `SHA256SUMS` を持つことを確かめ、`SHA256SUMS` でその中を照合し直し（`sha256sum --strict -c` と、一覧以外のファイルが無いこと）、通ったら D2 の規則で `latest` を付け替える。版のフォルダの中身は変えない。照合に失敗したら `latest` を変えずに終了コード 1
- 検討した別案: README に手で `ln -s` する手順を書く（照合をやり直さず、途中の状態を残す方法になりやすい）
- 選択理由: 今回の `2026.11.6.1136` に、照合をやり直したうえで `latest` だけを作れる
- 委任指示: issue-to-pr の推奨案での委任

### D6. コンテナの環境変数

- 選択した案: `devcontainer.json` の `containerEnv` に `RESONITE_MANAGED_DATA_PATH=/home/vscode/.local/share/create-reso-world/resonite-managed-data/latest` を足す
- 検討した別案: `remoteEnv`（VS Code が開いたプロセスにだけ効き、`docker exec` などの経路で欠ける）。zshrc で export する（シェルの種類に依存する）
- 選択理由: コンテナの全プロセスに効く。mount と同じく `/home/vscode` を直接書く
- 委任指示: issue-to-pr の推奨案での委任

### D7. `initialize.bash` に `latest` の検査を入れるか

- 選択した案: 入れない
- 検討した別案: `latest` が symlink で、指す先が `/` を含む（共有フォルダの外を指しうる）なら止まる
- 選択理由: `latest` を書くのはコピーのスクリプトだけで、書く値は版の規則に合う名前（`/` を含まない）に限る。コンテナの起動を止める検査を足すより、README に手で作らないことを書く。mount は読み取り専用で、flux-sdk は DLL を読むだけ
- 委任指示: issue-to-pr の推奨案での委任

### D8. README

- 選択した案: 「Resonite の managed data（ProtoFlux、任意）」の節の、`initialize.bash` の説明・状態の表・手順 2〜6 を、`latest` と環境変数に合わせて直す。状態の表の「指す先を設定していない」を「DLL をまだコピーしていない（`latest` が無い）」に変え、事実 3 の文を書く。特定の版に固定するときは `--library-path` を使うこと（`.resoloop.json` は環境変数より優先度が低く効かない）、`latest` が指す版のフォルダは消さないことを書く。ProtoFlux の節の概要の文も合わせる
- 委任指示: issue-to-pr の推奨案での委任

## テストの方針（AGENTS.md の「テストの採用基準」）

既存の `.devcontainer/test-copy-resonite-managed-data.bash` に足す。どれも壊れてもエラーにならず、古い版・照合していない版の DLL を気付かないまま使う、利用者が置いたものを上書きする損害が残る（S）。

- 正常例: 新しい版のコピーで `latest` が相対リンク `<版>` を指す（拒否のテストの正常例を兼ねる）
- 既存より古い版（`sort -V` で古く、文字列では新しい名前）のコピーで `latest` が変わらない
- 照合に失敗したコピーで `latest` が変わらない（既存の失敗の種類の 1 つで確かめる）
- `SHA256SUMS` の無い（中断した）より新しい版のフォルダがあっても、照合済みの新しい版のコピーで `latest` が付け替わる
- `latest` が実ディレクトリのとき、版のフォルダを作らずに止まり、何も変えない
- `--version latest` で何も作らずに止まる
- `--relink-latest`: 照合済みの版で `latest` が作られる。中身を変えた版では `latest` が変わらない

`devcontainer.json` の値と README は F（固定値）なので書かない。代わりに JSON の解析（`check-layout.sh`）と `git diff` で確かめる。

## 受け入れ基準

- 動作環境: コピーのスクリプトは WSL（コンテナの外）の bash・GNU coreutils。テストはこのコンテナで、偽の DLL と `env HOME=<一時>` で実行する。環境変数は rebuild 後のコンテナ
- 実入力: 版の名前は `2026.11.6.1136` の形（数字と `.`）。比較は `2025.9.9.9` < `2025.11.3.1234`（文字列順と逆）を含む。コピー元のパスは空白・括弧・日本語を含む（既存のテストの偽のコピー元）
- 防御範囲: 対象は共有フォルダの直下の `latest` だけ。照合済みの版のうち最も新しい版のときだけ付け替える。対象外の反例: 照合に失敗した・中断した版、既存より古い版、`latest` が symlink 以外、版の名前が `latest`（どれも `latest` を変えない）。古い版のフォルダの削除・Resonite の版の自動検出はしない
- rebuild 後のコンテナでの `RESONITE_MANAGED_DATA_PATH`・doctor・check・build の確認は、マージの後に利用者が行う（PR と Issue に残す）
