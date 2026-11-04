#!/bin/bash
# .devcontainer/pi-herdr-launcher-resume.ts（Herdr の復元で、ランチャーから起動した Pi をそのランチャーで再開させる拡張）のテスト。
# 偽の Herdr のソケットを一時ディレクトリに立て、拡張が送る報告を受けて確かめる。利用者の ~/.pi・Herdr には触れない。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION="${REPO_ROOT}/.devcontainer/pi-herdr-launcher-resume.ts"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "${TEST_ROOT:?}"' EXIT

cat > "${TEST_ROOT}/test.mjs" <<'JS'
import net from "node:net";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [extensionPath, root] = process.argv.slice(2);
const socketPath = path.join(root, "herdr.sock");
const sessions = path.join(root, "sessions dir");
const received = [];
const rejected = new Set();

function fail(message) {
    console.error(`FAIL: ${message}`);
    process.exit(1);
}
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Herdr 0.9.5 と同じく、1 行の JSON の要求に 1 行の JSON で応える。ペインを持っていない報告の拒否は resume_not_accepted
const server = net.createServer((connection) => {
    let buffer = "";
    connection.on("error", () => {});
    connection.on("data", (chunk) => {
        buffer += chunk;
        const end = buffer.indexOf("\n");
        if (end < 0) return;
        const request = JSON.parse(buffer.slice(0, end));
        received.push(request);
        const response = rejected.has(request.params?.agent_session_path)
            ? { id: request.id, error: { code: "resume_not_accepted", message: "resume_argv requires the reporter to hold the pane; report its state with pane.report_agent first" } }
            : { id: request.id, result: { type: "ok" } };
        connection.end(`${JSON.stringify(response)}\n`);
    });
});
await new Promise((resolve) => server.listen(socketPath, resolve));

Object.assign(process.env, {
    HERDR_ENV: "1",
    HERDR_SOCKET_PATH: socketPath,
    HERDR_PANE_ID: "w9:p9",
    PI_SUPERAGENTS_LAUNCHER: "pigs",
});
const { default: extension } = await import(pathToFileURL(extensionPath).href);
const handlers = {};
extension({ on: (name, handler) => { handlers[name] = handler; } });
if (typeof handlers.session_start !== "function") fail("the extension must handle session_start");

const context = (mode, file, id) => ({
    mode,
    sessionManager: { getSessionFile: () => file, getSessionId: () => id },
});
const requestsFor = (file) => received.filter((request) => request.params?.agent_session_path === file);

// 防ぐ損害: pi-superagents の子 Pi（--mode json）は親の HERDR_PANE_ID と PI_SUPERAGENTS_LAUNCHER を継承する。
// 子が報告すると、子のセッションが親のペインの再開先になり、復元で別のセッションが黙って開く。
async function test_non_tui_pi_does_not_report() {
    const child = path.join(sessions, "2026-11-05T00-00-00-000Z_child.jsonl");
    handlers.session_start({ reason: "startup" }, context("json", child, "child"));
    await sleep(1000);
    if (requestsFor(child).length !== 0) fail("a non-TUI Pi must not report a resume command");
}

// 防ぐ損害: Herdr は resume_argv の無い報告やセッションのパスの変更で、保存済みの再開コマンド（agent_resume）を消さない。
// /new などの切り替えの後に報告し直さないか、前のセッションのやり直しが後から届くと、復元で前のセッションが黙って開く。
async function test_reports_launcher_resume_and_follows_session_switch() {
    const oldFile = path.join(sessions, "2026-11-05T00-00-00-000Z_old.jsonl");
    const newFile = path.join(sessions, "2026-11-05T00-00-01-000Z_new.jsonl");
    rejected.add(oldFile);
    handlers.session_start({ reason: "startup" }, context("tui", oldFile, "old"));
    await sleep(300);
    handlers.session_start({ reason: "new" }, context("tui", newFile, "new"));
    await sleep(9000);

    const first = received.findIndex((request) => request.params?.agent_session_path === newFile);
    if (first < 0) fail("the new session must be reported");
    const request = received[first];
    const params = request.params;
    if (request.method !== "pane.report_agent_session") fail(`method: ${request.method}`);
    if (params.source !== "herdr:pi") fail(`source: ${params.source}`);
    if (params.agent !== "pi") fail(`agent: ${params.agent}`);
    if (params.pane_id !== "w9:p9") fail(`pane_id: ${params.pane_id}`);
    if (params.session_start_source !== "new") fail(`session_start_source: ${params.session_start_source}`);
    if (JSON.stringify(params.resume_argv) !== JSON.stringify(["pigs", "--session", newFile])) {
        fail(`resume_argv: ${JSON.stringify(params.resume_argv)}`);
    }
    if (!Number.isSafeInteger(params.seq)) fail(`seq: ${params.seq}`);

    const old = requestsFor(oldFile);
    if (old.length === 0) fail("the startup session must be reported");
    if (old[0].params.session_start_source !== "startup") fail(`startup session_start_source: ${old[0].params.session_start_source}`);
    if (old[0].params.resume_argv?.[2] !== oldFile) fail(`startup resume_argv: ${JSON.stringify(old[0].params.resume_argv)}`);
    if (received.slice(first + 1).some((later) => later.params?.agent_session_path === oldFile)) {
        fail("a retry for the previous session must not arrive after the new session is reported");
    }
    if (received.slice(0, first).some((earlier) => earlier.params.seq >= params.seq)) {
        fail("the new session must be reported with a larger seq than every earlier report");
    }
}

await test_non_tui_pi_does_not_report();
await test_reports_launcher_resume_and_follows_session_switch();
server.close();
process.exit(0);
JS

node "${TEST_ROOT}/test.mjs" "$EXTENSION" "$TEST_ROOT"
printf 'OK test-pi-herdr-launcher-resume\n'
