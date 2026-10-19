# 親 #116: DSH native write policy の別スコープ計画

- 状態: **draft**。計画の作成許可のみ。設計内容の承認・実装・権限変更・実機再試行は未許可。
- 親: usaturn/create-reso-world#116、ボード `review-automation-board`。
- 提案キー: `dsh-native-write-policy`。新しい子Issueは未作成・未登録。番号・native dependencyは発明しない。
- 基準: `origin/main` = `1335f410e624355cd558029bdcdad65eaa944ed8`。消費側の未マージPR #182 = `0d1cd19477ea00b216c3cc8f9400c3eb9afe4395`。
- 許可の出所: 「親 #116でDSH側の対応を別スコープとして計画する」という提案に対する利用者の「提案どおりにしてください。」。これは拒否操作の再試行や新Issue・実装PRの作成指示ではない。

## 目的と観測事実

#153のpr-reviewに変更範囲外のDSH adapter修正を混ぜず、正式レビュー保存先への限定的な書き込みを、DSHのnative filesystem policyとbubblewrapの両方で扱えるようにするための後続作業を定義する。

既存実機の拒否対象は、親reviewsの`.staging/`内にある自身のMarkdown draftへのnative `write`だった。`sandbox_write_paths`は`tools/agent_runner/adapters/dsh.py:210`から`dsh_sandbox.py:47–53`のbind mountに渡るが、native policyは`dsh.py:232–236`の`workspace-write`と主workspaceだけである。

導入済みDSH `0.2.0-rc.2`の`@deepseek-ai/dsh-sandbox-policy/README.md:147`は、`SessionHeader.cwd`による主workspaceは1つ、追加writable rootsは`SandboxExecutionPolicy`に含まれないと明記している。`workspaceRoot`はsession cwdの上書き手段ではない。CLIの`--grant`やpromptの例外記述だけではnative writeの許可にならない。

根拠は権限/tool-callメタデータ、導入済みpackage、現行adapter、既取得のContext7公式資料。レビュー本文・候補・thinkingは読まない。#174の401/403行番号による診断誤判定は別問題で、この拒否操作の原因と混同しない。

## 選択と代案（エージェントの推奨。未承認）

### P-1: 公式に追加書込先を表現できるDSHを条件にする

**推奨:** DSHがnative filesystem policyに追加書込先を指定できる、検証可能な公式インターフェースを提供した後、adapterの事前許可をそのAPIへ接続する。bubblewrapだけ広げる修正はしない。今の版で実現できると見せかけず、対応APIが確認できるまで実装はblocked/not readyとする。

追加APIの名前・設定キー・対応版は現在未確認である。将来の`extraWritableRoots`や`--add-dir`等を推測して実装しない。上流のclone・改変・PR作成は行わない。公開版の採用候補を調べる作業と、外部リポジトリの実装は別の権限である。

### P-2: 領域/cwdの再設計は今回は採らない

既存隔離TMPDIRを子の成果置き場にして親へ渡す案、session cwdを共通の所有領域へ変更する案は代案として残す。ただしRequest/work_dir照合、停止後の親保存、秘密情報の掃除、Git領域と成果の所有検査を同時に見直す必要がある。現在の拒否を別パスやbash書き込みで通すために実行しない。採るなら別の具体的設計・許可・検証が必要で、本計画の暗黙のfallbackにはしない。

### P-3: 拡大しないもの

full-access、共有`.git`全体、親reviews全体、別HOME/cache/cwd、native writeをbashへ切り替える迂回、GitHub tokenの子への引き渡し、導入済みpackageの直接編集は採らない。

## 作業の境界と担当案

| 作業 | 所有範囲 | 他の作業との関係 |
| --- | --- | --- |
| 公式APIの実現性確認 | 公開資料・導入候補packageの隔離調査、Spec/Planへの証拠追記 | 現在は未充足の外部入力。インストールやモデル起動はしない |
| DSH native policyの接続 | `tools/agent_runner/adapters/dsh.py`の`Dsh.prepare`、対応する実行テスト。必要なら`dsh_sandbox.py`の既存grant検査の共通化とそのテスト | #151の後続候補。#174/PR #180の診断・collect部分は所有しない。着手時にPRの状態と重複を再確認 |
| 版と運用の整合 | `.devcontainer/install_beforehand.bash`のDSH導入段、同テスト、`.devcontainer/README.md`の該当箇所。必要なら`tools/agent_runner/runtimes/dsh.rst`を新設（現状は未存在） | 対応APIの証明後。版だけを写したテストは禁止。RSTを変える実行者はrst-writerを読む |
| pr-reviewの受け入れ再開 | #153の既存PR #182、固定snapshotからのDSH実機1回 | 新しい実行許可後のみ。#153側がhelperの入力と保存検査を所有し、後続タスクは`.agents/skills/pr-review/`を勝手に変更しない |

