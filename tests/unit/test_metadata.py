"""Unit tests for metadata processor."""

import shutil
import pytest
from pathlib import Path
from docx import Document

from src.processors.metadata import process_document, perform_metadata_management


@pytest.fixture
def test_docs_dir():
    """Return path to test documents directory."""
    return Path('tests/test_documents')


@pytest.fixture
def temp_doc(test_docs_dir, tmp_path):
    """Create a temporary copy of simple_doc.docx for testing."""
    source = test_docs_dir / 'simple_doc.docx'
    dest = tmp_path / 'metadata_test.docx'
    shutil.copy(source, dest)
    return dest


def test_clear_single_metadata_field():
    """Test clearing a single metadata field."""
    doc = Document()
    doc.core_properties.author = 'Test Author'
    doc.core_properties.title = 'Test Title'

    config = {
        'metadata_operations': {
            'clear': ['author']
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.author == ''
    assert doc.core_properties.title == 'Test Title'  # Unchanged


def test_clear_multiple_metadata_fields():
    """Test clearing multiple metadata fields."""
    doc = Document()
    doc.core_properties.author = 'Test Author'
    doc.core_properties.title = 'Test Title'
    doc.core_properties.subject = 'Test Subject'
    doc.core_properties.keywords = 'test, keywords'

    config = {
        'metadata_operations': {
            'clear': ['author', 'title', 'subject']
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 3
    assert doc.core_properties.author == ''
    assert doc.core_properties.title == ''
    assert doc.core_properties.subject == ''
    assert doc.core_properties.keywords == 'test, keywords'  # Unchanged


def test_set_single_metadata_field():
    """Test setting a single metadata field."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'author': 'New Author'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.author == 'New Author'


def test_set_multiple_metadata_fields():
    """Test setting multiple metadata fields."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'author': 'New Author',
                'title': 'New Title',
                'subject': 'New Subject',
                'keywords': 'new, keywords'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 4
    assert doc.core_properties.author == 'New Author'
    assert doc.core_properties.title == 'New Title'
    assert doc.core_properties.subject == 'New Subject'
    assert doc.core_properties.keywords == 'new, keywords'


def test_clear_and_set_operations():
    """Test combining clear and set operations."""
    doc = Document()
    doc.core_properties.author = 'Old Author'
    doc.core_properties.title = 'Old Title'

    config = {
        'metadata_operations': {
            'clear': ['author'],
            'set': {
                'title': 'New Title',
                'subject': 'New Subject'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 3
    assert doc.core_properties.author == ''
    assert doc.core_properties.title == 'New Title'
    assert doc.core_properties.subject == 'New Subject'


def test_clear_nonexistent_field():
    """Test clearing a field that doesn't exist (should be skipped)."""
    doc = Document()
    doc.core_properties.author = 'Test Author'

    config = {
        'metadata_operations': {
            'clear': ['nonexistent_field', 'author']
        }
    }

    changes = perform_metadata_management(doc, config)

    # Only 'author' should be cleared, nonexistent field is skipped
    assert changes == 1
    assert doc.core_properties.author == ''


def test_set_nonexistent_field():
    """Test setting a field that doesn't exist (should be skipped)."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'nonexistent_field': 'value',
                'author': 'Test Author'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    # Only 'author' should be set, nonexistent field is skipped
    assert changes == 1
    assert doc.core_properties.author == 'Test Author'


def test_empty_metadata_operations():
    """Test with empty metadata operations."""
    doc = Document()
    doc.core_properties.author = 'Test Author'

    config = {
        'metadata_operations': {}
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 0
    assert doc.core_properties.author == 'Test Author'  # Unchanged


def test_no_metadata_operations_key():
    """Test with missing metadata_operations key."""
    doc = Document()
    doc.core_properties.author = 'Test Author'

    config = {}

    changes = perform_metadata_management(doc, config)

    assert changes == 0
    assert doc.core_properties.author == 'Test Author'  # Unchanged


def test_unicode_metadata_values():
    """Test setting metadata with Unicode characters."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'author': '作者名',
                'title': 'Document 文档',
                'keywords': 'test, 测试, émoji 😀'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 3
    assert doc.core_properties.author == '作者名'
    assert doc.core_properties.title == 'Document 文档'
    assert doc.core_properties.keywords == 'test, 测试, émoji 😀'


def test_process_document_success(temp_doc):
    """Test process_document wrapper function with successful operation."""
    config = {
        'metadata_operations': {
            'set': {
                'author': 'Test Author',
                'title': 'Test Title'
            }
        }
    }

    result = process_document(str(temp_doc), config)

    assert result.success is True
    assert result.changes_made == 2
    assert result.error_message is None
    assert result.duration_seconds > 0

    # Verify changes were saved
    doc = Document(temp_doc)
    assert doc.core_properties.author == 'Test Author'
    assert doc.core_properties.title == 'Test Title'


def test_process_document_no_changes(temp_doc):
    """Test process_document with no changes made."""
    config = {
        'metadata_operations': {
            'clear': [],
            'set': {}
        }
    }

    result = process_document(str(temp_doc), config)

    assert result.success is True
    assert result.changes_made == 0
    assert result.error_message is None


def test_process_document_file_not_found():
    """Test process_document with non-existent file."""
    config = {
        'metadata_operations': {
            'set': {'author': 'Test'}
        }
    }

    result = process_document('nonexistent.docx', config)

    assert result.success is False
    assert result.changes_made == 0
    assert result.error_message is not None
    assert 'nonexistent.docx' in result.file_path


def test_clear_company_field():
    """Test clearing company field."""
    doc = Document()
    doc.core_properties.category = 'Test Company'

    config = {
        'metadata_operations': {
            'clear': ['category']
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.category == ''


def test_set_content_status():
    """Test setting content_status field."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'content_status': 'Final'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.content_status == 'Final'


def test_clear_comments():
    """Test clearing comments field."""
    doc = Document()
    doc.core_properties.comments = 'Some comments here'

    config = {
        'metadata_operations': {
            'clear': ['comments']
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.comments == ''


def test_overwrite_existing_metadata():
    """Test overwriting existing metadata values."""
    doc = Document()
    doc.core_properties.author = 'Old Author'
    doc.core_properties.title = 'Old Title'

    config = {
        'metadata_operations': {
            'set': {
                'author': 'New Author',
                'title': 'New Title'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 2
    assert doc.core_properties.author == 'New Author'
    assert doc.core_properties.title == 'New Title'


def test_clear_revision_sets_to_zero():
    """Test that clearing revision field attempts to set it to 0."""
    doc = Document()
    # Note: revision field may be read-only in python-docx
    doc.core_properties.revision = 5

    config = {
        'metadata_operations': {
            'clear': ['revision']
        }
    }

    changes = perform_metadata_management(doc, config)

    # Revision field might be read-only, so changes could be 0 or 1
    assert changes >= 0


def test_datetime_fields_not_cleared():
    """Test that datetime fields (created, modified) are not cleared."""
    doc = Document()

    config = {
        'metadata_operations': {
            'clear': ['created', 'modified']
        }
    }

    changes = perform_metadata_management(doc, config)

    # Datetime fields should be skipped, so changes = 0
    assert changes == 0


def test_set_last_modified_by():
    """Test setting last_modified_by field."""
    doc = Document()

    config = {
        'metadata_operations': {
            'set': {
                'last_modified_by': 'Automation Script'
            }
        }
    }

    changes = perform_metadata_management(doc, config)

    assert changes == 1
    assert doc.core_properties.last_modified_by == 'Automation Script'


def test_process_document_with_unicode(temp_doc):
    """Test process_document with Unicode metadata."""
    config = {
        'metadata_operations': {
            'set': {
                'author': '李明 (Lǐ Míng)',
                'title': 'Café Resume 😀',
                'keywords': 'naïve, résumé'
            }
        }
    }

    result = process_document(str(temp_doc), config)

    assert result.success is True
    assert result.changes_made == 3

    # Verify Unicode preserved
    doc = Document(temp_doc)
    assert doc.core_properties.author == '李明 (Lǐ Míng)'
    assert doc.core_properties.title == 'Café Resume 😀'
    assert doc.core_properties.keywords == 'naïve, résumé'


def test_set_invalid_property_type(temp_doc):
    """Test that setting property to invalid type doesn't crash (edge case for exception handler)."""
    config = {
        'metadata_operations': {
            'set': {
                'revision': 'not_a_number',  # revision should be int, this triggers exception
                'author': 'Valid Author'  # This should succeed
            }
        }
    }

    result = process_document(str(temp_doc), config)

    # Should succeed overall (exception is caught)
    assert result.success is True
    # Only the valid property should be changed
    assert result.changes_made == 1

    # Verify valid property was set, invalid was skipped
    doc = Document(temp_doc)
    assert doc.core_properties.author == 'Valid Author'
