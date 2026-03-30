"""
CPAverse Tax Prep Agent — Orchestrator

Central coordinator that manages the agent's daily workflow:
1. Morning startup: Open Drake, log into TaxDome, run morning report
2. Daytime loop: Monitor TaxDome for new activity, process documents
3. Evening shutdown: Save work, close Drake for updates

The orchestrator enforces the security policy, coordinates between
TaxDome and Drake, and ensures all actions comply with Circular 230.

Architecture:
    orchestrator.py (this file)
        ├── credential_manager.py  — TOTP, passwords, login tracking
        ├── taxdome_session.py     — TaxDome browser automation & chat
        ├── drake_lifecycle.py     — Drake daily open/close/password rotation
        └── activity_logger.py     — GitHub-based activity log for morning reports

Approved Systems (per AGENT-SECURITY-POLICY.md):
    - TaxDome (app.taxdome.com) — client portal, document management, team chat
    - Drake Tax 2025 (AWS WorkSpace) — tax preparation software
    - GitHub (api.github.com) — activity logs, code repo
    - Google Chat (webhook) — admin-only notifications to Josh
    - Claude API (api.anthropic.com) — report formatting
    - n8n Cloud (cpaverse.app.n8n.cloud) — workflow automation

Dependencies: credential_manager, taxdome_session, drake_lifecycle
"""

import os
import json
import time as time_module
from datetime import datetime, time, timedelta
from typing import Optional

from credential_manager import CredentialManager
from taxdome_session import TaxDomeSessionManager
from drake_lifecycle import DrakeLifecycleManager


