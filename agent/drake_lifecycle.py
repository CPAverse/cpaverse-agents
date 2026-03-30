"""
CPAverse Agent — Drake Tax 2025 Daily Lifecycle Manager

Manages the daily open/close cycle for Drake Tax software on AWS WorkSpace.
Drake must be closed each night so updates can run, and reopened each morning.

Lifecycle:
    7:00 AM CT — Agent opens Drake, logs in with credentials + TOTP
    7:00 AM - 9:00 PM CT — Agent works in Drake (preparing returns)
    9:00 PM CT — Agent saves all work, closes Drake for nightly updates

Password Rotation:
    Every 90 days, Drake forces a password change.
    Agent generates a new password, answers the security question,
    sets the new password, and notifies Josh via Google Chat.

Multi-Year Support:
    Drake installs multiple years (2025, 2024, 2023, etc.)
    Each year has its own TOTP/MFA code but shares the same password.
    Starting with 2025 only, but designed to scale.

File Access:
    The AWS WorkSpace has virtual drives that map to TaxDome client folders.
    This means the agent can access client documents (W-2s, 1099s, organizers, etc.)
    directly from the file system while working in Drake — no need to download
    them through TaxDome's browser UI.

    Virtual Drive Mapping:
        The mapped drive (typically a network/virtual drive letter) syncs with
        TaxDome's document storage. Each client has a folder structure with
        their uploaded documents organized by type and tax year.

Document Classification:
    Supported document types for agent processing:
    - W-2 (wages and salaries)
    - 1099-INT (interest income)
    - 1099-DIV (dividend income)
    - 1099-NEC (self-employment/contractor income)
    - 1099-R (retirement distributions)
    - 1098 (mortgage interest, education credits)
    - Organizers (client questionnaires)
    - Bank statements (for reconciliation)
    - ID documents (for verification)
    - Prior returns (for carryovers and amendments)

Dependencies: credential_manager.py, Firecrawl (browser automation)
"""

import os
from datetime import datetime, time
from typing import Optional, List

from credential_manager import CredentialManager


