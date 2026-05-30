from firebase_functions import https_fn
from firebase_admin import initialize_app
from flask import Response
from a2wsgi import ASGIMiddleware

# โหลด FastAPI app ตัวเดิมของเราจากโฟลเดอร์ app
from app.main import app 

initialize_app()

# แปลง ASGI (FastAPI) เป็น WSGI เพื่อให้ทำงานร่วมกับ Firebase Functions ได้
wsgi_app = ASGIMiddleware(app)

@https_fn.on_request(max_instances=5)
def api(req: https_fn.Request) -> https_fn.Response:
    environ = req.environ.copy()
    
    response_status = []
    response_headers = []
    
    def start_response(status, headers, exc_info=None):
        response_status.append(status)
        response_headers.extend(headers)
        
    result = wsgi_app(environ, start_response)
    
    status_code = int(response_status[0].split(" ")[0]) if response_status else 200
    
    return Response(
        response=result,
        status=status_code,
        headers=response_headers
    )
