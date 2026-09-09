import os
import json
import subprocess
import httpx
from app.services.command_router import router as cmd_router
from .webhook_utils import (
    _reply, log_audit_event, check_admin_access, get_repo_context, logger,
    get_gcp_project_id, get_gcp_region, get_gcp_access_token, load_scheduler_jobs_config
)
from app.services import telegram
from datetime import datetime, timezone

@cmd_router.bind("/metrics", requires_admin=True, audit_log=True, task_route="worker/handle-metrics", loading_text="⏳ กำลังดึงข้อมูลสถิติ...")
async def handle_metrics_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    parts = command.strip().split()
    days = 7
    if len(parts) > 1:
        try:
            days = int(parts[1])
        except ValueError:
            pass

    async with get_repo_context() as repo:
        try:
            logs = await repo.get_cron_metrics(days=days)
        except Exception as e:
            logger.error(f"Failed to fetch metrics: {e}")
            await telegram.send_telegram_message(chat_id, "❌ ไม่สามารถดึงข้อมูล metrics ได้ในขณะนี้")
            return

    if not logs:
        await telegram.send_telegram_message(chat_id, f"ℹ️ ไม่มีข้อมูล metrics ในช่วง {days} วันที่ผ่านมา")
        return

    import io
    import csv
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["routine_name", "run_at", "duration_s", "alerts_sent", "locations_checked", "errors", "extra_data"])
    
    for log in logs:
        run_at_str = log.get("run_at").isoformat() if log.get("run_at") else ""
        extra_str = json.dumps(log.get("extra_data"), ensure_ascii=False) if log.get("extra_data") else ""
        writer.writerow([
            log.get("routine_name"),
            run_at_str,
            log.get("duration_s"),
            log.get("alerts_sent"),
            log.get("locations_checked"),
            log.get("errors"),
            extra_str
        ])
        
    csv_data = output.getvalue().encode("utf-8")
    
    await telegram.send_telegram_document(chat_id, csv_data, f"metrics_{days}_days.csv")


@cmd_router.bind("/setbudget", requires_admin=True, audit_log=True, task_route="worker/handle-setbudget", loading_text="⏳ กำลังตั้งค่างบประมาณ...")
async def handle_setbudget_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    parts = command.strip().split()
    if len(parts) < 2:
        await telegram.send_telegram_message(
            chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
        )
        return

    try:
        amount = float(parts[1])
    except ValueError:
        await telegram.send_telegram_message(
            chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาพิมพ์: /setbudget <จำนวนงบประมาณ (ตัวเลข)>"
        )
        return

    from app.services.billing_service import BillingService
    billing_svc = BillingService()
    success = await billing_svc.update_budget(amount)
    
    if success:
        await telegram.send_telegram_message(
            chat_id, f"✅ ปรับงบประมาณ GCP สำเร็จเป็น {amount} THB เรียบร้อยแล้ว"
        )
    else:
        await telegram.send_telegram_message(
            chat_id, "❌ ไม่สามารถปรับงบประมาณ GCP ได้ กรุณาตรวจสอบ logs ของระบบ"
        )


@cmd_router.bind("/bypass_logout")
async def handle_bypass_logout_command(chat_id: int, username: str = ""):
    async with get_repo_context() as repo:
        await repo.delete_admin_bypass(chat_id)
    log_audit_event("bypass_logout", chat_id, username, {})
    await telegram.send_telegram_message(chat_id, "ออกจากระบบ Emergency Admin Bypass เรียบร้อยแล้ว")


@cmd_router.bind("/bypass")
async def handle_bypass_login_command(chat_id: int, command: str, username: str = ""):
    password = command.removeprefix("/bypass").strip()
    if not password:
        await telegram.send_telegram_message(chat_id, "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณากรอกรหัสผ่านด้วยครับ: /bypass <รหัสผ่าน>")
        return
    import os
    actual_pass = os.getenv("ADMIN_BYPASS_PASSWORD")
    if actual_pass and password == actual_pass:
        async with get_repo_context() as repo:
            await repo.save_admin_bypass(chat_id)
        log_audit_event("bypass_login_success", chat_id, username, {})
        await telegram.send_telegram_message(chat_id, "✅ ยืนยันรหัสผ่านถูกต้อง! เปิดใช้งาน Emergency Admin Bypass (1 ชั่วโมง)")
    else:
        log_audit_event("bypass_login_failed", chat_id, username, {})
        await telegram.send_telegram_message(chat_id, "❌ รหัสผ่านไม่ถูกต้อง")


