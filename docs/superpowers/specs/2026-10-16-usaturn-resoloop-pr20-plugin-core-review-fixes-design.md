# usaturn/resoloop PR #20: プラグインの土台のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（文書用ブランチ `docs/issue-97-plugin-core`。同じテーマの文書専用 PR #109 が open）
- 対象リポジトリ・PR: https://github.com/usaturn/resoloop/pull/20（`feat/plugin-core` → `main`）
- 関連 Issue: usaturn/create-reso-world#97（PR 本文の `Refs`。親 #95。`closingIssuesReferences` は空）
- 関連文書: `docs/superpowers/specs/2026-10-16-create-reso-world-issue97-resoloop-plugin-core-design.md`、`docs/superpowers/plans/2026-10-16-create-reso-world-issue97-resoloop-plugin-core.md`
- 検証したコード HEAD: `a9a8427e33b14b700fdc2e558b6fbad46fd991b6`（PR の分岐点は上流の `99c59be`。base `main` = `dc58ac55764f50b8ecc63b52c4dc89273e61a095` は head の祖先ではない）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning https://github.com/usaturn/resoloop/pull/20` を指定し、レビューの作成後に「続行してください」と指示した。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う。Plan の「マージはしない（利用者の指示による）」は実装時の指示で、この依頼が後から与えたマージの許可を妨げない
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT: `/workspaces/reso-world/.worktrees/issue-97-plugin-core-docs`（文書 PR #109 の head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用）
- CODE_ROOT: `/workspaces/reso-world/external/resoloop/.worktrees/issue-97-plugin-core`（PR head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`external/resoloop/reviews/#20-feat-plugin-core/` の 4 ファイル。対象 HEAD はすべて `a9a8427e33b1` で、`pull/20/head` の取得結果の祖先（同じコミット）である。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | Low 1、Info 1 |
| `gpt-6.1-sol.md` | Request changes | High 1、Medium 2 |
| `SWE-2-High.md` | Approve | Medium 1、Low 1 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Low 1、未確認の候補 1 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Opus L-1、SWE M-1 | ディレクトリの導入元を symlink を含むパスで渡すと、`git rev-parse --show-toplevel`（実パス）と `Path.GetFullPath`（字句の正規化）が一致せず、Git の一覧を使わずに全体を写す。`git` が失敗したとき（safe.directory の拒否など）も同じ | 対応しない。現行 HEAD で再現した（下の「再現」A）。`.gitignore` の対象（`.venv/lib/site.py`・`secret.env`）が `package/` に写り、`.venv` に symlink があると `PLUGIN_SOURCE_INVALID`（`.venv/python` を名指し）で止まる。実パスなら写らない。致命的でない理由: 導入元は読むだけで変えず、写し先は新しい staging だけなので、データは失われない。写した中身はプロジェクトの中の写しで、プラグインの `.gitignore` も一緒に写るので、プロジェクトの Git も同じパターンを無視し続ける（漏れ得るのは `.git/info/exclude` だけで除外したファイル）。結果は、明示の誤りで止まるか、manifest と commands に影響しない余分なファイルが入るかで、実パスを渡せば避けられる。この環境のパス（`/workspaces`、`external/resoloop-meshy`、`worlds/*`）に symlink は無い。直し方（`--show-prefix` で判定する、実パスに解決する）は設計の選択 |
| R2 | GPT H-1 | `.resoloop` か `.resoloop/plugins` が外部へのリンクだと、`plugin remove NAME --yes` がリンク先の `NAME` を再帰削除する。導入もリンク先へ書く | 対応しない。現行 HEAD で再現した（下の「再現」B）。致命的でない理由: `.resoloop/plugins` は resoloop が `Directory.CreateDirectory` で実ディレクトリとして作り、このリポジトリの手順・構成にリンクにするものは無い（全ワールドの `.resoloop` は実ディレクトリ）。リンクにしても消す対象は利用者が置いた `<plugins>/NAME` で、リンクにする理由（`.resoloop` の移動、プラグインの共有）の範囲では、消えるのは名指ししたプラグインである。関係の無いデータが消えるには、プラグインでないディレクトリを `--yes` 付きで名指しする必要があり、実ディレクトリの `.resoloop/plugins/` に置いた場合も同じく消える（Spec「記録や中身が壊れていても消せる」）。親のリンクを拒否すると、`.resoloop` を移した構成の挙動も変わるので、どちらにするかは仕様の選択 |
| R3 | GPT M-1 | `package/` 自体をリンクに置き換えると、中身のハッシュが一致すれば `List`・`Load`・`LoadAll` が受け入れる | 対応しない。現行 HEAD で再現した（下の「再現」C。子のリンクなら `PLUGIN_MODIFIED`）。致命的でない理由: リンクの先の全ファイルは毎回ハッシュで照合され、内容の変更・欠け・余分は検出される。この PR はプラグインのコードを実行しない。`install.json` は保護されておらず、`package/` を差し替えられる者はハッシュも書き換えられるので、照合は誤った変更の検出であり、権限の境界ではない |
| R4 | GPT M-2 | 同じ提供名を持つ別名の 2 プラグインを同じプロジェクトへ同時に導入すると、どちらも成功し、`LoadAll` が `PLUGIN_NAME_CONFLICT` になる | 対応しない。現行 HEAD で確認した（`src/RLoop.Core/Plugins/PluginInstaller.cs:46` の `EnsureInstallable` から `:53` の `Directory.Move` まで排他が無い）。致命的でない理由: 同じプロジェクトへの同時の導入が条件で、ファイルは失われない。結果は `LoadAll` が両方の名前を示す `PLUGIN_NAME_CONFLICT` で検出され、`plugin remove` で戻せる。この PR のコマンドは `LoadAll` を呼ばない |
| R5 | SWE L-1、DeepSeek L-1 | directory の記録の `commit` を検証しないので、12 文字未満の値を手で書くと、テキストの `plugin list` が `UNEXPECTED_ERROR`（exit 7）で落ちる | 対応しない。現行 HEAD で再現した（下の「再現」D）。致命的でない理由: resoloop は directory の記録に `null` を書くので、`install.json` を手で書き換えたときだけ起きる。`--json` の一覧と `remove` は使え、誤った結果は残らない |
| R6 | Opus I-1 | CLI を足したが README・スキルを更新していない | 対応しない。Spec が決着させている（親 #95 の分担で、`plugin` コマンドの文書は #101 が書く）。PR 本文にも書かれている |
| R7 | DeepSeek の未確認の候補 | `resoloop init` が作る `.resoloop/.gitignore` が `plugins/` を無視しない | 対応しない。確認した（`src/RLoop.Core/ProjectInitializer.cs:89` は `state/`・`flux-state/` だけ）。この PR の変更ではなく、`ProjectInitializer.cs` は Issue #97 の「変えてよいもの」に含まれない。`data/` の Git の扱いは #98 が決める。`package/` の中身は導入元の写しで、R1 のとおりプラグインの `.gitignore` も写る |

