# ProtoFlux 用の Resonite managed data をコンテナと共有する設計

## 管理と実行許可

- 文書管理・対象: `usaturn/create-reso-world`、Issue #283
- 状態: `completed`（リポジトリの変更の実装・検証・レビューを完了。内容の承認を意味しない。rebuild・実 DLL での確認は下記のとおり未実施）
- 利用者の指示: `/issue-to-pr https://github.com/usaturn/create-reso-world/issues/283 --merge`。実行中に追加で「コメントも確認してください」「https://github.com/usaturn/resoloop 上流にPRすることが必要かどうかも検討して。」
- 許可: 通常の設計判断を推奨案で決め、検証・commit・push・PR 作成の後、PR 修正ループを回す。マージはループの `finalize.py` だけが行う。実行の指示は実行許可であり、内容の承認（`approved`）ではない。
- 調査した基準: `origin/main` = `a204b51f1e05cf0668be1c0724cf93f107ee8436`。ResoLoop は導入済みの 0.2.0 と、その公開の commit `orange3134/resoloop@a7be2dd`（`external/resoloop` の `upstream/main`）を読んだ。
- 関連: [Issue #283 の調査結果と解決案のコメント](https://github.com/usaturn/create-reso-world/issues/283#issuecomment-6431753810)、#251・#252（flux-sdk の導入。どちらも closed）

## 意図と原因

Dev Container に flux-sdk は入るが、ProtoFlux のグラフの check・build・配備には Windows ホストにある Resonite の managed DLL（`FrooxEngine.dll` など）が要る。flux-sdk の自動探索は、コンテナ内の SDK の配置先と Linux の Steam の配置先しか見ないので、コンテナからは必ず失敗する。既定の mount にも DLL の置き場所が無い。

この run で、DLL が無いコンテナで次を実測した。

- `resoloop doctor --json` の `resonite-managed-data` は `warning` で、メッセージは `Not explicitly configured; Flux-SDK auto-discovery failed: at FluxSDK.CLI.Main.main(String[] args) in /workspace/Flux-SDK/src/FluxSDK.CLI/Main.fs:line 32`（Issue と同じ）。ResoLoop 0.2.0 の `FluxManagedDataProbe` は、構造化した診断が無いと SDK の出力の最後の行を選ぶため、例外の最後の行だけが出る
- `resoloop doctor --library-path <dir> --json` は受け付けられる。設定の解決（`ConfigResolver`）が全コマンド共通で、`doctor` の使い方の行に書かれていないだけである
- `resoloop flux check <file.pg> --project <dir> --json` は終了コード 9 で、stderr の JSON（`error.code` が `FLUX_COMMAND_FAILED`）の `error.context.stderr` に、SDK の元のエラー（見つからない 11 個の DLL と、探したディレクトリの一覧）がそのまま残る

足りないのは、DLL をコンテナから読める場所と、その用意・確認の手順である。ResoLoop と flux-sdk の挙動は変えなくても、この Issue の条件は満たせる。

## 条件と除外範囲

1. WSL 側の専用のディレクトリ `~/.local/share/create-reso-world/resonite-managed-data` を、コンテナの同じパス（`/home/vscode/.local/share/create-reso-world/resonite-managed-data`）に読み取り専用で bind mount する。ほかのホストのディレクトリ（`/mnt/c`、Windows のユーザーフォルダ、Steam のライブラリ）は公開しない。
2. `initialize.bash` は、共有元が無ければ空の実ディレクトリを作る。中身（利用者がコピーした DLL）は変えない・消さない。DLL を探す・コピーする処理は持たない。
3. 共有元がリンク・ファイルなど実ディレクトリでなければ、`initialize.bash` は理由を表示して非 0 で止まる（mount の前）。リンクを mount すると、リンク先（Resonite のインストール先全体や `/mnt/c` など）がそのままコンテナに見え、エラーにならないため。
4. DLL を用意していない利用者のコンテナは、今までどおり起動する（空のディレクトリが mount されるだけ）。
5. 使う版は利用者が選ぶ。`initialize.bash`・`--env-file` で `RESONITE_MANAGED_DATA_PATH` を自動では設定しない。「いちばん新しいサブディレクトリ」や「フォルダがあること」を準備済みの判定にしない。
6. `.devcontainer/README.md` に、DLL が無いときに何をどこへ用意するか（Windows で DLL の場所を確かめる→WSL で版ごとのフォルダへコピーして SHA-256 で照合→rebuild→コンテナで読み取り専用と DLL を確かめる→doctor と非空のグラフの check・build→設定の保存）と、未設定・準備済みの見え方、doctor が最後の行しか出さないときに SDK の元のエラーを読む方法を書く。`docs/integration.md` の「Rebuild 後に確かめること」には、任意の確認としてこの節への参照を足す（全員が必須の確認にはしない）。
7. DLL・その記録はリポジトリ・Docker イメージ・配布物に入れない。
8. 除外: ResoLoop・flux-sdk の変更、Resonite・SDK の更新、ワールドのプロジェクトの変更、利用者の HOME や `~/.config/create-reso-world/env` の変更、Windows の DLL の特定・コピー・rebuild・実 DLL での check/build（この run では行えない。マージの後に利用者が行う）。

### Issue の受け入れ条件との対応

| Issue の受け入れ条件 | この変更で満たすもの | マージの後に残る確認 |
| --- | --- | --- |
| DLL が無いときに、何をどこへ用意すべきか判断できる | 条件 6 の README の節。元のエラーの読み方は実測済み | — |
| 選択した DLL ディレクトリが読み取り専用で使え、資格情報や無関係なホストディレクトリを公開しない | 条件 1・3。mount の一覧・readonly・リンクの拒否をテストで守る | rebuild 後に `findmnt` で `ro` を確かめる |
| DLL 未設定の利用者のコンテナ起動を妨げない | 条件 2・4。一時 HOME で `initialize.bash` が通ることをテストで確かめる | rebuild でコンテナが起動する |
| 実行中の Resonite と対応する DLL を指定して、警告が消え、flux check/build が成功する | 手順だけ（条件 6） | 実 DLL での doctor・check・build（利用者） |
| 未設定・解消済みの両方の状況と回避策を記録する | 未設定の状況は Issue 本文とこの Spec の実測。README に両方の見え方を書く | 解消済みの記録を Issue に追記する（利用者） |

マージの後でしか確かめられない項目が残るので、PR は `Refs #283` にする（`Closes` にしない）。run の最後に、PR の URL と残りの確認を Issue にコメントする。

## 検討した案と決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示・停止条件 |
| --- | --- | --- | --- | --- |
| D1 | 利用者が DLL をコピーした WSL 側の専用ディレクトリを、読み取り専用で bind mount する | (a) Windows の DLL のディレクトリを直接 mount（写真フォルダと同じリンク方式）、(b) リポジトリの中（`.gitignore` 付き）に置く、(c) mount せず `docker cp` で入れる | 公開範囲をコピーした DLL だけにでき、未設定でも空のディレクトリで起動できる。(a) はインストール先の他のファイルまで見え、`/mnt/c` の見え方と Resonite の更新中の書き換えに左右される。(b) は誤って commit する危険と、worktree ごとに置き直す手間がある。(c) は rebuild で消える。Issue のコメントの推奨案と同じ | 通常の設計判断の委任により選択 |
| D2 | 共有元がリンク・ファイルなら `initialize.bash` が止まる | 写真フォルダと同じくリンクを許す、何も調べない | リンクを許すと D1 の (a) と同じ公開範囲になり、条件 1 を守れない。何も調べないと、リンクのまま mount されてもエラーにならない（気付けない） | 同上。リンクを使いたい利用者は、DLL をコピーする手順に従う |
| D3 | 版ごとのサブディレクトリを利用者が作り、`--library-path`・`RESONITE_MANAGED_DATA_PATH`・プロジェクトの `.resoloop.json` の `resoniteManagedDataPath` で明示して指す | `--env-file` で最新のサブディレクトリを自動で指す、`current` というリンクを決まりにする | 自動で選ぶと、実行中の Resonite と違う版の DLL を準備済みと誤って扱う。`~/.resoloop/config.json` は mount されず rebuild で消えるので、保存先の候補にしない | 同上 |
| D4 | README に手順と、未設定・準備済みの見え方、元のエラーの読み方を書く。`docs/integration.md` には任意の確認として参照だけを足す | 確認用のスクリプトを足す、postCreate で managed data を確かめる | 必要な確認は既存の `resoloop doctor`・`flux check`・`flux build` で足りる。postCreate の必須条件にすると、ProtoFlux を使わない利用者の作成が失敗する | 同上 |
| D5 | テストは `.devcontainer/test-initialize-mounts.bash` に、mount の一覧の更新（既存の F∩S）、読み取り専用の mount の一覧（F∩S、新規）、共有元のリンクの拒否と実ディレクトリの中身の保持（S、新規）だけを足す | README の文言・11 個の DLL の一覧のテスト、ファイルの共有元の拒否のテスト | readonly が外れても、リンクを受け付けても、起動はエラーにならず、ホストのファイルが書き換え・公開される（AGENTS.md の S・F∩S）。README の文言は F。ファイルの共有元は `mkdir -p` がエラーで止まる（L） | 同上 |
| D6 | ResoLoop への PR はこの Issue では作らない。doctor の表示の改善は、usaturn/resoloop の別の Issue（から上流 orange3134/resoloop への PR）の候補として報告する | この Issue の中で usaturn/resoloop に PR を作る、改善を待ってから進める | Issue の条件は ResoLoop を変えずに満たせる（`flux check --json` の `error.context.stderr` で元のエラーを読める）。Issue 本文も ResoLoop 側は「別途報告を検討」としている。issue-to-pr の対象は create-reso-world で、ResoLoop の変更は別の Issue・run になる。新しい Issue の作成は利用者の許可を得てから行う（`.agents/execution-budget.md`） | 利用者の追加指示（上流への PR の要否の検討）への回答。Issue の作成・PR は行わない |
| D7 | `executing-plans`（このセッションが inline で実装する）で 2 つの Task を順に行い、最後にブランチ全体のレビューを別のサブエージェントに依頼する | `subagent-driven-development` | `implement_task.py check` の `self` が true。Task は 2 つで、文書の Task は設定の Task の挙動をそのまま説明するので、文脈を子に渡しきるより順に書くほうが確実 | issue-to-pr の 4 章の表のとおり |
| D8 | PR 本文は `Refs #283` | `Closes #283` | 実 DLL での check/build と rebuild の確認がマージの後にしか行えない | issue-to-pr の 5 章のとおり |

### 解決した割り当て

- `loop.py check-options`（`loop_args` は空）: max_cycles = 3、assign は無し、template = `.devcontainer/agent-runner.toml`、config は無し。どれも既定の適用で、利用者の指定ではない。review.inspect = `claude-opus, devin-swe, pi-deepseek`、fix.implement = `claude-opus`、fix.self-review・fix.fix-check = `self`、fallback はすべて空（雛形の既定の適用）。
- `implement_task.py check`（`--implement` 無し）: assignment.agents = `[self]`、fallback = `[]`、self = true。雛形の既定の適用であり、利用者の指定ではない。

## ResoLoop 側の改善候補（D6 の持ち越し）

この Issue では行わない。利用者の許可があれば、usaturn/resoloop に Issue を作り、fork で直してから orange3134/resoloop に PR を出す（`docs/resoloop-fork-workflow.md`）。

1. `FluxManagedDataProbe` は、構造化した診断が無いとき、SDK の出力の最後の行（例外のスタックの最後の行）を表示する。例外の先頭（`When loading the Froox engine DLL's I couldn't find the following:` と、足りない DLL・探したディレクトリ）を表示すれば、doctor だけで何が足りないか分かる。
2. `resoloop doctor` の使い方の行（`resoloop doctor [--url ws://localhost:PORT] [--json]`）に `--library-path` が無い。実際には受け付ける。

## 検証と残る確認

- `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`（README の「テスト」のうち、ワールドの行を除く）
- 足したテストが守りを確かめていることを、一時的な変異（`readonly` を外す、リンクの検査を外す）で確かめる。変異はコミットしない
- README の手順のうち、この container で実行できるもの（DLL が無いときの doctor・`flux check --json` の `error.context.stderr`、`findmnt` の `ro` の読み方）は実測済み。DLL がある状態の doctor・check・build と、rebuild 後の mount は、マージの後に利用者が確かめる

## 実装とブランチ全体のレビュー（PR 作成前）

- 実装: Task 1 `58388d0`（mount・`initialize.bash`・テスト）、Task 2 `39d64f3`（README・`docs/integration.md`）、レビュー修正 `fe287a7`、Plan の記録 `44e8c46`。経過と裁定は Plan の「完了」にある
- ブランチ全体のレビュー（新しいサブエージェント、読み取り専用）: Critical 0、Important 1、Minor 4。README のコピーの手順が `mkdir` の失敗後も続いて版が混ざったまま `copied and verified` と出る問題（Important 1）を再現してから `&&` でつなぐ形に直し、照合の一覧をコピー元で作る向きにした（Minor 1）。表の行名（Minor 2）は Important に上げて直した。リンクを消す案内（Minor 3）と、ProtoFlux の節の指し方の列挙の `.resoloop.json`（Minor 4）は先送り

## PR #284 レビュー修正ループ・サイクル 1 の結果

- 対象: `usaturn/create-reso-world` PR #284、レビュー HEAD `44e8c46d4d1659ab0907602490f42b7798eb8b3a`、base `a204b51f1e05cf0668be1c0724cf93f107ee8436`
- planner: `claude-opus-5-5`、runtime `claude-code`。実行許可は冒頭の `/issue-to-pr ... --merge`（ループの既定: サイクルの上限 3）
- 結論: **2 修正不要**。全指摘 1 件 = 解消済み 0 / 対応する 0 / 対応しない 1。票数ではなく、現行のコミット済みの変更・関連処理・テスト・仕様と照合して判断した

| レビューファイル | モデル | runtime | HEAD | 再実行 | recommendation | 実測秒数 |
| --- | --- | --- | --- | --- | --- | --- |
| `claude-opus-5-5.md` | `claude-opus-5-5` | `claude-code` | `44e8c46d4d16` | はい（Initial） | Approve | 392.75 |
| `SWE-2-Max.md` | `SWE-2 Max` | `devin` | `44e8c46d4d16` | はい（Initial） | Approve | 390.21 |
| `deepseek-deepseek-v4.1-flash.md` | `deepseek/deepseek-v4.1-flash` | `pi` | `44e8c46d4d16` | はい（Initial） | Approve | 786.95 |

保存先は `/workspaces/reso-world/reviews/usaturn/create-reso-world/#284-feat-issue-283-resonite-managed-data/`。3 名とも runner の受け取りは accepted で、失敗・再実行・retained は無い。前のサイクルの判断は無い。

### 指摘の振り分け

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| `SWE-2-Max#L-1@44e8c46d4d16`（Low。共有元をリンク・ファイルにして止まったとき、メッセージと README に消し方の案内が無い） | 対応しない | 確認済みの一覧の V-1 で再現した（リンクの下に版のフォルダを作っても止まり続け、リンクを消すと通る）。ただし、文書化した手順（実ディレクトリへのコピー）から外れてリンクを作ったときだけ起き、`initialize.bash` は終了コード 1 で `must be a real directory, not a link or a file` と理由を示して止まる。データの消失・秘密情報の露出・誤った成功にはならず、致命的の条件に当たらない。PR 作成前のレビューの Minor 3 と同じ論点で、先送りの判断と一致する |

要件対応: 修正が無いので、Spec の条件 1〜8 と Issue の受け入れ条件の対応は「条件と除外範囲」の表のまま変わらない。共有する前提（パスの表記、ResoLoop 0.2.0 の挙動）は Plan の Task 3 で照合済み。

### 確認の範囲と根拠

全指摘・PR の変更 7 ファイル・関連処理（`.devcontainer/mounts.bash`、`scripts/check-layout.sh` の mount の検査、`.devcontainer/test-readme.bash`）を、コミット済みの内容で読んだ。確認済みの一覧は review-verify（mode cycle）で作り、`verified/44e8c46d4d16.json`・`.md` に保存した（confirmed 1、not_reproduced 0、unverified 0、確認 85 秒）。V-1 は、PR head を照合した隔離 worktree で、共有元がリンク・ファイル・壊れたリンクのとき止まり、実ディレクトリのとき通ることを実行で確かめた。`coverage.remaining` は rebuild・Docker の実 mount と、実 DLL・Windows 側の手順で、どちらもマージの後に利用者が確かめる項目（条件 8）。

### 検証の再利用と最終化の前提

issue-to-pr の `--merge` の規則（1 サイクル目で修正不要、サイクルの HEAD が PR 作成前に検証した HEAD と同じ）により、PR 作成前の検証を `finalize.py` の検証の記録に使う。検証の前後とも未 commit の変更は無く、すべて終了コード 0。`origin/main` を取り直し、base が上記 SHA のまま head の祖先であることを確かめた（base との一時的な merge は不要）。

- `bash .devcontainer/run-tests.bash`: 23 本 PASS、83 秒
- `bash scripts/check-layout.sh`: PASS
- `uv run pytest tests/skills .agents/skills .agents/scripts tools`: 1237 passed、465 秒
- 記録と実ログ: `/workspaces/reso-world/tmp/agents/issue-283.zm8muatb/verify-44e8c46/verification.json`、`/workspaces/reso-world/tmp/agents/issue-283.zm8muatb/checks.json`、同じディレクトリの `devcontainer.log`・`layout.log`・`pytest.log`
- 自己レビュー: 結論 2 のため未実施（修正していない）
