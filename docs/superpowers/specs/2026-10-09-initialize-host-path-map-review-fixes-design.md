# PR #65 initialize.bash が RESOLOOP_HOST_PATH_MAP を渡す: レビュー指摘の選別

- 文書管理: `usaturn/create-reso-world`
- 対象 PR: https://github.com/usaturn/create-reso-world/pull/65（`feat/initialize-host-path-map`）
- 状態: completed
- 対象 HEAD: `6139ae7a16af6703f25885848a94776ac6580ec4`（レビュー 2 件とも同じ HEAD）
- 入力: `reviews/#65-feat-initialize-host-path-map/`（`SWE-2-High.md`、`opencode-go-deepseek-v4.1-flash.md`）
- 実行許可: 依頼 `/review-fix-planning <PR URL>` による完遂（修正要否の確定、修正不要ならマージと関連 Issue の更新まで）
- 結論: 2（修正不要としてマージ）。「対応する」は 0 件
- 経路: 完遂のため brainstorming は呼ばない。PR の差分は 3 ファイル +38/−5 で、コードの修正は無い

## 指摘の振り分け

| ID | 指摘 | 区分 | 根拠 |
|---|---|---|---|
| SWE L-1 / DeepSeek 候補 2 | 別名 symlink 経由でフォルダを開くと FROM がずれる | 対応しない | 発生しても map が効かず従来どおり取り込みが失敗するだけで、データ・設定・秘密情報に害は無い。Dev Containers が symlink のどの段階の basename を使うかは両レビューとも未検証で、実在する構成として確認できていない |
| SWE I-1 / DeepSeek L-1 | `/mnt/*` のリポジトリでは map を書かない | 対応しない | 設計判断。PR 本文と README に「書かない」と明記済みで、書かない場合は従来の挙動と同じ。`C:\` への対応付けは別の機能で、本 PR の範囲外 |
| SWE I-2 | `devcontainer.json` の `--env-file` コメントが古い | 対応しない | 説明の追随漏れ。実害なし |
| DeepSeek I-1 | `.gitignore` のコメントが古い | 対応しない | 説明の追随漏れ。実害なし |
| DeepSeek 候補 1 | `initializeCommand` で `WSL_DISTRO_NAME` が見えるか、rebuild 後の自動注入が未観測 | 対応しない | 到達できる欠陥の再現ではなく実機確認の勧め。見えない場合は map が書かれず従来どおりになるだけ。PR 本文が「rebuild 後の自動注入は未確認」と明記している |
| SWE テスト提案 1・2 / DeepSeek テスト提案 1・2 | `/mnt/*` 分岐、symlink と WSL の併用、期待値の別実装 | 対応しない | 致命的な指摘ではなく、テストの追加も対応にあたる。`/mnt` は書き込めずテストできない |

件数: 解消済み 0 / 対応する 0 / 対応しない 6 グループ（上表）。

## 確認

- 全指摘に加え、PR の変更 3 ファイル（`initialize.bash`・`test-initialize-mounts.bash`・`README.md`）の差分を全文読み、`initialize.bash` の呼出元（`devcontainer.json` の `initializeCommand`、`--env-file`）と `test-readme.bash`・`check-layout.sh` の関係を確認した。
- PR が持ち込む致命的な欠陥は見つからなかった。`: >` での切り詰めが先に行われ、写真フォルダの行・map の行はどちらも追記で、`WSL_DISTRO_NAME` が空・未設定でも `${WSL_DISTRO_NAME:-}` で止まらない。
- 検証（専用の worktree、HEAD `6139ae7`）: `test-initialize-mounts.bash`、`test-readme.bash`、`bash .devcontainer/run-tests.bash`（28 件 PASS）、`bash scripts/check-layout.sh` がすべて成功。
- base（`origin/main` = `427be4d`）は PR の分岐点から進んでいない。
- CI: プライベートの create-reso-world は CI を使わない（`AGENTS.md`）。check は報告されない。

## 守る条件と影響経路

「対応する」が 0 件のため作らない。

## 既知の制限（PR 本文に追記する）

実在する制約のうち、PR 本文に無いものを書く。`/mnt/*` は本文に「書かない」とあるため、symlink 経由の件だけ追記する。

- 別名の symlink 経由でフォルダを開いた場合は、FROM が実体のフォルダ名になり、コンテナの `/workspaces/<開いたフォルダ名>` と一致しない可能性がある（未検証）。その場合は従来どおり取り込みが失敗する。

## 自己レビュー

修正が無いため行わない。
