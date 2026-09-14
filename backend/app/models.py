from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Text, Boolean
from app.database import Base

class UserLocation(Base):
    __tablename__ = "user_locations"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    name = Column(String, default="default", nullable=False)
    platform = Column(String, default="telegram", nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    retention_type = Column(String, nullable=False) # 'ONCE', 'TWO_MONTHS', 'FOREVER'
    expires_at = Column(DateTime, nullable=True)
    last_alerted_at = Column(DateTime, nullable=True)
    last_alert_max_rain = Column(Float, nullable=True, default=0.0)  # mm/hr ของการแจ้งเตือนครั้งล่าสุด
    tracking_mode = Column(String, default="auto", nullable=False) # "auto" | "manual"
    locked_target_id = Column(String, nullable=True) # e.g. "A"
    locked_target_cx = Column(Integer, nullable=True)
    locked_target_cy = Column(Integer, nullable=True)
    is_snoozed = Column(Boolean, default=False, nullable=False)
    snooze_until = Column(DateTime, nullable=True)

    # Presence Verification & Policy (Issue #289, #290, #291)
    # presence_policy: 'always_notify' | 'always_ask' | 'schedule_based' | 'silent_card'
    presence_policy = Column(String, default="always_ask", nullable=False)
    schedule_active_days = Column(String, nullable=True) # e.g. "[1,2,3,4,5]"
    schedule_active_start = Column(String, nullable=True) # e.g. "08:00"
    schedule_active_end = Column(String, nullable=True) # e.g. "18:00"
    presence_answer_ttl_minutes = Column(Integer, default=120, nullable=False) # Countdown TTL in minutes
    default_fallback_policy = Column(String, default="notify", nullable=False) # 'notify' | 'skip'

    @property
    def is_snoozed_bool(self) -> bool:
        if not self.is_snoozed:
            return False
        if self.snooze_until:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            return self.snooze_until > now
        return bool(self.is_snoozed)

    # Allow accessing is_snoozed as boolean for ease of use
    @property
    def is_snoozed_state(self) -> bool:
        return bool(self.is_snoozed)


class PresenceAnswerCache(Base):
    """
    Caches user confirmation answers on whether to receive alerts at a given location.
    Countdown TTL enables asking again only after the cache expires (Issue #289).
    """
    __tablename__ = "presence_answer_cache"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    location_name = Column(String, index=True, nullable=False)
    answer = Column(String, nullable=False) # 'yes' | 'no'
    expires_at = Column(DateTime, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False)


class DeveloperMock(Base):
    __tablename__ = "developer_mocks"

    chat_id = Column(String, primary_key=True, index=True)
    state = Column(String, nullable=False) # 'rain', 'clear'

class UserFeedback(Base):
    __tablename__ = "user_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    feedback_type = Column(String, nullable=False) # e.g. 'false_alarm'
    prediction_context = Column(String, nullable=True) # e.g. "max_rain: 1.5 mm/hr"

class SystemUsageEvent(Base):
    """
    Unified Event Log: Tracks proactive rain alerts, on-demand queries, and mock tests.
    Used for accuracy verification and multi-tier unit economics (Issue #298).
    """
    __tablename__ = "system_usage_events"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
    location_name = Column(String, index=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    alerted_at = Column(DateTime, index=True, nullable=False)
    rain_intensity_mm = Column(Float, default=0.0, nullable=False)
    alert_type = Column(String, default="rain", nullable=False)
    user_feedback_result = Column(String, nullable=True) # 'false_alarm' | 'true_alarm' | None
    auto_verify_result = Column(String, nullable=True)   # 'false_alarm' | 'true_alarm' | None
    auto_verified_at = Column(DateTime, nullable=True)
    
    event_category = Column(String, default="proactive_alert", nullable=False)
    command_name = Column(String, nullable=True)
    is_mock = Column(Boolean, default=False, nullable=False)


class ExternalCostConfig(Base):
    """
    Configures non-GCP monthly infrastructure costs (Proxy pools, external weather APIs).
    Used to compute total Cost Per Alert accurately (Issue #292).
    """
    __tablename__ = "external_cost_config"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String, index=True, nullable=False) # 'tmd_proxy', 'tomorrow_api', etc.
    month = Column(String, index=True, nullable=False)        # 'YYYY-MM'
    amount_thb = Column(Float, default=0.0, nullable=False)


class DisasterAlertHistory(Base):
    __tablename__ = "disaster_alert_history"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True, nullable=False)
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

class RadarStationModel(Base):
    __tablename__ = "radar_stations"

    code = Column(String(32), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    static_image_url = Column(Text, nullable=False)
    loop_page_url = Column(Text, nullable=True)
    loop_gif_url = Column(Text, nullable=True)
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    radius_km = Column(Float, default=240.0, nullable=False)

    lat_max = Column(Float, nullable=False)
    lng_min = Column(Float, nullable=False)
    lat_min = Column(Float, nullable=False)
    lng_max = Column(Float, nullable=False)

    static_crop_x = Column(Integer, default=0, nullable=False)
    static_crop_y = Column(Integer, default=0, nullable=False)
    static_crop_width = Column(Integer, default=800, nullable=False)
    static_crop_height = Column(Integer, default=800, nullable=False)

    loop_crop_x = Column(Integer, default=0, nullable=False)
    loop_crop_y = Column(Integer, default=0, nullable=False)
    loop_crop_width = Column(Integer, default=680, nullable=False)
    loop_crop_height = Column(Integer, default=680, nullable=False)

    projection_type = Column(String(32), default="azimuthal", nullable=False)
    is_active = Column(Integer, default=1, nullable=False) # 1 = True, 0 = False for SQL compatibility
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

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

    chat_id = Column(String, primary_key=True, index=True)
    expires_at = Column(DateTime, nullable=False)

class Donor(Base):
    __tablename__ = "donors"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, index=True, nullable=False)
    hashed_transaction_id = Column(String, unique=True, nullable=False)
    pseudonym = Column(String, nullable=True, default="Anonymous")
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class Payout(Base):
    """Audit trail for Stripe automatic payouts (Issue #210).

    Tracks payout lifecycle: created → paid | failed.
    idempotency_key prevents double-processing of duplicate webhook events.
    Zero-PII: stores only Stripe-generated IDs, no bank account details.
    """
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True, index=True)
    payout_id = Column(String, unique=True, index=True, nullable=False)       # Stripe po_xxx ID
    status = Column(String, nullable=False)                                    # 'pending' | 'paid' | 'failed' | 'canceled'
    amount_cents = Column(BigInteger, nullable=False)                          # สตางค์ — 500000 = 5,000 THB
    currency = Column(String, default="thb", nullable=False)
    arrival_date = Column(DateTime, nullable=True)                             # วันที่โอนเข้าบัญชี
    idempotency_key = Column(String, unique=True, index=True, nullable=False)  # {payout_id}-{event_type}
    failure_code = Column(String, nullable=True)                               # Stripe error code
    failure_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

class RadarFrameCache(Base):
    __tablename__ = "radar_frame_cache"

    frame_hash = Column(String, primary_key=True, index=True)
    timestamp = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False)

class ApiQuota(Base):
    __tablename__ = "api_quotas"

    quota_key = Column(String, primary_key=True, index=True)
    count = Column(Integer, default=0, nullable=False)

