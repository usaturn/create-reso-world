# 登録済み外部ツールの共通運用

通常ツールの対象は `external-tools.toml`、対象の解決・取得は `tools/external_tools/` で管理する。
個別の取得スクリプトや、スキルごとのツール名一覧は追加しない。既存 parent / ResoLoop fork / Meshy の特殊経路は
`AGENTS.md` の「リポジトリ境界」と各手順書を維持する。

**登録は対象の定義だけである。** repo 作成・clone・実装・push・PR・マージ・release・実機操作は、利用者の指示と
各ワークフローで別に許可を確認する。共通基盤は Dev Container、Python 3.14 以上、uv、Git を前提にする。
Spec・Plan は外部 repo へ移さず、create-reso-world の `docs/superpowers/` にコミットする。

## 台帳候補の検証と採用

台帳は `schema_version = 1` と `tools.<key>`、各ツールは次の 4 項目だけを持つ。以下は Emission Editor の登録例であり、
実際の repo 作成・公開・実機準備の完了を示さない。

```toml
schema_version = 1

[tools.emission-editor]
repository = "usaturn/resonite-emission-editor"
path = "external/emission-editor"
base_branch = "main"
ci = "disabled"
```

- key は小文字の英数字と内部の `-`、repository は GitHub の owner/repo。path は常設親の `external/` 以下の相対パス。
- absolute / `..` / 重複・親子重複 / 既存特殊 repo との衝突 / 祖先 symlink による範囲外を拒否する。
- base は展開しない literal heads ref。`git check-ref-format` で検証し、`main` を決め打ちしない。
- CI は `required` または `disabled`。通常 profile は一律 `managed-tool-v1`、マージは手動。

候補は文書用 worktree の branch で編集・レビューする。`parse_registry(data, parent_root=..., commit=...)` による候補の
検証は読取専用で、操作権限を与えない。CLI に任意の候補台帳を渡して操作する入口は無い。

運用に使うのは、identity を検証した **常設親の detached HEAD の blob** だけ。その HEAD はローカル `origin/main` の祖先で
なければならない。親の未コミット変更、feature branch/worktree、外部 repo の候補を採用済みとして扱わない。
読み取り時に fetch は行わない。

採用するには、別途許可された親 PR のレビュー・マージと、親 checkout の安全な更新が必要である。
通常ツールの cleanup から親を更新しない。親への採用前は CLI が `registry_missing`（または未採用の理由）で停止するのが正常。
台帳の無い旧親では既存特殊経路だけを保持し、壊れた・読めない台帳は「登録なし」として握り潰さない。

## 読取確認と取得

共通機構を含む create-reso-world の source checkout で実行する。既定の親はその Git common-dir から決める。
外部 repo や近くの clone を探索しない。`--parent-root` を指定する場合も、検証可能な常設親の絶対パスだけを渡す。

```bash
uv run --no-project python -m tools.external_tools list
uv run --no-project python -m tools.external_tools show emission-editor
uv run --no-project python -m tools.external_tools check emission-editor
```

list/show は採用済み登録、check はローカルの checkout / common-dir / remote / 実送信先の一致を JSON で返す。
check が `ready` のときだけ成功終了する。**通信はしないため、GitHub の存在・権限・CI 設定を確認済みとは表示しない。**
未登録・checkout 不在・remote 不一致・候補複数では停止し、親 checkout や別 clone へ fallback しない。
資格情報付き URL、曖昧な remote、Git の URL 書き換えによる別送信先も拒否する。

clone の明示許可を得てから、同じ source checkout で共通 CLI を使う。

```bash
uv run --no-project python -m tools.external_tools clone emission-editor
```

取得するのは指定 key の repo/base だけ。排他ロック、一意な staging、検証後の Linux 非置換 rename を使い、
常設 checkout を detached にする。setup・submodule 初期化・release・実機操作やローカル main の作成は行わない。
既存物は上書き・削除せず、既存 checkout の dirty / ignored 残骸でも停止する。排他や非置換 rename が未対応なら、
破壊的な代替手段を使わず停止する。成功終了は `cloned` / 検証済み `present` だけ。

