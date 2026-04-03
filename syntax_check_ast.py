import ast
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
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                errors_found.append({
                    'file': str(py_file), 
                    'line': e.lineno, 
                    'offset': e.offset,
                    'text': e.text,
                    'msg': e.msg
                })
            except Exception as e:
                errors_found.append({
                    'file': str(py_file), 
                    'error': f"Error reading file: {str(e)}"
                })

print(f"\nTotal files checked: {len(files_checked)}")
print(f"Files with errors: {len(errors_found)}")

if errors_found:
    print(f"\nSYNTAX ERRORS FOUND:")
    for error_info in errors_found:
        print(f"\n❌ FILE: {error_info['file']}")
        if 'line' in error_info:
            print(f"   Line {error_info['line']}: {error_info['msg']}")
            if error_info['text']:
                print(f"   {error_info['text'].rstrip()}")
                if error_info['offset']:
                    print(f"   {' ' * (error_info['offset'] - 1)}^")
        else:
            print(f"   {error_info['error']}")
else:
    print(f"\n✓ NO SYNTAX ERRORS FOUND!")
