"""Settings dialog for global Codex Desk preferences."""

from __future__ import annotations

import wx

from codex_desk.preferences import (
    AppPreferences,
    PERSONALITIES,
    SPEAKER_LABEL_MODES,
    TranscriptPreferences,
)


SPEAKER_LABEL_DISPLAY = {
    "none": "No speaker labels",
    "role": "You / Assistant",
}


class SettingsDialog(wx.Dialog):
    """Native settings dialog for personality and transcript display."""

    def __init__(self, parent: wx.Window, preferences: AppPreferences) -> None:
        super().__init__(parent, title="Settings", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._preferences = preferences
        self._create_controls()
        self._populate(preferences)
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_preferences(self) -> AppPreferences:
        """Return preferences selected by the user."""
        return AppPreferences(
            personality=self._personality_choice.GetStringSelection(),
            transcript=TranscriptPreferences(
                speaker_labels=self._speaker_labels_choice.GetClientData(
                    self._speaker_labels_choice.GetSelection()
                ),
                show_tool_calls=self._show_tool_calls.GetValue(),
                show_reasoning=self._show_reasoning.GetValue(),
                show_diagnostics=self._show_diagnostics.GetValue(),
                show_file_summaries=self._show_file_summaries.GetValue(),
            ),
        )

    def _create_controls(self) -> None:
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        personality_label = wx.StaticText(panel, label="Agent personality:")
        self._personality_choice = wx.Choice(panel, choices=list(PERSONALITIES))

        transcript_box = wx.StaticBox(panel, label="Transcript")
        transcript_sizer = wx.StaticBoxSizer(transcript_box, wx.VERTICAL)
        speaker_labels_label = wx.StaticText(panel, label="Speaker labels:")
        self._speaker_labels_choice = wx.Choice(panel)
        for label_mode in SPEAKER_LABEL_MODES:
            self._speaker_labels_choice.Append(SPEAKER_LABEL_DISPLAY[label_mode], label_mode)
        self._show_tool_calls = wx.CheckBox(panel, label="Show tool calls")
        self._show_reasoning = wx.CheckBox(panel, label="Show reasoning summaries")
        self._show_diagnostics = wx.CheckBox(panel, label="Show Codex diagnostics")
        self._show_file_summaries = wx.CheckBox(panel, label="Show concise file summaries")
        transcript_sizer.Add(speaker_labels_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=4)
        transcript_sizer.Add(self._speaker_labels_choice, flag=wx.EXPAND | wx.ALL, border=4)
        transcript_sizer.Add(self._show_tool_calls, flag=wx.ALL, border=4)
        transcript_sizer.Add(self._show_reasoning, flag=wx.ALL, border=4)
        transcript_sizer.Add(self._show_diagnostics, flag=wx.ALL, border=4)
        transcript_sizer.Add(self._show_file_summaries, flag=wx.ALL, border=4)

        sizer.Add(personality_label, flag=wx.LEFT | wx.RIGHT | wx.TOP, border=8)
        sizer.Add(self._personality_choice, flag=wx.EXPAND | wx.ALL, border=8)
        sizer.Add(transcript_sizer, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=8)

        buttons = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)
        sizer.Add(buttons, flag=wx.EXPAND | wx.ALL, border=8)

        panel.SetSizer(sizer)

    def _populate(self, preferences: AppPreferences) -> None:
        self._personality_choice.SetStringSelection(preferences.personality)
        self._speaker_labels_choice.SetStringSelection(
            SPEAKER_LABEL_DISPLAY[preferences.transcript.speaker_labels]
        )
        self._show_tool_calls.SetValue(preferences.transcript.show_tool_calls)
        self._show_reasoning.SetValue(preferences.transcript.show_reasoning)
        self._show_diagnostics.SetValue(preferences.transcript.show_diagnostics)
        self._show_file_summaries.SetValue(preferences.transcript.show_file_summaries)
