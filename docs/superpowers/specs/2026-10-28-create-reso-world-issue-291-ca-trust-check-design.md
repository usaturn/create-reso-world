# Issue #291: eMudhra 中間CA の侵害に対するトラストストアの確認と更新

## 管理・実行許可

- 文書管理: usaturn/create-reso-world
- 対象: usaturn/create-reso-world #291（https://github.com/usaturn/create-reso-world/issues/291）
- 状態: draft（内容の承認は未取得）。「PR #293 のレビュー修正（サイクル 1）」の節は completed（結論 1、修正して push）
- 指示: `/issue-to-pr #291 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge`
- 許可: 通常の設計判断を推奨案で決め、検証・commit・push・PR 作成と、PR 修正ループ（`finalize.py`）によるマージまで行う。実行の許可であり、内容の承認ではない
- 設計時の base: `origin/main` の `4f7e64f5fb9655fed59bff12121474c538cfb109`
- 関連文書: Plan `docs/superpowers/plans/2026-10-28-create-reso-world-issue-291-ca-trust-check.md`

## 意図

2026-10-20 に eMudhra の中間CA 8 件の秘密鍵が侵害された。ブラウザと OS は失効情報で対応済みだが、失効情報を読まないクライアントは、修正版へ更新するまで侵害された中間CA を信頼し続ける。開発コンテナは、システムの CA バンドル（OpenSSL）、Node.js の同梱 CA、uv の同梱 CA（webpki-roots）など、別々のトラストストアで HTTPS を検証している。

着手時のコンテナは侵害された中間CA を信頼していない（Issue の表と「初期観測」）。守りたいのは、rebuild・ツールの更新・古いベースイメージのキャッシュでこの状態が崩れたときに、気付かずに古いまま使い続けることを防ぐことである。

## 目的・非目的

目的:

- rebuild 後とツールの更新後に、コンテナの主なクライアントが侵害された中間CA を信頼していないことを、1 つのコマンドで確かめられるようにする
- 確かめられないとき（ネットワーク障害、確認用ホストの変化）を「安全」と報告しない
- postCreate で `ca-certificates` を、更新した索引の最新版へ上げる。上げられなければ postCreate を失敗させる
- 同梱 CA を持つツールを点検し、結果を Issue に記録する。ホスト側で利用者が行う更新を案内する

非目的（Issue の「対象外」のとおり）: ワールドのプロジェクトの環境、ホストや Electron アプリ自体の更新作業、証明書ピンニング・社内プロキシ・CA バンドルの独自配布、ベースイメージの作り直し、過去に信頼していた証拠の調査。

避けること（動いても失敗とみなす）: 接続の失敗や、信頼の欠如と関係のない検証エラー（期限切れ・名前の不一致）を「信頼していない」と報告すること。外部ホストへの接続を postCreate や `run-tests.bash` に入れること。

## 設計

### 1. `.devcontainer/verify-ca-trust.bash`（新規）

使い方: `bash .devcontainer/verify-ca-trust.bash [HOST[:PORT] ...]`。引数が無ければ、確認サイトがコマンドラインのクライアント向けに挙げる 4 ホスト（`dv-g3b-emudhra`・`dv-g3b-aaa-emudhra`・`dv-g3b-noct-emudhra`・`dv-g3b-aaa-noct-emudhra` の `.we-have-a-problem.com`、ポート 443）を使う。`-h`・`--help` で使い方を表示する。ホスト名とポートの形が不正なら、使い方を表示して終了コード 64 で止まる。

対象のクライアントと、それぞれが使うトラストストア:

| 表示名 | 接続の方法 | トラストストア |
| --- | --- | --- |
| `openssl` | `openssl s_client`（`-verify_return_error`・`-verify_hostname`、CA の指定なし） | OpenSSL の既定（システムの CA バンドル） |
| `curl` | `curl -sS -o /dev/null --no-location`（`.curlrc` の `--location` を打ち消し、リダイレクトを追わない） | curl の設定（既定はシステムの CA バンドル） |
| `git` | `git ls-remote https://HOST:PORT/`（`GIT_TRACE_CURL` で HTTP 応答を記録） | git の設定（既定はシステムの CA バンドル） |
| `python` | `uv run --no-project python -I` の `urllib.request`（リダイレクトを追わない opener）と `ssl.create_default_context()` | リポジトリのツールが使う Python の `ssl`（システムの OpenSSL） |
| `node` | `node -e` の `fetch()`（`redirect: "manual"`） | Node.js の同梱 CA（`NODE_EXTRA_CA_CERTS` などの設定を含む） |
| `uv` | `uv --color never -vv pip compile` で確認用ホストを index にする（`--no-config --no-cache`、再試行 0。`UV_CONFIG_FILE` と、index を足す環境変数 `UV_INDEX`・`UV_EXTRA_INDEX_URL` などは外す） | uv の同梱 CA（webpki-roots）。`SSL_CERT_FILE`・`UV_NATIVE_TLS` などの環境変数は反映する |

