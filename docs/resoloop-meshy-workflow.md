# resoloop-meshy の開発

仕様: `docs/superpowers/specs/2026-10-16-create-reso-world-issue-96-plugin-repo-design.md`。この文書は、resoloop の Meshy プラグインのリポジトリ（usaturn/resoloop-meshy）を、create-reso-world の下で開発する手順をまとめる。

## リポジトリ

- usaturn/resoloop-meshy。Meshy の Web アプリで作った GLB を仕上げて resoloop へ渡すプラグインの道具とスキルを置く。Meshy の API（生成、ダウンロード、`meshy-cli`）は使わない
- GitHub の非公開リポジトリ。上流（orange3134/resoloop）へプラグイン機構を提案するとき（#105）に外部のプラグインの例として見せるなら、利用者の確認を経て公開にする
- ライセンスは AGPL-3.0-or-later（resoloop と同じ）
- GitHub Actions は無効にしてある。CI（`.github/workflows/`）は作らない
- このリポジトリでの規約は、プラグインのリポジトリの `AGENTS.md` にある。create-reso-world の `AGENTS.md` にも従う

## checkout の位置と remote

checkout は create-reso-world の親 checkout の `external/resoloop-meshy`（ルートの `.gitignore` で無視する）に置く。`/workspaces` の直下に置かない理由は `docs/resoloop-fork-workflow.md` の「checkout の位置と remote 構成」と同じで、`external/` はリポジトリの中にあるので Rebuild の後も残る。

remote は `origin`（https://github.com/usaturn/resoloop-meshy.git）だけである。fork ではないので `upstream` は無い。`scripts/resoloop-meshy.sh` はこの URL と比べて、食い違いがあれば止まる（末尾の `/` と `.git` の違いは同じ URL とみなす）。

非公開のリポジトリなので、clone には GitHub の認証が要る。この Dev Container は `gh auth git-credential` を git の認証に使うので、`gh auth status` が通っていれば足りる。

## `scripts/resoloop-meshy.sh` のサブコマンド

| サブコマンド | 動作 | ネットワーク |
| --- | --- | --- |
| `clone` | checkout が無ければ `origin` から clone する。既にあれば `origin` を確かめるだけで、何も変えない。`origin` が無い・違うときや、その場所が自前の git の checkout でないときは止まる | 取得のみ |
| `status` | checkout の HEAD・ブランチ（または `detached`）・追跡ファイルの未コミットの変更の有無と、`origin` の確認の結果を表示する。何も変えない | なし |

既定の checkout の場所は、スクリプトを含む create-reso-world の親 checkout（git の common dir の親）の `external/resoloop-meshy` である。create-reso-world の worktree（`.worktrees/<topic>`）で実行しても、worktree の中ではなく親 checkout を指す。worktree の中に clone すると、worktree を消したときにプラグインの作業ごと消えるためである。

終了コード: 0 成功（`status` は常に 0）、1 状態が期待と違う（自前の git の checkout でない、`origin` が無い・違う）、2 使い方の誤り、3 前提不足（git が無い）、4 `git clone` の失敗。

環境変数 `RESOLOOP_MESHY_CHECKOUT`（checkout の場所）と `RESOLOOP_MESHY_ORIGIN_URL`（`origin` の URL）で既定の値を差し替えられる。テストと特殊な運用向け。

`origin` が食い違っているときは、`git -C external/resoloop-meshy remote set-url origin https://github.com/usaturn/resoloop-meshy.git`（無ければ `remote add`）で直す。

## 開発の流れ

コマンドは create-reso-world の親 checkout のルートで実行する。

1. `bash scripts/resoloop-meshy.sh clone` で取得する（初回だけ）。`bash scripts/resoloop-meshy.sh status` で状態を確かめる。
2. checkout そのものは `main` のまま切り替えず、`git -C external/resoloop-meshy pull --ff-only` で `origin/main` に追従させる。
3. 作業ブランチと worktree を作る: `git -C external/resoloop-meshy worktree add -b <type>/<topic> .worktrees/<topic> origin/main`。`.worktrees/` はプラグインのリポジトリの `.gitignore` で無視している。
4. worktree（`external/resoloop-meshy/.worktrees/<topic>`）で変更してコミットし、そこで `uv run pytest` を実行する。
5. push（`git -C external/resoloop-meshy/.worktrees/<topic> push -u origin <type>/<topic>`）、PR の作成（`gh pr create --repo usaturn/resoloop-meshy --base main --head <type>/<topic>`）、マージは、利用者の指示があるときだけ行う。`--head` を省くと、`gh` は親 checkout（detached HEAD）のブランチを head にしようとして止まる。
6. マージの後に、`git -C external/resoloop-meshy worktree remove .worktrees/<topic>` とブランチの削除で片付け、手順 2 で `main` を追従させる。

Spec・Plan はプラグインのリポジトリに置かず、create-reso-world の `docs/superpowers/` に置く（create-reso-world の `AGENTS.md` の「Spec・Plan の保存と公開」）。

## PR のレビューと修正

`pr-review` と `review-fix-planning` には、checkout の絶対パス（例: `/workspaces/reso-world/external/resoloop-meshy`）を `CODE_ROOT` として明示して渡す。共通の helper（`scripts/superpowers_context.py`）は、それが checkout 自身のルートであることと、usaturn/resoloop-meshy と一致する remote が 1 つだけであることを照合する。レビューの結果は `CODE_ROOT` の `reviews/` に書かれ、プラグインのリポジトリの `.gitignore` で無視している。
