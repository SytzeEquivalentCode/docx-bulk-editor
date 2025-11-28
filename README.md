# DOCX Bulk Editor

A lightweight Windows desktop application for batch processing Microsoft Word (.docx) documents. Built with Python 3.11+ and PySide6 (Qt 6), it provides a native desktop experience for search/replace operations, metadata management, formatting enforcement, and document validation across hundreds of files simultaneously.

## Features

- **Batch Search & Replace**: Literal and regex search with formatting preservation
- **Metadata Management**: Clear or set document properties (author, company, etc.)
- **Table Formatting**: Standardize table styles across documents
- **Style Enforcement**: Apply consistent formatting rules
- **Document Validation**: Verify document structure and compliance
- **Automatic Backups**: Create backups before modifications with one-click restore
- **Real-time Progress**: Monitor processing with detailed progress tracking
- **Job History**: Review and restore previous operations

## Architecture

### Threading Model

```
Main Thread (UI)
    ↓ Qt Signals/Slots
Worker Thread (QThread)
    ↓ Multiprocessing (IPC)
Process Pool (CPU-bound operations)
```

- **Main Thread**: UI updates only, never blocks
- **Worker Thread**: Job orchestration, database I/O, pool management
- **Process Pool**: Document processing with python-docx (bypasses GIL)

### Project Structure

```
docx-bulk-editor/
├── src/
│   ├── ui/              # PySide6 UI components
│   ├── workers/         # QThread workers
│   ├── processors/      # Document processors (multiprocessing)
│   ├── database/        # SQLite database layer
│   ├── core/            # Config, logging, backup
│   └── utils/           # Utility functions
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── test_documents/  # Sample .docx files
├── assets/              # Application resources
└── config.json          # Application configuration
```

## Requirements

- **Python**: 3.11 or higher
- **Operating System**: Windows 10/11 (64-bit)
- **Dependencies**: See `requirements.txt`

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/docx-bulk-editor.git
cd docx-bulk-editor
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**
```bash
.\venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Development

### Running the Application

```bash
python src/main.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_search_replace.py
```

### Code Formatting

```bash
# Format code with Black
black src/

# Check code style
pylint src/
```

### Building Executable

```bash
# Build single-file executable
pyinstaller docx_bulk_editor.spec --clean
```

Output: `dist/docx_bulk_editor.exe` (~150-200MB)

## Configuration

The application uses `config.json` for configuration. Key settings:

```json
{
  "backup": {
    "directory": "./backups",
    "retention_days": 7
  },
  "processing": {
    "pool_size": null,
    "timeout_per_file_seconds": 60
  },
  "ui": {
    "theme": "system",
    "window_width": 1000,
    "window_height": 700
  }
}
```

## Windows Considerations

### Unicode Handling

**Always** specify `encoding='utf-8'` when opening files:

```python
# ✅ CORRECT
with open('file.txt', 'r', encoding='utf-8') as f:
    data = f.read()

# ❌ WRONG (uses Windows default cp1252)
with open('file.txt', 'r') as f:
    data = f.read()
```

### Path Handling

- Use `pathlib.Path` for cross-platform compatibility
- Support UNC paths: `\\server\share\file.docx`
- Use raw strings or forward slashes: `r"C:\path"` or `"C:/path"`

## Performance Targets

- **Startup time**: < 3 seconds
- **Processing speed**: 10-50 documents/minute (operation-dependent)
- **Memory footprint**: < 500MB for 500 documents
- **UI responsiveness**: 60 FPS during processing

## Documentation

- **CLAUDE.md**: Developer guide and implementation patterns
- **PRD.txt**: Complete product requirements and architecture
- **CLAUDE_CODE_SETUP.md**: Claude Code integration guide

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

## Support

For issues and questions, please use the GitHub issue tracker.