判定の規則（クライアントとホストの組ごと）。拒否を示す証拠だけで「信頼していない」とし、それ以外の失敗はすべて「判定不能」に倒す。

1. **信頼している**: TLS が成立した証拠がある。`openssl` は接続の確立（`CONNECTION ESTABLISHED`）、`curl` は終了コード 0、`git` は `GIT_TRACE_CURL` の HTTP 応答ヘッダの受信、`python`・`node` は HTTP 応答（状態コードは問わない）、`uv` は `-vv` の応答受信かリダイレクトの受信の記録。対象が返した 3xx も含み、リダイレクト先の結果は判定に使わない。拒否の証拠より優先する
2. **信頼していない**: 発行者を信頼しないことを示す検証エラーがある。
   - OpenSSL の検証コード（`openssl`・`curl`・`git`・`python`）: 2（unable to get issuer certificate）、19（self-signed certificate in certificate chain）、20（unable to get local issuer certificate）、21（unable to verify the first certificate）、23（certificate revoked）、27（certificate not trusted）、28（certificate rejected）
   - Node.js のエラーコード: `UNABLE_TO_GET_ISSUER_CERT`・`SELF_SIGNED_CERT_IN_CHAIN`・`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`・`UNABLE_TO_VERIFY_LEAF_SIGNATURE`・`CERT_REVOKED`・`CERT_UNTRUSTED`・`CERT_REJECTED`
   - uv（rustls）: `invalid peer certificate:` に続く `UnknownIssuer`・`Revoked`・`Other(OtherError(CertDistrusted))`。最後に失敗した URL（`Failed to fetch:`）が対象の index のときだけ数える
3. **判定不能**: 上のどちらでもない。接続の拒否・名前解決の失敗・タイムアウト・コマンドが無い・期限切れや名前の不一致などの検証エラー・想定外の出力が当たる

出力: 組ごとに 1 行（表示名、`HOST:PORT`、判定、根拠の短い説明）と、最後に要約を 1 行。終了コードは、すべて「信頼していない」なら 0、「信頼している」が 1 つでもあれば 1、それ以外で「判定不能」があれば 2。

各接続はクライアント側のタイムアウト（15 秒）と、外側の `timeout`（30 秒）で打ち切る。作業用の一時ディレクトリを cwd にして実行し、終わったら消す。

### 2. postCreate の `ca-certificates` の更新

`.devcontainer/install_beforehand.bash` の `apt update` の直後に、独立した step として `sudo apt-get install -y ca-certificates` を実行する関数 `upgrade_ca_certificates` を置き、失敗したら `fail` で postCreate を止める。この後の step の `curl | bash` の導入も、更新したトラストストアで検証される。`STEP_TOTAL` は実際の step の数（追加後 31）に合わせる（着手前から 29 と 30 でずれていた）。

### 3. 文書

- `.devcontainer/README.md` に「トラストストアの確認（eMudhra 中間CA の侵害）」の節を足す。確認のコマンド、3 つの判定と終了コードの読み方、クライアントごとのトラストストアと「信頼している」になったときの更新方法、スクリプトの対象外のツールの扱い、ホスト側の更新の案内（Windows 11・ブラウザ・WSL2 の Gentoo・Docker Desktop・Git for Windows・VS Code・Electron アプリ。修正版は確認サイトの一覧に従う）を書く
- 同じ README の「既存環境の更新」に、postCreate の `ca-certificates` の更新、rebuild 後の確認、rebuild しないときの `ca-certificates` の更新コマンドを足す
- ルートの `README.md` の「Dev Container を起動する」の 3 に、確認のコマンドとホスト側の案内への参照を足す

### 4. 同梱 CA のツールの点検

Issue の方針 5 の対象（uv・Codex CLI・cursor-agent・devin・gemini（Antigravity CLI の `agy`）・gitleaks・Blender）の版と、使うトラストストア、判定を Issue #291 のコメントに記録する。着手時の点検では、どれも修正版以上か、Linux のシステムストアを使っており（「初期観測」）、`install_*.bash` の版を上げる必要は無い。

