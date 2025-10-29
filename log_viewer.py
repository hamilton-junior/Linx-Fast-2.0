"""Log viewer removed.

This module previously provided a CTk-based log viewer. The application
was refactored to remove in-UI log reading/preview/export/clear functionality.

Left a harmless stub to avoid import-time crashes in case any module still
references LogViewer; instantiating the class will raise a RuntimeError so
that any remaining callers are obvious during runtime.
"""


class LogViewer:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("LogViewer has been removed from the application.")
