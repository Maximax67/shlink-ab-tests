from datetime import datetime, timedelta, timezone
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.google_forms import get_forms_mapper
from app.config import get_settings
from app.models.visit import Visit
from app.models.google_form import GoogleForm

logger = logging.getLogger(__name__)
settings = get_settings()


class UrlBuilder:

    @staticmethod
    def build_url(
        target_url: str,
        forward_query: bool,
        query_params: Dict[str, str],
        last_visit: Optional[Visit] = None,
        include_form_params: bool = True,
        db: Optional[Session] = None,
    ) -> str:
        """
        Build final redirect URL with query parameters

        Args:
            target_url: Base target URL
            forward_query: Whether to forward query parameters
            query_params: Query parameters from request
            last_visit: Last visit record
            include_form_params: Whether to include Google Forms params
            db: Database session (required for Google Forms)

        Returns:
            Final redirect URL
        """
        parsed = urlparse(target_url)

        # Start with existing query params from target URL
        existing_params = parse_qs(parsed.query)
        final_params = {k: v[0] for k, v in existing_params.items()}

        # Add forwarded query params if enabled
        if forward_query and query_params:
            final_params.update(query_params)

        # Handle Google Forms prefilling
        if include_form_params and "docs.google.com/forms" in target_url and db:
            final_params = UrlBuilder._add_google_forms_params(
                target_url, final_params, query_params, last_visit, db
            )

        # Rebuild URL with new query params
        new_query = urlencode(final_params)
        redirect_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

        return redirect_url

    @staticmethod
    def _add_google_forms_params(
        target_url: str,
        params: Dict[str, str],
        query_params: Dict[str, str],
        last_visit: Optional[Visit],
        db: Session,
    ) -> Dict[str, Any]:
        """
        Add Google Forms prefill parameters using API

        Args:
            target_url: Target Google Forms URL
            params: Existing URL parameters
            query_params: Query parameters from request
            last_visit: Last visit record
            db: Database session

        Returns:
            Updated parameters dict with Google Forms entry IDs
        """

        try:
            # Extract responder form ID from URL
            responder_form_id = UrlBuilder.extract_form_id(target_url)
            if not responder_form_id:
                logger.warning("Could not extract responder form ID from URL")
                return params

            # Look up edit form ID in database
            google_form = db.execute(
                select(GoogleForm).where(
                    GoogleForm.responder_form_id == responder_form_id
                )
            ).scalar_one_or_none()

            if not google_form:
                logger.warning(
                    f"⚠️  Google Form not connected: {responder_form_id}. "
                    f"Add this form in admin dashboard to enable auto-filling."
                )
                return params

            # Use edit form ID for API calls
            form_id = google_form.form_id
            logger.info(
                f"Using edit form ID {form_id} for responder form {responder_form_id}"
            )

            # Get forms mapper
            mapper = get_forms_mapper()

            if not mapper.is_form_accessible(form_id):
                logger.warning(f"Form {form_id} not accessible via API")
                return params

            # Map utm_source if present
            if "utm_source" in query_params:
                entry_id = mapper.get_field_entry_id(form_id, "utm_source")
                if entry_id:
                    params[f"entry.{entry_id}"] = query_params["utm_source"]
                    logger.info(f"Mapped utm_source to {entry_id}")

                del query_params["utm_source"]

            # Map utm_medium if present
            if "utm_medium" in query_params:
                entry_id = mapper.get_field_entry_id(form_id, "utm_medium")
                if entry_id:
                    params[f"entry.{entry_id}"] = query_params["utm_medium"]
                    logger.info(f"Mapped utm_medium to {entry_id}")

                del query_params["utm_medium"]

            # Map utm_campaign if present
            if "utm_campaign" in query_params:
                entry_id = mapper.get_field_entry_id(form_id, "utm_campaign")
                if entry_id:
                    params[f"entry.{entry_id}"] = query_params["utm_campaign"]
                    logger.info(f"Mapped utm_campaign to {entry_id}")

                del query_params["utm_campaign"]

            # Map click_id if appropriate
            if last_visit and UrlBuilder.should_include_click_id(last_visit):
                entry_id = mapper.get_field_entry_id(form_id, "click_id")
                if entry_id:
                    params[f"entry.{entry_id}"] = str(last_visit.id)
                    logger.info(f"Mapped click_id to {entry_id}")

                time_entry_id = mapper.get_field_entry_id(form_id, "click_timestamp")
                if time_entry_id:
                    params[f"entry.{time_entry_id}"] = str(last_visit.date)
                    logger.info(f"Mapped click_timestamp to {time_entry_id}")

            return params

        except Exception as e:
            logger.error(f"Error adding Google Forms params: {e}")
            # Return params unchanged on error
            return params

    @staticmethod
    def extract_form_id(url: str) -> Optional[str]:
        """
        Extract Google Forms ID from URL (responder or edit format)

        Args:
            url: Google Forms URL

        Returns:
            Form ID or None
        """
        try:
            if not url:
                return None

            patterns = [
                r"/d/e/([a-zA-Z0-9_-]+)",
                r"/d/([a-zA-Z0-9_-]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            logger.error(f"Error extracting form ID from URL: {e}")
            return None

    @staticmethod
    def should_include_click_id(last_visit: Visit) -> bool:
        """
        Determine if click_id should be included based on last visit time

        Args:
            last_visit: Last visit record

        Returns:
            True if click_id should be included
        """

        if last_visit.date.tzinfo is None:
            last_visit_date = last_visit.date.replace(tzinfo=timezone.utc)
        else:
            last_visit_date = last_visit.date

        time_diff = datetime.now(timezone.utc) - last_visit_date
        max_age = timedelta(seconds=settings.click_id_max_age_seconds)

        return time_diff <= max_age

    @staticmethod
    def get_redirect_url(original_url: str) -> Optional[str]:
        """Extract the redirect-url from the original_url query parameter."""
        try:
            parsed = urlparse(original_url)
            query_params = parse_qs(parsed.query)

            redirect_url = query_params.get("url", [None])[0]
            if redirect_url is None:
                return None

            del query_params["url"]

            string_params: Dict[str, str] = {}

            for param, value in query_params.items():
                string_params[param] = value[0] if len(value) == 1 else str(value)

            return UrlBuilder.build_url(
                redirect_url,
                True,
                string_params,
                None,
                False,
            )
        except Exception:
            return None
