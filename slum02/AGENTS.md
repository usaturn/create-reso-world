# ResoLoop project guide

Use `resoloop` as the only mutation interface for Resonite content in this project. Use the project skills under `.agents/skills/` for the requested workflow. If no connection URL is configured, follow resonite-build's automatic discovery workflow: discover first, connect if there is one candidate, or ask the user to choose if there are multiple. Run `resoloop doctor --json` with the selected URL before world work.

## Required workflow

- Inspect unfamiliar Component types, members, methods, and Flux nodes through Reflection or Flux-SDK metadata. Never guess runtime names.
- Before mutation, review `diff --brief` targets and reasons. Diff already includes offline and runtime Reflection validation; standalone validate is for offline authoring or diagnosis. Apply repeats preflight. Re-run the same apply and confirm it converges without writes.
- Keep declarative content in `content/`, ProtoGraph source in `flux/`, and session state under `.resoloop/`.
- Prefer stable selectors such as `$slot:key`, `$component:key`, and `$member:key.Member`; pass `--state` after reconnecting.

## Resonite safety

- Never delete or mutate `Root`, an unverified ID, or existing user content outside the requested ownership boundary.
- Put experiments below an unmistakable `ResoLoop_Test_*` Slot and clean only its exact verified ID.
- Review delete candidates before `--prune --yes`. Slot delete and Component remove always require explicit `--yes`.
- Treat ResoniteLink IDs as session-scoped and re-observe after a session restart.
