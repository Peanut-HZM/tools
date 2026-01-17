"""
Property-based tests for SearchService

**Feature: markdown-editor, Property 7: Search Results Contain Query**
**Feature: markdown-editor, Property 8: Regex Search Pattern Matching**
**Feature: markdown-editor, Property 9: Case-Sensitive Search Behavior**
"""
import tempfile
import re
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume

from app.services.search_service import SearchService


# Strategy for valid file names (ASCII only)
valid_filename = st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789_-'
    ),
    min_size=1,
    max_size=15
)

# Strategy for search keywords (simple ASCII)
search_keyword = st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789'
    ),
    min_size=1,
    max_size=10
)

# Strategy for file content
file_content = st.text(
    alphabet=st.characters(
        whitelist_categories=(),
        whitelist_characters='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 \n.,!?-_'
    ),
    min_size=10,
    max_size=200
)


@given(
    filenames=st.lists(valid_filename, min_size=1, max_size=5, unique=True),
    keyword=search_keyword
)
@settings(max_examples=100)
def test_search_results_contain_query(filenames, keyword):
    """
    **Feature: markdown-editor, Property 7: Search Results Contain Query**
    
    For any search query and set of markdown files, all returned search results
    SHALL contain the search query string.
    
    **Validates: Requirements 6.1, 6.2**
    """
    with tempfile.TemporaryDirectory() as root:
        # Create files with content containing the keyword
        for i, name in enumerate(filenames):
            filepath = Path(root) / f"{name}.md"
            # Some files contain the keyword, some don't
            if i % 2 == 0:
                content = f"This file contains {keyword} in its content."
            else:
                content = "This file has different content."
            filepath.write_text(content)
        
        service = SearchService(root)
        results = service.search_content(keyword)
        
        # All results should contain the keyword
        for result in results:
            for match in result.matches:
                assert keyword.lower() in match.content.lower(), \
                    f"Search result doesn't contain keyword '{keyword}': {match.content}"


@given(
    filename=valid_filename,
    content=file_content,
    pattern_base=st.text(
        alphabet=st.characters(
            whitelist_categories=(),
            whitelist_characters='abcdefghijklmnopqrstuvwxyz'
        ),
        min_size=2,
        max_size=5
    )
)
@settings(max_examples=100)
def test_regex_search_pattern_matching(filename, content, pattern_base):
    """
    **Feature: markdown-editor, Property 8: Regex Search Pattern Matching**
    
    For any valid regular expression pattern and file content, the SearchService
    with regex mode enabled SHALL return results that match the pattern according
    to standard regex semantics.
    
    **Validates: Requirements 6.4**
    """
    assume(len(pattern_base) >= 2)
    
    with tempfile.TemporaryDirectory() as root:
        # Create file with content that includes the pattern
        filepath = Path(root) / f"{filename}.md"
        # Ensure content contains something that matches the pattern
        full_content = f"{content}\nThis line has {pattern_base}123 in it."
        filepath.write_text(full_content)
        
        service = SearchService(root)
        
        # Search with regex pattern (word followed by digits)
        regex_pattern = f"{pattern_base}\\d+"
        results = service.search_content(regex_pattern, regex=True)
        
        # Verify all matches actually match the regex
        compiled = re.compile(regex_pattern, re.IGNORECASE)
        for result in results:
            for match in result.matches:
                assert compiled.search(match.content), \
                    f"Match doesn't satisfy regex '{regex_pattern}': {match.content}"


@given(
    filename=valid_filename,
    keyword=search_keyword
)
@settings(max_examples=100)
def test_case_sensitive_search_behavior(filename, keyword):
    """
    **Feature: markdown-editor, Property 9: Case-Sensitive Search Behavior**
    
    For any search query, when case-sensitive mode is enabled, the SearchService
    SHALL only return results where the case of the matched text exactly matches
    the query case.
    
    **Validates: Requirements 6.5**
    """
    assume(len(keyword) >= 2)
    
    with tempfile.TemporaryDirectory() as root:
        filepath = Path(root) / f"{filename}.md"
        
        # Create content with both cases
        upper_keyword = keyword.upper()
        lower_keyword = keyword.lower()
        content = f"Line with {upper_keyword} uppercase.\nLine with {lower_keyword} lowercase."
        filepath.write_text(content)
        
        service = SearchService(root)
        
        # Case-sensitive search for lowercase
        results = service.search_content(lower_keyword, case_sensitive=True)
        
        for result in results:
            for match in result.matches:
                # The exact keyword should be in the content
                assert lower_keyword in match.content, \
                    f"Case-sensitive search returned wrong case: {match.content}"


@given(
    filenames=st.lists(valid_filename, min_size=1, max_size=5, unique=True),
    keyword=search_keyword
)
@settings(max_examples=100)
def test_file_search_contains_keyword(filenames, keyword):
    """
    **Feature: markdown-editor, Property 7: Search Results Contain Query**
    
    For any file name search, all returned results SHALL have names containing
    the search keyword.
    
    **Validates: Requirements 6.1**
    """
    with tempfile.TemporaryDirectory() as root:
        # Create files, some with keyword in name
        for i, name in enumerate(filenames):
            if i % 2 == 0:
                filepath = Path(root) / f"{name}_{keyword}.md"
            else:
                filepath = Path(root) / f"{name}.md"
            filepath.write_text("Content")
        
        service = SearchService(root)
        results = service.search_files(keyword)
        
        # All results should have keyword in name
        for result in results:
            assert keyword.lower() in result.name.lower(), \
                f"File search result doesn't contain keyword '{keyword}': {result.name}"
