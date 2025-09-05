"""AI Response ORM Model"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.orm.base import Base

class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    ai_request_id = Column(Integer, ForeignKey("ai_requests.id"), nullable=False, index=True)
    text_response = Column(Text, nullable=False)
    rating = Column(Boolean, nullable=True)  # true=хороший, false=плохой, null=не оценено
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Опционально: связь для удобства доступа к запросу
    ai_request = relationship("AIRequest", back_populates="responses")