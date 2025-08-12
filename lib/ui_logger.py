import logging as _logging, sys, customtkinter  # type: ignore
from typing import Dict, Optional

# Map C# Color names/log levels to CustomTkinter color names/hex codes for display
LOG_COLORS: Dict[str, str] = {
    "white": "white",
    "red": "#FF4444",  # A brighter red for errors/critical
    "green": "#44FF44",  # A brighter green for success info
    "yellow": "#FFFF00",  # Yellow for warnings
    "blue": "#66B2FF",  # A light blue for specific new entries/debug
}

# Module-level logger instance
_ui_logger: _logging.Logger = _logging.getLogger("UILogger")
_ui_logger.setLevel(_logging.DEBUG)  # Default level for the UI logger

# A flag to ensure handler is not added multiple times
_is_handler_setup: bool = False


class CustomTextHandler(_logging.Handler):
    """
    A custom logging handler that sends log records to a customtkinter CTkTextbox.
    """

    _textbox_instance: Optional[customtkinter.CTkTextbox] = None
    _colors_map: Dict[str, str] = LOG_COLORS

    @classmethod
    def set_textbox(cls, textbox: customtkinter.CTkTextbox) -> None:
        """Sets the CTkTextbox instance for the handler."""
        cls._textbox_instance = textbox

    def emit(self, record: _logging.LogRecord) -> None:
        if self._textbox_instance is None:
            # Fallback to console if textbox is not set
            _logging.StreamHandler().emit(record)
            return

        msg = self.format(record)

        # Determine color tag based on log level
        if record.levelno >= _logging.CRITICAL:
            color_tag = "red"
        elif record.levelno >= _logging.ERROR:
            color_tag = "red"
        elif record.levelno >= _logging.WARNING:
            color_tag = "yellow"
        elif record.levelno >= _logging.INFO:
            # Check for specific "blue" tag if it was used in log functions
            # (e.g., if a log function explicitly passed 'blue' as a hint)
            # This requires a bit more logic if you want to pass 'color' as extra.
            # For simplicity, we'll map default info to 'white'.
            color_tag = "white"
        elif record.levelno >= _logging.DEBUG:
            color_tag = "blue"  # Example for debug messages
        else:
            color_tag = "white"  # Default fallback

        # Insert text with a tag
        self._textbox_instance.insert("end", msg + "\n", color_tag)
        # Scroll to bottom
        self._textbox_instance.see("end")


# Public functions for logging to the UI
def setup_ui_logging(textbox: customtkinter.CTkTextbox) -> None:
    """
    Initializes the UI logger with the given CTkTextbox.
    This should be called ONCE when the UI is ready.
    """
    global _is_handler_setup
    if not _is_handler_setup:
        # Configure text box tags with colors
        for tag, color in LOG_COLORS.items():
            textbox.tag_config(tag, foreground=color)

        handler = CustomTextHandler()
        formatter = _logging.Formatter(
            "%(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)

        CustomTextHandler.set_textbox(
            textbox
        )  # Pass the textbox instance to the handler
        _ui_logger.addHandler(handler)
        _ui_logger.propagate = (
            False  # Prevent logs from going to default console if not desired
        )
        _is_handler_setup = True
        info("UI Logger initialized.")
    else:
        info("UI Logger already set up. Skipping re-initialization.")


def debug(message: str, **kwargs) -> None:
    """Logs a debug message to the UI."""
    _ui_logger.debug(message, stacklevel=2, **kwargs)


def info(message: str, **kwargs) -> None:
    """Logs an informational message to the UI."""
    _ui_logger.info(message, stacklevel=2, **kwargs)


def warning(message: str, **kwargs) -> None:
    """Logs a warning message to the UI."""
    _ui_logger.warning(message, stacklevel=2, **kwargs)


def error(message: str, **kwargs) -> None:
    """Logs an error message to the UI."""
    _ui_logger.error(message, stacklevel=2, **kwargs)


def critical(message: str, **kwargs) -> None:
    """Logs a critical message to the UI."""
    _ui_logger.critical(message, stacklevel=2, **kwargs)

def exception(message: str, **kwargs) -> None:
    """Logs an exception to the UI."""
    _ui_logger.exception(message, stacklevel=2, **kwargs)

def basicConfig(
    level: int = _logging.DEBUG,
    format: str = "%(filename)s:%(lineno)d - %(message)s",  # options: asctime (timestamp), levelname (info,debuf,...), name, filename, lineno, message
) -> None:
    """
    Configures the UI logger similar to logging.basicConfig.

    :param level: Log level (e.g., logging.DEBUG)
    :param format: Format string for log messages
    """
    global _is_handler_setup

    if not _is_handler_setup:
        _logging.basicConfig(level=level, format=format)
    else:
        _ui_logger.setLevel(level)
        formatter = _logging.Formatter(format)

        for handler in _ui_logger.handlers:
            if isinstance(handler, CustomTextHandler):
                handler.setFormatter(formatter)
                break


# Inject other attributes dynamically into the module namespace
_module = sys.modules[__name__]
for name in dir(_logging):
    if not hasattr(_module, name):  # Don't overwrite your custom functions
        setattr(_module, name, getattr(_logging, name))
