from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Feeding(Base):
    __tablename__ = "feedings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class SleepSession(Base):
    __tablename__ = "sleep_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)


class Diaper(Base):
    __tablename__ = "diapers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    diaper_type = Column(String, nullable=False)  # wet, dirty, both
    created_at = Column(DateTime, default=datetime.utcnow)


class Weight(Base):
    __tablename__ = "weights"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    weight_g = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    # feeding, sleep, diaper, weight
    event_type = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
