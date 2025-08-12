from typing import Optional


class DicUtils:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._base_map: dict[str, str] = {}
        self._changes: dict[str, str] = {}
        self._lines: list[str] = []
        self._update_lines: list[str] = []
        self.read()

    def read(self):
        with open(self.file_path, encoding="utf-8") as f:
            self._lines = f.readlines()
        self._base_map = self._parse_lines(self._lines)

    def writeto(self, fileout: str):
        if not self._base_map:
            return False

        lines = list(self._base_map.values())
        if self._lines == lines:
            return False

        with open(fileout, "w", encoding="utf-8") as f:
            f.write("".join(lines))
        return True

    def create_patch(self, fileout: str):
        if not self._changes:
            self._update_lines.clear()
            return 2

        lines = list(self._changes.values())
        if self._update_lines == lines:
            self._update_lines.clear()
            self._changes.clear()
            return 3

        with open(fileout, "w", encoding="utf-8") as f:
            f.write("".join(self._changes.values()))
        self._changes.clear()
        self._update_lines.clear()
        return 1

    def _parse_lines(self, lines: list[str]):
        data = {}
        for line in lines:
            line = line.lstrip()
            if line.startswith("#"):
                key = line.split("\t", 1)[0]  # "#17"
                data[key] = line
        return data

    def merge_with(self, update_file: str, is_create_patch: Optional[bool] = None):
        with open(update_file, encoding="utf-8") as f:
            self._update_lines.extend(f.readlines())
        update_map = self._parse_lines(self._update_lines)

        for key, updated_line in update_map.items():
            old_line = self._base_map.get(key)
            if old_line is None:
                if is_create_patch is None:
                    self._base_map[key] = updated_line
                    continue
                self._changes[key] = updated_line
                continue
            if old_line != updated_line:
                if is_create_patch is None:
                    self._base_map[key] = updated_line
                    continue
                self._changes[key] = updated_line
