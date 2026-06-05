from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime
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
