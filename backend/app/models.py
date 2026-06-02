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

class DeveloperMock(Base):
    __tablename__ = "developer_mocks"

    chat_id = Column(BigInteger, primary_key=True, index=True)
    state = Column(String, nullable=False) # 'rain', 'clear'
