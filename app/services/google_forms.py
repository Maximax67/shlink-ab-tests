"""
Google Forms field mapping service with caching
"""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional, Dict, Set
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
import requests

from app.config import get_settings
from app.models.form_entry import FormEntry
from app.models.google_form import GoogleForm

logger = logging.getLogger(__name__)


class GoogleFormsFieldMapper:
    """
    Service for mapping Google Forms field names to entry IDs
    with built-in caching
    """

    def __init__(
        self,
        app_script_url: str,
        app_script_api_token: str,
        fields_to_cache: Set[str] = set(
            [
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "click_id",
                "click_timestamp",
            ]
        ),
    ):
        """
        Initialize Google Forms API client

        Args:
            app_script_url: URL to hosted App Script
            app_script_api_token: App Script API token
            fields_to_cache: Google form fields to cache
        """
        self.app_script_url = app_script_url
        self.app_script_api_token = app_script_api_token
        self.fields_to_cache = fields_to_cache

    def get_form(self, form_id: str) -> Optional[Dict[str, Any]]:
        headers = {"Accept": "application/json"}
        params = {"formId": form_id, "token": self.app_script_api_token}

        try:
            response = requests.get(self.app_script_url, params=params, headers=headers)
            response.raise_for_status()

            data: Dict[str, Any] = response.json()
            status_code = data["status"]
            if status_code != 200:
                raise Exception(
                    f"Request error {status_code}: {data.get("error", "Unknown error")}"
                )

            return data
        except Exception as e:
            logger.error(e)

            return None

    @staticmethod
    def get_form_entries(db: Session, form_id: str) -> List[FormEntry]:
        entries_q = (
            select(FormEntry).join(GoogleForm).where(GoogleForm.form_id == form_id)
        )
        entries_res = db.execute(entries_q)
        entries_list = list(entries_res.scalars().all())

        return entries_list

    @staticmethod
    def get_field_to_entry_mappings(db: Session, form_id: str) -> Dict[str, int]:
        entries_list = GoogleFormsFieldMapper.get_form_entries(db, form_id)
        mappings: Dict[str, int] = {}
        for entry in entries_list:
            mappings[entry.title] = entry.entry_id

        return mappings

    def update_mapping(self, db: Session, form_id: str, data: Dict[str, Any]) -> None:
        saved_entries_list = self.get_form_entries(db, form_id)
        saved_entries: Dict[str, FormEntry] = {}
        for entry in saved_entries_list:
            saved_entries[entry.title] = entry

        if len(saved_entries_list):
            google_form_id = saved_entries_list[0].google_form_id
        else:
            form_id_q = select(GoogleForm.id).where(GoogleForm.form_id == form_id)
            form_id_res = db.execute(form_id_q)
            google_form_id = form_id_res.scalar_one()

        mapping = data["mapping"]
        for entry in mapping:
            title = entry["title"]
            if title in self.fields_to_cache:
                entry_id = entry["entryId"]
                saved_entry = saved_entries.pop(title, None)
                if saved_entry:
                    if saved_entry.entry_id != entry_id:
                        saved_entry.entry_id = entry_id
                        saved_entry.updated_at = datetime.now(timezone.utc)
                else:
                    new_entry = FormEntry(
                        title=title, entry_id=entry_id, google_form_id=google_form_id
                    )
                    db.add(new_entry)

        if saved_entries:
            db.execute(
                delete(FormEntry).where(
                    FormEntry.id.in_([c.id for c in saved_entries.values()])
                )
            )

        db.commit()


# Global instance (singleton pattern)
_forms_mapper: Optional[GoogleFormsFieldMapper] = None


def get_forms_mapper() -> GoogleFormsFieldMapper:
    """
    Get or create global GoogleFormsFieldMapper instance

    Returns:
        GoogleFormsFieldMapper instance
    """
    global _forms_mapper
    if _forms_mapper is None:
        settings = get_settings()
        _forms_mapper = GoogleFormsFieldMapper(
            settings.app_script_url, settings.app_script_api_key
        )

    return _forms_mapper
