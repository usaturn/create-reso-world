// @ts-nocheck
//
// Herdr の復元で、ランチャー（pigs など）から起動した Pi のペインを、同じランチャーで再開させる（create-reso-world #309）。
// scripts/setup_pi_superagents.zsh が ~/.pi/agent/extensions/herdr-launcher-resume.ts に置く。Herdr の Pi 連携
// （herdr-agent-state.ts、managed by herdr）は書き換えず、その横で動く。共通ヘルパ（pi-superagents-exec.zsh）が
// bwrap に --setenv PI_SUPERAGENTS_LAUNCHER <ランチャー> を渡したときだけ動き、素の pi・子 Pi・Herdr の外では何もしない。
//
// Herdr 0.9.5 で確かめた振る舞い（docs/superpowers/specs/2026-11-05-issue-309-herdr-pi-launcher-resume-design.md）:
//   - resume_argv はペインを持つ source（状態を報告した herdr:pi）からしか受け付けない（resume_not_accepted）
//   - seq の無い報告は保存されず、同じ source のセッションの報告は seq の大きい順にしか受け付けない
//   - セッションのパスの変更には session_start_source が要る
//   - 保存済みの再開コマンドは、resume_argv の無い報告やパスの変更では消えない。セッションを切り替えたら報告し直す
// Herdr の連携の seq は起動時の時刻（ミリ秒 × 1000）から 1 ずつ増えるので、時刻から作るこの拡張の seq の方が大きい。
// このため以後の連携のセッションの報告は捨てられるが、この拡張が同じパスを報告するので、Herdr が持つパスは正しく保たれる。
// 状態の報告（working / idle）の seq は別に比べられ、影響を受けない。
//
// 拡張の中の例外は Pi ごと終了させるので、外に出さない。

import net from "node:net";
import path from "node:path";

const SOURCE = "herdr:pi";
const LAUNCHER_PATTERN = /^[a-z][a-z0-9_-]*$/;
const SESSION_ID_PATTERN = /^[A-Za-z0-9-]+$/;
// Herdr は resume_argv にアポストロフィと制御文字を許さない
const REJECTED_BY_HERDR = /['\u0000-\u001f\u007f]/;
// 起動直後は Herdr の連携がまだ状態を報告しておらず、resume_not_accepted になり得る
const RETRY_DELAYS_MS = [0, 250, 500, 1000, 2000, 4000];
const RESPONSE_TIMEOUT_MS = 2000;
// 拡張のモジュールが読み直されても、世代番号と seq を共有する
const STATE_KEY = Symbol.for("create-reso-world.herdr-launcher-resume");

function sharedState() {
    if (!globalThis[STATE_KEY]) {
        globalThis[STATE_KEY] = { generation: 0, seq: 0 };
    }
    return globalThis[STATE_KEY];
}

function nextSeq(state) {
    state.seq = Math.max(state.seq + 1, Date.now() * 1000);
    return state.seq;
}

function sleep(ms) {
    return new Promise((resolve) => {
        const timer = setTimeout(resolve, ms);
        timer.unref?.();
    });
}

// 結果は "ok"（受け付けた）、"retry"（やり直す）、"stop"（ほかの拒否。やり直しても通らない）
function send(socketPath, request) {
    return new Promise((resolve) => {
        let done = false;
        let buffer = "";
        let socket;
        const finish = (outcome) => {
            if (done) return;
            done = true;
            clearTimeout(timeout);
            socket?.destroy();
            resolve(outcome);
        };
        const timeout = setTimeout(() => finish("retry"), RESPONSE_TIMEOUT_MS);
        timeout.unref?.();
        try {
            socket = net.createConnection(socketPath);
        } catch {
            finish("retry");
            return;
        }
        socket.on("error", () => finish("retry"));
        socket.on("end", () => finish("retry"));
        socket.on("connect", () => socket.write(`${JSON.stringify(request)}\n`));
        socket.on("data", (chunk) => {
            buffer += chunk;
            const end = buffer.indexOf("\n");
            if (end < 0) return;
            try {
                const response = JSON.parse(buffer.slice(0, end));
                if (response?.result) {
                    finish("ok");
                } else {
                    finish(response?.error?.code === "resume_not_accepted" ? "retry" : "stop");
                }
            } catch {
                finish("retry");
            }
        });
    });
}

async function report(socketPath, state, generation, params) {
    for (const delay of RETRY_DELAYS_MS) {
        if (delay > 0) {
            await sleep(delay);
        }
        // 新しいセッションが始まったら、前のセッションの報告を送らない
        if (state.generation !== generation) {
            return;
        }
        const request = {
            id: `${SOURCE}:launcher-resume:${Date.now()}:${Math.random().toString(36).slice(2)}`,
            method: "pane.report_agent_session",
            params: { ...params, seq: nextSeq(state) },
        };
        if ((await send(socketPath, request)) !== "retry") {
            return;
        }
    }
}

function resumeTarget(sessionFile, sessionId) {
    if (!REJECTED_BY_HERDR.test(sessionFile)) {
        return sessionFile;
    }
    if (typeof sessionId === "string" && SESSION_ID_PATTERN.test(sessionId)) {
        return sessionId;
    }
    return undefined;
}

export default function (pi) {
    const launcher = process.env.PI_SUPERAGENTS_LAUNCHER;
    const socketPath = process.env.HERDR_SOCKET_PATH;
    const paneId = process.env.HERDR_PANE_ID;
    if (process.env.HERDR_ENV !== "1" || !socketPath || !paneId ||
        typeof launcher !== "string" || !LAUNCHER_PATTERN.test(launcher)) {
        return;
    }

    pi.on("session_start", (event, ctx) => {
        try {
            // TUI だけ。子 Pi（--mode json）は親の HERDR_PANE_ID を継承するので、報告すると親のペインの再開先を奪う
            if (ctx?.mode !== "tui") {
                return;
            }
            const state = sharedState();
            state.generation += 1;
            const generation = state.generation;
            const sessionFile = ctx?.sessionManager?.getSessionFile?.();
            if (typeof sessionFile !== "string" || !path.isAbsolute(sessionFile)) {
                return;
            }
            let sessionId;
            try {
                sessionId = ctx.sessionManager.getSessionId?.();
            } catch {
                sessionId = undefined;
            }
            const target = resumeTarget(sessionFile, sessionId);
            if (!target) {
                return;
            }
            // session_start の処理（Pi の起動）を待たせない
            report(socketPath, state, generation, {
                pane_id: paneId,
                source: SOURCE,
                agent: "pi",
                session_start_source: typeof event?.reason === "string" ? event.reason : undefined,
                agent_session_path: sessionFile,
                resume_argv: [launcher, "--session", target],
            }).catch(() => {});
        } catch {
            // 報告できなくても Pi は使える。復元は Herdr の既定（Pi そのもので再開）に戻るだけ
        }
    });
}
