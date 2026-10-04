# PR #24 レビュー指摘の選別 Spec

## 対象と目的

- 対象 PR: https://github.com/usaturn/create-reso-world/pull/24
- リポジトリ: `usaturn/create-reso-world`
- 作業ルート: `/workspaces/reso-world`。`origin` が対象リポジトリの URL と一致することを確認済み。
- 対象ブランチ: `feat/issue-18-remove-excluded-agents`
- 検証した現行 HEAD: `d6c8523084257621ceb3be23d14e0eb8ac138a2b`
- 入力ディレクトリ: `reviews/#24-feat-issue-18-remove-excluded-agents/`
- PR URL の番号を `#24` として解決し、指定規則の2か所の直下で一致するディレクトリが上記1件だけであることを確認した。

現行 HEAD のコミット済み内容に対して指摘を検証し、`review-fix-planning` の基準を満たす修正だけを選ぶ。新しい問題の探索や、既存の設計判断の変更は対象に含めない。

## レビュー入力

指定ディレクトリ内の全3ファイルを読んだ。各レビューが記録した HEAD の短縮 SHA は、現行 HEAD と一致する。

| ファイル | 記録された対象 HEAD | 指摘数 |
| --- | --- | --- |
| `gpt-6.1-sol.md` | `d6c852308425` | 0 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `d6c852308425` | 1（Info I-1） |
| `claude-opus-5-5.md` | `d6c852308425` | 0 |

未検証候補・追加テスト提案は、いずれのレビューにも無い。`claude-opus-5-5.md` が「既出として件数に含めない事項」と明記した記述は、新たな指摘として扱わない。

## 全指摘の分類

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 0 |
| 判断保留 | 0 |
| 対応しない | 1 |
| 合計 | 1 |

| ID・出典 | 指摘 | 分類 | 根拠 |
| --- | --- | --- | --- |
| I-1 / `commandcode-deepseek-deepseek-v4.1-flash.md` | 撤去した `MAAS_ANTHROPIC_TOKEN` を共有の `env -u` リストから外したままにするか | 対応しない | 現行 HEAD の既存 Spec の D-3（99行）が削除と README での案内を明示し、コード・README・テストが一致する。指摘は設計判断の再確認であり、分類条件 (a)〜(d) を満たさない。 |

解消済みの指摘は無い。トークンの引き継ぎは現行 HEAD でも再現したため、「解消済み」とは判定しない。数行で変更できても、既存の仕様を変更する提案なので「判断保留」には置かない。

## 現行 HEAD で確認した根拠

以下のソース・テスト・文書は、すべて `git show d6c8523084257621ceb3be23d14e0eb8ac138a2b:<path>` で確認した。

| ファイル・行 | 確認した内容 |
| --- | --- |
| `.devcontainer/zshrc.txt:71` | `cc_launcher_unsets` に `MAAS_ANTHROPIC_TOKEN` は含まれない。 |
| `.devcontainer/zshrc.txt:127`、`:148`、`:179` | `ccdd`・`ccddg`・`ccdu` は共有リストを使って子 `claude` を起動する。 |
| `.devcontainer/zshrc.txt:218` | `~/.config/create-reso-world/env` を `set -a` の下で読み込み、変数を export する。 |
| `.devcontainer/README.md:59` | 古いトークンを `env` から削除するよう案内し、残せば子プロセスにも渡ると説明する。 |
| `.devcontainer/test-herdr-migration.bash:529` | `zshrc.txt` に撤去対象のトークン名を戻さないことを検査する。531〜577行の `expected_unsets` にも含まれない。 |
| `.devcontainer/test-readme.bash:60` | `-u MAAS_ANTHROPIC_TOKEN` の再混入を検出し、63行で README の削除案内を確認する。 |
| `docs/superpowers/specs/2026-10-04-issue-18-remove-excluded-agents-design.md:99` | D-3 は共有リストから外す方針を明示する。110行では、後続の #21 がこのリストを引き継ぐことも明記する。 |

### 隔離環境での実行検証

