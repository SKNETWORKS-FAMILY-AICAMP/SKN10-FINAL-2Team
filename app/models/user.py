from sqlalchemy import Column, String, Integer, Boolean, Text
from .base import BaseModel

class User(BaseModel):
    __tablename__ = "users"

    name = Column(String(100), nullable=False)
    age = Column(Integer)
    gender = Column(String(10))
    health_conditions = Column(Text)
    allergies = Column(Text)
    is_guest = Column(Boolean, default=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100)) 