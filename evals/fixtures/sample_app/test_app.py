#!/usr/bin/env python3
"""
Todo Application - Test Script

This script tests the basic functionality of the todo application to ensure
everything is working correctly. It creates sample todos, performs operations,
and verifies the results.
"""

import os
import sys
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo import TodoManager, TodoItem, Priority, TodoStatus
from utils import ValidationUtils, TodoUtils, DateUtils, create_sample_todos
from config import Config


def test_todo_item_creation():
    """Test creating and manipulating TodoItem objects"""
    print("Testing TodoItem creation...")

    # Create a basic todo
    todo = TodoItem("Test todo", "This is a test description", Priority.HIGH)

    assert todo.title == "Test todo"
    assert todo.description == "This is a test description"
    assert todo.priority == Priority.HIGH
    assert todo.status == TodoStatus.PENDING
    assert not todo.is_completed()
    assert todo.is_pending()

    # Test marking as completed
    todo.mark_completed()
    assert todo.is_completed()
    assert todo.completed_at is not None

    # Test tags
    todo.add_tag("test")
    todo.add_tag("sample")
    assert "test" in todo.tags
    assert "sample" in todo.tags

    todo.remove_tag("test")
    assert "test" not in todo.tags
    assert "sample" in todo.tags

    print("✅ TodoItem creation tests passed")


def test_todo_manager():
    """Test TodoManager functionality"""
    print("Testing TodoManager...")

    # Create a temporary manager
    test_file = "test_todos.json"
    manager = TodoManager(test_file)

    # Add some todos
    todo1 = manager.add_todo("Task 1", "First task", Priority.HIGH)
    todo2 = manager.add_todo("Task 2", "Second task", Priority.MEDIUM)
    todo3 = manager.add_todo("Task 3", "Third task", Priority.LOW)

    # Test getting todos
    assert len(manager.get_all_todos()) == 3
    assert len(manager.get_pending_todos()) == 3
    assert len(manager.get_completed_todos()) == 0

    # Test completing a todo
    todo1.mark_completed()
    manager.save_todos()

    assert len(manager.get_pending_todos()) == 2
    assert len(manager.get_completed_todos()) == 1

    # Test search
    results = manager.search_todos("Task 1")
    assert len(results) == 1
    assert results[0].title == "Task 1"

    # Test stats
    stats = manager.get_todo_stats()
    assert stats['total'] == 3
    assert stats['pending'] == 2
    assert stats['completed'] == 1

    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

    print("✅ TodoManager tests passed")


def test_validation_utils():
    """Test validation utilities"""
    print("Testing ValidationUtils...")

    # Test title validation
    assert ValidationUtils.validate_title("Valid title")
    assert not ValidationUtils.validate_title("")
    assert not ValidationUtils.validate_title("   ")
    assert not ValidationUtils.validate_title("a" * 201)  # Too long

    # Test tag validation
    assert ValidationUtils.validate_tag("valid_tag")
    assert ValidationUtils.validate_tag("valid-tag")
    assert ValidationUtils.validate_tag("validtag123")
    assert not ValidationUtils.validate_tag("invalid tag")  # Space
    assert not ValidationUtils.validate_tag("invalid@tag")  # Special char

    # Test sanitization
    assert ValidationUtils.sanitize_title("  Valid title  ") == "Valid title"
    assert ValidationUtils.sanitize_tag("Valid-Tag") == "valid-tag"

    print("✅ ValidationUtils tests passed")


def test_todo_utils():
    """Test todo utility functions"""
    print("Testing TodoUtils...")

    # Create sample todos
    todos = create_sample_todos()

    # Test filtering
    high_priority = TodoUtils.filter_todos(todos, priority=Priority.HIGH)
    assert all(todo.priority == Priority.HIGH for todo in high_priority)

    completed = TodoUtils.filter_todos(todos, status=TodoStatus.COMPLETED)
    assert all(todo.is_completed() for todo in completed)

    # Test sorting
    sorted_by_title = TodoUtils.sort_todos(todos, 'title')
    titles = [todo.title for todo in sorted_by_title]
    assert titles == sorted(titles)

    # Test summary
    summary = TodoUtils.get_todo_summary(todos)
    assert 'total' in summary
    assert 'pending' in summary
    assert 'completed' in summary
    assert summary['total'] == len(todos)

    print("✅ TodoUtils tests passed")