## 決定記録

| 項目 | 選択した案 | 検討した別案 | 選択理由 | 委任・停止条件 |
| --- | --- | --- | --- | --- |
| 判定の根拠 | 拒否・成立のどちらも、出力にある証拠でだけ決め、証拠が無ければ判定不能 | 終了コードが 0 以外なら「信頼していない」 | 接続の失敗を安全と報告しない（Issue のリスク）。誤りが出ても非 0 の側に倒れる | 推奨案の委任 |
| 「信頼していない」とする検証エラー | 発行者を信頼しないことを示すものだけ（OpenSSL 2・19・20・21・23・27・28 と対応する Node.js・rustls の理由） | TLS の検証エラーをすべて含める | 確認用ホストの証明書が期限切れになったり名前が変わったりすると、検証の対象が中間CA の信頼から外れる。それを安全と報告すると、気付けない | 推奨案の委任 |
| 対照ホスト（正常に接続できるホスト） | 置かない | 各クライアントで対照ホストへの接続の成功を前提にする | 何も検証できないクライアントは、普段の利用で接続に失敗して気付く。危ない側（信頼している）は HTTP 応答で必ず捕まえる。外部への依存を増やさない | 推奨案の委任 |
| 判定の優先 | 成立の証拠を拒否の証拠より優先する | 拒否の証拠を優先する | プロキシの CONNECT の応答などで両方が出たとき、非 0 の側に倒す | 推奨案の委任 |
| Python の実行 | `uv run --no-project python -I` | `python3` | AGENTS.md の「Python は uv 必須」に合わせ、リポジトリのツールが実際に使う Python（着手時は `/usr/bin/python3`）を確かめる | 推奨案の委任 |
| uv の接続 | `uv -vv pip compile --no-config --no-cache` で確認用ホストを index にし、`UV_HTTP_RETRIES=0` | `uv pip install --dry-run`、利用者の uv の設定ファイルを読む | 環境（venv）を作らずに済み、`-vv` で応答の受信を区別できる。設定ファイルと環境変数の別 index が混ざらないよう、`--no-config` にし、index を足す環境変数（`UV_INDEX`・`UV_DEFAULT_INDEX`・`UV_INDEX_URL`・`UV_EXTRA_INDEX_URL`・`UV_FIND_LINKS`・`UV_TORCH_BACKEND`・`UV_NO_INDEX`・`UV_OFFLINE`）を外す（extra の index は対象より先に問い合わせられ、その結果で対象を判定してしまう。最終レビューの指摘）。設定ファイルの TLS の指定は反映しないが、TLS の環境変数は反映する | 推奨案の委任 |
| 終了コード | 0（すべて信頼していない）・1（信頼している）・2（判定不能）・64（使い方の誤り） | 非 0 を 1 つにまとめる | 次の行動（更新か再実行か）が違う。使い方の誤りは `herdr-agent-task.bash` と同じ 64 | 推奨案の委任 |
| `ca-certificates` の更新 | `apt-get install -y ca-certificates` を独立の step で `apt update` の直後に実行 | Issue 案の `--only-upgrade`、基本パッケージの一覧に足す | `--only-upgrade` はパッケージが無いと何もせず 0 で終わる。独立の step にすると postCreate のログで更新を追え、後の step の HTTPS の導入も新しいトラストストアで検証される | 推奨案の委任。上げられなければ postCreate を失敗させる（Issue の受け入れ条件） |
| ホスト側の案内の置き場所 | `.devcontainer/README.md` の新しい節。ルートの README からは参照だけ | ルートの README に全文 | ツールとトラストストアの対応と同じ場所にまとめる。ルートの README は起動の手順に 1 行足すだけにする | Issue が置き場所を実装時の判断に委ねている |
| 点検の記録 | Issue #291 のコメント。版を上げる `install_*.bash` の変更はしない | 版を固定して上げる | 点検したツールはどれも修正版以上か、システムストアを使う。版は今後も変わるので、README には修正版の下限と確かめ方だけを書く | Issue の方針 5 |
| テスト | 実際のクライアントとローカルの `openssl s_server` で 4 つの状態（信頼させた・信頼させない・期限切れ・閉じたポート）を確かめる 1 本と、`upgrade_ca_certificates` の失敗を偽の `sudo`・`apt-get` で確かめる追記 | 偽のクライアントの出力で対応表を網羅する | 実際の出力の形で、危ない側（成立・期限切れ・接続できない）を「信頼していない」にしないことを確かめられる。拒否の文言（`CERT_REVOKED`・`CertDistrusted`）の取りこぼしは非 0 で気付ける（L）ので網羅しない | AGENTS.md の「テストの採用基準」 |
| 実行方式 | `superpowers:executing-plans`（このセッションが実装） | `superpowers:subagent-driven-development` | 実装の根拠になる実際の出力の観測をこのセッションが持っており、README は確認スクリプトの出力に依存する。Task 数が少なく逐次で進む | `implement_task.py check` の `self` が true |
| Plan の実装担当 | `self`（fallback なし） | `--implement` での置き換え | `implement_task.py check` の観測結果。雛形の既定の適用であり、利用者の指定ではない | — |
| マージのループ | `max_cycles=3`（既定の適用）、`review.inspect` は `pi-gpt`・`devin-swe`・`pi-deepseek`（利用者の指定）、`fix.implement` は `claude-opus`、`self-review`・`fix-check` は `self`（既定の適用）、fallback はすべてなし | — | `loop.py check-options` の観測結果。template は `/workspaces/reso-world/.devcontainer/agent-runner.toml`、config は null | 対象・競合・安全境界の変化、必要なツールの失敗では issue-to-pr の停止条件に従う |