`mktemp -d` が返した `/tmp/review-fix-planning.oZJQzw` の配下に detached worktree を作り、HEAD が上記 SHA と一致することを確認した。fixture、ダミー HOME、テストの一時ファイルはすべて同じ親ディレクトリ内に置いた。実際の資格情報やサービスは使用していない。

`claude` を対象変数だけを表示するスタブに置き換え、`env -i` の下で現行 HEAD の `zshrc.txt` を source して、3つのランチャーを個別に起動した。

| 条件 | `ccdd` | `ccddg` | `ccdu` |
| --- | --- | --- | --- |
| fixture の `env` に `MAAS_ANTHROPIC_TOKEN=fake-legacy-maas-token` を記載 | ダミー値を引き継ぐ | ダミー値を引き継ぐ | ダミー値を引き継ぐ |
| fixture の `env` から同じ変数を削除し、新しいシェルで起動 | 未設定 | 未設定 | 未設定 |

続けて同じ worktree で以下を実行し、全体の終了コード0を確認した。

- `bash .devcontainer/test-readme.bash`: `PASS: README tool table matches the Dev Container files`
- `bash .devcontainer/test-herdr-migration.bash`: `PASS: herdr Dev Container migration`

実行後の worktree に変更は無かった。検証終了後、`git worktree remove` の成功を確認してから親ディレクトリを削除した。Spec 作成時点で、この検証環境は残っていない。

## brainstorming の経路と対応方針

経路は **bounded**。既存のランチャーの挙動についての1件だけを扱い、再現と既存仕様の突き合わせで判断できる。新しい機能・インターフェースや、未解決の設計上の疑問は無い。`review-fix-planning` の規定に従い、bounded でも本 Spec を作成する。

I-1 は、古い資格情報を子プロセスへ渡さない防御を残すか、撤去対象の設定を共有リストから外すかという設計上の論点である。既存の D-3 を維持し、今回はコード・README・既存テストを変更しない。

「対応する」は0件なので、修正方針・修正後の検証方法・実装 Task は無い。回帰テストの追加や文書の追記も提案しない。

## 状態と検証範囲

選別と Spec 作成の後、2026-10-04 にユーザが本判定を明示承認した。修正対象は0件なので、追加実装・commit・push は行っていない。Spec はローカルにのみ存在する。

承認後の依頼に従い、[ステータスコメント](https://github.com/usaturn/create-reso-world/pull/24#issuecomment-5978189452)を投稿した。モデル名はランタイムの session metadata から `gpt-6.1-sol` と確定した。現行 HEAD が検証時と同じで、CI がすべて成功、PR が MERGEABLE / CLEAN であることを確認し、`--match-head-commit` で対象 SHA を指定してマージした。

2026-10-04 08:40:30 UTC にマージ完了。マージコミットは `408e7a3ad5b16f38954eac3089b3c04548c78139`。その後、PR の状態が MERGED であり、自モデルのマーカーを持つコメントが残っていることを確認した。

全体のテストスイート、配置検査、Dev Container の rebuild は今回実行していない。選別結果は I-1 と上記2本の関連テストの範囲に限り、PR 全体の再レビューやマージ可否の保証ではない。

## 作業時間

- 入力の読み取り・PR と HEAD の確認: 08:27:11〜08:27:33 UTC（約22秒）。
- コミット済み内容の確認・隔離検証・後片付け: 08:27:33〜08:29:33 UTC（約2分）。
- 分類・bounded の経路判定・Spec 作成と確認: 08:29:33〜08:31:51 UTC（約2分18秒）。
- 記録した開始から最終確認まで: 約4分40秒。

上記の開始時刻は最初に記録した時計の時刻である。冒頭のスキル読み込みは含まない。並行した読み取り・照合の時間は重ねて加算していない。

承認後の投稿・マージ作業は、記録した開始から最終確認まで約2分6秒。

- PR・CI・モデル名の確認とコメント投稿: 08:38:40〜08:40:14 UTC（約1分34秒）。
- マージと状態確認: 08:40:14〜08:40:46 UTC（約32秒）。
