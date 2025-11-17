#!/usr/bin/env python
"""
Code Validation Script
Validates Python code for syntax errors, imports, and common issues
"""
import ast
import sys
import os
from pathlib import Path
from typing import List, Tuple, Dict
import importlib.util


class CodeValidator:
    """Validates Python code files"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []

    def validate_syntax(self, file_path: Path) -> bool:
        """Check if file has valid Python syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            ast.parse(code)
            return True
        except SyntaxError as e:
            self.errors.append({
                'file': str(file_path),
                'type': 'SyntaxError',
                'line': e.lineno,
                'message': str(e)
            })
            return False
        except Exception as e:
            self.errors.append({
                'file': str(file_path),
                'type': 'ParseError',
                'message': str(e)
            })
            return False

    def check_imports(self, file_path: Path) -> bool:
        """Check if all imports can be resolved"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if not self._can_import(module_name):
                            self.warnings.append({
                                'file': str(file_path),
                                'type': 'ImportWarning',
                                'line': node.lineno,
                                'message': f"Cannot import '{module_name}'"
                            })

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if not self._can_import(node.module):
                            self.warnings.append({
                                'file': str(file_path),
                                'type': 'ImportWarning',
                                'line': node.lineno,
                                'message': f"Cannot import from '{node.module}'"
                            })

            return True
        except Exception as e:
            return True  # Already caught in validate_syntax

    def _can_import(self, module_name: str) -> bool:
        """Check if a module can be imported"""
        # Skip checking for local relative imports
        if module_name.startswith('.'):
            return True

        # Try to find the module spec
        try:
            spec = importlib.util.find_spec(module_name.split('.')[0])
            return spec is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def check_file(self, file_path: Path):
        """Run all checks on a file"""
        if file_path.name.startswith('_') and file_path.name != '__init__.py':
            return  # Skip private files

        print(f"Checking {file_path}...")
        self.validate_syntax(file_path)
        self.check_imports(file_path)

    def validate_directory(self, directory: Path = None):
        """Validate all Python files in directory"""
        if directory is None:
            directory = self.base_path

        python_files = list(directory.rglob("*.py"))

        # Exclude certain directories
        exclude_dirs = {'__pycache__', 'venv', '.venv', 'node_modules', '.git'}
        python_files = [
            f for f in python_files
            if not any(part in exclude_dirs for part in f.parts)
        ]

        print(f"Found {len(python_files)} Python files to validate\n")

        for file_path in python_files:
            self.check_file(file_path)

    def print_report(self):
        """Print validation report"""
        print("\n" + "="*80)
        print("VALIDATION REPORT")
        print("="*80 + "\n")

        if self.errors:
            print(f"❌ ERRORS: {len(self.errors)}")
            print("-" * 80)
            for error in self.errors:
                print(f"\nFile: {error['file']}")
                print(f"Type: {error['type']}")
                if 'line' in error:
                    print(f"Line: {error['line']}")
                print(f"Message: {error['message']}")
        else:
            print("✅ No syntax errors found")

        print("\n")

        if self.warnings:
            print(f"⚠️  WARNINGS: {len(self.warnings)}")
            print("-" * 80)
            for warning in self.warnings:
                print(f"\nFile: {warning['file']}")
                print(f"Type: {warning['type']}")
                if 'line' in warning:
                    print(f"Line: {warning['line']}")
                print(f"Message: {warning['message']}")
        else:
            print("✅ No import warnings")

        print("\n" + "="*80)

        if self.errors:
            print("❌ VALIDATION FAILED")
            return False
        else:
            print("✅ VALIDATION PASSED")
            return True


def main():
    """Main validation function"""
    # Get backend directory
    backend_dir = Path(__file__).parent.parent

    print(f"Validating code in: {backend_dir}\n")

    validator = CodeValidator(backend_dir)
    validator.validate_directory()

    success = validator.print_report()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