失敗時は JSON の `status`・`reason_code`・`registry_commit` と、残った `staging` の完全パスを報告する。
staging は自動削除・再利用・正式配置しない。既存のロックファイルの存在だけで実行中とは判断せず、ロックを手で消して迂回しない。
所有する処理の停止と、未保存物・正式配置先との対応を確認し、利用者の指示を得るまで保持する。
cleanup に登録済みという理由だけで staging の削除を許可しない。

## repo 自身の規約で実装・検証する

clone/check の成功後も、その repo の `AGENTS.md` と `README.md` を読む。編集範囲、テスト・lint・ビルドのコマンド、
必要な環境と実行許可は repo 側で定義する。共通 CLI に任意 setup コマンドを登録しない。
Emission Editor の Python 下限も `requires-python = ">=3.14"` とする。

操作ごとに同じ resolver の検証を受ける。

| operation | 許可する root |
| --- | --- |
| `review-workspace` / `cleanup` | 登録済み常設 checkout |
| `implement` / `review-fix` | 同じ common-dir の、名前付き branch を持つ明示 linked worktree |
| `base-read` | 同じ common-dir の常設 checkout または linked worktree の root |

同じ origin URL の別 clone は同じ repository の作業場所とみなさない。レビューは既存 helper の
`review-workspace` 経路、修正は linked worktree の `review-fix` 経路を使う。
レビュー保存先は全 repo 共通の `PARENT_ROOT/reviews/<owner>/<repo>/#<PR>-<branch>/` のまま。
`target_root` と保存先を混同しない。未登録 repo の明示 `CODE_ROOT` による PR レビュー・承認済み review-fix は維持するが、
未登録 repo の新規実装には広げない。

## CI の実設定照合と手動マージ

controller は登録値と GitHub の実状態を、許可された読取で照合する。

- `ci=disabled`: `gh api "repos/$PR_REPO/actions/permissions"` の `enabled` が **実際に false** であることを確認する。
  ローカル check の `ready` や台帳の値だけで CI を免除しない。
- `ci=required`: `gh pr checks "$PR_NUMBER" --repo "$PR_REPO"` 等で実際の PR checks を読み、必要な checks の成功を確認する。
  checks 不在・失敗・実行中・取得失敗を成功にしない。
- 不一致なら停止して報告する。登録があるだけで Actions の設定を自動変更しない。未知 repo に親の CI 免除を流用しない。

通常ツールでは自動マージしない。`issue-to-pr --merge` は対象外。明示した PR 修正ループでレビュー・修正を行っても、
`review-fix-planning` / `finalize.py` の既存マージ許可範囲は広がらず、通常ツールは手動マージ待ちとして停止する。
修正不要・CI 成功・登録成功はマージ許可ではない。必要な検証結果と PR/head/base を示して、利用者が手動でマージする。
push は `AGENTS.md` の秘密情報検査と、PR の head remote / branch の再照合を経る。

マージ後の片付けは `repo-cleanup-after-merge` の共通 resolver と既存の所有・PR 終了・取り込み・clean・ignored ファイルの
条件をすべて満たすものだけに限る。通常ツールから親の更新や fork sync を呼ばず、親の worktree・同 origin の別 clone・
未マージ branch/worktree は残す。

## 新しい通常ツールを追加する

1. 作成・取得・実装などの依頼と許可を確認する。既存 checkout の探索や無断作成をしない。
2. 文書用 branch で台帳に 1 entry を足し、配置・base・CI 方針を検証する。
3. 対象 repo の `AGENTS.md` / `README.md` に編集範囲・検証・実行条件を書く。
4. 親への採用後、共通 CLI と各 workflow を使う。通常の追加ではスキル・共通コードへツール名一覧や専用取得手順を足さない。
5. GitHub 作成・公開・CI 実設定・実機準備について、確認したことと未確認のことを分けて報告する。
