# サイクルの確認（mode: cycle）

## 入口と HEAD

`TOOL_ROOT`・`PARENT_ROOT` は [SKILL.md](../SKILL.md) のとおり。既知でない repository は利用者が明示した checkout の絶対パスを `--code-root` に渡す。remote が対象 owner/repo と一意に一致することは resolver が検査する。既知の経路は AGENTS.md の「リポジトリ境界」に従い、不足 checkout を探したり clone したりしない。owner 名だけで一律拒否しない。

```bash
TARGET_JSON=$(uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_target.py" review-dir "$ARG" --for-planning)
```

必要な場合は `--code-root "$CODE_ROOT"`、曖昧な旧配置の明示パスには `--pr "$PR_URL"` を追加する。番号・URL は親の `reviews/<owner>/<repo>/` 直下だけを探す。旧配置は明示パスだけで読む。非0では停止し、2=指定不正、3=PR無し、4=repository無し、5=認証、6=API、7=親/checkout、8=レビュー無し、9=候補複数、11=パス/PR対応、12=fetch を区別して報告する。9 は候補の完全パスを示す。

JSON の `parent_root`, `repository`, `number`, `url`, `review_dir`, `target_root`, `base_remote`, `head_sha`, `base_ref` を使い、`TARGET_REPO_ROOT=target_root` とする。返された実在 checkout を使う。番号・URL の経路でも全入力候補の `pr.repository` と `pr.number` を解決した PR と照合する。別 PR の候補は使わず、不一致を報告する。パス名から repository を推測しない。

PR head は既存 helper の `fetch_pull_head(checkout, repository, number, head_sha, remote=base_remote)` で `refs/pr-review/repos/<owner>/<repo>/<N>` に固定する。CLI に clone サブコマンドはない。呼出例（値は取得した JSON から渡す）:

```bash
uv run --project "$PARENT_ROOT" --locked python - "$TOOL_ROOT" "$TARGET_REPO_ROOT" "$PR_REPO" "$PR_NUMBER" "$VERIFY_HEAD" "$BASE_REMOTE" <<'PYCODE'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / '.agents/scripts'))
from review_target import fetch_pull_head
print(fetch_pull_head(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), sys.argv[5], remote=sys.argv[6]))
PYCODE
git -C "$TARGET_REPO_ROOT" fetch --no-tags "$BASE_REMOTE" "$BASE_REF"
BASE=$(git -C "$TARGET_REPO_ROOT" merge-base FETCH_HEAD "$VERIFY_HEAD")
```

## 時間

