# Issue #122: Dev Container で uv が使う Python をシステムの Python に固定する

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/122
- 検証した基準 HEAD: `cd602e63e04e51616cd5043dd46b0cbefd8fc60e`（`origin/main`。Issue の比較の基準 `71607d9` の後は文書の変更だけ）
- 移植元: usaturn/agent-workspace の `main`、`d3f4151`（`.devcontainer/README.md` の「uv の Python 実行環境（#561）」）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-17-create-reso-world-issue122-uv-system-python.md`
- 実行許可: 2026-10-17（JST）、利用者が「#122 に着手せよ。専用 worktree を作成し、途中で止めずに推奨案で PR を出せ」と指示した。推奨案での実装、専用 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージと rebuild は利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である

## 意図

uv が uv 管理の古い Python を選んだり、必要な版が無いときに勝手にダウンロードしたりしないようにする。Dev Container の `containerEnv` に `UV_PYTHON_PREFERENCE=system` と `UV_PYTHON_DOWNLOADS=manual` を設定し、cwd に関係なく、Herdr のペインや各エージェントを含むコンテナ内のプロセスがシステムの Python（`/usr/bin/python3`、3.14.4）を使うようにする。

## 確認した事実（2026-10-17）

- uv 0.13.1。`/usr/bin/python3` は 3.14.4。今のコンテナに uv 管理の Python は無く、`~/.local/share/uv` も無い。`~/.local/share/uv` は `mounts` の対象外なので、rebuild で消える
- ルートの `pyproject.toml` と `templates/world-project/pyproject.toml` は `requires-python = ">=3.12"`。追跡しているファイルで、uv に Python の版を指定して呼ぶ箇所は無い（`.agents/skills/rst-writer/evals/` の評価用の手順を除く）。postCreate・スクリプトの uv の呼び出しは `uv run --no-project` か、プロジェクトの `uv run`・`uv sync` である
- Blender（`/usr/bin/blender`）は、システムの Python 3.14.4 と NumPy 2.3.5 で動く。`scripts/new-world.sh` が設定する `blenderExecutable` のラッパー（`templates/world-project/blender-system-python`）は、PATH から `.venv/bin` を外し `VIRTUAL_ENV` を消してから `/usr/bin/blender` を起動する。uv の Python の探索は使わない
- ローカルのワールドの `.venv` の参照先: `akichi`・`asakusa01`・`slum02`・`slum04` とリポジトリのルートは `/usr/bin` の 3.14.4。`LumenAbyss_Argon`・`LumenAbyss_Opus`・`reso-workshop` は uv 管理の 3.12（`~/.local/share/uv/python/cpython-3.12-linux-x86_64-gnu`、2026-10-12〜15 に作成）で、その interpreter は rebuild で既に消えている
- 隔離した uv 管理の 3.12（`UV_PYTHON_INSTALL_DIR`・`UV_CACHE_DIR` を一時ディレクトリに向けて導入）で確かめた結果:
  - `.venv` の無いディレクトリの `uv run --no-project python` は、既定では uv 管理の 3.12.15 を選び、2 つの設定を付けるとシステムの 3.14.4 を選ぶ
  - 2 つの設定の下で、未導入の 3.11 を `--python 3.11` で求めると、ダウンロードせずに `No interpreter found` と `Python downloads are set to 'manual'` の hint で終了コード 2 で失敗する
  - 導入済みの 3.12 は `--python 3.12` で引き続き使える（明示指定は対象外）
  - uv 管理の 3.12 を指す既存の `.venv` は、interpreter が残っていれば作り直されずに 3.12 のまま使われる。interpreter が消えていれば、`uv run` が `Ignoring existing virtual environment linked to non-existent Python interpreter` と表示して、システムの 3.14.4 で作り直す
  - 2 つの設定の下で、uv 管理の 3.12 が見える状態でも、雛形から作ったワールドの `uv run pytest` はシステムの 3.14.4 で `.venv` を作って成功し、`uv run` から起動したラッパーの Blender で `import bpy, numpy` が成功する

## 判断

- **D-1 置き場所**: `.devcontainer/devcontainer.json` の `containerEnv` に 2 つを足す（Issue の範囲）。ユーザ別の `~/.config/uv/uv.toml`、`install_beforehand.bash`、`zshrc.txt`、プロジェクトの `pyproject.toml` には重複して置かない。移植元と同じく、設定元を 1 か所にして食い違いを防ぐ
- **D-2 Blender とワールドの `.venv` への影響**: 影響は無いので、コードは変えない
  - Blender とラッパーは uv の Python の探索を使わず、Blender 自体がシステムの Python 3.14 で動く
  - 既存の `.venv` は、設定を変えても作り直されない（Issue の「対象にしない」のとおり）。interpreter が消えた `.venv`（今の `LumenAbyss_Argon`・`LumenAbyss_Opus`・`reso-workshop`）は、次の `uv run` でシステムの 3.14 に作り直される。これは設定の有無にかかわらず起きるが、設定があれば uv 管理の古い版が後で入っても選ばれない
  - README には、uv 管理の古い版を指す `.venv` の確かめ方と、作り直しが起きることを書く