既存の公開API `Dsh.prepare(context: AdapterContext) -> LaunchSpec`、`AdapterContext.sandbox_write_paths`、Request/Receipt/Result、provider/modelの識別方法を変えない。追加の許可はcontrollerが起動前に確定したcanonicalな対象だけ。nativeとbashの双方で必要な対象へ到達でき、許可していない隣接パスへ到達できないことを実行で証明する。通常ファイルの保存ロックを扱うためだけに、その親`.git`ディレクトリへ許可を広げない。

`tools/workspace`・`projects.toml`は導入しない。#116冒頭の利用者決定（致命的な指摘だけ修正、結論の三択、修正後の自己レビュー最大1回）を維持する。個人設定・認証・他runtime・別の子のファイルは変更しない。

## 依存と実行ゲート

- 既存入力: #151 completed/main取り込み済みのadapterと識別API。#153/PR #182の親snapshot・staged・停止後finalizeの仕様は、マージ済みでなくても固定SHAの読み取り入力として参照できる。#153の完了をnative接続作業の先行にして循環依存を作らない。
- **Gate A（未充足）:** 公式の追加書込先API、対応する公開版/固定ソース、native write/editとbashの意味、必要なファイル単位/ディレクトリ単位の境界を確認する。read-onlyや拒否の挙動を保つ証拠も必要。無ければ停止し、本Spec/Planをblockedのまま保つ。
- **Gate B（未充足）:** 親の調整役が新タスク/既存タスクの正式な所有範囲を決め、内容・実装・必要な版変更を具体的に許可する。新Issue作成やboardのnative関係変更は別途指示があるときだけ。
- **Gate C:** Gate Aの証拠に基づき本Spec/Planを具体化し、再度レビュー・許可を得てから実装する。対応APIが未定のままコード担当を起動しない。
- **Gate D:** fake/offline検証に成功し、別途認められた実機予算・対象・停止条件があるときだけ、現行PR HEADのfresh prepare-parentからpending DSHを1回起動する。成功済みDevin/非runnerは繰り返さない。1回のDSH成功だけで、同一HEADにおける全員の並行受け入れを満たしたと主張しない。

## 受け入れ条件（将来の実装用。今回は未実行）

1. controllerが許可したPR固有保存領域へのnative write/editとbashの書き込みが同じDSH sessionのworkspace-writeで成功する。
2. 兄弟PR、許可対象の兄弟ディレクトリ、symlink経由の範囲外、read-onlyの対象への書き込みは拒否される。file grantが必要なときは親ディレクトリへ広げない。
3. cwd・HOME・cache・DSH permission modeを拒否後に切り替えず、GitHub tokenを渡さず、停止未確認・Identity/Request/digest/HEAD不一致では正式保存しない。
4. 対応していない公式APIや不明な版/APIでは有料起動より前に停止し、追加bindをnative対応済みと報告しない。既存Result形式で失敗/unsupportedを表す責務はGate A後に固定する。
5. fake CLI/native-policy backendで正常系と拒否系を実行し、実機の必要性と未実施を分けて報告する。文面・モデル一覧・可変版の一致だけのテストは作らない。
6. 実機が許可された場合だけ、外側状態、exit、stop_confirmed、payload、保存pair/run記録、cleanup、sensitive_paths/outside_changesを照合する。stagedやafter_run exit0だけを成功にしない。

## Builder checkと調整結果

読み取り専用のsp-reconを1回起動し、仕様から計画できるかとローカルの対象パスを確認した。重要な指摘はruntime手順の`dsh.rst`が未存在という点で、「既存の変更」ではなく必要時の新設と明記した。#174/PR #180の関連は子のローカル入力だけでは検証できなかったため、調整役がGitHubのPRメタデータで確認した（PR #180はOPEN、`fix/issue-174-dsh-tool-diagnostics`、HEAD `f5550936db665490aa7908b4d0f4906be479431c`）。診断修正とnative policy接続は別範囲で、着手時の再確認を必須とする。Gate Aの未確認APIを子が推測して埋めることはしない。

## 今回の成果・公開

計画のみ。文書用worktreeのdraft Spec/Planをローカルcommitし、親 #116のコメントへ4成果物とhashを公開・復元検査する。文書branchのpush/新PR、新Issue、実装テスト、DSH/Devin等の実機起動はしない。Git branch/PRは公開未実施と明記する。#153とPR #182は変更せずopen/blockedのまま維持する。
