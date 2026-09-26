# 再設計の統合手順

仕様: `docs/superpowers/specs/2026-09-26-create-reso-world-redesign-design.md` 10.1 節。フェーズ 6 で完成させる。ここには各フェーズで実施した「メイン作業ツリー側の操作」と、マージ後に必要な手順を積み上げる。

## フェーズ 0 で実施したこと

- `origin` を https://github.com/usaturn/create-reso-world.git に設定し、`main`（feat/slum02-slum の HEAD `2119a3e` へ fast-forward 済み）、`feat/slum02-slum`、`feat/tokyo-nova-world`、`chore/repo-redesign` を push した。
- tokyo-nova の未コミット変更（変更 12 件、新規 6 件）を `wip/tokyo-nova-refinement` にコミットして push した。作業ツリーの内容は変えていない。`content/tokyo-nova/layout.json` は `modeling/tokyo_nova/layout.py` より古い生成物なので、作業再開時に再生成が必要。

## フェーズ 1 で実施したこと（メイン作業ツリー）

- `MyResoniteProject/ATS.txt`、`BTD.txt`、`TNX.txt` を `private/trpg/` へ移動した（`tmp/` の同一コピーはそのまま）。`tokyo_nova_resoloop_world_prompt.md` は本文中で名前に触れるだけなので変更していない。
- 空の `tools/` を削除した。
- `.git/info/exclude` から存在しない `.devin/mcp_config.local.json` の行を外した（同じ規則はルート `.gitignore` に移した）。
- `.git/info/exclude`（全 worktree 共通）に `/private/` を暫定追加した。マージ後はルート `.gitignore` が同じ規則を持つので、この行は削除してよい。

## マージ前にユーザが行うこと

1. 作業ツリー（`/workspaces/reso-world`）の `.claude/settings.local.json` は `feat/slum02-slum` で追跡されており、未コミットの変更が乗っている。`chore/repo-redesign` はこのファイルを index から削除するため、マージ・rebase の前に `cp /workspaces/reso-world/.claude/settings.local.json ~/settings.local.json.bak` などで退避し、マージ後に元の場所へ戻す（マージ後は ignore 対象になるので再追跡されない）。`feat/tokyo-nova-world` と `wip/tokyo-nova-refinement` も同じファイルを追跡しているため、これらを新しい `main` に rebase するときも同様の退避が必要。
2. `chore/repo-redesign` が新しく追跡するパスのうち、作業ツリーに未追跡のまま存在するものは、マージや rebase の checkout を中断させる（git は未追跡ファイルを上書きしない）。次のコマンドで一覧を標準出力に出し、同じ相対パスのまま `~/reso-world-untracked-backup/` へ移してからマージする。

   ```bash
   git -C /workspaces/reso-world ls-tree -r -z --name-only origin/chore/repo-redesign | while IFS= read -r -d '' p; do
     if [ -e "/workspaces/reso-world/$p" ] || [ -L "/workspaces/reso-world/$p" ]; then
       git -C /workspaces/reso-world ls-files --error-unmatch -- "$p" >/dev/null 2>&1 || printf '%s\n' "$p"
     fi
   done
   ```

   2026-09-26 時点の該当: 68 件。内訳は次のとおり。
   - MyResoniteProject と akichi の resoloop scaffold（各 27 件、計 54 件）: `AGENTS.md`、`.resoloop.json`、`.resoloop/.gitignore`、`.agents/skills/.resoloop-bundled.json`、resonite-blender/resonite-build/resonite-debug/resonite-flux/resonite-inspect/resonite-uix の `SKILL.md` 6 件、resonite-uix の `recipes/` 配下 8 件と `references/` 配下 5 件、`flux/` 配下 4 ファイル（`.gitignore`、`Main.pg`、`protograph.toml`、`resoloop.flux.json`）
   - `MyResoniteProject/.agents/sp-implementer.md`: 1 件
   - `slum02/.resoloop/.gitignore`: 1 件
   - ルート `.claude/skills/` の Blender 系 symlink 10 件（blender-modeler、brutalist-mood、dark-gritty-mood、geometry-nodes、hard-surface、horror-style、procedural-modeling、prop-artist、sci-fi-punk-worlds、uv-workflow）と `references`: 計 11 件
   - `.devcontainer/devcontainer-lock.json`: 1 件
3. 退避したファイルは、マージ後に同じパスに入る追跡版と内容を比べてから削除する。`AGENTS.md`（先頭を resoloop preview.14 の文面に揃え、固有節を追加）と `.resoloop/.gitignore`（`cache/` を追加）以外は同一のはず。

## マージ後にユーザが行うこと（随時追記）

1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` は「マージ前にユーザが行うこと」で退避した内容を元の場所へ戻す。
3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
4. `.git/info/exclude` に暫定追加した `/private/` の行を削除する（ルート `.gitignore` の `/private/` 規則に置き換わる）。
5. 不要になった未追跡物を削除する。`akichi/.agents/skills/` の Blender 系 10 スキルと `references/`・`tests/`（ルートの `.agents/skills/` に移ったため）、`akichi/.claude/skills/` と `MyResoniteProject/.claude/skills/` の Blender 系 symlink、ルート `.claude/skills/` の `resonite-*` の未追跡 symlink（resonite-* はプロジェクト側で読む）、`MyResoniteProject/.agents/sp-*.md` のうち `sp-implementer.md` 以外の 8 件（pi-superagents の組み込み定義と同一のため）。
6. `MyResoniteProject/` で `uv sync` を実行し、`uv run pytest` が通ることを確認する（プロジェクト専用の環境になった）。
7. `bash scripts/check-layout.sh` がすべて `ok` で `PASS: check-layout` になることを確認する。
