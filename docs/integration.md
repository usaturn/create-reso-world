# 再設計の統合手順

仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 10.1 節。各フェーズで実施した「メイン作業ツリー側の操作」、PR を出す前に行ったこと、マージの前後にユーザが行うこと、Rebuild 後の確認をまとめる。

## フェーズ 0 で実施したこと

- `origin` を https://github.com/usaturn/create-reso-world.git に設定し、`main`（feat/slum02-slum の HEAD `2119a3e` へ fast-forward 済み）、`feat/slum02-slum`、`feat/tokyo-nova-world`、`chore/repo-redesign` を push した。
- tokyo-nova の未コミット変更（変更 12 件、新規 6 件）を `wip/tokyo-nova-refinement` にコミットして push した。作業ツリーの内容は変えていない。`content/tokyo-nova/layout.json` は `modeling/tokyo_nova/layout.py` より古い生成物なので、作業再開時に再生成が必要。

## フェーズ 1 で実施したこと（メイン作業ツリー）

- `MyResoniteProject/ATS.txt`、`BTD.txt`、`TNX.txt` を `private/trpg/` へ移動した（`tmp/` の同一コピーはそのまま）。`tokyo_nova_resoloop_world_prompt.md` は本文中で名前に触れるだけなので変更していない。
- 空の `tools/` を削除した。
- `.git/info/exclude` から存在しない `.devin/mcp_config.local.json` の行を外した（同じ規則はルート `.gitignore` に移した）。
- `.git/info/exclude`（全 worktree 共通）に `/private/` を暫定追加した。マージ後はルート `.gitignore` が同じ規則を持つので、この行は削除してよい。

## PR を出す前に行ったこと（フェーズ 6）

1. `chore/repo-redesign` に、その時点の `feat/slum02-slum` をマージした（マージコミット）。仕様 10.1 は rebase としていたが、`chore/repo-redesign` は push 済みで force push をしないため、マージに置き換えた（フェーズ 6 の判断事項）。
2. `main` を `feat/slum02-slum` の HEAD へ fast-forward し（`git fetch . feat/slum02-slum:main`）、`main` と `chore/repo-redesign` を push してから、`main` 宛ての PR を 1 本だけ開いた。
3. 下の「PR のマージ前にユーザが行うこと」の手順 2 の一覧を PR の直前に作り直し、件数を更新した。

## PR のマージ前にユーザが行うこと

手順 2 の 2 つのコードブロックは同じシェルで実行する（1 つ目で作った `list` 変数を 2 つ目で使う）。手順 1 の前に、`/workspaces/reso-world` で動いているエージェントのセッションを止める（片付けた `.claude/settings.local.json` などを書き戻さないように）。

1. 作業ツリー（`/workspaces/reso-world`）の未コミットの変更のうち、マージで上書きされるものを片付ける。
   - `.claude/settings.local.json` は `feat/slum02-slum` で追跡されており、未コミットの変更が乗っている。`chore/repo-redesign` はこのファイルを index から削除するため、`cp /workspaces/reso-world/.claude/settings.local.json ~/settings.local.json.bak` で退避してから `git checkout -- .claude/settings.local.json` で変更を戻す。マージ後に退避した内容を元の場所へ戻す（マージ後は ignore 対象になるので再追跡されない）。`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` も同じファイルを追跡しているため、これらを新しい `main` に rebase するときも同様の退避が必要。
   - `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計（`AGENTS.md` と新しい `.pi/APPEND_SYSTEM.md`）に取り込み済みであることを確認したうえで、`git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。どちらもマージで変わるため、変更が残っているとマージが止まる。
