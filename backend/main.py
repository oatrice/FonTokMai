from firebase_functions import https_fn
from firebase_admin import initialize_app

# โหลด FastAPI app ตัวเดิมของเราจากโฟลเดอร์ app
from app.main import app 

initialize_app()

# สร้าง Webhook Endpoint สำหรับ Firebase Cloud Functions โดยห่อ FastAPI ไว้
@https_fn.on_request(max_instances=5)
def api(req: https_fn.Request) -> https_fn.Response:
    return https_fn.asgi_app(app)(req)