- **D-3 `requires-python` をそろえるか**: この Issue ではそろえず、ルートと雛形の `>=3.12` を変えない
  - 2 つの設定で、新しく作る `.venv` と `uv run --no-project` はシステムの 3.14 を使う。#116 の helper は `uv run --no-project python` で呼ぶので、`requires-python` は効かない
  - ルートを上げると `uv.lock` の作り直しが要る。雛形を上げても、追跡対象外の既存のワールドの `pyproject.toml` は変わらず、そろわない
  - 見直す条件: 3.14 の構文を使うコードがルートのプロジェクトのテスト（`uv run pytest tests/skills .agents/skills`）の対象に入るとき（#116 の helper のテストなど）。その Issue でルートの `requires-python` を `>=3.14` にするかを決める
- **D-4 README**: `.devcontainer/README.md` の「テストの実行」と「Resonite ワールド開発ツール」の間に「uv の Python 実行環境」の節を足す。書くこと:
  - 2 つの設定の意味と、`containerEnv` に置く理由（cwd・ペイン・エージェントに関係なく効く。ほかの場所に重複して置かない）
  - 限界: 版番号を強制する仕組みではない。`--python`・`UV_PYTHON` の明示、有効な仮想環境・既存の `.venv` は別に確かめる
  - Blender とワールドの `.venv` への影響（D-2）
  - 既存コンテナの移行（移植元の「既存コンテナの移行」を、この環境に合わせて書き換える）: 旧版を参照する `.venv` の確認、rebuild（`~/.local/share/uv` は rebuild で消えるので、rebuild の前の `uv python uninstall` は要らない）、rebuild 後の確認の手順（一時ディレクトリでの通常実行が 3.14 以上・未導入の 3.12 の明示指定が `manual` で失敗すること、`verify-resonite-tooling.bash`、ワールドの `uv run pytest`）
  - 旧版で互換性を確かめる必要があるとき: 移植元の「3.14 未満で互換性を確認する場合」の、一時ディレクトリに interpreter とキャッシュを隔離する手順。`uv python install` を素のまま使うと `~/.local/bin/python3.X` が置かれて Blender を壊す（`docs/meshy-resoloop.md`）ため、`--no-bin` を付けた隔離の手順だけを案内する（エージェントの判断で範囲に含めた）
- **D-5 テスト**: 新しいテストは書かない。設定値と文書だけの変更で、コードを実行して確かめる挙動が無い（`AGENTS.md` の「テストの採用基準」、Issue の「検証」）。代わりに、`devcontainer.json` の構文の検査、`bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、上の隔離した検証、README の確認の手順を子シェルで実行した結果を PR に書く
- **D-6 PR と Issue**: PR の本文は `Refs #122` にし、マージで #122 を自動で close しない。受け入れ基準の確認（作り直した Dev Container での確認）は利用者の rebuild の後にしかできないため。#125 も同じ `containerEnv` に足すので、後からマージする側で衝突を解消する

## 2026-10-17 リビルド後の残課題への実行許可

利用者は issue-to-pr で「https://github.com/usaturn/create-reso-world/issues/122 問題解決をしてください。」と依頼し、続けて「ローカル配置の修復と、非ワールドを区別する検査仕様の変更まで進めてよいか。既存 `.venv` の再作成や別リポジトリの編集は含めない」との確認に「OK」と回答した。この具体的な範囲変更を実行許可として記録する。文書の内容承認を意味しないため状態は draft のまま。基準 HEAD は `76f1098af9f07388f4c10d55786ea9d726654171`。

PR #129 で D-1〜D-6 は実装済み。rebuild 後の Python 選択・ダウンロード抑止・Blender の成功は Issue のコメント `6236361598` に記録済み。今回の新しい変更は以下の決定記録だけで、旧設定を再実装しない。下の範囲外にあるローカルでの uv run 禁止は、今回許可された正常な system Python 3.14 の環境に限り解除する。

### 決定記録

