# PR #8 レビュー指摘の再選別（第7回）

- 状態: 計画のみ。実装・commit・push はユーザーの明示承認待ち。
- 対象: `usaturn/create-reso-world` PR #8（`docs/list-shrink-recreate-split`）。現行のコミット済み HEAD: `3c44ef3e282a906f83b7ad798e120ca85c53fccf`。
- 経路: **bounded**。既存の文書 PR に対する指摘の再判定で、新機能・設計変更・実装変更は提案しない。review-fix-planning の規則により、この経路でも Spec を保存する。
- 意図と成功条件: 指定されたレビュー9ファイルの全指摘を現在の PR head に照らし、古い指摘を再実装しない。ユーザーの承認を受けるまでは PR の実装・反映を行わない。

## 1. 入力と検証範囲

入力は `reviews/#8-docs-list-shrink-recreate-split/` 直下の次の9ファイルのみ。冒頭の対象 HEAD は以下の通り。履歴に現れるさらに古い HEAD は各レビュー本文の検出時 HEAD に従う。

| レビューファイル | 冒頭の対象 HEAD |
| --- | --- |
| `SWE-2-Max.md` | `3c44ef3e282a` |
| `claude-sonnet-5-5.md` | `3c44ef3e282a` |
| `commandcode-deepseek-deepseek-v4.1-flash.md` | `cca3a9016d21` |
| `deepseek-deepseek-v4.1-flash.md` | `3c44ef3e282a` |
| `gpt-6-sol.md` | `c6749fc01605` |
| `grok-4.7.md` | `913a0f805917` |
| `opencode-go-muse-spark-1.3-contributor.md` | `3c44ef3e282a` |
| `qwen3.8-max.md` | `3c44ef3e282a` |
| `xai-grok-4.7.md` | `3c44ef3e282a` |

`gh pr view` と `git fetch origin docs/list-shrink-recreate-split` で同一 HEAD と open な PR を確認した。検証対象文書は `git show 3c44ef3e:<path>` のコミット済み blob と PR 本文で照合し、他の作業ツリーの未コミット source/test は根拠にしない。旧 HEAD の挙動指摘については `mktemp` 以下の detached worktree を `c6749fc01605` で作成し SHA を照合してから旧・現行の記述を比較した。検証後に `git worktree remove --force` と親ディレクトリ削除を済ませている。PR は文書のみなので計画コードの実行・実機確認はここでは行わない。

以下の ID は**ファイル名 + そのファイル内の ID**で識別する。同じ ID が別モデルにも現れるため、ファイルを省略して同一指摘として扱わない。分類は解消済み31件、対応する0件、判断保留0件、対応しない5件（合計36件）。

## 2. 全指摘の分類

