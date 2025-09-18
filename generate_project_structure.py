import os
import fnmatch

def parse_gitignore(gitignore_path):
    """Parses a .gitignore file and returns a list of patterns."""
    patterns = []
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def is_ignored(path, patterns, base_dir):
    """Checks if a path should be ignored based on .gitignore patterns."""
    relative_path = os.path.relpath(path, base_dir).replace('\\', '/')
    
    for pattern in patterns:
        # Handle directory-only patterns
        if pattern.endswith('/'):
            if os.path.isdir(path) and fnmatch.fnmatch(relative_path + '/', pattern):
                return True
            if fnmatch.fnmatch(relative_path, pattern.rstrip('/')):
                 if os.path.isdir(path):
                    return True
        # Handle general patterns
        elif fnmatch.fnmatch(relative_path, pattern):
            return True
        elif fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False

def generate_tree_structure(startpath, gitignore_patterns, output_file, indent=""):
    """Generates a tree-like structure of the project and writes it to a file."""
    if startpath == ".":
        output_file.write(".\n")

    try:
        entries = sorted(os.listdir(startpath))
        files = [e for e in entries if os.path.isfile(os.path.join(startpath, e))]
        dirs = [e for e in entries if os.path.isdir(os.path.join(startpath, e))]

        all_entries = dirs + files
        
        for i, entry in enumerate(all_entries):
            full_path = os.path.join(startpath, entry)
            if is_ignored(full_path, gitignore_patterns, "."):
                continue

            connector = "├── " if i < len(all_entries) - 1 else "└── "
            output_file.write(f"{indent}{connector}{entry}\n")

            if os.path.isdir(full_path):
                new_indent = indent + ("│   " if i < len(all_entries) - 1 else "    ")
                generate_tree_structure(full_path, gitignore_patterns, output_file, new_indent)
    except OSError:
        pass

if __name__ == "__main__":
    project_root = "."
    gitignore_path = os.path.join(project_root, ".gitignore")
    output_filename = "project_structure.txt"

    gitignore_patterns = parse_gitignore(gitignore_path)

    with open(output_filename, "w", encoding="utf-8") as f:
        generate_tree_structure(project_root, gitignore_patterns, f, "")

    print(f"Project structure written to {output_filename}")