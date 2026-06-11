---
name: windows-bat-debug
description: Procedure for diagnosing and fixing Windows .bat/.cmd scripts that fail with "... was unexpected at this time."
source: auto-skill
extracted_at: '2026-06-11T11:29:54.616Z'
---

# Windows batch debug procedure

Use this when a `.bat` or `.cmd` script fails with:
```
... was unexpected at this time.
```

## Procedure
1. Read the target script file directly to inspect its current content.
2. Check for obvious batch syntax issues:
   - missing `@echo off` and `setlocal`
   - missing line breaks between commands
   - unterminated parentheses in `if (...) ( ... )` blocks
   - unbalanced quotes around `set "VAR=value"`
3. Check line endings:
   - run a byte-level inspection to detect lone `LF` (Unix) endings vs Windows `CRLF`
   - if needed, normalize to `CRLF` by reading the file as text and rewriting it through a Windows-aware writer
4. Isolate the failure:
   - create a minimal `_test_min.bat` containing just `@echo off` and one `echo` line to confirm `cmd` execution works
   - run the real script via `start "" "path\to\script.bat"` to avoid path quoting issues from `/s /c`
5. Fix the identified issue and re-run from the repo root:
   - prefer `start "" "MouseMasterClone\start.bat"`
   - if running inline is required, use `cmd /d /s /c "script.bat"`
6. Verify no extra batch fragments remain after the main logic.

## Notes
- If `pause` hangs in automation, replace with `exit /b` or remove interactive prompts.
- If `%~dp0` resolution is ambiguous, run a `_test_dp0.bat` that echoes `%~dp0` to confirm the working directory.
