---
name: n8n-workflows
description: >-
  Build and update n8n workflows via MCP with clear canvas layout. Use when
  creating or modifying n8n workflows, adding nodes or branches, or working
  with user-n8n-mcp on n8n.bentenberge.com.
---

# n8n Workflows

Instance: `https://n8n.bentenberge.com`. Inventory and credentials in `ops/raspberry-pi/context.md`. Tool split (MCP vs REST API) in `.cursor/rules/n8n-raspberry-pi.mdc`.

## Canvas layout

Spend some time assessing the placement of any new nodes and branches so that it doesn't overlap with existing ones and the workflow canvas remains visually clear and unjumbled.

Before adding or moving nodes:

1. Call `get_workflow_details` and note existing `position` values on all nodes.
2. Place new nodes with clear separation — main flow left-to-right; branch paths on different Y levels.
3. Set coordinates via `position: [x, y]` on `addNode`, or `setNodePosition` after adding.
4. Do not reposition nodes the user has already arranged unless they ask.

Rough spacing: ~200px horizontal between sequential nodes; ~150px+ vertical between parallel branches.

## Build pipeline (MCP)

1. `get_sdk_reference` — read SDK patterns first
2. `search_nodes` / `get_node_types` — exact parameter names; never guess
3. `update_workflow` — one operation per call if batches fail
4. `publish_workflow` — draft changes are not live until published

Credentials: assign via MCP when possible; token creds via REST API (`N8N_API_KEY` in `ops/raspberry-pi/.env`). OAuth (Google Calendar) requires n8n UI.

## Gotchas

- **Filesystem binary mode**: `$binary.data.data` is not base64 — use a Code node with `getBinaryDataBuffer()` before APIs that expect inline audio.
- **Intermediate nodes drop fields**: if a node replaces `$json` (e.g. Telegram send), reference upstream Set nodes by name in expressions rather than `$json.field`.
- **IF branches**: wire both outputs; output 0 = true, output 1 = false.
