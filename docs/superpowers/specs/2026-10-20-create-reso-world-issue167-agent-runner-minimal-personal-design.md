# Issue #167: agent-runner の個人設定を雛形の丸写しにしない

## 管理・実行許可

- 文書管理・コード対象: `usaturn/create-reso-world`。対象 Issue: https://github.com/usaturn/create-reso-world/issues/167（親 Issue・ボードは無い）
- 状態: draft
- 関連 Plan: `docs/superpowers/plans/2026-10-20-create-reso-world-issue167-agent-runner-minimal-personal.md`
- DOC_ROOT・CODE_ROOT: `/workspaces/reso-world/.worktrees/issue-167-agent-runner-minimal-personal`（branch `fix/issue-167-agent-runner-minimal-personal`）。PARENT_ROOT: `/workspaces/reso-world`
- 実行許可: 2026-10-20（JST）、利用者が `/issue-to-pr #167` で着手を指示した。issue-to-pr の委任により、通常の設計判断を推奨案で決め、Spec・Plan の commit、実装、検証、push の前の検査、push、PR の作成（`Closes #167`）まで行う。マージはしない
  - 下の判断は、利用者に確認を取らずに決めたエージェントの判断であり、内容の承認（`approved`）ではない
- 予約: なし（ボードの子ではないので `planning-parallel-issues` の予約を使わない）
- 基準: `origin/main` の `8f5074a`
- builder check: issue-to-pr で質問を省いたので、brainstorming の読み合わせはサブエージェントを起動せず、この Spec をエージェント自身が実装者として読んで行った。利用者に確かめる必要のある点は無かった

## 意図

postCreate（`.devcontainer/install_beforehand.bash` の `place_agent_runner_config`）が、個人設定 `~/.config/agent-runner/config.toml` に雛形 `.devcontainer/agent-runner.toml` を丸ごと写すのをやめる。runner は「雛形 < 個人設定」で設定を重ねるので、写しがあると雛形の値（役割の期限・agent のモデルやコマンド）がすべて写しの値で上書きされ、雛形を変えても次の rebuild まで効かない。個人設定は上書きの置き場所を示すだけの最小のファイルにし、雛形の値は利用者が個人設定に書いたものを除いて常に雛形から効くようにする。

## 確認した事実（2026-10-20）

- #150 は close 済みで、雛形には `[agents.*]`（DSH・pi・Claude Code・Codex・Cursor・Devin）と `[workflows.review]`・`[workflows.fix]`・`[workflows.issue]` が入っている。Issue の本文の「今の雛形は roles だけ」は書いた時点の状態で、今は写しに agent のモデル名・コマンドが含まれる
- 今のコンテナの個人設定 `~/.config/agent-runner/config.toml` は、今の雛形と同じ内容（`diff` で差分なし。2026-10-19 23:55 に postCreate が作成）。雛形が変わるまでは実害は無い
- 設定の重ね方は `tools/agent_runner/config.py` の `_merge`（table は再帰的に統合、それ以外は置換）。`schema_version` は各モデルで `Literal[1]`。個人設定に `schema_version = 1` だけを書いたファイルは、雛形に重ねても値を何も変えない
- 個人設定を作るのは `place_agent_runner_config` だけ。`~/.config/agent-runner` は mount していないので、rebuild のたびに消え、postCreate で作り直される。restart では作り直されない
- `tools/agent_runner/tests/test_cli.py` の `test_shipped_template_passes_check` は、`personal = "template-copy"` で「postCreate が雛形を個人設定に写す」ことを前提にしている
- 雛形の写しの扱いを書いた文書は `.devcontainer/README.md`（agent-runner の節と DSH の節）、`tools/agent_runner/interfaces.rst`（個人設定の段落）、雛形の冒頭のコメント、`install_beforehand.bash` の関数の前のコメント。ほかに写しを前提にするコード・スキルは無い（`git grep` で確認）

## 設計

### 最小の個人設定

追跡するファイル `.devcontainer/agent-runner-personal.toml` を足す。中身は次だけにする。