最初の PR API 前に UTC・epoch の開始時刻を取得し記録する。全体30分、調査25分、保存・片付け5分を固定し、短い利用者予算があれば短い方を使う。途中で延長しない。段階の境目で現在時刻を確認し、調査期限後は新しい確認を始めず残りを unverified/coverage.remaining にして保存する。読み取り専用の補助委譲は [pr-review の時間・委譲規約](../../pr-review/references/time-budget.md#委譲) の起動条件を満たす最大1件。根拠の精読・最終判定は自分で行う。長時間処理は monitoring-long-tasks を使い、停止を確認してから片付ける。時刻と待ち込み秒数を timing、確認秒数を accuracy.verify_seconds に残す。

## 手順

1. **集める**
   - `TARGET_JSON` の `head_sha` を `VERIFY_HEAD` とする。上の fetch 手順で PR ref を固定し、`base_remote` の base ref を fetch して merge-base を `BASE` にする。HEAD が変われば入口からやり直す。
   - レビュアーはレビューディレクトリの直下の `<model>.md` だけで数える（`findings/` と `verified/` はレビュアーではない）。各レビューファイルの `## Review history` の最後の行の HEAD（12文字）が `VERIFY_HEAD` の先頭12文字と違うレビュアーは「古いレビュアー」として区別し（`inputs[].stale`）、その候補は確かめるが、見逃しの集計には入れない。
   - `findings/<model>-<VERIFY_HEAD 先頭 12 文字>.json` があれば、それを `uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" validate <ファイル>` で検査し、`uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" check-pair <model>.md <ファイル>` でレビューファイルと一致することを確かめてから読む（`input_kind: json`）。一致しなければ、その候補一覧は使わず、レビューファイルを読む。無いレビュアーは、`uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" from-markdown <model>.md --review-file <model>.md --repo "$PR_REPO" --pr <PR> --model <モデル> --runtime <ランタイム>` で読み取る（`input_kind: markdown`。新しい項目は空なので、このスキルが補う）。`from-markdown` が読めなかった見出しや Summary の件数との食い違いを報告して止まったときは、そのレビューファイルの Markdown を直接読む: 指摘を 1 件ずつ拾い、読めなかった理由を `coverage` に書く。指摘を黙って落とさない。
   - レビュアーが Unverified candidates に挙げた候補も、確かめる対象に入れる。
2. **まとめる**
   - 守るべき性質と位置が同じ候補を 1 件にまとめる。元の指摘の参照（`<レビューファイル名から .md を除いたもの>#<ID>@<検出 HEAD>`。判断の記録と同じ書き方）をすべて `sources` に残し、元の重大度を `reported_severities` に残す。
   - レビュアーの数は根拠にしない。似ていても性質が違う候補はまとめない。
3. **確かめる**
   - 各候補を `VERIFY_HEAD` のコミット済みの内容で読み、挙動についての主張は隔離した worktree で再現する（[共通の隔離手順](../SKILL.md#ツールと隔離実行)）。判定は `confirmed`（再現した。`reproduction` に、コマンド・場所・条件・結果。挙動についての主張は、挙動を実行した再現があるときだけ `confirmed` にする。コードや文書を読んだだけの確認は、文書・静的な主張にだけ使い、そのことを `place` に書く）、`not_reproduced`（再現しなかった・反証した。`basis` に根拠）、`unverified`（確認できていない。`missing_checks` に足りない確認）のどれかにする。
   - 「この指摘が誤りだとしたらどこか」を確かめる（既存のガード、テストによる固定、文書化された意図）。反証できたものは `not_reproduced`。
4. **別の入力を試す**
   - 確かめた性質ごとに、同じ性質に反しうる別の入力を挙げて実行する。レビュアーの `variants` に加えて、同じ文法の別の書き方、同じ状態の別の値、境界の値を自分で挙げる。報告された入力の形だけで性質を書かない（例: `Z` 付きの日時だけでなく、`+09:00` 付き・オフセット無し・小数秒付き）。
   - 入力ごとに `variants` へ、反する（`violates`）・反しない（`holds`）・未確認（`unchecked`）と、確かめた方法を書く。反する入力が見つかれば、指摘の範囲がその分広いことを `basis` に書く。
5. **条件を述べている箇所と照合する**
   - その性質や条件を述べている README・スキル（.agents の本体と、まだ一本化していない版）・`interfaces.rst`・ヘルプ・docstring を検索し（例: `git -C "$TARGET_REPO_ROOT" grep -n '<条件を表す語>' "$VERIFY_HEAD" -- README.md .agents .claude docs tools`）、実装と一致するかを `statement_sites` に書く（`consistent`・`inconsistent`・`unchecked`）。実行した検索のコマンドを `basis` に書く。
   - 検索の語は、条件の文言だけにしない。その振る舞いに関わる状態・操作・コマンドの名前（例: 状態名、サブコマンド名、設定のキー）でも探す。同じ条件を別の言い回しで述べた文書は、文言では見つからない。
6. **未確認の範囲を閉じる**
   - レビュアーが判断しなかったもの（候補一覧の `coverage.declined`、レビューファイルの Review coverage の読めなかった範囲・未実施の検証、`Needs manual verification` の理由）は、このサイクルのうちに読むか確かめ、`coverage.closed` に書く。読めないものだけを、理由を付けて `coverage.remaining` に残す。次のサイクルに回さない。
7. **PR 起因を確かめる**
   - base と比べ、PR 起因（`introduced`・`surfaced`・`preexisting`・`unknown`）と根拠（原因の commit、base 側の状態。`git show <base>:<path>`、`git log -S`）を `pr_relation` に書く。「差分に悪い行がある」だけで判断しない。原因の commit が分かれば `cause_commit` に書く。
   - 判断の記録に前のサイクルがあれば、原因の commit が前のサイクルの `reviewed_head` の祖先かどうかで、その欠陥が存在していた最初のサイクルの HEAD（`first_present_head`）と、遅れた発見か（`late_detection`）を書く。決められなければ `unknown`。
   - 安全性の 3 項目（資格情報・秘密情報が想定していない相手へ渡る、意図した範囲の外を書き換える・削除する、権限の確認や書き込み前の検査を迂回できる）に当たると主張する指摘は、示された経路（入口・入力・環境と、渡る先・書き換える先、または迂回される検査）をコードを読むか実行して確かめ、`safety_path` に書く（安全性の経路）。重大度は再評価しない。
8. **書き出す**（[共通の保存手順](../SKILL.md#保存と報告)）。`uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" validate <一時ファイル>` に通ってから、置き換える。

`accuracy` は各 reviewer の候補数・各 verdict 数・unique・missed と発見時間を記録する。同じ HEAD の他 reviewer が発見した confirmed のみ見逃しに数え、stale reviewer には現在の見逃しを帰属させない。v2 の inputs と accuracy.reviewers の model/runtime/provenance を一致させる。手動回収できなかった範囲は coverage.remaining に残す。