async def _run_admin_script(script_relative_path: str, success_msg: str, chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if str(chat_id) not in telegram.DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_relative_path)
        result = subprocess.run(["bash", script_path], capture_output=True, text=True, cwd=os.path.dirname(script_path))
        if result.returncode == 0:
            msg = success_msg
        else:
            raw_err = (result.stderr or result.stdout or "").strip()
            clean_err = raw_err[:200] + ("..." if len(raw_err) > 200 else "")
            msg = f"❌ เกิดข้อผิดพลาดในการรันสคริปต์ (Exit code: {result.returncode})\nError: {clean_err}\n(กรุณาดูรายละเอียดใน server logs)"
    except Exception as e:
        logger.error(f"_run_admin_script error: {e}")
        msg = f"❌ เกิดข้อผิดพลาดในระบบ: {e}"

    await _reply(chat_id, msg, message_id_to_edit)


def _resume_cloud_scheduler_jobs() -> dict[str, str]:
    """
    สั่ง Resume Google Cloud Scheduler jobs ทั้งหมดที่ระบบกำหนดไว้ให้เป็น ACTIVE
    ผ่าน Cloud Scheduler REST API (ข้ามตัวที่มี state: PAUSED ใน config)
    Returns dict mapping job_name -> status ("RESUMED" or error message)
    """
    results: dict[str, str] = {}
    jobs_config = load_scheduler_jobs_config()
    jobs_to_resume = [
        j.get("job_name") for j in jobs_config
        if j.get("job_name") and j.get("state") != "PAUSED"
    ]

    project_id = get_gcp_project_id()
    region = get_gcp_region()

    try:
        token = get_gcp_access_token()
    except Exception as e:
        logger.error(f"[restore_public_access] Failed to get GCP access token: {e}")
        return {name: f"ERROR: {e}" for name in jobs_to_resume}

    with httpx.Client(timeout=10) as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        for job_name in jobs_to_resume:
            url = f"https://cloudscheduler.googleapis.com/v1/projects/{project_id}/locations/{region}/jobs/{job_name}:resume"
            try:
                resp = client.post(url, headers=headers)
                if resp.status_code == 200:
                    logger.info(f"[restore_public_access] ▶️ Resumed Cloud Scheduler job: {job_name}")
                    results[job_name] = "RESUMED"
                else:
                    logger.warning(f"[restore_public_access] ⚠️ Failed to resume {job_name} (HTTP {resp.status_code}): {resp.text}")
                    results[job_name] = f"HTTP_{resp.status_code}"
            except Exception as e:
                logger.error(f"[restore_public_access] ❌ Exception resuming {job_name}: {e}")
                results[job_name] = f"ERROR: {e}"

    return results


@cmd_router.bind("/restore_public_access", requires_admin=True, task_route="worker/handle-restore-public-access", loading_text="⏳ กำลังกู้คืนสิทธิ์ Public Access ให้กับ API...")
async def handle_restore_public_access_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    try:
        async with get_repo_context() as repo:
            settings = await repo.get_system_settings()
            if not settings:
                settings = {}
            if settings.get("emergency_shutdown"):
                settings["emergency_shutdown"] = False
                await repo.set_system_settings(settings)
                logger.info("[restore_public_access] Reset emergency_shutdown = False in database.")
    except Exception as e:
        logger.error(f"[restore_public_access] Failed to reset emergency_shutdown flag: {e}")

    # Resume Cloud Scheduler jobs
    try:
        scheduler_resume_results = _resume_cloud_scheduler_jobs()
        logger.info(f"[restore_public_access] Cloud Scheduler resume results: {scheduler_resume_results}")
    except Exception as e:
        logger.error(f"[restore_public_access] Failed to resume Cloud Scheduler jobs: {e}")

    await _run_admin_script(
        "../../scripts/restore_public_access.sh",
        "✅ กู้คืนสิทธิ์ Public Access ให้กับ fontokmai-api และสั่ง Resume Cloud Scheduler สำเร็จแล้วครับ",
        chat_id, command, username, message_id_to_edit
    )


@cmd_router.bind("/disable_public_access", requires_admin=True, task_route="worker/handle-disable-public-access", loading_text="⏳ กำลังยกเลิกสิทธิ์ Public Access (โหมด Private)...")
async def handle_disable_public_access_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    await _run_admin_script(
        "../../scripts/disable_public_access.sh",
        "✅ ยกเลิกสิทธิ์ Public Access (โหมด Private) เรียบร้อยแล้วครับ",
        chat_id, command, username, message_id_to_edit
    )