- 有効な行は `schema_version = 1` だけ
- コメントで、このファイルの役割（雛形に重ねて読む。table は統合、配列は置換。書いた値は雛形の更新より優先されるので、要らなくなったら消す。資格情報の値は書かない）と、上書きの例を示す。例は、役割の期限・workflow の担当と fallback・`after_run = []` の 3 つ程度で、すべてコメントにする。agent 名は README の例と同じ仮の名前（`agent-a` など）にする

### postCreate

`place_agent_runner_config` は、写す元を雛形から `.devcontainer/agent-runner-personal.toml` に変えるだけにする。置く条件（保存先が `XDG_CONFIG_HOME`（絶対パスのとき）か `~/.config` の下、既存の設定と壊れた symlink は変えない、置けなければ失敗を返す）は変えない。

### 文書

- `.devcontainer/README.md` の agent-runner の節: postCreate が置くのは最小の個人設定であり、雛形の値は個人設定に書いたものを除いて雛形から効くこと。上書きは要るものだけを書くこと。#167 より前に置かれた個人設定は雛形の丸写しなので、自分の上書きを足していなければ消してよい（rebuild でも置き換わる）こと
- 同 DSH の節の「既存の個人 agent-runner 設定は上書きされない。保存済みの agent 定義が古ければ…」を、個人設定に `[agents.dsh-*]` を書いているときの話に直す
- `tools/agent_runner/interfaces.rst` の「雛形をコピーした後も、既存個人設定を導入処理で更新しない。」を、導入処理が置く最小の個人設定の説明に直す
- 雛形の冒頭のコメントと、`install_beforehand.bash` の関数の前のコメントを、新しい挙動に合わせる

### 既存の写し

自動では移行しない。今のコンテナの個人設定もこの作業では書き換えない（利用者のホームの設定であり、今の雛形と同じ内容なので雛形が変わるまで実害は無い）。最終報告で、置き換えるコマンドを案内する。

## 受け入れ条件

1. 個人設定が無いとき、postCreate の関数は、runner と同じ規則で決まる保存先に `.devcontainer/agent-runner-personal.toml` と同じ内容のファイルを置く。既存の設定・壊れた symlink は変えず、保存先に書けなければ失敗を返す（今までの検査を保つ）
2. 雛形の役割の期限と agent のモデルを変えた雛形（T'）について、postCreate が置いた個人設定と一緒に `load_config` で読んだ結果が、個人設定なしで T' を読んだ結果と同じで、かつ変える前の雛形の結果と違う（変えた値が効いている）
3. 雛形と最小の個人設定の組み合わせで、`python -m tools.agent_runner check` が成功する
4. 「文書」の 4 項目を直す
5. `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools` が通る（`check-layout.sh` が環境の要因で失敗するときは、その原因を示して報告する）

## 除外範囲

- runner の設定の読み方（`resolve_config_path`・`_merge`・`load_config`）は変えない
- `.devcontainer/herdr.toml` の「無いときだけ写す」同じ形の処理（README の Herdr の節）は、この Issue の対象外
- 雛形の冒頭のコメントのうち #150・#151 などの経緯の行、README・`AGENTS.md` に残る「#150・#151 で adapter が入るまでは」の記述は直さない（この Issue の対象外）
- 利用者のホームにある既存の個人設定は書き換えない

## 決定記録

### D-167-1 個人設定の作り方

- 選択した案: (a) `schema_version = 1` と上書きの例のコメントだけの最小のファイルを置く
- 検討した別案: (b) 個人設定を作らない（`place_agent_runner_config` を外す）。(c) 丸写しのまま、雛形を変えたら個人設定を消すか rebuild する手順を文書に書く
- 選択理由: (a) は上書きの置き場所と書き方を示しつつ、雛形の更新を妨げない。(b) は雛形の更新を妨げないが、上書きの置き場所と書き方を利用者が文書から探す必要がある。(c) は雛形が変わるたびに利用者の操作が要り、古いモデル名で起動する問題が残る。Issue の推奨も (a)
- 委任指示: issue-to-pr の委任により推奨案を選んだ

### D-167-2 最小の個人設定の置き場所

