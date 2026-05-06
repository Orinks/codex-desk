"""Provider management panel for configuring AI providers."""
import json
import os
import subprocess

import wx

# List of all supported providers and their info
PROVIDERS = [
    {
        "id": "anthropic",
        "name": "Anthropic (Claude)",
        "description": "Claude Pro/Max subscription",
        "auth_type": "oauth",
        "env_key": "ANTHROPIC_API_KEY",
    },
    {
        "id": "openai",
        "name": "OpenAI (ChatGPT)",
        "description": "ChatGPT Plus/Pro subscription",
        "auth_type": "oauth",
        "env_key": "OPENAI_API_KEY",
    },
    {
        "id": "google",
        "name": "Google (Gemini)",
        "description": "Gemini CLI or Google AI",
        "auth_type": "oauth",
        "env_key": "GEMINI_API_KEY",
    },
    {
        "id": "github-copilot",
        "name": "GitHub Copilot",
        "description": "Copilot subscription",
        "auth_type": "oauth",
        "env_key": None,
    },
    {
        "id": "azure",
        "name": "Azure OpenAI",
        "description": "Azure OpenAI Service",
        "auth_type": "api_key",
        "env_key": "AZURE_OPENAI_API_KEY",
    },
    {
        "id": "amazon-bedrock",
        "name": "Amazon Bedrock",
        "description": "AWS Bedrock (Claude, Llama, etc.)",
        "auth_type": "aws",
        "env_key": None,
    },
    {
        "id": "mistral",
        "name": "Mistral",
        "description": "Mistral AI",
        "auth_type": "api_key",
        "env_key": "MISTRAL_API_KEY",
    },
    {
        "id": "groq",
        "name": "Groq",
        "description": "Groq (fast inference)",
        "auth_type": "api_key",
        "env_key": "GROQ_API_KEY",
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "description": "Unified access to many models",
        "auth_type": "api_key",
        "env_key": "OPENROUTER_API_KEY",
    },
    {
        "id": "ollama",
        "name": "Ollama",
        "description": "Local models",
        "auth_type": "local",
        "env_key": None,
    },
]


def get_auth_file_path() -> str:
    """Get the path to Pi's auth.json file."""
    return os.path.expanduser("~/.pi/agent/auth.json")


def check_provider_status() -> dict:
    """Check which providers are configured.
    
    Returns dict of provider_id -> status info.
    """
    status = {}
    
    # Check auth.json for OAuth tokens
    auth_path = get_auth_file_path()
    oauth_providers = set()
    if os.path.exists(auth_path):
        try:
            with open(auth_path, 'r') as f:
                auth_data = json.load(f)
                # Check for various OAuth token types
                for key in auth_data.get("tokens", {}).keys():
                    if "anthropic" in key.lower():
                        oauth_providers.add("anthropic")
                    if "openai" in key.lower() or "chatgpt" in key.lower():
                        oauth_providers.add("openai")
                    if "google" in key.lower() or "gemini" in key.lower():
                        oauth_providers.add("google")
                    if "github" in key.lower() or "copilot" in key.lower():
                        oauth_providers.add("github-copilot")
        except (json.JSONDecodeError, IOError):
            pass
    
    # Check environment variables for API keys
    api_key_providers = set()
    for provider in PROVIDERS:
        if provider["env_key"] and os.environ.get(provider["env_key"]):
            api_key_providers.add(provider["id"])
    
    # Build status dict
    for provider in PROVIDERS:
        provider_id = provider["id"]
        if provider_id in oauth_providers:
            status[provider_id] = {"type": "oauth", "configured": True}
        elif provider_id in api_key_providers:
            status[provider_id] = {"type": "api_key", "configured": True}
        else:
            status[provider_id] = {"type": provider["auth_type"], "configured": False}
    
    return status


