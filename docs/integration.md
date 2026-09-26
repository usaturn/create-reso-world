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

## マージ後にユーザが行うこと（随時追記）

1. `git -C /workspaces/reso-world fetch origin` の後、`feat/slum02-slum` を `origin/main` に rebase するか ff-merge する。
2. `CLAUDE.md` と `.pi/APPEND_SYSTEM.md` の未コミット変更は、フェーズ 2 で新設計に取り込み済みであることを確認したうえで `git checkout -- CLAUDE.md .pi/APPEND_SYSTEM.md` で破棄する。`.claude/settings.local.json` は「マージ前にユーザが行うこと」で退避した内容を元の場所へ戻す。
3. `MyResoniteProject/modeling/tokyo_nova/layout.py.orig` は新しい `.gitignore` で見えなくなる。不要なら削除する。
4. `.git/info/exclude` に暫定追加した `/private/` の行を削除する（ルート `.gitignore` の `/private/` 規則に置き換わる）。
