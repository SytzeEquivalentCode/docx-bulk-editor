# Claude Code Configuration for DOCX Bulk Editor Project

This document describes the Claude Code agent and hook configuration for optimal development of this Python PySide6 desktop application.

## 🤖 Custom Specialized Agents

Three custom subagents have been configured to provide specialized expertise for this project:

### 1. Python Frontend Specialist (`python-frontend-specialist`)

**Location**: `~/.claude/agents/python-frontend-specialist.md`

**Specialization**:
- PySide6/Qt6 desktop application UI development
- QThread threading patterns for responsive UIs
- Signal/slot architecture for thread-safe communication
- Windows-specific UI considerations (DPI, Unicode, native dialogs)
- Qt widget hierarchies and layouts
- Performance optimization for 60 FPS responsiveness

**Key Expertise**:
- ✅ QMainWindow, QWidget, complex layouts
- ✅ QThread workers with progress signals
- ✅ Drag & drop, file dialogs, keyboard shortcuts
- ✅ High DPI scaling for modern Windows displays
- ✅ UTF-8 encoding for Windows Unicode handling
- ✅ QSettings for persistent configuration

**Usage**: Invoke this agent for any UI-related tasks, widget design, threading in GUI context, or user interaction features.

---

### 2. Python Backend Specialist (`python-backend-specialist`)

**Location**: `~/.claude/agents/python-backend-specialist.md`

**Specialization**:
- Document processing with python-docx library
- Multiprocessing for CPU-bound parallel tasks
- SQLite database management (thread-safe)
- Backup strategies and error recovery
- Performance optimization and memory management
- PyInstaller compatibility patterns

**Key Expertise**:
- ✅ python-docx for DOCX manipulation (search/replace, metadata, tables, styles)
- ✅ multiprocessing.Pool with `freeze_support()` for PyInstaller
- ✅ Robust error handling (locked files, corrupt documents, out of memory)
- ✅ SQLite with transactions, indexing, thread-safe connections
- ✅ Backup creation, validation, and restoration
- ✅ Batch processing optimization (10-50 docs/min target)

**Usage**: Invoke this agent for document processing logic, parallel computation, database operations, or backend architecture tasks.

---

### 3. Python QA Engineer (`python-qa-engineer`)

**Location**: `~/.claude/agents/python-qa-engineer.md`

**Specialization**:
- Testing Python PySide6 desktop applications
- pytest framework with fixtures, parametrization, mocking
- PySide6 GUI testing with QTest and QSignalSpy
- Multiprocessing and threading validation
- Performance testing and profiling
- Bug identification and root cause analysis

**Key Expertise**:
- ✅ Unit, integration, end-to-end, and regression testing
- ✅ PySide6 GUI testing (QTest, event simulation, signal verification)
- ✅ Multiprocessing validation (serialization, error isolation, PyInstaller compatibility)
- ✅ Windows-specific testing (Unicode paths, UNC paths, file locking, high DPI)
- ✅ Performance testing (startup time, processing speed, memory profiling)
- ✅ pytest-cov for code coverage (target > 80%)
- ✅ Bug reporting with severity classification (P0-P3)

**Usage**: Invoke this agent for writing tests, finding bugs, verifying fixes, performance testing, or quality assurance tasks.

---

## 🪝 Hooks Configuration

### Automatic Task Progression Hook

**Type**: Stop Hook (runs after Claude finishes responding)
**Location**: Configured in `~/.claude/settings.json`
**Script**: `~/.claude/taskmaster-continue.ps1`

#### What It Does

After Claude completes a response, the hook:

1. ✅ Checks if `.taskmaster/tasks/tasks.json` exists in the project
2. ✅ If exists:
   - Reads current task status (pending, in-progress, done)
   - Prompts Claude to evaluate if current task is complete
   - Suggests next pending task to work on
   - Provides MCP tool commands for task management
3. ✅ If not exists: Exits silently (no interruption)

#### Configuration

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\\Users\\s.pakvis\\.claude\\taskmaster-continue.ps1\""
          }
        ]
      }
    ]
  }
}
```

#### Benefits

- 🎯 **Automatic Task Flow**: No need to manually ask "what's next?"
- 🔄 **Continuous Progress**: Claude keeps working through task list
- 📋 **Zero Context Loss**: Hook reminds Claude of remaining tasks
- ⚡ **Optional Activation**: Only runs when tasks.json exists

---

## 📁 Project Structure for Claude Code

```
docx-bulk-editor/
├── .claude/                    # Project-specific Claude Code config (optional)
│   └── agents/                 # Project-level custom agents (if needed)
├── .taskmaster/                # Task management integration
│   ├── README.md               # Hook documentation
│   └── tasks/
│       └── tasks.json          # Task list (created by TaskMaster AI MCP)
├── PRD.txt                     # Product Requirements Document
├── CLAUDE_CODE_SETUP.md        # This file
└── [project files...]
```

---

## 🚀 Usage Guidelines

### For Frontend Development

When working on UI tasks:

```
Use the python-frontend-specialist agent for:
- Designing QMainWindow layouts
- Implementing QThread workers for long-running operations
- Creating progress dialogs and status updates
- Handling file drag-and-drop
- Configuring keyboard shortcuts
- Ensuring high DPI and Unicode support
```

### For Backend Development

When working on processing logic:

```
Use the python-backend-specialist agent for:
- Implementing document processors (search/replace, metadata, tables)
- Setting up multiprocessing pools with PyInstaller support
- Creating SQLite schemas and database operations
- Implementing backup creation and restoration
- Optimizing performance for batch processing
- Handling errors gracefully per-file
```

### Task Management

#### Current Session (TodoWrite)

For this development session, use Claude Code's **TodoWrite** tool:

```python
# Create task list
TodoWrite(todos=[
    {"content": "Implement search/replace UI", "status": "pending", "activeForm": "Implementing search/replace UI"},
    {"content": "Add multiprocessing pool", "status": "pending", "activeForm": "Adding multiprocessing pool"}
])

