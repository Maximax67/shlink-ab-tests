"""
Google Forms field mapping service with caching
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Dict, Set
import requests

from app.config import get_settings

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
        cache_ttl: timedelta = timedelta(minutes=15),
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
        """
        self.app_script_url = app_script_url
        self.app_script_api_token = app_script_api_token
        self.cache: Dict[tuple[str, str], tuple[int, datetime]] = (
            {}
        )  # (form_id, field_name) -> (entry_id, timestamp)
        self.cache_ttl = cache_ttl
        self.fields_to_cache = fields_to_cache

    def get_field_entry_id(self, form_id: str, field_name: str) -> Optional[int]:
        """
        Get entry ID for a field name with caching

        Args:
            form_id: Google Forms ID
            field_name: Name/title of the field to find

        Returns:
            Entry ID (e.g., "entry.123456789") or None if not found
        """
        cache_key = (form_id, field_name)
        entry_id: Optional[int] = None

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

            mapping = data["mapping"]
            for entry in mapping:
                title = entry["title"]
                if title in self.fields_to_cache:
                    self.cache[(form_id, title)] = (
                        entry["entryId"],
                        datetime.now(timezone.utc),
                    )

            return data
        except Exception as e:
            logger.error(e)

            return None

    def is_form_accessible(self, form_id: str) -> bool:
        return bool(self.get_form(form_id))

    def _fetch_field_entry_id(self, form_id: str, field_name: str) -> Optional[int]:
        """
        Fetch field entry ID from Google Forms API

        Args:
            form_id: Google Forms ID
            field_name: Name/title of the field

        Returns:
            Entry ID or None if not found
        """
        form = self.get_form(form_id)
        if not form:
            return None

        mapping = form["mapping"]
        for entry in mapping:
            if field_name == entry["title"]:
                entry_id: Optional[int] = entry["entryId"]
                return entry_id

        logger.warning(f"Field '{field_name}' not found in form {form_id}")

        return None

    def clear_cache(self) -> None:
        """Clear all cached entries"""
        self.cache.clear()
        logger.info("Google Forms cache cleared")

    def clear_expired_cache(self) -> None:
        """Remove expired entries from all caches"""
        now = datetime.now(timezone.utc)
        self.cache = {
            k: v for k, v in self.cache.items() if now - v[1] <= self.cache_ttl
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
        _forms_mapper = GoogleFormsFieldMapper(
            settings.app_script_url, settings.app_script_api_key
        )

    return _forms_mapper
