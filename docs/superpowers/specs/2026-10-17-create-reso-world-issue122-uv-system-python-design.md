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

## 範囲外

- 既存の `.venv` の作り直し、`--python`・`UV_PYTHON` で版を明示した場合（Issue の「対象にしない」）
- `requires-python` の変更（D-3）、`AGENTS.md`・`CLAUDE.md` への規則の追加
- Dev Container 外の環境での Python の選択
- この作業の中で、ローカルのワールドの `.venv` に `uv run` を実行すること（追跡対象外の利用者の作業物で、作り直しが起きるため）
- rebuild と、作り直した Dev Container での受け入れ確認（利用者が行う）