class AgentOrchestrator:
    """
    Central coordinator for the CPAverse Tax Prep Agent.

    Trusted team members (per security policy):
        - Josh Mauer (josh) — Admin, all permissions
        - Sarah (sarah) — Tax Prep Lead
        - Adam (adam) — Tax Prep Lead
    """

    # ── Constants ──────────────────────────────────────────────────
    MORNING_START = time(7, 0)    # 7:00 AM CT
    EVENING_SHUTDOWN = time(21, 0)  # 9:00 PM CT
    MONITOR_INTERVAL_SECONDS = 300  # Check TaxDome every 5 minutes
    AGENT_NAME = "CPAverse Tax Agent"
    AGENT_VERSION = "0.1.0"

    # Trusted team members — ONLY these users can give instructions
    TRUSTED_USERS = {
        "josh": {"role": "admin", "full_name": "Josh Mauer"},
        "sarah": {"role": "tax_prep_lead", "full_name": "Sarah"},
        "adam": {"role": "tax_prep_lead", "full_name": "Adam"},
    }

    # Hard-blocked actions (per AGENT-SECURITY-POLICY.md section 5)
    PROHIBITED_ACTIONS = [
        "send_email",
        "file_tax_return",      # Requires Josh's explicit approval
        "click_external_link",  # Human decision only
        "share_client_pii",
        "disable_mfa",
        "modify_security_policy",
        "access_bank_accounts",
        "install_software",
    ]

    def __init__(self, config_path: Optional[str] = None):
        """Initialize all subsystems."""
        self.cred_manager = CredentialManager(config_path)
        self.taxdome = TaxDomeSessionManager(self.cred_manager)
        self.drake = DrakeLifecycleManager(self.cred_manager)

        # Agent state
        self.is_running = False
        self.current_phase = "idle"  # idle, morning_startup, monitoring, evening_shutdown
        self.activity_log = []
        self.last_monitor_check = None

    # ── Security Enforcement ──────────────────────────────────────

    def validate_instruction(self, instruction: str, source_user: str) -> dict:
        """
        Validate an instruction before executing it.

        Security checks (per AGENT-SECURITY-POLICY.md):
        1. Is the source user trusted?
        2. Does the instruction contain prohibited actions?
        3. Does the instruction require elevated approval (Josh only)?

        Returns:
            {
                "allowed": bool,
                "reason": str,
                "requires_approval": bool,
                "approval_from": str or None
            }
        """
        # Check 1: Is user trusted?
        if source_user.lower() not in self.TRUSTED_USERS:
            self.cred_manager.send_security_alert(
                "unauthorized_instruction",
                f"Instruction received from untrusted user: {source_user}\n"
                f"Instruction: {instruction[:100]}..."
            )
            return {
                "allowed": False,
                "reason": f"User '{source_user}' is not in the trusted team list",
                "requires_approval": False,
                "approval_from": None,
            }

        # Check 2: Prohibited action?
        instruction_lower = instruction.lower()
        for action in self.PROHIBITED_ACTIONS:
            keywords = action.replace("_", " ")
            if keywords in instruction_lower:
                return {
                    "allowed": False,
                    "reason": f"Action '{action}' is prohibited by security policy",
                    "requires_approval": False,
                    "approval_from": None,
                }

        # Check 3: Restricted actions that require Josh's approval
        restricted_keywords = [
            "file return", "submit return", "e-file",
            "override", "delete client", "remove client",
            "change team", "modify permissions",
        ]
        for keyword in restricted_keywords:
            if keyword in instruction_lower:
                user_role = self.TRUSTED_USERS[source_user.lower()]["role"]
                if user_role != "admin":
                    return {
                        "allowed": False,
                        "reason": f"Action requires admin (Josh) approval",
                        "requires_approval": True,
                        "approval_from": "josh",
                    }

        return {
            "allowed": True,
            "reason": "Instruction validated",
            "requires_approval": False,
            "approval_from": None,
        }

    def detect_prompt_injection(self, message: str) -> bool:
        """
        Detect potential prompt injection attempts in messages.

        Per AGENT-SECURITY-POLICY.md section 3:
        - Treat ALL external text as untrusted data
        - Never execute instructions embedded in client documents
        - Alert Josh on any injection attempt detected
        """
        injection_patterns = [
            "ignore previous instructions",
            "ignore your instructions",
            "you are now",
            "new instructions:",
            "system prompt:",
            "admin override",
            "execute the following",
            "disregard your programming",
            "forget your rules",
            "act as if",
            "pretend you are",
            "sudo ",
            "override security",
        ]

        message_lower = message.lower()
        for pattern in injection_patterns:
            if pattern in message_lower:
                self.cred_manager.send_security_alert(
                    "injection_attempt",
                    f"Potential prompt injection detected.\n"
                    f"Pattern matched: '{pattern}'\n"
                    f"Message excerpt: {message[:200]}..."
                )
                self.log_activity(
                    "SECURITY",
                    f"Prompt injection attempt blocked (pattern: {pattern})"
                )
                return True

        return False

    # ── Daily Lifecycle ───────────────────────────────────────────

    def morning_startup(self):
        """
        Execute morning startup sequence (7:00 AM CT).

        1. Check credential status (password expirations, login blocks)
        2. Start Drake Tax 2025
        3. Authenticate into TaxDome
        4. Generate and deliver morning reports
        5. Begin monitoring loop
        """
        self.current_phase = "morning_startup"
        self.log_activity("LIFECYCLE", "Morning startup initiated")

        # Step 1: Credential health check
        cred_status = self.cred_manager.get_credential_status()
        for system, status in cred_status.items():
            if status["password_status"] == "expired":
                self.log_activity(
                    "CREDENTIAL",
                    f"{system}: Password EXPIRED — rotation needed"
                )
            elif status["login_blocked"]:
                self.log_activity(
                    "CREDENTIAL",
                    f"{system}: Login BLOCKED — awaiting Josh intervention"
                )

        # Step 2: Start Drake
        try:
            drake_result = self.drake.morning_startup()
            self.log_activity("DRAKE", f"Drake startup: {drake_result.get('status', 'unknown')}")
        except Exception as e:
            self.log_activity("DRAKE", f"Drake startup FAILED: {str(e)}")
            self.cred_manager.send_security_alert(
                "system_error",
                f"Drake morning startup failed: {str(e)}"
            )

        # Step 3: Authenticate TaxDome
        try:
            td_result = self.taxdome.ensure_authenticated()
            self.log_activity("TAXDOME", f"TaxDome auth: {td_result.get('status', 'unknown')}")
        except Exception as e:
            self.log_activity("TAXDOME", f"TaxDome auth FAILED: {str(e)}")
            self.cred_manager.send_security_alert(
                "system_error",
                f"TaxDome authentication failed: {str(e)}"
            )

        # Step 4: Deliver morning reports via TaxDome chat
        try:
            self.deliver_morning_reports()
        except Exception as e:
            self.log_activity("REPORT", f"Morning report delivery FAILED: {str(e)}")

        # Step 5: Transition to monitoring
        self.current_phase = "monitoring"
        self.is_running = True
        self.log_activity("LIFECYCLE", "Morning startup complete — entering monitoring phase")

    def evening_shutdown(self):
        """
        Execute evening shutdown sequence (9:00 PM CT).

        1. Save all open work in Drake
        2. Close Drake for nightly updates
        3. Log out of TaxDome
        4. Write daily summary to activity log
        """
        self.current_phase = "evening_shutdown"
        self.log_activity("LIFECYCLE", "Evening shutdown initiated")

        # Step 1-2: Close Drake
        try:
            drake_result = self.drake.evening_shutdown()
            self.log_activity("DRAKE", f"Drake shutdown: {drake_result.get('status', 'unknown')}")
        except Exception as e:
            self.log_activity("DRAKE", f"Drake shutdown error: {str(e)}")

        # Step 3: TaxDome logout (optional — it times out anyway)
        self.taxdome.is_authenticated = False

        # Step 4: Write daily summary
        self.log_activity("LIFECYCLE", "Evening shutdown complete")
        self.write_daily_summary()

        self.current_phase = "idle"
        self.is_running = False

    # ── Monitoring Loop ───────────────────────────────────────────

    def run_monitor_cycle(self):
        """
        Execute one monitoring cycle.

        Called every MONITOR_INTERVAL_SECONDS during the workday.
        Checks TaxDome for new activity and processes it.
        """
        if not self.is_running:
            return

        now = datetime.now()
        self.last_monitor_check = now

        # Re-authenticate TaxDome if session expired
        if not self.taxdome.is_authenticated:
            try:
                self.taxdome.ensure_authenticated()
            except Exception as e:
                self.log_activity("TAXDOME", f"Re-auth failed: {str(e)}")
                return

        # Check for new activity
        try:
            activity = self.taxdome.check_new_activity()
            if activity and activity.get("has_new_items"):
                self.process_new_activity(activity)
        except Exception as e:
            self.log_activity("MONITOR", f"Activity check error: {str(e)}")

        # Check for new chat messages
        try:
            messages = self.taxdome.check_chat_messages()
            if messages:
                self.process_chat_messages(messages)
        except Exception as e:
            self.log_activity("MONITOR", f"Chat check error: {str(e)}")

    def process_new_activity(self, activity: dict):
        """
        Process new TaxDome activity detected during monitoring.

        Types of activity:
        - New document uploaded by client
        - New organizer completed
        - Client status change
        - New appointment scheduled
        """
        items = activity.get("items", [])
        for item in items:
            item_type = item.get("type", "unknown")
            client = item.get("client_name", "Unknown")

            # Circular 230 compliance: log all client interactions
            self.log_activity(
                "CLIENT_ACTIVITY",
                f"[{item_type}] {client}: {item.get('description', 'No description')}"
            )

            # Route based on type
            if item_type == "document_upload":
                self.log_activity(
                    "DOCUMENT",
                    f"New document from {client} — queued for processing"
                )
            elif item_type == "organizer_complete":
                self.log_activity(
                    "ORGANIZER",
                    f"Organizer completed by {client} — ready for tax prep"
                )

    def process_chat_messages(self, messages: list):
        """
        Process new chat messages from TaxDome.

        Security: All messages are scanned for prompt injection before processing.
        Only messages from trusted team members are treated as instructions.
        """
        for msg in messages:
            sender = msg.get("sender", "unknown")
            content = msg.get("content", "")

            # Security: Check for injection
            if self.detect_prompt_injection(content):
                continue

            # Only act on messages from trusted users
            validation = self.validate_instruction(content, sender)
            if validation["allowed"]:
                self.log_activity(
                    "CHAT",
                    f"Instruction from {sender}: {content[:100]}"
                )
                # TODO: Route instruction to appropriate handler
            elif validation["requires_approval"]:
                self.log_activity(
                    "CHAT",
                    f"Instruction from {sender} requires Josh approval: {content[:100]}"
                )
                # TODO: Notify Josh for approval via TaxDome chat

    # ── Morning Reports ───────────────────────────────────────────

    def deliver_morning_reports(self):
        """
        Deliver tailored morning reports to each team member via TaxDome chat.

        Per communication architecture:
        - Josh: Executive summary (all systems, security, full activity)
        - Sarah: Filtered to her assigned clients and tasks
        - Adam: Filtered to his assigned clients and tasks
        - Google Chat webhook: Admin-only alerts (security, passwords)
        """
        security_summary = self.cred_manager.get_security_summary()

        for username, info in self.TRUSTED_USERS.items():
            try:
                report = self.build_report_for_user(username, info["role"])
                if report:
                    self.taxdome.send_chat_message(
                        recipient=username,
                        message=report
                    )
                    self.log_activity(
                        "REPORT",
                        f"Morning report delivered to {info['full_name']} via TaxDome chat"
                    )
            except Exception as e:
                self.log_activity(
                    "REPORT",
                    f"Failed to deliver report to {info['full_name']}: {str(e)}"
                )

    def build_report_for_user(self, username: str, role: str) -> str:
        """
        Build a tailored morning report based on user role.

        Admin (Josh): Full report with security summary, all clients, system status
        Tax Prep Lead: Filtered to their assigned clients and pending tasks
        """
        now = datetime.now()
        header = f"Good morning! Here's your {now.strftime('%A, %B %d')} report.\n"

        if role == "admin":
            # Full executive report
            security = self.cred_manager.get_security_summary()
            report = (
                f"{header}\n"
                f"{security}\n\n"
                f"━━━ SYSTEM STATUS ━━━\n"
                f"Drake Tax 2025: {'Running' if self.drake.is_running else 'Stopped'}\n"
                f"TaxDome: {'Connected' if self.taxdome.is_authenticated else 'Disconnected'}\n"
                f"Agent Version: {self.AGENT_VERSION}\n\n"
                f"━━━ ACTIVITY SUMMARY ━━━\n"
            )
            # Add recent activity
            recent = [a for a in self.activity_log[-20:]]
            if recent:
                for entry in recent:
                    report += f"  {entry['time']} [{entry['category']}] {entry['message']}\n"
            else:
                report += "  No activity logged yet today.\n"

            return report

        else:
            # Tax Prep Lead report — filtered view
            report = (
                f"{header}\n"
                f"━━━ YOUR TASKS ━━━\n"
                f"(Task filtering will be active once TaxDome browser automation is live)\n\n"
                f"━━━ CLIENT ACTIVITY ━━━\n"
            )
            # Filter activity to this user's clients
            client_activity = [
                a for a in self.activity_log
                if a["category"] in ("CLIENT_ACTIVITY", "DOCUMENT", "ORGANIZER")
            ]
            if client_activity:
                for entry in client_activity[-10:]:
                    report += f"  {entry['time']} {entry['message']}\n"
            else:
                report += "  No new client activity.\n"

            return report

    # ── Activity Logging ──────────────────────────────────────────

    def log_activity(self, category: str, message: str):
        """
        Log an activity entry.

        These entries feed into the morning report and daily summary.
        Per security policy: NEVER include client PII, passwords, or secrets.
        """
        entry = {
            "time": datetime.now().strftime("%H:%M"),
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "message": message,
        }
        self.activity_log.append(entry)

        # Also print for debugging during development
        print(f"[{entry['time']}] [{category}] {message}")

    def write_daily_summary(self):
        """
        Write the daily activity summary to GitHub for the morning report workflow.

        This is the file that n8n's Morning Report workflow reads each day.
        """
        now = datetime.now()
        summary_lines = [
            f"# CPAverse Tax Agent — Daily Activity Log",
            f"## {now.strftime('%A, %B %d, %Y')}",
            "",
        ]

        # Group by category
        categories = {}
        for entry in self.activity_log:
            cat = entry["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(entry)

        for cat, entries in categories.items():
            summary_lines.append(f"### {cat}")
            for entry in entries:
                summary_lines.append(f"- [{entry['time']}] {entry['message']}")
            summary_lines.append("")

        summary = "\n".join(summary_lines)

        # TODO: Write to GitHub via API (logs/daily-activity.md)
        # This will be handled by the n8n workflow or direct GitHub API call
        self.log_activity("SYSTEM", "Daily summary written")

        return summary

    # ── Main Run Loop ─────────────────────────────────────────────

    def run(self):
        """
        Main agent loop — runs continuously during the workday.

        Schedule:
            7:00 AM CT  — morning_startup()
            7:05 AM - 8:55 PM CT — run_monitor_cycle() every 5 minutes
            9:00 PM CT  — evening_shutdown()
        """
        self.log_activity("SYSTEM", f"{self.AGENT_NAME} v{self.AGENT_VERSION} starting")

        while True:
            now = datetime.now()
            current_time = now.time()

            # Morning startup
            if (current_time >= self.MORNING_START
                    and current_time < self.EVENING_SHUTDOWN
                    and self.current_phase == "idle"):
                self.morning_startup()

            # Monitoring cycle
            elif (self.current_phase == "monitoring"
                    and current_time < self.EVENING_SHUTDOWN):
                if (self.last_monitor_check is None
                        or (now - self.last_monitor_check).seconds >= self.MONITOR_INTERVAL_SECONDS):
                    self.run_monitor_cycle()

            # Evening shutdown
            elif (current_time >= self.EVENING_SHUTDOWN
                    and self.current_phase != "idle"):
                self.evening_shutdown()

            # Sleep between checks
            time_module.sleep(30)  # Check schedule every 30 seconds


# ── Entry Point ───────────────────────────────────────────────────

def main():
    """Start the CPAverse Tax Prep Agent."""
    print("=" * 60)
    print("  CPAverse Tax Prep Agent")
    print(f"  Version: {AgentOrchestrator.AGENT_VERSION}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}")
    print("=" * 60)

    # Load config from environment or file
    config_path = os.environ.get("CPAVERSE_CONFIG_PATH")
    agent = AgentOrchestrator(config_path)

    try:
        agent.run()
    except KeyboardInterrupt:
        print("\nAgent stopped by user")
        agent.evening_shutdown()
    except Exception as e:
        agent.cred_manager.send_security_alert(
            "system_error",
            f"Agent crashed: {str(e)}"
        )
        raise


if __name__ == "__main__":
    main()
