Refactor notes — SOLID improvements

Overview
--------
This commit introduces small, focused refactors to move the project toward SOLID principles.
The goal was to introduce low-risk, high-value abstractions so UI classes depend on interfaces
instead of concrete modules. This keeps behavior stable while making the code easier to test
and extend.

Key changes
-----------
1. DialogService (DIP / SRP)
   - Created `services/dialog_service.py`.
   - Provides a small adapter class `DialogService` with methods: `message`, `ask_yes_no`, `ask_string`.
   - `TemplateEditor` now instantiates and uses this service when available. This inverts the dependency
     (DIP) so UI code depends on an abstraction instead of the module `ctk_dialogs` directly.

2. TemplateServiceAdapter (OCP / ISP)
   - Created `services/template_service.py` with `TemplateServiceInterface` and `TemplateServiceAdapter`.
   - This adapter wraps the existing `manager` object and exposes a narrow surface used by the UI.
   - UI components can be updated to rely on the interface, keeping the implementation closed for modification
     while open for extension (OCP). New managers can be adapted with minimal changes.

3. TemplateEditor wiring (SRP / DIP)
   - `template_editor.py` now creates `self.dialogs` and `self.template_service` adapters at init.
   - All dialog calls go through the dialog adapter when present, with a fallback to `ctk_dialogs` to preserve
     compatibility.
   - Manager calls still work via `TemplateServiceAdapter` to centralize the interface.

4. Visual tweaks
   - Small adjustments to separator color selection and Save/Delete button colors were made previously; left as-is.

5. Build script
   - Added `build.py` (Python) to replace the previous `build.bat` behavior.
   - A backup of the original `build.bat` was saved as `build.bat.bak`.
   - `build.py` runs `generate_version.write_version_py()` (or the equivalent script) and invokes PyInstaller
     with the same files/data as before. It is cleaner and easier to extend/test.

How to extend
-------------
- To add unit tests for UI-independent logic, inject mocks for `DialogService` and `TemplateServiceInterface`.
- To support a new storage backend for templates, implement a concrete adapter that follows
  `TemplateServiceInterface` and pass it to the UI.

Notes and caveats
-----------------
- This is a small, incremental refactor: it introduces abstractions and wires them into `TemplateEditor`.
  A full project wide SOLID refactor would require more time (splitting `main_window` responsibilities,
  decoupling business logic from UI, and adding an IoC container or explicit dependency injection points).
- All changes were designed to be non-breaking. If you have custom manager implementations, they are still
  supported via `TemplateServiceAdapter`.

Next steps
----------
- Add unit tests for `services/template_service.py` replacement logic (rename placeholder behaviour).
- Incrementally move more UI modules to depend on the new interfaces.
- Consider introducing lightweight dependency injection to wire services centrally.
