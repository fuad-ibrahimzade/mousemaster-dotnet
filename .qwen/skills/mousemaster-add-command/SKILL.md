---
name: mousemaster-add-command
description: Procedure for adding a new mouse/keyboard command to the mousemaster Java/JNA low-level hook project.
source: auto-skill
extracted_at: '2026-06-11T13:47:55.510Z'
---

# Adding a command to mousemaster

Use this when extending the `mousemaster` project with a new actionable behavior (e.g. `MoveToActiveWindowCenter`).

## Pattern

1. Define the command record in `Command.java` (sealed interface):
   ```java
   record MyNewCommand() implements Command {}
   ```
2. Add a method on `MouseController.java` (or the relevant manager) that performs the action.
3. Wire the command in `CommandRunner.java`:
   ```java
   case MyNewCommand myNewCommand -> mouseController.myNewMethod();
   ```
4. Add a JUnit 5 test in `src/test/java/mousemaster/` using the existing plain-JUnit style (no mocking framework). Verify the record exists and that the target method is resolvable via reflection.

## Verification

- Run compile to ensure parity:
  ```bat
  mvnw compile -DskipTests
  ```
- If `JAVA_HOME` is unset, configure it before running Maven.

## Notes

- The project uses `com.sun.jna.platform.win32` for Windows APIs. Prefer fully-qualified names or add imports rather than wildcard imports.
- `CommandRunner` is the central dispatch point; all user-facing commands route through it.
- Tests in this project do **not** use Mockito—they use plain JUnit 5 assertions and reflection checks.
