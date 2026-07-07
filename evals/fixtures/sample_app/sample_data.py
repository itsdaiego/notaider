"""
Todo Application - Sample Data Generator

This module provides functionality to generate sample todo data for testing
and demonstration purposes. It creates realistic todos with various priorities,
statuses, and tags.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from todo import TodoManager, TodoItem, Priority, TodoStatus
from utils import create_sample_todos


def generate_realistic_todos() -> List[TodoItem]:
    """Generate a comprehensive set of realistic todo items"""
    todos = []

    # Work-related todos
    work_todos = [
        {
            "title": "Prepare quarterly presentation",
            "description": "Create slides for Q4 performance review meeting with stakeholders",
            "priority": Priority.HIGH,
            "tags": ["work", "presentation", "quarterly"],
            "days_ago": 5
        },
        {
            "title": "Code review for new feature",
            "description": "Review pull request #234 for user authentication improvements",
            "priority": Priority.HIGH,
            "tags": ["work", "code-review", "urgent"],
            "days_ago": 2
        },
        {
            "title": "Update project documentation",
            "description": "Add API documentation for the new endpoints",
            "priority": Priority.MEDIUM,
            "tags": ["work", "documentation", "api"],
            "days_ago": 7
        },
        {
            "title": "Team meeting preparation",
            "description": "Prepare agenda and talking points for weekly team sync",
            "priority": Priority.MEDIUM,
            "tags": ["work", "meeting", "team"],
            "days_ago": 1
        },
        {
            "title": "Performance optimization",
            "description": "Investigate and fix database query performance issues",
            "priority": Priority.HIGH,
            "tags": ["work", "performance", "database"],
            "days_ago": 3
        }
    ]

    # Personal todos
    personal_todos = [
        {
            "title": "Schedule dentist appointment",
            "description": "Book routine cleaning and checkup",
            "priority": Priority.MEDIUM,
            "tags": ["personal", "health", "appointment"],
            "days_ago": 4
        },
        {
            "title": "Plan weekend trip",
            "description": "Research destinations and book accommodation for weekend getaway",
            "priority": Priority.LOW,
            "tags": ["personal", "travel", "weekend"],
            "days_ago": 10
        },
        {
            "title": "Learn new recipe",
            "description": "Try cooking Thai green curry from scratch",
            "priority": Priority.LOW,
            "tags": ["personal", "cooking", "learning"],
            "days_ago": 6
        },
        {
            "title": "Organize digital photos",
            "description": "Sort and backup photos from summer vacation",
            "priority": Priority.LOW,
            "tags": ["personal", "organization", "photos"],
            "days_ago": 15
        },
        {
            "title": "Call insurance company",
            "description": "Inquire about updating auto insurance policy",
            "priority": Priority.MEDIUM,
            "tags": ["personal", "insurance", "finance"],
            "days_ago": 8
        }
    ]

    # Household todos
    household_todos = [
        {
            "title": "Fix leaky faucet",
            "description": "Replace washers in kitchen sink faucet",
            "priority": Priority.HIGH,
            "tags": ["home", "maintenance", "plumbing"],
            "days_ago": 3
        },
        {
            "title": "Deep clean bathroom",
            "description": "Scrub tiles, clean grout, and organize medicine cabinet",
            "priority": Priority.MEDIUM,
            "tags": ["home", "cleaning", "bathroom"],
            "days_ago": 2
        },
        {
            "title": "Plant herbs in garden",
            "description": "Plant basil, oregano, and thyme in the herb garden",
            "priority": Priority.LOW,
            "tags": ["home", "gardening", "herbs"],
            "days_ago": 12
        },
        {
            "title": "Replace air filter",
            "description": "Change HVAC air filter - it's been 3 months",
            "priority": Priority.MEDIUM,
            "tags": ["home", "maintenance", "hvac"],
            "days_ago": 5
        }
    ]

    # Learning and development todos
    learning_todos = [
        {
            "title": "Complete Python course",
            "description": "Finish chapters 8-10 of advanced Python programming course",
            "priority": Priority.MEDIUM,
            "tags": ["learning", "programming", "python"],
            "days_ago": 9
        },
        {
            "title": "Read 'Clean Code' book",
            "description": "Continue reading Robert Martin's book on software craftsmanship",
            "priority": Priority.LOW,
            "tags": ["learning", "books", "programming"],
            "days_ago": 20
        },
        {
            "title": "Practice Spanish",
            "description": "Complete daily lesson on language learning app",
            "priority": Priority.LOW,
            "tags": ["learning", "language", "spanish"],
            "days_ago": 1
        }
    ]

    # Combine all todo categories
    all_todo_data = work_todos + personal_todos + household_todos + learning_todos

    # Create TodoItem objects
    for todo_data in all_todo_data:
        todo = TodoItem(
            title=todo_data["title"],
            description=todo_data["description"],
            priority=todo_data["priority"]
        )

        # Add tags
        for tag in todo_data["tags"]:
            todo.add_tag(tag)

        # Adjust creation date
        days_ago = todo_data["days_ago"]
        created_date = datetime.now() - timedelta(days=days_ago)
        todo.created_at = created_date
        todo.updated_at = created_date

        todos.append(todo)

    return todos


def set_realistic_statuses(todos: List[TodoItem]) -> List[TodoItem]:
    """Set realistic statuses for todos based on their age and priority"""
    now = datetime.now()

    for todo in todos:
        days_old = (now - todo.created_at).days

        # Higher probability of completion for older, high-priority todos
        if todo.priority == Priority.HIGH:
            if days_old > 5:
                # 70% chance of completion for old high-priority todos
                if hash(todo.id) % 10 < 7:
                    completion_date = todo.created_at + timedelta(days=days_old // 2)
                    todo.completed_at = completion_date
                    todo.status = TodoStatus.COMPLETED
                    todo.updated_at = completion_date
            elif days_old > 10:
                # 20% chance of cancellation for very old todos
                if hash(todo.id) % 10 < 2:
                    todo.status = TodoStatus.CANCELLED
                    todo.updated_at = todo.created_at + timedelta(days=days_old - 2)

        elif todo.priority == Priority.MEDIUM:
            if days_old > 7:
                # 50% chance of completion for old medium-priority todos
                if hash(todo.id) % 10 < 5:
                    completion_date = todo.created_at + timedelta(days=days_old // 2)
                    todo.completed_at = completion_date
                    todo.status = TodoStatus.COMPLETED
                    todo.updated_at = completion_date
            elif days_old > 15:
                # 15% chance of cancellation for very old todos
                if hash(todo.id) % 10 < 1:
                    todo.status = TodoStatus.CANCELLED
                    todo.updated_at = todo.created_at + timedelta(days=days_old - 3)

        elif todo.priority == Priority.LOW:
            if days_old > 14:
                # 30% chance of completion for old low-priority todos
                if hash(todo.id) % 10 < 3:
                    completion_date = todo.created_at + timedelta(days=days_old // 2)
                    todo.completed_at = completion_date
                    todo.status = TodoStatus.COMPLETED
                    todo.updated_at = completion_date
            elif days_old > 30:
                # 25% chance of cancellation for very old todos
                if hash(todo.id) % 10 < 2:
                    todo.status = TodoStatus.CANCELLED
                    todo.updated_at = todo.created_at + timedelta(days=days_old - 5)

    return todos


def create_sample_data_file(filename: str = "sample_todos.json") -> str:
    """Create a sample data file with realistic todos"""
    todos = generate_realistic_todos()
    todos = set_realistic_statuses(todos)

    # Convert to dictionary format
    data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_todos": len(todos),
            "description": "Sample todo data for testing and demonstration"
        },
        "todos": [todo.to_dict() for todo in todos]
    }

    # Save to file
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    return filename


def load_sample_data_into_manager(manager: TodoManager, filename: str = "sample_todos.json"):
    """Load sample data into a TodoManager instance"""
    if not os.path.exists(filename):
        create_sample_data_file(filename)

    with open(filename, 'r') as f:
        data = json.load(f)

    for todo_data in data["todos"]:
        todo = TodoItem.from_dict(todo_data)
        manager.todos.append(todo)

    manager.save_todos()


def add_todo(self, title: str, description: str = '', priority: Priority = Priority.MEDIUM) -> TodoItem:
        """Add a new todo item"""
        todo = TodoItem(title, description, priority)
        self.todos.append(todo)
        self.save_todos()

def create_scenario_files():
    """Create separate files for each demo scenario"""
    scenarios = generate_demo_scenarios()

    for scenario_name, todos in scenarios.items():
        filename = f"scenario_{scenario_name}.json"
        data = {
            "metadata": {
                "scenario": scenario_name,
                "generated_at": datetime.now().isoformat(),
                "total_todos": len(todos),
                "description": f"Sample todos for {scenario_name.replace('_', ' ')} scenario"
            },
            "todos": [todo.to_dict() for todo in todos]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)


def main():
    """Main function to generate sample data"""

    # Create main sample data file
    main_file = create_sample_data_file()
    

    # Create scenario files
    create_scenario_files()

    # Create a manager with sample data
    manager = TodoManager("sample_todos_manager.json")
    load_sample_data_into_manager(manager, main_file)

    
    

    # Print statistics
    stats = manager.get_todo_stats()
    
    
    
    
    


if __name__ == "__main__":
    main()
