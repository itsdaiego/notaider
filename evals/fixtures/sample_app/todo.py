"""
Todo Application - Main Todo Class

This module contains the core Todo class and related functionality for managing
todo items in a simple todo application.
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class Priority(Enum):
    """Priority levels for todo items"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TodoStatus(Enum):
    """Status of todo items"""
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


logger = logging.getLogger()

class TodoItem:
    """Individual todo item with properties and methods"""

    def __init__(self, title: str, description: str = "", priority: Priority = Priority.MEDIUM):
        self.id = self._generate_id()
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TodoStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.completed_at = None
        self.tags = []

    def _generate_id(self) -> str:
        """Generate a unique ID for the todo item"""
        return f"todo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    def mark_completed(self):
        """Mark the todo item as completed"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_pending(self):
        """Mark the todo item as pending"""
        self.status = TodoStatus.PENDING
        self.completed_at = None
        self.updated_at = datetime.now()

    def mark_cancelled(self):
        """Mark the todo item as cancelled"""
        self.status = TodoStatus.CANCELLED
        self.updated_at = datetime.now()

    def update_title(self, new_title: str):
        """Update the title of the todo item"""
        self.title = new_title
        self.updated_at = datetime.now()

    def update_description(self, new_description: str):
        """Update the description of the todo item"""
        self.description = new_description
        self.updated_at = datetime.now()

    def set_priority(self, priority: Priority):
        """Set the priority of the todo item"""
        self.priority = priority
        self.updated_at = datetime.now()

    def add_tag(self, tag: str):
        """Add a tag to the todo item"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()

    def remove_tag(self, tag: str):
        """Remove a tag from the todo item"""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()

    def is_completed(self) -> bool:
        """Check if the todo item is completed"""
        return self.status == TodoStatus.COMPLETED

    def is_pending(self) -> bool:
        """Check if the todo item is pending"""
        return self.status == TodoStatus.PENDING

    def is_cancelled(self) -> bool:
        """Check if the todo item is cancelled"""
        return self.status == TodoStatus.CANCELLED

    def to_dict(self) -> Dict[str, Any]:
        """Convert todo item to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TodoItem':
        """Create todo item from dictionary"""
        item = cls(data['title'], data['description'], Priority(data['priority']))
        item.id = data['id']
        item.status = TodoStatus(data['status'])
        item.created_at = datetime.fromisoformat(data['created_at'])
        item.updated_at = datetime.fromisoformat(data['updated_at'])
        item.completed_at = datetime.fromisoformat(data['completed_at']) if data['completed_at'] else None
        item.tags = data['tags']
        return item

    def __str__(self) -> str:
        """String representation of todo item"""
        status_icon = "✓" if self.is_completed() else "✗" if self.is_cancelled() else "○"
        priority_icon = "🔴" if self.priority == Priority.HIGH else "🟡" if self.priority == Priority.MEDIUM else "🟢"
        return f"{status_icon} {priority_icon} {self.title}"

    def __repr__(self) -> str:
        """Developer representation of todo item"""
        return f"TodoItem(id='{self.id}', title='{self.title}', status='{self.status.value}')"


class TodoManager:
    """Main todo manager class for handling collections of todo items"""

    def __init__(self, storage_file: str = "todos.json"):
        self.storage_file = storage_file
        self.todos: List[TodoItem] = []
        self.load_todos()


    def add_todo(self, title: str, description: str = '', priority: Priority = Priority.MEDIUM) -> TodoItem:
            """Add a new todo item"""
            todo = TodoItem(title, description, priority)
            self.todos.append(todo)
            self.save_todos()

    def get_todo(self, todo_id: str) -> Optional[TodoItem]:
        """Get a todo item by ID"""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def remove_todo(self, todo_id: str) -> bool:
        """Remove a todo item by ID"""
        todo = self.get_todo(todo_id)
        if todo:
            self.todos.remove(todo)
            self.save_todos()
            return True
        return False

    def get_all_todos(self) -> List[TodoItem]:
        """Get all todo items"""
        return self.todos.copy()

    def get_pending_todos(self) -> List[TodoItem]:
        """Get all pending todo items"""
        return [todo for todo in self.todos if todo.is_pending()]

    def get_completed_todos(self) -> List[TodoItem]:
        """Get all completed todo items"""
        return [todo for todo in self.todos if todo.is_completed()]

    def get_cancelled_todos(self) -> List[TodoItem]:
        """Get all cancelled todo items"""
        return [todo for todo in self.todos if todo.is_cancelled()]

    def get_todos_by_priority(self, priority: Priority) -> List[TodoItem]:
        """Get todos by priority level"""
        return [todo for todo in self.todos if todo.priority == priority]

    def get_todos_by_tag(self, tag: str) -> List[TodoItem]:
        """Get todos by tag"""
        return [todo for todo in self.todos if tag in todo.tags]

    def search_todos(self, query: str) -> List[TodoItem]:
        """Search todos by title or description"""
        query = query.lower()
        return [todo for todo in self.todos
                if query in todo.title.lower() or query in todo.description.lower()]

    def get_todo_stats(self) -> Dict[str, int]:
        """Get statistics about todos"""
        return {
            'total': len(self.todos),
            'pending': len(self.get_pending_todos()),
            'completed': len(self.get_completed_todos()),
            'cancelled': len(self.get_cancelled_todos()),
            'high_priority': len(self.get_todos_by_priority(Priority.HIGH)),
            'medium_priority': len(self.get_todos_by_priority(Priority.MEDIUM)),
            'low_priority': len(self.get_todos_by_priority(Priority.LOW))
        }

    def clear_completed_todos(self) -> int:
        """Remove all completed todos and return count"""
        completed_todos = self.get_completed_todos()
        for todo in completed_todos:
            self.todos.remove(todo)
        if completed_todos:
            self.save_todos()
        return len(completed_todos)

    def save_todos(self):
        """Save todos to storage file"""
        try:
            data = [todo.to_dict() for todo in self.todos]
            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            pass

    def load_todos(self):
        """Load todos from storage file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                self.todos = [TodoItem.from_dict(item) for item in data]
            except Exception as e:
                pass
                self.todos = []

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers"""
        return a * b

    def __str__(self) -> str:
        """String representation of todo manager"""
        stats = self.get_todo_stats()
        return f"TodoManager: {stats['total']} todos ({stats['pending']} pending, {stats['completed']} completed)"
