@AGENTS.md

## Claude Code 固有

- ユーザの指示が曖昧な場合は AskUserQuestion で確認する
- `TaskOutput(block=true)` の raw dump は読まず、途中経過は出力ファイルを必要な範囲だけ読む
- 共有スキルの正本は `.agents/skills/` にあり、Claude Code は `.claude/skills/<name>` の symlink 経由で読む。スキルを追加・改名・削除したら `.claude/skills/` の symlink も合わせ、`scripts/check-layout.sh` で確認する
- ワールドのプロジェクトでは、プロジェクトの `CLAUDE.md`（`@AGENTS.md` の 1 行）がプロジェクトの `AGENTS.md` を読み込む
