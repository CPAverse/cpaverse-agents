"""
CPAverse Agent — Client Activity Logger

Writes structured activity reports to each client's "Office Use Only" folder
in TaxDome after every agent interaction. This is the agent's "paper trail"
— when it starts work on a client again, it reads the activity log to
reconstruct what has been done, what's pending, and what questions are open.

Report Format:
    Each interaction generates a timestamped report file:
        Office Use Only/
            agent_memory.json          ← Machine-readable (memory_manager.py)
            agent_activity_log.md      ← Human-readable running log
            agent_reports/
                2026-03-30_doc_review.md
                2026-03-30_data_entry.md

    The activity_log.md is append-only and always contains the full history.
    Individual reports in agent_reports/ are per-session snapshots.

Why Both Formats:
    - agent_memory.json: For the agent to "read up" quickly (structured data)
    - agent_activity_log.md: For Josh/Sarah/Adam to review what the agent did
      (human-readable, can be viewed in TaxDome's document viewer)

Circular 230 Compliance:
    - Every action is documented with timestamp, reasoning, and source
    - Professional judgments include the basis for the position taken
    - Flags and questions are clearly marked
    - Draft status is always indicated — nothing is final without CPA review

Dependencies: memory_manager.py (for accessing client memory)
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class ClientActivityLogger:
    """
    Writes human-readable and machine-parseable activity reports
    to each client's Office Use Only folder in TaxDome.
    """

    # Report types
    REPORT_DOC_REVIEW = "document_review"
    REPORT_DATA_ENTRY = "data_entry"
    REPORT_RETURN_REVIEW = "return_review"
    REPORT_CLIENT_COMM = "client_communication"
    REPORT_CALENDAR = "calendar_update"
    REPORT_GENERAL = "general"

    def __init__(self, taxdome_drive_path: Optional[str] = None):
        """
        Initialize the activity logger.

        Args:
            taxdome_drive_path: Base path to TaxDome virtual drive
                                (e.g., "T:\\" or "/mnt/taxdome/")
        """
        self.taxdome_drive = taxdome_drive_path or os.environ.get(
            "TAXDOME_VIRTUAL_DRIVE", ""
        )

    def get_client_folder(self, client_id: str,
                           client_name: str) -> str:
        """
        Get the path to a client's Office Use Only folder.

        TaxDome folder structure:
            {drive}/clients/{client_name}/Office Use Only/

        If the folder doesn't exist, create it.
        """
        safe_name = self._sanitize_folder_name(client_name)
        folder = os.path.join(
            self.taxdome_drive, "clients", safe_name, "Office Use Only"
        )
        os.makedirs(folder, exist_ok=True)

        reports_dir = os.path.join(folder, "agent_reports")
        os.makedirs(reports_dir, exist_ok=True)

        return folder