2. `chore/repo-redesign` が新しく追跡するパスのうち、作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout を中断させる（git は未追跡ファイルを上書きしない）。まず一覧を NUL 区切りでファイルに書き出して確認する。`origin/chore/repo-redesign` を最新にするため、先に `git fetch origin` を実行する。

   ```bash
   cd /workspaces/reso-world
   git fetch origin
   list="$HOME/reso-world-untracked-backup.list"
   git ls-tree -r -z --name-only origin/chore/repo-redesign | while IFS= read -r -d '' p; do
     if [ -e "$p" ] || [ -L "$p" ]; then
       git ls-files --error-unmatch -- "$p" >/dev/null 2>&1 || printf '%s\0' "$p"
     fi
   done > "$list"
   tr '\0' '\n' < "$list"
   echo "件数: $(tr -cd '\0' < "$list" | wc -c)"
   ```

   一覧を確認したら、同じ相対パスのまま `~/reso-world-untracked-backup/` へ退避する。`mv` はシンボリックリンクをリンクのまま（実体を追わずに）移動し、`-n` は退避先に同名のファイルがあっても上書きしない。

   ```bash
   while IFS= read -r -d '' p; do
     mkdir -p "$HOME/reso-world-untracked-backup/$(dirname -- "$p")"
     mv -n -- "$p" "$HOME/reso-world-untracked-backup/$p"
   done < "$list"
   ```

   退避が終わったら、同じ一覧コマンドをもう一度実行して 0 件になり、`git status --short` に手順 1 の 3 件（`.claude/settings.local.json`、`CLAUDE.md`、`.pi/APPEND_SYSTEM.md`）が出ないことを確かめてから、PR をマージして「PR のマージ後にユーザが行うこと」の 1 に進む。1 件でも表示されたら、進めずにその内容を確認する。

   ```bash
   git ls-tree -r -z --name-only origin/chore/repo-redesign | while IFS= read -r -d '' p; do
     if [ -e "$p" ] || [ -L "$p" ]; then
       git ls-files --error-unmatch -- "$p" >/dev/null 2>&1 || printf '%s\n' "$p"
     fi
   done
   ```

   2026-09-27 時点の該当: 68 件（2026-09-26 と同じ）。内訳は次のとおり。
   - MyResoniteProject と akichi の resoloop scaffold（各 27 件、計 54 件）: `AGENTS.md`、`.resoloop.json`、`.resoloop/.gitignore`、`.agents/skills/.resoloop-bundled.json`、resonite-blender/resonite-build/resonite-debug/resonite-flux/resonite-inspect/resonite-uix の `SKILL.md` 6 件、resonite-uix の `recipes/` 配下 8 件と `references/` 配下 5 件、`flux/` 配下 4 ファイル（`.gitignore`、`Main.pg`、`protograph.toml`、`resoloop.flux.json`）
   - `MyResoniteProject/.agents/sp-implementer.md`: 1 件
   - `slum02/.resoloop/.gitignore`: 1 件
   - ルート `.claude/skills/` の Blender 系 symlink 10 件（blender-modeler、brutalist-mood、dark-gritty-mood、geometry-nodes、hard-surface、horror-style、procedural-modeling、prop-artist、sci-fi-punk-worlds、uv-workflow）と `references`: 計 11 件
   - `.devcontainer/devcontainer-lock.json`: 1 件
3. `~/reso-world-untracked-backup/` へ退避したファイルは、マージ後に同じパスに入る追跡版と内容を比べてから削除する。`AGENTS.md`（先頭を resoloop preview.14 の文面に揃え、固有節を追加。仕様 4.2）と `.resoloop/.gitignore`（`cache/` を追加。仕様 4.3）以外は同一のはず。`MyResoniteProject/.agents/sp-implementer.md` はブランチでは `../../.agents/sp-implementer.md` への symlink なので、退避した実ファイルはルートの `.agents/sp-implementer.md` と比べる。

   比べるには、手順 2 の一覧を読み直して次を実行する。表示されたパスだけを確かめればよい。

   ```bash
   cd /workspaces/reso-world
   while IFS= read -r -d '' p; do
     b="$HOME/reso-world-untracked-backup/$p"
     if [ -L "$b" ] || [ -L "$p" ]; then
       [ "$(readlink -- "$b")" = "$(readlink -- "$p")" ] || printf 'differs (symlink): %s\n' "$p"
     else
       cmp -s -- "$b" "$p" || printf 'differs: %s\n' "$p"
     fi
   done < "$HOME/reso-world-untracked-backup.list"
   ```