| ID | 選択した案 | 検討した別案 | 選択理由 | 委任指示または停止条件 |
| --- | --- | --- | --- | --- |
| D-7 | 検査ルート直下のローカル設定 `.check-layout-projects.json` で、プロジェクトの相対パスから `world`・`assets`・`items` を明示指定する。未指定は従来どおり world | 名前のハードコード、AGENTS や pyproject の有無による自動分類、全件 skip | 意図的な特殊構成だけを利用者側で区別でき、壊れたワールドの必須ファイル不足を自動分類で見逃さない。個人の配置は設定を gitignore して追跡しない | 利用者の OK による検査仕様の変更許可 |
| D-8 | 設定は jq で object/string/既知の profile を検証。キーは `worlds/<英数字で始まる英数字・_-の名前>` または従来の4名だけ。存在する収集済みプロジェクトに完全一致しないキー、不正JSON、通常ファイルでない設定、jq 不足は FAIL | 不正値や古いキーを無視、glob で除外 | タイプミスや外部パス指定で検査範囲が静かに変わるのを防ぐ。設定ファイルは `--root` のディレクトリから読む | 検証不能な設定は成功扱いにしない |
| D-9 | world は既存検査を維持。assets は通常ファイルの `.resoloop.json` のみを必要とし、同梱スキル同期の検査対象外。items は world の必須ファイル・共有リンク・スキルを検査し、ルートの `flux/resoloop.flux.json` の代わりに実ディレクトリ `items/` を要求 | 特殊構成にダミーの world 雛形を補う、items の共通検査も省く | Meshy原本領域とアイテムリポジトリの既存仕様に合わせ、必要な共通検査は残す。全体の追跡・ignore・mount 検査は全profileで維持 | 有料原本・独立リポジトリ内のファイルは変更しない |
| D-10 | MyResoniteProject/akichi/slum02/slum03 の誤った共有リンク12本だけを相対深さに合わせて更新。Astra は `uv lock` のみで不足lockfileを生成 | new-world --apply の一括同期、resoloop init | --apply は誤った既存リンクを上書きせず、init は既存コンテンツを変える。lock作成だけなら環境や依存をインストールしない | 対象パスと旧値を確認・バックアップし、不一致や新規競合があれば止める |
| D-11 | akichi/slum02 の正常な system 3.14 環境は、bin 内の生成済みテキストに残る旧 `.venv` 絶対パスのみ置換。パッケージや interpreter は変えない | 環境全体の再作成、旧位置への互換symlink | 現在の interpreter と依存は正常で、移設時の絶対パスだけが起動を妨げる。再インストールや恒久的な旧パス依存を避ける | 旧パスを含む通常ファイルだけをバックアップして編集。Argon/Opus/workshopの消失した3.12環境は触らない |
| D-12 | 一時fixtureでprofileの分岐・入力拒否・未指定worldの検査維持・assetsでの同期回避をRED→GREEN確認。ローカル修復は差分と実コマンドで確認する | 設定値や文言の固定テスト | 実行ロジックには回帰テストが必要だが、ローカル設定やファイル一覧のコピーをテストにしない | root/worktreeでREADMEの検証入口を実行。ローカルはakichi/slum02の通常 `uv run pytest`、Astraに `.venv` が作られないことを確認 |

### 今回の受け入れ基準

- 標準ワールドは設定なしで従来どおり検査する。必須ファイル不足・不正profile設定は終了コード1。
- 意図的な assets/items 構成が、明示設定によって必要な検査だけを受ける。プロジェクト内容は変更しない。
- 修復後の親checkoutで、変更版 checker の `--root /workspaces/reso-world` と通常のワールド `uv run pytest` が成功する。
- 作業worktreeで README の非ワールド検証3本が成功。親checkoutの追跡ファイルは編集しないため、マージ前の旧checkerが特殊構成で失敗することは別記する。
- 新PRは Closes #122。今回の残課題を完了させる変更として公開し、マージは行わない。

### 残課題の実行記録（2026-10-17 UTC）

- 共有リンク12本、akichi/slum02のbin内16ファイルに残る旧絶対パスを修正。バックアップとの照合で指定した置換だけを確認する。`.venv`のディレクトリinodeは修復前後で同一（akichi=1283217、slum02=1798231）。
- Astraはuv.lockだけを作成し、`.venv`は存在しない。ローカルprofile設定はasakusa01-meshy=assets、reso-workshop=items。これら2領域自身には書き込んでいない。
- 親checkoutの旧.gitignoreにはまだ新しい設定の除外が無いので、同じ1パスを `.git/info/exclude` にも登録した。追跡する親ファイルは未変更。
- 修復後: 変更版checkerの `--root /workspaces/reso-world` 成功、akichiの通常 `uv run pytest` 62 passed、slum02は226 passed。環境の再作成なし。
- 作業worktree: profile回帰テストRED→GREEN、配置検査成功、Pythonテスト625 passed、Resonite toolchain検査成功。
- shell suiteの最初の実行は31/32。READMEの実在しない短縮パスを参照検査が検出したため、実際のパスとローカル設定の説明に修正。個別docs検査は成功。全体の最終再実行とブランチレビューは別途記録する。
- Argon/Opus/workshopの消失したuv管理3.12参照は、許可の対象外として保持。ResoLoopのスキル更新警告も自動更新しない。

## 範囲外

- 既存の `.venv` の作り直し、`--python`・`UV_PYTHON` で版を明示した場合（Issue の「対象にしない」）
- `requires-python` の変更（D-3）、`AGENTS.md`・`CLAUDE.md` への規則の追加
- Dev Container 外の環境での Python の選択
- この作業の中で、ローカルのワールドの `.venv` に `uv run` を実行すること（追跡対象外の利用者の作業物で、作り直しが起きるため）
- rebuild と、作り直した Dev Container での受け入れ確認（利用者が行う）