分類: **解消済み 0 / 対応する 0 / 対応しない 7**。「対応する」が無いので、「守る条件と影響経路」の表と、同じ条件の再発のきっかけの確認は対象が無い。

仕様の論点として残すもの:

- R1: ディレクトリが作業ツリーの最上位かを、パスの比較ではなく `git rev-parse --show-prefix` で判定するか。`.git` があるのに `git` が失敗したとき、全体を写さずに止めるか
- R2: `.resoloop`・`.resoloop/plugins` がリンクのとき、導入と削除を拒否するか、リンク先で行うか
- R4: 同じプロジェクトへの導入を排他するか

## 確認の範囲

- 変更ファイル: `src/RLoop.Core/Plugins/` の 7 ファイル（`PluginErrors`・`PluginGit`・`PluginInstaller`・`PluginManifest`・`PluginNames`・`PluginRegistry`・`SemanticVersion`）は全文。`Program.cs` は差分（`RunPlugin`・dispatch・help）。テストは `PluginInstallerTests.cs` を全文、他の 2 ファイルとフィクスチャはテスト名と構成
- 関連処理: `ProjectInitializer.cs` の `.resoloop/.gitignore` の生成、Spec の導入・記録・照合・削除・一覧の節、Plan の実施結果と見送った指摘、Issue #97 の受け入れ条件
- base との関係: fork の `main`（`dc58ac5`）から head への `Program.cs` の差分に、新しいトップレベルのコマンドは無い（`PluginNames.BuiltinCommands` の予約名から漏れるものは無い）
- 自己確認: 削除がリンクを辿らないこと（`DeleteTree`）、名前の検証がパスの組み立てより前にあること、Git の URL の形と `--end-of-options`・`--` による引数の注入の防止、URL の資格情報の拒否、checkout の前の symlink・submodule の拒否、`core.fsmonitor=false` と `GIT_TERMINAL_PROMPT=0`、照合がリンクをハッシュしないこと、staging から `Directory.Move` で配置することを読んだ。PR が持ち込んだ致命的な欠陥は見つからなかった

