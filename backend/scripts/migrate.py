#!/usr/bin/env python
"""
Database Migration Management Script
Simplified wrapper around Alembic commands
"""
import sys
import os
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def run_command(cmd: list):
    """Run shell command"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def migrate_up():
    """Run all pending migrations"""
    print("🔄 Running database migrations...")
    return run_command(['alembic', 'upgrade', 'head'])


def migrate_down(steps: int = 1):
    """Rollback migrations"""
    print(f"⏪ Rolling back {steps} migration(s)...")
    return run_command(['alembic', 'downgrade', f'-{steps}'])


def create_migration(message: str):
    """Create a new migration"""
    print(f"📝 Creating migration: {message}")
    return run_command(['alembic', 'revision', '--autogenerate', '-m', message])


def show_current():
    """Show current migration version"""
    print("📍 Current migration version:")
    return run_command(['alembic', 'current'])


def show_history():
    """Show migration history"""
    print("📜 Migration history:")
    return run_command(['alembic', 'history'])


def reset_database():
    """Reset database to initial state"""
    confirm = input("⚠️  This will RESET the entire database. Are you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        print("🗑️  Resetting database...")
        run_command(['alembic', 'downgrade', 'base'])
        print("✅ Database reset complete. Run 'migrate up' to recreate tables.")
        return 0
    else:
        print("❌ Reset cancelled")
        return 1


def main():
    """Main CLI"""
    if len(sys.argv) < 2:
        print("""
MindShift Database Migration Tool

Usage:
    python migrate.py <command> [args]

Commands:
    up              - Run all pending migrations
    down [N]        - Rollback N migrations (default: 1)
    create <msg>    - Create a new migration
    current         - Show current migration version
    history         - Show migration history
    reset           - Reset database (WARNING: deletes all data)

Examples:
    python migrate.py up
    python migrate.py down 2
    python migrate.py create "add user preferences"
    python migrate.py current
        """)
        return 1

    command = sys.argv[1]

    if command == 'up':
        return migrate_up()

    elif command == 'down':
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        return migrate_down(steps)

    elif command == 'create':
        if len(sys.argv) < 3:
            print("❌ Error: Migration message required")
            print("Usage: python migrate.py create <message>")
            return 1
        message = ' '.join(sys.argv[2:])
        return create_migration(message)

    elif command == 'current':
        return show_current()

    elif command == 'history':
        return show_history()

    elif command == 'reset':
        return reset_database()

    else:
        print(f"❌ Unknown command: {command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
