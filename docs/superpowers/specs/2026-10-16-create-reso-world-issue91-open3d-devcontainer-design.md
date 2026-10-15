# Issue #91: open3d のシステムのライブラリを Dev Container に入れる

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`
- 対象 Issue: https://github.com/usaturn/create-reso-world/issues/91（親 #95 のボード、子のキー `open3d-devcontainer`）
- 検証した基準 HEAD: `e7eb72a1602ac03e723bc50c9734773102947df1`（`main`）
- 状態: draft（文書の内容に対する利用者の明示承認は無い）
- 関連 Plan: `docs/superpowers/plans/2026-10-16-create-reso-world-issue91-open3d-devcontainer.md`
- 実行許可: 2026-10-16（JST）、利用者が「#91 に着手せよ。途中で止めずに推奨案で PR まで作成して」と指示した。推奨案での実装、隔離 worktree、commit、push、create-reso-world への PR の作成まで許可されている。マージと rebuild は利用者が行う。下の判断は確認を取らずに決めたエージェントの判断である
- 予約: `refs/heads/agent-claims/issue-91`（`93c587d5f2e454cc3f35ea81e43a638ffb8e0534`、#91 の issuecomment-6199566832）

## 意図

Meshy の物の UV の展開（UVAtlas）に使う open3d 0.20.0 を、rebuild した Dev Container で手作業の apt なしに import できるようにする。完了の条件は、rebuild の後に `uv run --no-project --with open3d==0.20.0 python -c "import open3d"` が成功すること、`bash .devcontainer/run-tests.bash` が成功すること、README に導入の理由が書かれていること。

## 確認した事実（2026-10-16）

- 今のコンテナでは上のコマンドが成功する（open3d 0.20.0、Python 3.14.4）。ただし `libegl1`・`libgl1` は 2026-10-12 に手で入れたもので（`/var/log/dpkg.log`、`apt-mark showmanual`）、Dev Container の定義には無い
- open3d の `pybind.cpython-314-x86_64-linux-gnu.so` を `ldd` で見ると、open3d の同梱物の外では `libEGL.so.1`（`libegl1`）・`libGL.so.1`（`libgl1`）・`libGLX.so.0`（`libglx0`）・`libGLdispatch.so.0`（`libglvnd0`）・X11 系・`libudev1`・`libusb-1.0-0` などを読む
- このうち rebuild で無くなるのは `libegl1`・`libgl1` だけ。`libglx0`・`libglvnd0`・X11 系・`libusb-1.0-0` は 2026-10-09 の基本パッケージの `apt install`（Blender の依存）で入っている。`libudev1`・`libstdc++6`・`libgcc-s1` はベースイメージにある。導入済みのパッケージで `libegl1`・`libgl1` に依存するものは無い（`apt-cache rdepends --installed`）
- `libegl1` は `libegl-mesa0` に、`libgl1` は `libglx0` に依存するので、2 つを指定すれば残りは apt が入れる
- open3d 0.20.0 の cp314 の配布物は 392 MB（PyPI の `open3d-0.20.0-cp314-cp314-manylinux_2_35_x86_64.whl`）で、依存を含め 59 パッケージを入れる。展開した uv の環境は 1.1 GB（open3d だけで 859 MB）。uv のキャッシュ（`~/.cache/uv`）は mount していないので、rebuild のたびに取得し直す
- `.devcontainer/` のテストに、基本パッケージの一覧や README の該当の文を照合するものは無い

## 判断

- **D-1 apt の行**: `.devcontainer/install_beforehand.bash` の基本パッケージの `apt install` の行の末尾（`python3-numpy` の後）に `libegl1 libgl1` を足す。ステップは増やさず、`STEP_TOTAL` は変えない（#95 で #103 の担当）。代案の「専用のステップを足す」は、失敗時の切り分けは楽になるが `STEP_TOTAL` を変えるので採らない
- **D-2 足すパッケージ**: `libegl1`・`libgl1` の 2 つだけにする。`libegl-mesa0`・`libglx0` は依存として入るので書かない。GPU（CUDA）、open3d の表示機能、torch の拡張（`open3d_torch_ops.so`）は範囲外
- **D-3 README**: `.devcontainer/README.md` の「Resonite ワールド開発ツール」の最初の段落（`python3-numpy` を書いている箇所）に `libegl1`・`libgl1` を足し、直後に理由の段落を置く。書くことは、open3d が CPU だけで使うときも import 時に `libEGL.so.1`・`libGL.so.1` を読むこと、open3d 本体は Dev Container の全体には入れず uv で入れること、確かめるコマンドと取得量。「導入ツール一覧」の表は mount と `initialize.bash` の対応を `test-readme.bash` が検査する表なので、行を足さない
- **D-4 postCreate の検査**: `verify-resonite-tooling.bash` に open3d の import の検査は足さない。理由は、rebuild のたびに 400 MB を超える取得と 1.1 GB の展開がかかること、open3d は Resonite の開発ツールの必須物ではなく Meshy の仕上げだけが使うこと、#95 のボードで #91 が変えてよいファイルに含まれないこと。プラグインの外部ツールの確認は #98・#102 の `doctor` で扱える。代案の「`ldconfig -p` で `libEGL.so.1`・`libGL.so.1` を確かめる軽い検査」も、apt の行の成功（失敗すれば postCreate が止まる）と同じことを再検査するだけなので採らない
- **D-5 テスト**: テストは足さない。パッケージの一覧と README の文の変更で、コードを実行して確かめる挙動が無い（`AGENTS.md` の「テストの採用基準」、作らない型 1・3）。代わりに `bash -n`、`bash .devcontainer/run-tests.bash`、`git diff` の確認、今のコンテナでの import の確認を行い、rebuild の後の import の確認を利用者に頼んで #91 に記録する
- **D-6 Python のパッケージの置き場所**: 元の本文の「やること 4」は #95 のボードで #90 へ移ったので、ここでは決めない
- **D-7 PR と Issue**: PR の本文は `Refs #91` にし、マージで #91 を自動で close しない。#91 の完了の証拠には、rebuild の後の `import open3d` の記録が含まれるため

## 範囲外

- `install_beforehand.bash`・`.devcontainer/README.md` の Meshy CLI の段と記述、`STEP_TOTAL`（#103）
- open3d の Python のパッケージの置き場所と、仕上げの道具の移動（#90）
- GPU（CUDA）・open3d の表示機能・torch の拡張
- `pip` による Dev Container の全体への導入（`AGENTS.md` の「Python は uv」）