## PR のマージ後にユーザが行うこと

1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に追従させる。PR の後に `feat/slum02-slum` へコミットしていなければ `git merge --ff-only origin/main` で済む。コミットしていれば rebase するかマージする。
2. `.claude/settings.local.json` は「PR のマージ前にユーザが行うこと」で退避した内容を元の場所へ戻す。
3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
4. `.git/info/exclude` に暫定追加した `/private/` の行は、`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` を新しい `main` に rebase した後に削除する（ルート `.gitignore` の `/private/` 規則に置き換わる）。それまでは、古い `.gitignore` のままのブランチで TRPG 本文を見えなくするために要る。
5. 不要になった未追跡物を削除する（どれも追跡している正本が別の場所にある。仕様 4.2 と 5.1）。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
6. `MyResoniteProject/` で `uv sync` を実行し、`uv run pytest` が通ることを確認する（プロジェクト専用の環境になった）。
7. `bash scripts/check-layout.sh` がすべて `ok` で `PASS: check-layout` になることを確認する。
8. （任意）`tmp/resoloop-blender5-uv-20260925` を `external/resoloop` へ移すと、fork のビルドを使うときの clone を省ける。手順は `docs/resoloop-fork-workflow.md` の「`tmp/` にある旧 checkout の整理」にある。
9. Dev Containers: Rebuild Container を実行する。postCreate は NuGet の最新の公開版の ResoLoop を導入する（ネットワークを要する）。確かめることは下の「Rebuild 後に確かめること」にある。`tmp/` の残りの旧 checkout は `docs/resoloop-fork-workflow.md` の「`tmp/` にある旧 checkout の整理」の手順で整理する。

## Rebuild 後に確かめること（仕様 9.3）

Dev Containers: Rebuild Container を実行した後、コンテナの中で次を確かめる。

1. `bash .devcontainer/verify-resonite-tooling.bash` が 0 で終わる。`dotnet --list-sdks` に `10.0.201` がある。
2. postCreate の ResoLoop の導入が通っている: `resoloop --version` が NuGet の最新の公開版を返し、`bash scripts/resoloop-fork.sh status` の `installed version` が `NuGet release` である。postCreate の出力に、各プロジェクトの `resoloop skills sync --check` の結果がある。`dotnet tool list --global` に `papaltine.fluxsdk 1.9.0` があり、`resoloop doctor --json` の `flux-sdk` が `pass` である（postCreate の出力に flux-sdk の WARN が無い）。fork へ push する `bash scripts/resoloop-fork.sh sync` を初めて使うときは、GitHub への push の認証が通ることを確かめる。
3. VS Code のターミナルと、エージェントが起動するプロセスの PATH に `/home/vscode/.local/bin`・`/home/vscode/bin`・`/home/vscode/.dotnet/tools` がある（`remoteEnv.PATH`）。
4. ホストに `~/.config/create-reso-world` が mode 700 で作られ、コンテナに mount されている。`env` を置いた場合は、新しいシェルでその変数が export されている。
   （任意、ProtoFlux を使うとき）ホストに `~/.local/share/create-reso-world/resonite-managed-data` が実ディレクトリで作られ、コンテナで `findmnt -no OPTIONS /home/vscode/.local/share/create-reso-world/resonite-managed-data` が `ro` で始まる。DLL を用意したら、`.devcontainer/README.md` の「Resonite の managed data（ProtoFlux、任意）」の手順で doctor と check・build を確かめる。
5. `bash scripts/check-layout.sh`、`bash .devcontainer/run-tests.bash`、各プロジェクトの `uv run pytest` が通る。
6. Devin で simplify-in-subagent を呼んだとき、サブエージェントが edit と exec のツールを持つ。
7. GitHub Actions の CI（devcontainer-tests、layout、skill-tests、gitleaks）がすべて成功する。PR の時点では、アカウントの課金の設定によりジョブが開始されず、GitHub 上では確かめられていない。
8. pi と Claude Code は、プロジェクトの trust を承認し直す。Codex は初回の起動時にプロジェクトの trust を承認する（仕様 10.1 の 5）。
