# Issue #326 Resonite managed DLL を手動で準備する PowerShell・Bash スクリプト 設計

## 管理

- 状態: draft
- Issue: https://github.com/usaturn/create-reso-world/issues/326（関連: #283）
- 実行許可: 利用者の指示 `/issue-to-pr #326 --merge`。issue-to-pr スキルにより、通常の設計判断を推奨案で決め、検証・commit・push・PR の作成まで続ける。`--merge` により、PR の作成後に pr-review-fix-loop を回し、修正不要と確かめられたら `finalize.py` がマージと Issue の更新を行う
- Issue の本文の「スクリプトの実装・実行と、実 DLL を使う確認は別途指示を待つ」のうち、実装と偽 DLL での実行は上の指示で許可されたものとして扱う。実 DLL・Windows・Resonite を使う確認は許可に含めない（対象外）
- 許可された範囲: `.devcontainer/find-resonite-managed-data.ps1`（新規）・`.devcontainer/copy-resonite-managed-data.bash`（新規）・`.devcontainer/test-copy-resonite-managed-data.bash`（新規）・`.devcontainer/README.md` の「Resonite の managed data（ProtoFlux、任意）」の節・この Spec と Plan
- この文書の commit は実行許可の記録であり、内容の承認（`approved`）ではない
- base: `usaturn/create-reso-world` の `main`（`refs/heads/main`）`4aa1ca04e51ec4bfe75873455e5465248edf2b81`。親 Issue・handoff の base の要求は無い
- ループの設定: `loop.py check-options`（利用者の指定なし）で、サイクルの上限 3（既定の適用）、レビュアー・担当は agent-runner の設定どおり（既定の適用）
- Plan の Task の担当: `implement_task.py check` で `self`（雛形 `.devcontainer/agent-runner.toml` の既定の適用）

## 目的

`.devcontainer/README.md` の手作業（Windows でコピー元を探す、WSL へ版ごとにコピーして照合する）を、利用者が手動で実行する 2 本のスクリプトにする。誤ったフォルダの自動採用、既存の版への上書き、範囲外への書き込み、照合していないコピーの成功報告を防ぐ。

## 確かめた事実（2026-11-07）

1. `initialize.bash` は `$HOME/.local/share/create-reso-world/resonite-managed-data` がリンク・ファイルなら止まり、無ければ実ディレクトリで作る。`devcontainer.json` は同じパスをコンテナの `/home/vscode/.local/share/create-reso-world/resonite-managed-data` に読み取り専用で mount する
2. README の手順 2 は `mkdir "$dest"` → `cp -p "$src"/*.dll` → コピー元で作った `SHA256SUMS` を版のフォルダに置いて `sha256sum -c` する形。手順 1 は PowerShell の 2 行（`Get-Process`・`Get-ChildItem -Recurse`）
3. このコンテナに `pwsh`・`shellcheck` は無い。`dotnet` 10 の SDK はある（`dotnet tool install PowerShell --tool-path <一時>` で pwsh を一時的に用意できる）。`shellcheck` は PyPI の `shellcheck-py` を `uv tool run` で一時的に使える
4. `.devcontainer/run-tests.bash` は `.devcontainer/test-*.bash` を自動で拾う。usaturn/create-reso-world の CI は停止中

## 決定記録

### D1. スクリプトの名前と置き場所

- 選択した案: `.devcontainer/find-resonite-managed-data.ps1`（Windows で探す。読むだけ）と `.devcontainer/copy-resonite-managed-data.bash`（WSL でコピーして照合する）
- 検討した別案: `scripts/` に置く（`scripts/` はコンテナの中で使うリポジトリのツールで、WSL の初回準備は `initialize.bash` と同じ `.devcontainer/` が合う）。1 本の Bash から `powershell.exe` を呼ぶ（WSL の interop が無効な環境で動かず、Windows 側の手順を利用者が確かめられない）
- 選択理由: Issue の方針の 2 本と置き場所のとおり
- 委任指示: issue-to-pr の推奨案での委任

### D2. PowerShell のコピー元の決め方

