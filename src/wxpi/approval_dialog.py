"""Tool approval dialog — shown when Pi requests tool execution approval."""
import json

import wx

from wxpi.rpc_events import ConfirmEvent


class ToolApprovalDialog(wx.Dialog):
    """Dialog shown when Pi requires approval to execute a tool.

    Per ARCH §16 and §18:
    - Shows tool name, args, and working directory
    - Deny button has default focus (safe default)
    - Escape key denies
    - Enter key allows when Allow is focused
    - "Allow All Session" adds to allow-list (bash is never allowed)
    """

    def __init__(
        self,
        parent: wx.Window,
        event: ConfirmEvent,
    ) -> None:
        self._confirm_event = event
        self._allow_all = False

        # Dialog title per ARCH spec
        super().__init__(
            parent,
            wx.ID_ANY,
            "Tool Execution Requires Approval",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self._create_ui()
        self._bind_events()

        # Center on parent
        self.CenterOnParent()

    def _create_ui(self) -> None:
        """Create the dialog UI."""
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Title announcement (for screen readers)
        title = wx.StaticText(
            self,
            wx.ID_ANY,
            "Tool execution requires approval",
            style=wx.ALIGN_CENTER,
        )
        title.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, flag=wx.BOTTOM, border=15)

        # Tool name
        tool_label = wx.StaticText(self, wx.ID_ANY, f"Tool: {self._confirm_event.tool}")
        tool_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(tool_label, flag=wx.BOTTOM, border=10)

        # Command/args in monospaced read-only text
        args_label = wx.StaticText(self, wx.ID_ANY, "Arguments:")
        sizer.Add(args_label, flag=wx.BOTTOM, border=5)

        # Format args for display
        args_text = self._format_args(self._confirm_event.args)
        self._args_ctrl = wx.TextCtrl(
            self,
            wx.ID_ANY,
            args_text,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(400, 100),
        )
        # Set monospace font
        font = wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self._args_ctrl.SetFont(font)
        sizer.Add(self._args_ctrl, flag=wx.EXPAND | wx.BOTTOM, border=10)

        # Working directory
        cwd_label = wx.StaticText(
            self,
            wx.ID_ANY,
            f"Working directory: {self._confirm_event.cwd}",
        )
        cwd_label.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(cwd_label, flag=wx.BOTTOM, border=15)

        # Buttons (per ARCH spec)
        button_sizer = wx.StdDialogButtonSizer()

        # Deny button (default, safe) — Escape triggers this
        deny_btn = wx.Button(self, wx.ID_NO, "Deny")
        deny_btn.SetName("Deny (Escape)")
        button_sizer.AddButton(deny_btn)

        # Allow button — Enter triggers this when focused
        allow_btn = wx.Button(self, wx.ID_YES, "Allow")
        allow_btn.SetName("Allow (Enter)")
        button_sizer.AddButton(allow_btn)

        # Allow All Session button — tab-reachable, bash excluded
        if self._confirm_event.tool != "bash":
            self._allow_all_btn = wx.Button(self, wx.ID_ANY, "Allow all (this session)")
            self._allow_all_btn.SetName("Allow all this session")
            button_sizer.AddButton(self._allow_all_btn)

        button_sizer.Realize()

        # Set Deny as default (safe default per ARCH)
        deny_btn.SetDefault()

        sizer.Add(button_sizer, flag=wx.ALIGN_RIGHT | wx.TOP, border=10)

        self.SetSizer(sizer)
        sizer.Fit(self)

        # Set minimum size
        self.SetMinSize((450, 250))
        
        # Steal focus per ARCH §6.5
        self.SetFocus()

    def _format_args(self, args) -> str:
        """Format args for display in the text control."""
        if args is None:
            return "(none)"
        if isinstance(args, str):
            return args
        if isinstance(args, dict):
            # Pretty-print dict args
            return json.dumps(args, indent=2)
        if isinstance(args, list):
            return "\n".join(str(a) for a in args)
        return str(args)

    def _bind_events(self) -> None:
        """Bind keyboard events."""
        # Escape key = Deny
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        
        # Allow All button click
        if self._confirm_event.tool != "bash":
            self.Bind(wx.EVT_BUTTON, self._on_allow_all, self._allow_all_btn)

    def _on_key_down(self, event: wx.KeyEvent) -> None:
        """Handle key events."""
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_ESCAPE:
            # Escape = Deny
            self.EndModal(wx.ID_NO)
        else:
            event.Skip()

    def _on_allow_all(self, event: wx.CommandEvent) -> None:
        """Handle Allow All button click."""
        self._allow_all = True
        self.EndModal(wx.ID_YES)

    def GetAllowAll(self) -> bool:
        """Return whether user selected 'Allow all (this session)'."""
        return self._allow_all