| 入力 | ID | 分類 | 現行 HEAD での根拠・判断 |
| --- | --- | --- | --- |
| SWE-2-Max | F-02 | 対応しない | PLAN:2152-2153 の `"fields"` は残るが、既存の上流の進捗報告と合わせる設計判断が DESIGN:186 に記録済み。段階名の是非は仕様判断であり誤動作の再現ではない。 |
| SWE-2-Max | I-3 | 対応しない | DESIGN:480 の D-30 補足は短縮表現だが、直前に同型の別 key の規則があり、DESIGN:247-249 と PLAN:3234-3244 では `sameTypeKeys` を優先する。事実誤認は確認できない。 |
| SWE-2-Max | F-01 | 解消済み | PLAN:418・3117 で nullable 参照に `!` を追加済み。 |
| SWE-2-Max | I-1 | 解消済み | DESIGN:480 の D-30 に複数候補への参照がある場合の補足を追記済み。 |
| SWE-2-Max | I-2 | 解消済み | PLAN:22 に SDK pin の cwd 差異の注記を追加済み。 |
| SWE-2-Max | I-4 | 解消済み | PR 本文のファイル節は現在の PR 差分の9ファイルを列挙し、承認状況にも第5・6回を記載済み。 |
| SWE-2-Max | I-5 | 解消済み | 第5回記録:140-142 は実施済みの `[x]` に更新済み。 |
| claude-sonnet-5-5 | M-1 | 解消済み | PLAN:1992-1993 の `ApplyRubbleAsync` は changed 3件・initial 4件の順になっている。 |
| claude-sonnet-5-5 | I-1 | 解消済み | PR 本文の検証節が初期再生と、その後の B3/B4 の変更・限定した検証を分けて説明する。 |
| commandcode-deepseek-deepseek-v4.1-flash | I-2 | 解消済み | PR 本文のファイル節に第5・6回の記録があり、差分9ファイルと一致する。 |
| commandcode-deepseek-deepseek-v4.1-flash | I-3 | 解消済み | 第5回記録:140-142 の実施項目が `[x]` に更新済み。 |
| commandcode-deepseek-deepseek-v4.1-flash | H-1 | 解消済み | PLAN:1992-1993 の縮小テストで `ApplyRubbleAsync` の引数順を修正済み。 |
| commandcode-deepseek-deepseek-v4.1-flash | H-2 | 解消済み | PLAN:3006 の `ResetWriteCounts()` が `LoseResponseOnWrite = 3` の直前にある。 |
| commandcode-deepseek-deepseek-v4.1-flash | I-1 | 解消済み | 第2回記録:95 は文書変更を「12操作」に修正済み。 |
| deepseek-deepseek-v4.1-flash | I-2 | 対応しない | 第5・6回記録:40・43 の「同じ基準」は隔離環境の要否の判断を指す。第4回:43 は任意に隔離 worktree を使用した記録であり、「第4回は作らなかった」とは書いていない。修正しても相互参照の読みやすさの改善に限られる。 |
| deepseek-deepseek-v4.1-flash | L-1 | 解消済み | PR 本文の検証済み件数と実装時の予定件数が別に記載され、現行 PLAN 冒頭の値と整合する。 |
| deepseek-deepseek-v4.1-flash | I-1 | 解消済み | DESIGN:3 は決定事項の範囲を `D-27〜D-33` と記す。 |
| gpt-6-sol | H-1 | 解消済み | PLAN:4215 の strict validate と同:4224-4225 の inspect・slot delete に、選択した接続先を渡す指示がある。 |
| gpt-6-sol | M-1 | 解消済み | DESIGN:247 の両候補が参照される分岐と PLAN:3234-3244 の `multipleReferencedCandidates` 分岐は、候補を削除せず参照の確認・張り替えを案内する。 |
| grok-4.7 | H-1 | 解消済み | PLAN:1992-1993 は changed 3件・initial 4件になり縮小テストの前提と一致する。 |
| opencode-go-muse-spark-1.3-contributor | L-1 | 解消済み | PLAN:22 の SDK 10.0.401 の記録に `global.json` 10.0.201 の適用範囲を注記済み。 |
| opencode-go-muse-spark-1.3-contributor | I-1 | 解消済み | PR 本文に第5・6回のファイルと承認状況を追記済み。 |
| qwen3.8-max | I-5 | 対応しない | DESIGN 8章はテストの網羅表ではなく、挙動は 7.3・7.5・7.7 に記述済み。テスト名3件の列挙漏れは事実誤認ではなく Info 級の追記提案。 |
| qwen3.8-max | I-8 | 対応しない | 第2回:22 と第3回:21 は `FIRST` を別ファイルに割り当てるが、各文書内に定義があり参照先を一意に解決できる。文書間で略記のスコープを統一する設計変更は不要。 |
| qwen3.8-max | L-1 | 解消済み | PR 本文で検証実績と予定値を分け、DESIGN:3 も D-33 まで更新済み。 |
| qwen3.8-max | L-2 | 解消済み | 旧指摘の `--changes-only` が `recreate` を落とす懸念は、既存の `Action != "no-op"` の扱いと矛盾する。現行文書の挙動を否定する事実は無い。追加テストは保険であり不要。 |
| qwen3.8-max | I-1 | 解消済み | DESIGN:3 は `D-27〜D-33` に修正済み。 |
| qwen3.8-max | I-2 | 解消済み | DESIGN 中のメソッド名が `SaveSlotIndexesAsync` に統一済み。 |
| qwen3.8-max | I-3 | 解消済み | 第1回修正記録:132 に 392 件と 394 件の母数は後から再導出できない旨の注記が追加済み。 |
| qwen3.8-max | I-4 | 解消済み | 第2回記録:96・183 に SDK pin の注記・参照が追加済み。 |
| qwen3.8-max | I-6 | 解消済み | PLAN:22 に `global.json` pin の適用範囲の注記が追加済み。 |
| qwen3.8-max | I-7 | 解消済み | PR 本文のファイル節・承認状況に第3・4回以降も反映済み。 |
| qwen3.8-max | I-9 | 解消済み | PR 本文のファイル節は第5・6回を含めた9件で、PR 差分と一致。 |
| xai-grok-4.7 | M-1 | 解消済み | PLAN の `VerifyReplacementsAsync` 分岐で置き換え元消失後も state を処理するよう修正し、PLAN:2995 の回帰テストを追加済み。 |
| xai-grok-4.7 | L-1 | 解消済み | PLAN の `ReferencesComponentKeys` で自己参照を除外し、PLAN:1985 の回帰テストを追加済み。 |
| xai-grok-4.7 | I-1 | 解消済み | DESIGN:3 が `D-27〜D-33` に更新済み。 |

## 3. 修正方針と承認ゲート

- **対応する0件**: (a) 現行 HEAD の誤動作、(b) 事実と異なる記述、(c) 理由なく削除された回帰ガード、(d) ユーザーによる名指し指定のいずれも該当しない。したがって変更・追加テスト・対応項目ごとの検証方法はない。
- **判断保留0件**: 残りは簡単な語句修正で潜在バグを消す類ではなく、記載の詳細度や既存の設計判断の話である。
- **対応しない5件**: DESIGN 8章を網羅表とみなすか、他の記録と略記・相互参照を統一するか、進捗段階名を変えるかという論点は、現行の仕様を変える証拠が無いため今回の修正範囲から除外する。
- 既存 PR の実装・commit・push は行わない。ユーザーが個別 ID の修正を明示的に希望した場合は、その指定に基づき別途方針と検証手順を確定する。承認があっても今回の0件という選別を黙って拡張しない。
