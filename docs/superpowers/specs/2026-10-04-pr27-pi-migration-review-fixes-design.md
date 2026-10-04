# PR #27 pi 移行レビューの対応方針

対象は `usaturn/create-reso-world` PR #27、`feat/issue-19-pi-migration`。検証した HEAD は `6f0cd9ee9d04da2f177c0ab97551945583b78d49`、base は `origin/main` の `c40a3bdc86c2b7349ec3b7859d5b06af5d81e6e5`。

ユーザは妥当な指摘を推奨案で修正し、プッシュまで実施すること、worktree・サブエージェントを使って PR 全体と差分外の関連箇所も調査することを指示した。通常の設計承認待ちは挟まず、この指示に従って進める。`pr-review` は使用しない。修正があるため今回はマージせず、既存 PR の head へ反映する。

## 入力と分類

入力は `reviews/#27-feat-issue-19-pi-migration/` の次の3ファイル。全件の対象 HEAD は上記と一致する。

- `claude-opus-5-5.md`
- `commandcode-deepseek-deepseek-v4.1-flash.md`
- `gpt-6.1-sol.md`

| ID | 分類 | 根拠と対応 |
| --- | --- | --- |
| Claude L-1 | 対応する (b)、文言のみ | `cleanup_pi_mcp.py:111` が disable entry の由来を adapter と断定するが、実装は完全一致値しか判別しない。docstring を値の説明にし、README に利用者が設定した値も成功する cleanup ごとに除去することと共有 agent directory への影響を明記する。無条件除去自体は Issue #19 の受け入れ条件と元 Spec の移行手順6に合うため、レビューの挙動変更案 (a)/(b) は採用しない。 |
| Claude I-1 | 対応する (b) | README:433 の新しいシェルだけで反映される説明は、既存 `~/.zshrc` が postCreate の連結コピーであることと合わない。rebuild と手動反映を区別し、後者では4つの旧 export の削除と利用中シェルでの unset を案内する。 |
| DeepSeek I-1 | 対応しない | pi-model-name の旧変数は主モデル判定に使わないという否定例であり、新規環境での設定・廃止拡張の導入を要求していない。Issue #19 と元 Spec はこの記述の保持を明記している。 |
| GPT I-1 | 対応する (b) | README:474–475 の OpenCode Go にも Distillation 用 `DEEPINFRA_TOKEN` が必要という説明は廃止済みの導入経路と矛盾する。この2行だけ削除し、通常の deepinfra 利用時の要件は保持する。 |

分類は解消済み0 / 対応する3 / 判断保留0 / 対応しない1。

追加調査ではルート `README.md:26` が ResoLoop を常に fork ビルドすると説明していた。現 lock と同文書の版管理節は nuget モードなので、事実誤認として修正する（追加 D-1、(b)）。ユーザの差分外も修正範囲にする指示を適用し、lock が選ぶ nuget / fork の両経路を正確に説明する。

## 設計と検証

brainstorming の経路は bounded。既存説明とコメントの修正であり、実行処理は変更しない。対象は `.devcontainer/README.md`、`.devcontainer/cleanup_pi_mcp.py` の docstring、ルート `README.md` とこの記録。

- Claude L-1: 旧 npm パッケージがない隔離環境で disable entry を除去し、再実行では設定とバックアップ数が不変になることを確認済み。利用者の再無効化後は次回に除去され、バックアップが増えることも確認した。既存 `test_builtin_disable_filter_preserves_other_settings_and_mode` が独自項目・mode・バックアップの元バイト列・冪等性を固定しているので新しいテストは追加しない。
- Claude I-1: 実 zsh と隔離 `.zshrc` で、新しいシェルでも旧 export が残ること、現テンプレートの追記でも残ることを再現済み。修正文と installer の連結処理を読み合わせる。
- GPT I-1: 修正後の API トークン節と廃止説明、導入一覧、モデル雛形、setup を読み合わせ、廃止した token 要件がないことを確認する。
- D-1: lock、導入スクリプト、ルート README の版管理節と説明を照合する。
- 修正後は `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills`、`git diff --check` を実行する。説明だけの変更なので新しい自動テストは追加しない。
- サブエージェントが修正全文を再点検してから、検証済みの変更を1コミットで既存 PR にプッシュする。

## PR 全体と関連箇所の調査結果

4つの隔離 worktree を固定 HEAD に作り、controller と3担当が16変更ファイルの差分・本体、削除 helper の旧内容、周辺の呼び出し元・安全策・設定・依存・共有リンクを確認した。検証用 worktree と一時 root は全担当の終了後に撤去済み。実装は新しい隔離 worktree で行う。

- cleanup 全49テスト成功（実 npm の offline 回帰を含む）。途中失敗、バックアップ、リンク拒否、保持保証、再実行を確認した。
- 実 pi 1.0.2 のローダーでルートと4ワールド × trust 許可/未許可の10ケース成功。利用者の拡張・他 builtin の無効化・独自設定・個人 MCP・元ファイルのバイト列を保持することを確認した。
- Google キー未設定ではヘッダー解決がネット接続前に失敗する。環境変数を設定して使う説明と一致し、追加修正は不要。実認証の接続と Dev Container rebuild は検証していない。
- 独自第三者拡張が撤去対象 helper に依存すると npm が helper を保持し、cleanup が残留を理由付きで停止する。標準8拡張にはその依存がなく、公式構成では再現しない。保持する実体を削除しない現仕様の停止として対応しない。
- baseline の全体 bash は24/25本成功。`tests/scripts/test-check-layout.bash` と直接の layout 検査だけが、既知の slum03 スキル未同期で失敗した。該当スキルと検査スクリプトは origin/main と同一で、Issue #19 がこの2件を検証の既存失敗として明記している。同期や版変更は行わない。

## 調査時間

controller の開始は約10:50 UTC。入力・境界・worktree準備は約3分、並列調査と全体差分・baseline 検証は約8分。子担当の所要時間は cleanup 8分06秒（精読・suite 2分10秒、再現2分02秒、標準依存の切り分け・報告3分54秒）、設定約6分（精読3分、実ローダー・個別検証2分、報告1分）、文書4分56秒（精読・再現3分06秒、報告・最終確認1分50秒）。並列時間は合算しない。修正・最終検証・公開の実測は PR 最終ステータスコメントに記録する。

## 修正後の確認

2026-10-04 11:07 UTC までに、新しい worktree で全体 bash を完了した。24/25本成功、終了コード1で、失敗は修正前と同じ slum03 未同期の配置検査だけだった。直接の layout も同じ理由で終了コード1。スキルテストは267件成功・1件スキップ、終了コード0。関連する README・指示・モデル設定・cleanup・provisioning の検査は成功した。

文書担当の独立点検でも追加の修正対象はなかった。README に記載した unset 行を実 zsh で確認し、旧 export の除去と組み合わせると子プロセスにも4変数が渡らなくなった。cleanup は docstring を除いた AST が元 HEAD と一致することを確認した。差分と新 Spec の空白検査も成功した。修正は説明とコメントに限られ、実行処理の変更はない。
