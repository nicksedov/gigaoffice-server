"""
Data models for code analysis results.

This module defines the core data structures used to represent analysis results,
including unused imports, type errors, and summary statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class ImportType(Enum):
    """Classification of import types."""
    STANDARD_LIBRARY = "standard"
    THIRD_PARTY = "third_party"
    LOCAL_RELATIVE = "local_relative"
    LOCAL_ABSOLUTE = "local_absolute"
    UNKNOWN = "unknown"


class TypeErrorType(Enum):
    """Classification of type validation errors."""
    MISSING_IMPORT = "missing_import"
    INVALID_REFERENCE = "invalid_reference"
    INCORRECT_GENERIC = "incorrect_generic"
    FORWARD_REFERENCE = "forward_reference"
    UNRESOLVED_TYPE = "unresolved_type"


@dataclass
class UnusedImport:
    """Represents an unused import statement in a file."""
    
    file_path: str
    line_number: int
    import_statement: str
    import_type: ImportType
    unused_symbols: List[str]
    suggestions: List[str] = field(default_factory=list)
    column_offset: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "import_statement": self.import_statement,
            "import_type": self.import_type.value,
            "unused_symbols": self.unused_symbols,
            "suggestions": self.suggestions,
            "column_offset": self.column_offset
        }


@dataclass
class TypeError:
    """Represents a type validation error."""
    
    file_path: str
    line_number: int
    error_type: TypeErrorType
    symbol_name: str
    context: str
    suggested_fix: str = ""
    column_offset: int = 0
    severity: str = "error"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "error_type": self.error_type.value,
            "symbol_name": self.symbol_name,
            "context": self.context,
            "suggested_fix": self.suggested_fix,
            "column_offset": self.column_offset,
            "severity": self.severity
        }


@dataclass
class EstimatedSavings:
    """Estimated savings from removing unused imports."""
    
    unused_import_count: int = 0
    potential_memory_savings_kb: float = 0.0
    import_time_savings_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "unused_import_count": self.unused_import_count,
            "potential_memory_savings_kb": self.potential_memory_savings_kb,
            "import_time_savings_ms": self.import_time_savings_ms
        }


@dataclass
class AnalysisSummary:
    """Summary statistics for analysis results."""
    
    total_unused_imports: int = 0
    total_type_errors: int = 0
    files_with_issues: int = 0
    total_files_analyzed: int = 0
    potential_savings: EstimatedSavings = field(default_factory=EstimatedSavings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_unused_imports": self.total_unused_imports,
            "total_type_errors": self.total_type_errors,
            "files_with_issues": self.files_with_issues,
            "total_files_analyzed": self.total_files_analyzed,
            "potential_savings": self.potential_savings.to_dict()
        }


@dataclass
class AnalysisResult:
    """Complete analysis results for a project."""
    
    project_path: str
    scan_timestamp: datetime
    files_analyzed: int
    unused_imports: List[UnusedImport] = field(default_factory=list)
    type_errors: List[TypeError] = field(default_factory=list)
    summary: AnalysisSummary = field(default_factory=AnalysisSummary)
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "project_path": self.project_path,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "files_analyzed": self.files_analyzed,
            "unused_imports": [ui.to_dict() for ui in self.unused_imports],
            "type_errors": [te.to_dict() for te in self.type_errors],
            "summary": self.summary.to_dict(),
            "configuration": self.configuration
        }
    
    def add_unused_import(self, unused_import: UnusedImport) -> None:
        """Add an unused import to the results."""
        self.unused_imports.append(unused_import)
        self.summary.total_unused_imports += 1
    
    def add_type_error(self, type_error: TypeError) -> None:
        """Add a type error to the results."""
        self.type_errors.append(type_error)
        self.summary.total_type_errors += 1
    
    def calculate_summary(self) -> None:
        """Calculate summary statistics from collected results."""
        files_with_issues = set()
        
        for unused_import in self.unused_imports:
            files_with_issues.add(unused_import.file_path)
        
        for type_error in self.type_errors:
            files_with_issues.add(type_error.file_path)
        
        self.summary.files_with_issues = len(files_with_issues)
        self.summary.total_files_analyzed = self.files_analyzed
        
        # Estimate savings (rough approximation)
        self.summary.potential_savings.unused_import_count = len(self.unused_imports)
        self.summary.potential_savings.potential_memory_savings_kb = len(self.unused_imports) * 0.5
        self.summary.potential_savings.import_time_savings_ms = len(self.unused_imports) * 0.1
