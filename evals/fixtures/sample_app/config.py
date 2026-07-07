"""
Todo Application - Configuration Module

This module contains configuration settings and constants for the todo application.
It provides a centralized place to manage application settings, file paths, and
other configuration parameters.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Main configuration class for the todo application"""

    # Application metadata
    APP_NAME = "Todo Application"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "A simple yet powerful todo manager built in Python"

    # Default file paths
    DEFAULT_DATA_DIR = os.path.expanduser("~/.todoapp")
    DEFAULT_TODO_FILE = "todos.json"
    DEFAULT_BACKUP_DIR = "backups"
    DEFAULT_EXPORT_DIR = "exports"

    # File settings
    AUTO_BACKUP = True
    BACKUP_COUNT = 5  # Number of backups to keep
    AUTO_SAVE = True

    # Display settings
    MAX_TITLE_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 1000
    MAX_TAG_LENGTH = 50

    # CLI settings
    DEFAULT_LIST_LIMIT = 20
    SHOW_COLORS = True
    SHOW_ICONS = True

    # Date/time settings
    DEFAULT_DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Priority settings
    PRIORITY_COLORS = {
        "high": "red",
        "medium": "yellow",
        "low": "green"
    }

    # Status settings
    STATUS_COLORS = {
        "pending": "yellow",
        "completed": "green",
        "cancelled": "red"
    }

    # Icons
    PRIORITY_ICONS = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }

    STATUS_ICONS = {
        "pending": "⏳",
        "completed": "✅",
        "cancelled": "❌"
    }

    # Export settings
    EXPORT_FORMATS = ["json", "csv", "txt", "md"]
    DEFAULT_EXPORT_FORMAT = "json"

    # Search settings
    SEARCH_CASE_SENSITIVE = False
    SEARCH_INCLUDE_TAGS = True
    SEARCH_INCLUDE_DESCRIPTION = True

    # Performance settings
    MAX_TODOS_IN_MEMORY = 10000
    AUTO_CLEANUP_DAYS = 365  # Days after which cancelled todos are auto-deleted

    @classmethod
    def get_data_dir(cls) -> str:
        """Get the data directory path"""
        return cls.DEFAULT_DATA_DIR

    @classmethod
    def get_todo_file_path(cls, filename: Optional[str] = None) -> str:
        """Get the full path to the todo file"""
        if filename is None:
            filename = cls.DEFAULT_TODO_FILE
        return os.path.join(cls.get_data_dir(), filename)

    @classmethod
    def get_backup_dir(cls) -> str:
        """Get the backup directory path"""
        return os.path.join(cls.get_data_dir(), cls.DEFAULT_BACKUP_DIR)

    @classmethod
    def get_export_dir(cls) -> str:
        """Get the export directory path"""
        return os.path.join(cls.get_data_dir(), cls.DEFAULT_EXPORT_DIR)

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        directories = [
            cls.get_data_dir(),
            cls.get_backup_dir(),
            cls.get_export_dir()
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_config_dict(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            "app_name": cls.APP_NAME,
            "app_version": cls.APP_VERSION,
            "app_description": cls.APP_DESCRIPTION,
            "data_dir": cls.get_data_dir(),
            "todo_file": cls.get_todo_file_path(),
            "backup_dir": cls.get_backup_dir(),
            "export_dir": cls.get_export_dir(),
            "auto_backup": cls.AUTO_BACKUP,
            "backup_count": cls.BACKUP_COUNT,
            "auto_save": cls.AUTO_SAVE,
            "max_title_length": cls.MAX_TITLE_LENGTH,
            "max_description_length": cls.MAX_DESCRIPTION_LENGTH,
            "max_tag_length": cls.MAX_TAG_LENGTH,
            "default_list_limit": cls.DEFAULT_LIST_LIMIT,
            "show_colors": cls.SHOW_COLORS,
            "show_icons": cls.SHOW_ICONS,
            "default_date_format": cls.DEFAULT_DATE_FORMAT,
            "default_datetime_format": cls.DEFAULT_DATETIME_FORMAT,
            "priority_colors": cls.PRIORITY_COLORS,
            "status_colors": cls.STATUS_COLORS,
            "priority_icons": cls.PRIORITY_ICONS,
            "status_icons": cls.STATUS_ICONS,
            "export_formats": cls.EXPORT_FORMATS,
            "default_export_format": cls.DEFAULT_EXPORT_FORMAT,
            "search_case_sensitive": cls.SEARCH_CASE_SENSITIVE,
            "search_include_tags": cls.SEARCH_INCLUDE_TAGS,
            "search_include_description": cls.SEARCH_INCLUDE_DESCRIPTION,
            "max_todos_in_memory": cls.MAX_TODOS_IN_MEMORY,
            "auto_cleanup_days": cls.AUTO_CLEANUP_DAYS
        }


class DevelopmentConfig(Config):
    """Development configuration with debugging enabled"""

    DEBUG = True
    VERBOSE_LOGGING = True
    DEFAULT_TODO_FILE = "todos_dev.json"

    # More frequent backups for development
    BACKUP_COUNT = 10

    # Development-specific settings
    SHOW_DEBUG_INFO = True
    ENABLE_PROFILING = False


class ProductionConfig(Config):
    """Production configuration with optimizations"""

    DEBUG = False
    VERBOSE_LOGGING = False

    # Production optimizations
    MAX_TODOS_IN_MEMORY = 50000
    AUTO_CLEANUP_DAYS = 730  # 2 years

    # Security settings
    SECURE_FILE_PERMISSIONS = True
    VALIDATE_INPUT_STRICTLY = True


class TestConfig(Config):
    """Test configuration for unit tests"""

    DEBUG = True
    DEFAULT_DATA_DIR = os.path.join(os.getcwd(), "test_data")
    DEFAULT_TODO_FILE = "test_todos.json"

    # Test-specific settings
    AUTO_BACKUP = False
    AUTO_SAVE = False
    CLEANUP_AFTER_TESTS = True


# Environment-based configuration selection
def get_config() -> Config:
    """Get the appropriate configuration based on environment"""
    env = os.getenv("TODO_ENV", "development").lower()

    if env == "production":
        return ProductionConfig()
    elif env == "test":
        return TestConfig()
    else:
        return DevelopmentConfig()


# Global configuration instance
config = get_config()


# Configuration validation
def validate_config(config_instance: Config) -> bool:
    """Validate configuration settings"""
    try:
        # Check required attributes
        required_attrs = [
            "APP_NAME", "APP_VERSION", "DEFAULT_DATA_DIR", "DEFAULT_TODO_FILE"
        ]

        for attr in required_attrs:
            if not hasattr(config_instance, attr):
                print(f"Missing required configuration attribute: {attr}")
                return False

        # Check data types
        if not isinstance(config_instance.MAX_TITLE_LENGTH, int):
            print("MAX_TITLE_LENGTH must be an integer")
            return False

        if not isinstance(config_instance.BACKUP_COUNT, int):
            print("BACKUP_COUNT must be an integer")
            return False

        # Check valid values
        if config_instance.MAX_TITLE_LENGTH <= 0:
            print("MAX_TITLE_LENGTH must be positive")
            return False

        if config_instance.BACKUP_COUNT < 0:
            print("BACKUP_COUNT must be non-negative")
            return False

        return True

    except Exception as e:
        print(f"Configuration validation error: {e}")
        return False


# Initialize configuration
def init_config():
    """Initialize configuration and create necessary directories"""
    global config

    # Validate configuration
    if not validate_config(config):
        print("Configuration validation failed, using defaults")
        config = Config()

    # Create necessary directories
    try:
        config.ensure_directories()
    except Exception as e:
        print(f"Failed to create directories: {e}")

    return config


# Export commonly used configuration values
DEFAULT_CONFIG = config
DATA_DIR = config.get_data_dir()
TODO_FILE_PATH = config.get_todo_file_path()
BACKUP_DIR = config.get_backup_dir()
EXPORT_DIR = config.get_export_dir()