@cmd_router.bind("/job", requires_admin=True, audit_log=True, task_route="worker/handle-job", loading_text="⏳ กำลังจัดการสถานะ Scheduler Job...")
async def handle_job_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    parts = command.strip().split()
    if len(parts) < 3:
        msg = "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาใช้:\n`/job <pause|resume> <check-rain|fetch-radar|disasters-freq|disasters-infreq>`"
        await _reply(chat_id, msg, message_id_to_edit)
        return

    action = parts[1].lower()
    job_key = parts[2].lower()

    if action not in ("pause", "resume"):
        msg = "❌ Action ไม่ถูกต้อง ต้องเป็น `pause` หรือ `resume` เท่านั้น"
        await _reply(chat_id, msg, message_id_to_edit)
        return

    job_mapping = {
        "check-rain": "fonmayang-check-rain",
        "fetch-radar": "fonmayang-fetch-radar",
        "disasters-freq": "fonmayang-disasters-freq",
        "disasters-infreq": "fonmayang-disasters-infreq",
    }

    job_name = job_mapping.get(job_key)
    if not job_name:
        msg = f"❌ ไม่พบ Job ชื่อ '{job_key}' ในระบบ"
        await _reply(chat_id, msg, message_id_to_edit)
        return

    project_id = get_gcp_project_id()
    region = get_gcp_region()

    try:
        token = get_gcp_access_token()
        url = f"https://cloudscheduler.googleapis.com/v1/projects/{project_id}/locations/{region}/jobs/{job_name}:{action}"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            if resp.status_code == 200:
                status_emoji = "⏸️" if action == "pause" else "▶️"
                msg = f"{status_emoji} จัดการสถานะ Job {job_name} เป็น {action.upper()} สำเร็จแล้วครับ"
            else:
                msg = f"❌ เกิดข้อผิดพลาดจาก Cloud Scheduler API (HTTP {resp.status_code})\nError: {resp.text[:200]}"
    except Exception as e:
        logger.error(f"handle_job_command error: {e}")
        msg = f"❌ เกิดข้อผิดพลาดในการรันคำสั่ง: {e}"

    await _reply(chat_id, msg, message_id_to_edit)


@cmd_router.bind("/status", requires_admin=True, audit_log=True, task_route="worker/handle-status", loading_text="⏳ กำลังดึงข้อมูลสถานะระบบและ GCP...")
async def handle_status_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    if not await check_admin_access(chat_id):
        return

    project_id = get_gcp_project_id()
    region = get_gcp_region()

    # 1. Check Cloud Run Public Access
    run_access_str = "❓ Unknown"
    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../scripts/check_public_access.sh")
        result = subprocess.run(["bash", script_path], capture_output=True, text=True, cwd=os.path.dirname(script_path))
        if "PUBLIC" in result.stdout:
            run_access_str = "🌐 PUBLIC (เปิดสาธารณะ)"
        elif "PRIVATE" in result.stdout:
            run_access_str = "🔒 PRIVATE (ปิดส่วนตัว)"
        else:
            run_access_str = "❓ Error reading policy"
    except Exception as e:
        run_access_str = f"❓ Exception: {e}"

    # 2. Check GCP Monthly Budget
    budget_str = "❓ Unknown"
    try:
        from app.services.billing_service import BillingService
        billing_svc = BillingService()
        budget = await billing_svc.get_budget()
        if budget is not None:
            budget_str = f"💰 {budget:,.2f} THB"
        else:
            budget_str = "❓ Not found or Billing Account not set"
    except Exception as e:
        budget_str = f"❓ Exception: {e}"

    # 3. Check Cloud Scheduler Jobs via REST API
    jobs_str = ""
    try:
        token = get_gcp_access_token()
        url = f"https://cloudscheduler.googleapis.com/v1/projects/{project_id}/locations/{region}/jobs"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                jobs_data = resp.json().get("jobs", [])
                job_states = []
                for job in jobs_data:
                    name = job.get("name", "").split("/")[-1]
                    state = job.get("state", "UNKNOWN")
                    state_emoji = "🟢 ACTIVE" if state == "ENABLED" else "⏸️ PAUSED" if state == "PAUSED" else f"❓ {state}"
                    job_states.append(f"• <code>{name}</code>: {state_emoji}")
                jobs_str = "\n".join(job_states)
            else:
                jobs_str = f"⚠️ ไม่สามารถดึงข้อมูล Jobs ได้ (HTTP {resp.status_code})"
    except Exception as e:
        logger.error(f"Failed to fetch Cloud Scheduler jobs via API: {e}")
        jobs_str = f"❌ Exception: {e}"

    msg = (
        "📊 <b>สถานะระบบหลังบ้าน (GCP Status Audit)</b>\n\n"
        f"🔹 <b>สิทธิ์เข้าถึง Cloud Run API:</b>\n{run_access_str}\n\n"
        f"🔹 <b>งบประมาณรายเดือน GCP (GCP Monthly Budget):</b>\n{budget_str}\n\n"
        f"🔹 <b>สถานะของงานระบบ (Cloud Scheduler Jobs):</b>\n{jobs_str or 'ไม่มีงาน'}"
    )

    # 4. Check emergency_overdrive & circuit_breaker_active from DB
    try:
        from app.database import AsyncSessionLocal
        from app.models import SystemConfig
        from sqlalchemy import select
        import json as _json

        async with AsyncSessionLocal() as db_sess:
            od_res = await db_sess.execute(select(SystemConfig.value_json).where(SystemConfig.key == "emergency_overdrive"))
            od_val = od_res.scalar_one_or_none()
            cb_res = await db_sess.execute(select(SystemConfig.value_json).where(SystemConfig.key == "circuit_breaker_active"))
            cb_val = cb_res.scalar_one_or_none()

        is_overdrive = False
        if od_val is not None:
            parsed = _json.loads(od_val)
            is_overdrive = parsed == "true" or parsed is True

        is_cb = False
        if cb_val is not None:
            parsed = _json.loads(cb_val)
            is_cb = parsed == "true" or parsed is True

        od_str = "⚡ <b>ACTIVE</b> — โหมดต่ออายุระบบฉุกเฉิน" if is_overdrive else "✅ ปกติ (ปิดอยู่)"
        cb_str = "🔴 <b>TRIPPED</b> — ใช้ข้อมูลพยากรณ์สำรอง" if is_cb else "✅ ปกติ (ไม่ได้ trip)"

        msg += (
            f"\n\n🔹 <b>Emergency Overdrive Mode:</b>\n{od_str}\n"
            f"🔹 <b>Circuit Breaker:</b>\n{cb_str}"
        )
    except Exception as e:
        msg += f"\n\n🔹 <b>Overdrive/CB:</b> ❓ Exception: {e}"

    await _reply(chat_id, msg, message_id_to_edit)


