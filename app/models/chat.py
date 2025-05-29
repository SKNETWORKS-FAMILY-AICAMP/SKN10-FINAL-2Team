from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel

class LLMRequest(BaseModel):
    __tablename__ = "llm_requests"

    user_id = Column(Integer, ForeignKey("users.id"))
    input_prompt = Column(Text)
    llm_response = Column(Text)
    model = Column(String(50))
    status = Column(String(20))

class RecommendationLog(BaseModel):
    __tablename__ = "recommendation_logs"

    user_id = Column(Integer, ForeignKey("users.id"))
    recommended_supplement_id = Column(Integer, ForeignKey("supplements.id"))
    reason = Column(Text)

class GuestSession(BaseModel):
    __tablename__ = "guest_sessions"

    session_id = Column(String(100), unique=True, index=True)
    browser_fingerprint = Column(String(100))
    temporary_health_conditions = Column(Text)
    temporary_allergies = Column(Text)

class GuestRecommendationLog(BaseModel):
    __tablename__ = "guest_recommendation_logs"

    session_id = Column(String(100), ForeignKey("guest_sessions.session_id"))
    recommended_supplement_id = Column(Integer, ForeignKey("supplements.id"))
    reason = Column(Text) 