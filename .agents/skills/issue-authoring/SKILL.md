---
name: issue-authoring
description: "GitHub の Issue を新しく起票するとき（「Issue を作って」「起票して」「Issue にして」「file an issue」）、既存の Issue を共有の書式に整形するとき、Issue の目標値を評価してコメントに残すときに使う。Issue への着手（実装・PR の作成）、親 Issue のボードの分割や子の選択、PR のレビューには使わない。"
---

# Issue の起票・整形・評価

Issue の書式は `.agents/issue-format.md` だけが定める。このスキルには写さない。本文・タイトル・ラベル・コメントなどの通常投稿は `scripts/publish_issue.py` の `draft` → 利用者の承認 → `publish` で行い、直接書き込んで helper を迂回しない。既存 Issue の整理で承認された同一目的の統合元を閉じる場合に限り、`references/reshaping.md` の条件と順序を満たした後、重複ラベルの追加と duplicate close の 2 操作を行う。

## モードの選び方

| 依頼 | 読むファイル |
|---|---|
| 新しく起票する | `references/authoring.md` |
| 既存の Issue を整形する | `references/reshaping.md` |
| 目標値を評価する | `references/evaluation.md` |

## 共通の動作

- 対象を `--repo owner/repo` で明示する。`.agents/issue-format.md` の対象解決と AGENTS.md「リポジトリ境界」に従い、共通 resolver が常設親・採用済み台帳・checkout と remote を確認する。不在・不一致・未登録なら止まり、別対象に切り替えない
- 対象リポジトリの AGENTS.md と README.md の規則も確認する。任意の clone や作業 checkout を推測しない
- 番号を受け取っても `gh issue view` で Issue かどうかを確かめない（PR の番号にも成功する）。`draft` が PR の番号を `not_an_issue` で止める

## 投稿の流れ

Python の例はリポジトリルートから実行する。秘密情報検査に使う Gitleaks の版は `.devcontainer/install_gitleaks.bash` の `GITLEAKS_VERSION` を確認し、検査失敗時は公開しない。

`draft` の `--out-dir` は空のディレクトリでなければ終了コード 2 で止まる。入力のファイルを `--out-dir` に置かず、案は保存のたびに新しい空のディレクトリへ書く。

1. 入力用に、親の main worktree で `uv run --locked python .agents/scripts/agent_tmp.py mkdir issue-src` を実行してディレクトリを作る。本文（`--body-file`）・機械可読ブロックの JSON（`--metadata-file`）・読んだ時点の Issue の JSON（`--read-json`。`gh api --hostname github.com repos/<owner>/<repo>/issues/<N>` の出力）のファイルは、ここに置く
2. 案を保存するたびに（作り直しを含む）、`uv run --locked python .agents/scripts/agent_tmp.py mkdir issue-draft` で新しい空のディレクトリを作る。そのディレクトリを `--out-dir` にして `uv run --locked python .agents/skills/issue-authoring/scripts/publish_issue.py draft {create|update|comment} ... --out-dir <そのディレクトリ>` を実行する（引数は各サブコマンドの `--help`）
3. **ターンを終える前には、問いを尋ねて終えるときも承認を求めて終えるときも、必ず手順 2 で案を保存する。** 問いがあっても先に尋ねず、その時点の根拠で案を作る（答えで決まる項目は `references/authoring.md` の 3 の未確定・未決事項で書く）。実行が対話か非対話かの判断に頼らない
4. 承認を求めるなら、出力の `preview` の `preview.md` を**全文**、`draft` のパス、`sha256` とともに利用者に見せてターンを終える。問いを尋ねるなら、選択肢つきの問いに `draft` のパス・`sha256` を添えてターンを終える
5. 返答を受け取ったら、問いへの答えなら案を直し、手順 2 に戻って新しい空のディレクトリへ `draft` を作り直して（`sha256` も新しくなる）手順 4 に戻る。承認なら `... publish_issue.py publish --draft <直近に見せた案のディレクトリ> --sha256 <直近に見せた値>` を実行する（`--draft` は、その `draft_saved` の `draft` の親のディレクトリで、`draft.json` ではない）

案を見せた後に内容を変えたら、手順 5 のとおり `draft` を作り直して改めて承認を得る。ただし既存 Issue の新規分割で、承認案の指定箇所に新規先 URL を入れる場合だけ、`references/reshaping.md` の限定置換を承認済み操作として扱える。仮文字列入りの元 draft を作成前に verify して提示し、作成後は同じ segments の指定箇所だけを正しい登録先の実 URL に置き換え、新 draft を build・draft update・verify する。承認時の最終本文の指定箇所だけをその URL に置き換えたものと新本文が一致し、対象 repo/番号・操作・タイトル・ラベル・関係などの比較対象も一致することを機械的に確認する。それ以外の差は新しい preview・diff・SHA を提示し再承認を得る。公開には再 verify した新 draft の新 SHA を使い、古い SHA は使わない。新 SHA は利用者が直接承認した値ではなく承認済み限定置換から生成した値として示す。

