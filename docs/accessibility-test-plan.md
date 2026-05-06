# wxAgent Accessibility Test Plan

## Main Window

Test with keyboard first, then NVDA Speech Viewer or Narrator.

- `Tab` reaches the model combo box. Expected announcement: "Model, combo box" with the selected
  model value.
- `Tab` reaches the reasoning effort choice. Expected announcement: "Reasoning effort, combo box"
  with the selected effort.
- `Tab` reaches the transcript. Expected announcement: "Conversation transcript, edit, read only".
- `Tab` moves from the transcript to the turn-details field. Expected announcement:
  "Turn details, edit, read only" with the current status plus the current or last model and
  reasoning effort.
- `Tab` reaches the prompt field. Expected announcement: "Prompt, edit".
- Changing model or reasoning effort updates the next Codex turn without moving focus unexpectedly.
- Changing model refreshes the reasoning effort choices to the values Codex reports for that model.
- Submitting a prompt updates the labeled turn-status row and status bar to elapsed text such as
  "Working for 3 seconds" until the turn finishes.
- Submitting a prompt updates the labeled turn-details row with the model and reasoning effort for
  the current turn plus the live status such as "Working for 3 seconds"; after completion it
  remains visible as the last turn details with status "Idle".
- Working status and other process state do not appear in the conversation transcript by default.

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
- The speaker labels combo box is labeled "Speaker labels" and defaults to "No speaker labels".
- Tool-call and reasoning transcript detail are opt-in.

## Tools Dialogs

- `Tools -> Slash Commands` or `Ctrl+/` opens a native command palette. Expected first focus:
  "Command search, edit".
- In the slash command palette, `Tab` reaches the command list, command details, Run, Insert, and
  Cancel controls. The command list announces each command name with its description.
- Running a slash command performs the same action as the matching menu item. Inserting a slash
  command returns focus to the prompt with the command text inserted.
- Typing a known command such as `/settings` in the prompt and pressing `Enter` runs the local UI
  command without sending text to Codex. Typing an unknown command preserves the prompt text and
  reports "Unknown slash command" in status.
- Typing `//settings` sends a literal `/settings` prompt to Codex.
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
