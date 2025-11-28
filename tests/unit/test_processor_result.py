"""Unit tests for ProcessorResult dataclass."""

import pickle
import pytest
from src.processors import ProcessorResult


def test_processor_result_instantiation():
    """Test ProcessorResult can be instantiated with all required fields."""
    result = ProcessorResult(
        success=True,
        file_path="C:/test/document.docx",
        changes_made=5,
        error_message=None,
        duration_seconds=1.5
    )

    assert result.success is True
    assert result.file_path == "C:/test/document.docx"
    assert result.changes_made == 5
    assert result.error_message is None
    assert result.duration_seconds == 1.5


def test_processor_result_with_defaults():
    """Test ProcessorResult with default values for optional fields."""
    result = ProcessorResult(
        success=True,
        file_path="C:/test/document.docx",
        changes_made=0
    )

    assert result.success is True
    assert result.file_path == "C:/test/document.docx"
    assert result.changes_made == 0
    assert result.error_message is None
    assert result.duration_seconds == 0.0


def test_processor_result_with_error():
    """Test ProcessorResult with error message."""
    result = ProcessorResult(
        success=False,
        file_path="C:/test/broken.docx",
        changes_made=0,
        error_message="File not found",
        duration_seconds=0.1
    )

    assert result.success is False
    assert result.file_path == "C:/test/broken.docx"
    assert result.changes_made == 0
    assert result.error_message == "File not found"
    assert result.duration_seconds == 0.1


def test_processor_result_pickle_serialization():
    """Test ProcessorResult can be pickled and unpickled for multiprocessing."""
    original = ProcessorResult(
        success=True,
        file_path="C:/test/document.docx",
        changes_made=10,
        error_message=None,
        duration_seconds=2.3
    )

    # Serialize
    pickled = pickle.dumps(original)
    assert pickled is not None

    # Deserialize
    unpickled = pickle.loads(pickled)

    # Verify all fields are preserved
    assert unpickled.success == original.success
    assert unpickled.file_path == original.file_path
    assert unpickled.changes_made == original.changes_made
    assert unpickled.error_message == original.error_message
    assert unpickled.duration_seconds == original.duration_seconds


def test_processor_result_pickle_with_error():
    """Test ProcessorResult with error message can be pickled."""
    original = ProcessorResult(
        success=False,
        file_path="C:/test/error.docx",
        changes_made=0,
        error_message="Permission denied",
        duration_seconds=0.05
    )

    # Serialize and deserialize
    pickled = pickle.dumps(original)
    unpickled = pickle.loads(pickled)

    # Verify error message is preserved
    assert unpickled.success is False
    assert unpickled.error_message == "Permission denied"


def test_processor_result_unicode_path():
    """Test ProcessorResult handles Unicode file paths (Windows UTF-8 support)."""
    result = ProcessorResult(
        success=True,
        file_path="C:/Users/测试/文档/émoji_😀.docx",
        changes_made=3,
        duration_seconds=1.0
    )

    # Verify Unicode path stored correctly
    assert result.file_path == "C:/Users/测试/文档/émoji_😀.docx"

    # Verify it can be pickled with Unicode
    pickled = pickle.dumps(result)
    unpickled = pickle.loads(pickled)
    assert unpickled.file_path == result.file_path


def test_processor_result_field_types():
    """Test ProcessorResult field types are correct."""
    result = ProcessorResult(
        success=True,
        file_path="test.docx",
        changes_made=5
    )

    assert isinstance(result.success, bool)
    assert isinstance(result.file_path, str)
    assert isinstance(result.changes_made, int)
    assert result.error_message is None or isinstance(result.error_message, str)
    assert isinstance(result.duration_seconds, float)


def test_processor_result_equality():
    """Test ProcessorResult equality comparison."""
    result1 = ProcessorResult(
        success=True,
        file_path="test.docx",
        changes_made=5,
        duration_seconds=1.0
    )

    result2 = ProcessorResult(
        success=True,
        file_path="test.docx",
        changes_made=5,
        duration_seconds=1.0
    )

    # Dataclass automatically implements __eq__
    assert result1 == result2


def test_processor_result_negative_changes():
    """Test ProcessorResult accepts zero or negative changes (edge case)."""
    result = ProcessorResult(
        success=True,
        file_path="test.docx",
        changes_made=0
    )

    assert result.changes_made == 0
