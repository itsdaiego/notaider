"""
Todo Application - Utilities Module

This module contains utility functions and helper classes for the todo application.
It provides common functionality like date formatting, validation, and data processing.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from todo import TodoItem, Priority, TodoStatus


class DateUtils:
    """Utility class for date and time operations"""

    @staticmethod
    def format_date(date: datetime, format_type: str = 'short') -> str:
        """Format a datetime object to a readable string"""
        if format_type == 'short':
            return date.strftime('%Y-%m-%d')
        elif format_type == 'long':
            return date.strftime('%Y-%m-%d %H:%M:%S')
        elif format_type == 'relative':
            return DateUtils.get_relative_time(date)
        else:
            return date.isoformat()

    @staticmethod
    def get_relative_time(date: datetime) -> str:
        """Get relative time string (e.g., '2 days ago', 'in 3 hours')"""
        now = datetime.now()
        diff = now - date

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "just now"

    @staticmethod
    def parse_date_string(date_str: str) -> Optional[datetime]:
        """Parse various date string formats"""
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%m/%d/%Y',
            '%m/%d/%y'
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def is_overdue(date: datetime) -> bool:
        """Check if a date is overdue"""
        return date < datetime.now()


class ValidationUtils:
    """Utility class for validation operations"""

    @staticmethod
    def validate_title(title: str) -> bool:
        """Validate todo title"""
        if not title or not title.strip():
            return False
        if len(title.strip()) > 200:
            return False
        return True

    @staticmethod
    def validate_description(description: str) -> bool:
        """Validate todo description"""
        if len(description) > 1000:
            return False
        return True

    @staticmethod
    def validate_tag(tag: str) -> bool:
        """Validate tag format"""
        if not tag or not tag.strip():
            return False
        # Tags should be alphanumeric with underscores and hyphens
        return re.match(r'^[a-zA-Z0-9_-]+$', tag.strip()) is not None

    @staticmethod
    def sanitize_title(title: str) -> str:
        """Sanitize title input"""
        return title.strip()[:200]

    @staticmethod
    def sanitize_description(description: str) -> str:
        """Sanitize description input"""
        return description.strip()[:1000]

    @staticmethod
    def sanitize_tag(tag: str) -> str:
        """Sanitize tag input"""
        # Remove special characters except underscores and hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', tag.strip())
        return sanitized.lower()


class TodoUtils:
    """Utility class for todo-specific operations"""

    @staticmethod
    def filter_todos(todos: List[TodoItem], **filters) -> List[TodoItem]:
        """Filter todos based on various criteria"""
        filtered = todos.copy()

        if 'status' in filters:
            status = filters['status']
            if isinstance(status, str):
                status = TodoStatus(status)
            filtered = [t for t in filtered if t.status == status]

        if 'priority' in filters:
            priority = filters['priority']
            if isinstance(priority, str):
                priority = Priority(priority)
            filtered = [t for t in filtered if t.priority == priority]

        if 'tags' in filters:
            tags = filters['tags']
            if isinstance(tags, str):
                tags = [tags]
            filtered = [t for t in filtered if any(tag in t.tags for tag in tags)]

        if 'search' in filters:
            query = filters['search'].lower()
            filtered = [t for t in filtered
                       if query in t.title.lower() or query in t.description.lower()]

        if 'created_after' in filters:
            date = filters['created_after']
            filtered = [t for t in filtered if t.created_at >= date]

        if 'created_before' in filters:
            date = filters['created_before']
            filtered = [t for t in filtered if t.created_at <= date]

        return filtered

    @staticmethod
    def sort_todos(todos: List[TodoItem], sort_by: str = 'created_at',
                   reverse: bool = False) -> List[TodoItem]:
        """Sort todos by various criteria"""
        if sort_by == 'created_at':
            return sorted(todos, key=lambda t: t.created_at, reverse=reverse)
        elif sort_by == 'updated_at':
            return sorted(todos, key=lambda t: t.updated_at, reverse=reverse)
        elif sort_by == 'title':
            return sorted(todos, key=lambda t: t.title.lower(), reverse=reverse)
        elif sort_by == 'priority':
            # Sort by priority (high, medium, low)
            priority_order = {Priority.HIGH: 3, Priority.MEDIUM: 2, Priority.LOW: 1}
            return sorted(todos, key=lambda t: priority_order[t.priority], reverse=reverse)
        elif sort_by == 'status':
            # Sort by status (pending, completed, cancelled)
            status_order = {TodoStatus.PENDING: 1, TodoStatus.COMPLETED: 2, TodoStatus.CANCELLED: 3}
            return sorted(todos, key=lambda t: status_order[t.status], reverse=reverse)
        else:
            return todos

    @staticmethod
    def get_todo_summary(todos: List[TodoItem]) -> Dict[str, Any]:
        """Get a summary of todo statistics"""
        if not todos:
            return {
                'total': 0,
                'pending': 0,
                'completed': 0,
                'cancelled': 0,
                'completion_rate': 0.0,
                'avg_completion_time': None,
                'priority_distribution': {'high': 0, 'medium': 0, 'low': 0}
            }

        pending = [t for t in todos if t.status == TodoStatus.PENDING]
        completed = [t for t in todos if t.status == TodoStatus.COMPLETED]
        cancelled = [t for t in todos if t.status == TodoStatus.CANCELLED]

        completion_rate = len(completed) / len(todos) * 100 if todos else 0

        # Calculate average completion time
        completed_times = []
        for todo in completed:
            if todo.completed_at:
                time_diff = todo.completed_at - todo.created_at
                completed_times.append(time_diff.total_seconds())

        avg_completion_time = None
        if completed_times:
            avg_seconds = sum(completed_times) / len(completed_times)
            avg_completion_time = timedelta(seconds=avg_seconds)

        # Priority distribution
        priority_dist = {
            'high': len([t for t in todos if t.priority == Priority.HIGH]),
            'medium': len([t for t in todos if t.priority == Priority.MEDIUM]),
            'low': len([t for t in todos if t.priority == Priority.LOW])
        }

        return {
            'total': len(todos),
            'pending': len(pending),
            'completed': len(completed),
            'cancelled': len(cancelled),
            'completion_rate': completion_rate,
            'avg_completion_time': avg_completion_time,
            'priority_distribution': priority_dist
        }

    @staticmethod
    def export_todos_to_dict(todos: List[TodoItem]) -> Dict[str, Any]:
        """Export todos to a dictionary format"""
        return {
            'export_date': datetime.now().isoformat(),
            'total_todos': len(todos),
            'todos': [todo.to_dict() for todo in todos]
        }

    @staticmethod
    def import_todos_from_dict(data: Dict[str, Any]) -> List[TodoItem]:
        """Import todos from a dictionary format"""
        todos = []
        for todo_data in data.get('todos', []):
            try:
                todo = TodoItem.from_dict(todo_data)
                todos.append(todo)
            except Exception as e:
                print(f"Error importing todo: {e}")
                continue
        return todos


class ColorUtils:
    """Utility class for terminal colors (if needed)"""

    # ANSI color codes
    COLORS = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'RESET': '\033[0m'
    }

    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Add color to text"""
        if color.upper() in ColorUtils.COLORS:
            return f"{ColorUtils.COLORS[color.upper()]}{text}{ColorUtils.COLORS['RESET']}"
        return text

    @staticmethod
    def get_priority_color(priority: Priority) -> str:
        """Get color for priority level"""
        colors = {
            Priority.HIGH: 'RED',
            Priority.MEDIUM: 'YELLOW',
            Priority.LOW: 'GREEN'
        }
        return colors.get(priority, 'WHITE')

    @staticmethod
    def get_status_color(status: TodoStatus) -> str:
        """Get color for status"""
        colors = {
            TodoStatus.PENDING: 'YELLOW',
            TodoStatus.COMPLETED: 'GREEN',
            TodoStatus.CANCELLED: 'RED'
        }
        return colors.get(status, 'WHITE')


