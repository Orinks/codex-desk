"""New session dialog for Codex thread options."""

from __future__ import annotations

import wx

from wxpi.codex_models import load_model_choices
from wxpi.preferences import (
    APPROVAL_POLICIES,
    APPROVAL_REVIEWERS,
    REASONING_EFFORTS,
    SANDBOX_MODES,
    THREAD_MODES,
    ThreadOptions,
)
from wxpi.worktrees import current_branch, list_branches


class NewSessionDialog(wx.Dialog):
    """Collect workspace and Codex thread options."""

    def __init__(self, parent: wx.Window, cwd: str, options: ThreadOptions) -> None:
        super().__init__(parent, title="New Session", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._initial_cwd = cwd
        self._options = options
        self._create_controls()
        self._populate(cwd, options)
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_cwd(self) -> str:
        """Return selected working directory."""
        return self._cwd_picker.GetPath()

    def get_thread_options(self) -> ThreadOptions:
        """Return selected Codex thread options."""
        base_branch = self._base_branch_choice.GetStringSelection().strip() or None
        return ThreadOptions(
            model=self._model_choice.GetStringSelection().strip() or self._options.model,
            reasoning_effort=self._reasoning_choice.GetStringSelection(),
            sandbox=self._sandbox_choice.GetStringSelection(),
            approval_policy=self._approval_choice.GetStringSelection(),
            approvals_reviewer=self._reviewer_choice.GetStringSelection(),
            mode=self._mode_choice.GetStringSelection(),
            base_branch=base_branch,
        )

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        model_choices = _model_choices_with_current(self._options.model)

        cwd_label = wx.StaticText(panel, label="Workspace folder:")
        self._cwd_picker = wx.DirPickerCtrl(panel, message="Choose a workspace folder")

        model_label = wx.StaticText(panel, label="Model:")
        self._model_choice = wx.Choice(panel, choices=model_choices)

        reasoning_label = wx.StaticText(panel, label="Reasoning effort:")
        self._reasoning_choice = wx.Choice(panel, choices=list(REASONING_EFFORTS))

        mode_label = wx.StaticText(panel, label="Workspace mode:")
        self._mode_choice = wx.Choice(panel, choices=list(THREAD_MODES))
        self._mode_choice.Bind(wx.EVT_CHOICE, self._on_mode_changed)

        branch_label = wx.StaticText(panel, label="Base branch for worktree:")
        self._base_branch_choice = wx.Choice(panel)

        sandbox_label = wx.StaticText(panel, label="Sandbox:")
        self._sandbox_choice = wx.Choice(panel, choices=list(SANDBOX_MODES))

        approval_label = wx.StaticText(panel, label="Approval policy:")
        self._approval_choice = wx.Choice(panel, choices=list(APPROVAL_POLICIES))

        reviewer_label = wx.StaticText(panel, label="Approval reviewer:")
        self._reviewer_choice = wx.Choice(panel, choices=list(APPROVAL_REVIEWERS))

        for label, control in (
            (cwd_label, self._cwd_picker),
            (model_label, self._model_choice),
            (reasoning_label, self._reasoning_choice),
            (mode_label, self._mode_choice),
            (branch_label, self._base_branch_choice),
            (sandbox_label, self._sandbox_choice),
            (approval_label, self._approval_choice),
            (reviewer_label, self._reviewer_choice),
        ):
            sizer.Add(label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
            sizer.Add(control, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)
        panel.SetSizer(sizer)

    def _populate(self, cwd: str, options: ThreadOptions) -> None:
        self._cwd_picker.SetPath(cwd)
        self._model_choice.SetStringSelection(options.model)
        self._reasoning_choice.SetStringSelection(options.reasoning_effort)
        self._mode_choice.SetStringSelection(options.mode)
        self._sandbox_choice.SetStringSelection(options.sandbox)
        self._approval_choice.SetStringSelection(options.approval_policy)
        self._reviewer_choice.SetStringSelection(options.approvals_reviewer)
        self._populate_branches(cwd, options.base_branch)
        self._sync_branch_enabled()

    def _populate_branches(self, cwd: str, selected_branch: str | None) -> None:
        try:
            branches = list_branches(cwd)
        except Exception:
            branches = []
        if not branches:
            try:
                branches = [current_branch(cwd)]
            except Exception:
                branches = ["HEAD"]
        self._base_branch_choice.Set(branches)
        self._base_branch_choice.SetStringSelection(selected_branch or branches[0])

    def _on_mode_changed(self, event: wx.CommandEvent) -> None:
        self._sync_branch_enabled()
        event.Skip()

    def _sync_branch_enabled(self) -> None:
        self._base_branch_choice.Enable(self._mode_choice.GetStringSelection() == "worktree")


def _model_choices_with_current(current_model: str) -> list[str]:
    choices = load_model_choices()
    if current_model not in choices:
        choices.insert(0, current_model)
    return choices
