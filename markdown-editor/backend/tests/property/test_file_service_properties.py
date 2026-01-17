"""
Property-based tests for FileService

**Feature: markdown-editor, Property 1: Directory Scanning Returns Only Markdown Files**
**Feature: markdown-editor, Property 2: Hidden Files Exclusion**
**Feature: markdown-editor, Property 3: File Content Round-Trip**
**Feature: markdown-editor, Property 14: File Rename Preserves Content**
"""
import os
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from app.services.file_service import FileService


# Windows reserved device names to avoid
WINDOWS_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                    'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
                    'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}

# Strategy for valid file names (ASCII only to avoid encoding issues on Windows)
valid_filename_chars = st.characters(
    whitelist_categories=(),
    whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789_-'
)

valid_filename = st.text(
    alphabet=valid_filename_chars,
    min_size=1,
    max_size=20
).filter(lambda x: x.upper() not in WINDOWS_RESERVED and len(x) > 0)

# Strategy for file extensions
file_extensions = st.sampled_from(['.md', '.markdown', '.txt', '.py', '.js', '.json', '.html'])

# Strategy for file content (ASCII only to avoid encoding issues)
file_content = st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n\t.,!?-_'
    ),
    min_size=0,
    max_size=500
)


def collect_all_files(node, files=None):
    """Recursively collect all file nodes from a tree"""
    if files is None:
        files = []
    
    if node.type == 'file':
        files.append(node)
    elif node.children:
        for child in node.children:
            collect_all_files(child, files)
    
    return files


@given(
    filenames=st.lists(valid_filename, min_size=1, max_size=10, unique=True),
    extensions=st.lists(file_extensions, min_size=1, max_size=10)
)
@settings(max_examples=100)
def test_directory_scanning_returns_only_markdown_files(filenames, extensions):
    """
    **Feature: markdown-editor, Property 1: Directory Scanning Returns Only Markdown Files**
    
    For any directory structure scanned by the FileService, all returned file nodes
    SHALL have extensions .md or .markdown, and no files with other extensions
    SHALL be included in the result.
    
    **Validates: Requirements 1.1**
    """
    with tempfile.TemporaryDirectory() as root:
        # Create files with various extensions
        created_files = []
        for i, (name, ext) in enumerate(zip(filenames, extensions)):
            # Cycle through extensions if we have more names than extensions
            actual_ext = extensions[i % len(extensions)]
            filename = f"{name}{actual_ext}"
            filepath = Path(root) / filename
            filepath.write_text(f"Content of {filename}")
            created_files.append((filename, actual_ext))
        
        # Scan directory
        service = FileService(root)
        tree = service.get_directory_tree()
        
        # Collect all files from tree
        files = collect_all_files(tree)
        
        # Verify all returned files are markdown
        for file_node in files:
            assert file_node.name.lower().endswith('.md') or file_node.name.lower().endswith('.markdown'), \
                f"Non-markdown file found in tree: {file_node.name}"
        
        # Verify all markdown files are included
        markdown_files = [f for f, ext in created_files if ext in ['.md', '.markdown']]
        found_files = [f.name for f in files]
        
        for md_file in markdown_files:
            assert md_file in found_files, f"Markdown file missing from tree: {md_file}"


