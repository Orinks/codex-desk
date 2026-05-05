# Recommendation

Build it, but keep the first version narrow.

The best product shape is not "a new coding agent." It is a native accessible control plane for
Codex: transcript, prompt input, approvals, diffs, status, sessions, and optional workflow profiles.

## Why This Is Worth Building

- Codex already supplies the agent backend and user authentication.
- wxPython gives screen reader users a better starting point than a terminal TUI or Electron shell.
- A native approval/review surface can be meaningfully better for keyboard and screen reader users.
- Optional profiles let power users add workflows without making the default experience strange.

## Main Risks

- Competing with official Codex surfaces instead of complementing them.
- Depending on unstable app-server protocol details without tests.
- Letting optional "superpowers" complicate the first-run experience.
- Assuming OpenAI speech can be free; it should remain optional and separate from core accessibility.

## MVP Scope

1. Open a workspace.
2. Start a Codex thread.
3. Send prompts.
4. Stream readable output.
5. Surface approvals accessibly.
6. Let users inspect optional profiles without installing them by surprise.

That is enough to prove the product.