class ProviderPanel(wx.Panel):
    """Panel for managing AI providers."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent, wx.ID_ANY)
        
        self._provider_status = check_provider_status()
        self._create_ui()

    def _create_ui(self) -> None:
        """Create the UI elements with accessibility in mind."""
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(
            self,
            wx.ID_ANY,
            "AI Provider Configuration",
            style=wx.ALIGN_CENTER,
        )
        title.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, flag=wx.BOTTOM | wx.TOP, border=15)
        
        # Instructions
        instructions = wx.StaticText(
            self,
            wx.ID_ANY,
            "Choose a provider, then click Configure or Remove.\n"
            "OAuth requires browser login. API key needs a key.",
            style=wx.ALIGN_CENTER,
        )
        sizer.Add(instructions, flag=wx.BOTTOM, border=10)
        
        # Refresh button with keyboard shortcut hint
        self._refresh_btn = wx.Button(self, wx.ID_ANY, "Refresh Status (F5)")
        self._refresh_btn.SetName("Refresh provider status")
        self.Bind(wx.EVT_BUTTON, self._on_refresh, self._refresh_btn)
        sizer.Add(self._refresh_btn, flag=wx.BOTTOM, border=10)
        
        # Provider selection using RadioBox for better accessibility
        # RadioBox provides better screen reader support than ListBox
        provider_choices = []
        for provider in PROVIDERS:
            prov_status = self._provider_status.get(provider["id"], {})
            if prov_status.get("configured"):
                status_str = "configured"
            else:
                status_str = "not configured"
            provider_choices.append(f"{provider['name']} ({status_str})")
        
        self._provider_radio = wx.RadioBox(
            self,
            wx.ID_ANY,
            "Select a provider:",
            choices=provider_choices,
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self._provider_radio.SetName("Provider selection")
        sizer.Add(self._provider_radio, proportion=1, flag=wx.EXPAND | wx.BOTTOM, border=10)
        
        # Bind selection event
        self.Bind(wx.EVT_RADIOBOX, self._on_select_provider, self._provider_radio)
        
        # Status display
        self._status_text = wx.StaticText(
            self,
            wx.ID_ANY,
            "Select a provider to see details.",
            style=wx.ALIGN_LEFT,
        )
        self._status_text.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sizer.Add(self._status_text, flag=wx.BOTTOM, border=10)
        
        # Action buttons with keyboard shortcut hints
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self._configure_btn = wx.Button(self, wx.ID_ANY, "Configure (Enter)")
        self._configure_btn.SetName("Configure selected provider")
        self.Bind(wx.EVT_BUTTON, self._on_configure, self._configure_btn)
        button_sizer.Add(self._configure_btn, flag=wx.RIGHT, border=10)
        
        self._remove_btn = wx.Button(self, wx.ID_ANY, "Remove (Delete)")
        self._remove_btn.SetName("Remove provider configuration")
        self.Bind(wx.EVT_BUTTON, self._on_remove, self._remove_btn)
        button_sizer.Add(self._remove_btn)
        
        sizer.Add(button_sizer, flag=wx.ALIGN_RIGHT)
        
        self.SetSizer(sizer)
        
        # Set initial status text
        self._update_status_text()

    def _update_provider_list(self) -> None:
        """Update the provider radio box with current status."""
        provider_choices = []
        for provider in PROVIDERS:
            prov_status = self._provider_status.get(provider["id"], {})
            if prov_status.get("configured"):
                status_str = "configured"
            else:
                status_str = "not configured"
            provider_choices.append(f"{provider['name']} ({status_str})")
        
        self._provider_radio.Set(provider_choices)

    def _on_refresh(self, event: wx.CommandEvent) -> None:
        """Refresh provider status."""
        self._provider_status = check_provider_status()
        self._update_provider_list()
        self._update_status_text()
        
    def _on_select_provider(self, event: wx.Event) -> None:
        """Handle provider selection from radio box."""
        self._update_status_text()

    def _update_status_text(self) -> None:
        """Update the status text based on selection."""
        selection = self._provider_radio.GetSelection()
        if selection == wx.NOT_FOUND:
            self._status_text.SetLabel("Select a provider to see details.")
            return
        
        provider = PROVIDERS[selection]
        provider_id = provider["id"]
        prov_status = self._provider_status.get(provider_id, {})
        
        if prov_status.get("configured"):
            auth_type = prov_status.get("type", "unknown")
            if auth_type == "oauth":
                self._status_text.SetLabel(
                    f"{provider['name']} is configured via OAuth login."
                )
            elif auth_type == "api_key":
                self._status_text.SetLabel(
                    f"{provider['name']} is configured via API key."
                )
            elif auth_type == "aws":
                self._status_text.SetLabel(
                    f"{provider['name']} is configured via AWS credentials."
                )
            else:
                self._status_text.SetLabel(
                    f"{provider['name']} is configured."
                )
        else:
            auth_type = provider.get("auth_type", "unknown")
            if auth_type == "oauth":
                self._status_text.SetLabel(
                    f"{provider['name']} requires OAuth login.\n"
                    "Click 'Configure Provider' to authenticate."
                )
            elif auth_type == "api_key":
                self._status_text.SetLabel(
                    f"{provider['name']} requires an API key.\n"
                    "Click 'Configure Provider' to enter your key."
                )
            elif auth_type == "local":
                self._status_text.SetLabel(
                    f"{provider['name']} runs locally.\n"
                    "Make sure Ollama is running on your machine."
                )
            else:
                self._status_text.SetLabel(
                    f"{provider['name']} is not configured."
                )

    def _on_configure(self, event: wx.CommandEvent) -> None:
        """Configure the selected provider."""
        selection = self._provider_radio.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox(
                "Please select a provider first.",
                "No Selection",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        
        provider = PROVIDERS[selection]
        auth_type = provider.get("auth_type", "unknown")
        
        if auth_type == "oauth":
            self._configure_oauth(provider)
        elif auth_type == "api_key":
            self._configure_api_key(provider)
        elif auth_type == "aws":
            self._configure_aws(provider)
        elif auth_type == "local":
            wx.MessageBox(
                "Ollama is a local service. Please ensure Ollama is running\n"
                "on your machine (https://ollama.ai).",
                "Ollama Setup",
                wx.OK | wx.ICON_INFORMATION,
                self,
            )
        else:
            wx.MessageBox(
                f"Unknown authentication type: {auth_type}",
                "Error",
                wx.OK | wx.ICON_ERROR,
                self,
            )

    # Mapping from our provider IDs to pi-ai login provider names
    PROVIDER_LOGIN_MAP = {
        "anthropic": "anthropic",
        "openai": "openai-codex",
        "google": "google-gemini-cli",
        "github-copilot": "github-copilot",
    }

    def _configure_oauth(self, provider: dict) -> None:
        """Configure provider via OAuth login."""
        # Get the pi-ai provider name for login
        provider_id = provider.get("id", "")
        login_provider = self.PROVIDER_LOGIN_MAP.get(provider_id, provider_id)
        
        result = wx.MessageBox(
            f"To configure {provider['name']},\n"
            f"a terminal will open for OAuth authentication.\n\n"
            f"Continue?",
            "OAuth Login",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        
        if result == wx.ID_YES:
            try:
                # Run @mariozechner/pi-ai login <provider> to open browser for OAuth
                # Use a new cmd window on Windows to properly handle the npx command
                import sys
                if sys.platform == "win32":
                    # Open a new cmd window that runs the login command
                    # The window will stay open so user can see any prompts/errors
                    subprocess.Popen(
                        f'start cmd /k npx @mariozechner/pi-ai login {login_provider}',
                        shell=True,
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:
                    subprocess.Popen(["npx", "@mariozechner/pi-ai", "login", login_provider], shell=True)
                
                wx.MessageBox(
                    f"A terminal should have opened for {provider['name']} authentication.\n\n"
                    f"Follow the prompts in the terminal to complete login.\n"
                    f"After completing the login, click 'Refresh Status' to update.",
                    "OAuth Started",
                    wx.OK | wx.ICON_INFORMATION,
                    self,
                )
            except Exception as e:
                wx.MessageBox(
                    f"Failed to start login: {str(e)}",
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                    self,
                )

    def _configure_api_key(self, provider: dict) -> None:
        """Configure provider via API key."""
        env_key = provider.get("env_key", "")
        
        # Check if already set in environment
        current_value = os.environ.get(env_key, "")
        
        # Ask user for API key
        dlg = wx.TextEntryDialog(
            self,
            f"Enter your {provider['name']} API key:",
            "API Key Configuration",
            defaultValue=current_value,
            style=wx.TE_PASSWORD,
        )
        
        if dlg.ShowModal() == wx.ID_OK:
            api_key = dlg.GetValue().strip()
            if api_key:
                # Set the environment variable
                os.environ[env_key] = api_key
                
                # Also save to a .env file for persistence
                self._save_api_key_to_env(env_key, api_key)
                
                # Refresh status
                self._provider_status = check_provider_status()
                self._update_provider_list()
                self._update_status_text()
                
                wx.MessageBox(
                    f"API key for {provider['name']} has been saved.\n\n"
                    f"Note: You may need to restart Codex Desk for the key to take effect.",
                    "API Key Saved",
                    wx.OK | wx.ICON_INFORMATION,
                    self,
                )
            else:
                wx.MessageBox(
                    "Please enter a valid API key.",
                    "Invalid Input",
                    wx.OK | wx.ICON_WARNING,
                    self,
                )
        
        dlg.Destroy()

    def _save_api_key_to_env(self, key: str, value: str) -> None:
        """Save API key to a .env file for persistence."""
        env_file = os.path.expanduser("~/.pi/agent/.env")
        
        try:
            # Read existing content
            existing = {}
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line:
                            k, v = line.split('=', 1)
                            existing[k.strip()] = v.strip()
            
            # Update with new value
            existing[key] = value
            
            # Write back
            with open(env_file, 'w') as f:
                for k, v in existing.items():
                    f.write(f"{k}={v}\n")
        except Exception as e:
            # Just warn, not critical
            print(f"Warning: Could not save API key to .env: {e}")

    def _configure_aws(self, provider: dict) -> None:
        """Configure provider via AWS credentials."""
        wx.MessageBox(
            f"To configure {provider['name']},\n"
            f"you need to have AWS credentials configured.\n\n"
            f"Options:\n"
            f"1. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables\n"
            f"2. Configure AWS profile in ~/.aws/credentials\n\n"
            f"Click 'Refresh Status' after configuring.",
            "AWS Configuration",
            wx.OK | wx.ICON_INFORMATION,
            self,
        )

    def _on_remove(self, event: wx.CommandEvent) -> None:
        """Remove provider configuration."""
        selection = self._provider_radio.GetSelection()
        if selection == wx.NOT_FOUND:
            wx.MessageBox(
                "Please select a provider first.",
                "No Selection",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        
        provider = PROVIDERS[selection]
        result = wx.MessageBox(
            f"Remove configuration for {provider['name']}?",
            "Confirm Removal",
            wx.YES_NO | wx.ICON_QUESTION,
            self,
        )
        
        if result == wx.ID_YES:
            # For OAuth, we'd need to remove from auth.json
            # For API keys, remove from .env
            env_key = provider.get("env_key")
            if env_key and os.environ.get(env_key):
                # Clear from environment
                del os.environ[env_key]
                
                # Remove from .env file
                self._remove_api_key_from_env(env_key)
            
            # Refresh status
            self._provider_status = check_provider_status()
            self._update_provider_list()
            self._update_status_text()
            
            wx.MessageBox(
                f"Configuration for {provider['name']} has been removed.",
                "Removed",
                wx.OK,
                self,
            )

    def _remove_api_key_from_env(self, key: str) -> None:
        """Remove API key from .env file."""
        env_file = os.path.expanduser("~/.pi/agent/.env")
        
        try:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()
                
                with open(env_file, 'w') as f:
                    for line in lines:
                        if not line.strip().startswith(f"{key}="):
                            f.write(line)
        except Exception as e:
            print(f"Warning: Could not remove API key from .env: {e}")


class ProviderDialog(wx.Dialog):
    """Dialog for provider management."""

    def __init__(self, parent: wx.Window) -> None:
        super().__init__(
            parent,
            wx.ID_ANY,
            "Manage AI Providers",
            size=(500, 500),
        )
        
        # Create sizer first
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
        panel = ProviderPanel(self)
        sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        
        # Close button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        close_btn = wx.Button(self, wx.ID_OK, "Close")
        btn_sizer.Add((0, 0), proportion=1)  # Spacer to push button to the right
        btn_sizer.Add(close_btn, flag=wx.ALL, border=10)
        sizer.Add(btn_sizer, flag=wx.EXPAND)
        
        self.CentreOnParent()