## 受け入れ基準と検証

Issue の受け入れ条件と、この Spec の設計からの条件:

1. 現行のコンテナで `bash .devcontainer/verify-ca-trust.bash` が 0 で終わり、4 ホスト × 6 クライアントが「信頼していない」と表示する（実際に外部へ接続して確かめ、結果を PR と Issue に記録する）
2. 到達できないホスト・ポートでは 0 で終わらず「判定不能」と表示する（テストで閉じたポートを使う）
3. テスト用の CA を各クライアントに信頼させた状態では「信頼している」と表示して非 0 で終わる（テストで `openssl s_server` と `SSL_CERT_FILE`・`CURL_CA_BUNDLE`・`GIT_SSL_CAINFO`・`NODE_EXTRA_CA_CERTS` を使う）
4. 信頼させた CA の期限切れの証明書では「信頼していない」と表示せず、非 0 で終わる（この Spec の設計から）
5. postCreate で `ca-certificates` を更新した索引の最新版へ上げ、上げられなければ postCreate が失敗する（関数のテストと、このコンテナでの実行。rebuild での確認はマージの後に残る）
6. `.devcontainer/README.md` の「既存環境の更新」に確認コマンドと 3 つの判定の読み方への案内がある
7. ホスト側で更新するもの（OS・ブラウザ・Electron アプリ・Docker Desktop・Git for Windows）の案内がある
8. 同梱 CA のツールの点検結果（版と判定、未確認ならその理由）が Issue に記録されている

検証の入口: worktree のルートで `bash .devcontainer/run-tests.bash`、`bash scripts/check-layout.sh`、`uv run pytest tests/skills .agents/skills .agents/scripts tools`。

マージの後でなければ確かめられない項目: rebuild の postCreate で `ca-certificates` が上がり、その後の `verify-ca-trust.bash` が 0 で終わること。このため PR は `Refs #291` とし、PR と Issue にこの項目を残す。

## 初期観測（2026-10-28、この開発コンテナ）

