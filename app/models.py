from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import ipaddress

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chats = relationship("Chat", back_populates="user")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    role = Column(String(20))  # 'user' or 'assistant'
    content = Column(Text)
    context_used = Column(JSON, nullable=True)  # Store RAG context
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")


class ApiRequestLog(Base):
    """Log table for API requests - memory-optimized for critical events only"""
    __tablename__ = "api_request_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    path = Column(String(200), nullable=False)  # Truncated path
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=True)  # Response time in milliseconds
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Null for unauthenticated
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # Truncated user agent
    event_type = Column(String(20), nullable=False)  # 'auth_failure', 'server_error', 'rate_limit', etc.
    details = Column(String(500), nullable=True)  # Additional context, truncated

    # Relationships
    user = relationship("User", backref="api_logs")

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_timestamp', 'timestamp'),
        Index('idx_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_status_timestamp', 'status_code', 'timestamp'),
    )


class DailyMetrics(Base):
    """Aggregated daily metrics to save space"""
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)  # Date for the metrics
    metrics = Column(JSON, nullable=False)  # Compressed JSON with endpoint stats
    created_at = Column(DateTime, default=datetime.utcnow)

    # Index for efficient date queries
    __table_args__ = (
        Index('idx_date', 'date'),
    )