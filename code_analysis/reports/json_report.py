"""
JSON Report Generator for code analysis results.

Provides structured JSON output for programmatic processing and CI/CD integration.
"""

import json
from datetime import datetime
from typing import Dict, Any
from code_analysis.models.results import AnalysisResult
from code_analysis.utils.config_manager import ConfigurationManager


class JSONReportGenerator:
    """Generator for JSON-formatted analysis reports."""
    
    def __init__(self, config: ConfigurationManager):
        """
        Initialize JSON report generator.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.indent = 2 if config.get('report.verbose', True) else None
    
    def generate_report(self, result: AnalysisResult) -> str:
        """
        Generate JSON report from analysis results.
        
        Args:
            result: Analysis results
            
        Returns:
            JSON formatted report string
        """
        report_data = self._build_report_structure(result)
        return json.dumps(report_data, indent=self.indent, default=str)
    
    def _build_report_structure(self, result: AnalysisResult) -> Dict[str, Any]:
        """
        Build the report data structure.
        
        Args:
            result: Analysis results
            
        Returns:
            Dictionary containing complete report data
        """
        return {
            "analysis_metadata": {
                "timestamp": result.scan_timestamp.isoformat(),
                "project_path": result.project_path,
                "files_analyzed": result.files_analyzed,
                "configuration": result.configuration
            },
            "summary": result.summary.to_dict(),
            "unused_imports": {
                "count": len(result.unused_imports),
                "items": [ui.to_dict() for ui in result.unused_imports]
            },
            "type_errors": {
                "count": len(result.type_errors),
                "items": [te.to_dict() for te in result.type_errors]
            },
            "recommendations": self._generate_recommendations(result)
        }
    
    def _generate_recommendations(self, result: AnalysisResult) -> list:
        """
        Generate actionable recommendations.
        
        Args:
            result: Analysis results
            
        Returns:
            List of recommendation dictionaries
        """
        recommendations = []
        
        if result.summary.total_unused_imports > 0:
            recommendations.append({
                "category": "unused_imports",
                "priority": "medium",
                "message": f"Remove {result.summary.total_unused_imports} unused import(s) to clean up the codebase",
                "impact": f"Potential savings: {result.summary.potential_savings.potential_memory_savings_kb:.2f} KB"
            })
        
        if result.summary.total_type_errors > 0:
            recommendations.append({
                "category": "type_errors",
                "priority": "high",
                "message": f"Fix {result.summary.total_type_errors} type error(s) to improve type safety",
                "impact": "Better IDE support and fewer runtime errors"
            })
        
        if result.summary.files_with_issues > result.summary.total_files_analyzed * 0.5:
            recommendations.append({
                "category": "code_quality",
                "priority": "medium",
                "message": "More than 50% of files have issues. Consider a comprehensive code review.",
                "impact": "Improved overall code quality"
            })
        
        return recommendations
    
    def save_report(self, result: AnalysisResult, output_path: str) -> None:
        """
        Save report to a JSON file.
        
        Args:
            result: Analysis results
            output_path: Path to save the JSON file
        """
        report = self.generate_report(result)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
    
    def generate_summary_only(self, result: AnalysisResult) -> str:
        """
        Generate a summary-only JSON report.
        
        Args:
            result: Analysis results
            
        Returns:
            JSON formatted summary string
        """
        summary_data = {
            "timestamp": result.scan_timestamp.isoformat(),
            "project_path": result.project_path,
            "summary": result.summary.to_dict(),
            "files_analyzed": result.files_analyzed
        }
        
        return json.dumps(summary_data, indent=self.indent, default=str)