- 実ホストへの接続: `curl`・`git`・`openssl`・Python は OpenSSL の検証コード 20、Node.js は `CERT_REVOKED`、uv は `invalid peer certificate: Other(OtherError(CertDistrusted))`。対照の `https://emudhra.we-have-a-problem.com/` は curl で 200
- ローカルの `openssl s_server -www`（テスト用 CA で信頼させた状態）: curl は終了コード 0、git は `<= Recv header: HTTP/1.0 200 ok` の後に `not valid: is this a git repository?`、openssl は `CONNECTION ESTABLISHED`、Python・Node.js は 200、uv は `-vv` で `Received response for fresh request with status 200 OK`。信頼させない状態では、OpenSSL 系は 20、Node.js は `UNABLE_TO_VERIFY_LEAF_SIGNATURE`、uv は `UnknownIssuer`
- Python 3.14 は CA 証明書に keyUsage が無いと検証に失敗する（テスト用 CA に keyUsage を付ける）
- uv は `SSL_CERT_FILE` を指定すると、そのファイルだけを信頼する。接続の失敗では既定で 3 回再試行する（`UV_HTTP_RETRIES=0` で止める）
- 同梱 CA のツールの点検（確認サイトの修正版と比べた）:

  | ツール | 版 | トラストストア | 判定 |
  | --- | --- | --- | --- |
  | uv | 0.13.6 | 同梱の webpki-roots | 修正版 0.13.5 以上。実ホストで `CertDistrusted` |
  | Codex CLI | 0.165.0 | Rust（rustls-webpki 0.103.16、native-tls） | rustls-webpki は修正版 0.103.16。Issue の点検で TLS の段階で止まることを確認済み |
  | cursor-agent | 2026.10.22-27dcf5f | 同梱の Node.js v24.22.1（`--use-system-ca` の分岐あり） | Node.js の修正版。同梱の `node` で実ホストが `CERT_REVOKED` |
  | devin | 3000.11.228 | Rust（rustls-platform-verifier 0.6.2、rustls-webpki 0.103.16）。webpki-roots は含まない | Linux ではシステムストア。rustls-webpki は修正版 |
  | agy（Antigravity CLI。Issue の「gemini」） | 1.4.8 | Go の `crypto/x509` のシステムストア（`x509roots/fallback` を含まない） | Linux ではシステムストア |
  | gitleaks | 8.30.1（Go 1.24.11） | Go のシステムストア（fallback を含まない）。検査は手元のリポジトリだけで、HTTPS を使わない | 版を上げる必要は無い |
  | Blender | 5.0.1（Ubuntu のパッケージ） | システムの Python 3.14.4 と OpenSSL 3.5.5（`/usr/lib/ssl/cert.pem`） | 実ホストで検証コード 20 |
  | GitHub CLI・Claude Code | 2.103.3・2.1.312 | 各自 | 修正版（2.102.1・2.1.303）以上 |

## PR #293 のレビュー修正（サイクル 1）

- 対象: PR https://github.com/usaturn/create-reso-world/pull/293（`feat/issue-291-ca-trust-check`）、レビューした HEAD `fa74d80e1b3a4d426ab0ec29d6a95a4f8759c011`、base `4f7e64f5fb9655fed59bff12121474c538cfb109`
- 実行許可: `/issue-to-pr #291 --assign inspect=pi-gpt,devin-swe,pi-deepseek --merge` による PR 修正ループ（review-fix-planning の完遂）。内容の承認ではない
- planner: `claude-opus-5-5`（Claude Code）。サイクル 1（前の判断の記録なし）
- 入力: `/workspaces/reso-world/reviews/usaturn/create-reso-world/#293-feat-issue-291-ca-trust-check/`

### レビュアーの構成

| レビューファイル | モデル | ランタイム | レビュー HEAD | 再実行 | Merge recommendation |
| --- | --- | --- | --- | --- | --- |
| gpt-6.1-sol.md | gpt-6.1-sol | pi | fa74d80e1b3a | true | Request changes |
| SWE-2-Max.md | SWE-2 Max | devin | fa74d80e1b3a | true | Approve |
| deepseek-deepseek-v4.1-flash.md | deepseek/deepseek-v4.1-flash | pi | fa74d80e1b3a | true | Approve |

### 全指摘と区分（解消済み 0 / 対応する 2 / 対応しない 3）

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| `gpt-6.1-sol#H-1@fa74d80e1b3a` リダイレクト先の検証エラーを対象の拒否と取り違える | 対応する（a） | 致命的: 侵害された CA を信頼するクライアントがあっても、対象が 3xx を返すだけで「信頼していない」・終了コード 0 になる（文書化された `HOST[:PORT]` と通常の 3xx で到達）。現行 HEAD の隔離 worktree で再現した（2 つの CA と 302 を返すサーバ。全クライアントに信頼させると python・node・uv が「信頼していない」、node だけに信頼させると終了コード 0）。curl も `.curlrc` の `--location` で同じになることを確かめた |
| `SWE-2-Max#M-1@fa74d80e1b3a` `UV_CONFIG_FILE` の別の index が uv の判定に混ざる | 対応する（a） | 致命的: uv が対象に接続しないまま、別のホストの拒否で「信頼していない」になり、終了コード 0 になりうる（uv の文書化された環境変数 `UV_CONFIG_FILE` で到達）。現行 HEAD で再現した（閉じたポートの対象で uv が `UnknownIssuer`） |
| `SWE-2-Max#L-1@fa74d80e1b3a` テストがプロキシ・`NODE_TLS_REJECT_UNAUTHORIZED`・`UV_CONFIG_FILE` を外さない | 対応しない | 外の環境にこれらがあるとテストが誤って失敗する方向で、気付ける。正しくないスクリプトを誤って通すことはない。見直す条件: 利用者の環境変数を引き継いだままテストを自動で実行する運用にするとき |
| `deepseek-deepseek-v4.1-flash#L-1@fa74d80e1b3a` postCreate の呼び出し側をテストしていない | 対応しない | 現行の呼び出し側（`if ! upgrade_ca_certificates; then fail …`）は正しく、将来の変更への保険にあたる。既存の `place_agent_runner_config` のテストと同じ形。見直す条件: 呼び出し側を変えるとき |
| `deepseek-deepseek-v4.1-flash#I-1@fa74d80e1b3a` `docs/integration.md` の rebuild 後の確認の一覧に無い | 対応しない | 記載の追加で、誤った手順ではない。確認は `.devcontainer/README.md` の「既存環境の更新」6 とルートの `README.md` にある。見直す条件: `docs/integration.md` を rebuild 後の確認の唯一の一覧にするとき |

