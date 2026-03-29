---
description: 'Workspace instructions for Linx Fast 2.0 - Python desktop template management application'
applyTo: '**'
---

# Project: Linx Fast 2.0

## Overview
Linx Fast 2.0 is a Python desktop application built with CustomTkinter for managing and processing text templates with dynamic placeholders. It follows SOLID principles with a service-oriented architecture for template operations, placeholder rendering, and UI management.

## Tech Stack
- Language: Python 3.x
- Framework: CustomTkinter (GUI)
- Package Manager: pip
- Build Tool: PyInstaller (via build.py)
- Testing: unittest

## Code Standards
- Follow PEP 8 conventions
- Use type hints where appropriate
- Apply SOLID principles (Single Responsibility, Open/Closed, etc.)
- Use descriptive variable and function names
- Add docstrings for public methods

## Architecture
- **Main App:** TemplateApp class orchestrates the application
- **Services Layer:** TemplateService and DialogService for business logic
- **Core Components:** TemplateManager (file I/O), PlaceholderEngine (rendering), ThemeManager (UI theming)
- **Data Storage:** Templates as .txt files with metadata in meta.json
- **UI:** CustomTkinter widgets with theme support

## Development Workflow
1. Run `python app.py` to start the application
2. Use `python -m unittest discover tests` for testing
3. Build with `python build.py` to create executable
4. Set `LFASTLOGLEVEL=DEBUG` for detailed logging to `./log/fast.log`

## Important Patterns
- Template naming: "Folder / TemplateName" (space-slash-space format)
- Placeholder syntax: `$Name$`, `$Name|Default$`, `$Agora[%H:%M]$`, `$[checkbox]Field$`
- Service adapters for extensibility (TemplateServiceAdapter)
- Debounced UI updates for theme changes
- Auto-logging decorator for debugging

## Do Not
- Hardcode desktop paths (use environment variables)
- Skip DPI awareness on Windows (ctypes.windll.shcore.SetProcessDpiAwareness())
- Modify version manually (auto-generated from git)
- Use print() for logging (use logger_config)
- Duplicate existing documentation (link to README.md, REFACTOR_NOTES.md, To-do.md)

## Key Files
- [app.py](app.py) - Main application entry point
- [template_manager.py](template_manager.py) - Template file operations
- [services/template_service.py](services/template_service.py) - Template business logic
- [utils/placeholder_engine.py](utils/placeholder_engine.py) - Dynamic field processing
- [theme_manager.py](theme_manager.py) - UI theming system
- [logger_config.py](logger_config.py) - Logging configuration

## Testing
- Run tests with `python -m unittest discover tests`
- Individual test files can be run directly: `python tests/test_theme_manager.py`
- Focus on unit tests for services and utilities
- UI tests use smoke testing approach

## Build & Deployment
- Use `python build.py` to create versioned .exe on Desktop
- Requires PyInstaller and git for version tagging
- Output includes version number from git describe
- Ensure all dependencies are installed before building