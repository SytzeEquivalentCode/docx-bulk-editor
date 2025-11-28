"""Metadata management processor for DOCX documents."""

import time
from typing import Dict, Any
from docx import Document

from src.processors import ProcessorResult


def process_document(file_path: str, config: Dict[str, Any]) -> ProcessorResult:
    """Top-level function for multiprocessing (must be module-level).

    Args:
        file_path: Path to the DOCX file to process
        config: Configuration dictionary with metadata operations

    Returns:
        ProcessorResult with success status and change count
    """
    start_time = time.time()

    try:
        doc = Document(file_path)
        changes = perform_metadata_management(doc, config)

        if changes > 0:
            doc.save(file_path)

        duration = time.time() - start_time
        return ProcessorResult(
            success=True,
            file_path=file_path,
            changes_made=changes,
            duration_seconds=duration
        )
    except Exception as e:
        duration = time.time() - start_time
        return ProcessorResult(
            success=False,
            file_path=file_path,
            changes_made=0,
            error_message=str(e),
            duration_seconds=duration
        )


def perform_metadata_management(doc: Document, config: Dict[str, Any]) -> int:
    """Clear or set metadata properties on a document.

    Args:
        doc: python-docx Document object
        config: Configuration dictionary containing:
            - metadata_operations: Dict with 'clear' list and 'set' dict
                - clear: List of property names to clear (set to empty string)
                - set: Dict of property_name: value to set

    Returns:
        Number of metadata fields modified

    Supported properties:
        - author: Document author
        - title: Document title
        - subject: Document subject
        - keywords: Document keywords
        - comments: Document comments
        - category: Document category
        - content_status: Content status
        - created: Creation date (datetime)
        - last_modified_by: Last modifier
        - modified: Last modified date (datetime)
        - revision: Revision number
    """
    core_props = doc.core_properties
    changes = 0

    metadata_operations = config.get('metadata_operations', {})

    # Clear operations - set specified fields to empty string
    for field in metadata_operations.get('clear', []):
        if hasattr(core_props, field):
            try:
                # Handle different property types
                if field in ('created', 'modified'):
                    # Don't clear datetime fields, skip them
                    continue
                elif field == 'revision':
                    # Revision is an integer, set to 0
                    setattr(core_props, field, 0)
                else:
                    # String properties
                    setattr(core_props, field, '')
                changes += 1
            except Exception:
                # Some properties may be read-only, skip them
                pass

    # Set operations - set specified fields to new values
    for field, value in metadata_operations.get('set', {}).items():
        if hasattr(core_props, field):
            try:
                setattr(core_props, field, value)
                changes += 1
            except Exception:
                # Some properties may be read-only or wrong type, skip them
                pass

    return changes
