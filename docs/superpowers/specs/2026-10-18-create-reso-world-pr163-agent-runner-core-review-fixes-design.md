# PR #163（Issue #149 agent_runner の土台）のレビュー指摘の選別

## 管理・実行許可

- 対象: `usaturn/create-reso-world` PR #163（`feat/issue-149-agent-runner-core`、`Closes #149`）
- 状態: `completed`
- 実行許可: 利用者の `/review-fix-planning #163`。計画で止める指示が無いので完遂の流れで進めた。この PR の承認済み実装修正と、結論 2 のマージ・関連 Issue の更新の実行許可として扱う。内容の承認（`approved`）ではない
- 入力: `reviews/usaturn/create-reso-world/#163-feat-issue-149-agent-runner-core/` の `gpt-6.1-sol.md`（Low 1 件）と `SWE-2-Max.md`（Info 1 件）。対象 HEAD はどちらも `8c35447d5974`
- 現行 HEAD: `8c35447d59749a17ea7bec08f5e5c3c8a8afd807`（レビューの対象 HEAD と同じ）。base は `origin/main` の `3e3c1a3`（PR の分岐点から進んでいない）
- 作業場所: 既存の worktree `/workspaces/reso-world/.worktrees/issue-149-agent-runner-core`（head ブランチを checkout 済み、未コミットの変更なし、HEAD が PR の head と一致したので再利用した）
- 以前のレビュー修正: なし（同じテーマの review-fix Spec も、PR の履歴のレビュー修正のコミットも無い）。「同じ条件の再発と設計の見直し」のきっかけ 1・2 には当たらない

## 結論

**結論 2: 修正不要としてマージする。** レビューの 2 件はどちらも現行 HEAD で事実として確かめたが、致命的ではない。確認中に自分で見つけた 3 件（S-1〜S-3）も、実在の構成では致命的な結果に到達しない。

| 区分 | 件数 |
| --- | --- |
| 解消済み | 0 |
| 対応する | 0 |
| 対応しない | 5（レビュー 2、自己確認 3） |

## 指摘の振り分け

| ID | 出どころ | 内容 | 区分 | 根拠（1 行） |
| --- | --- | --- | --- | --- |
| L-1 | gpt-6.1-sol | Spec の「公開する仕様」が挙げる `validate_config` を `tools.agent_runner` から import できない | 対応しない | import は即座に `ImportError` で止まり誤った結果を出さない。移植元も同じく公開せず、後続で移植する利用側はすべて `tools.agent_runner.config` から import する |
| I-1 | SWE-2-Max | 名前が秘密扱いで値の短い環境変数があると、ログ・payload の無関係な部分まで `[REDACTED]` になる | 対応しない | 発生条件が実在の構成に無く、この PR では adapter が無いので redact の経路に到達しない。過剰側に倒れる移植元の設計で、秘密は露出しない |
| S-1 | 自己確認 | テストの fixture の git（`test_cli.py:55-77`・`test_runner.py:164-177`・`test_review_regressions.py:25-34`・`test_workspace.py:27-44`）が `GIT_*` を除かずに環境を引き継ぐ。`GIT_DIR` などが export された状態で pytest を実行すると、実リポジトリの設定・index・ブランチを書き換え得る | 対応しない | 実環境の `GIT_*` は `GIT_EDITOR` だけで、git hook（`core.hooksPath` 未設定、`.git/hooks` は sample だけ）・alias も無く、リポジトリのスクリプトも `GIT_DIR` を設定して pytest を呼ばない。runner の担当の環境は `GIT_*` を除く（`runner.py:421`）。移植元のまま |
| S-2 | 自己確認 | `test_environ.py:43-50` は失敗したときに限り、pytest の差分表示で実環境の環境変数の値を出す | 対応しない | `/proc/self/environ` と、それを読んで作る `literal_environ()` の比較で、`_literal` を差し替えるテストは monkeypatch で戻すので失敗する条件が無い（今回と PR の記録の実行で成功） |
| S-3 | 自己確認 | `output_dir` を渡さないテストが `/tmp/create-reso-world-agent-runner-*` を残す | 対応しない | 名前は `mkdtemp` で一意で、既存のファイルを上書き・削除しない。PR の説明の「既知の制限・持ち越し」に記載済み。残る資格情報はテスト用の偽の値だけ（サブエージェントが変数名とパスだけを表示して検索し、実環境の値の一致は 0 件） |

### L-1: `validate_config` のパッケージ直下からの公開

- 現行 HEAD での確認: `tools/agent_runner/__init__.py` の import と `__all__` に `validate_config` が無い（`config.py` には実装がある）。PR の Spec（`docs/superpowers/specs/2026-10-18-create-reso-world-issue149-agent-runner-core-design.md` の「公開する仕様」）は `tools.agent_runner` の公開 API に挙げている
- 移植元との比較: usaturn/agent-workspace `a47b206` の `tools/agent_runner/__init__.py` は PR と 1 行も違わず、`validate_config` を公開していない。移植元の利用側（後続の #153〜#157 が移植する `implement_task.py`・`run_roles.py`・`dispatch.py`）と `runner.py` は、すべて `from tools.agent_runner.config import validate_config` を使う
- 致命的でない理由: Spec のとおり `from tools.agent_runner import validate_config` と書くと、設定を読む前に `ImportError` で止まるだけで、誤った検査結果や状態の変更は起こらない。利用者向けの仕様 `interfaces.rst` は関数名だけを示し、Python API の例（`from tools.agent_runner import load_config, run_workflow`）はどちらも公開済みである
- 扱い: PR の説明の「既知の制限・持ち越し」に、条件（Spec の記述と実装の差）と回避方法（`tools.agent_runner.config` から import する）を書き足す。Spec の記述を直すかどうかは後続（#150 以降で公開 API を使う子）の判断に残す

