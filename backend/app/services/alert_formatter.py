from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pydantic import BaseModel
from typing import Optional, Any

BKK_TZ = ZoneInfo('Asia/Bangkok')

class AlertDecision(BaseModel):
    location_name: Optional[str] = None
    type: str  # 'all_clear', 'rain', 'error'
    max_rain: float = 0.0
    result: dict[str, Any]
    severity_escalated: bool = False
    last_max_rain: float = 0.0

class TelegramFormatter:
    @staticmethod
    def format(decision: AlertDecision) -> str:
        loc_name = decision.location_name or "Default"
        loc_name_str = f" '{loc_name.capitalize()}' " if loc_name.lower() != "default" else ""
        
        if decision.type == "all_clear":
            return f"☀️ สภาพอากาศ ณ พิกัด{loc_name_str}เคลียร์แล้ว\n(ไม่มีแนวโน้มฝนตกในขณะนี้)"
            
        if decision.type == "rain":
            result = decision.result
            predictions = result.get("predictions", [])
            eta_minutes = 0
            rain_start_dt = None

            if predictions:
                try:
                    base_time = datetime.fromisoformat(predictions[0].get("time", "").replace("Z", "+00:00"))
                except Exception:
                    base_time = None
                    
                for pred in predictions:
                    if pred.get("rain", 0) >= 0.1:  # RAIN_TRIGGER_THRESHOLD_MM fallback
                        if base_time:
                            try:
                                pred_time = datetime.fromisoformat(pred.get("time", "").replace("Z", "+00:00"))
                                current_utc = datetime.now(timezone.utc)
                                eta_minutes = int((pred_time - current_utc).total_seconds() / 60)
                                if eta_minutes < 0:
                                    eta_minutes = 0
                                rain_start_dt = pred_time
                            except Exception:
                                eta_minutes = 0
                        else:
                            eta_minutes = 0
                        break

            intensity_str = result.get("intensity", "ไม่ทราบ")
            duration_min = result.get("duration_minutes", 0)
            wind_speed_kmh = result.get("wind_speed_kmh", 0.0)
            endpoint_source = result.get("endpoint", "unknown")
            
            source_map = {
                "tomorrow": "Tomorrow.io",
                "rainbow-local": "Rainbow (Local)",
                "rainbow-global": "Rainbow (Global)"
            }
            source_name = source_map.get(endpoint_source, endpoint_source)
            
            if not rain_start_dt:
                rain_start_dt = datetime.now(timezone.utc) + timedelta(minutes=eta_minutes)
                
            rain_end_dt = rain_start_dt + timedelta(minutes=duration_min)
            start_time_str = rain_start_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
            end_time_str = rain_end_dt.astimezone(BKK_TZ).strftime("%H:%M น.")
            distance_km = (eta_minutes / 60.0) * wind_speed_kmh
            
            text = ""
            if decision.severity_escalated:
                text += f"⚠️ *อัปเดต: ฝนทวีความรุนแรงขึ้น!*\n({decision.last_max_rain:.1f} mm/hr → {decision.max_rain:.1f} mm/hr)\n\n"

            rain_summary = result.get("rain_summary")
            if rain_summary:
                text += f"🌧️ ข้อมูลพยากรณ์ฝนสำหรับพิกัด{loc_name_str}ของคุณ\n"
                text += f"{rain_summary}\n\n"
                wind_dir_text = result.get("wind_dir_text", "ไม่ทราบ")
                if wind_speed_kmh > 0: text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h (พัดไปทางทิศ {wind_dir_text})\n"
                if eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"
            else:
                if eta_minutes == 0: text += f"🌧️ ฝนกำลังตกอยู่ที่พิกัด{loc_name_str}ของคุณ ณ ขณะนี้\n"
                else:
                    text += f"🌧️ ฝนกำลังเคลื่อนมาทางพิกัด{loc_name_str}ของคุณ\n"
                    text += f"⏰ จะเริ่มตกเวลา: {start_time_str} (ในอีก {eta_minutes} นาที)\n"
                
                duration_text = f"ตกต่อเนื่อง {duration_min} นาที"
                if duration_min >= 60:
                    hrs = duration_min // 60
                    mins = duration_min % 60
                    duration_text = f"ตกต่อเนื่อง {hrs} ชม. {mins} นาที" if mins > 0 else f"ตกต่อเนื่อง {hrs} ชม."
                    
                if duration_min > 0: text += f"🛑 คาดว่าจะหยุดเวลา: {end_time_str} ({duration_text})\n\n"
                else: text += "\n"
                    
                if intensity_str == "ไม่มีฝน" and eta_minutes > 0:
                    if decision.max_rain > 10.0: max_int = "ฝนตกหนักมาก"
                    elif decision.max_rain > 2.5: max_int = "ฝนตกหนัก"
                    elif decision.max_rain > 0.5: max_int = "ฝนตกปานกลาง"
                    else: max_int = "ฝนตกเล็กน้อย"
                    text += f"💧 ความรุนแรง (สูงสุด): {max_int} ({decision.max_rain:.1f} mm/hr)\n"
                else:
                    text += f"💧 ความรุนแรง: {intensity_str} ({decision.max_rain:.1f} mm/hr)\n"
                
                wind_dir_text = result.get("wind_dir_text", "ไม่ทราบ")
                if wind_speed_kmh > 0: text += f"🌬️ สภาพลม: {wind_speed_kmh:.1f} km/h (พัดไปทางทิศ {wind_dir_text})\n"
                if eta_minutes > 0 and wind_speed_kmh > 0: text += f"📏 ระยะห่างจากกลุ่มฝน: ประมาณ {distance_km:.1f} กม.\n"

            growth_rate = result.get("growth_rate_pct")
            if growth_rate is not None and "ไม่พบฝน" not in (rain_summary or ""):
                if growth_rate > 5.0:
                    text += f"📈 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): กำลังก่อตัวแรงขึ้น (+{growth_rate:.1f}%/15min)\n"
                elif growth_rate < -5.0:
                    text += f"📉 พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): อ่อนกำลังลง ({growth_rate:.1f}%/15min)\n"
                else:
                    text += f"➖ พัฒนาการเมฆฝน (15 นาทีที่ผ่านมา): คงที่\n"
                    
            text += f"📡 แหล่งข้อมูล: {source_name}\n"
            update_time_str = datetime.now(BKK_TZ).strftime("%d/%m/%Y %H:%M:%S")
            text += f"🔄 ข้อมูลอัปเดตล่าสุด: {update_time_str}\n"

            return text
            
        return ""
