import importlib.util
import types
import os


def load(module_file: str) -> types.ModuleType:
    """
    Dynamically load a Python module from a file path.

    Args:
        mod_file_path (str): Absolute path to the .py file.

    Returns:
        types.ModuleType: The loaded Python module object.
    """
    module_name: str = os.path.splitext(os.path.basename(module_file))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from '{module_file}'")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
