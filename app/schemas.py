"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


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

    class Config:
        from_attributes = True


class ShortUrlResponse(BaseModel):
    """Schema for short URL response"""

    id: int
    short_code: str
    original_url: str
    redirect_url: Optional[str]
    title: Optional[str]
    date_created: datetime
    max_visits: Optional[int]

    class Config:
        from_attributes = True


class ShortUrlWithTests(ShortUrlResponse):
    """Schema for short URL with A/B tests"""

    ab_tests: list[ABTestResponse] = []
    total_probability: float = Field(default=0.0)

    class Config:
        from_attributes = True


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
