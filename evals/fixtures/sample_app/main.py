#!/usr/bin/env python3
"""
Todo Application - Main Entry Point

This is the main entry point for the todo application. It provides a simple
interface to run the todo app with various options and commands.
"""

import sys
import os
from typing import List, Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo import TodoManager, TodoItem, Priority, TodoStatus
from cli import TodoCLI
from utils import create_sample_todos, TodoUtils, DateUtils
from sample_data import generate_realistic_todos, load_sample_data_into_manager


def print_welcome_message():
    """Print welcome message and basic information"""
    pass


def print_help():
    """Print help information"""
    print("Usage: python main.py [command] [options]")
    print()
    print("Commands:")
    print("  run                    - Start the CLI interface")
    print("  demo                   - Run with sample data")
    print("  create-samples         - Create sample data files")
    print("  stats                  - Show statistics")
    print("  help                   - Show this help message")
    print()
    print("Examples:")
    print("  python main.py run add 'Buy groceries' --priority high")
    print("  python main.py demo")
    print("  python main.py stats")
    print()


def run_cli_mode(args: List[str]):
    """Run the CLI interface"""
    cli = TodoCLI()
    cli.run(args)


def run_demo_mode():
    """Run in demo mode with sample data"""
    print("🎯 Starting Demo Mode...")
    print()

    # Create a demo manager
    demo_manager = TodoManager("demo_todos.json")

    # Check if demo data already exists
    if len(demo_manager.todos) == 0:
        print("📝 Creating sample todos for demo...")
        todos = generate_realistic_todos()

        # Add sample todos to manager
        for todo in todos:
            demo_manager.todos.append(todo)

        demo_manager.save_todos()
        print(f"✅ Created {len(todos)} sample todos")
        print()

    # Show statistics
    stats = demo_manager.get_todo_stats()
    print("📊 Demo Todo Statistics:")
    print(f"  Total todos: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  Cancelled: {stats['cancelled']}")
    print()

    # Show some sample todos
    print("📋 Sample Todos:")
    todos = demo_manager.get_all_todos()[:10]  # Show first 10
    for i, todo in enumerate(todos, 1):
        status_icon = "✅" if todo.is_completed() else "❌" if todo.is_cancelled() else "⏳"
        priority_icon = "🔴" if todo.priority == Priority.HIGH else "🟡" if todo.priority == Priority.MEDIUM else "🟢"
        print(f"  {i:2d}. {status_icon} {priority_icon} {todo.title}")

    if len(demo_manager.todos) > 10:
        print(f"     ... and {len(demo_manager.todos) - 10} more todos")

    print()
    print("🔧 You can now use the CLI commands:")
    print("  python main.py run list")
    print("  python main.py run add 'New todo' --priority high")
    print("  python main.py run complete 1")
    print()


def create_sample_data():
    """Create sample data files"""
    print("📁 Creating sample data files...")

    from sample_data import create_sample_data_file, create_scenario_files

    # Create main sample file
    main_file = create_sample_data_file()
    print(f"✅ Created: {main_file}")

    # Create scenario files
    create_scenario_files()

    print("📊 Sample data creation complete!")
    print()


def show_stats():
    """Show statistics for existing todos"""
    manager = TodoManager()

    if len(manager.todos) == 0:
        print("📭 No todos found. Use 'python main.py demo' to create sample data.")
        return

    stats = manager.get_todo_stats()
    todos = manager.get_all_todos()

    print("📊 Todo Statistics:")
    print(f"  Total todos: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Completed: {stats['completed']}")
    print(f"  Cancelled: {stats['cancelled']}")
    print()

    print("📈 Priority Distribution:")
    print(f"  High priority: {stats['high_priority']}")
    print(f"  Medium priority: {stats['medium_priority']}")
    print(f"  Low priority: {stats['low_priority']}")
    print()

    # Show completion rate
    completion_rate = (stats['completed'] / stats['total']) * 100 if stats['total'] > 0 else 0
    print(f"✅ Completion rate: {completion_rate:.1f}%")

    # Show recent activity
    recent_todos = TodoUtils.sort_todos(todos, 'updated_at', reverse=True)[:5]
    if recent_todos:
        print()
        print("🕐 Recent Activity:")
        for todo in recent_todos:
            relative_time = DateUtils.get_relative_time(todo.updated_at)
            print(f"  • {todo.title} - {relative_time}")

    print()


def interactive_mode():
    """Run in interactive mode"""
    print("🎮 Interactive Mode")
    print("Type 'help' for available commands or 'exit' to quit")
    print()

    cli = TodoCLI()

    while True:
        try:
            user_input = input("todo> ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("👋 Goodbye!")
                break

            if user_input.lower() == 'help':
                cli.parser.print_help()
                continue

            # Parse and execute command
            args = user_input.split()
            cli.run(args)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main entry point"""
    print_welcome_message()

    # Parse command line arguments
    args = sys.argv[1:]

    if not args:
        print("🤔 No command specified. Here are your options:")
        print()
        print_help()
        return

    command = args[0].lower()

    if command == 'help' or command == '--help' or command == '-h':
        print_help()

    elif command == 'run':
        # Run CLI with remaining arguments
        cli_args = args[1:]
        run_cli_mode(cli_args)

    elif command == 'demo':
        run_demo_mode()

    elif command == 'create-samples':
        create_sample_data()

    elif command == 'stats':
        show_stats()

    elif command == 'interactive' or command == 'i':
        interactive_mode()

    else:
        print(f"❌ Unknown command: {command}")
        print()
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
