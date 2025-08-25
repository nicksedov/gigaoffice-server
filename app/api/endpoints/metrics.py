"""
Metrics and Analytics Endpoints
Endpoints for service monitoring, performance metrics, and usage analytics
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.models.health import MetricsResponse
from app.services.ai.factory import gigachat_factory
from app.services.kafka.service import kafka_service
from app.db.repositories.ai_requests import AIRequestRepository
from app.db.session import get_db
from app.utils.logger import structured_logger
from sqlalchemy.orm import Session

# Create router
router = APIRouter(prefix="/api", tags=["Metrics"])

# Dependencies
async def get_current_user():
    """Get current user (simplified implementation)"""
    # TODO: Implement proper authentication
    return {"id": 1, "username": "admin", "role": "admin"}

async def get_ai_request_repo(db: Session = Depends(get_db)) -> AIRequestRepository:
    """Get AI request repository instance"""
    return AIRequestRepository(db)

def validate_admin_access(current_user: Dict = Depends(get_current_user)):
    """Validate that user has admin access"""
    if not current_user or current_user.get("role") not in ["admin", "premium"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return current_user

@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    period: str = "day",
    current_user: Dict = Depends(validate_admin_access)
):
    """
    Get comprehensive service metrics
    
    Args:
        period: Time period for metrics (hour, day, week, month)
        current_user: Authenticated admin user
    
    Returns:
        MetricsResponse: Service performance and usage metrics
    """
    try:
        structured_logger.log_api_request(
            endpoint="/api/metrics",
            method="GET",
            duration=0,
            user_id=str(current_user.get("id"))
        )
        
        # Validate period parameter
        valid_periods = ["hour", "day", "week", "month"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Get GigaChat statistics
        try:
            generate_service = gigachat_factory.get_service("generate")
            gigachat_stats = generate_service.get_usage_statistics()
        except Exception as e:
            logger.warning(f"Failed to get GigaChat stats: {e}")
            gigachat_stats = {"total_tokens_used": 0}
        
        # Get Kafka queue information
        try:
            kafka_info = kafka_service.get_queue_info()
            kafka_stats = kafka_info.get("statistics", {})
        except Exception as e:
            logger.warning(f"Failed to get Kafka stats: {e}")
            kafka_stats = {
                "messages_sent": 0,
                "messages_received": 0,
                "messages_failed": 0,
                "avg_processing_time": 0
            }
        
        # Calculate success/failure rates
        total_requests = kafka_stats.get("messages_received", 0)
        failed_requests = kafka_stats.get("messages_failed", 0)
        successful_requests = max(0, total_requests - failed_requests)
        
        metrics = MetricsResponse(
            period=period,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_processing_time=kafka_stats.get("avg_processing_time", 0),
            total_tokens_used=gigachat_stats.get("total_tokens_used", 0)
        )
        
        structured_logger.log_service_call(
            service="metrics",
            method="get_metrics",
            duration=0,
            success=True,
            metadata={
                "period": period,
                "total_requests": total_requests,
                "tokens_used": metrics.total_tokens_used
            }
        )
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        structured_logger.log_service_call(
            service="metrics",
            method="get_metrics",
            duration=0,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/detailed")
async def get_detailed_metrics(
    period: str = "day",
    current_user: Dict = Depends(validate_admin_access)
):
    """
    Get detailed service metrics with breakdown by components
    
    Args:
        period: Time period for metrics
        current_user: Authenticated admin user
    
    Returns:
        Dict with detailed metrics for all service components
    """
    try:
        # Period validation
        valid_periods = ["hour", "day", "week", "month"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Calculate time range
        period_hours = {"hour": 1, "day": 24, "week": 168, "month": 720}
        hours = period_hours.get(period, 24)
        start_time = datetime.now() - timedelta(hours=hours)
        
        # GigaChat metrics
        gigachat_metrics = {}
        try:
            generate_service = gigachat_factory.get_service("generate")
            classify_service = gigachat_factory.get_service("classify")
            
            gigachat_metrics = {
                "generate_service": generate_service.get_usage_statistics(),
                "classify_service": classify_service.get_usage_statistics(),
                "health_status": {
                    "generate": generate_service.check_service_health(),
                    "classify": classify_service.check_service_health()
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get detailed GigaChat metrics: {e}")
            gigachat_metrics = {"error": str(e)}
        
        # Kafka metrics
        kafka_metrics = {}
        try:
            kafka_metrics = {
                "queue_info": kafka_service.get_queue_info(),
                "health_status": kafka_service.get_health_status()
            }
        except Exception as e:
            logger.warning(f"Failed to get Kafka metrics: {e}")
            kafka_metrics = {"error": str(e)}
        
        # System metrics (placeholder for future implementation)
        system_metrics = {
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "disk_usage": 0.0,
            "active_connections": 0
        }
        
        return {
            "status": "success",
            "period": period,
            "time_range": {
                "start": start_time.isoformat(),
                "end": datetime.now().isoformat(),
                "hours": hours
            },
            "gigachat": gigachat_metrics,
            "kafka": kafka_metrics,
            "system": system_metrics,
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting detailed metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/performance")
async def get_performance_metrics(
    current_user: Dict = Depends(validate_admin_access),
    ai_repo: AIRequestRepository = Depends(get_ai_request_repo)
):
    """
    Get performance-specific metrics
    
    Args:
        current_user: Authenticated admin user
        ai_repo: AI request repository
    
    Returns:
        Dict with performance metrics and trends
    """
    try:
        # Get recent performance data
        recent_requests = ai_repo.get_recent_completed(limit=100)
        
        if not recent_requests:
            return {
                "status": "success",
                "message": "No recent completed requests",
                "metrics": {
                    "avg_processing_time": 0,
                    "min_processing_time": 0,
                    "max_processing_time": 0,
                    "total_requests": 0
                }
            }
        
        # Calculate performance metrics
        processing_times = [req.processing_time for req in recent_requests if req.processing_time]
        token_counts = [req.tokens_used for req in recent_requests if req.tokens_used]
        
        performance_metrics = {
            "processing_times": {
                "avg": sum(processing_times) / len(processing_times) if processing_times else 0,
                "min": min(processing_times) if processing_times else 0,
                "max": max(processing_times) if processing_times else 0,
                "count": len(processing_times)
            },
            "token_usage": {
                "avg": sum(token_counts) / len(token_counts) if token_counts else 0,
                "min": min(token_counts) if token_counts else 0,
                "max": max(token_counts) if token_counts else 0,
                "total": sum(token_counts) if token_counts else 0
            },
            "request_volume": {
                "total": len(recent_requests),
                "completed": len([r for r in recent_requests if r.status == "completed"]),
                "failed": len([r for r in recent_requests if r.status == "failed"])
            }
        }
        
        return {
            "status": "success",
            "timeframe": "last_100_requests",
            "metrics": performance_metrics,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/usage")
async def get_usage_analytics(
    period: str = "week",
    current_user: Dict = Depends(validate_admin_access)
):
    """
    Get usage analytics and trends
    
    Args:
        period: Analysis period
        current_user: Authenticated admin user
    
    Returns:
        Dict with usage analytics data
    """
    try:
        # Get prompt usage analytics
        from app.services.prompts.manager import prompt_manager
        
        period_days = {"day": 1, "week": 7, "month": 30}
        days = period_days.get(period, 7)
        
        prompt_analytics = await prompt_manager.get_usage_analytics(days=days)
        
        # Combine with service metrics
        usage_data = {
            "period": period,
            "days_analyzed": days,
            "prompt_analytics": prompt_analytics,
            "service_uptime": {
                "kafka_status": kafka_service.get_health_status().get("status"),
                "gigachat_status": "unknown"  # Will be filled by actual health check
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # Add GigaChat service status
        try:
            generate_service = gigachat_factory.get_service("generate")
            health = generate_service.check_service_health()
            usage_data["service_uptime"]["gigachat_status"] = health.get("status")
        except Exception:
            pass
        
        return {
            "status": "success",
            "data": usage_data
        }
        
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/export")
async def export_metrics(
    period: str = "month",
    format: str = "json",
    current_user: Dict = Depends(validate_admin_access)
):
    """
    Export metrics data for external analysis
    
    Args:
        period: Time period for export
        format: Export format (json or csv)
        current_user: Authenticated admin user
    
    Returns:
        Exported metrics data
    """
    try:
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Unsupported format")
        
        # Get comprehensive metrics
        detailed_metrics = await get_detailed_metrics(period, current_user)
        
        if format == "json":
            import json
            from fastapi.responses import Response
            
            return Response(
                content=json.dumps(detailed_metrics, indent=2, ensure_ascii=False),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=metrics_{period}.json"}
            )
        
        elif format == "csv":
            # Simple CSV export (flatten the data)
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow(["Metric", "Value", "Period", "Timestamp"])
            
            # Write basic metrics
            basic_metrics = await get_metrics(period, current_user)
            writer.writerow(["Total Requests", basic_metrics.total_requests, period, datetime.now().isoformat()])
            writer.writerow(["Successful Requests", basic_metrics.successful_requests, period, datetime.now().isoformat()])
            writer.writerow(["Failed Requests", basic_metrics.failed_requests, period, datetime.now().isoformat()])
            writer.writerow(["Average Processing Time", basic_metrics.avg_processing_time, period, datetime.now().isoformat()])
            writer.writerow(["Total Tokens Used", basic_metrics.total_tokens_used, period, datetime.now().isoformat()])
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=metrics_{period}.csv"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))