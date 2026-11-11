# 修正の確認（mode: fix_check）

## 完全入力と期限

request は次の7項目だけを持つ JSON object。全て必須、未知キーと型の暗黙変換は拒否する。

| キー | 値 |
| --- | --- |
| `repository` | `to` を HEAD に持つ checkout（修正を commit した worktree）の絶対パス。from も読める同じ repository のもの。HEAD が `to` でなければ dispatch は起動の前に終了コード 2 で止まる。runner が保護するのはこの checkout だけ（main worktree を含むほかの checkout の変化・回収・監査不能は `unprotected_changes` に報告するだけ） |
| `from` | 修正前の完全な小文字 hex SHA（40/64文字） |
| `to` | 修正後の完全 SHA。検証の `reviewed_head` と同じ |
| `fix_ids` | 1件以上、重複なし、空白だけでない参照文字列の配列 |
| `fix_sections` | 採用変更と検証を含む Spec の Fix 節全文。空白のみ不可 |
| `verified_file` | 入力の確認済み一覧の絶対パス。旧配置も読取元として使える |
| `review_dir` | 新規成果物を保存する D-10 レビューディレクトリの絶対パス（`verified/` の親） |

不足時は入力不備として停止する。会話・過去案・未コミット変更から補わない。呼び出し前に verified_file を既存 helper で validate し、PR/対象 HEAD と fix_ids の対応を確認する。`TARGET_REPO_ROOT=repository`, `VERIFY_HEAD=to` とし、[共通の隔離手順](../SKILL.md#ツールと隔離実行)を使う。

呼び出し側は入力のPRを `review_target.py resolve <PR URL> [--code-root <明示checkout>]` で確認し、その JSON の `review_dir`（既存 `review_directory` が組み立てる D-10 パス）を `OUTPUT_REVIEW_DIR` とする。`review_dir` 入力がこのパスと一致することを dispatch 前に確認し、不一致なら入力不備として停止する。`verified_file` の親や旧配置の読取先を保存先に流用せず、無断で request を補正しない。修正確認の対象SHAは引き続き request の `to` であり、resolve が返す公開PR headへ置き換えない。resolve の `review_dir` はまだ無いことがある。PR照合と保存先のリンクの確認の後、dispatch の前に `OUTPUT_REVIEW_DIR` を作る（[cycle の保存先確定](cycle.md#新規成果物の保存先)と同じ時点）。`verified/` は作らなくてよく、作るならディレクトリにする。dispatch は保存先を作らず、無ければ起動の前に終了コード 2 で止まる。JSON・sidecar・要約は全て `OUTPUT_REVIEW_DIR/verified/` に保存する。D-10の保存条件を満たせなければ理由を報告して停止する。

期限は最大1800秒、確定・保存の予約は `min(300, deadline_seconds // 2)` 秒。dispatch の `time_limits`（started_at, stop_new_checks_at, deadline_at）が指定する絶対期限を守る。確認の区切りで `date -u` を確認し、stop_new_checks_at 後は新規確認を始めず未確認を unchecked と coverage.remaining にして deadline_at 前に返す。再委譲しない。順序は一覧固定（主張・全変更ファイル・文書候補）→文書候補の判定→主張の確認→変更ファイルの検査。段階内は短い確認から行う。

関連テストを通しローカルで commit した修正を、実装時の思い込みではなく主張ごとの証拠で確かめる。確かめるのは `to` のコミット済み内容と隔離 worktree での実行だけ。

## 担当の割り当て

固定仕様は [agent_runner のインターフェース](../../../../tools/agent_runner/interfaces.rst)。工程名 `fix_check` に対応する設定の役割名は **`fix-check`**。`workflows.fix.assignments.fix-check` の一次担当 1 件と明示 fallback を使う。他の役割を一緒に起動しない。

```bash
uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/../../../tools/agent_runner/with_keys.py" -- \
  python "$SKILL_DIR/scripts/dispatch.py" \
  --request "$FIX_INPUT" --output-dir "$NEW_RUN_DIR"
```

`with_keys.py` は、ランチャー起動セッションでも runner に key を届ける wrapper である（`.devcontainer/README.md` の「API トークン」節）。wrapper は後段と同じ checkout のものを使う。上の `$SKILL_DIR/../../../tools/agent_runner/with_keys.py` は helper と同じ checkout から導く。別の checkout の wrapper を使うときは、後段の雛形を `--template` で wrapper に渡す。helper に `--template`・`--config` を渡すときは、wrapper の `--` の前にも同じ値を渡す。wrapper と helper が同じ checkout のとき、渡さない既定では両方がその checkout の雛形と `resolve_config_path()` の個人設定を使うので、何も足さなくてよい。`accept` は runner を起動しないので wrapper を通さない。

`SKILL_DIR` はこのスキル本体の絶対パス。既定 template は TOOL_ROOT の `.devcontainer/agent-runner.toml`、personal config は明示 `--config` または既存の設定解決順を使う。共有 template に workflow.fix が無ければ、利用者設定か session 内の明示 `--template` で供給する。共有設定へ自動追加しない。request は上の 7 項目を持つ JSON、NEW_RUN_DIR は既存でない一意の保存先（親 main root の agent_tmp.py で作ったセッション領域の子）。`--template`/`--config` を使うときは上のとおり wrapper の `--` の前にも同じ値を渡す。担当だけ上書きする場合は `--assign <agent_id|self>` を helper だけに付ける。書き込み役・複数一次担当・不完全入力は拒否する。

dispatch の終了コードは次のとおり。出力の JSON 行は `state`・`artifact_dir`・`outside_changes`・`unprotected_changes`・`checkout_audit`・`review_changes`。`outside_changes` は runner が保護する checkout（request の `repository` の checkout）の変化・削除・監査不能。`unprotected_changes` はそれ以外の checkout（main worktree を含む）の内容の変化・登録ごとの回収・監査不能（多くはほかのセッションの worktree や親の checkout）で、終了コードにも受け取りにも影響しない（`tools/agent_runner/interfaces.rst`）。起動前（`self` を含む）に、`review_dir` が既存のディレクトリで、`verified` が無いかディレクトリであることを確かめる。満たさなければ担当を起動せず、`artifact_dir` も作らず、保存先を作成・削除・置換しない。起動前に `review_dir` 本体の device/inode と全エントリの種類・権限・内容ハッシュを固定し、停止確認後に照合する。同じ内容を持つ別ディレクトリへの置換も変更として拒否する。Gitignored・対象 repository 外の保存先も検査する。リンクはリンク先の文字列のハッシュだけを記録し、参照先は走査しない。保存入口の `review_dir` 本体・その全祖先・`verified` のリンクは起動前と各 snapshot 前に拒否する。accept は inventory 再生成前と、全ての文書・主張の検証後から最初のディレクトリ・一時ファイル作成までの間に、同じ処理で起動時の snapshot 全体と再照合する。リンクだけでなく root の device/inode、全エントリの種類・権限・内容・リンク先の変更や監査不能も、保存前に拒否する。

- 0: `self`、または `success` で `outside_changes` と `review_changes` が空。
- 1: 失敗・停止未確認、または `outside_changes` / `review_changes` がある（`success` でも 1）。停止未確認では保存先を読み直さず `review_changes` は null、監査不能も無変更とはしない。
- 起動前の checkout 監査失敗は `state=failed`, `category=environment` の診断を stdout JSON に出し終了1。監査できない状態を無変更にしない。
- 2: 設定・入力の誤り。`review_dir` が無い・ディレクトリでない、`verified` がディレクトリでない、を含む。stderr に、秘密を含まない分類（設定・runner のカテゴリ、request の誤った欄名、入力の誤りの種類）を出す。

`dispatch.json` の欄は、`batch`（runner の結果）・`request`（検証済みの入口）・`verified`（入力の確認済みの一覧）・`skill`（`path` と `sha256`）・`verifier`（`success` のときの実測値、ほかは null）・`time_limits`・`review_snapshot`（起動前の保存先の相対パスと観測値。内容そのものは保存しない）・`review_changes`（変更パス、停止未確認なら null）・`prompt`（`self` のときだけ）。

- `self`: 外部を起動しない。`dispatch.json` の完全入力と prompt に従い司令塔が下の確認を実行する。未実施の確認を合格としない。司令塔が自分で実行したことは、一覧の該当する `basis` と要約に書く。
- 外部: 同期終了した結果を、次の helper で検査して保存する。`$RUN_DIR` は dispatch が出力した JSON 行の `artifact_dir`（`dispatch.json` のあるディレクトリ）。失敗を暗黙に self へ置き換えない。runner の success は応答の回収成功だけで、payload の中身の正しさは保証しない。外部担当は呼び出し側の保存先に書かない。

  ```bash
  uv run --project "$PARENT_ROOT" --locked python "$SKILL_DIR/scripts/dispatch.py" accept --run-dir "$RUN_DIR"
  ```

  - 終了コード 0: 受け取った。保存した 2 つのパス（`statement_candidates` と `fix_check`）を JSON で 1 行出力する。要約の `.fix-check.md` は helper が書かないので、呼び出し側が受け取った一覧から書く。
  - 終了コード 1: 受け取らない。helper は正式な成果物を追加保存せず、理由を stderr に 1 行出す。保存先が起動前と違う場合は、不正な payload でも、その検査より先に拒否し、変更した相対パスをエスケープして列挙する。外部担当や他セッションが書いたファイルは自動削除・復元しない。列挙されたファイルを以前の成功した保存とは見なさず、この run の結果として使用しない。これは観測時点での受け取りの検査であり、検査と保存の間の悪意ある同時変更を防ぐ sandbox や変更の復元を保証しない。保存の途中で I/O のエラー（`OSError`）が起きたときも 1 で、helper は自分が置いたものを置く前に戻し、保存先全体が dispatch 時と同じことを確かめてから終わる。原因を `review_dir` の中を変えずに直せば（`review_dir` の外の空きを作る、など）、同じ `--run-dir` でやり直せる（外部の担当を起動し直さない）。`review_dir` の中（`verified/` の権限など）を変えて直すと dispatch 時と違うので拒否され、dispatch し直すことになる。
  - 終了コード 2: `dispatch.json` が読めない、固定済みの `verified.pr` が欠落・不正、またはレビューディレクトリが無い。
  - 終了コード 3: 保存の途中の I/O のエラーの後、保存先を dispatch 時の状態に戻せなかった、または戻したことを確かめられなかった。dispatch 時と違う相対パスをエスケープして列挙する。以前の一覧は不整合なことがある。回復の仕方は「保存する結果」。
  - 受け取らない条件: 結果が `success` でない（`self` を含む。self は司令塔が自分で確認して validate する）、どれかの attempt の `stop_confirmed` が真でない、runner が保護する checkout が変わった・消えた・監査できない（`outside_changes`・`checkout_audit` の `protected` な観測。`unprotected_changes` は理由にしない）、保存先が起動前と異なる（dispatch 後の変更も再検査）・監査できない・保存入口・その祖先・`verified` がリンク、最後の payload が `verified` と `inventory` の 2 つの object だけでない、payload の `verified.pr` の repository または number が `dispatch.json` の `verified.pr` と違う、`inventory` が道具の出力と合わない、`inventory.fix_ids` が request の `fix_ids` と違う、validate に通らない。
  - 対象 PR は dispatch 時に保存した `verified.pr` を基準に照合し、元の `verified_file` を再読込して変更しない。固定済み PR の欠落・不正と、結果の PR の不一致は、`verified/` や成果物を作る前に拒否する。
  - `inventory` は、道具（`statement-candidates`）の出力をそのまま含み、担当が見つけた語・候補を後ろに足しただけのものだけを受け取る。道具の候補・変更ファイル・主張を消したり書き換えたりしたものは受け取らない。
- 外部の `verifier` は `dispatch.json` の同名フィールド（実担当の model/runtime/provenance）で全体を置き換える。helper が runner の identity の null を unknown、skill_versions を skills(path/sha256)へ変換し、run_id/request_id/actual_agent は BatchResult/Result から、runtime は actual_agent の設定から得る。requested model/provider/effort を actual にコピーしない。実測 skill_versions の `sha256:` 接頭辞は除去し、skill 名だけのキーからパスを推測せず unknown にする。不明パスに異なる hash が複数ある場合は 1 つを選ばず、v2 の unknown 行にまとめる。元の名前と値は BatchResult に全件保持する。inline で渡したこのスキルの内容は input の skill(path/sha256)で特定し、ネイティブの discovery を観測したとは書かない。self は司令塔の実観測値を使い、未観測は unknown。timing には開始/終了/秒数と waiting_seconds（未計測は null）、accuracy.verify_seconds には実測値を記録する。入力レビュアーの provenance は inputs と accuracy で同じ観測値を使う。

## 読み取り専用の対象

`writes=false` は呼び出し側 checkout と提供 worktree の変更を禁止する。**担当が作る一意の一時ディレクトリでの生成物・検査用ファイル・候補 JSON・validate ログの作成は禁止しない。** from/to のコミット済み内容をそこへ展開し、そこでビルド・lint・テストを実行する。生成物を要することを未実施の理由にしない。資格情報や環境変数の例は fake CLI と `env HOME="$TMP_HOME" ...` のワンショットだけで試す。実環境の資格情報や実サービスを使わない。uv は Python 3.14 以上で実行する。元 checkout の修正・commit・push や他者の作業領域への書き込みはしない。外部の担当には、dispatch が、これらの書き込み（一意の一時ディレクトリ、再現用 worktree の登録、`tool_root` の helper の実行、uv の環境）を runner の作業範囲の指示の例外（`dispatch.py` の `fix_check_write_exceptions`）として渡す。例外の見出しは「only these」なので、許可は依頼の本文ではなくこの一覧に並べる。

## 主張と変更ファイルの一覧

**判定より先に一覧を固定する。** Spec の Fix 節の採用変更・検証、from..to の commit message、書き足した説明を読み、独立した主張を 1 件ずつ列挙する。1 つの説明が複数の性質を主張するなら分ける。`claims.json` は `{"fix_ids": [...], "claims": [{"id": "C-1", "fix_id", "claim", "source", "kind": "artifact"|"behavior"|"static"}]}`。各 Fix に 1 件以上。出典を記録し、確認しづらい主張を一覧から消さない。

- artifact: 生成して、その主張が現れる全データ/ノード/出力と意味を検査する。ビルド成功や構造の一部分だけで、他の属性・関連・名前まで満たすと判断しない。検査述語と観測値を artifact 欄に残す。
- behavior: 別の入力・境界・失敗状態も実行する。
- static: コミット済みの記述を読む。実行が必要な主張を static へ読み替えない。

変更ファイルは道具が全パスを列挙する。各ファイルに適用する lint・型検査・ビルドの規則を定義元から読む。たとえば RST は [rst-core-style-guide](../../rst-writer/references/rst-core-style-guide.md) と対象プロフィール、リポジトリの検証は AGENTS.md。規則をここに写さない。削除/rename/テストも検査欄から落とさない。コマンドを `to` の隔離 worktree で実行し、規則の定義元、コマンド、HEAD、終了コード、結果を `fix_evidence.files` に残す。削除や適用する検査が無い場合だけ理由付き not_applicable。環境不足・時間切れは unchecked と coverage.remaining。lint 規則が `--fix` を使う場合は隔離コピーでだけ実行し、実行前後の hash/diff も保存する。終了 0 でも修正が発生したらコミット済みの原文は規則違反なので failed の指摘にする。自動修正後のコピーを元のコミットの合格証拠にしない。

確認を始めたら、文書候補と主張と変更ファイルを道具で列挙してから照合する。

1. 条件を述べている文書の候補を列挙する。

   ```bash
   uv run --project "$PARENT_ROOT" --locked python "$TOOL_ROOT/.agents/scripts/review_findings.py" statement-candidates --root "$TARGET_REPO_ROOT" --from <from> --to <to> --claims "$CLAIMS_JSON" --output "<自分の一意の一時ディレクトリ>/<to 先頭 12 文字>.statement-candidates.json"
   ```

   外部担当は、この一時出力の内容を `inventory` として返す。呼び出し側の保存先へは書かず、保存は `accept` が行う。self では司令塔が validate して保存する。
   修正の差分から、コードの変更行と前後の行の状態名・識別子・CLI オプションと、文書の変更行（追加・削除）の識別子らしい語・コードスパン・RST の directive 名と role 名を取り出し、`to` のコミット済みの README・SKILL.md・`*.rst` などを検索した結果である。ヒットが多すぎる語は `common_terms` に件数だけが入る。文書の小文字だけの語（`body`・`deprecated` など）とコードスパンでない `.` を含む名前は取らないので、文書・テンプレートの修正では、変更行の主題の語を自分で足して検索する（`inventory` の後ろに足す）。
2. 候補を判定する。
   - 判定の単位: `consistent`・`inconsistent` は候補ごとの判定行（`ids` が 1 件）にする。`unrelated`・`unchecked` は、理由が同じ候補を語ごとにまとめてよい。
   - 読む範囲: 名前を含む前後の段落も読み、全 Fix のどの主張/変化に関係するかを確認する。同名の 1 条件だけを見て、他の Fix や別の属性・値・場所・経路の変化を見落とさない。
   - `basis`: basis には比較した具体的な変更前→変更後の値と、文書の記述を書く。`unrelated`・`unchecked` をまとめた行の `basis` には、その語がそこで何を指すか（`unchecked` なら足りない確認）を書く。
   - 候補の `text`: 長い行では一致した語の前後の抜粋なので、`consistent`・`inconsistent` にする前に `git show <to>:<path>` でその行と前後の段落を読む。
   - 関係の判断:
     - 「禁止を明記していない」「同じ工程の説明」は consistent の証拠ではない。関係がある候補は実装/実行の具体的な値と文書の値が合うか確かめる。
     - `unrelated` は同名の別物など事実として関係が無い場合だけ。「通常の利用ではない」「利用者はそう使わない」は採否なので、この値の根拠にしない。
   - 条件を狭めた修正:
     - **from では満たせて to では外れる場面**を先に列挙し、そこで文書の手順を実行して両者を比較する。
     - 境界を越える値・設定の継承や伝播を変えたなら、直接の入口だけでなく、その後段で同じ文書手順を実行する組み合わせも試す。
     - **from/to で同じ入力と前処理を保つ。** 値は入口の前で 1 回だけ用意し、その値を使う後段の手順を実行する。境界通過後に不足した値を再設定してからの成功は、失われた伝播を確かめた証拠にならない。
     - from 成功→to 失敗の事実を回避策や追加条件で消さない。文書に範囲の限定が無いのに特定の境界だけ無関係と推測しない。
     - fake の値/コマンドで確かめ、通常の利用と認めるかは判定しない。実行できなければ unchecked で残す。
   - 判定の種類: `consistent`（一致）・`inconsistent`（不一致）・`unrelated`（修正した条件と関係ない）・`unchecked`（時間切れなどで判定できない。`coverage.remaining` に残す）のどれかにする。
   - **ヒットしたのに判定しない候補を残さない。** 言い換えて書かれた記述（同じ状態や操作を、条件を付けずに述べているもの）は、語が一致した行を読んで判断する。
3. `inconsistent` の候補は、指摘（`findings[]`）の `statement_sites` に `inconsistent` で書く（同じ `path`）。
4. 判定を一覧の `statement_candidates`（`file` と `judgments`）に書く。`common_terms` の語は、修正した条件に関わるものだけ、自分で絞って検索する。
5. 列挙した主張を `fix_evidence.claims` に、各変更ファイルを `fix_evidence.files` に全件判定する。形は [review-findings の 5 章](../../../review-findings.md#修正の主張と変更ファイルの検査fix_evidence)。主張は holds/violates/unchecked、ファイルは passed/failed/not_applicable/unchecked。checks に command/head/mode/exit_code/result/artifact、問題は confirmed の findings 参照を残す。unchecked は coverage.remaining の claim:C-ID/file:PATH にも残す。判定後に都合よく一覧を減らさない。
6. `validate` は文書候補・主張・変更ファイルの全件判定、出典 HEAD、実行証拠と問題の指摘参照を突き合わせる。候補の sidecar も同じディレクトリに置く。通らなければ保存せず、原因を調べて直す。自然言語の主張の完全な抽出や証拠の意味まで道具が証明するわけではない。

道具の候補は最低限のもので、検索の上限ではない。次の範囲のうち、条件を述べている箇所の照合では、候補に無い箇所も自分で探す。

- 範囲:
  - 修正の差分（`git -C "$TARGET_REPO_ROOT" diff <from>..<to>`）が、意図した性質を満たすか
  - 修正した性質についての同じ種類の別の入力（確認済みの一覧の `variants` と、新たに挙げたもの）で、修正が効くか
  - 修正が変えた条件を述べている箇所（README・スキルの本体・`interfaces.rst`・ヘルプ）が、新しい条件と一致するか。修正の差分で文書の記述を書き換えたなら、`git -C "$TARGET_REPO_ROOT" diff <from>..<to> --` で書き換える前の記述の語を取り出し、その語でほかの文書を検索する（直し忘れた文書は古い記述のまま残っている）。あわせて、変えた振る舞いに関わる状態・操作・コマンドの名前でも検索する。修正が条件を狭めた（受け付ける・続ける・成功とする場合を減らした）ときは、その振る舞いを条件なしで述べている箇所（「〜後も対応する」「〜でも動く」「必ず〜する」など）を探す。狭めた条件がその箇所に書かれていなければ `inconsistent` にする
  - 修正で書き足した説明（docstring・コメント・README・スキルの文言）が主張していることが、事実か
- **PR 全体の再レビューはしない**（push 後の次のサイクルで行う）。
- 出力は `verified/<修正後 HEAD 先頭 12 文字>.fix-check.json` と `.fix-check.md`。同じ to でやり直すと既存結果を置き換える。新しく見つけた問題は、サイクルの確認と同じ形で書く（判定と根拠。採否は書かない）。確認担当が見つけた問題の `sources` は空の配列にし、参照は `fix-check#V-<n>@<to 先頭 12 文字>` と書く。
- 呼び出し側（review-fix-planning）は、結果の問題を自分の決め方で判断する。このスキルは push を止める・進めるを決めない。

## 保存する結果

新規の `review-findings/v2` は共通の項目に加え、`fix_check={from,to,fix_ids}`、`statement_candidates={file,judgments}`、`fix_evidence={claims,files}` を必須にする。外部 payload は正確に `{"verified": object, "inventory": object}`。accept は sidecar → fix-check JSON の順で保存し、2件同時の一括置換を保証しない（置き換えの間に読む読み手は、新しい sidecar と古い fix-check JSON の組を見ることがある）。同じ to の再試行では既存結果を置き換える。self は両方を同じ一時保存ディレクトリに置いて validate 成功後に保存する。要約は [共通の保存・報告](../SKILL.md#保存と報告)の順序で呼び出し側が書く。

accept は、置き換える前の同名のファイルを一時ディレクトリ `verified/.accept-*/` に `<名前>.previous` として写してから置き換える。保存の途中で例外が上がったら、この accept が置いたものだけを置く前に戻す。戻すのは、置いたときの inode と内容のままのファイルだけで、他者が置き換え・書き換えたものは戻さない。

| 失敗した時点 | 初回の保存（同じ名前の結果が無い） | 既存の結果の更新 |
| --- | --- | --- |
| 置き換えの前（`verified/`・一時ファイル・写しの作成、sidecar の置き換え） | 作った `verified/` と一時ディレクトリを消す | 既存の 2 件は変わらない。一時ディレクトリを消す |
| fix-check JSON の置き換え | 置いた sidecar を消し、作った `verified/` と一時ディレクトリを消す | 置いた sidecar を写しで戻し、一時ディレクトリを消す |

- 戻した後に、保存先全体を dispatch 時の snapshot と照合する。同じなら終了コード 1 で、原因を `review_dir` の中を変えずに直してから同じ `--run-dir` で accept をやり直す（中を変えて直したときは拒否されるので、dispatch し直す）
- 戻す操作が失敗した、他者が変えていたので戻さなかった、照合できなかったときは終了コード 3 で、戻さなかったファイルの写しは一時ディレクトリに残る。列挙したパスに他者の変更が無ければ、この run が置いたファイルを写しで置き換え（写しが無ければ消し）、一時ディレクトリと dispatch 時に無かった `verified/` を消すと、同じ `--run-dir` でやり直せる（戻しきれていなければ accept が拒否する）。他者の変更があれば、その run は使わずに dispatch し直す
- `OSError` 以外の例外（Ctrl-C など）でも置いたものは戻してから上げ直すが、照合はせず、終了コード 1・3 にもならない。`verified/` や一時ディレクトリを作った直後に届くと、空のディレクトリが残ることがある。状態は、同じ `--run-dir` で accept をやり直すと分かる（dispatch 時と違えば拒否される）
- 保証するのは、保存の処理の中で上がった例外だけである。突然死（kill・電源断）では、一時ディレクトリや、新しい sidecar と古い fix-check JSON の組が残ることがあり、同じ run の accept は保存先の照合で拒否される（写しから手で戻す）。最後の観測の後に他者が保存先を変えた場合（2 回目の照合から置き換えまで、戻す前の確認から戻すまで）と、電源断に対する永続性（fsync しない）も保証しない