- 選択した案: 追跡するファイル `.devcontainer/agent-runner-personal.toml` を足し、postCreate はそれを写す
- 検討した別案: `install_beforehand.bash` の関数の中にヒアドキュメントで書く
- 選択理由: TOML のファイルとして検査で `load_config` に渡せ、コメントを TOML の中で保守できる。関数は写す元を変えるだけで、今の検査（保存先・既存の設定・壊れた symlink・書けない保存先）をそのまま使える。名前は `.devcontainer/` の他のファイル（`herdr-agent-task.bash`・`pi-models.json`）に合わせてハイフンでつなぐ
- 委任指示: issue-to-pr の委任による判断

### D-167-3 `schema_version = 1` を有効な行にする

- 選択した案: 有効な行として `schema_version = 1` を書く
- 検討した別案: 有効な行を持たない、コメントだけのファイルにする
- 選択理由: Issue の (a) が指定している。利用者が後で足す上書きがどの版の形を前提にしているかを示し、runner の schema が上がったときに `schema_version` の分類で止まる（古い形の上書きを黙って新しい意味で読まない）。schema の更新は個人設定の移行を伴う変更なので、そこで止まるのは意図どおり
- 委任指示: issue-to-pr の委任による判断

### D-167-4 上書きの例

- 選択した案: 役割の期限・workflow の担当と fallback・`after_run = []` の例をコメントで書き、agent 名は仮の名前にする
- 検討した別案: 実在する agent 名（`claude-opus` など）を使う。例を書かない
- 選択理由: 仮の名前なら、雛形の agent の追加・改名で例が古くならない。例が無いと、上書きの書き方（table の統合・配列の置換）を文書から探す必要がある
- 委任指示: issue-to-pr の委任による判断

### D-167-5 既存の写しの扱い

- 選択した案: 自動では移行しない。README に、#167 より前の個人設定は丸写しであり、自分の上書きが無ければ消してよい（rebuild でも置き換わる）と書く
- 検討した別案: postCreate で、既存の個人設定が雛形と同じ内容なら最小のファイルに置き換える。移行用のスクリプトを足す
- 選択理由: postCreate は rebuild の直後に動き、`~/.config/agent-runner` は mount していないので、そのとき個人設定は通常は無い。移行の処理が働く場面が無く、既存の設定を書き換えない今の規則も崩す。写しが残るのは rebuild していない今のコンテナだけで、rebuild で解消する
- 委任指示: issue-to-pr の委任による判断。今のコンテナの個人設定を書き換えるかは利用者が決める

### D-167-6 検証の方法

- 選択した案: `test-install-beforehand.bash` で、postCreate の関数が置いたファイルと、雛形の各役割の `deadline_seconds` を 1 増やし各 agent の `model` に接尾辞を付けた雛形（T'）を `load_config` で読み、受け入れ条件 2 を確かめる。T' は雛形の行を正規表現で書き換えて作り、値をテストに写さない
- 検討した別案: pytest だけで `.devcontainer/agent-runner-personal.toml` を直接読む。特定の値（`5400` など）を置き換える
- 選択理由: Issue の検証の指定どおり、postCreate が置いた個人設定を使う。特定の値を置き換えると、運用で変わる値をテストに写すことになる（`AGENTS.md` のテストの採用基準 3）。`check` の出力には期限やモデルの値が出ないので、`load_config` の結果を比べる
- 委任指示: issue-to-pr の委任による判断

### D-167-7 `test_cli.py` の既存の検査

- 選択した案: `test_shipped_template_passes_check` の `template-copy` を、postCreate が置く `.devcontainer/agent-runner-personal.toml` に替える
- 検討した別案: そのまま残す。消す
- 選択理由: この検査のコメントは「postCreate が雛形を写す」ことを前提にしている。postCreate が置くファイルが変わるので、雛形と一緒に `check` が通ることを、実際に置くファイルで確かめる
- 委任指示: issue-to-pr の委任による判断

### D-167-8 実装の担当と実行方式

- 選択した案: 担当は `self`（`implement_task.py check` の結果。雛形の既定の適用であり、利用者の指定ではない）。実行方式は `superpowers:executing-plans`（inline）
- 検討した別案: `superpowers:subagent-driven-development`
- 選択理由: Task は少なく、検査と実装・文書が同じ数ファイルに集まり、順に変える方が文脈を渡しやすい
- 委任指示: issue-to-pr の 4 章の 4 の表に従った
