import filecmp
import hashlib
import os
import sys
import threading
import time
from contextlib import contextmanager
from functools import wraps
from typing import Union


class Utils:
    @staticmethod
    def log_mod_run_time(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            start_msg = f"[{func.__name__}] - "
            mod_name = args[3]
            if mod_name:
                start_msg += f"{mod_name} - "
            start_msg += "Starting..."
            print(start_msg)

            result = func(*args, **kwargs)
            end = time.perf_counter()
            elapsed = end - start
            finish_msg = f"[{func.__name__}] - "
            if mod_name:
                finish_msg += f"{mod_name} - "
            finish_msg += f"Finished in {elapsed:.4f} seconds."
            print(finish_msg)

            return result

        return wrapper

    @staticmethod
    def log_time(message=None):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                start_msg = f"[{func.__name__}] - "
                if message:
                    start_msg += f"{message} - "
                start_msg += "Starting..."
                print(start_msg)

                result = func(*args, **kwargs)
                end = time.perf_counter()
                elapsed = end - start
                finish_msg = f"[{func.__name__}] - "
                if message:
                    finish_msg += f"{message} - "
                finish_msg += f"Finished in {elapsed:.4f} seconds."
                print(finish_msg)

                return result

            return wrapper

        return decorator

    @staticmethod
    def center_window(window, width, height):
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        x = int((screen_w / 2) - (width / 2))
        y = int((screen_h / 2) - (height / 2))
        window.geometry(f"{width}x{height}+{x}+{y}")

    @staticmethod
    def move_to_top(window):
        window.attributes("-topmost", True)  # always on top
        window.lift()
        # release always-on-top
        window.after(100, lambda: window.attributes("-topmost", False))
        # must delay focus to make it work
        window.after(150, lambda: window.focus_force())

        # mod_window.overrideredirect(True)  # removes title bar and border. do not use
        # # Another way to make it on top of main window
        # # title bar color not dark
        # mod_window.transient(self)      # keeps it visually on top
        # mod_window.grab_set()           # makes it modal
        # mod_window.focus_force()        # focus it immediately

    @staticmethod
    def show_progress_bar(bar, before=None):
        # bar.pack(pady=10, padx=10, fill='x')
        bar.pack(before=before, padx=10, fill="x")
        bar.set(0)  # start at 0%

    @staticmethod
    def task(target, *args, **kwargs):
        threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True).start()

    @staticmethod
    @contextmanager
    def temp_sys_path_and_cwd(path: str):
        original_sys_path = list(sys.path)
        original_cwd = os.getcwd()
        sys.path.insert(0, str(path))
        os.chdir(path)
        try:
            yield
        finally:
            sys.path[:] = original_sys_path
            os.chdir(original_cwd)

    @staticmethod
    @contextmanager
    def temp_sys_path(path: str):
        original_sys_path = list(sys.path)
        sys.path.insert(0, str(path))
        os.chdir(path)
        try:
            yield
        finally:
            sys.path[:] = original_sys_path

    @staticmethod
    def should_copy(file1, file2):
        # If sizes differ, definitely not the same
        if not os.path.exists(file1) or not os.path.exists(file2):
            return True  # Missing file = needs copy
        if os.path.getsize(file1) != os.path.getsize(file2):
            return True  # Different size = different
        return not filecmp.cmp(file1, file2, shallow=False)

    @staticmethod
    def file_hash(path):
        h = hashlib.blake2b()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.digest()

    @staticmethod
    def should_write(source: Union[str, bytes], dst_path: str, encoding="utf-8"):
        """
        Returns True if `dst_path` does not exist or its content differs from `source`.

        - If `source` is str, it will be encoded using `encoding` before comparison.
        - If `source` is bytes, it will be used directly.
        """
        if not os.path.exists(dst_path):
            return True
        if isinstance(source, str):
            source_bytes = source.encode(encoding)
        elif isinstance(source, bytes):
            source_bytes = source
        else:
            raise TypeError(f"Unsupported source type: {type(source)}")
        try:
            return Utils.file_hash(dst_path) != hashlib.blake2b(source_bytes).digest()
        except Exception:
            return True
