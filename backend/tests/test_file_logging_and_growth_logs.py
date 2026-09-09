import os
import logging
import pytest

def test_file_logging_handler_configuration(tmp_path, monkeypatch):
    """Verify that file logging handler is properly added and writes sensitive-filtered logs."""
    test_log_file = tmp_path / "test_backend.log"
    monkeypatch.setenv("LOG_FILE_PATH", str(test_log_file))

    # Import and run logging setup
    from app.main import setup_file_logging
    handler = setup_file_logging(str(test_log_file))
    
    assert handler is not None
    assert os.path.exists(test_log_file)
    
    # Directly emit a record through the handler to verify formatting and filtering
    test_logger = logging.getLogger("test_logger")
    record = test_logger.makeRecord(
        name="test_logger",
        level=logging.INFO,
        fn="test_file.py",
        lno=10,
        msg="Normal message with apikey=12345secret",
        args=(),
        exc_info=None
    )
    handler.handle(record)
    handler.flush()
    
    with open(test_log_file, "r") as f:
        content = f.read()
    
    assert "Normal message with apikey=***" in content
    assert "12345secret" not in content
    
    # Clean up handler from root
    logging.root.removeHandler(handler)
    handler.close()

def test_growth_decay_logging_in_weather_manager(caplog):
    """Verify that [GROWTH_DECAY] is logged when processing cloud clusters."""
    caplog.set_level(logging.INFO)
    
    from app.services import weather_manager
    cloud = {
        "label": "A",
        "cx": 100,
        "cy": 100,
        "dbz_now": 30.0,
        "dbz_prev": 20.0,
        "growth_rate": 0.5, # +50%
        "predicted_dbz": 35.0,
        "eta_min": 15.0
    }
    
    weather_manager.log_growth_decay_telemetry(
        target_label="A",
        dbz_now=cloud["dbz_now"],
        dbz_prev=cloud["dbz_prev"],
        growth_rate=cloud["growth_rate"],
        context="timeline_clustering"
    )
    
    assert "[GROWTH_DECAY]" in caplog.text
    assert "target=A" in caplog.text
    assert "now=30.0" in caplog.text
    assert "prev=20.0" in caplog.text
    assert "+50.0%" in caplog.text
    assert "trend=intensifying" in caplog.text