### 要件対応

- PR の約束（この Spec の「受け入れ基準と検証」と防御範囲）: 発行者を信頼しない検証エラーだけを「信頼していない」にし、TLS の成立は「信頼している」・非 0 にする。H-1・M-1 は、対象ではないホストの拒否を対象の「信頼していない」にしており、この約束に反する
- 共有条件: 判定の規則と表示（`classify`）を 6 つのクライアントが共有する。統合担当は planner（このセッション）で、修正の取り込みの後にテストと一時的な対照で、全クライアントの経路を確かめる

### 設計の見直し（きっかけ: 同じ守る条件の 2 回目）

`fa74d80`（最終レビューの指摘への対応）で、uv が環境変数の別の index で判定する問題を、その環境変数を外す点の修正で直した。今回の H-1・M-1 は同じ条件（対象への接続だけで判定する）が、設定ファイルとリダイレクトという別の入口で破れたものである。

**守る条件の設計:** 各行の判定は、そのクライアントが指定した HOST:PORT と行った TLS の接続と、そのホストが返した HTTP 応答だけから決める。設定（別の index・設定ファイル）やリダイレクトで接続した別のホストの結果を、対象の判定に使わない。対象が HTTP の応答（3xx を含む）を返したら、TLS が成立した証拠として「信頼している」にする。この条件は、6 つのクライアント、3 つの判定、接続の失敗・拒否・成立のどの停止位置でも成り立つ。

**`fa74d80` で足りなかった理由:** 判定（`classify`）が、証拠がどのホストへの接続のものかを確かめず、混入を起こす入力を 1 つずつ外していた。入口を列挙しきれなければ、残った入口で同じ誤りになる。

**比べた直し方:**

| 案 | 内容 | 判断 |
| --- | --- | --- |
| 点の修正を続ける | `UV_CONFIG_FILE` を外し、python・node のリダイレクトを止める | 未知の入口（uv の新しい設定など）が残る。選ばない |
| 条件を 1 か所で保つ | HTTP のクライアントはリダイレクトを追わず 3xx を成立に数える。uv の拒否は、最後の `Failed to fetch` の URL が対象のときだけ数える。あわせて既知の入口（`UV_CONFIG_FILE`）も外す | **選んだ**。どの入口から別のホストが混ざっても、その拒否は対象の判定にならず、判定不能（非 0）に倒れる |
| 保証を狭める | リダイレクトするホストや uv の設定を対象外として文書化する | 実行許可は保証を狭める変更を委任していない。選ばない |

### 守る条件と影響経路

