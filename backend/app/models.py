from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Text
from app.database import Base

class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    name = Column(String, default="default", nullable=False)
    platform = Column(String, default="telegram", nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    retention_type = Column(String, nullable=False) # 'ONCE', 'TWO_MONTHS', 'FOREVER'
    expires_at = Column(DateTime, nullable=True)
    last_alerted_at = Column(DateTime, nullable=True)
    last_alert_max_rain = Column(Float, nullable=True, default=0.0)  # mm/hr ของการแจ้งเตือนครั้งล่าสุด

class DeveloperMock(Base):
    __tablename__ = "developer_mocks"

    chat_id = Column(BigInteger, primary_key=True, index=True)
    state = Column(String, nullable=False) # 'rain', 'clear'

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    feedback_type = Column(String, nullable=False) # e.g. 'false_alarm'
    prediction_context = Column(String, nullable=True) # e.g. "max_rain: 1.5 mm/hr"

class DisasterAlertHistory(Base):
    __tablename__ = "disaster_alert_history"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    event_id = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False) # e.g. 'earthquake', 'cyclone', 'fire'
    alerted_at = Column(DateTime, nullable=False)

class ApiReliability(Base):
    __tablename__ = "api_reliability"

    endpoint = Column(String, primary_key=True, index=True) # 'xweather', 'tomorrow', 'rainbow-local', 'rainbow-global', 'open-meteo'
    total_queries = Column(Integer, default=0, nullable=False)
    false_alarms = Column(Integer, default=0, nullable=False)
    
    # accuracy_score = 1.0 - (false_alarms / total_queries) if total_queries > 0 else initial_score
    # We store the raw score directly for easier querying/sorting
    accuracy_score = Column(Float, default=1.0, nullable=False)

class RadarLatestCache(Base):
    __tablename__ = "radar_latest_cache"

    station_code = Column(String, primary_key=True, index=True)
    frames_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    last_gif_fallback_time = Column(Float, default=0.0, nullable=False)
    source = Column(String, default="api")

class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String, primary_key=True, index=True)
    value_json = Column(Text, nullable=False)

class CronRunLog(Base):
    __tablename__ = "cron_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    routine_name = Column(String, index=True, nullable=False)  # e.g. 'check_rain', 'fetch_tmd_radar'
    run_at = Column(DateTime, nullable=False)                   # UTC timestamp
    duration_s = Column(Float, nullable=False)                  # seconds
    alerts_sent = Column(Integer, default=0, nullable=False)
    locations_checked = Column(Integer, default=0, nullable=False)
    errors = Column(Integer, default=0, nullable=False)
    extra_data = Column(Text, nullable=True)                    # JSON string for extra fields

class AdminBypass(Base):
    __tablename__ = "admin_bypass"

    chat_id = Column(BigInteger, primary_key=True, index=True)
    expires_at = Column(DateTime, nullable=False)
