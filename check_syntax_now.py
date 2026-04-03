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

for directory in directories:
    dir_path = Path(directory)
    if dir_path.exists():
        for py_file in sorted(dir_path.rglob("*.py")):
            files_checked.append(str(py_file))
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                errors_found.append({'file': str(py_file), 'error': str(e)})

print(f"\nTotal files checked: {len(files_checked)}")
print(f"Files with errors: {len(errors_found)}")

if errors_found:
    print(f"\nSYNTAX ERRORS FOUND:")
    for error_info in errors_found:
        print(f"\n❌ {error_info['file']}")
        print(error_info['error'])
else:
    print(f"\n✓ NO SYNTAX ERRORS FOUND!")