class DrakeLifecycleManager:
    """Manages the daily lifecycle of Drake Tax software."""

    def __init__(self, credential_manager: CredentialManager):
        self.cred_manager = credential_manager
        self.system_name = "drake_2025"

        # Schedule configuration
        self.morning_open_time = time(7, 0)     # 7:00 AM CT
        self.evening_close_time = time(21, 0)   # 9:00 PM CT

        # AWS WorkSpace virtual drive — maps to TaxDome client files
        # The drive letter/path will be configured per environment
        self.taxdome_drive_path = os.environ.get(
            "TAXDOME_VIRTUAL_DRIVE", ""
        )  # e.g., "T:\" or "/mnt/taxdome/"

        # State tracking
        self.is_drake_open = False
        self.is_running = False
        self.session_start_time = None
        self.returns_processed_today = 0

    # ── Morning Startup ───────────────────────────────────────────

    def morning_startup(self, browser_automation) -> dict:
        """
        Morning startup sequence for Drake.

        Steps:
        1. Check if login is blocked (too many failures)
        2. Check if password needs rotation
        3. Open Drake application on AWS WorkSpace
        4. Login with username + password
        5. Enter TOTP code
        6. Verify successful login
        7. Navigate to the work queue

        Args:
            browser_automation: Firecrawl browser control instance

        Returns:
            {"success": bool, "message": str, "password_rotated": bool}
        """
        result = {
            "success": False,
            "message": "",
            "password_rotated": False,
        }

        # Step 1: Check login block
        if self.cred_manager.is_login_blocked(self.system_name):
            result["message"] = (
                "Login blocked due to consecutive failures. "
                "Waiting for Josh to resolve."
            )
            return result

        # Step 2: Check password expiration
        pw_status = self.cred_manager.check_password_expiration(self.system_name)
        if pw_status["expired"]:
            result["message"] = (
                "Password expired. Will attempt rotation during login."
            )
            # Password rotation will happen during the login flow
            # when Drake presents the change password dialog

        # Step 3-6: Login sequence (browser automation)
        login_result = self._perform_login(browser_automation)

        if not login_result["success"]:
            attempt = self.cred_manager.record_login_attempt(
                self.system_name, success=False
            )
            result["message"] = (
                f"Login failed. Attempt {attempt['consecutive_failures']} "
                f"of {self.cred_manager.max_login_attempts}."
            )
            if attempt["blocked"]:
                result["message"] += " Login now blocked. Josh has been alerted."
            return result

        # Record successful login
        self.cred_manager.record_login_attempt(self.system_name, success=True)
        self.is_drake_open = True
        self.session_start_time = datetime.now()
        self.returns_processed_today = 0

        result["success"] = True
        result["message"] = "Drake 2025 opened successfully."
        result["password_rotated"] = login_result.get("password_rotated", False)

        return result

    def _perform_login(self, browser_automation) -> dict:
        """
        Execute the Drake login flow via browser automation.

        This is a template — actual Firecrawl commands will be added
        once the browser automation layer is configured.

        Returns:
            {"success": bool, "password_rotated": bool}
        """
        # TODO: Implement with Firecrawl browser automation
        #
        # Pseudocode for the login flow:
        #
        # 1. browser.open_application("Drake Tax 2025")
        # 2. browser.wait_for_element("username_field")
        # 3. browser.type("username_field", credentials.username)
        # 4. browser.type("password_field", credentials.password)
        # 5. browser.click("login_button")
        #
        # 6. If MFA prompt appears:
        #    a. Wait for TOTP timing (if <5 seconds remaining, wait for next code)
        #    b. code = self.cred_manager.generate_totp_code("drake_2025")
        #    c. browser.type("mfa_field", code)
        #    d. browser.click("verify_button")
        #
        # 7. If password change dialog appears:
        #    a. rotation = self.cred_manager.rotate_password("drake_2025")
        #    b. browser.type("current_password", old_password)
        #    c. browser.type("new_password", rotation["new_password"])
        #    d. browser.type("confirm_password", rotation["new_password"])
        #    e. browser.type("security_answer", credentials.security_answer)
        #    f. browser.click("change_password_button")
        #    g. return {"success": True, "password_rotated": True}
        #
        # 8. If main dashboard appears:
        #    return {"success": True, "password_rotated": False}
        #
        # 9. If error appears:
        #    return {"success": False, "password_rotated": False}

        return {"success": False, "password_rotated": False}

    # ── Evening Shutdown ──────────────────────────────────────────

    def evening_shutdown(self, browser_automation) -> dict:
        """
        Evening shutdown sequence for Drake.

        Steps:
        1. Save all open work
        2. Close any open returns
        3. Exit Drake application
        4. Verify Drake is closed
        5. Log session summary

        Args:
            browser_automation: Firecrawl browser control instance

        Returns:
            {"success": bool, "message": str, "session_summary": dict}
        """
        if not self.is_drake_open:
            return {
                "success": True,
                "message": "Drake was not open.",
                "session_summary": None,
            }

        # TODO: Implement with Firecrawl browser automation
        #
        # Pseudocode:
        # 1. browser.keyboard_shortcut("Ctrl+S")  # Save current work
        # 2. browser.click("File > Close Return")
        # 3. browser.click("File > Exit")
        # 4. browser.wait_for_element_gone("drake_window", timeout=30)

        session_duration = None
        if self.session_start_time:
            session_duration = (
                datetime.now() - self.session_start_time
            ).total_seconds() / 3600  # hours

        session_summary = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "session_duration_hours": round(session_duration, 1) if session_duration else 0,
            "returns_processed": self.returns_processed_today,
            "opened_at": (
                self.session_start_time.strftime("%H:%M CT")
                if self.session_start_time else "N/A"
            ),
            "closed_at": datetime.now().strftime("%H:%M CT"),
        }

        self.is_drake_open = False
        self.session_start_time = None

        return {
            "success": True,
            "message": "Drake closed for nightly updates.",
            "session_summary": session_summary,
        }

    # ── Password Rotation ─────────────────────────────────────────

    def handle_password_rotation(self, browser_automation) -> dict:
        """
        Handle Drake's forced password change dialog.

        Called when the login flow detects the password change screen.
        Generates a new password, enters it, answers the security question,
        and notifies Josh via Google Chat.

        Returns:
            {"success": bool, "notification_sent": bool}
        """
        # Generate new password and notify Josh
        rotation = self.cred_manager.rotate_password(self.system_name)

        if not rotation["success"]:
            return {"success": False, "notification_sent": False}

        # TODO: Implement with Firecrawl browser automation
        #
        # Pseudocode:
        # 1. browser.type("new_password_field", rotation["new_password"])
        # 2. browser.type("confirm_password_field", rotation["new_password"])
        # 3. browser.type("security_answer_field", security_answer)
        # 4. browser.click("change_password_button")
        # 5. Verify success

        return {
            "success": True,
            "notification_sent": rotation["notification_sent"],
        }

    # ── Proactive Rotation Check ──────────────────────────────────

    def check_proactive_rotation(self) -> dict:
        """
        Check if password should be rotated proactively (before Drake forces it).

        Called during the morning startup. If password expires within 7 days,
        recommend rotating now to avoid being caught off-guard.

        Returns:
            {"should_rotate": bool, "days_remaining": int, "message": str}
        """
        status = self.cred_manager.check_password_expiration(self.system_name)

        if status["warning_level"] in ("expired", "1_day", "7_day"):
            return {
                "should_rotate": True,
                "days_remaining": status["days_remaining"],
                "message": (
                    f"Drake password expires in {status['days_remaining']} days. "
                    f"Recommend rotating now."
                ),
            }

        return {
            "should_rotate": False,
            "days_remaining": status["days_remaining"],
            "message": "Password OK.",
        }

    # ── Virtual Drive — TaxDome Client Files ─────────────────────

    def get_client_documents(self, client_folder: str) -> List[dict]:
        """
        List available documents for a client from the TaxDome virtual drive.

        The AWS WorkSpace has mapped drives that sync with TaxDome's
        document storage. This allows the agent to access client files
        (W-2s, 1099s, organizers, bank statements, etc.) directly from
        the filesystem without needing TaxDome browser automation.

        Args:
            client_folder: Client folder name on the virtual drive

        Returns:
            List of document dicts:
            [{"filename": "W-2_Employer.pdf", "path": "T:\ClientName\2025\W-2_Employer.pdf",
              "type": "w2", "size_bytes": 12345, "modified": "2026-03-28"}]

        SECURITY: Client documents are confidential (IRC §7216).
        - NEVER log filenames containing client PII
        - NEVER copy files outside the approved system boundary
        - Documents are READ-ONLY from the agent's perspective
        """
        if not self.taxdome_drive_path:
            return []

        client_path = os.path.join(self.taxdome_drive_path, client_folder)
        if not os.path.exists(client_path):
            return []

        documents = []
        try:
            for root, dirs, files in os.walk(client_path):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    stat = os.stat(filepath)
                    doc_type = self._classify_document(filename)
                    documents.append({
                        "filename": filename,
                        "path": filepath,
                        "type": doc_type,
                        "size_bytes": stat.st_size,
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime
                        ).strftime("%Y-%m-%d"),
                    })
        except PermissionError:
            pass  # Drive may not be mounted or accessible

        return documents

    def _classify_document(self, filename: str) -> str:
        """
        Classify a document by its filename into a tax document type.

        Returns: "w2", "1099", "1098", "organizer", "bank_statement",
                 "id", "prior_return", "other"
        """
        name_lower = filename.lower()

        if "w-2" in name_lower or "w2" in name_lower:
            return "w2"
        elif "1099" in name_lower:
            # Sub-classify 1099s
            if "int" in name_lower:
                return "1099_int"
            elif "div" in name_lower:
                return "1099_div"
            elif "nec" in name_lower or "misc" in name_lower:
                return "1099_nec"
            elif "r" in name_lower and "1099" in name_lower:
                return "1099_r"
            return "1099"
        elif "1098" in name_lower:
            return "1098"
        elif "organizer" in name_lower:
            return "organizer"
        elif "bank" in name_lower or "statement" in name_lower:
            return "bank_statement"
        elif "license" in name_lower or "id" in name_lower or "passport" in name_lower:
            return "id"
        elif "prior" in name_lower or "return" in name_lower:
            return "prior_return"
        else:
            return "other"

    def check_virtual_drive(self) -> dict:
        """
        Check if the TaxDome virtual drive is accessible.

        Returns:
            {"available": bool, "path": str, "message": str}
        """
        if not self.taxdome_drive_path:
            return {
                "available": False,
                "path": "",
                "message": "TAXDOME_VIRTUAL_DRIVE not configured",
            }

        if os.path.exists(self.taxdome_drive_path):
            return {
                "available": True,
                "path": self.taxdome_drive_path,
                "message": "TaxDome virtual drive accessible",
            }
        else:
            return {
                "available": False,
                "path": self.taxdome_drive_path,
                "message": "TaxDome virtual drive not mounted or accessible",
            }

    # ── Status ────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get current Drake status for reporting."""
        pw_status = self.cred_manager.check_password_expiration(self.system_name)

        drive_status = self.check_virtual_drive()

        return {
            "is_open": self.is_drake_open,
            "session_start": (
                self.session_start_time.strftime("%H:%M CT")
                if self.session_start_time else None
            ),
            "returns_processed_today": self.returns_processed_today,
            "password_days_remaining": pw_status["days_remaining"],
            "password_warning": pw_status["warning_level"],
            "login_blocked": self.cred_manager.is_login_blocked(self.system_name),
            "virtual_drive_available": drive_status["available"],
        }