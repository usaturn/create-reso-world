# create-reso-world PR #109: プラグインの土台の文書のレビュー修正要否

- 文書管理リポジトリ: `usaturn/create-reso-world`（PR #109 の head ブランチ `docs/issue-97-plugin-core`）
- 対象リポジトリ・PR: https://github.com/usaturn/create-reso-world/pull/109（`docs/issue-97-plugin-core` → `main`）
- 関連 Issue: #97（PR 本文の `Refs`。親 #95。`closingIssuesReferences` は空）
- 関連文書: `docs/superpowers/specs/2026-10-16-create-reso-world-issue97-resoloop-plugin-core-design.md`、`docs/superpowers/plans/2026-10-16-create-reso-world-issue97-resoloop-plugin-core.md`、`docs/superpowers/specs/2026-10-16-usaturn-resoloop-pr20-plugin-core-review-fixes-design.md`
- 検証した HEAD: `8429ef937b70f79ad163d73efd192c54d1e6ce19`（レビューの対象 `fe39954` の子。差分は PR #20 の review-fix Spec の追加だけ）
- 状態: completed
- 実行許可: 利用者が `/review-fix-planning #109` を指定した。計画のみの制限は無く、同スキルの完遂（修正要否の確定、修正が不要ならマージと関連 Issue の更新）として扱う
- 結論: 2（修正不要としてマージ）
- PARENT_ROOT: `/workspaces/reso-world`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-97-plugin-core-docs`（PR の head を checkout 済みの既存 worktree を、clean・HEAD 一致の条件で再利用。このセッションの片付け対象ではない）

## 入力

`reviews/#109-docs-issue-97-plugin-core/` の 4 ファイル。対象 HEAD はすべて `fe39954d8673` で、`pull/109/head`（`8429ef9`）の祖先である。

| ファイル | 判定 | 指摘 |
| --- | --- | --- |
| `claude-opus-5-5.md` | Approve | Info 2 |
| `gpt-6.1-sol.md` | Approve | なし |
| `SWE-2-High.md` | Approve | Medium 1、Info 1 |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | Approve | Info 5 |

## 分類

| ID | 出どころ | 指摘 | 分類と根拠 |
| --- | --- | --- | --- |
| R1 | Opus I-1、SWE M-1、DeepSeek I-1 | Plan の全文ブロックのうち `PluginRegistry.cs`（`PluginFiles.Scan`、1543 行）と `PluginInstaller.cs`（`DeleteTree`、2128 行）が、最終レビューの修正 `a9a8427` の前のリンクの判定（`LinkTarget` または `ReparsePoint`）のまま。Plan 59 行目は全文と宣言し、Spec 230 行目と食い違う | 対応しない。現行 HEAD で確認した（全文ブロック 14 個を抜き出して `a9a8427` と比べ、12 個が一致、2 個が判定の 1 行と理由のコメント 1 行だけ違う）。致命的でない理由: Plan の実装は完了し、fork の `main`（`39db994`）に `a9a8427` の内容でマージ済みで、2 ファイルとも `a9a8427` と同じ。修正は Plan の「実施結果」と「判断」に書かれている。`docs/superpowers/README.md` 52 行目は、Plan を今の環境でそのまま再実行する手順ではなく記録と定める。上流への提案 #105 の入力は fork の `main` のコミットで、#98〜#100 は `src/RLoop.Core/Plugins/` の既存のファイルを変えない。ブロックを写して実装し直す経路は無い |
| R2 | Opus I-1、DeepSeek I-4 | 実施結果の「2088 行の追加」は修正前の `6443d70` の値で、`a9a8427` は 2089 行 | 対応しない。確認した（`git diff --shortstat 99c59be` で `6443d70` は 2088、`a9a8427` は 2089）。記録の数値で、使うと誤る手順は無い |
| R3 | Opus I-2 | Spec は `Load` の誤りを「無ければ PLUGIN_NOT_INSTALLED、問題があればその誤り」、`PLUGIN_NAME_INVALID` の場面を `remove` だけとするが、実装の `Load` も規則に合わない名前を `PLUGIN_NAME_INVALID`（終了コード 2）にする | 対応しない。確認した（`a9a8427` の `PluginRegistry.cs:155`、Plan 1411 行、テスト `LoadReportsMissingAndInvalidNames`）。致命的でない理由: 実装が Spec より厳しく、規則に合わない名前はパスを組み立てる前に誤りで止まる。Spec どおりに使っても、誤りのコードが違うだけで何も変わらない |
| R4 | Opus I-2、DeepSeek I-3 | Spec は `commit` を「完全な 40 桁」とするが、記録の検証は 64 桁（SHA-256 のリポジトリ）も受け付ける | 対応しない。確認した（`a9a8427` の `PluginRegistry.cs:63`）。実装が広いだけで、40 桁の記録はそのまま通る |
| R5 | Opus I-2、SWE I-1 | Spec の `src/RLoop.Core/Plugins/` のファイルの表に `PluginGit.cs` が無く、`git` の呼び出しを `PluginInstaller.cs` の役割としている | 対応しない。確認した（Spec 62〜69 行、`a9a8427` の 7 ファイル）。Plan のファイルの構成（52 行）と実装にはあり、後続の子はこのディレクトリの既存のファイルを変えない |
| R6 | DeepSeek I-2 | Spec の `plugin list --json` の例（257 行）に `"problem": null` があるが、CLI は null の欄を出さない | 対応しない。確認した（`a9a8427` の `OutputWriter.cs:109` の `WhenWritingNull`）。Plan の「判断」に記録済みで、CLI 全体の既存の挙動である。状態は `ok` の欄で分かり、一覧の文書は #101 が実装の help も入力にして書く |
| R7 | DeepSeek I-5 | Spec・Plan の確認用コピー（`tmp/superpowers-review/`・`docs_draft/superpowers/`）が無い | 対応しない。確認した（どちらにも #97 のファイルが無い）。運用の手順で、PR の内容には影響しない。利用者の指示「途中で止めずに推奨案で PR まで作成して」により PR を確認の場にしており、Spec・Plan は `draft` のまま（内容の承認ではないと冒頭に書いてある） |