### I-1: 短い秘密値による過剰な redact

- 現行 HEAD での確認: `environ.secret_values` は名前に `SECRET|TOKEN|CREDENTIAL|PASSWORD|API_KEY` を含む環境変数の値を長さを問わず集め、`runner.py:336` が runner 自身の環境全体から集めた値で、ストリーミングの redact（`process._Redactor`）、retained の receipt・`export.json`（`redact_file`）、payload・identity（`runner._scrub`）を置き換える。短い値なら無関係な部分文字列も置き換わる
- 発生条件の確認: この Dev Container の実環境で名前が該当する環境変数は 10 個で、値はすべて 32 文字以上（値は表示せず、名前・長さ・数字だけかを確かめた）。リポジトリの設定（`.claude/settings.json` の `env`、`~/.claude/settings.json`、`~/.codex/config.toml`、`~/.pi/agent/settings.json`）にも、`MAX_THINKING_TOKENS` のような名前が該当する短い値の設定は無い
- 到達性: この PR には adapter が無く、`run` は `unsupported`（雛形に workflow が無いので `invalid_reference`）で返る。redact の経路は偽の adapter のテストからしか通らない
- 致命的でない理由: 起きても過剰側に倒れる（秘密の露出ではない）。設計は移植元のまま（`environ.py`・`process.py`・`runner.py` は移植元と同一）
- 論点（設計の是非）: 最小長の下限を設けるか、`interfaces.rst` の redact の節に短い値の挙動を書くかは、adapter を入れる #150・#151 で実際の CLI の環境を見て決める。PR の説明の保証（「ログの redact」）とは食い違わないので、既知の制限には書き足さない

## 確認の範囲

- 全指摘 2 件を、現行 HEAD のコミット済みの内容で確かめた（L-1 は `__init__.py`・Spec・移植元の比較、I-1 は 3 か所のコードと実環境の環境変数・設定）
- 変更ファイル 40 件:
  - 移植したコード・テスト（`tools/`）は、移植元 `a47b206` とファイルごとに比べた。違いは Spec の C-3（grok-build を外す）・C-4（出力先の接頭辞）・C-7（submodule の監査の検査をテストの中で作る）・C-9（`test_shipped_template_passes_check` のパラメータ化）・C-13（コメントの Issue 番号）・`interfaces.rst` の移植先への書き換え・`tools/test_support` の縮小だけで、いずれも安全
  - ランナー本体（`runner.py`・`process.py`・`_supervisor.py`・`workspace.py`・`config.py`・`cli.py`・`hooks.py`・`receipts.py`・`environ.py`・`models.py`・`adapters/__init__.py`・`adapters/skills.py`・`__init__.py`・`__main__.py`）と `interfaces.rst` の全文を読んだ
  - テスト（`tools/agent_runner/tests/` の全ファイル、`tools/test_support/`）の全文はサブエージェントが行単位で読み、一時領域の外への書き込み、本物の CLI の起動、秘密情報の出力、残るプロセス、機能していない検査を探した。通常の実行で致命的なものは無く、条件付きの S-1〜S-3 を挙げた（上の表）。起動するのは `sys.executable`・`/usr/bin/env`・`/bin/sh`・`touch`・`git` だけで、ネットワークを使わない。入れ子の拒否・未対応の runtime の拒否・redact・停止の確認の検査は、どれも対象そのものを見ている
  - 移植ではない変更（`.devcontainer/install_beforehand.bash`・`test-install-beforehand.bash`・`agent-runner.toml`、`pyproject.toml`・`uv.lock`、`AGENTS.md`・`README.md`・`.devcontainer/README.md`・`.agents/monitoring-runtimes.md`・`monitoring-long-tasks/SKILL.md`、PR の Spec・Plan）の差分を読んだ。`place_agent_runner_config` はワークスペースのルートを cwd にして呼ばれ、既存の設定（壊れた symlink を含む）を上書きせず、保存先の決め方が `resolve_config_path` と一致する。`requires-python >=3.14` はシステムの Python 3.14.4 と合う
- 守る条件と影響経路の表: 「対応する」項目が無いので作らない

## 検証

専用の worktree（HEAD `8c35447`）で順に実行した。base は分岐点から進んでいないので、base を merge したツリーでの再検証は不要。

| コマンド | 結果 |
| --- | --- |
| `uv run pytest tests/skills .agents/skills .agents/scripts tools`（README の「テスト」。`pyproject.toml` の pytest の設定の変更が全ての入口に効くため） | 終了コード 0、1414 passed（383 秒） |
| `bash .devcontainer/run-tests.bash`（環境の変更） | 終了コード 0、PASS 32 本（327 秒） |
| `bash scripts/check-layout.sh` | 終了コード 0、PASS |
| `env AGENT_RUNNER_DEPTH=1 uv run pytest tools/agent_runner`（runner の担当の中からの実行。PR の受け入れ 3） | 終了コード 0、339 passed（56 秒） |
| `uv run --locked python -m tools.agent_runner check`・`list` | 終了コード 0。6 runtime すべて `supported: false`、agents・workflows は空、roles は 4 つ |
| 実行後の `git status --porcelain` と HEAD | 空、`8c35447` のまま |

- CI: `usaturn/create-reso-world` は private で CI を止めているので確認しない（`AGENTS.md` の「GitHub Actions」）

## 自己レビュー

未実施（結論 2。修正が無いので、修正後の自己レビューは行わない）
