"""Profile selection dialog for optional wxAgent capability packs."""

from __future__ import annotations

import wx

from wxpi.profiles import AgentProfile, list_profiles


class ProfileDialog(wx.Dialog):
    """Show the built-in and optional agent profiles."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, wx.ID_ANY, "Agent Profiles", size=(560, 420))
        self._profiles = list_profiles()
        self._create_ui()
        self.CentreOnParent()

    def _create_ui(self) -> None:
        sizer = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, wx.ID_ANY, "Agent Profiles")
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, flag=wx.ALL, border=12)

        choices = [self._choice_label(profile) for profile in self._profiles]
        self._profile_radio = wx.RadioBox(
            self,
            wx.ID_ANY,
            "Select a profile:",
            choices=choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._profile_radio.SetSelection(0)
        self.Bind(wx.EVT_RADIOBOX, self._on_select_profile, self._profile_radio)
        sizer.Add(self._profile_radio, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        details_label = wx.StaticText(self, wx.ID_ANY, "Profile details:")
        sizer.Add(details_label, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        self._details = wx.TextCtrl(
            self,
            wx.ID_ANY,
            style=wx.TE_MULTILINE | wx.TE_READONLY,
            size=(-1, 120),
        )
        self._details.SetToolTip("Selected profile details")
        sizer.Add(self._details, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)

        close_btn = wx.Button(self, wx.ID_OK, "Close")
        sizer.Add(close_btn, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=12)

        self.SetSizer(sizer)
        self._update_details()

    def _on_select_profile(self, event: wx.CommandEvent) -> None:
        self._update_details()

    def _update_details(self) -> None:
        profile = self._profiles[self._profile_radio.GetSelection()]
        lines = [profile.name, "", profile.description]
        if profile.installed_by_default:
            lines.extend(["", "Installed by default."])
        else:
            lines.extend(["", "Optional install steps:"])
            lines.extend(f"- {step}" for step in profile.install_steps)
        self._details.SetValue("\n".join(lines))

    @staticmethod
    def _choice_label(profile: AgentProfile) -> str:
        suffix = "default" if profile.installed_by_default else "optional"
        return f"{profile.name} ({suffix})"
