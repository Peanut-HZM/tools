"""
Property-based tests for path validation

**Feature: markdown-editor, Property 6: Path Traversal Prevention**
**Validates: Requirements 8.1, 8.3**
"""
import os
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings

from app.utils.path_utils import validate_path, is_hidden, is_markdown_file


# Strategy for generating paths with traversal attempts
traversal_patterns = st.sampled_from([
    '../',
    '..\\',
    '../..',
    '../../',
    'foo/../bar/../..',
    'foo/../../bar',
    '..%2f',
    '..%5c',
    './../',
    'dir/subdir/../../..',
])


@given(traversal=traversal_patterns, suffix=st.text(min_size=0, max_size=20))
@settings(max_examples=100)
def test_path_traversal_rejected(traversal: str, suffix: str):
    """
    **Feature: markdown-editor, Property 6: Path Traversal Prevention**
    
    For any path containing directory traversal sequences (e.g., '..'),
    the validate_path function SHALL reject the request and return an error.
    """
    with tempfile.TemporaryDirectory() as root:
        # Create a path with traversal attempt
        malicious_path = f"{traversal}{suffix}"
        
        is_valid, result = validate_path(malicious_path, root)
        
        # Path with '..' should be rejected
        assert not is_valid, f"Path with traversal should be rejected: {malicious_path}"
        assert "traversal" in result.lower() or "outside" in result.lower()


@given(
    subdir=st.text(
        alphabet=st.characters(whitelist_categories=(), whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789_-'),
        min_size=1,
        max_size=10
    ),
    filename=st.text(
        alphabet=st.characters(whitelist_categories=(), whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789_-'),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100)
def test_valid_paths_within_root_accepted(subdir: str, filename: str):
    """
    **Feature: markdown-editor, Property 6: Path Traversal Prevention**
    
    For any valid path within the root directory (no traversal sequences),
    the validate_path function SHALL accept the request.
    """
    with tempfile.TemporaryDirectory() as root:
        # Create a valid path within root
        valid_path = f"{subdir}/{filename}"
        
        is_valid, result = validate_path(valid_path, root)
        
        # Valid paths should be accepted
        assert is_valid, f"Valid path should be accepted: {valid_path}, got error: {result}"
        # Result should be the resolved absolute path
        assert Path(result).is_absolute()


@given(
    outside_path=st.sampled_from([
        '/etc/passwd',
        '/tmp/outside',
        'C:\\Windows\\System32',
        '/root/.ssh/id_rsa',
    ])
)
@settings(max_examples=100)
def test_absolute_paths_outside_root_rejected(outside_path: str):
    """
    **Feature: markdown-editor, Property 6: Path Traversal Prevention**
    
    For any absolute path that is outside the root directory,
    the validate_path function SHALL reject the request.
    """
    with tempfile.TemporaryDirectory() as root:
        is_valid, result = validate_path(outside_path, root)
        
        # Paths outside root should be rejected
        assert not is_valid, f"Path outside root should be rejected: {outside_path}"


@given(name=st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_hidden_file_detection(name: str):
    """
    Test that hidden file detection works correctly.
    A file is hidden if and only if its name starts with '.'.
    """
    expected_hidden = name.startswith('.')
    actual_hidden = is_hidden(name)
    
    assert actual_hidden == expected_hidden, f"Hidden detection failed for: {name}"


@given(name=st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_markdown_file_detection(name: str):
    """
    Test that markdown file detection works correctly.
    A file is markdown if it ends with .md or .markdown (case insensitive).
    """
    lower_name = name.lower()
    expected_markdown = lower_name.endswith('.md') or lower_name.endswith('.markdown')
    actual_markdown = is_markdown_file(name)
    
    assert actual_markdown == expected_markdown, f"Markdown detection failed for: {name}"
