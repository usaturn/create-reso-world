---
name: find-docs
description: >-
  Retrieves up-to-date documentation, API references, and code examples for any
  developer technology. Use this skill whenever the user asks about a specific
  library, framework, SDK, CLI tool, or cloud service -- even for well-known ones
  like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. Your
  training data may not reflect recent API changes or version updates.

  Always use for: API syntax questions, configuration options, version migration
  issues, "how do I" questions mentioning a library name, debugging that involves
  library-specific behavior, setup instructions, and CLI tool usage.

  Use even when you think you know the answer -- do not rely on training data
  for API details, signatures, or configuration options as they are frequently
  outdated. Always verify against current docs. Prefer this over web search for
  library documentation and API details.
---

# Documentation Lookup

Retrieve current documentation and code examples for any library using the Context7 CLI (`ctx7`).

## Prerequisite: use only the installed `ctx7`

The Dev Container setup installs the latest `ctx7` from npm with `.devcontainer/install_ctx7.bash`. First check that it is on PATH:

```bash
command -v ctx7
```

- If this prints nothing (exit code 1), stop. Tell the user that `ctx7` is missing and that Rebuild Container, or `bash .devcontainer/install_ctx7.bash`, installs it (see "Context7 CLI（ctx7）" in `.devcontainer/README.md`). Do not run `npm install` yourself
- Do not switch to `npx ctx7`, a Context7 MCP server, the claude.ai Context7 connector, or the Pi Context7 extension (`resolve-library-id`, `query-docs`, `/c7-docs`). This repository uses Context7 only through `ctx7` in this skill
- If `ctx7` prints `Update available` or suggests `ctx7 upgrade` or `npm install -g ctx7@latest`, do not follow it. The user updates `ctx7` by rerunning `bash .devcontainer/install_ctx7.bash` or rebuilding the container
- Do not run `ctx7 setup` or `ctx7 remove`. They write MCP settings and skills to the shared `~/.claude`, `~/.codex`, and similar locations

A subagent without a shell (Bash or similar) cannot run `ctx7`. Ask the parent agent, or a worker with a shell, to fetch the documentation, passing the library name and the question. If that is not possible, say in the result that the documentation could not be fetched; do not silently answer from training data.

## Scope in this repository

This skill is the canonical Context7 procedure. The root `AGENTS.md` keeps only the rule not to switch away from `ctx7` and the limit of three commands per question, and points here.

- Use it for the specifications of libraries, frameworks, SDKs, APIs, CLIs, and cloud services.
- Do not use it for refactoring, business logic, or code review.
- When the user gives an ID in the `/org/project` form, skip `ctx7 library` and query `ctx7 docs` with that ID.

## Workflow

Two-step process: resolve the library name to an ID, then query docs with that ID.

```bash
# Step 1: Resolve library ID
ctx7 library <name> <query>

# Step 2: Query documentation
ctx7 docs <libraryId> <query>
```

You MUST call `ctx7 library` first to obtain a valid library ID UNLESS the user explicitly provides a library ID in the format `/org/project` or `/org/project/version`.

IMPORTANT: Do not run these commands more than 3 times per question. If you cannot find what you need after 3 attempts, use the best result you have.

## Step 1: Resolve a Library

Resolves a package/product name to a Context7-compatible library ID and returns matching libraries.

```bash
ctx7 library react "How to clean up useEffect with async operations"
ctx7 library nextjs "How to set up app router with middleware"
ctx7 library prisma "How to define one-to-many relations with cascade delete"
```

Always pass a `query` argument — it is required and directly affects result ranking. Use the user's intent to form the query, which helps disambiguate when multiple libraries share a similar name. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query.

### Result fields

Each result includes:

- **Library ID** — Context7-compatible identifier (format: `/org/project`)
- **Name** — Library or package name
- **Description** — Short summary
- **Code Snippets** — Number of available code examples
- **Source Reputation** — Authority indicator (High, Medium, Low, or Unknown)
- **Benchmark Score** — Quality indicator (100 is the highest score)
- **Versions** — List of versions if available. Use one of those versions if the user provides a version in their query. The format is `/org/project/version`.

### Selection process

