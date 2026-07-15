import pytest
import respx
import httpx
from unittest.mock import patch
from app.services.telegram import setup_telegram_commands

@respx.mock
@pytest.mark.asyncio
async def test_setup_telegram_commands_production():
    # Arrange: set environment to production
    with patch.dict("os.environ", {"ENVIRONMENT": "production", "TELEGRAM_BOT_TOKEN": "test_token"}):
        route = respx.post("https://api.telegram.org/bottest_token/setMyCommands").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": True})
        )

        # Act
        result = await setup_telegram_commands()

        # Assert
        assert result is True
        assert route.called
        # Check payload
        request_payload = route.calls.last.request.read().decode("utf-8")
        import json
        payload_data = json.loads(request_payload)
        
        commands = payload_data["commands"]
        command_names = [c["command"] for c in commands]
        
        assert "rain" in command_names
        assert "check" in command_names
        assert "lock" in command_names
        assert "radar" in command_names
        assert "mylocation" in command_names
        assert "unlock" in command_names
        assert "bypass" in command_names
        assert "bypass_logout" in command_names
        assert "metrics" in command_names
        assert "setbudget" in command_names
        assert "tmd_fallback" in command_names
        assert "restore_public_access" in command_names
        assert "job" in command_names
        assert "status" in command_names
        # Should NOT have devmock
        assert "devmock" not in command_names

@respx.mock
@pytest.mark.asyncio
async def test_setup_telegram_commands_development():
    # Arrange: set environment to development
    with patch.dict("os.environ", {"ENVIRONMENT": "development", "TELEGRAM_BOT_TOKEN": "test_token"}):
        route = respx.post("https://api.telegram.org/bottest_token/setMyCommands").mock(
            return_value=httpx.Response(200, json={"ok": True, "result": True})
        )

        # Act
        result = await setup_telegram_commands()

        # Assert
        assert result is True
        assert route.called
        
        request_payload = route.calls.last.request.read().decode("utf-8")
        import json
        payload_data = json.loads(request_payload)
        
        commands = payload_data["commands"]
        command_names = [c["command"] for c in commands]
        
        # Should have rain, check, lock AND devmock and others
        assert "rain" in command_names
        assert "check" in command_names
        assert "lock" in command_names
        assert "radar" in command_names
        assert "mylocation" in command_names
        assert "unlock" in command_names
        assert "devmock" in command_names

@respx.mock
@pytest.mark.asyncio
async def test_setup_telegram_commands_graceful_failure():
    # Arrange: API returns error
    with patch.dict("os.environ", {"ENVIRONMENT": "development", "TELEGRAM_BOT_TOKEN": "test_token"}):
        route = respx.post("https://api.telegram.org/bottest_token/setMyCommands").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        # Act
        result = await setup_telegram_commands()

        # Assert: Should not crash, just return False
        assert result is False
        assert route.called
