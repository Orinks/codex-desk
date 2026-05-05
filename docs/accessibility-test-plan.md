# wxAgent Accessibility Test Plan

## Main Window

Test with keyboard first, then NVDA Speech Viewer or Narrator.

- `Tab` reaches the model combo box. Expected announcement: "Model, combo box" with the selected
  model value.
- `Tab` reaches the reasoning effort choice. Expected announcement: "Reasoning effort, combo box"
  with the selected effort.
- `Tab` reaches the transcript. Expected announcement: "Conversation transcript, edit, read only".
- `Tab` reaches the prompt field. Expected announcement: "Prompt, edit".
- Changing model or reasoning effort updates the next Codex turn without moving focus unexpectedly.

## New Session and Change Workspace

- `File -> New Session` and `File -> Change Workspace` open the same labeled session options dialog.
- `Tab` order follows: workspace folder, model, reasoning effort, workspace mode, base branch,
  sandbox, approval policy, approval reviewer, OK, Cancel.
- Model is a combo box populated from Codex's local model cache, including `codex-auto-review`
  when the cache reports it.
- Approval reviewer includes `user` and `auto_review`. This is separate from the sandbox selector.
- Sandbox defaults to `workspace-write`; full access is available but not required for auto-review.

## Settings

- `Edit -> Settings` exposes personality and transcript options with visible labels or checkbox
  labels.
- Tool-call and reasoning transcript detail are opt-in.

## Tools Dialogs

- `Tools -> MCP Servers` lists configured MCP servers with columns for name, type, target, status,
  and auth.
- `Tools -> Codex Plugins` lists configured plugins and marketplaces.
- Add dialogs use visible `StaticText` labels immediately before each edit box.

## Release Gate

- Run a keyboard-only pass.
- Run NVDA with Speech Viewer open and record any missing name, wrong role, or unexpected focus jump.
- Run Narrator as a second smoke test on Windows.
- Use Accessibility Insights for Windows Live Inspect on the main model, reasoning, transcript, and
  prompt controls.