1. Analyze the query to understand what library/package the user is looking for
2. Select the most relevant match based on:
   - Name similarity to the query (exact matches prioritized)
   - Description relevance to the query's intent
   - Documentation coverage (prioritize libraries with higher Code Snippet counts)
   - Source reputation (consider libraries with High or Medium reputation more authoritative)
   - Benchmark score (higher is better, 100 is the maximum)
3. If multiple good matches exist, acknowledge this but proceed with the most relevant one
4. If no good matches exist, clearly state this and suggest query refinements
5. For ambiguous queries, request clarification before proceeding with a best-guess match

### Version-specific IDs

If the user mentions a specific version, use a version-specific library ID:

```bash
# General (latest indexed)
ctx7 docs /vercel/next.js "How to set up app router"

# Version-specific
ctx7 docs /vercel/next.js/v14.3.0-canary.87 "How to set up app router"
```

The available versions are listed in the `ctx7 library` output. Use the closest match to what the user specified.

## Step 2: Query Documentation

Retrieves up-to-date documentation and code examples for the resolved library.

```bash
ctx7 docs /react/react "How to clean up useEffect with async operations"
ctx7 docs /vercel/next.js "How to add authentication middleware to app router"
ctx7 docs /prisma/orm "How to define one-to-many relations with cascade delete"
```

### Redirected library IDs

When a library ID has moved, `ctx7 docs` prints the new ID and exits with code 1:

```text
⚠ Library has been redirected
New ID: /react/react
Run: ctx7 docs "/react/react" "useEffect cleanup"
```

Retry once with the new ID. The retry counts toward the limit of three commands per question.

### Writing good queries

The query directly affects the quality of results. Be specific and include relevant details. Do not include any sensitive or confidential information such as API keys, passwords, credentials, personal data, or proprietary code in your query.

| Quality | Example |
|---------|---------|
| Good | `"How to set up authentication with JWT in Express.js"` |
| Good | `"React useEffect cleanup function with async operations"` |
| Bad | `"auth"` |
| Bad | `"hooks"` |

Use the user's full question as the query when possible, vague one-word queries return generic results.

The output contains two types of content: **code snippets** (titled, with language-tagged blocks) and **info snippets** (prose explanations with breadcrumb context).

## Authentication

Works without authentication. The environment variable `CONTEXT7_API_KEY` raises the rate limit; the user puts `CONTEXT7_API_KEY=<key>` in `~/.config/create-reso-world/env`, and the shell loads and exports it (see `.devcontainer/README.md`). When the variable is set, `ctx7` uses it ahead of `ctx7 login` credentials. Never print the key; check only whether it is set:

```bash
if [ -n "${CONTEXT7_API_KEY:-}" ]; then echo "CONTEXT7_API_KEY: set"; else echo "CONTEXT7_API_KEY: not set"; fi
```

`ctx7 whoami` shows only the `ctx7 login` state, so it prints `Not logged in.` even when `CONTEXT7_API_KEY` is in use.

The user runs `ctx7 login` themselves. It stores credentials in `~/.config/context7/credentials.json` (under `XDG_CONFIG_HOME` when that is an absolute path). This Dev Container does not bind-mount that directory, so a rebuild removes them.

## Error Handling

| Situation | Response |
|---|---|
| `command -v ctx7` prints nothing | Stop and point to the setup, as in the prerequisite section |
| `⚠ Library has been redirected` | Retry once with the new ID shown |
| `✖ Library "..." not found` | Resolve the ID again with `ctx7 library` |
| Quota error ("Monthly quota reached" or "quota exceeded") | The steps below |

If a command fails with a quota error:
1. Inform the user their Context7 quota is exhausted
2. Suggest they authenticate for higher limits: `CONTEXT7_API_KEY` in `~/.config/create-reso-world/env`, or `ctx7 login`
3. If they cannot or choose not to authenticate, answer from training knowledge and clearly note it may be outdated

Do not silently fall back to training data — always tell the user why Context7 was not used.

## Common Mistakes

- Library IDs require a `/` prefix — `/react/react` not `react/react`
- Always run `ctx7 library` first — `ctx7 docs react "hooks"` will fail without a valid ID
- Use descriptive queries, not single words — `"React useEffect cleanup function"` not `"hooks"`
- Do not include sensitive information (API keys, passwords, credentials) in queries
- Do not make up for a missing `ctx7` with `npx ctx7@latest` or `npm install -g ctx7@latest`; stop and point to the setup
