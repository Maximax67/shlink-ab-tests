"""
Google Forms field mapping service with caching
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict
from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from app.config import get_settings

logger = logging.getLogger(__name__)


class GoogleFormsFieldMapper:
    """
    Service for mapping Google Forms field names to entry IDs
    with built-in caching
    """

    def __init__(self, service_account_file: str):
        """
        Initialize Google Forms API client

        Args:
            service_account_file: Path to service account JSON file
        """
        self.service_account_file = service_account_file
        self.cache: Dict[tuple[str, str], tuple[str, datetime]] = (
            {}
        )  # (form_id, field_name) -> (entry_id, timestamp)
        self.form_cache: Dict[str, tuple[Dict[str, Any], datetime]] = (
            {}
        )  # form_id -> (form_data, timestamp)
        self.cache_ttl = timedelta(minutes=15)
        self.form_cache_ttl = timedelta(minutes=2)
        self._service = None

    @property
    def service(self) -> Any:
        """Lazy load Google Forms API service"""
        if self._service is None:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=["https://www.googleapis.com/auth/forms.body.readonly"],
                )  # type: ignore[no-untyped-call]
                self._service = build("forms", "v1", credentials=credentials)
                logger.info("Google Forms API service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Forms API: {e}")
                raise
        return self._service

    def _get_form(self, form_id: str) -> Optional[Dict[str, Any]]:
        """Get Google Form structure with caching"""
        now = datetime.now(timezone.utc)

        if form_id in self.form_cache:
            form_data, timestamp = self.form_cache[form_id]
            if now - timestamp <= self.form_cache_ttl:
                logger.debug(f"Form cache hit for {form_id}")
                return form_data

            logger.debug(f"Form cache expired for {form_id}")
            del self.form_cache[form_id]

        try:
            data: Dict[str, Any] = self.service.forms().get(formId=form_id).execute()
            print(json.dumps(data, indent=2))
            self.form_cache[form_id] = (data, now)
            logger.info(f"Fetched and cached form data for {form_id}")
            return data

        except HttpError as e:
            logger.error(f"Google Forms API error for form {form_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching form structure: {e}")
            return None

    def get_field_entry_id(self, form_id: str, field_name: str) -> Optional[str]:
        """
        Get entry ID for a field name with caching

        Args:
            form_id: Google Forms ID
            field_name: Name/title of the field to find

        Returns:
            Entry ID (e.g., "entry.123456789") or None if not found
        """
        cache_key = (form_id, field_name)
        entry_id: Optional[str] = None

        if cache_key in self.cache:
            entry_id, timestamp = self.cache[cache_key]
            age = datetime.now(timezone.utc) - timestamp

            if age <= self.cache_ttl:
                logger.debug(f"Cache hit for {form_id}:{field_name}")
                return entry_id

            logger.debug(f"Cache expired for {form_id}:{field_name}")
            del self.cache[cache_key]

        entry_id = self._fetch_field_entry_id(form_id, field_name)

        if entry_id:
            self.cache[cache_key] = (entry_id, datetime.now(timezone.utc))

        return entry_id

    def is_form_accessible(self, form_id: str) -> bool:
        return bool(self._get_form(form_id))

    def _fetch_field_entry_id(self, form_id: str, field_name: str) -> Optional[str]:
        """
        Fetch field entry ID from Google Forms API

        Args:
            form_id: Google Forms ID
            field_name: Name/title of the field

        Returns:
            Entry ID or None if not found
        """
        form = self._get_form(form_id)
        if not form:
            return None

        items = form.get("items", [])
        field_name_lower = field_name.lower()

        for item in items:
            title = item.get("title", "").lower()
            description = item.get("description", "").lower()

            if field_name_lower in title or field_name_lower in description:
                question = item.get("questionItem", {}).get("question", {})
                question_id = question.get("questionId")
                if question_id:
                    entry_id = f"entry.{question_id}"
                    logger.info(
                        f"Found entry ID {entry_id} for field '{field_name}' in form {form_id}"
                    )
                    return entry_id

        logger.warning(f"Field '{field_name}' not found in form {form_id}")
        return None

    def clear_cache(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        self.form_cache.clear()
        logger.info("Google Forms caches cleared")

    def clear_expired_cache(self) -> None:
        """Remove expired entries from all caches"""
        now = datetime.now(timezone.utc)

        self.cache = {
            k: v for k, v in self.cache.items() if now - v[1] <= self.cache_ttl
        }

        self.form_cache = {
            k: v
            for k, v in self.form_cache.items()
            if now - v[1] <= self.form_cache_ttl
        }


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
        _forms_mapper = GoogleFormsFieldMapper(settings.google_credentials_path)

    return _forms_mapper
