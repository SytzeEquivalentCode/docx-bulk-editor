# Phase 3: Core Infrastructure Tests - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Test the core infrastructure components that support document processing: ConfigManager, BackupManager, Logger, and DatabaseManager. These are foundational layers that other parts of the system depend on. Tests validate configuration loading/saving, backup creation/restoration, log rotation/encoding, and database CRUD/transactions.

</domain>

<decisions>
## Implementation Decisions

### Test Isolation Strategy
- **ConfigManager:** Temp directory per test — each test gets fresh temp dir, writes config there, auto-cleanup
- **BackupManager:** Temp directory + real docx files — create actual test documents, run real backup/restore cycles
- **DatabaseManager:** In-memory SQLite per test — each test gets `:memory:` database with schema applied fresh (consistent with Phase 2)
- **Logger:** Temp directory per test — each test writes logs to isolated temp dir for rotation/encoding testing

### Error Condition Coverage

**ConfigManager errors:**
- Missing config file → falls back to defaults
- Corrupt JSON → reports clear error message
- Type mismatches → validation catches and reports

**BackupManager errors:**
- Disk full → graceful failure with clear message
- Source file missing → error before backup attempt
- Restore fails → reports what went wrong, original state preserved

**DatabaseManager errors:**
- Transaction rollback → failed transactions roll back cleanly, no partial state
- Constraint violations → unique/foreign key violations report clearly

**Logger errors:**
- Rotation boundary → test behavior at size limit, no data loss
- Encoding edge cases → Unicode characters logged correctly (UTF-8 on Windows)

### Claude's Discretion
- Specific fixture implementation details
- Order of test modules within phase
- Whether to test Windows-specific edge cases (file locking, permission denied) — not required
- Database migration testing approach — not discussed, use judgment

</decisions>

<specifics>
## Specific Ideas

- Continue pattern from Phase 2: programmatic test document generation, no static test files
- In-memory SQLite pattern already established — maintain consistency
- Focus on realistic failure paths over exotic edge cases

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-core-infrastructure-tests*
*Context gathered: 2026-01-30*
