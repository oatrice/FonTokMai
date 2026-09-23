import pytest
from app.core.dev_settings import DevSettings, get_dev_settings, update_dev_settings

def test_dev_settings_defaults():
    settings = get_dev_settings()
    assert isinstance(settings, DevSettings)
    assert settings.use_local_fixtures is False
    assert settings.use_skn240_backup is False
    assert settings.flow_mode == "average"
    assert settings.search_radius == 80
    assert settings.min_dbz == 10.0
    assert settings.cluster_min == 3
    assert settings.dot_threshold == 0.6
    assert settings.min_ambient_dbz == 20.0
    assert settings.min_ambient_size == 15
    assert settings.prediction_steps == 13
    assert settings.decay_enabled is True
    assert settings.hit_radius == 7
    assert settings.verbose is False
    assert settings.show_trajectory is True

def test_dev_settings_update():
    settings = get_dev_settings()
    # Verify initial state
    assert settings.verbose is False
    
    # Update state
    updated_settings = update_dev_settings({"verbose": True, "min_dbz": 15.0})
    
    # Verify new state
    assert updated_settings.verbose is True
    assert updated_settings.min_dbz == 15.0
    
    # Verify singleton was updated
    current_settings = get_dev_settings()
    assert current_settings.verbose is True
    assert current_settings.min_dbz == 15.0
    
    # Reset for other tests
    update_dev_settings({"verbose": False, "min_dbz": 10.0})

def test_dev_settings_update_invalid_key_ignored():
    original_dict = get_dev_settings().model_dump()
    updated = update_dev_settings({"non_existent_key": "value"})
    assert updated.model_dump() == original_dict
