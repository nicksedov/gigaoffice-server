"""
Code Analyzer - Main orchestrator for the analysis pipeline.

Coordinates all services to perform comprehensive code analysis including
unused import detection and type validation.
"""

import os
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from code_analysis.utils.config_manager import ConfigurationManager
from code_analysis.services.file_discovery import FileDiscoveryService
from code_analysis.services.ast_analysis import ASTAnalysisService
from code_analysis.services.import_resolver import ImportResolverService
from code_analysis.services.import_analyzer import ImportAnalyzer
from code_analysis.services.type_validation import TypeValidationService
from code_analysis.models.results import AnalysisResult, AnalysisSummary
from code_analysis.reports.console_report import ConsoleReportGenerator
from code_analysis.reports.json_report import JSONReportGenerator


class CodeAnalyzer:
    """Main analyzer orchestrating the analysis pipeline."""
    
    def __init__(self, project_root: str, config_path: Optional[str] = None):
        """
        Initialize code analyzer.
        
        Args:
            project_root: Root directory of the project to analyze
            config_path: Optional path to configuration file
        """
        self.project_root = os.path.abspath(project_root)
        self.config = ConfigurationManager(config_path)
        
        # Initialize services
        self.file_discovery = FileDiscoveryService(self.config)
        self.ast_service = ASTAnalysisService()
        self.resolver_service = ImportResolverService(self.config, self.project_root)
        self.import_analyzer = ImportAnalyzer(
            self.ast_service,
            self.resolver_service,
            self.config
        )
        self.type_validator = TypeValidationService(
            self.ast_service,
            self.resolver_service,
            self.config
        )
        
        # Initialize report generators
        self.console_reporter = ConsoleReportGenerator(self.config)
        self.json_reporter = JSONReportGenerator(self.config)
    
    def analyze(self, target_path: Optional[str] = None) -> AnalysisResult:
        """
        Perform comprehensive code analysis.
        
        Args:
            target_path: Optional specific path to analyze (defaults to project root)
            
        Returns:
            Analysis results
        """
        start_time = datetime.now()
        analysis_path = target_path if target_path else self.project_root
        
        print(f"Starting code analysis of: {analysis_path}")
        print("="*80)
        
        # Step 1: Discover Python files
        print("Step 1/5: Discovering Python files...")
        python_files = self.file_discovery.discover_python_files(analysis_path)
        print(f"Found {len(python_files)} Python files")
        
        if not python_files:
            print("No Python files found to analyze.")
            return self._create_empty_result()
        
        # Get project statistics
        stats = self.file_discovery.get_project_statistics(python_files)
        print(f"Total lines of code: {stats['total_lines']}")
        print()
        
        # Step 2: Extract imports and build dependency map
        print("Step 2/5: Extracting imports and building dependency map...")
        self._extract_imports(python_files)
        import_stats = self.resolver_service.get_import_statistics()
        print(f"Total imports found: {import_stats['total_imports']}")
        print()
        
        # Step 3: Analyze for unused imports
        print("Step 3/5: Analyzing for unused imports...")
        unused_imports = self._analyze_unused_imports(python_files)
        print(f"Found {len(unused_imports)} unused imports")
        print()
        
        # Step 4: Validate type annotations
        print("Step 4/5: Validating type annotations...")
        type_errors = self._validate_types(python_files)
        print(f"Found {len(type_errors)} type errors")
        print()
        
        # Step 5: Generate results
        print("Step 5/5: Generating analysis results...")
        result = AnalysisResult(
            project_path=self.project_root,
            scan_timestamp=start_time,
            files_analyzed=len(python_files),
            unused_imports=unused_imports,
            type_errors=type_errors,
            configuration=self.config.to_dict()
        )
        
        # Calculate summary
        result.calculate_summary()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"Analysis completed in {duration:.2f} seconds")
        print("="*80)
        print()
        
        return result
    
    def _extract_imports(self, files: List[str]) -> None:
        """
        Extract imports from all files.
        
        Args:
            files: List of Python file paths
        """
        for file_path in files:
            tree = self.ast_service.parse_file(file_path)
            if tree:
                imports = self.ast_service.extract_imports(tree)
                for import_info in imports:
                    self.resolver_service.track_import(import_info, file_path)
    
    def _analyze_unused_imports(self, files: List[str]) -> list:
        """
        Analyze files for unused imports.
        
        Args:
            files: List of Python file paths
            
        Returns:
            List of unused imports
        """
        all_unused = []
        
        if self.config.get('performance.parallel_processing', True):
            # Parallel processing
            max_workers = self.config.get('performance.max_workers', 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self.import_analyzer.analyze_file, f): f for f in files}
                
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        unused = future.result()
                        all_unused.extend(unused)
                    except Exception as e:
                        print(f"Error analyzing {file_path}: {e}")
        else:
            # Sequential processing
            for file_path in files:
                try:
                    unused = self.import_analyzer.analyze_file(file_path)
                    all_unused.extend(unused)
                except Exception as e:
                    print(f"Error analyzing {file_path}: {e}")
        
        return all_unused
    
    def _validate_types(self, files: List[str]) -> list:
        """
        Validate type annotations in files.
        
        Args:
            files: List of Python file paths
            
        Returns:
            List of type errors
        """
        all_errors = []
        
        if self.config.get('performance.parallel_processing', True):
            # Parallel processing
            max_workers = self.config.get('performance.max_workers', 4)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self.type_validator.validate_file, f): f for f in files}
                
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        errors = future.result()
                        all_errors.extend(errors)
                    except Exception as e:
                        print(f"Error validating types in {file_path}: {e}")
        else:
            # Sequential processing
            for file_path in files:
                try:
                    errors = self.type_validator.validate_file(file_path)
                    all_errors.extend(errors)
                except Exception as e:
                    print(f"Error validating types in {file_path}: {e}")
        
        return all_errors
    
    def _create_empty_result(self) -> AnalysisResult:
        """Create an empty analysis result."""
        return AnalysisResult(
            project_path=self.project_root,
            scan_timestamp=datetime.now(),
            files_analyzed=0,
            configuration=self.config.to_dict()
        )
    
    def generate_console_report(self, result: AnalysisResult) -> None:
        """
        Generate and print console report.
        
        Args:
            result: Analysis results
        """
        self.console_reporter.print_report(result)
    
    def save_json_report(self, result: AnalysisResult, output_path: str) -> None:
        """
        Save analysis results as JSON.
        
        Args:
            result: Analysis results
            output_path: Path to save JSON file
        """
        self.json_reporter.save_report(result, output_path)
        print(f"JSON report saved to: {output_path}")
    
    def get_statistics(self) -> dict:
        """
        Get comprehensive statistics about the analysis.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            "import_statistics": self.resolver_service.get_import_statistics(),
            "usage_statistics": self.import_analyzer.get_usage_statistics(),
            "validation_statistics": self.type_validator.get_validation_statistics(),
        }
