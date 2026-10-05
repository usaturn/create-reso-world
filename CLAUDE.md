@AGENTS.md

## Claude Code 固有

- ユーザの指示が曖昧な場合は AskUserQuestion で確認する
- 長時間タスクの途中経過は出力ファイルを必要な範囲だけ読み、完了は終了コードで確認する。`TaskOutput(block=true)` の raw dump は読まない。監視と待機は `AGENTS.md` のエージェント運用と `monitoring-long-tasks` スキルに従う
- 共有スキルの正本は `.agents/skills/` にあり、Claude Code は `.claude/skills/<name>` の symlink 経由で読む。スキルを追加・改名・削除したら `.claude/skills/` の symlink も合わせ、`scripts/check-layout.sh` で確認する
- ワールドのプロジェクトでは、プロジェクトの `CLAUDE.md`（`@AGENTS.md` の 1 行）がプロジェクトの `AGENTS.md` を読み込む
- ユーザとのやり取りは必ず日本語で表記する

## 一時ファイル・ディレクトリの削除

rm / rmdir の削除対象にシェル変数を使う場合は、
各変数に ${VAR:?} 形式の空値ガードを付け、パス全体を引用すること。

例: rm -rf -- "${T:?}/${n:?}"

この規則はサブエージェントが実行するコマンドにも適用すること。