def test_date_utils():
    """Test date utility functions"""
    print("Testing DateUtils...")

    now = datetime.now()

    # Test date formatting
    formatted = DateUtils.format_date(now, 'short')
    assert len(formatted) == 10  # YYYY-MM-DD format

    formatted_long = DateUtils.format_date(now, 'long')
    assert len(formatted_long) > 10  # Includes time

    # Test relative time
    past_time = datetime.now()
    relative = DateUtils.get_relative_time(past_time)
    assert "now" in relative.lower() or "ago" in relative.lower()

    print("✅ DateUtils tests passed")


def test_config():
    """Test configuration system"""
    print("Testing Config...")

    config = Config()

    # Test basic properties
    assert hasattr(config, 'APP_NAME')
    assert hasattr(config, 'APP_VERSION')
    assert hasattr(config, 'DEFAULT_TODO_FILE')

    # Test methods
    data_dir = config.get_data_dir()
    assert isinstance(data_dir, str)
    assert len(data_dir) > 0

    todo_path = config.get_todo_file_path()
    assert isinstance(todo_path, str)
    assert config.DEFAULT_TODO_FILE in todo_path

    # Test config dict
    config_dict = config.get_config_dict()
    assert isinstance(config_dict, dict)
    assert 'app_name' in config_dict

    print("✅ Config tests passed")


def test_serialization():
    """Test JSON serialization/deserialization"""
    print("Testing serialization...")

    # Create a todo
    original = TodoItem("Test serialization", "Test description", Priority.HIGH)
    original.add_tag("test")
    original.mark_completed()

    # Convert to dict
    todo_dict = original.to_dict()
    assert isinstance(todo_dict, dict)
    assert todo_dict['title'] == "Test serialization"
    assert todo_dict['priority'] == "high"
    assert todo_dict['status'] == "completed"
    assert "test" in todo_dict['tags']

    # Convert back to TodoItem
    restored = TodoItem.from_dict(todo_dict)
    assert restored.title == original.title
    assert restored.description == original.description
    assert restored.priority == original.priority
    assert restored.status == original.status
    assert restored.tags == original.tags

    print("✅ Serialization tests passed")


def test_file_operations():
    """Test file operations"""
    print("Testing file operations...")

    test_file = "test_file_ops.json"

    # Create manager and add data
    manager = TodoManager(test_file)
    manager.add_todo("File test 1", "Test description", Priority.HIGH)
    manager.add_todo("File test 2", "Test description", Priority.LOW)

    # Verify file was created
    assert os.path.exists(test_file)

    # Load data in new manager
    new_manager = TodoManager(test_file)
    assert len(new_manager.todos) == 2

    # Verify data integrity
    titles = [todo.title for todo in new_manager.todos]
    assert "File test 1" in titles
    assert "File test 2" in titles

    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

    print("✅ File operations tests passed")


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("Testing edge cases...")

    # Test empty manager
    empty_manager = TodoManager("empty_test.json")
    assert len(empty_manager.todos) == 0
    assert len(empty_manager.get_pending_todos()) == 0

    stats = empty_manager.get_todo_stats()
    assert stats['total'] == 0

    # Test invalid operations
    todo = TodoItem("Test", "Test", Priority.MEDIUM)

    # Test duplicate tag addition
    todo.add_tag("test")
    todo.add_tag("test")  # Should not add duplicate
    assert todo.tags.count("test") == 1

    # Test removing non-existent tag
    todo.remove_tag("nonexistent")  # Should not raise error

    # Test marking completed multiple times
    todo.mark_completed()
    first_completion = todo.completed_at
    todo.mark_completed()
    second_completion = todo.completed_at
    # Should update the completion time
    assert second_completion >= first_completion

    # Clean up
    if os.path.exists("empty_test.json"):
        os.remove("empty_test.json")

    print("✅ Edge cases tests passed")


def run_all_tests():
    """Run all tests"""
    print("🧪 Running Todo Application Tests")
    print("=" * 50)

    try:
        test_todo_item_creation()
        test_todo_manager()
        test_validation_utils()
        test_todo_utils()
        test_date_utils()
        test_config()
        test_serialization()
        test_file_operations()
        test_edge_cases()

        print("\n" + "=" * 50)
        print("🎉 All tests passed successfully!")
        print("✅ Todo application is working correctly")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def add_todo(self, title: str, description: str = '', priority: Priority = Priority.MEDIUM) -> TodoItem:
        """Add a new todo item"""
        todo = TodoItem(title, description, priority)
        self.todos.append(todo)
        self.save_todos()
        print(f"Added todo: {title}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_functionality()
    else:
        run_all_tests()
        demo_functionality()