## 承認

**承認は、案を見せた後の対話での利用者の返答だけ。** 最初の依頼は案の承認ではない。複数 Issue の案も一回の返答でまとめて承認できる。承認の前は、`publish`・`gh issue create`・`gh issue edit`・`gh issue close`・`gh issue comment`・`gh label create`・`gh api` の POST/PATCH/DELETE を実行しない。helper が止まっても、直接の書き込みで回避しない。案変更の再承認には「投稿の流れ」の限定 URL 置換だけが例外となる。

| よくある言い訳 | 実際 |
|---|---|
| 「依頼が『起票して』なので承認済み」 | 依頼は案の承認ではない。案を見せて返答を待つ |
| 「非対話なので確認できないから起票する」 | 確認できないなら起票しない。`draft` まで行い、報告して終える |
| 「書式に合っているので見せなくてよい」 | 書式に合うことは承認の代わりにならない。全文を見せる |
| 「ラベルだけ先に作っておく」 | ラベルの作成も承認の対象。案に含め、`publish` に作らせる |
| 「少し直しただけなので再承認は要らない」 | 限定 URL 置換を除き、`draft` を作り直し（投稿の流れの手順 5）、改めて承認を得る |

次のどれかを考えたら止まる: 「承認済みとみなす」「作ってから見直してもらう」、案の要約だけで承認を求める、返答の前に `publish` を実行する。

## 非対話の実行

案を見せた後に返答を受け取れない実行（Claude Code で `AskUserQuestion` がツールの一覧に無い `claude -p`、`pi -p`、agent-runner の担当、CI）では `publish` も重複ラベル追加・close も実行しない。`draft` まで行い、`draft` のパス・`sha256`・尋ねたかった問い（選択肢つき）を報告して終える。helper は `CLAUDE_CODE_SESSION_ATTENDED=0`・`AGENT_RUNNER_DEPTH`・`CI` などで見分けられる実行の `publish` を `non_interactive` で拒否するが、`pi -p` は見分けられない。

`AskUserQuestion` が無いことは、Claude Code でだけ非対話の印になる。Pi は対話のセッションでも持たず、自分が `pi -p` かも観察できない。どのランタイムでも、`publish` は承認の返答を受け取った後にだけ実行する。

## helper の出力ごとの次の操作

| 出力 | 次の操作 |
|---|---|
| `draft_saved` | 投稿の流れの手順 4 に進む（案を見せて承認を待つ、または問いを尋ねる） |
| `published`・`already_published` | URL を報告し、後片付けをする |
| 終了コード 2 | 標準エラー出力の理由を読んで入力を直す |
| `check_failed`・`too_large`・`unknown_label`・`not_an_issue` | 出力の内容を読み、本文・ラベル・対象を直して `draft` を作り直す（投稿の流れの手順 5） |
| `secret_detected` | 秘密情報を本文から除いて `draft` を作り直す（投稿の流れの手順 5） |
| `scan_failed` | 止まって報告する |
| `conflict`・`draft_changed`・`labels_changed` | 取得し直して `draft` を作り直し（投稿の流れの手順 5）、改めて承認を得る。`conflict` は、読んだ後に Issue の本文・タイトル・ラベルが変わったとき |
| `non_interactive` | 報告して終える |
| `uncertain` | 送り直さず、GitHub の画面で結果を確かめるよう利用者に伝えて止まる |
| `gh_failed` | `step`・`message` を報告して止まる |

## 後片付け

通常の単票では `published` を返したら、この run で作った案のディレクトリ（作り直しで残った古い案も）と入力用のディレクトリが不要か確認して消す。AGENTS.md「削除」のとおり、削除対象に変数を使う場合は各変数に `${VAR:?}` を付け、パス全体を引用する。自分が作成した資料以外は消さない。複数 Issue の整理では最初の `published` では消さず、承認済み案・snapshot・segments・URL 置換の比較元・実施結果を全操作完了まで保持し、完了時にその run の資料をまとめて同じガードで片付ける。消せなければ完全パスを報告する。問い・承認待ちでターンを終えるとき、途中停止時、非対話の実行では資料を残し、完全パスを報告する。途中停止からは現在の状態を読み、完了済みと未実施を区別して残りだけ進め、案の変化に必要な再承認を得る。

## ランタイムごとの違い

- **Claude Code:** 問いは `AskUserQuestion`（1 回にまとめ、各問いに 2〜4 個の選択肢。推奨を先頭にして「（推奨）」を付ける）。`claude -p` は `AskUserQuestion` が無い非対話の実行で、helper が見分ける
- **Pi:** 問いを尋ねるツールが無い（対話のセッションでも）。番号付きの選択肢を本文に書き、推奨を示してターンを終える。終える前に案を保存する。`pi -p` は非対話の実行だが、Pi 自身も helper も対話のセッションと見分けられない。承認の返答を受け取るまで `publish` を実行しない
- **ほかのランタイム:** 問いのツールが無ければ Pi と同じ。helper が非対話の実行を見分けられないことがある
