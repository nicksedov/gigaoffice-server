"""
Console Report Generator for code analysis results.

Provides formatted console output with color coding and detailed information
about unused imports and type errors.
"""

import os
from typing import List, Dict, Any
from code_analysis.models.results import AnalysisResult, UnusedImport, TypeError, ImportType
from code_analysis.utils.config_manager import ConfigurationManager


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    @classmethod
    def disable(cls):
        """Disable colors."""
        cls.HEADER = ''
        cls.OKBLUE = ''
        cls.OKCYAN = ''
        cls.OKGREEN = ''
        cls.WARNING = ''
        cls.FAIL = ''
        cls.ENDC = ''
        cls.BOLD = ''
        cls.UNDERLINE = ''


class ConsoleReportGenerator:
    """Generator for console-formatted analysis reports."""
    
    def __init__(self, config: ConfigurationManager):
        """
        Initialize console report generator.
        
        Args:
            config: Configuration manager
        """
        self.config = config
        self.use_colors = config.get('report.color_output', True)
        self.verbose = config.is_verbose()
        self.group_by_file = config.get('report.group_by_file', True)
        
        if not self.use_colors:
            Colors.disable()
    
    def generate_report(self, result: AnalysisResult) -> str:
        """
        Generate console report from analysis results.
        
        Args:
            result: Analysis results
            
        Returns:
            Formatted report string
        """
        lines = []
        
        # Header
        lines.append(self._generate_header(result))
        lines.append("")
        
        # Summary
        lines.append(self._generate_summary(result))
        lines.append("")
        
        # Unused imports section
        if result.unused_imports:
            lines.append(self._generate_unused_imports_section(result))
            lines.append("")
        
        # Type errors section
        if result.type_errors:
            lines.append(self._generate_type_errors_section(result))
            lines.append("")
        
        # Footer
        lines.append(self._generate_footer(result))
        
        return "\n".join(lines)
    
    def _generate_header(self, result: AnalysisResult) -> str:
        """Generate report header."""
        header = f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n"
        header += f"{Colors.BOLD}{Colors.HEADER}Code Analysis Report{Colors.ENDC}\n"
        header += f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.ENDC}\n"
        header += f"Project: {Colors.BOLD}{result.project_path}{Colors.ENDC}\n"
        header += f"Scan Time: {result.scan_timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        header += f"Files Analyzed: {result.files_analyzed}"
        return header
    
    def _generate_summary(self, result: AnalysisResult) -> str:
        """Generate summary section."""
        summary = result.summary
        
        lines = [
            f"{Colors.BOLD}Summary{Colors.ENDC}",
            f"{'-'*80}",
            f"Total Unused Imports: {Colors.WARNING}{summary.total_unused_imports}{Colors.ENDC}",
            f"Total Type Errors: {Colors.FAIL}{summary.total_type_errors}{Colors.ENDC}",
            f"Files with Issues: {summary.files_with_issues}/{summary.total_files_analyzed}",
        ]
        
        if summary.potential_savings.unused_import_count > 0:
            lines.append("")
            lines.append(f"{Colors.BOLD}Potential Savings:{Colors.ENDC}")
            lines.append(f"  Unused imports: {summary.potential_savings.unused_import_count}")
            lines.append(f"  Estimated memory savings: {summary.potential_savings.potential_memory_savings_kb:.2f} KB")
            lines.append(f"  Estimated import time savings: {summary.potential_savings.import_time_savings_ms:.2f} ms")
        
        return "\n".join(lines)
    
    def _generate_unused_imports_section(self, result: AnalysisResult) -> str:
        """Generate unused imports section."""
        lines = [
            f"{Colors.BOLD}{Colors.WARNING}Unused Imports{Colors.ENDC}",
            f"{'-'*80}",
        ]
        
        if self.group_by_file:
            # Group by file
            by_file: Dict[str, List[UnusedImport]] = {}
            for unused in result.unused_imports:
                if unused.file_path not in by_file:
                    by_file[unused.file_path] = []
                by_file[unused.file_path].append(unused)
            
            for file_path in sorted(by_file.keys()):
                rel_path = os.path.relpath(file_path, result.project_path)
                lines.append(f"\n{Colors.BOLD}{Colors.OKCYAN}{rel_path}{Colors.ENDC}")
                
                for unused in sorted(by_file[file_path], key=lambda x: x.line_number):
                    lines.append(self._format_unused_import(unused, result.project_path))
        else:
            # List all
            for unused in sorted(result.unused_imports, key=lambda x: (x.file_path, x.line_number)):
                lines.append(self._format_unused_import(unused, result.project_path))
        
        return "\n".join(lines)
    
    def _format_unused_import(self, unused: UnusedImport, project_path: str) -> str:
        """Format a single unused import."""
        rel_path = os.path.relpath(unused.file_path, project_path)
        
        lines = [
            f"  Line {unused.line_number}: {Colors.WARNING}{unused.import_statement}{Colors.ENDC}",
        ]
        
        if self.verbose:
            lines.append(f"    Type: {self._format_import_type(unused.import_type)}")
            if unused.unused_symbols:
                lines.append(f"    Unused: {', '.join(unused.unused_symbols)}")
            
            if self.config.get('report.show_suggestions', True) and unused.suggestions:
                lines.append(f"    {Colors.OKGREEN}Suggestions:{Colors.ENDC}")
                for suggestion in unused.suggestions:
                    lines.append(f"      - {suggestion}")
        
        return "\n".join(lines)
    
    def _generate_type_errors_section(self, result: AnalysisResult) -> str:
        """Generate type errors section."""
        lines = [
            f"{Colors.BOLD}{Colors.FAIL}Type Errors{Colors.ENDC}",
            f"{'-'*80}",
        ]
        
        if self.group_by_file:
            # Group by file
            by_file: Dict[str, List[TypeError]] = {}
            for error in result.type_errors:
                if error.file_path not in by_file:
                    by_file[error.file_path] = []
                by_file[error.file_path].append(error)
            
            for file_path in sorted(by_file.keys()):
                rel_path = os.path.relpath(file_path, result.project_path)
                lines.append(f"\n{Colors.BOLD}{Colors.OKCYAN}{rel_path}{Colors.ENDC}")
                
                for error in sorted(by_file[file_path], key=lambda x: x.line_number):
                    lines.append(self._format_type_error(error))
        else:
            # List all
            for error in sorted(result.type_errors, key=lambda x: (x.file_path, x.line_number)):
                lines.append(self._format_type_error(error))
        
        return "\n".join(lines)
    
    def _format_type_error(self, error: TypeError) -> str:
        """Format a single type error."""
        lines = [
            f"  Line {error.line_number}: {Colors.FAIL}{error.error_type.value}{Colors.ENDC}",
            f"    Symbol: {error.symbol_name}",
        ]
        
        if self.verbose:
            lines.append(f"    Context: {error.context}")
            
            if error.suggested_fix:
                lines.append(f"    {Colors.OKGREEN}Suggestion:{Colors.ENDC} {error.suggested_fix}")
        
        return "\n".join(lines)
    
    def _format_import_type(self, import_type: ImportType) -> str:
        """Format import type with color."""
        type_colors = {
            ImportType.STANDARD_LIBRARY: Colors.OKBLUE,
            ImportType.THIRD_PARTY: Colors.OKCYAN,
            ImportType.LOCAL_ABSOLUTE: Colors.OKGREEN,
            ImportType.LOCAL_RELATIVE: Colors.OKGREEN,
            ImportType.UNKNOWN: Colors.WARNING,
        }
        
        color = type_colors.get(import_type, '')
        return f"{color}{import_type.value}{Colors.ENDC}"
    
    def _generate_footer(self, result: AnalysisResult) -> str:
        """Generate report footer."""
        footer = f"{Colors.BOLD}{'='*80}{Colors.ENDC}\n"
        
        total_issues = result.summary.total_unused_imports + result.summary.total_type_errors
        
        if total_issues == 0:
            footer += f"{Colors.BOLD}{Colors.OKGREEN}✓ No issues found! Code quality is excellent.{Colors.ENDC}"
        else:
            footer += f"{Colors.BOLD}Total Issues Found: {total_issues}{Colors.ENDC}"
        
        return footer
    
    def print_report(self, result: AnalysisResult) -> None:
        """
        Print report to console.
        
        Args:
            result: Analysis results
        """
        report = self.generate_report(result)
        print(report)