@given(
    visible_names=st.lists(valid_filename, min_size=1, max_size=5, unique=True),
    hidden_names=st.lists(valid_filename, min_size=1, max_size=5, unique=True)
)
@settings(max_examples=100)
def test_hidden_files_excluded(visible_names, hidden_names):
    """
    **Feature: markdown-editor, Property 2: Hidden Files Exclusion**
    
    For any directory structure containing hidden files (names starting with '.'),
    the Directory_Tree SHALL exclude all hidden files and directories from the
    returned tree structure.
    
    **Validates: Requirements 1.4**
    """
    # Ensure no overlap between visible and hidden names
    assume(not set(visible_names) & set(hidden_names))
    
    with tempfile.TemporaryDirectory() as root:
        # Create visible markdown files
        for name in visible_names:
            filepath = Path(root) / f"{name}.md"
            filepath.write_text(f"Content of {name}")
        
        # Create hidden markdown files
        for name in hidden_names:
            filepath = Path(root) / f".{name}.md"
            filepath.write_text(f"Hidden content of {name}")
        
        # Create a hidden directory with markdown files
        hidden_dir = Path(root) / ".hidden_dir"
        hidden_dir.mkdir()
        (hidden_dir / "secret.md").write_text("Secret content")
        
        # Scan directory
        service = FileService(root)
        tree = service.get_directory_tree()
        
        # Collect all files from tree
        files = collect_all_files(tree)
        
        # Verify no hidden files are included
        for file_node in files:
            assert not file_node.name.startswith('.'), \
                f"Hidden file found in tree: {file_node.name}"
            assert '.hidden_dir' not in file_node.path, \
                f"File from hidden directory found: {file_node.path}"
        
        # Verify visible files are included
        for name in visible_names:
            expected_name = f"{name}.md"
            assert any(f.name == expected_name for f in files), \
                f"Visible file missing from tree: {expected_name}"


@given(
    filename=valid_filename,
    content=file_content
)
@settings(max_examples=100)
def test_file_content_round_trip(filename, content):
    """
    **Feature: markdown-editor, Property 3: File Content Round-Trip**
    
    For any valid file path and content string, saving the content via FileService
    and then reading it back SHALL return content identical to the original.
    
    **Validates: Requirements 2.3**
    """
    with tempfile.TemporaryDirectory() as root:
        # Create initial file
        filepath = f"{filename}.md"
        full_path = Path(root) / filepath
        full_path.write_text("Initial content")
        
        service = FileService(root)
        
        # Save new content
        result = service.save_file(filepath, content)
        assert result.success, f"Save failed: {result.message}"
        
        # Read content back
        file_content = service.read_file(filepath)
        
        # Verify round-trip
        assert file_content.content == content, \
            f"Content mismatch after round-trip. Expected: {repr(content)}, Got: {repr(file_content.content)}"


@given(
    old_name=valid_filename,
    new_name=valid_filename,
    content=file_content
)
@settings(max_examples=100)
def test_file_rename_preserves_content(old_name, new_name, content):
    """
    **Feature: markdown-editor, Property 14: File Rename Preserves Content**
    
    For any existing file, after renaming via FileService, the old path SHALL not exist,
    the new path SHALL exist, and the content at the new path SHALL be identical
    to the original content.
    
    **Validates: Requirements 4.3**
    """
    # Ensure different names
    assume(old_name != new_name)
    
    with tempfile.TemporaryDirectory() as root:
        old_path = f"{old_name}.md"
        new_path = f"{new_name}.md"
        
        # Create file with content
        full_old_path = Path(root) / old_path
        full_old_path.write_text(content)
        
        service = FileService(root)
        
        # Rename file
        result = service.rename_file(old_path, new_path)
        assert result.success, f"Rename failed: {result.message}"
        
        # Verify old path doesn't exist
        assert not full_old_path.exists(), "Old file still exists after rename"
        
        # Verify new path exists and has same content
        full_new_path = Path(root) / new_path
        assert full_new_path.exists(), "New file doesn't exist after rename"
        
        new_content = full_new_path.read_text()
        assert new_content == content, \
            f"Content changed after rename. Expected: {repr(content)}, Got: {repr(new_content)}"


@given(
    filename=valid_filename,
    content=file_content
)
@settings(max_examples=100)
def test_file_creation_persistence(filename, content):
    """
    **Feature: markdown-editor, Property 13: File Creation Persistence**
    
    For any valid file path and content, after creating a file via FileService,
    the file SHALL exist and be readable with the specified content.
    
    **Validates: Requirements 4.1**
    """
    with tempfile.TemporaryDirectory() as root:
        filepath = f"{filename}.md"
        
        service = FileService(root)
        
        # Create file
        result = service.create_file(filepath, content)
        assert result.success, f"Create failed: {result.message}"
        
        # Verify file exists
        full_path = Path(root) / filepath
        assert full_path.exists(), "File doesn't exist after creation"
        
        # Verify content
        file_content = service.read_file(filepath)
        assert file_content.content == content, \
            f"Content mismatch. Expected: {repr(content)}, Got: {repr(file_content.content)}"
