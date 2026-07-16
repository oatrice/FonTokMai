import os
import json
import subprocess
from app.services.command_router import router as cmd_router
from .webhook_utils import (
    _reply, log_audit_event, check_admin_access, get_repo_context, logger
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


@cmd_router.bind("/bypass ")
async def handle_bypass_login_command(chat_id: int, command: str, username: str = ""):
    password = command.removeprefix("/bypass ").strip()
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
    import subprocess
    import os
    
    if str(chat_id) not in telegram.DEVELOPER_CHAT_IDS:
        log_audit_event("admin_command_executed", chat_id, username, {"command": command})

    try:
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_relative_path)
        result = subprocess.run(["bash", script_path], capture_output=True, text=True, cwd=os.path.dirname(script_path))
        if result.returncode == 0:
            msg = success_msg
        else:
            msg = f"❌ เกิดข้อผิดพลาดในการรันสคริปต์ (Exit code: {result.returncode})\nError: {result.stderr or result.stdout}"
    except Exception as e:
        msg = f"❌ เกิดข้อผิดพลาดในระบบ: {e}"

    await _reply(chat_id, msg, message_id_to_edit)


@cmd_router.bind("/restore_public_access", requires_admin=True, task_route="worker/handle-restore-public-access", loading_text="⏳ กำลังกู้คืนสิทธิ์ Public Access ให้กับ API...")
async def handle_restore_public_access_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    await _run_admin_script(
        "../../scripts/restore_public_access.sh",
        "✅ กู้คืนสิทธิ์ Public Access ให้กับ fontokmai-api สำเร็จแล้วครับ",
        chat_id, command, username, message_id_to_edit
    )


@cmd_router.bind("/disable_public_access", requires_admin=True, task_route="worker/handle-disable-public-access", loading_text="⏳ กำลังยกเลิกสิทธิ์ Public Access (โหมด Private)...")
async def handle_disable_public_access_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    await _run_admin_script(
        "../../scripts/disable_public_access.sh",
        "✅ ยกเลิกสิทธิ์ Public Access (โหมด Private) เรียบร้อยแล้วครับ",
        chat_id, command, username, message_id_to_edit
    )


@cmd_router.bind("/job", requires_admin=True, audit_log=True, task_route="worker/handle-job", loading_text="⏳ กำลังจัดการสถานะ Scheduler Job...")
async def handle_job_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
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

    import os
    project_id = os.getenv("GCP_PROJECT_ID", "fonmayang")
    region = os.getenv("GCP_LOCATION", "asia-southeast1")

    try:
        cmd_args = ["gcloud", "scheduler", "jobs", action, job_name, f"--project={project_id}", f"--location={region}", "--quiet"]
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        if result.returncode == 0:
            status_emoji = "⏸️" if action == "pause" else "▶️"
            msg = f"{status_emoji} จัดการสถานะ Job {job_name} เป็น {action.upper()} สำเร็จแล้วครับ"
        else:
            msg = f"❌ เกิดข้อผิดพลาดจาก gcloud API (Exit code: {result.returncode})\nError: {result.stderr or result.stdout}"
    except Exception as e:
        msg = f"❌ เกิดข้อผิดพลาดในการรันคำสั่ง: {e}"

    await _reply(chat_id, msg, message_id_to_edit)


@cmd_router.bind("/status", requires_admin=True, audit_log=True, task_route="worker/handle-status", loading_text="⏳ กำลังดึงข้อมูลสถานะระบบและ GCP...")
async def handle_status_command(chat_id: int, command: str, username: str = "", message_id_to_edit: int = None):
    project_id = os.getenv("GCP_PROJECT_ID", "fonmayang")
    region = os.getenv("GCP_LOCATION", "asia-southeast1")

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

    # 3. Check Cloud Scheduler Jobs
    jobs_str = ""
    try:
        cmd_args = ["gcloud", "scheduler", "jobs", "list", f"--project={project_id}", f"--location={region}", "--format=json"]
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        if result.returncode == 0:
            jobs_data = json.loads(result.stdout)
            job_states = []
            for job in jobs_data:
                name = job.get("name", "").split("/")[-1]
                state = job.get("state", "UNKNOWN")
                state_emoji = "🟢 ACTIVE" if state == "ENABLED" else "⏸️ PAUSED" if state == "PAUSED" else f"❓ {state}"
                job_states.append(f"• <code>{name}</code>: {state_emoji}")
            jobs_str = "\n".join(job_states)
        else:
            jobs_str = f"❌ ไม่สามารถดึงข้อมูล Jobs ได้: {result.stderr or result.stdout}"
    except Exception as e:
        jobs_str = f"❌ Exception: {e}"

    msg = (
        "📊 <b>สถานะระบบหลังบ้าน (GCP Status Audit)</b>\n\n"
        f"🔹 <b>สิทธิ์เข้าถึง Cloud Run API:</b>\n{run_access_str}\n\n"
        f"🔹 <b>งบประมาณรายเดือน GCP (GCP Monthly Budget):</b>\n{budget_str}\n\n"
        f"🔹 <b>สถานะของงานระบบ (Cloud Scheduler Jobs):</b>\n{jobs_str or 'ไม่มีงาน'}"
    )

    await _reply(chat_id, msg, message_id_to_edit)