# Update as you work
TodoWrite(todos=[
    {"content": "Implement search/replace UI", "status": "completed", "activeForm": "Implementing search/replace UI"},
    {"content": "Add multiprocessing pool", "status": "in_progress", "activeForm": "Adding multiprocessing pool"}
])
```

#### Future: TaskMaster AI MCP

When TaskMaster AI MCP server is installed:

1. Tasks will be stored in `.taskmaster/tasks/tasks.json`
2. The Stop hook will automatically activate
3. Use MCP tools: `mcp__taskmaster-ai__next_task`, `mcp__taskmaster-ai__set_task_status`
4. Hook will prompt Claude to continue with next task after each completion

---

## 🔧 Technical Highlights

### Threading Architecture (from PRD)

```
┌─────────────────────────────────────┐
│     Main Thread (PySide6 UI)        │ ← python-frontend-specialist, python-qa-engineer
├─────────────────────────────────────┤
│          ↕ Signals/Slots            │
├─────────────────────────────────────┤
│    Worker Thread (QThread)          │ ← python-backend-specialist, python-qa-engineer
│  • Job orchestration                │
│  • Multiprocessing pool management  │
│  • SQLite database I/O              │
├─────────────────────────────────────┤
│          ↕ Multiprocessing          │
├─────────────────────────────────────┤
│   Multiprocessing Pool (N workers)  │ ← python-backend-specialist, python-qa-engineer
│  • Document processors              │
│  • python-docx operations           │
│  • CPU-bound parallel tasks         │
└─────────────────────────────────────┘
```

### Key Patterns to Follow

✅ **Main Thread**: Only UI updates and user input (never block!)
✅ **Worker Thread (QThread)**: Business logic, pool management, database
✅ **Multiprocessing Pool**: CPU-bound document processing
✅ **Signal/Slot**: Thread-safe communication between layers
✅ **UTF-8 Encoding**: Always explicit on Windows (`encoding='utf-8'`)
✅ **PyInstaller**: Include `multiprocessing.freeze_support()` in main guard

---

## 📋 Development Phases (from PRD)

| Phase | Focus | Primary Agent |
|-------|-------|---------------|
| Phase 0-1 | Project setup, infrastructure | Backend Specialist + QA Engineer |
| Phase 2 | Document processors | Backend Specialist + QA Engineer |
| Phase 3 | Core UI | Frontend Specialist + QA Engineer |
| Phase 4 | Advanced UI features | Frontend Specialist + QA Engineer |
| Phase 5 | Packaging (PyInstaller) | Backend Specialist + QA Engineer |
| Phase 6 | Testing & Polish | All three agents |

---

## 🎯 Performance Targets (from PRD)

- **Startup Time**: < 3 seconds
- **Processing Speed**: 10-50 docs/minute
- **Memory Footprint**: < 500MB for 500 documents
- **UI Responsiveness**: 60 FPS during processing
- **.exe Size**: < 200MB

---

## 📚 Quick Reference

### Invoke Agents in Prompts

```
"@python-frontend-specialist - Please implement the progress dialog UI with QThread worker"
"@python-backend-specialist - Create the document backup manager with SQLite tracking"
"@python-qa-engineer - Write comprehensive tests for the search/replace processor"
```

### Check Hook Status

```bash
# View current hooks configuration
cat ~/.claude/settings.json | grep -A 20 '"hooks"'

# Test the taskmaster hook (if tasks.json exists)
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.claude\taskmaster-continue.ps1"
```

### Monitor Task Progress

During development, the TodoWrite tool and Stop hook work together:
1. You create todos with TodoWrite
2. Claude works through tasks
3. Stop hook checks for .taskmaster/tasks/tasks.json
4. If found, prompts to continue; if not found, normal flow continues

---

## 🔐 Security Notes

- Hooks run with your current user's permissions
- The taskmaster-continue.ps1 script only reads tasks.json (read-only)
- No external network calls in hooks
- UTF-8 encoding prevents Unicode exploits on Windows

---

## ✅ Setup Verification

Run these checks to verify everything is configured:

```bash
# 1. Check agents exist
ls ~/.claude/agents/python-*

# 2. Check hooks configuration
cat ~/.claude/settings.json

# 3. Check project structure
ls -la .taskmaster/

# 4. Verify taskmaster script exists
ls ~/.claude/taskmaster-continue.ps1
```

Expected results:
- ✅ Three agent files in `~/.claude/agents/`: frontend, backend, and QA engineer
- ✅ Stop hook configured in settings.json
- ✅ `.taskmaster/tasks/` directory exists (created)
- ✅ taskmaster-continue.ps1 script exists

---

## 🚧 Future Enhancements

Potential improvements:
- [ ] Add PreToolUse hook for automatic code formatting before edits
- [ ] Create project-level agents in `.claude/agents/` for team sharing
- [ ] Integrate with TaskMaster AI MCP server when available
- [ ] Add PostToolUse hook for automatic testing after Write operations
- [ ] Create notification hooks for long-running operations

---

## 📖 Resources

- **Claude Code Docs**: https://code.claude.com/docs
- **PySide6 Documentation**: https://doc.qt.io/qtforpython/
- **python-docx Docs**: https://python-docx.readthedocs.io/
- **PyInstaller Manual**: https://pyinstaller.org/en/stable/

---

**Last Updated**: 2025-11-26
**Claude Code Version**: Latest
**Project**: DOCX Bulk Editor v1.0
