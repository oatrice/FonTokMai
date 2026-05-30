import pytest
from app.repositories.base import LocationRepository

def test_location_repository_is_abstract():
    with pytest.raises(TypeError):
        # Should raise TypeError: Can't instantiate abstract class LocationRepository
        # with abstract methods get_active_locations, get_location, save_location, update_last_alerted
        LocationRepository()