| 経路 | 判定 | 変更前の挙動 | 観測する結果 | 確かめる方法（assertion） | 実行結果・証拠 |
| --- | --- | --- | --- | --- | --- |
| python（`urllib` がリダイレクトを追う） | 修正する | リダイレクト先の拒否を対象の「信頼していない」にする | 対象の 302 で「信頼している」 | テストのリダイレクトの状態で 6 行が「信頼している」・非 0 | ae401f8・bf5c503 で PASS（6 行「信頼している」、python は HTTP 302）。修正前は「信頼していない  OpenSSL 20」。NoRedirect を外した対照で FAIL |
| node（`fetch` がリダイレクトを追う） | 修正する | 同上 | 同上 | 同上 | 同上（node は HTTP 302）。修正前は `UNABLE_TO_VERIFY_LEAF_SIGNATURE`。`redirect: "manual"` を外した対照で FAIL |
| curl（`.curlrc` の `--location`） | 修正する | 同上 | 同上 | 同上（一時 HOME に `.curlrc`） | 同上。修正前は終了コード 60・OpenSSL 20。`--no-location` を外した対照で FAIL |
| uv（自分でリダイレクトを追う） | 修正する | 同上 | 同上（`Received HTTP 3xx … Redirecting` を成立の証拠に） | 同上 | 同上（`Received HTTP 302 Found. Redirecting to`）。修正前は `UnknownIssuer`。3xx の証拠を外した対照で FAIL |
| uv（`UV_CONFIG_FILE` の別の index） | 修正する | 別のホストの拒否を対象の「信頼していない」にする | 正例が 0・6 行「信頼していない」のまま | 正例の `run` に `UV_CONFIG_FILE`（閉じたポートの extra index）を足す | ae401f8・bf5c503 で PASS。修正前は正例が終了コード 2。`-u UV_CONFIG_FILE` を外した対照で FAIL |
| uv（未知の入口からの別のホストの拒否） | 修正する | 同上 | 対象以外の URL の拒否は判定不能 | 一時的な対照（`-u UV_CONFIG_FILE` を外した版で正例の uv が判定不能になる。テストは足さない） | ae401f8 の対照: 照合ありで「判定不能  対象ではない URL での失敗」、照合を外すと「信頼していない  UnknownIssuer」 |
| git（リダイレクト） | 既に満たす | 最初の応答ヘッダで「信頼している」 | 同上 | テストのリダイレクトの状態 | 修正前・後とも「信頼している」（最初の応答ヘッダ）。git はリダイレクト先にも接続するが、判定には使わない（fix-check#V-2） |
| openssl | 既に満たす | HTTP を使わず、対象への 1 本の接続 | 同上 | 同上 | 修正前・後とも「信頼している」 |
| git の `url.<base>.insteadOf`、curl の `--connect-to`・`--resolve` | 対象外 | 利用者の設定で URL・接続先を書き換える特殊な構成。README に注意を書く | ― | ― | 対象外 |

### 修正と検証

- 修正の担当: `run_roles.py --phase implement`（`fix.implement` は `claude-opus`）。依頼は `/workspaces/reso-world/tmp/agents/pr-293-review-fix.9gpyniud/implement-prompt.md`
- テスト（`AGENTS.md` の「テストの採用基準」の S）: リダイレクトの状態を 1 つ足し（状態は 5 つになった）、既存の正例に `UV_CONFIG_FILE` を足した。URL の照合はテストに入れず、一時的な対照で確かめた
- 修正 1: `ae401f8`（担当 claude-opus、Claude Code 2.1.312、534 秒、停止確認済み）。RED は 2 つ（正例が `got 2`、リダイレクトの状態が `got 2`）を確かめてから直した
- 実行した `run_roles.py --phase implement` の 1 回目の終了コードは 1 だった（`outside_changes`）。挙がった 2 つの worktree（`/tmp/review-fix-planning.jTyYzf`・`/tmp/review-fix-planning.giCOzX`）は、planner の手順 3 の後片付けと、確認済みの一覧を作った担当の後片付けで外したもので、修正担当の操作ではない（時刻で照合した）
- ガードを 1 つずつ外した対照（隔離 worktree）: `--no-location`・`redirect: "manual"`・python の NoRedirect・uv の 3xx の証拠・`-u UV_CONFIG_FILE` の 5 つとも、外すとテストが FAIL した

### 自己レビュー（1 回）

`run_roles.py --phase self-review` を 1 回呼んだ（`pre_push_review` の枠を 1 つ予約）。2 つの役割はどちらも割り当てが `self` で、planner が新しいサブエージェント（Claude Code、claude-opus-5-5）2 つに同時に任せた。

- self-review（PR 全体の再レビュー、`ae401f8`）: `claude-opus-5-5-commit-ae401f800aab63b6195b3b58f1c9258a2d3df404.md`。Needs manual verification（修正後の実ホストの確認が未実施だったため。planner が統合の後に実行した）。指摘 L-1・L-2・I-1・I-2
- fix-check（修正の確認）: `verified/ae401f800aab.fix-check.json`。主張 11 件のうち holds 9・violates 2。新しい問題 V-1〜V-4。観点 3（検出力）では、変異 7 件のうち、URL の照合だけを外した変異をテストが検出しない（意図どおり。上の経路表）

