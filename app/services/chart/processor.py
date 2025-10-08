"""
Chart Processing Service for Kafka Consumer
Service to handle chart generation requests from Kafka queue
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from app.models.types.enums import RequestStatus
from app.models.orm.chart_request import ChartRequest
from app.models.api.chart import ChartGenerationRequest, DataSource
from app.services.database.session import get_db_session
from app.services.chart import chart_intelligence_service, chart_validation_service

class ChartProcessingService:
    """Service for processing chart generation requests from Kafka"""
    
    def __init__(self):
        self.processing_stats = {
            "charts_processed": 0,
            "charts_failed": 0,
            "total_processing_time": 0.0
        }
    
    async def process_chart_request(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a chart generation request from Kafka"""
        
        request_id = message_data.get("id")
        input_data = message_data.get("input_data", [])
        
        if not input_data or not input_data[0].get("chart_request"):
            return {
                "success": False,
                "error": "Invalid chart request data",
                "request_id": request_id
            }
        
        chart_request_data = input_data[0]["chart_request"]
        
        try:
            # Parse chart request
            chart_request = ChartGenerationRequest(**chart_request_data)
            
            start_time = datetime.now()
            
            # Update database status to processing
            with get_db_session() as db:
                db_request = db.query(ChartRequest).filter(ChartRequest.id == request_id).first()
                if db_request:
                    db_request.status = RequestStatus.PROCESSING.value
                    db_request.started_at = start_time
                    db.commit()
            
            # Process chart generation
            result = await self._generate_chart(chart_request, request_id)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Update database with results
            with get_db_session() as db:
                db_request = db.query(ChartRequest).filter(ChartRequest.id == request_id).first()
                if db_request:
                    if result["success"]:
                        db_request.status = RequestStatus.COMPLETED.value
                        db_request.chart_config = result.get("chart_config")
                        db_request.chart_type = result.get("chart_type")
                        db_request.recommended_chart_types = result.get("recommendations", [])
                        db_request.data_analysis = result.get("data_analysis", {})
                        db_request.confidence_score = result.get("confidence_score", 0.0)
                        db_request.tokens_used = result.get("tokens_used", 0)
                        self.processing_stats["charts_processed"] += 1
                    else:
                        db_request.status = RequestStatus.FAILED.value
                        db_request.error_message = result.get("error", "Unknown error")
                        self.processing_stats["charts_failed"] += 1
                    
                    db_request.completed_at = end_time
                    db_request.processing_time = processing_time
                    db.commit()
            
            self.processing_stats["total_processing_time"] += processing_time
            
            logger.info(f"Chart processing completed for request {request_id} in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing chart request {request_id}: {e}")
            
            # Update database status to failed
            with get_db_session() as db:
                db_request = db.query(ChartRequest).filter(ChartRequest.id == request_id).first()
                if db_request:
                    db_request.status = RequestStatus.FAILED.value
                    db_request.error_message = str(e)
                    db_request.completed_at = datetime.now()
                    db.commit()
            
            self.processing_stats["charts_failed"] += 1
            
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id
            }
    
    async def _generate_chart(self, chart_request: ChartGenerationRequest, request_id: str) -> Dict[str, Any]:
        """Generate chart using AI services"""
        
        try:
            # Validate data source
            is_valid_data, data_errors = chart_validation_service.validate_data_source(chart_request.data_source)
            if not is_valid_data:
                return {
                    "success": False,
                    "error": f"Invalid data source: {', '.join(data_errors)}",
                    "request_id": request_id
                }
            
            # Get chart preferences as dict
            chart_preferences = chart_request.chart_preferences.dict() if chart_request.chart_preferences else None
            
            # Get AI recommendation
            logger.info(f"Getting AI recommendation for chart request {request_id}")
            recommendation = await chart_intelligence_service.recommend_chart_type(
                chart_request.data_source,
                chart_request.chart_instruction,
                chart_preferences
            )
            
            # Generate chart configuration
            logger.info(f"Generating chart config for request {request_id}")
            chart_config = await chart_intelligence_service.generate_chart_config(
                chart_request.data_source,
                chart_request.chart_instruction,
                recommendation.primary_recommendation.recommended_chart_type,
                chart_preferences
            )
            
            # Validate generated configuration
            is_valid, validation_errors = chart_validation_service.validate_chart_config(chart_config)
            is_compatible, compatibility_warnings = chart_validation_service.validate_r7_office_compatibility(chart_config)
            
            if not is_valid:
                logger.warning(f"Generated chart config has validation errors: {validation_errors}")
            
            if not is_compatible:
                logger.warning(f"Generated chart config has compatibility warnings: {compatibility_warnings}")
            
            # Prepare result
            result = {
                "success": True,
                "request_id": request_id,
                "chart_config": chart_config.dict(),
                "chart_type": chart_config.chart_type.value,
                "recommendations": [
                    rec.dict() for rec in [recommendation.primary_recommendation] + recommendation.alternative_recommendations
                ],
                "data_analysis": recommendation.data_analysis,
                "confidence_score": recommendation.primary_recommendation.confidence,
                "tokens_used": recommendation.generation_metadata.get("tokens_used", 0),
                "processing_metadata": {
                    "validation_errors": validation_errors,
                    "compatibility_warnings": compatibility_warnings,
                    "is_valid": is_valid,
                    "is_r7_office_compatible": is_compatible
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in chart generation for request {request_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "request_id": request_id
            }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        avg_processing_time = (
            self.processing_stats["total_processing_time"] / self.processing_stats["charts_processed"]
            if self.processing_stats["charts_processed"] > 0 else 0.0
        )
        
        return {
            "charts_processed": self.processing_stats["charts_processed"],
            "charts_failed": self.processing_stats["charts_failed"],
            "success_rate": (
                self.processing_stats["charts_processed"] / 
                (self.processing_stats["charts_processed"] + self.processing_stats["charts_failed"])
                if (self.processing_stats["charts_processed"] + self.processing_stats["charts_failed"]) > 0 else 0.0
            ),
            "average_processing_time": avg_processing_time,
            "total_processing_time": self.processing_stats["total_processing_time"]
        }

# Global instance
chart_processing_service = ChartProcessingService()