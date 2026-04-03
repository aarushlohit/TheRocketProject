import py_compile
import os
import sys
from pathlib import Path

directories = [
    r"c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\agent\core",
    r"c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\agent\nlu",
    r"c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\agent\skills",
    r"c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\agent\platform",
    r"c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket\agent\utils"
]

files_checked = []
errors_found = []

# Find all Python files
for directory in directories:
    dir_path = Path(directory)
    if dir_path.exists():
        for py_file in dir_path.rglob("*.py"):
            files_checked.append(str(py_file))
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                errors_found.append({
                    'file': str(py_file),
                    'error': str(e)
                })
    else:
        print(f"Directory not found: {directory}")

print(f"\n{'='*80}")
print(f"PYTHON SYNTAX CHECK REPORT")
print(f"{'='*80}")
print(f"\nTotal files checked: {len(files_checked)}")
print(f"Files with errors: {len(errors_found)}")

if files_checked:
    print(f"\nFiles checked:")
    for f in sorted(files_checked):
        print(f"  ✓ {f}")

if errors_found:
    print(f"\n{'='*80}")
    print(f"SYNTAX ERRORS FOUND:")
    print(f"{'='*80}")
    for error_info in errors_found:
        print(f"\n❌ {error_info['file']}")
        print(f"{error_info['error']}")
else:
    print(f"\n{'='*80}")
    print(f"✓ NO SYNTAX ERRORS FOUND!")
    print(f"{'='*80}")
