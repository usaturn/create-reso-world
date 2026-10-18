---
name: review-verify
description: >-
  Use when レビュー結果の真偽・再現を確認して確認済み一覧を作る、PR のレビュー候補をまとめる、またはコミット後の修正を mode fix_check で確かめるとき。レビューディレクトリのパス・PR 番号・URL を受け取る。採否・重大度・修正方針の決定には使わない。
---

# レビュー候補の確認

全レビュアーの候補を、指定したコミット済み HEAD と隔離した worktree で確かめ、事実と未確認事項を保存する。採否・重大度の再評価・修正設計・push 可否は呼び出し側の役割であり、このスキルでは決めない。時間の圧力や多数の同意でもこの境界は変えない。

| 入力 | 読む手順 | 出力 |
| --- | --- | --- |
| レビューディレクトリの絶対パス、PR 番号、PR URL（既定 `cycle`） | [cycle.md](references/cycle.md) | `verified/<HEAD12>.json` と `.md` |
| 7 項目の JSON（`fix_check`） | [fix-check.md](references/fix-check.md) | `verified/<to12>.fix-check.json` と `.md`、同 stem の `.statement-candidates.json` |

## 共通の境界

- 新規成果物は D-10 の `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/verified/` にだけ保存する。旧配置のレビューは読取元として扱い、保存先とは分ける。ほかに書けるのは自分の一意の一時ディレクトリだけ。PR コメント、push、commit、修正、レビューファイル・候補一覧の書換えはしない。他者の未コミット変更を読まない。
- 根拠は `git show <HEAD>:<path>` と、その HEAD を照合した隔離 worktree での実行。元の作業ツリーの修正を「修正済み」の証拠にしない。
- 判定は `confirmed`・`not_reproduced`・`unverified`。挙動の confirmed には実行証拠、静的な主張にはコミット済み記述の根拠が必要。コマンド失敗・依存不足・時間切れ・未読は `unverified` と `missing_checks`。票数は根拠にしない。
- 入力不足を会話や未コミット案から補わない。秘密の値を入力・出力・ログへ写さない。

## ツールと隔離実行

`TOOL_ROOT` はこのスキルを持つ create-reso-world checkout、`SKILL_DIR="$TOOL_ROOT/.agents/skills/review-verify"`。`PARENT_ROOT` は次で取得する親 checkout。対象コードの `TARGET_REPO_ROOT` と混同しない。Python は root の uv 環境を使う。

```bash
PARENT_ROOT=$(uv run --no-project python "$TOOL_ROOT/.agents/scripts/agent_tmp.py" root)
```

各モードで決めた完全 SHA を `VERIFY_HEAD` に置き、挙動は次の worktree で実行する。入口解決・HEAD 取得に失敗したら隔離実行を始めない。checkout の探索・clone はしない。

```bash
REPRO_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/review-fix-planning.XXXXXX")
WT="$REPRO_ROOT/worktree"
git -C "$TARGET_REPO_ROOT" worktree add --detach "$WT" "$VERIFY_HEAD"
test "$(git -C "$WT" rev-parse HEAD)" = "$(git -C "$TARGET_REPO_ROOT" rev-parse "$VERIFY_HEAD^{commit}")"
```

SHA 不一致なら止め、その worktree を根拠にしない。再現スクリプト・ログ・生成物は `$REPRO_ROOT` の worktree 外へ置く。Python は `-B` でキャッシュを作らない。生成が必要ならコミット済み内容を自分の隔離コピーへ展開してそこで実行する。実環境の資格情報・実サービスは使わず、fake 値と `env HOME="$TMP_HOME" ...` のワンショットで確認する。

worktree を使う全確認の終了後に片付ける。停止未確認の担当が使っている間は削除しない。

```bash
git -C "$TARGET_REPO_ROOT" worktree remove --force "$WT" && rm -rf -- "${REPRO_ROOT:?}"
```

remove 失敗時は親を削除せず、WT と REPRO_ROOT の完全パスを報告する。再現の `place` には HEAD・隔離方法・配置を記し、消える一時パスを根拠の識別子にしない。

## 保存と報告

形式の定義は [review-findings.md](../../review-findings.md) 3・5 章。新規結果は `review-findings/v2`。`pr`, `reviewed_head`, `base`, `verifier`, `skill`, `timing`, `inputs`, `coverage`, `findings`, `accuracy` を埋める。v2 の provenance は実観測値を使い、未観測は `unknown`。実際に読んだ SKILL.md bytes の SHA256 を主要 skill と provenance.skills に同じ値で記録する。要求モデル名を観測モデル名にしない。時間不明は null、待ち時間も記録する。

各モードで入力の読取先とは別に `OUTPUT_REVIEW_DIR` を確定し、`VERIFIED_DIR="$OUTPUT_REVIEW_DIR/verified"` を使う。owner/repo・PR番号・ブランチは確認済みPRメタデータから取得し、既存 helper の `review_directory` で D-10 のパスを組み立てる（[cycle の保存先確定](references/cycle.md#新規成果物の保存先)）。出力先やその親にリンクがある、書き込めない、PR対応を確認できない場合は停止し、旧配置へ保存し直さない。

JSON と要約、fix_check の sidecar は全て `VERIFIED_DIR` に保存する。JSON はこのディレクトリの一時ファイルに書き、次を通してから `mv` で置換する。失敗時は既存結果を残す。fix_check の sidecar の検査手順はモード文書に従う。

```bash
uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" validate "$DRAFT_JSON"
```

要約の順序は、HEAD と入力 → verdict ごとの件数 → confirmed の性質・位置・別入力・不一致文書 → unverified と missing_checks → coverage.remaining → 実測時間。採否や修正案は加えない。呼び出し側へ JSON/要約の完全パス、件数、残り、時間、後片付け結果を返す。push 判断を求められたときも確認結果だけを渡す。

本体は `.agents/skills/review-verify/`。Claude Code は `.claude/skills/review-verify` の相対リンク、Pi の明示入口は `/skill:review-verify`。bootstrap・共有設定を変更しない。評価 controller 用（通常の確認では読まない）の行動評価は [evals.json](evals/evals.json)、実測記録と fixture の再実行は [validation.md](evals/validation.md)。
