"""Scraping session metadata schema."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScrapingSession(BaseModel):
    """Metadata for scraping sessions."""

    session_id: str = Field(..., description="Unique session identifier")
    roaster_name: str = Field(..., description="Name of the roaster being scraped")
    started_at: datetime = Field(default_factory=datetime.now, description="Session start time")
    ended_at: datetime | None = Field(None, description="Session end time")

    # Results
    success: bool = Field(False, description="Whether scraping was successful")
    beans_found: int = Field(0, ge=0, description="Number of beans found")
    beans_processed: int = Field(0, ge=0, description="Number of beans successfully processed")
    errors: list[str] = Field(default_factory=list, description="List of error messages")

    # Configuration used
    scraper_version: str = Field("1.0", description="Scraper version")
    config_used: dict[str, Any] | None = Field(None, description="Scraping configuration used")

    # Performance metrics
    duration_seconds: float | None = Field(None, ge=0, description="Total duration in seconds")
    pages_scraped: int = Field(0, ge=0, description="Number of pages scraped")
    requests_made: int = Field(0, ge=0, description="Total HTTP requests made")

    def mark_completed(self, success: bool = True):
        """Mark the session as completed."""
        self.ended_at = datetime.now()
        self.success = success
        if self.started_at and self.ended_at:
            self.duration_seconds = (self.ended_at - self.started_at).total_seconds()

    def add_error(self, error_message: str):
        """Add an error message to the session."""
        self.errors.append(error_message)

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        validate_assignment=True
    )