分類: **解消済み 0 / 対応する 0 / 対応しない 7**（レビューの指摘 9 件を、同じ内容ごとにまとめた）。「対応する」が無いので、「守る条件と影響経路」の表と、同じ条件の再発のきっかけの確認は対象が無い。

仕様の論点として残すもの:

- R1・R3〜R6: 完了した Plan・Spec の細部を最終の実装に合わせ直すか、実施結果と fork の `main` を参照すれば足りるとするか

## 確認の範囲

- 変更ファイル: Spec（313 行）、Plan（2460 行）、PR #20 の review-fix Spec（90 行）の全文
- 実装との照合: Plan の全文ブロック 14 個を `external/resoloop` の `a9a8427` と比べた（R1）。fork の `main`（`39db994`）の `PluginRegistry.cs`・`PluginInstaller.cs` が `a9a8427` と同じこと、R3〜R6 の該当行を `git show` で読んだ
- 関連: `docs/superpowers/README.md` の文書の位置付け、Issue #98〜#101・#105 の「変えないもの」と入力
- 自己確認: 文書に秘密情報が無いこと（URL の `secret-token` はテストの `example.invalid`）、Plan の手順の対象（fork のブランチ・PR、マージはしない）を読んだ。PR が持ち込んだ致命的な欠陥は見つからなかった

## 検証

文書だけの変更なのでテストは書かない（AGENTS.md の「テストの採用基準」）。構造の検査で代えた。

| 場所 | 検査 | 結果 |
| --- | --- | --- |
| 専用の worktree（`8429ef9`、未コミットの変更なし） | 変更 3 ファイルのコードフェンスの対応、`json` のブロックの解析、Spec・Plan の相互参照の実在、`git diff --check origin/main...HEAD` | フェンス 30 組がすべて閉じ、JSON 5 個が解析でき、参照 4 件が実在。空白の誤りなし |
| head に base（`1129cb3`）を merge した一時ツリー（merge コミット `26129d2`、push しない） | 同上 | 競合なし。結果は同じ。一時ツリーは削除した |

CI: create-reso-world はプライベートで CI を止めているため確認しない（AGENTS.md の「GitHub Actions」）。

## 自己レビュー

未実施。結論 2 で修正が無いため、修正後の自己レビューの対象が無い。

## PR 本文に書き足すこと

R1・R3〜R6 は、PR 本文が示す「Spec の API・エラー」「Plan の実施結果」と細部が食い違うので、既知の制限に足す。

- Plan の全文ブロックのうち `PluginRegistry.cs`・`PluginInstaller.cs` の 2 個は、最終レビューの修正（`a9a8427`）の前の版である。最終の内容は fork の `main` と Plan の「判断」を見る
- Spec の API と記録の説明は、実装より狭い箇所がある（`Load` も `PLUGIN_NAME_INVALID` を返す、`commit` は 64 桁も受け付ける、`git` の呼び出しは `PluginGit.cs`、`plugin list --json` は null の欄を出さない）。細部は fork の `main` の実装を基準にする

## 作業時間

着手の時刻は記録していない。2026-10-16 に、レビューの読込と境界・worktree の確認（04:56Z まで）、指摘の再現と変更ファイルの精読（04:56Z〜04:58Z 頃）、構造の検査と base との merge の検査、Spec の作成（〜05:00Z 頃）を行った
