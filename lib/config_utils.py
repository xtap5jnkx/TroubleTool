import configparser
import os
from typing import Optional

CONFIG_FILENAME = "troubletool_config.ini"
AUTO_EXTRACT_FILES = "CEGUI/datafiles/lua_scripts, script, stage, xml"


def _get_config() -> configparser.ConfigParser:
    """
    Reads the config file, creating and populating it with defaults if it's
    missing sections or options. Returns the config object.
    """
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILENAME, encoding="utf-8")
    except Exception as e:
        print(f"Error reading config file: {e}.\n\nCreating {CONFIG_FILENAME} file.")

    is_modified = False
    if not config.has_section("Paths"):
        config.add_section("Paths")
        is_modified = True

    if not config.has_option("Paths", "troubleshooter"):
        config.set("Paths", "troubleshooter", "")
        is_modified = True

    if not config.has_section("ExtractFiles"):
        config.add_section("ExtractFiles")
        is_modified = True

    if not config.has_option("ExtractFiles", "auto"):
        config.set("ExtractFiles", "auto", AUTO_EXTRACT_FILES)
        is_modified = True

    if is_modified:
        if not os.path.exists(CONFIG_FILENAME):
            dirname = os.path.dirname(CONFIG_FILENAME)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as config_file:
            config.write(config_file)

    return config


def save_troubleshooter_path(path: str) -> None:
    """Saves the Troubleshooter path to the config file."""
    config = _get_config()
    old_path = config.get("Paths", "troubleshooter", fallback="")

    if old_path != path:
        config.set("Paths", "troubleshooter", path)
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as config_file:
            config.write(config_file)


def load_troubleshooter_path() -> Optional[str]:
    """
    Loads the Troubleshooter path from the config file.
    Returns the path as a string, or None if the option is missing.
    """
    config = _get_config()
    return config.get("Paths", "troubleshooter", fallback=None)


def save_extract_files(rel_files: str) -> None:
    config = _get_config()
    old_rel_files = config.get("ExtractFiles", "manual", fallback="")

    if old_rel_files != rel_files:
        config.set("ExtractFiles", "manual", rel_files)
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as config_file:
            config.write(config_file)


def load_auto_extract_files() -> str:
    config = _get_config()
    return config.get("ExtractFiles", "auto", fallback="")


def load_default_auto_extract_files() -> str:
    config = _get_config()
    str_files = config.get("ExtractFiles", "auto", fallback="")
    if str_files == AUTO_EXTRACT_FILES:
        return str_files
    config.set("ExtractFiles", "auto", AUTO_EXTRACT_FILES)
    return config.get("ExtractFiles", "auto", fallback="")


def save_auto_extract_files(rel_files: str) -> None:
    config = _get_config()
    old_rel_files = config.get("ExtractFiles", "auto", fallback="")

    if old_rel_files != rel_files:
        config.set("ExtractFiles", "auto", rel_files)
        with open(CONFIG_FILENAME, "w", encoding="utf-8") as config_file:
            config.write(config_file)


def load_extract_files() -> str:
    config = _get_config()
    return config.get(
        "ExtractFiles",
        "manual",
        fallback=config.get("ExtractFiles", "auto", fallback=""),
    )


#     # for return default value if not found
#     return config.get("Paths", "troubleshooter", fallback=None)
#
#     # raise KeyError if section or key not found
#     # return config["Paths"]["troubleshooter"]
