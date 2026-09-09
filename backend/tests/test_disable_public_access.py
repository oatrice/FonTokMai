import os
import subprocess
import pytest
from unittest.mock import patch, AsyncMock
from app.routers.webhook_admin import handle_disable_public_access_command, _run_admin_script

def test_disable_public_access_script_idempotent_when_binding_not_found(tmp_path):
    """
    Test that disable_public_access.sh exits 0 and reports success/idempotent status
    even when gcloud outputs 'Policy binding with the specified principal, role, and condition not found!'.
    """
    # Create a mock gcloud executable in tmp_path
    mock_gcloud = tmp_path / "gcloud"
    mock_gcloud.write_text(
        "#!/bin/bash\n"
        "echo 'ERROR: (gcloud.run.services.remove-iam-policy-binding) Policy binding with the specified principal, role, and condition not found!' >&2\n"
        "exit 1\n"
    )
    mock_gcloud.chmod(0o755)

    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts/disable_public_access.sh"))

    # Execute script with PATH prefixed with tmp_path
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["TELEGRAM_BOT_TOKEN"] = ""
    env["DEVELOPER_CHAT_IDS"] = ""

    result = subprocess.run(["bash", script_path], env=env, capture_output=True, text=True)
    
    # It should succeed (exit code 0) and inform that public access is disabled/already disabled
    assert result.returncode == 0, f"Script failed with code {result.returncode}, stderr: {result.stderr}, stdout: {result.stdout}"
    assert "Public access disabled" in result.stdout or "already disabled" in result.stdout or "Private" in result.stdout


@pytest.mark.asyncio
async def test_run_admin_script_success():
    with patch("app.routers.webhook_admin._reply", new_callable=AsyncMock) as mock_reply, \
         patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "OK"
        mock_run.return_value.stderr = ""

        await _run_admin_script(
            "../../scripts/disable_public_access.sh",
            "✅ ยกเลิกสิทธิ์ Public Access (โหมด Private) เรียบร้อยแล้วครับ",
            12345,
            "/disable_public_access",
            "testuser"
        )

        mock_reply.assert_called_once()
        args, _ = mock_reply.call_args
        assert "✅" in args[1]
