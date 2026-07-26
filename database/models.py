from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True)
    gmail_message_id = Column(String, unique=True, nullable=False)
    sender = Column(String)
    sender_domain = Column(String)
    subject = Column(String)
    decision = Column(String)
    confidence = Column(Float)
    execution_time_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    traces = relationship("ReasoningTrace", back_populates="email", cascade="all, delete-orphan")


class ReasoningTrace(Base):
    __tablename__ = "reasoning_traces"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("email_logs.id"), nullable=False)
    step_number = Column(Integer)
    thought = Column(Text)
    action = Column(String)
    action_input = Column(Text)
    observation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    email = relationship("EmailLog", back_populates="traces")

def get_session(database_url: str):
    """Creates tables if they don't exist yet, and returns a session factory."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)