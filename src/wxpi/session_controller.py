"""SessionController — wires Codex events to the wx UI."""
import os
from typing import Optional

import wx

from wxpi.approval_dialog import ToolApprovalDialog
from wxpi.codex_app_server_bridge import CodexAppServerBridge
from wxpi.preferences import AppPreferences, ThreadOptions
from wxpi.rpc_events import (
    AgentEndEvent,
    AgentStartEvent,
    ConfirmEvent,
    DiagnosticEvent,
    FileChangeSummaryEvent,
    MessageUpdateEvent,
    parse_event,
    ReasoningUpdateEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from wxpi.transcript import format_file_summary, should_show_event


class SessionController:
    """Owns the Codex bridge and dispatches events to the UI.

    All bridge callbacks run on a background thread. This class
    dispatches all UI updates via wx.CallAfter() to ensure thread safety.
    """

    def __init__(self, main_frame) -> None:
        self._main_frame = main_frame
        self._bridge: Optional[CodexAppServerBridge] = None
        self._allow_list: set[str] = set()  # Per-session allow-list for tools
        self._current_tool: Optional[str] = None  # Track current tool for block rendering
        self._preferences = AppPreferences()
        self._thread_options = ThreadOptions()

    def set_preferences(self, preferences: AppPreferences) -> None:
        """Apply transcript preferences for future bridge events."""
        self._preferences = preferences

    def set_thread_options(self, thread_options: ThreadOptions) -> None:
        """Apply thread options for future turns and sessions."""
        self._thread_options = thread_options
        if self._bridge:
            self._bridge.set_thread_options(thread_options)

    def new_session(
        self,
        cwd: str,
        preferences: AppPreferences | None = None,
        thread_options: ThreadOptions | None = None,
    ) -> None:
        """Start a new session in the given working directory."""
        self._stop_bridge()
        self._allow_list.clear()
        self._preferences = preferences or self._preferences
        self._thread_options = thread_options or self._thread_options
        self._bridge = CodexAppServerBridge()
        self._bridge.on_event(self._on_event)
        self._bridge.on_process_exit(self._on_process_exit)
        self._bridge.start(
            cwd=cwd,
            preferences=self._preferences,
            thread_options=self._thread_options,
        )
        self._main_frame.set_turn_status("Idle")

    def continue_session(self, session_path: str) -> None:
        """Continue an existing session from the given session file path."""
        self._stop_bridge()
        self._allow_list.clear()
        cwd = os.path.dirname(os.path.dirname(session_path))
        self._bridge = CodexAppServerBridge()
        self._bridge.on_event(self._on_event)
        self._bridge.on_process_exit(self._on_process_exit)
        self._bridge.start(
            cwd=cwd,
            session_path=session_path,
            continue_session=True,
            preferences=self._preferences,
            thread_options=self._thread_options,
        )

    def send_prompt(self, text: str) -> None:
        """Send a prompt to Codex."""
        if self._bridge:
            self._main_frame.set_turn_status("Thinking...")
            self._main_frame.append_transcript(f"\nYou: {text}\n\n")
            self._bridge.send_prompt(text)

    def send_abort(self) -> None:
        """Send an abort command to Pi."""
        if self._bridge:
            self._bridge.send_abort()

    def _stop_bridge(self) -> None:
        """Stop the current PiBridge if any."""
        if self._bridge:
            self._bridge.stop()
            self._bridge = None

    # ------------------------------------------------------------------
    # Bridge callbacks (run on background thread)
    # ------------------------------------------------------------------

    def _on_event(self, raw_event: dict) -> None:
        """Handle an incoming Codex event from the background thread."""
        if not should_show_event(raw_event.get("type", ""), self._preferences.transcript):
            return

        event = parse_event(raw_event)

        # Dispatch to the appropriate handler via CallAfter for thread safety
        if isinstance(event, AgentStartEvent):
            wx.CallAfter(self._on_agent_start, event)
        elif isinstance(event, AgentEndEvent):
            wx.CallAfter(self._on_agent_end, event)
        elif isinstance(event, TurnStartEvent):
            wx.CallAfter(self._on_turn_start, event)
        elif isinstance(event, TurnEndEvent):
            wx.CallAfter(self._on_turn_end, event)
        elif isinstance(event, MessageUpdateEvent):
            wx.CallAfter(self._on_message_update, event)
        elif isinstance(event, ReasoningUpdateEvent):
            wx.CallAfter(self._on_reasoning_update, event)
        elif isinstance(event, FileChangeSummaryEvent):
            wx.CallAfter(self._on_file_change_summary, event)
        elif isinstance(event, ToolExecutionStartEvent):
            wx.CallAfter(self._on_tool_execution_start, event)
        elif isinstance(event, ToolExecutionEndEvent):
            wx.CallAfter(self._on_tool_execution_end, event)
        elif isinstance(event, ConfirmEvent):
            wx.CallAfter(self._on_confirm, event)
        elif isinstance(event, DiagnosticEvent):
            wx.CallAfter(self._on_diagnostic, event)
        else:
            # Unknown event type - log it but don't crash
            wx.CallAfter(self._main_frame.append_transcript, f"\n[Unknown event: {raw_event.get('type', '?')}]\n")

    def _on_process_exit(self) -> None:
        """Handle Codex process exit."""
        wx.CallAfter(self._main_frame.set_turn_status, "Disconnected")
        wx.CallAfter(self._main_frame.append_transcript, "\n[Codex process exited]\n")

    # ------------------------------------------------------------------
    # Event handlers (run on main wx thread via CallAfter)
    # ------------------------------------------------------------------

    def _on_agent_start(self, event: AgentStartEvent) -> None:
        """Handle agent_start event."""
        self._main_frame.set_model(event.model)
        self._main_frame.set_turn_status("Thinking...")

    def _on_agent_end(self, event: AgentEndEvent) -> None:
        """Handle agent_end event."""
        self._main_frame.set_turn_status("Idle")
        self._main_frame.get_input_focus()

    def _on_turn_start(self, event: TurnStartEvent) -> None:
        """Handle turn_start event."""
        self._main_frame.append_transcript("\nAssistant: ")

    def _on_turn_end(self, event: TurnEndEvent) -> None:
        """Handle turn_end event."""
        self._main_frame.append_transcript("\n")

    def _on_message_update(self, event: MessageUpdateEvent) -> None:
        """Handle message_update event (streaming text)."""
        self._main_frame.append_transcript(event.delta)

    def _on_reasoning_update(self, event: ReasoningUpdateEvent) -> None:
        """Handle optional reasoning transcript text."""
        self._main_frame.append_transcript(f"\n[Reasoning: {event.delta}]\n")

    def _on_file_change_summary(self, event: FileChangeSummaryEvent) -> None:
        """Handle concise file change summaries."""
        summary = format_file_summary(
            created=event.created,
            edited=event.edited,
            deleted=event.deleted,
        )
        self._main_frame.append_transcript(f"\n{summary}\n")

    def _on_diagnostic(self, event: DiagnosticEvent) -> None:
        """Handle bridge diagnostics without surfacing expected Codex noise."""
        if event.severity == "debug":
            return
        self._main_frame.append_transcript(f"\n[Codex warning: {event.message}]\n")

    def _on_tool_execution_start(self, event: ToolExecutionStartEvent) -> None:
        """Handle tool_execution_start event."""
        self._current_tool = event.tool
        self._main_frame.append_transcript(f"\n[TOOL: {event.tool} | RUNNING]\n")

    def _on_tool_execution_end(self, event: ToolExecutionEndEvent) -> None:
        """Handle tool_execution_end event."""
        status_str = "DONE" if event.status == "success" else f"FAILED (exit {event.exit_code})"
        self._main_frame.append_transcript(f"\n[TOOL: {self._current_tool} | {status_str}]\n")
        self._current_tool = None

    def _on_confirm(self, event: ConfirmEvent) -> None:
        """Handle confirm event (tool approval request)."""
        # Check if tool is in allow-list (bash is never allowed per ARCH)
        if event.tool in self._allow_list and event.tool != "bash":
            # Auto-approve
            self._bridge.send_ui_response(event.id, True)
            self._main_frame.append_transcript(f"\n[Auto-approved: {event.tool}]\n")
            return

        # Show approval dialog
        self._main_frame.append_transcript(f"\n[Tool approval needed: {event.tool}]\n")
        
        # Get the parent window for the dialog
        parent = self._main_frame
        
        # Show the dialog (modal - blocks until user responds)
        dialog = ToolApprovalDialog(parent, event)
        result = dialog.ShowModal()
        allow_all = dialog.GetAllowAll()
        dialog.Destroy()
        
        if result == wx.ID_YES:
            # User clicked Allow or Allow All
            self._bridge.send_ui_response(event.id, True)
            
            # If Allow All was selected and tool is not bash, add to allow-list
            if allow_all and event.tool != "bash":
                self._allow_list.add(event.tool)
                self._main_frame.append_transcript(f"\n[Added {event.tool} to session allow-list]\n")
        else:
            # User clicked Deny or pressed Escape
            self._bridge.send_ui_response(event.id, False)
            self._main_frame.append_transcript(f"\n[Tool {event.tool} denied]\n")