- 選択した案: 引数 `-InstallPath`・`-ManagedPath`・`-ResoniteVersion`（すべて任意）。
  - `-ManagedPath` を指定したら、そのフォルダ直下に `FrooxEngine.dll` があるかだけを確かめて使う
  - それ以外は、`-InstallPath` か、実行中のプロセスのうち名前が `Resonite` で始まるものの実行ファイルのフォルダをインストール先にする。そのうち `Path` を読めない（null か取得で例外）ものが 1 つでもあれば、どれも選ばずに終了コード 1 で止まり、`-InstallPath`（または `-ManagedPath`）を求める。プロセスのフォルダが 2 つ以上なら一覧を出して `-InstallPath` を求め、0 なら起動か `-InstallPath` を求める
  - インストール先の下を再帰で探した `FrooxEngine.dll` が 1 つならそのフォルダ、2 つ以上なら一覧を出して `-ManagedPath` を求め、0 なら止まる
  - 結果として、コピー元のフォルダ、直下の `*.dll` の数、`FrooxEngine.dll` のファイル版（参考。Resonite の版ではないと明記）、WSL で実行するコマンド（`wslpath -u` の単一引用符の中に Windows のパスを入れ、`'` は `'\''` に置き換える）を表示する。`-ResoniteVersion` が無ければ版の部分は `<Resonite の版>` のまま表示する
  - 終了コード: 0 は 1 つに決まった、1 は決められない（候補 0・複数）、2 は引数の誤り
  - 書き込みはしない（`Get-Process`・`Get-ChildItem`・`Test-Path`・`Get-Item` だけを使う）。メッセージは英語・ASCII のみにする
- 検討した別案: 候補が複数なら実行中のプロセスに近いものを選ぶ（Issue の「勝手に選ばず明示指定を求める」に反する）。`Resonite_Data\Managed` を最初に見る（決め打ちの禁止に反する）。日本語のメッセージ（Windows PowerShell 5.1 は BOM の無い UTF-8 の .ps1 を ANSI として読み、文字化けする。BOM を付けると他のツールで扱いにくい）
- 選択理由: 自動採用の防止と、Windows PowerShell 5.1 と PowerShell 7 の両方で同じに動くこと
- 委任指示: issue-to-pr の推奨案での委任

### D3. Bash のコピーと照合

- 選択した案: `copy-resonite-managed-data.bash --source <WSL のパス> --version <版>`。
  - 版は `^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$` だけを受け付ける（`/`・`..` の脱出、空、先頭の `.`・`-` を拒否）
  - 共有先 `root=$HOME/.local/share/create-reso-world/resonite-managed-data` がリンク・ファイルなら止まる。無ければ `mkdir -p` で作る（`initialize.bash` と同じ）
  - コピー元はディレクトリで、直下に通常のファイルの `FrooxEngine.dll` があること。直下の `*.dll` に通常のファイルでないもの（symlink・ディレクトリ）があれば止まる。コピー元が共有先の中なら止まる
  - 版のフォルダは `mkdir`（`-p` なし）で作り、既にある（リンク・壊れたリンクを含む）なら止まる。作った後に、リンクでないことと、`realpath` の親が `realpath "$root"` であることを確かめる
  - コピー元の直下の `*.dll` の SHA-256 の一覧を一時ファイルに作り、各 DLL を `cp -p --` でコピーし、コピー後にコピー元の直下の `*.dll` の名前の集合と SHA-256 の一覧を作り直して最初と一致することを確かめる（コピー中のコピー元の DLL の追加・削除・内容の変更。Resonite の更新）。版のフォルダで一覧を `sha256sum -c` し、版のフォルダの `*.dll` の名前の集合が一覧と一致することを確かめる。全部通ったら一覧を `SHA256SUMS` として版のフォルダに置き、`copied and verified` と、コンテナから参照するパスを表示する
  - 失敗したら、成功の文を出さずに非 0 で終わり、残った版のフォルダの完全パスと、再試行の前に確かめること（Resonite を更新中でないか、コピー元が正しいか、残ったフォルダを自分で確かめて消すこと）を表示する。版のフォルダを自動で消さない
  - 設定ファイル・シェルの設定・`RESONITE_MANAGED_DATA_PATH` は変えない
- 検討した別案: 一時フォルダにコピーしてから版の名前へ `mv` する（失敗時に残るのが一時フォルダになり分かりやすいが、Issue の「残ったコピー先を示す」で足り、名前の衝突の判定が 2 か所になる）。`SHA256SUMS` を版のフォルダに最初に置く（照合に失敗したフォルダにも一覧が残り、照合済みと見分けにくい）。`--source` に Windows のパスも受け付けて `wslpath` で変換する（`\` の引用の誤りが増える。PowerShell が `wslpath -u` を含むコマンドを出す）
- 選択理由: Issue の受け入れ基準のとおりで、README の手作業の手順と同じ配置（版のフォルダの `SHA256SUMS`）を保つ
- 委任指示: issue-to-pr の推奨案での委任

### D4. テスト

- 選択した案: `.devcontainer/test-copy-resonite-managed-data.bash` に、隔離した一時 HOME（`env HOME=...` のワンショット）と、実行時に作る偽 DLL で、S の条件だけをテストする: (1) 正常例（空白・括弧・日本語を含むコピー元、直下でない DLL と DLL 以外は複写しない、一覧と内容が一致、コピー元が変わらない）、(2) 既存の版のフォルダを変えずに拒否、(3) 版の `../` 等の脱出を拒否して範囲外に何も作らない、(4) 共有先が symlink なら拒否してリンク先に書かない、(5) 版のフォルダが壊れた symlink なら拒否してリンク先に作らない、(6) PATH の偽 `cp` で内容を壊す・1 件を落とすと成功と報告せず、版のフォルダを消さない
- 検討した別案: PowerShell のテストもコミットする（このコンテナと CI に pwsh が無く、常に skip するテストは守りにならない）。引数の解析・ヘルプのテスト（L）
- 選択理由: AGENTS.md のテストの採用基準。PowerShell は一時的に用意した pwsh で、偽のインストール先（候補 1・2・0、`-ManagedPath`、空白・括弧・日本語・`'` を含むパス）に対して実行して確かめ、結果を報告する（コミットしない）
- 委任指示: issue-to-pr の推奨案での委任

