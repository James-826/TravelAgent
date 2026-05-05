from datetime import date

import pytest

from app.models.travel import Location, TravelRequest


def test_location_requires_complete_coordinates() -> None:
    with pytest.raises(ValueError):
        Location(city="杭州", latitude=30.25)


def test_request_rejects_invalid_date_range() -> None:
    with pytest.raises(ValueError):
        TravelRequest(
            destination=Location(city="杭州"),
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 3),
        )