## 再現

`a9a8427` を detach した隔離 worktree で CLI（`dotnet resoloop.dll`）をビルドし、使い捨てのプロジェクト（`resoloop init`）で実行した。隔離 worktree は終了後に削除した。

| ID | 手順 | 結果 |
| --- | --- | --- |
| A（R1） | `.gitignore` に `.venv/`・`secret.env` を書いた Git の作業ツリーを、実パスと symlink 経由で `plugin install` | 実パス 5 ファイル、symlink 経由 7 ファイル（`.venv/lib/site.py`・`secret.env` を含む）。`.venv` に symlink を足すと、symlink 経由は `PLUGIN_SOURCE_INVALID`、実パスは成功 |
| B（R2） | `.resoloop/plugins` を外部のディレクトリ（`user-assets/keep.txt` を含む）へのリンクにして `plugin list`、`plugin remove user-assets --yes` | `list` は `user-assets` を `PLUGIN_RECORD_INVALID` と表示。`remove` は exit 0 で、外部の `keep.txt` が消えた |
| C（R3） | 導入済みの `package/` を外へ移してリンクに置き換え、`plugin list --json` | `ok: true`。`package/linked` に子のリンクを置くと `PLUGIN_MODIFIED` |
| D（R5） | directory の記録の `commit` を `"abc"` にして `plugin list` | テキストは `UNEXPECTED_ERROR`（exit 7）。`--json` は exit 0 で `"commit":"abc"` |

## 検証

| 場所 | コマンド | 結果 |
| --- | --- | --- |
| CODE_ROOT（`a9a8427`、未コミットの変更なし） | `dotnet build ResoLoop.slnx`、`dotnet test ResoLoop.slnx --no-build` | ビルド 警告 0・エラー 0。RLoop.Tests 527 passed、RLoop.IntegrationTests 19 passed（live の設定なし）。実行後も `git status --porcelain` は空 |
| head に base（`dc58ac5`）を merge した一時ツリー（merge コミット `212f3ac`、push しない） | 同上 | 競合なし。ビルド 警告 0・エラー 0。RLoop.Tests 531 passed、RLoop.IntegrationTests 19 passed。一時ツリーは削除した |

公開 CI: run 38794156165 がこの head で `linux-offline-python`（45 秒）・`windows`（3 分 56 秒）とも成功（`gh pr checks 20 --repo usaturn/resoloop`）。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

「対応しない」のうち、実在する制約で PR 本文の保証と食い違うもの（R1〜R5）を、既知の制限に条件と回避方法つきで足す。

- R1: 「Git の作業ツリーの最上位は `git ls-files` の一覧で写し、無視されたファイルは入らない」は、symlink を含むパスと `git` が失敗したときに成り立たない。実パスを渡す
- R2: 「`.resoloop/plugins/NAME/` だけを消す」は、親がリンクならリンク先で行う。`.resoloop/plugins` を実ディレクトリに保つ
- R3: 「リンクは `PLUGIN_MODIFIED`」は、`package/` 自体のリンクには成り立たない（中身は照合する）
- R4: 「他のプラグインが提供する名前は導入の前に拒否する」は、同時の導入では成り立たない。一方を `remove` する
- R5: 「`List()` は全プラグインを照合の結果つきで返す」は、手で壊した記録ではテキストの出力が落ちる。`--json` を使うか、導入し直す

## 作業時間

- 1 回目 2026-10-16T03:49Z 頃〜03:52Z 頃（約 3 分）: PR の状態とレビューの有無の確認。レビューが無く、利用者の判断で止めた
- 2 回目 2026-10-16T04:29Z 頃〜04:50Z 頃（約 21 分）: レビューの読込と境界・worktree の確認（約 4 分）、変更ファイルと関連処理の精読（約 6 分）、再現（約 3 分）、ビルドとテスト 2 回（約 4 分）、Spec の作成（約 4 分）
