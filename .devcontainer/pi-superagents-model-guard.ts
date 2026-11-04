/**
 * pi-superagents の子 Pi が、tier の model（--models）と違う model で最初の要求を送る前に止める（#310）。
 *
 * Pi は --models を、資格情報のある（使える）model の中からだけ解決する。解決できないと警告だけを出して既定の
 * 選び方で別の model を選び、要求を送って終了コード 0 で終わる。bare のパターンは部分一致でも解決し、名指しの
 * provider が使えないと、同じ ID を持つ別の provider の model が選ばれることもある。ランチャーの起動前の検査
 * （pi-superagents-exec.zsh）は資格情報を解決しないので、これらを見られない。この拡張は子 Pi の中で、Pi が最初の
 * 要求に使う model（ctx.model）を --models と照合する。資格情報を解決し直さないので、key のコマンドの実行は増えない。
 * 既存のセッションを引き継ぐ子（fork・再開）では、Pi は --models を使わずにセッションの model を使う。これも tier と違う
 * model なので止め、資格情報の問題と取り違えないよう理由を分けて出す。
 *
 * pi-superagents は子 Pi を --no-extensions で起動し、tier 設定の superagents.extensions に挙げた拡張だけを
 * 読み込ませる。リポジトリの tier 設定（.devcontainer/pi-superagents/<launcher>.json）がこのファイルを挙げ、
 * scripts/setup_pi_superagents.zsh が ~/.pi/agent/extensions/subagent.d/ に置く。subagent.d/ の直下のファイルは
 * Pi の自動探索の対象外なので、親の Pi には読み込まれない。
 *
 * print モードの Pi には、拡張から終了コードを付けて止める手段が無い（ハンドラの例外は報告されるだけで処理が続き、
 * ctx.shutdown は終了コードを選べない）。session_start は最初の要求より前に待たれるので、ここで理由を stderr に
 * 書いて終了コード 1 で終わる。pi-superagents は終了コードが 0 でない子の stderr を、実行記録（run-history.jsonl・
 * meta.json）と親の結果に残す。同じ理由で、確かめる途中の例外（Pi の更新で API が変わったときなど）も自分で
 * 捕まえて止める。例外の内容は資格情報やコマンドの文字列を含みうるので書かない。タスクの本文は読まない。
 */

type ModelRef = { provider: string; id: string };

const PREFIX = "[pi-superagents-model-guard]";
// Pi の thinking level。--models の末尾の :<level> を外すのに使う（level でない接尾辞は ID の一部として残す）。
const LEVELS = new Set(["off", "minimal", "low", "medium", "high", "xhigh", "max"]);
const UPDATE_HINT = "Pi の更新で API が変わった場合は、pi-superagents-model-guard.ts を新しい Pi に合わせる必要があります。";

const same = (left: string, right: string) => left.toLowerCase() === right.toLowerCase();
const label = (model: ModelRef) => `${model.provider}/${model.id}`;

// Pi の引数の解析（dist/cli/args.js）と同じく、-- で止め、後の --models が勝ち、カンマで分ける。
function modelPatterns(argv: readonly string[]): string[] | undefined {
    let patterns: string[] | undefined;
    for (let index = 0; index < argv.length; index++) {
        if (argv[index] === "--") break;
        if (argv[index] === "--models" && index + 1 < argv.length) {
            index += 1;
            patterns = argv[index]
                .split(",")
                .map((pattern) => pattern.trim())
                .filter((pattern) => pattern.length > 0);
        }
    }
    return patterns;
}

function isModelRef(value: unknown): value is ModelRef {
    const model = value as Partial<ModelRef> | undefined;
    return typeof model?.provider === "string" && typeof model.id === "string";
}

