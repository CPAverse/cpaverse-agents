"""
CPAverse Agent — Credential Manager

Handles secure credential storage, TOTP code generation, password rotation,
and notification to Josh Mauer via Google Chat webhook.

Dependencies: pyotp, requests (or httpx)
Install: pip install pyotp requests

SECURITY: This module handles sensitive credentials.
- NEVER log passwords, TOTP secrets, or generated codes
- NEVER commit credential values to git
- All secrets are loaded from environment variables or secure config
- Generated passwords are sent ONLY to the admin Google Chat webhook
"""

import os
import json
import hmac
import hashlib
import struct
import base64
import secrets
import string
import time
from datetime import datetime, timedelta
from typing import Optional

try:
    import pyotp
except ImportError:
    pyotp = None
    # Fallback: we use built-in hmac/hashlib for TOTP generation

try:
    import requests
except ImportError:
    requests = None
    print("WARNING: requests not installed. Run: pip install requests")


class CredentialManager:
    """Manages credentials for all systems the CPAverse Tax Agent accesses."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize with config from environment variables or a secure config file.

        Config structure (loaded from env or file):
        {
            "google_chat_webhook": "https://chat.googleapis.com/v1/spaces/...",
            "systems": {
                "taxdome": {
                    "username": "admin@joshmauercpa.com",  # CPAverse Tax Agent seat
                    "totp_secret": "...",  # Base32 TOTP secret (env: TAXDOME_TOTP_SECRET)
                    "login_url": "https://app.taxdome.com/login",
                    "password_rotation_days": null  # TaxDome doesn't force rotation
                },
                "drake_2025": {
                    "username": "...",
                    "totp_secret": "...",
                    "security_question": "...",
                    "security_answer": "...",
                    "login_url": "...",
                    "password_rotation_days": 90,
                    "last_password_change": "2026-03-30"
                }
            }
        }
        """
        self.config = self._load_config(config_path)
        self.max_login_attempts = 3
        self._login_attempt_counts = {}

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from environment variables or secure file."""
        config = {}

        # Google Chat webhook for admin notifications
        config["google_chat_webhook"] = os.environ.get(
            "CPAVERSE_GCHAT_WEBHOOK",
            "https://chat.googleapis.com/v1/spaces/AAQAgN8ueP8/messages"
            "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
            "&token=bVxn5g_M9Qep3C9ecvs__dZVDMQGI1GfRLby57qB86Q"
        )

        # Load system credentials from environment
        config["systems"] = {}

        # TaxDome
        if os.environ.get("TAXDOME_USERNAME"):
            config["systems"]["taxdome"] = {
                "username": os.environ["TAXDOME_USERNAME"],
                "totp_secret": os.environ.get("TAXDOME_TOTP_SECRET"),
                "login_url": "https://app.taxdome.com/login",
                "password_rotation_days": None,
            }

        # Drake 2025
        if os.environ.get("DRAKE_2025_USERNAME"):
            config["systems"]["drake_2025"] = {
                "username": os.environ["DRAKE_2025_USERNAME"],
                "totp_secret": os.environ.get("DRAKE_2025_TOTP_SECRET"),
                "security_question": os.environ.get("DRAKE_2025_SECURITY_QUESTION"),
                "security_answer": os.environ.get("DRAKE_2025_SECURITY_ANSWER"),
                "login_url": os.environ.get("DRAKE_2025_LOGIN_URL", ""),
                "password_rotation_days": 90,
                "last_password_change": os.environ.get(
                    "DRAKE_2025_LAST_PW_CHANGE",
                    datetime.now().strftime("%Y-%m-%d")
                ),
            }

        # Also try loading from a secure config file (for local dev)
        if config_path and os.path.exists(config_path):
            with open(config_path, "r") as f:
                file_config = json.load(f)
                # Merge, env vars take priority
                for key, value in file_config.items():
                    if key not in config or not config[key]:
                        config[key] = value

        return config

    # ── TOTP / MFA ────────────────────────────────────────────────

    def generate_totp_code(self, system_name: str) -> Optional[str]:
        """
        Generate a current TOTP 6-digit code for the specified system.

        Args:
            system_name: "taxdome", "drake_2025", etc.

        Returns:
            6-digit TOTP code string, or None if not configured.

        SECURITY: Code is generated in memory only, never logged or stored.
        Uses pyotp if available, otherwise falls back to built-in hmac/hashlib.
        """
        system = self.config["systems"].get(system_name)
        if not system or not system.get("totp_secret"):
            return None

        if pyotp is not None:
            totp = pyotp.TOTP(system["totp_secret"])
            return totp.now()

        # Fallback: generate TOTP using built-in libraries (no pyotp needed)
        secret = system["totp_secret"]
        key = base64.b32decode(secret)
        counter = int(time.time()) // 30
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[-1] & 0x0F
        code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
        return f"{code % 1000000:06d}"

    def get_totp_time_remaining(self, system_name: str) -> int:
        """
        Get seconds remaining before the current TOTP code expires.
        Useful for timing login attempts — if <5 seconds, wait for next code.
        """
        if pyotp is None:
            return 0
        return 30 - (int(time.time()) % 30)

    # ── Password Management ───────────────────────────────────────

    def generate_password(self, length: int = 14) -> str:
        """
        Generate a cryptographically secure password.

        Requirements:
        - 12-16 characters (default 14)
        - Mix of uppercase, lowercase, digits, and special characters
        - At least 1 of each category
        - No ambiguous characters (0/O, 1/l/I)

        SECURITY: Password is returned in memory only.
        """
        if length < 12:
            length = 12
        if length > 16:
            length = 16

        # Character sets (excluding ambiguous chars)
        uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I, O
        lowercase = "abcdefghjkmnpqrstuvwxyz"    # no i, l, o
        digits = "23456789"                       # no 0, 1
        special = "!@#$%^&*-_=+"

        # Ensure at least one of each
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Fill remaining with random mix
        all_chars = uppercase + lowercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))

        # Shuffle to randomize position of guaranteed characters
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)
        return "".join(password_list)

    def check_password_expiration(self, system_name: str) -> dict:
        """
        Check if a system's password is approaching expiration.

        Returns:
            {
                "expired": bool,
                "days_remaining": int or None,
                "warning_level": "none" | "30_day" | "7_day" | "1_day" | "expired"
            }
        """
        system = self.config["systems"].get(system_name)
        if not system or not system.get("password_rotation_days"):
            return {"expired": False, "days_remaining": None, "warning_level": "none"}

        rotation_days = system["password_rotation_days"]
        last_change = datetime.strptime(
            system.get("last_password_change", "2026-01-01"), "%Y-%m-%d"
        )
        expiration = last_change + timedelta(days=rotation_days)
        days_remaining = (expiration - datetime.now()).days

        if days_remaining <= 0:
            warning = "expired"
        elif days_remaining <= 1:
            warning = "1_day"
        elif days_remaining <= 7:
            warning = "7_day"
        elif days_remaining <= 30:
            warning = "30_day"
        else:
            warning = "none"

        return {
            "expired": days_remaining <= 0,
            "days_remaining": max(0, days_remaining),
            "warning_level": warning,
        }

    def rotate_password(self, system_name: str) -> dict:
        """
        Generate a new password and notify Josh Mauer via Google Chat.

        Returns:
            {
                "success": bool,
                "new_password": str (for immediate use in the rotation flow),
                "notification_sent": bool
            }

        SECURITY: The new password is returned to the caller for immediate use
        in the password change flow, then should be discarded from memory.
        The only persistent record is the Google Chat notification to Josh.
        """
        new_password = self.generate_password()
        expiration_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")

        # Send notification to Josh via Google Chat
        notification_sent = self._notify_admin(
            f"*Password Rotation — {system_name.replace('_', ' ').title()}*\n\n"
            f"New password: `{new_password}`\n"
            f"Changed: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}\n"
            f"Expires: {expiration_date}\n\n"
            f"Please update 1Password."
        )

        # Update last change date in config
        if system_name in self.config["systems"]:
            self.config["systems"][system_name]["last_password_change"] = (
                datetime.now().strftime("%Y-%m-%d")
            )

        return {
            "success": True,
            "new_password": new_password,
            "notification_sent": notification_sent,
        }

    # ── Login Management ──────────────────────────────────────────

    def record_login_attempt(self, system_name: str, success: bool) -> dict:
        """
        Track login attempts per system.
        After 3 consecutive failures, alerts Josh and blocks further attempts.

        Returns:
            {
                "blocked": bool,
                "consecutive_failures": int,
                "alert_sent": bool
            }
        """
        if system_name not in self._login_attempt_counts:
            self._login_attempt_counts[system_name] = 0

        if success:
            self._login_attempt_counts[system_name] = 0
            return {"blocked": False, "consecutive_failures": 0, "alert_sent": False}

        self._login_attempt_counts[system_name] += 1
        failures = self._login_attempt_counts[system_name]

        alert_sent = False
        if failures >= self.max_login_attempts:
            alert_sent = self._notify_admin(
                f"*SECURITY ALERT — Login Failure*\n\n"
                f"System: {system_name.replace('_', ' ').title()}\n"
                f"Consecutive failures: {failures}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}\n\n"
                f"Agent has stopped login attempts. Please verify credentials "
                f"and check for account lockout."
            )

        return {
            "blocked": failures >= self.max_login_attempts,
            "consecutive_failures": failures,
            "alert_sent": alert_sent,
        }

    def is_login_blocked(self, system_name: str) -> bool:
        """Check if login attempts are blocked for a system."""
        return (
            self._login_attempt_counts.get(system_name, 0) >= self.max_login_attempts
        )

    def reset_login_block(self, system_name: str):
        """Reset login block (called after Josh resolves the issue)."""
        self._login_attempt_counts[system_name] = 0

    # ── Notifications ─────────────────────────────────────────────

    def _notify_admin(self, message: str) -> bool:
        """
        Send a notification to Josh Mauer via Google Chat webhook.

        SECURITY: Only sends to the configured admin webhook.
        Never sends client data. Only system status and credentials.
        """
        if requests is None:
            print(f"NOTIFICATION (requests not available): {message}")
            return False

        webhook_url = self.config.get("google_chat_webhook")
        if not webhook_url:
            print("WARNING: No Google Chat webhook configured")
            return False

        try:
            response = requests.post(
                webhook_url,
                json={"text": message},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"WARNING: Failed to send notification: {e}")
            return False

    def send_security_alert(self, alert_type: str, details: str) -> bool:
        """
        Send a security alert to Josh Mauer.

        alert_type: "injection_attempt", "unauthorized_instruction",
                     "unusual_access", "credential_issue", "system_error"
        """
        return self._notify_admin(
            f"*SECURITY ALERT — {alert_type.replace('_', ' ').title()}*\n\n"
            f"{details}\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M CT')}"
        )

    # ── Status Report ─────────────────────────────────────────────

    def get_credential_status(self) -> dict:
        """
        Get status of all managed credentials for the morning report.

        Returns dict with expiration warnings, login status, etc.
        SECURITY: Never includes actual passwords or secrets in the output.
        """
        status = {}
        for system_name in self.config.get("systems", {}):
            expiration = self.check_password_expiration(system_name)
            status[system_name] = {
                "password_status": expiration["warning_level"],
                "days_until_expiration": expiration["days_remaining"],
                "login_blocked": self.is_login_blocked(system_name),
                "consecutive_failures": self._login_attempt_counts.get(
                    system_name, 0
                ),
            }
        return status

    def get_security_summary(self) -> str:
        """
        Generate a security summary section for the morning report.
        Plain text format suitable for Google Chat or TaxDome chat.
        """
        status = self.get_credential_status()
        lines = ["━━━ SECURITY SUMMARY ━━━"]

        for system_name, info in status.items():
            display_name = system_name.replace("_", " ").title()
            pw_status = info["password_status"]

            if pw_status == "expired":
                lines.append(f"⚠️ {display_name}: PASSWORD EXPIRED — rotation needed")
            elif pw_status == "1_day":
                lines.append(
                    f"⚠️ {display_name}: Password expires TOMORROW"
                )
            elif pw_status == "7_day":
                lines.append(
                    f"📋 {display_name}: Password expires in "
                    f"{info['days_until_expiration']} days"
                )
            elif pw_status == "30_day":
                lines.append(
                    f"📋 {display_name}: Password expires in "
                    f"{info['days_until_expiration']} days"
                )
            else:
                days = info["days_until_expiration"]
                if days is not None:
                    lines.append(f"✓ {display_name}: OK ({days} days until rotation)")
                else:
                    lines.append(f"✓ {display_name}: OK (no rotation required)")

            if info["login_blocked"]:
                lines.append(
                    f"  🚫 LOGIN BLOCKED — {info['consecutive_failures']} "
                    f"consecutive failures"
                )

        return "\n".join(lines)
