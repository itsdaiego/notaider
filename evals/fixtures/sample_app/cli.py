"""
Todo Application - Command Line Interface

This module provides a command-line interface for interacting with the todo application.
It supports various commands for managing todos, viewing lists, and performing operations.
"""

import argparse
import sys
from typing import List, Optional
from todo import TodoManager, TodoItem, Priority, TodoStatus


class TodoCLI:
    """Command-line interface for the todo application"""

    def __init__(self):
        self.manager = TodoManager()
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser for the CLI"""
        parser = argparse.ArgumentParser(
            description="Simple Todo Application",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python cli.py add "Buy groceries" --priority high
  python cli.py list
  python cli.py complete 1
  python cli.py search "grocery"
  python cli.py stats
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Add command
        add_parser = subparsers.add_parser('add', help='Add a new todo')
        add_parser.add_argument('title', help='Title of the todo')
        add_parser.add_argument('--description', '-d', default='', help='Description of the todo')
        add_parser.add_argument('--priority', '-p', choices=['low', 'medium', 'high'],
                               default='medium', help='Priority level')

        # List command
        list_parser = subparsers.add_parser('list', help='List todos')
        list_parser.add_argument('--status', choices=['pending', 'completed', 'cancelled'],
                                help='Filter by status')
        list_parser.add_argument('--priority', choices=['low', 'medium', 'high'],
                                help='Filter by priority')
        list_parser.add_argument('--tag', help='Filter by tag')

        # Complete command
        complete_parser = subparsers.add_parser('complete', help='Mark todo as completed')
        complete_parser.add_argument('id', help='Todo ID or index')

        # Cancel command
        cancel_parser = subparsers.add_parser('cancel', help='Mark todo as cancelled')
        cancel_parser.add_argument('id', help='Todo ID or index')

        # Uncomplete command
        uncomplete_parser = subparsers.add_parser('uncomplete', help='Mark todo as pending')
        uncomplete_parser.add_argument('id', help='Todo ID or index')

        # Remove command
        remove_parser = subparsers.add_parser('remove', help='Remove a todo')
        remove_parser.add_argument('id', help='Todo ID or index')

        # Edit command
        edit_parser = subparsers.add_parser('edit', help='Edit a todo')
        edit_parser.add_argument('id', help='Todo ID or index')
        edit_parser.add_argument('--title', help='New title')
        edit_parser.add_argument('--description', help='New description')
        edit_parser.add_argument('--priority', choices=['low', 'medium', 'high'],
                                help='New priority')

        # Tag commands
        tag_parser = subparsers.add_parser('tag', help='Add tag to todo')
        tag_parser.add_argument('id', help='Todo ID or index')
        tag_parser.add_argument('tag', help='Tag to add')

        untag_parser = subparsers.add_parser('untag', help='Remove tag from todo')
        untag_parser.add_argument('id', help='Todo ID or index')
        untag_parser.add_argument('tag', help='Tag to remove')

        # Search command
        search_parser = subparsers.add_parser('search', help='Search todos')
        search_parser.add_argument('query', help='Search query')

        # Stats command
        subparsers.add_parser('stats', help='Show todo statistics')

        # Clear command
        subparsers.add_parser('clear', help='Clear completed todos')

        return parser

    def _get_todo_by_id_or_index(self, identifier: str) -> Optional[TodoItem]:
        """Get a todo by ID or index"""
        # Try to get by ID first
        todo = self.manager.get_todo(identifier)
        if todo:
            return todo

        # Try to get by index
        try:
            index = int(identifier) - 1  # Convert to 0-based index
            todos = self.manager.get_all_todos()
            if 0 <= index < len(todos):
                return todos[index]
        except ValueError:
            pass

        return None

    def _print_todo_list(self, todos: List[TodoItem], show_index: bool = True):
        """Print a formatted list of todos"""
        if not todos:
            print("No todos found.")
            return

        for i, todo in enumerate(todos, 1):
            index_str = f"{i:2d}. " if show_index else ""
            priority_color = self._get_priority_color(todo.priority)
            status_str = f"[{todo.status.value.upper()}]"

            print(f"{index_str}{todo} {status_str}")
            if todo.description:
                print(f"     Description: {todo.description}")
            if todo.tags:
                print(f"     Tags: {', '.join(todo.tags)}")
            if todo.completed_at:
                print(f"     Completed: {todo.completed_at.strftime('%Y-%m-%d %H:%M')}")
            print()

    def _get_priority_color(self, priority: Priority) -> str:
        """Get color code for priority (placeholder for future color support)"""
        colors = {
            Priority.HIGH: "RED",
            Priority.MEDIUM: "YELLOW",
            Priority.LOW: "GREEN"
        }
        return colors.get(priority, "")

    def run(self, args: Optional[List[str]] = None):
        """Run the CLI with given arguments"""
        parsed_args = self.parser.parse_args(args)

        if not parsed_args.command:
            self.parser.print_help()
            return

        try:
            if parsed_args.command == 'add':
                self.cmd_add(parsed_args)
            elif parsed_args.command == 'list':
                self.cmd_list(parsed_args)
            elif parsed_args.command == 'complete':
                self.cmd_complete(parsed_args)
            elif parsed_args.command == 'cancel':
                self.cmd_cancel(parsed_args)
            elif parsed_args.command == 'uncomplete':
                self.cmd_uncomplete(parsed_args)
            elif parsed_args.command == 'remove':
                self.cmd_remove(parsed_args)
            elif parsed_args.command == 'edit':
                self.cmd_edit(parsed_args)
            elif parsed_args.command == 'tag':
                self.cmd_tag(parsed_args)
            elif parsed_args.command == 'untag':
                self.cmd_untag(parsed_args)
            elif parsed_args.command == 'search':
                self.cmd_search(parsed_args)
            elif parsed_args.command == 'stats':
                self.cmd_stats(parsed_args)
            elif parsed_args.command == 'clear':
                self.cmd_clear(parsed_args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    def cmd_add(self, args):
        """Add a new todo"""
        priority = Priority(args.priority)
        todo = self.manager.add_todo(args.title, args.description, priority)
        print(f"Added todo: {todo}")

    def cmd_list(self, args):
        """List todos with optional filtering"""
        todos = self.manager.get_all_todos()

        if args.status:
            status = TodoStatus(args.status)
            todos = [t for t in todos if t.status == status]

        if args.priority:
            priority = Priority(args.priority)
            todos = [t for t in todos if t.priority == priority]

        if args.tag:
            todos = [t for t in todos if args.tag in t.tags]

        self._print_todo_list(todos)

    def cmd_complete(self, args):
        """Mark a todo as completed"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        todo.mark_completed()
        self.manager.save_todos()
        print(f"Completed todo: {todo}")

    def cmd_cancel(self, args):
        """Mark a todo as cancelled"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        todo.mark_cancelled()
        self.manager.save_todos()
        print(f"Cancelled todo: {todo}")

    def cmd_uncomplete(self, args):
        """Mark a todo as pending"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        todo.mark_pending()
        self.manager.save_todos()
        print(f"Marked as pending: {todo}")

    def cmd_remove(self, args):
        """Remove a todo"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        if self.manager.remove_todo(todo.id):
            print(f"Removed todo: {todo}")
        else:
            print(f"Failed to remove todo: {args.id}")

    def cmd_edit(self, args):
        """Edit a todo"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        if args.title:
            todo.update_title(args.title)
        if args.description:
            todo.update_description(args.description)
        if args.priority:
            todo.set_priority(Priority(args.priority))

        self.manager.save_todos()
        print(f"Updated todo: {todo}")

    def cmd_tag(self, args):
        """Add a tag to a todo"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        todo.add_tag(args.tag)
        self.manager.save_todos()
        print(f"Added tag '{args.tag}' to: {todo}")

    def cmd_untag(self, args):
        """Remove a tag from a todo"""
        todo = self._get_todo_by_id_or_index(args.id)
        if not todo:
            print(f"Todo not found: {args.id}")
            return

        todo.remove_tag(args.tag)
        self.manager.save_todos()
        print(f"Removed tag '{args.tag}' from: {todo}")

    def cmd_search(self, args):
        """Search for todos"""
        todos = self.manager.search_todos(args.query)
        print(f"Search results for '{args.query}':")
        self._print_todo_list(todos)

    def cmd_stats(self, args):
        """Show todo statistics"""
        stats = self.manager.get_todo_stats()
        print("Todo Statistics:")
        print(f"  Total todos: {stats['total']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Cancelled: {stats['cancelled']}")
        print(f"  High priority: {stats['high_priority']}")
        print(f"  Medium priority: {stats['medium_priority']}")
        print(f"  Low priority: {stats['low_priority']}")

    def cmd_clear(self, args):
        """Clear completed todos"""
        count = self.manager.clear_completed_todos()
        print(f"Cleared {count} completed todos.")


def main():
    """Main entry point for the CLI"""
    cli = TodoCLI()
    cli.run()


if __name__ == '__main__':
    main()