@cmd_router.bind("/overdrive", requires_admin=True, audit_log=True, task_route="worker/handle-overdrive", loading_text="⏳ กำลังเปลี่ยนสถานะ Overdrive Mode...")
async def handle_overdrive_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    """Toggle emergency_overdrive flag in NeonDB.
    
    Usage: /overdrive on | /overdrive off | /overdrive status
    """
    if not await check_admin_access(chat_id):
        return

    parts = command.strip().split()
    if len(parts) < 2 or parts[1].lower() not in ("on", "off", "status"):
        await _reply(
            chat_id,
            "❌ รูปแบบการใช้งานไม่ถูกต้อง กรุณาใช้:\n"
            "• `/overdrive on` — เปิด Extended Lifespan Mode\n"
            "• `/overdrive off` — ปิด Extended Lifespan Mode\n"
            "• `/overdrive status` — ตรวจสอบสถานะปัจจุบัน",
            message_id_to_edit,
        )
        return

    action = parts[1].lower()

    from app.database import AsyncSessionLocal
    from app.models import SystemConfig
    from sqlalchemy import select
    import json as _json

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(SystemConfig).where(SystemConfig.key == "emergency_overdrive")
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if action == "status":
                    current_val = False
                    if record:
                        parsed = _json.loads(record.value_json)
                        current_val = parsed == "true" or parsed is True
                    status_str = "⚡ ACTIVE — โหมดต่ออายุระบบฉุกเฉิน" if current_val else "✅ ปิดอยู่ (ปกติ)"
                    await _reply(chat_id, f"📊 <b>Emergency Overdrive Mode:</b>\n{status_str}", message_id_to_edit)
                    return

                new_value = "true" if action == "on" else "false"
                new_val_json = _json.dumps(new_value)
                if record:
                    record.value_json = new_val_json
                else:
                    session.add(SystemConfig(key="emergency_overdrive", value_json=new_val_json))

        log_audit_event("overdrive_toggled", chat_id, username, {"action": action})

        if action == "on":
            msg = (
                "⚡ <b>Extended Lifespan Mode เปิดแล้ว</b>\n\n"
                "• Runway จะแสดงเป็น ∞ (ไม่มีวันสิ้นสุด)\n"
                "• Circuit Breaker จะ bypass อัตโนมัติ\n"
                "• API ทุกตัวจะทำงานต่อเนื่องโดยไม่สนใจ Jar HP\n\n"
                "⚠️ ใช้ในกรณีฉุกเฉินเท่านั้น ปิดด้วย /overdrive off"
            )
        else:
            msg = (
                "✅ <b>Extended Lifespan Mode ปิดแล้ว</b>\n\n"
                "ระบบกลับสู่โหมดปกติ — Runway และ Circuit Breaker จะทำงานตามงบประมาณจริง"
            )

        await _reply(chat_id, msg, message_id_to_edit)

    except Exception as e:
        logger.error(f"handle_overdrive_command error: {e}")
        await _reply(chat_id, f"❌ เกิดข้อผิดพลาดในการอัปเดต Overdrive Mode: {e}", message_id_to_edit)

