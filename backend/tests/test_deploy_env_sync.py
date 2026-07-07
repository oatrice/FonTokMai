import os
import re

def test_deploy_env_sync():
    """
    ตรวจสอบว่าตัวแปรสภาพแวดล้อมที่จำเป็นใน .env.example 
    ถูกระบุไว้ในสคริปต์ deploy_cloudrun.sh สำหรับ Cloud Run ครบถ้วนหรือไม่
    """
    # 1. อ่านตัวแปรทั้งหมดจาก .env.example
    env_example_path = os.path.join(os.path.dirname(__file__), "../.env.example")
    assert os.path.exists(env_example_path)
    
    env_keys = set()
    with open(env_example_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key = line.split("=")[0].strip()
                env_keys.add(key)

    # 2. อ่านตัวแปรใน deploy_cloudrun.sh
    deploy_script_path = os.path.join(os.path.dirname(__file__), "../deploy/deploy_cloudrun.sh")
    assert os.path.exists(deploy_script_path)
    
    with open(deploy_script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    # ดึงค่าใน --set-env-vars block
    match = re.search(r'--set-env-vars\s+"([^"]+)"', script_content, re.DOTALL)
    assert match is not None, "ไม่พบส่วนของ --set-env-vars ใน deploy_cloudrun.sh"
    
    env_vars_block = match.group(1)
    
    # ดึงคีย์ตัวแปรที่ถูก set (ฝั่งซ้ายของเครื่องหมาย =)
    set_keys = set()
    for line in env_vars_block.split(","):
        line = line.strip().replace("\\", "")
        if "=" in line:
            key = line.split("=")[0].strip()
            set_keys.add(key)

    # 3. กำหนดตัวแปรที่ยกเว้น (เพราะมีอยู่แล้วในระดับระบบ/GCP Environment)
    ignored_keys = {
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GCP_PROJECT",
        "GOOGLE_CLOUD_PROJECT",
        "GCP_LOCATION",
        "CLOUD_TASKS_QUEUE",
        "CLOUD_RUN_SERVICE_NAME",
        "BUDGET_AMOUNT_THB" # ใช้ใน local / scheduler-based shutdown แยกต่างหาก
    }

    # คีย์ที่จำเป็นต้องมีในสคริปต์
    required_keys = env_keys - ignored_keys

    # ตรวจสอบว่าคีย์ที่จำเป็นทั้งหมดถูก set ใน deploy_cloudrun.sh หรือยัง
    missing_keys = required_keys - set_keys
    assert not missing_keys, f"❌ ตัวแปรเหล่านี้อยู่ใน .env.example แต่ยังไม่ได้เพิ่มใน deploy_cloudrun.sh: {missing_keys}"
