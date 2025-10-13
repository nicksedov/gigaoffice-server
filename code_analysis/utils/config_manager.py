"""
Configuration Manager for code analysis system.

Handles loading, validation, and management of configuration settings
from YAML files and command-line overrides.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml


class ConfigurationManager:
    """Manages configuration for the code analysis system."""
    
    DEFAULT_CONFIG = {
        "exclusions": [
            "__pycache__",
            "*.pyc",
            ".git",
            ".venv",
            "venv",
            "env",
            "*.egg-info",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
        ],
        "exclude_directories": [
            "migrations",
            ".git",
            "__pycache__",
        ],
        "import_categories": {
            "standard_library": [
                "os", "sys", "typing", "datetime", "json", "re",
                "pathlib", "collections", "functools", "itertools",
                "asyncio", "abc", "dataclasses", "enum", "copy",
                "time", "io", "logging", "warnings", "contextlib",
                "inspect", "ast", "importlib", "pkgutil"
            ]
        },
        "analysis_rules": {
            "ignore_star_imports": False,
            "check_string_imports": True,
            "check_type_annotations": True,
            "check_docstrings": True,
            "detect_dynamic_imports": True,
            "fastapi_patterns": {
                "check_dependency_injection": True,
                "check_router_registration": True,
                "check_pydantic_models": True,
            }
        },
        "report": {
            "verbose": True,
            "format": "console",
            "show_suggestions": True,
            "color_output": True,
            "group_by_file": True,
        },
        "performance": {
            "parallel_processing": True,
            "max_workers": 4,
            "cache_ast": True,
            "incremental_analysis": True,
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration YAML file. If None, uses default config.
        """
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)
        
        # Load standard library modules dynamically
        self._populate_standard_library()
        
        # Load third-party packages from requirements.txt
        self._load_third_party_packages()
    
    def load_from_file(self, config_path: str) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to YAML configuration file
        """
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge_config(user_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            print("Using default configuration.")
    
    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """
        Merge user configuration with default configuration.
        
        Args:
            user_config: User-provided configuration dictionary
        """
        for key, value in user_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    def _populate_standard_library(self) -> None:
        """Populate standard library modules list from sys.builtin_module_names."""
        standard_libs = set(self.config["import_categories"]["standard_library"])
        
        # Add builtin modules
        for module_name in sys.builtin_module_names:
            standard_libs.add(module_name)
        
        # Add common standard library modules
        common_stdlib = [
            "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
            "asyncore", "atexit", "base64", "bdb", "binascii", "binhex",
            "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb", "chunk",
            "cmath", "cmd", "code", "codecs", "codeop", "collections", "colorsys",
            "compileall", "concurrent", "configparser", "contextlib", "contextvars",
            "copy", "copyreg", "crypt", "csv", "ctypes", "curses", "dataclasses",
            "datetime", "dbm", "decimal", "difflib", "dis", "distutils", "doctest",
            "email", "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
            "fileinput", "fnmatch", "formatter", "fractions", "ftplib", "functools",
            "gc", "getopt", "getpass", "gettext", "glob", "graphlib", "grp", "gzip",
            "hashlib", "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
            "imp", "importlib", "inspect", "io", "ipaddress", "itertools", "json",
            "keyword", "lib2to3", "linecache", "locale", "logging", "lzma", "mailbox",
            "mailcap", "marshal", "math", "mimetypes", "mmap", "modulefinder", "multiprocessing",
            "netrc", "nis", "nntplib", "numbers", "operator", "optparse", "os", "ossaudiodev",
            "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil", "platform",
            "plistlib", "poplib", "posix", "posixpath", "pprint", "profile", "pstats",
            "pty", "pwd", "py_compile", "pyclbr", "pydoc", "queue", "quopri", "random",
            "re", "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
            "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
            "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
            "sqlite3", "ssl", "stat", "statistics", "string", "stringprep", "struct",
            "subprocess", "sunau", "symbol", "symtable", "sys", "sysconfig", "syslog",
            "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test", "textwrap",
            "threading", "time", "timeit", "tkinter", "token", "tokenize", "trace",
            "traceback", "tracemalloc", "tty", "turtle", "turtledemo", "types", "typing",
            "typing_extensions", "unicodedata", "unittest", "urllib", "uu", "uuid", "venv",
            "warnings", "wave", "weakref", "webbrowser", "wsgiref", "xdrlib", "xml",
            "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib"
        ]
        
        for module in common_stdlib:
            standard_libs.add(module)
        
        self.config["import_categories"]["standard_library"] = sorted(list(standard_libs))
    
    def _load_third_party_packages(self) -> None:
        """Load third-party package names from requirements.txt."""
        requirements_files = ["requirements.txt", "requirements-dev.txt", "setup.py"]
        third_party = set()
        
        for req_file in requirements_files:
            req_path = Path.cwd() / req_file
            if req_path.exists():
                try:
                    with open(req_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Extract package name (before version specifier)
                                package = line.split('==')[0].split('>=')[0].split('<=')[0].split('>')[0].split('<')[0].strip()
                                if package:
                                    # Normalize package name
                                    package = package.replace('-', '_').lower()
                                    third_party.add(package)
                except Exception as e:
                    print(f"Warning: Failed to read {req_file}: {e}")
        
        if "third_party" not in self.config["import_categories"]:
            self.config["import_categories"]["third_party"] = []
        
        self.config["import_categories"]["third_party"] = sorted(list(third_party))
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_exclusion_patterns(self) -> List[str]:
        """Get file/directory exclusion patterns."""
        return self.get("exclusions", [])
    
    def get_excluded_directories(self) -> List[str]:
        """Get directories to exclude from analysis."""
        return self.get("exclude_directories", [])
    
    def is_standard_library(self, module_name: str) -> bool:
        """
        Check if a module is part of the standard library.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if module is in standard library
        """
        standard_libs = self.get("import_categories.standard_library", [])
        base_module = module_name.split('.')[0]
        return base_module in standard_libs
    
    def is_third_party(self, module_name: str) -> bool:
        """
        Check if a module is a third-party package.
        
        Args:
            module_name: Name of the module to check
            
        Returns:
            True if module is a third-party package
        """
        third_party = self.get("import_categories.third_party", [])
        base_module = module_name.split('.')[0].replace('-', '_').lower()
        return base_module in third_party
    
    def should_check_type_annotations(self) -> bool:
        """Check if type annotation validation is enabled."""
        return self.get("analysis_rules.check_type_annotations", True)
    
    def should_check_fastapi_patterns(self) -> bool:
        """Check if FastAPI pattern detection is enabled."""
        return self.get("analysis_rules.fastapi_patterns.check_dependency_injection", True)
    
    def get_report_format(self) -> str:
        """Get configured report format."""
        return self.get("report.format", "console")
    
    def is_verbose(self) -> bool:
        """Check if verbose output is enabled."""
        return self.get("report.verbose", True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary."""
        return self.config.copy()