| 指摘 | 区分 | 根拠 |
| --- | --- | --- |
| `fix-check#V-1@ae401f800aab` と `claude-opus-5-5-commit-ae401f800aab63b6195b3b58f1c9258a2d3df404#L-1@ae401f800aab` `FORCE_COLOR`・`CLICOLOR_FORCE` で uv の行が「判定不能」になる | 対応する（a） | 致命的: 色を強制する環境変数がある環境では、uv が拒否していても確認が一度も通らない（手順のとおりに使うと誤った結果）。この回の修正（`uv_fetch_failure` の行頭の照合）が持ち込んだ回帰で、修正前は 0 だった。再現済み |
| `claude-opus-5-5-commit-…#L-2@ae401f800aab` uv の成立の証拠が URL を見ていない（`UV_CONSTRAINT` で別の index） | 対応しない | 誤っても「信頼している」・終了コード 1 の側に倒れ、安全と報告しない。修正前と同じ挙動。見直す条件: 成立の証拠の誤りで更新の手間が問題になるとき |
| `claude-opus-5-5-commit-…#I-1@ae401f800aab` と `fix-check#V-2@ae401f800aab` README の「リダイレクト先には接続しない」は git・uv に当てはまらない | 対応しない | 記述の不正確さで、そのとおりに進めても誤った結果にはならない（判定にはリダイレクト先の結果を使わない）。見直す条件: README のこの節を次に変えるとき |
| `claude-opus-5-5-commit-…#I-2@ae401f800aab` と `fix-check#V-3@ae401f800aab` Spec・Plan・README の uv の記述が古い | 対応しない | 誤った結果にはならない。Spec はこのサイクルの記録として、設計の節の該当行（接続の方法の表・判定の規則）も更新した。Plan は実装時点の記録として変えない |
| `fix-check#V-4@ae401f800aab` テストの説明（状態の数・使うサーバ）が古い | 対応しない | 説明の古さで、誤った結果にはならない。見直す条件: テストの説明を次に変えるとき |

### 設計の見直し（きっかけ: 自己レビューでの再発）

V-1 は、この回の修正が原因の致命的な指摘である。守る条件の設計に「uv の判定は出力の文字列を読むので、出力の形を環境に左右されないように固定する（色を付けない）」を足した。出力を読むほかのクライアントは、色を付けない（curl・git・openssl）か、自分で書いた行を読む（python・node）ので、変えない。直し方は、照合を色の制御文字に合わせて緩める案と比べ、出力の形そのものを固定する `uv --color never` を選んだ（照合の正規表現を複雑にしない）。

- 修正 2: `bf5c503`（担当 claude-opus、144 秒、停止確認済み）。修正前に `env FORCE_COLOR=1 bash .devcontainer/run-tests.bash .devcontainer/test-verify-ca-trust.bash` が FAIL（`got 2`）、修正後に `FORCE_COLOR=1`・`CLICOLOR_FORCE=1`・環境変数なしの 3 通りで PASS
- テストは足さない（誤りは非 0 の「判定不能」の側に倒れ、気付ける。`AGENTS.md` の L）
- 自己レビューの後の修正なので、2 回目の自己レビューはしていない（V-1 の修正は再レビューしていない）

### 最後の修正の後の検証（`bf5c503`）

| コマンド | 終了コード | 結果 |
| --- | --- | --- |
| `bash .devcontainer/run-tests.bash` | 0 | 24 test(s) PASS（開始時の作業ツリーは clean。実行中に Spec の文書だけを編集した） |
| `bash scripts/check-layout.sh` | 0 | PASS |
| `env FORCE_COLOR=1 bash .devcontainer/run-tests.bash .devcontainer/test-verify-ca-trust.bash` | 0 | PASS |
| `env CLICOLOR_FORCE=1 bash .devcontainer/run-tests.bash .devcontainer/test-verify-ca-trust.bash` | 0 | PASS |
| `env FORCE_COLOR=1 bash .devcontainer/verify-ca-trust.bash`（実ホスト） | 0 | 24 件すべて「信頼していない」。`ae401f8` でも色なしで 24 件・0 |

### 結論

結論 1（修正して push）。対応する 3 件（H-1・M-1・V-1/L-1）を直し、対応しない 7 件（レビュアーの 3 件と、自己レビュー・修正の確認の 4 件）は上の理由で残した。未確認の事項: git の `url.<base>.insteadOf`、curl の `--connect-to`・`--resolve` で接続先を書き換えた環境（対象外として README に注意を書いた）。

- 修正と自己レビューの担当（`run_roles.py` の割り当て）: implement は claude-opus（2 回）、self-review・fix-check は self（自己レビューの呼び出し 1 回）
- 確認済みの一覧: `verified/fa74d80e1b3a.json`（confirmed 5）、工程の記録: `verified/fa74d80e1b3a.planning.json`、修正の確認: `verified/ae401f800aab.fix-check.json`
