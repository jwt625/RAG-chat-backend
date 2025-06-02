from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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