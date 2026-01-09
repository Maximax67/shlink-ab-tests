"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_serializer


class ABTestBase(BaseModel):
    """Base schema for A/B test"""

    target_url: str = Field(..., min_length=1)
    probability: float = Field(..., ge=0.0, le=1.0)
    is_active: bool = True


class ABTestCreate(ABTestBase):
    """Schema for creating A/B test"""

    pass


class ABTestUpdate(BaseModel):
    """Schema for updating A/B test"""

    target_url: Optional[str] = Field(None, min_length=1)
    probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None


class ABTestResponse(ABTestBase):
    """Schema for A/B test response"""

    id: int
    short_url_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class ShortUrlResponse(BaseModel):
    """Schema for short URL response"""

    id: int
    short_code: str
    original_url: str
    redirect_url: Optional[str]
    title: Optional[str]
    date_created: datetime
    max_visits: Optional[int]

    model_config = ConfigDict(
        from_attributes=True,
    )


class ShortUrlWithTests(ShortUrlResponse):
    """Schema for short URL with A/B tests"""

    ab_tests: list[ABTestResponse] = []
    total_probability: float = Field(default=0.0)

    model_config = ConfigDict(
        from_attributes=True,
    )


class LoginRequest(BaseModel):
    """Schema for admin login"""

    token: str = Field(..., min_length=1)


class RedirectStats(BaseModel):
    """Schema for redirect statistics"""

    short_code: str
    target_url: str
    is_ab_test: bool
    ab_test_id: Optional[int] = None
    timestamp: datetime


class VisitLocationSchema(BaseModel):
    """Schema for visit location"""

    id: int
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    region_name: Optional[str] = None
    city_name: Optional[str] = None
    timezone: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_empty: bool = True

    model_config = ConfigDict(from_attributes=True)

    @model_serializer
    def custom_serializer(self) -> Dict[str, Any]:
        if self.is_empty:
            return {
                "id": self.id,
                "is_empty": True,
            }

        return {
            "id": self.id,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "region_name": self.region_name,
            "city_name": self.city_name,
            "timezone": self.timezone,
            "lat": self.lat,
            "lon": self.lon,
            "is_empty": False,
        }


class VisitWithLocationSchema(BaseModel):
    """Schema for visit with location data"""

    id: int
    referer: Optional[str] = None
    date: datetime
    remote_addr: Optional[str] = None
    user_agent: Optional[str] = None
    visited_url: Optional[str] = None
    type: str
    potential_bot: bool
    redirect_url: Optional[str] = None
    short_url_id: Optional[int] = None
    visit_location_id: Optional[int] = None
    location: Optional[VisitLocationSchema] = None

    model_config = ConfigDict(from_attributes=True)


class ShortUrlSyncSchema(BaseModel):
    """Schema for short URL sync"""

    id: int
    original_url: str
    short_code: str
    date_created: datetime
    valid_since: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    max_visits: Optional[int] = None
    import_source: Optional[str] = None
    import_original_short_code: Optional[str] = None
    title: Optional[str] = None
    title_was_auto_resolved: bool
    crawlable: bool
    forward_query: bool
    domain_id: Optional[int] = None
    author_api_key_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SyncResponse(BaseModel):
    """Generic sync response wrapper"""

    total: int
    limit: int
    offset: int
    data: List[Any]
