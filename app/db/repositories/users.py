"""
Users Repository
Specialized repository for user management operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from .base import BaseRepository
from ..models import User, UserRole
from ...utils.logger import structured_logger


class UsersRepository(BaseRepository[User]):
    """Repository for user management operations"""
    
    def __init__(self, db: Session):
        super().__init__(db, User)
    
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all active users"""
        return self.db.query(User).filter(
            User.is_active == True
        ).order_by(User.username).offset(skip).limit(limit).all()
    
    def get_by_role(self, role: UserRole, 
                   active_only: bool = True,
                   skip: int = 0, limit: int = 100) -> List[User]:
        """Get users by role"""
        query = self.db.query(User).filter(User.role == role.value)
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        return query.order_by(User.username).offset(skip).limit(limit).all()
    
    def search_users(self, search_term: str,
                    active_only: bool = True,
                    skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, or full name"""
        query = self.db.query(User).filter(
            func.lower(User.username).contains(search_term.lower()) |
            func.lower(User.email).contains(search_term.lower()) |
            func.lower(User.full_name).contains(search_term.lower())
        )
        
        if active_only:
            query = query.filter(User.is_active == True)
        
        return query.order_by(User.username).offset(skip).limit(limit).all()
    
    def create_user(self, username: str, email: str, hashed_password: str,
                   full_name: Optional[str] = None,
                   role: UserRole = UserRole.USER) -> User:
        """Create a new user"""
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "full_name": full_name,
            "role": role.value,
            "is_active": True
        }
        
        return self.create(user_data)
    
    def update_password(self, user_id: int, new_hashed_password: str) -> Optional[User]:
        """Update user password"""
        user = self.get(user_id)
        if user:
            user.hashed_password = new_hashed_password
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """Update user's last login timestamp"""
        user = self.get(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def deactivate_user(self, user_id: int) -> Optional[User]:
        """Deactivate a user account"""
        user = self.get(user_id)
        if user:
            user.is_active = False
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def activate_user(self, user_id: int) -> Optional[User]:
        """Activate a user account"""
        user = self.get(user_id)
        if user:
            user.is_active = True
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def update_role(self, user_id: int, new_role: UserRole) -> Optional[User]:
        """Update user role"""
        user = self.get(user_id)
        if user:
            user.role = new_role.value
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def increment_request_count(self, user_id: int, tokens_used: int = 0) -> Optional[User]:
        """Increment user's request count and token usage"""
        user = self.get(user_id)
        if user:
            user.total_requests += 1
            user.monthly_requests += 1
            user.total_tokens_used += tokens_used
            user.monthly_tokens_used += tokens_used
            
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def reset_monthly_stats(self, user_id: int) -> Optional[User]:
        """Reset monthly statistics for a user"""
        user = self.get(user_id)
        if user:
            user.monthly_requests = 0
            user.monthly_tokens_used = 0
            
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def bulk_reset_monthly_stats(self) -> int:
        """Reset monthly statistics for all users"""
        updated_count = self.db.query(User).update({
            User.monthly_requests: 0,
            User.monthly_tokens_used: 0
        })
        
        self.db.flush()
        
        structured_logger.log_database_operation(
            "BULK_UPDATE", "users", 0, affected_rows=updated_count
        )
        
        return updated_count
    
    def get_users_exceeding_limits(self) -> List[User]:
        """Get users who have exceeded their usage limits"""
        return self.db.query(User).filter(
            and_(
                User.is_active == True,
                User.monthly_requests >= User.daily_request_limit * 30,  # Approximate monthly limit
            )
        ).all()
    
    def get_heavy_users(self, min_requests: int = 100,
                       time_period_days: int = 30) -> List[User]:
        """Get users with high usage in specified time period"""
        since = datetime.utcnow() - timedelta(days=time_period_days)
        
        # This would typically require a join with ai_requests table
        # For now, we'll use the monthly stats as approximation
        return self.db.query(User).filter(
            and_(
                User.is_active == True,
                User.monthly_requests >= min_requests
            )
        ).order_by(desc(User.monthly_requests)).all()
    
    def get_inactive_users(self, days_inactive: int = 30) -> List[User]:
        """Get users who haven't logged in for specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)
        
        return self.db.query(User).filter(
            and_(
                User.is_active == True,
                func.coalesce(User.last_login, User.created_at) < cutoff_date
            )
        ).order_by(User.last_login).all()
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        total_users = self.db.query(User).count()
        active_users = self.db.query(User).filter(User.is_active == True).count()
        
        # Role breakdown
        role_counts = {}
        for role in UserRole:
            count = self.db.query(User).filter(User.role == role.value).count()
            role_counts[role.value] = count
        
        # Recent registrations (last 30 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        recent_registrations = self.db.query(User).filter(
            User.created_at >= recent_cutoff
        ).count()
        
        # Active users (logged in last 30 days)
        active_cutoff = datetime.utcnow() - timedelta(days=30)
        recently_active = self.db.query(User).filter(
            User.last_login >= active_cutoff
        ).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "role_breakdown": role_counts,
            "recent_registrations": recent_registrations,
            "recently_active_users": recently_active
        }
    
    def update_usage_limits(self, user_id: int,
                           daily_request_limit: Optional[int] = None,
                           monthly_token_limit: Optional[int] = None) -> Optional[User]:
        """Update user's usage limits"""
        user = self.get(user_id)
        if user:
            if daily_request_limit is not None:
                user.daily_request_limit = daily_request_limit
            if monthly_token_limit is not None:
                user.monthly_token_limit = monthly_token_limit
            
            self.db.add(user)
            self.db.flush()
            self.db.refresh(user)
        
        return user
    
    def check_username_available(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if username is available"""
        query = self.db.query(User).filter(User.username == username)
        
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        
        return query.first() is None
    
    def check_email_available(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """Check if email is available"""
        query = self.db.query(User).filter(User.email == email)
        
        if exclude_user_id:
            query = query.filter(User.id != exclude_user_id)
        
        return query.first() is None