class FileUtils:
    """Utility class for file operations"""

    @staticmethod
    def ensure_directory_exists(filepath: str):
        """Ensure the directory for a file exists"""
        import os
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    @staticmethod
    def backup_file(filepath: str, backup_suffix: str = '.backup'):
        """Create a backup of a file"""
        import shutil
        import os

        if os.path.exists(filepath):
            backup_path = filepath + backup_suffix
            shutil.copy2(filepath, backup_path)
            return backup_path
        return None

    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes"""
        import os
        try:
            return os.path.getsize(filepath)
        except OSError:
            return 0


def create_sample_todos() -> List[TodoItem]:
    """Create sample todos for testing purposes"""
    from todo import TodoItem, Priority

    todos = []

    # Sample todos with different priorities and statuses
    sample_data = [
        ("Buy groceries", "Get milk, bread, eggs, and fruits", Priority.HIGH, ["shopping", "food"]),
        ("Complete project report", "Finish the quarterly analysis report", Priority.HIGH, ["work", "urgent"]),
        ("Call mom", "Haven't talked to her in a week", Priority.MEDIUM, ["family", "personal"]),
        ("Exercise", "Go for a 30-minute run", Priority.MEDIUM, ["health", "fitness"]),
        ("Read a book", "Finish reading 'The Art of War'", Priority.LOW, ["personal", "learning"]),
        ("Clean the house", "Vacuum and dust all rooms", Priority.LOW, ["chores", "home"]),
        ("Plan vacation", "Research destinations and book flights", Priority.MEDIUM, ["travel", "personal"]),
        ("Update resume", "Add recent projects and skills", Priority.HIGH, ["career", "work"]),
        ("Learn Python", "Complete online Python course", Priority.MEDIUM, ["learning", "programming"]),
        ("Organize photos", "Sort and backup photos from last year", Priority.LOW, ["personal", "organization"])
    ]

    for title, description, priority, tags in sample_data:
        todo = TodoItem(title, description, priority)
        for tag in tags:
            todo.add_tag(tag)
        todos.append(todo)

    # Mark some as completed
    if len(todos) > 2:
        todos[0].mark_completed()  # Buy groceries
        todos[4].mark_completed()  # Read a book

    # Mark one as cancelled
    if len(todos) > 5:
        todos[5].mark_cancelled()  # Clean the house

    return todos


def generate_todo_id() -> str:
    """Generate a unique todo ID"""
    import uuid
    return f"todo_{uuid.uuid4().hex[:8]}"


def parse_priority(priority_str: str) -> Priority:
    """Parse priority string to Priority enum"""
    priority_map = {
        'h': Priority.HIGH,
        'high': Priority.HIGH,
        'm': Priority.MEDIUM,
        'medium': Priority.MEDIUM,
        'l': Priority.LOW,
        'low': Priority.LOW
    }
    return priority_map.get(priority_str.lower(), Priority.MEDIUM)


def parse_status(status_str: str) -> TodoStatus:
    """Parse status string to TodoStatus enum"""
    status_map = {
        'p': TodoStatus.PENDING,
        'pending': TodoStatus.PENDING,
        'c': TodoStatus.COMPLETED,
        'completed': TodoStatus.COMPLETED,
        'done': TodoStatus.COMPLETED,
        'cancelled': TodoStatus.CANCELLED,
        'canceled': TodoStatus.CANCELLED
    }
    return status_map.get(status_str.lower(), TodoStatus.PENDING)