### D5. README

- 選択した案: 「Resonite の managed data（ProtoFlux、任意）」の手順 1・2 を、2 本のスクリプトの実行に置き換える。Windows → WSL → Dev Container の実行場所と順序、`powershell -NoProfile -ExecutionPolicy Bypass -File` での起動（実行ポリシーの設定は変えない）、対応する版（Windows PowerShell 5.1 と PowerShell 7）と使うコマンド、WSL で必要なコマンド（bash・coreutils の `sha256sum`・`realpath`・`cp`、`wslpath`）、空白・括弧・日本語のパスの例、更新中にコピーしない・上書きしない、失敗時の扱い、コピー・照合の成功と check/build の成功と実機の確認の区別を書く。手順 3〜6 は残し、手順 6 の「1・2 のとおり」を保つ
- 検討した別案: 手作業の手順も併記する（2 通りの手順が食い違う。スクリプトは数十行で読める）
- 委任指示: issue-to-pr の推奨案での委任

## 受け入れ基準

- 動作環境: Bash は WSL2 の Linux（コンテナの外）の bash 4 以上と GNU coreutils。テストはこの Dev Container（Ubuntu 26.04）の bash で実行する。PowerShell は Windows 11 の Windows PowerShell 5.1 と PowerShell 7。このコンテナでは Linux 版の pwsh 7 で偽のインストール先に対して確かめ、Windows の実機・実 DLL では確かめない（未検証として報告する）
- 実入力: コピー元 `…/Program Files (x86)/Steam/steamapps/common/リゾナイト テスト/` のような空白・括弧・日本語を含むパス、版 `2025.11.3.1234` のような文字列、`FrooxEngine.dll` を含む複数の `*.dll`、DLL 以外のファイル、サブフォルダの DLL
- 防御範囲: 対象は、版の文字列による脱出（`../x`・`a/b`・`.`・`..`・空）、共有先の symlink、版のフォルダの既存（実ディレクトリ・symlink・壊れた symlink）、コピーの欠落・内容の不一致・コピー中のコピー元の変化、PowerShell の候補 0・複数。対象外は、`$HOME` や `~/.local` 自体が symlink である配置（利用者の HOME の構成として受け入れる）、スクリプトの実行中に他のプロセスが共有先を書き換える競合、Windows の実行ポリシー・署名、実 DLL での SDK の check/build

## 実装の結果（2026-11-07）

- 実行方式: `superpowers:executing-plans` で inline（Plan の「実行方式」）
- Bash: `.devcontainer/test-copy-resonite-managed-data.bash` が PASS。一時的な改変（`mkdir -p`、ハッシュの照合・コピー元の変化の検出・版の検証・共有先のリンクの拒否を外す）の 5 つはすべてテストが FAIL で検出した。コピー先のファイル一覧の照合を外す改変は検出しない（欠落と内容の違いはハッシュの照合が見つけ、一覧の照合は対象外とした外部からの追加への重ねの守りのため、テストを足さない）
- shellcheck（`uv tool run --from shellcheck-py shellcheck`）: 2 ファイルで警告なし
- PowerShell: このコンテナに一時的に導入した Linux 版 pwsh 7.6.9 で、構文解析、ASCII のみ、偽のインストール先（空白・括弧・日本語・`'` を含む）に対する候補 1・2・0、`-ManagedPath`、`-ManagedPath` に DLL が無い、版の誤り（`../x`・末尾の改行）、`-InstallPath` と `-ManagedPath` の同時指定、偽の `Resonite` プロセス 1 つ・2 つのフォルダを確かめた。表示した WSL のコマンドを偽の `wslpath` と一時 HOME で bash に渡し、コピーと照合が通ることも確かめた。Windows PowerShell 5.1・Windows 11 の実機・実 DLL では確かめていない（未検証）
- 全体のレビュー（Claude Code のサブエージェント、読むだけ）: 致命的な指摘なし。軽微な指摘のうち、PowerShell の版の検証の `$` を `\z` にする、DLL の数を大文字小文字を区別して数える、の 2 つを採用して修正した。コピー先の一覧の照合とコピー元が共有先の内側の拒否のテストの追加は、上の理由で採用しない
