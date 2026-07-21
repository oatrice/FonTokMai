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
        assert "radar" in command_names
        assert "mylocation" in command_names
        assert "tracking" in command_names
        assert "nowcast" in command_names

        
        # Admin / Dev commands should NOT be in the production list
        assert "lock" not in command_names
        assert "unlock" not in command_names
        assert "bypass" not in command_names
        assert "bypass_logout" not in command_names
        assert "metrics" not in command_names
        assert "setbudget" not in command_names
        assert "tmd_fallback" not in command_names
        assert "restore_public_access" not in command_names
        assert "disable_public_access" not in command_names
        assert "job" not in command_names
        assert "status" not in command_names
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
        
        assert "rain" in command_names
        assert "check" in command_names
        assert "radar" in command_names
        assert "tracking" in command_names
        assert "nowcast" in command_names
        assert "lock" in command_names
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
