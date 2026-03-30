"""
CPAverse Agent — TaxDome Session Manager

Manages the agent's browser session in TaxDome, including:
- Login with credentials + TOTP when sessions expire
- Team chat monitoring and sending
- Tailored report delivery to individual Tax Prep Leads
- Document and notification checking

TaxDome forces periodic logouts, so the agent must be able to
re-authenticate autonomously using stored credentials and TOTP secrets.

Browser Automation:
    Uses Firecrawl API for all browser interactions. The agent connects to
    TaxDome through the browser like a human — there are no TaxDome webhooks
    or native API endpoints available for automation.

Chat System:
    The agent sends tailored morning reports to each team member via TaxDome's
    team chat feature. Reports are filtered based on user role:
    - Admin (Josh): Full executive report with all activity, security alerts
    - Tax Prep Leads: Filtered to their assigned clients and tasks only

Dependencies: credential_manager.py, Firecrawl (browser automation)
"""

import os
import time as time_module
from datetime import datetime
from typing import Optional

from credential_manager import CredentialManager


class TaxDomeBrowser:
    """
    Firecrawl-based browser automation for TaxDome.

    This wraps the Firecrawl API to provide TaxDome-specific navigation
    methods. All browser interaction goes through this class.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        self.base_url = os.environ.get("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev")
        self.session_id = None

    def start_session(self) -> bool:
        """Initialize a Firecrawl browser session."""
        # TODO: Implement Firecrawl session creation
        # resp = requests.post(f"{self.base_url}/v1/sessions", headers=...)
        # self.session_id = resp.json()["session_id"]
        return False

    def navigate(self, url: str) -> dict:
        """Navigate the browser to a URL."""
        # TODO: Firecrawl navigate
        # resp = requests.post(f"{self.base_url}/v1/sessions/{self.session_id}/navigate",
        #     json={"url": url})
        return {"status": "not_implemented"}

    def type_text(self, selector: str, text: str) -> bool:
        """Type text into a form field identified by CSS selector."""
        # TODO: Firecrawl type action
        return False

    def click(self, selector: str) -> bool:
        """Click an element identified by CSS selector."""
        # TODO: Firecrawl click action
        return False

    def get_text(self, selector: str) -> Optional[str]:
        """Get text content of an element."""
        # TODO: Firecrawl extract text
        return None

    def element_exists(self, selector: str) -> bool:
        """Check if an element exists on the page."""
        # TODO: Firecrawl element check
        return False

    def get_page_text(self) -> str:
        """Get full page text content (for parsing notifications, chats, etc.)."""
        # TODO: Firecrawl scrape page text
        return ""

    def wait_for(self, selector: str, timeout_seconds: int = 10) -> bool:
        """Wait for an element to appear on the page."""
        # TODO: Firecrawl wait/poll
        return False

    def close_session(self):
        """Close the Firecrawl browser session."""
        # TODO: Cleanup
        self.session_id = None


class TaxDomeSessionManager:
    """Manages the agent's TaxDome browser session and communications."""

    # TaxDome CSS selectors (will need updating as TaxDome UI changes)
    SELECTORS = {
        # Login page
        "email_input": 'input[name="email"], input[type="email"]',
        "password_input": 'input[name="password"], input[type="password"]',
        "login_button": 'button[type="submit"]',
        "mfa_input": 'input[name="code"], input[placeholder*="code"]',
        "mfa_verify_button": 'button[type="submit"]',
        "remember_device": 'input[type="checkbox"]',
        # Dashboard
        "dashboard_indicator": '.dashboard, [data-testid="dashboard"]',
        # Chat
        "chat_panel": '.chat-panel, [data-testid="team-chat"]',
        "chat_input": 'textarea.message-input, [data-testid="message-input"]',
        "chat_send": 'button.send-button, [data-testid="send-message"]',
        "unread_badge": '.unread-count, [data-testid="unread-indicator"]',
        # Notifications
        "notification_bell": '.notifications-bell, [data-testid="notifications"]',
        "notification_items": '.notification-item',
    }

    def __init__(self, credential_manager: CredentialManager):
        self.cred_manager = credential_manager
        self.system_name = "taxdome"
        self.browser = TaxDomeBrowser()

        # Session state
        self.is_authenticated = False
        self.last_activity = None
        self.is_running = False

        # Team configuration
        self.team_members = {
            "josh": {
                "name": "Josh Mauer",
                "role": "admin",
                "report_type": "executive",
            },
            "sarah": {
                "name": "Sarah",
                "role": "tax_prep_lead",
                "report_type": "lead",
            },
            "adam": {
                "name": "Adam",
                "role": "tax_prep_lead",
                "report_type": "lead",
            },
        }

    # ── Authentication ────────────────────────────────────────────

    def ensure_authenticated(self) -> dict:
        """
        Ensure we have an active TaxDome session.
        If session expired, re-authenticate.

        Returns:
            {"status": "authenticated" | "login_failed" | "blocked"}
        """
        if self.is_authenticated:
            # Verify session is still valid
            if self.browser.element_exists(self.SELECTORS["dashboard_indicator"]):
                return {"status": "authenticated"}
            else:
                self.is_authenticated = False

        return self._perform_login()

    def _perform_login(self) -> dict:
        """
        Login to TaxDome via browser automation.

        Steps:
        1. Navigate to TaxDome login page
        2. Enter username/email
        3. Enter password
        4. Handle MFA prompt with TOTP code
        5. Verify successful login

        Returns:
            {"status": "authenticated" | "login_failed" | "blocked"}
        """
        if self.cred_manager.is_login_blocked(self.system_name):
            return {"status": "blocked"}

        # Get credentials
        system_config = self.cred_manager.config["systems"].get(self.system_name)
        if not system_config:
            return {"status": "login_failed", "reason": "No TaxDome credentials configured"}

        try:
            # Step 1: Navigate to login page
            self.browser.navigate(system_config["login_url"])
            self.browser.wait_for(self.SELECTORS["email_input"])

            # Step 2: Enter email
            self.browser.type_text(
                self.SELECTORS["email_input"],
                system_config["username"]
            )

            # Step 3: Enter password
            password = os.environ.get("TAXDOME_PASSWORD", "")
            self.browser.type_text(self.SELECTORS["password_input"], password)

            # Step 4: Click login
            self.browser.click(self.SELECTORS["login_button"])

            # Step 5: Handle MFA if prompted
            if self.browser.wait_for(self.SELECTORS["mfa_input"], timeout_seconds=5):
                # Wait for optimal TOTP timing (>5 seconds remaining)
                remaining = self.cred_manager.get_totp_time_remaining(self.system_name)
                if remaining < 5:
                    time_module.sleep(remaining + 1)

                totp_code = self.cred_manager.generate_totp_code(self.system_name)
                if totp_code:
                    self.browser.type_text(self.SELECTORS["mfa_input"], totp_code)
                    self.browser.click(self.SELECTORS["mfa_verify_button"])

            # Step 6: Remember device if prompted
            if self.browser.element_exists(self.SELECTORS["remember_device"]):
                self.browser.click(self.SELECTORS["remember_device"])

            # Step 7: Verify dashboard loaded
            if self.browser.wait_for(self.SELECTORS["dashboard_indicator"], timeout_seconds=15):
                self.is_authenticated = True
                self.last_activity = datetime.now()
                self.cred_manager.record_login_attempt(self.system_name, success=True)
                return {"status": "authenticated"}
            else:
                self.cred_manager.record_login_attempt(self.system_name, success=False)
                return {"status": "login_failed", "reason": "Dashboard not loaded after login"}

        except Exception as e:
            self.cred_manager.record_login_attempt(self.system_name, success=False)
            return {"status": "login_failed", "reason": str(e)}

    # ── Team Chat — Sending ────────────────────────────────────────

    def send_chat_message(self, recipient: str, message: str) -> bool:
        """
        Send a message in TaxDome team chat.

        Args:
            recipient: Team member key ("josh", "sarah", "adam") or "all"
            message: Plain text message to send

        Returns True if sent successfully.

        SECURITY: Messages sent only to authorized team members.
        Never sends to clients or external parties.
        """
        if recipient not in self.team_members and recipient != "all":
            return False

        if not self.is_authenticated:
            auth = self.ensure_authenticated()
            if auth["status"] != "authenticated":
                return False

        try:
            # Navigate to team chat
            self.browser.navigate("https://app.taxdome.com/team/chat")
            self.browser.wait_for(self.SELECTORS["chat_panel"])

            if recipient == "all":
                # Send to team chat channel
                pass  # TODO: Select team chat channel
            else:
                # Find or open DM with specific team member
                member_name = self.team_members[recipient]["name"]
                # TODO: Search for and open chat with member_name

            # Type and send message
            self.browser.type_text(self.SELECTORS["chat_input"], message)
            self.browser.click(self.SELECTORS["chat_send"])

            self.last_activity = datetime.now()
            return True

        except Exception as e:
            print(f"Chat send error: {e}")
            return False

    # ── Team Chat — Reading ────────────────────────────────────────

    def check_chat_messages(self) -> list:
        """
        Check TaxDome team chat for new messages directed at the agent.

        Returns list of message dicts:
        [
            {
                "sender": "josh",
                "content": "Rush the Smith return",
                "timestamp": "2026-03-30 09:15"
            }
        ]
        """
        if not self.is_authenticated:
            return []

        try:
            # Check for unread indicators
            if not self.browser.element_exists(self.SELECTORS["unread_badge"]):
                return []

            # Navigate to chat
            self.browser.navigate("https://app.taxdome.com/team/chat")
            self.browser.wait_for(self.SELECTORS["chat_panel"])

            # TODO: Parse unread messages
            # For each unread conversation:
            #   - Extract sender name
            #   - Match to team_members dict
            #   - Extract message text
            #   - Build structured result

            self.last_activity = datetime.now()
            return []

        except Exception as e:
            print(f"Chat check error: {e}")
            return []

    # ── Notification Monitoring ────────────────────────────────────

    def check_new_activity(self) -> dict:
        """
        Check TaxDome for new client/document activity.

        Returns:
            {
                "has_new_items": bool,
                "items": [
                    {
                        "type": "document_upload" | "organizer_complete" | ...,
                        "client_name": "...",
                        "description": "..."
                    }
                ]
            }
        """
        if not self.is_authenticated:
            return {"has_new_items": False, "items": []}

        try:
            # Click notification bell
            self.browser.click(self.SELECTORS["notification_bell"])
            self.browser.wait_for(self.SELECTORS["notification_items"], timeout_seconds=5)

            # TODO: Parse notification items from page
            # For each notification:
            #   - Classify type (document, organizer, message, deadline)
            #   - Extract client name
            #   - Extract description
            #   - Build structured result

            self.last_activity = datetime.now()
            return {"has_new_items": False, "items": []}

        except Exception as e:
            print(f"Activity check error: {e}")
            return {"has_new_items": False, "items": []}

    # ── Morning Report Delivery ────────────────────────────────────

    def send_morning_report(self, team_member: str, report_data: dict) -> bool:
        """
        Send a tailored morning report to a specific team member via TaxDome chat.

        Args:
            team_member: "josh", "sarah", or "adam"
            report_data: Dict containing activity log, client assignments, etc.
        """
        member = self.team_members.get(team_member)
        if not member:
            return False

        if member["report_type"] == "executive":
            report = self._format_executive_report(report_data)
        else:
            report = self._format_lead_report(team_member, report_data)

        return self.send_chat_message(team_member, report)

    def _format_executive_report(self, data: dict) -> str:
        """Format the full executive morning report for Josh."""
        today = datetime.now().strftime("%B %d, %Y")
        apr15 = datetime(2026, 4, 15)
        days_left = (apr15 - datetime.now()).days

        return (
            f"CPAverse Agent Report — {today}\n\n"
            f"━━━ COMPLETED SINCE LAST REPORT ━━━\n"
            f"{data.get('completed', 'No returns processed since last report.')}\n\n"
            f"━━━ NEEDS YOUR ATTENTION ━━━\n"
            f"{data.get('urgent', 'No urgent items.')}\n\n"
            f"━━━ WAITING ON CLIENTS ━━━\n"
            f"{data.get('waiting', 'No pending client requests.')}\n\n"
            f"━━━ DEADLINE WATCH ━━━\n"
            f"Days until April 15: {days_left}\n"
            f"Returns completed: {data.get('returns_completed', 0)}\n"
            f"Returns in progress: {data.get('returns_in_progress', 0)}\n\n"
            f"━━━ AGENT ACTIVITY SUMMARY ━━━\n"
            f"Returns processed: {data.get('returns_processed', 0)}\n"
            f"Documents classified: {data.get('docs_classified', 0)}\n"
            f"Flags raised: {data.get('flags_raised', 0)}\n\n"
            f"— CPAverse Tax Prep Agent"
        )

    def _format_lead_report(self, lead: str, data: dict) -> str:
        """Format a tailored report for a Tax Prep Lead (their clients only)."""
        member = self.team_members[lead]
        today = datetime.now().strftime("%B %d, %Y")

        assigned_clients = data.get("assignments", {}).get(lead, [])
        completed = [
            c for c in data.get("completed_list", [])
            if c.get("assigned_to") == lead
        ]
        urgent = [
            c for c in data.get("urgent_list", [])
            if c.get("assigned_to") == lead
        ]
        waiting = [
            c for c in data.get("waiting_list", [])
            if c.get("assigned_to") == lead
        ]

        completed_text = "\n".join(
            [f"  - {c['description']}" for c in completed]
        ) or "No items completed."

        urgent_text = "\n".join(
            [f"  ! {c['description']}" for c in urgent]
        ) or "No urgent items."

        waiting_text = "\n".join(
            [f"  - {c['description']}" for c in waiting]
        ) or "No items waiting."

        return (
            f"Good morning {member['name']}! Here's your update for {today}:\n\n"
            f"Your clients: {len(assigned_clients)} assigned\n\n"
            f"━━━ COMPLETED ━━━\n{completed_text}\n\n"
            f"━━━ NEEDS ATTENTION ━━━\n{urgent_text}\n\n"
            f"━━━ WAITING ON CLIENTS ━━━\n{waiting_text}\n\n"
            f"Let me know if you need anything!\n"
            f"— CPAverse Tax Prep Agent"
        )

    # ── Status ────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get current TaxDome session status."""
        return {
            "authenticated": self.is_authenticated,
            "last_activity": (
                self.last_activity.strftime("%H:%M CT")
                if self.last_activity else None
            ),
            "login_blocked": self.cred_manager.is_login_blocked(self.system_name),
        }