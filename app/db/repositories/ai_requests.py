"""
AI Requests Repository
Specialized repository for AI request operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from .base import BaseRepository
from ..models import AIRequest, RequestStatus, User
from ...utils.logger import structured_logger


class AIRequestRepository(BaseRepository[AIRequest]):
    """Repository for AI request operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, AIRequest)
    
    def get_by_user(self, user_id: int, skip: int = 0, limit: int = 100) -> List[AIRequest]:
        """Get AI requests by user ID"""
        return self.db.query(AIRequest).filter(
            AIRequest.user_id == user_id
        ).order_by(desc(AIRequest.created_at)).offset(skip).limit(limit).all()
    
    def get_pending_requests(self, limit: int = 50) -> List[AIRequest]:
        """Get pending requests ordered by priority and creation time"""
        return self.db.query(AIRequest).filter(
            AIRequest.status == RequestStatus.PENDING.value
        ).order_by(
            desc(AIRequest.priority),
            AIRequest.created_at
        ).limit(limit).all()
    
    def get_processing_requests(self) -> List[AIRequest]:
        """Get currently processing requests"""
        return self.db.query(AIRequest).filter(
            AIRequest.status == RequestStatus.PROCESSING.value
        ).all()
    
    def get_requests_by_status(self, status: RequestStatus, 
                              skip: int = 0, limit: int = 100) -> List[AIRequest]:
        """Get requests filtered by status"""
        return self.db.query(AIRequest).filter(
            AIRequest.status == status.value
        ).order_by(desc(AIRequest.created_at)).offset(skip).limit(limit).all()
    
    def get_user_request_count(self, user_id: int, 
                              time_period: Optional[timedelta] = None) -> int:
        """Get user's request count for specified time period"""
        query = self.db.query(AIRequest).filter(AIRequest.user_id == user_id)
        
        if time_period:
            since = datetime.utcnow() - time_period
            query = query.filter(AIRequest.created_at >= since)
        
        return query.count()
    
    def get_user_token_usage(self, user_id: int,
                            time_period: Optional[timedelta] = None) -> int:
        """Get user's total token usage for specified time period"""
        query = self.db.query(func.sum(AIRequest.tokens_used)).filter(
            AIRequest.user_id == user_id,
            AIRequest.status == RequestStatus.COMPLETED.value
        )
        
        if time_period:
            since = datetime.utcnow() - time_period
            query = query.filter(AIRequest.created_at >= since)
        
        result = query.scalar()
        return result or 0
    
    def get_requests_by_category(self, category: str,
                                skip: int = 0, limit: int = 100) -> List[AIRequest]:
        """Get requests by category"""
        return self.db.query(AIRequest).filter(
            AIRequest.category == category
        ).order_by(desc(AIRequest.created_at)).offset(skip).limit(limit).all()
    
    def get_failed_requests(self, since: Optional[datetime] = None,
                           skip: int = 0, limit: int = 100) -> List[AIRequest]:
        """Get failed requests with optional time filter"""
        query = self.db.query(AIRequest).filter(
            AIRequest.status == RequestStatus.FAILED.value
        )
        
        if since:
            query = query.filter(AIRequest.created_at >= since)
        
        return query.order_by(desc(AIRequest.created_at)).offset(skip).limit(limit).all()
    
    def get_requests_with_high_processing_time(self, 
                                             threshold_seconds: float = 30.0,
                                             skip: int = 0, 
                                             limit: int = 100) -> List[AIRequest]:
        """Get requests that took longer than threshold to process"""
        return self.db.query(AIRequest).filter(
            and_(
                AIRequest.processing_time > threshold_seconds,
                AIRequest.status == RequestStatus.COMPLETED.value
            )
        ).order_by(desc(AIRequest.processing_time)).offset(skip).limit(limit).all()
    
    def update_status(self, request_id: int, status: RequestStatus) -> Optional[AIRequest]:
        """Update request status"""
        request = self.get(request_id)
        if request:
            request.status = status.value
            if status == RequestStatus.PROCESSING:
                request.started_at = datetime.utcnow()
            elif status in [RequestStatus.COMPLETED, RequestStatus.FAILED]:
                request.completed_at = datetime.utcnow()
                if request.started_at:
                    request.processing_time = (request.completed_at - request.started_at).total_seconds()
            
            self.db.add(request)
            self.db.flush()
            self.db.refresh(request)
        
        return request
    
    def mark_as_completed(self, request_id: int, result_data: Dict[str, Any],
                         tokens_used: int = 0) -> Optional[AIRequest]:
        """Mark request as completed with results"""
        request = self.get(request_id)
        if request:
            request.mark_as_completed(result_data, tokens_used)
            self.db.add(request)
            self.db.flush()
            self.db.refresh(request)
        
        return request
    
    def mark_as_failed(self, request_id: int, error_message: str) -> Optional[AIRequest]:
        """Mark request as failed with error message"""
        request = self.get(request_id)
        if request:
            request.mark_as_failed(error_message)
            self.db.add(request)
            self.db.flush()
            self.db.refresh(request)
        
        return request
    
    def set_user_rating(self, request_id: int, rating: int, 
                       feedback: Optional[str] = None) -> Optional[AIRequest]:
        """Set user rating for completed request"""
        request = self.get(request_id)
        if request and request.is_completed:
            request.user_rating = rating
            if feedback:
                request.user_feedback = feedback
            
            self.db.add(request)
            self.db.flush()
            self.db.refresh(request)
        
        return request
    
    def get_analytics_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get analytics data for specified date range"""
        query = self.db.query(AIRequest).filter(
            and_(
                AIRequest.created_at >= start_date,
                AIRequest.created_at <= end_date
            )
        )
        
        total_requests = query.count()
        
        # Status breakdown
        status_counts = {}
        for status in RequestStatus:
            count = query.filter(AIRequest.status == status.value).count()
            status_counts[status.value] = count
        
        # Performance metrics
        completed_query = query.filter(AIRequest.status == RequestStatus.COMPLETED.value)
        
        avg_processing_time = self.db.query(
            func.avg(AIRequest.processing_time)
        ).filter(
            and_(
                AIRequest.created_at >= start_date,
                AIRequest.created_at <= end_date,
                AIRequest.status == RequestStatus.COMPLETED.value
            )
        ).scalar() or 0
        
        total_tokens = self.db.query(
            func.sum(AIRequest.tokens_used)
        ).filter(
            and_(
                AIRequest.created_at >= start_date,
                AIRequest.created_at <= end_date,
                AIRequest.status == RequestStatus.COMPLETED.value
            )
        ).scalar() or 0
        
        # Category breakdown
        category_counts = self.db.query(
            AIRequest.category,
            func.count(AIRequest.id)
        ).filter(
            and_(
                AIRequest.created_at >= start_date,
                AIRequest.created_at <= end_date
            )
        ).group_by(AIRequest.category).all()
        
        return {
            "total_requests": total_requests,
            "status_breakdown": status_counts,
            "avg_processing_time": float(avg_processing_time),
            "total_tokens_used": total_tokens,
            "category_breakdown": dict(category_counts)
        }
    
    def cleanup_old_requests(self, days_old: int = 90) -> int:
        """Clean up old completed/failed requests"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        deleted_count = self.db.query(AIRequest).filter(
            and_(
                AIRequest.created_at < cutoff_date,
                AIRequest.status.in_([
                    RequestStatus.COMPLETED.value,
                    RequestStatus.FAILED.value,
                    RequestStatus.CANCELLED.value
                ])
            )
        ).delete(synchronize_session=False)
        
        self.db.flush()
        
        structured_logger.log_database_operation(
            "CLEANUP", "ai_requests", 0, affected_rows=deleted_count
        )
        
        return deleted_count