// パターンが model を指すか。glob は、どの model を求めたかを決められないので一致しないものとする。最初の / の前が
// Pi の知っている provider なら provider と ID の両方を、それ以外（bare の ID、知らない provider）はパターン全体を
// ID と比べる。大文字小文字は区別しない（Pi の解決と同じ）。
function matches(pattern: string, model: ModelRef, providers: ReadonlySet<string>): boolean {
    if (/[*?[]/u.test(pattern)) return false;
    let text = pattern;
    const colon = text.lastIndexOf(":");
    if (colon !== -1 && LEVELS.has(text.slice(colon + 1))) text = text.slice(0, colon);
    const slash = text.indexOf("/");
    if (slash > 0 && providers.has(text.slice(0, slash).toLowerCase())) {
        return same(model.provider, text.slice(0, slash)) && same(model.id, text.slice(slash + 1));
    }
    return same(model.id, text);
}

const UNRESOLVED = [
    "理由: 要求された model と、Pi がこの子で使う model が一致しません。Pi は --models を資格情報のある model の中からだけ解決し、解決できないと警告だけを出して別の model を選びます。",
    "主な原因: 子 Pi の環境にその provider の資格情報が無い（未ログイン、環境変数の違い）、model ID の誤り、Pi の model catalog が古い。",
    "確かめ方: ランチャーの外の素の pi で pi --list-models <provider> を実行すると、使える model を確かめられます。",
];
// 既存のセッションを引き継ぐ子（pi-superagents の fork、lineage-only の再開）では、Pi は --models で model を決めず、
// セッションの model を復元する（復元できなければ設定の既定を使う）。資格情報の問題ではないので、理由を分けて出す。
const CONTINUED = [
    "理由: この子は既存のセッションを引き継いでいます（pi-superagents の fork、または前の実行の再開）。Pi は既存のセッションでは --models を使わず、セッションの model を使います（復元できなければ設定の既定の model）。",
    "主な原因: fork（--fork）の子は親のセッションの model を引き継ぐので、tier の model が親の model と違うと止まります。再開では、前の実行の後に tier の model を変えると止まります。",
    "対処: tier の model で動かすには fork を使わずに実行し直します。親と同じ model でよければ、その tier の model を親の model に合わせます。",
];

// 既存のセッションにメッセージがあるか。理由の選び分けだけに使い、読めなければ false にする（止めることは変えない）。
function continuesSession(ctx: any): boolean {
    try {
        const branch: unknown = ctx.sessionManager?.getBranch?.();
        return Array.isArray(branch) && branch.some((entry) => (entry as { type?: unknown } | undefined)?.type === "message");
    } catch {
        return false;
    }
}

// 止める理由を返す（照合が通れば undefined）。ctx の値はそれぞれ 1 回だけ読む。
function stopReasons(ctx: any, patterns: readonly string[]): string[] | undefined {
    const current: unknown = ctx.model;
    const registry = ctx.modelRegistry;
    const all: unknown = typeof registry?.getAll === "function" ? registry.getAll() : undefined;
    if (!Array.isArray(all) || !all.every(isModelRef)) {
        return ["Pi の API（ctx.modelRegistry.getAll）から、Pi の知っている model を読めません。", UPDATE_HINT];
    }
    if (current === undefined || current === null) {
        return ["Pi が選んだ model: なし", ...UNRESOLVED];
    }
    if (!isModelRef(current)) {
        return ["Pi の API（ctx.model）から、Pi が選んだ model を読めません。", UPDATE_HINT];
    }
    const providers = new Set(all.map((model) => model.provider.toLowerCase()));
    if (patterns.some((pattern) => matches(pattern, current, providers))) return undefined;
    return [`Pi が選んだ model: ${label(current)}`, ...(continuesSession(ctx) ? CONTINUED : UNRESOLVED)];
}

function stop(patterns: readonly string[], reasons: readonly string[]): never {
    const lines = [
        `${PREFIX} ERROR: 子 Pi が、要求された model と違う model で要求を送ろうとしています。最初の要求の前に終了します。`,
        `  要求された model（--models）: ${patterns.join(",")}`,
        ...reasons.map((reason) => `  ${reason}`),
    ];
    process.stderr.write(lines.map((line) => `${line}\n`).join(""));
    process.exit(1);
}

export default function (pi: { on(event: "session_start", handler: (event: unknown, ctx: any) => Promise<void>): void }) {
    pi.on("session_start", async (_event, ctx) => {
        const patterns = modelPatterns(process.argv.slice(2));
        if (patterns === undefined) return;
        let reasons: string[] | undefined;
        try {
            reasons = stopReasons(ctx, patterns);
        } catch {
            reasons = [
                "Pi の API（ctx.model・ctx.modelRegistry.getAll）から照合する途中で、例外が起きました（例外の内容は、資格情報を含みうるので書きません）。",
                UPDATE_HINT,
            ];
        }
        if (reasons !== undefined) stop(patterns, reasons);
    });
}
