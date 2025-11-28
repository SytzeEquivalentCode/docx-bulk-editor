"""Document processors for multiprocessing operations."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessorResult:
    """Picklable result for multiprocessing compatibility.

    This dataclass is designed to be serializable via pickle for use with
    multiprocessing.Pool. All fields use basic types (bool, str, int, float)
    to ensure compatibility across process boundaries.

    Attributes:
        success: Whether the document processing completed successfully
        file_path: Path to the processed document
        changes_made: Number of changes/replacements made to the document
        error_message: Error description if processing failed, None otherwise
        duration_seconds: Time taken to process the document in seconds
    """
    success: bool
    file_path: str
    changes_made: int
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


__all__ = ['ProcessorResult']
