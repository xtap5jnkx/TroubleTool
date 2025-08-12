import logging
import os
from collections import defaultdict, deque
from typing import Optional

from lib import re_utils
from lib.utils import Utils


class LuaUtils:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._raw_code: Optional[str] = None
        self._base_map: Optional[dict[str, str]] = None
        self._original_map: Optional[dict[str, str]] = None
        self._changes: dict[str, list[tuple[str, str]]] = {}
        self._mods_path: Optional[str] = None
        self._mod_data_path: Optional[str] = None
        self._mod_file: Optional[str] = None
        self.read()

    @property
    def base_map(self) -> dict[str, str]:
        if not self._base_map:
            raise ValueError("Lua base_map not initialized")
        return self._base_map

    @base_map.setter
    def base_map(self, value: dict[str, str]):
        self._base_map = value

    @property
    def mods_path(self):
        if not self._mods_path:
            raise ValueError("Lua mods_path not initialized")
        return self._mods_path

    @mods_path.setter
    def mods_path(self, value: str):
        self._mods_path = value

    @property
    def mod_file(self):
        if not self._mod_file:
            raise ValueError("Lua mod_file not initialized")
        return self._mod_file

    @mod_file.setter
    def mod_file(self, value: str):
        self._mod_file = value

    def read(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            self._raw_code = f.read()
        self._base_map = LuaUtils._extract_definitions(self._raw_code)
        self._original_map = self._base_map.copy()

    @staticmethod
    def _read_file(file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            return rf"{f.read()}"

    def _get_mod_data_path(self):
        if self._mod_data_path:
            return self._mod_data_path

        mod_name = os.path.relpath(self.mod_file, self.mods_path).split(os.sep)[0]

        return os.path.join(self.mods_path, mod_name)

    def _read_from_file(self, from_file: str):
        if not from_file.endswith(".lua"):
            from_file += ".lua"

        self._mod_data_path = self._get_mod_data_path()

        file_path = (
            os.path.join(self._mod_data_path, "lua", from_file)
            if self.mods_path
            else from_file
        )
        with open(file_path, "r", encoding="utf-8") as f:
            return rf"{f.read()}"

    def writeto(self, fileout: str):
        if not self._base_map or self._base_map == self._original_map:
            return False

        sorted_keys = self._resolve_dependency_order(self._base_map)
        content = "\n".join(self._base_map[key] for key in sorted_keys) + "\n"

        with open(fileout, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def create_patch(self, fileout: str, relative_path: str):
        if not self._changes:
            return 2
        rel_path = relative_path.replace("\\", "/")
        action_map = {"new": "add_definition", "update": "replace_definition"}
        change_blocks = [
            f'def patch(game_files):\n\tscript = game_files.script("{rel_path}")\n'
        ]

        for change_type, items in self._changes.items():
            func_name = action_map.get(change_type)
            # if not items or not func_name:
            #     continue

            change_blocks.extend(
                # use raw code for escape special characters like `\n`
                f'\n\tscript.{func_name}("{name}", r"""{code}""")\n'
                for name, code in items
            )
        content = "".join(change_blocks)

        if not Utils.should_write(content, fileout):
            self._changes.clear()
            return 3

        with open(fileout, "w", encoding="utf-8") as f:
            f.write(content)
        self._changes.clear()
        return 1

    @staticmethod
    def _extract_definitions(raw_code: str) -> dict[str, str]:
        blocks = re_utils.COMMENT.sub("", raw_code)
        blocks = re_utils.DEF.split(blocks)
        definitions: dict[str, str] = {}
        for block in blocks:
            clean_block = block.strip()
            if not clean_block:
                continue

            func_match = re_utils.FUNC_DEF.match(clean_block)
            if func_match:
                definitions[func_match.group(0)] = clean_block
                continue

            if_match = re_utils.STARTSWITH_IF.match(clean_block)
            if if_match:
                definitions[if_match.group(0)] = clean_block
                continue

            if "=" in clean_block:
                key, _ = clean_block.split("=", 1)
                definitions[key.rstrip()] = clean_block
                continue

            logging.warning(f"not recognized block: {clean_block}")
        # for key, value in definitions.items():
        #     print(f"{key}: {value}")
        return definitions

    @staticmethod
    def _build_identifier_map(
        items: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, set[str]], dict[str, int]]:
        """Builds maps for identifiers and initializes in-degree counts."""
        identifier_map: dict[str, str] = {}
        split_keys: dict[str, set[str]] = {}
        in_degree: dict[str, int] = {key: 0 for key in items}

        # Map each individual identifier to the composite key that defines it.
        # e.g., {'fa': 'fa,haha,tata', 'haha': 'fa,haha,tata', ...}
        for key in items:
            local_name_match = re_utils.LOCAL_DEF.match(key)
            if local_name_match:
                # Local definition: "local foo, bar" or "local function baz"
                names_str = local_name_match.group(1)
                defined_vars = {v.strip() for v in names_str.split(",")}
                for var in defined_vars:
                    identifier_map[var] = key
                split_keys[key] = defined_vars

            # rare case for `if _G['a'] == nil then`
            elif re_utils.STARTSWITH_IF.match(key):
                objects = {
                    m.group(1) for m in re_utils.OBJECT_IN_IF.finditer(items[key])
                }
                if not objects:
                    continue
                for obj_name in objects:
                    identifier_map[obj_name] = key
                split_keys[key] = objects
        return identifier_map, split_keys, in_degree

    @staticmethod
    def _find_key_dependencies(
        items: dict[str, str],
        identifier_map: dict[str, str],
        in_degree: dict[str, int],
        reverse_graph: defaultdict[str, set],
    ):
        """Finds dependencies from definition keys (e.g., `obj.method` depends on `obj`)."""
        for key in items:
            # exclude local definition
            if re_utils.LOCAL_DEF.match(key) or re_utils.STARTSWITH_IF.match(key):
                continue

            if has_object := re_utils.OBJECT_IN_FUNC.match(key):
                obj_name = has_object.group(1)
                if obj_name not in identifier_map:
                    in_degree[key] = 1
                    reverse_graph[obj_name].add(key)
                continue

            # exclude other function
            if re_utils.STARTSWITH_FUNC.match(key):
                continue

            # vars need extract by `,` and if it is a property of an object,
            # increase key degree and add object name to reverse graph
            defined_vars = {v.strip() for v in key.split(",")}
            seen = set()
            for var in defined_vars:
                if has_object := re_utils.OBJECT_IN_VAR.match(var):
                    obj_name = has_object.group(1)
                    if obj_name in identifier_map or obj_name in seen:
                        continue
                    in_degree[key] += 1
                    reverse_graph[obj_name].add(key)
                    seen.add(obj_name)

    def _resolve_dependency_order(self, items: dict[str, str]) -> list[str]:
        """
        Given a dict of items {key: value}, where values may reference other keys,
        returns a list of keys sorted so that dependencies appear before dependents.
        Handles composite keys like "var1,var2" for multiple assignments.
        """
        identifier_map, split_keys, in_degree = LuaUtils._build_identifier_map(items)

        # incoming/outgoing edges in a conceptual graph
        # dependency_graph = defaultdict(set)  # key -> set of keys it depends on
        reverse_graph = defaultdict(set)  # key -> set of keys that depend on it

        # Build the dependency graph
        LuaUtils._find_key_dependencies(items, identifier_map, in_degree, reverse_graph)

        # find value dependencies
        for key, value in items.items():
            vars_from_key = split_keys.get(key, set())
            referenced_vars = {m.group(0) for m in re_utils.IDENTIFIERS.finditer(value)}
            for ref in referenced_vars:
                # if ref in all_keys and ref != key:
                if ref in identifier_map and ref not in vars_from_key:
                    definer_key = identifier_map[ref]
                    # dependency_graph[key].add(definer_key)
                    if key not in reverse_graph[definer_key]:
                        in_degree[key] += 1
                        reverse_graph[definer_key].add(key)

        # in_degree = {key: len(dependency_graph[key]) for key in items}
        ready = deque([key for key, deg in in_degree.items() if deg == 0])
        sorted_order = []

        # Kahn's algorithm for topological sort
        while ready:
            node = ready.popleft()
            sorted_order.append(node)
            for dependent in reverse_graph[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    ready.append(dependent)

        # Detect cycle: if not all nodes are sorted, there's a cycle
        if len(sorted_order) != len(items):
            cycle_nodes = {k for k, v in in_degree.items() if v > 0}
            raise ValueError(f"Cyclic dependency detected among nodes: {cycle_nodes}")

        return sorted_order

    def _find_changes(self, update_map: dict[str, str]):
        changes = defaultdict(list)
        for key, value in update_map.items():
            if key not in self.base_map:
                changes["new"].append((key, value))
            elif self.base_map[key] != value:
                changes["update"].append((key, value))
        return changes

    def merge_with(self, update_file: str, is_create_patch: Optional[bool] = None):
        update_raw_code = LuaUtils._read_file(update_file)
        if self._raw_code == update_raw_code:
            return

        update_map = LuaUtils._extract_definitions(update_raw_code)
        self._changes = self._find_changes(update_map)

        if not self._changes or is_create_patch:
            return

        merged_map = {}
        for key, value in self._changes["new"]:
            merged_map[key] = f"-- NEW\n{value}"
        for key, value in self._changes["update"]:
            merged_map[key] = f"-- UPDATE\n{value}"

        self.base_map.update(merged_map)

    def _get_code_from_args(self, code: Optional[str], from_file: Optional[str]):
        if not code and not from_file:
            raise ValueError("Either code or from_file must be provided.")
        if code and from_file:
            raise ValueError("Provide either code or from_file, not both.")

        if from_file:
            return self._read_from_file(from_file)

        assert code is not None
        return code

    def add_definition(self, def_name, code=None, from_file=None):
        if self.base_map.get(def_name):
            logging.warning(f"Def '{def_name}' already exists. overwrite.")
            # raise ValueError(f"Func/Var '{def_name}' already exists.")
        code_to_add = self._get_code_from_args(code, from_file)
        self.base_map[def_name] = code_to_add

    def replace_definition(self, def_name, code=None, from_file=None):
        if not self.base_map.get(def_name):
            logging.warning(f"Def '{def_name}' not found. add new.")
            # raise ValueError(f"Func/Var '{def_name}' not found.")
        code_to_replace = self._get_code_from_args(code, from_file)
        self.base_map[def_name] = code_to_replace

    def replace_code(
        self,
        def_name: str,
        old_code: str,
        new_code: Optional[str] = None,
        from_file: Optional[str] = None,
        count: int = -1,
    ):
        def_block_code = self.base_map.get(def_name)
        if not def_block_code:
            raise ValueError(f"'{def_name}' not found")
        if old_code not in def_block_code:
            raise ValueError(rf"'{old_code}' not found in '{def_name}'")
        code_to_replace = self._get_code_from_args(new_code, from_file)
        self.base_map[def_name] = def_block_code.replace(
            old_code, code_to_replace, count
        )

    def insert_code(
        self,
        def_name: str,
        target: str,
        code: Optional[str] = None,
        from_file: Optional[str] = None,
        position: str = "after",
        count: int = -1,
    ):
        if count == 0:
            return
        if not target:
            raise ValueError("target must be provided.")
        if position not in ("before", "after"):
            raise ValueError("Position must be 'before' or 'after'.")

        block_code = self.base_map.get(def_name)
        if not block_code:
            raise ValueError(f"'{def_name}' not found.")
        code_to_insert = self._get_code_from_args(code, from_file)

        parts = []
        limit = offset = pos = 0

        while (pos := block_code.find(target, pos)) != -1:
            line_start = block_code.rfind("\n", 0, pos) + 1
            line_end = block_code.find("\n", pos + len(target))
            if line_end == -1:
                line_end = len(block_code)

            # # whole lines matches
            # if block_code[line_start:line_end] == target:

            if position == "before":
                parts.extend([block_code[offset:line_start], code_to_insert + "\n"])
                offset = line_start
            elif position == "after":
                parts.extend([block_code[offset:line_end], "\n" + code_to_insert])
                offset = line_end

            limit += 1
            if count != -1 and limit >= count:
                break

            pos = line_end + 1  # move to next line

        if limit == 0:
            raise ValueError(f"{target} not found in '{def_name}'.")

        parts.append(block_code[offset:])
        self.base_map[def_name] = "".join(parts)

        # for m in re.finditer(rf"(?m)^{re.escape(target)}$", block_code):
        #     if count != -1 and limit >= count:
        #         break
        #     start, end = m.span()
        #
        #     if position == "before":
        #         # insert_at = start + offset
        #         insert_str = code_to_insert + "\n"
        #         parts.extend([block_code[offset:start], insert_str])
        #         offset = start
        #     elif position == "after":
        #         # insert_at = end + offset
        #         insert_str = "\n" + code_to_insert
        #         parts.extend([block_code[offset:end], insert_str])
        #         offset = end
        #
        #     limit += 1
        #
        # if limit == 0:
        #     raise ValueError(f"{target} not found in '{def_name}'.")
        #
        # parts.append(block_code[offset:])

        # # Efficiently find all matches before processing
        # all_matches = list(re.finditer(rf"(?m)^{re.escape(target)}$", block_code))
        # if not all_matches:
        #     raise ValueError(f"'{target}' not found in '{def_name}'.")
        #
        # matches = all_matches if count == -1 else all_matches[:count]
        # if not matches:
        #     return
        #
        # parts = []
        # last_idx = 0
        # if position == "before":
        #     insert_str = code_to_insert + "\n"
        #     for m in matches:
        #         start, _ = m.span()
        #         parts.append(block_code[last_idx:start])
        #         parts.append(insert_str)
        #         last_idx = start
        # else:  # position == "after"
        #     insert_str = "\n" + code_to_insert
        #     for m in matches:
        #         _, end = m.span()
        #         parts.append(block_code[last_idx:end])
        #         parts.append(insert_str)
        #         last_idx = end


def main():
    base_script = LuaUtils("./base.lua")
    base_script.merge_with("./update.lua")
    # base_script.insert_code(
    #     "iac", """	return fa,tata,boo();""", "\tabc", position="after", count=2
    # )
    base_script.writeto("./base.lua")


# # sample
# base_file = """
# o.pri = function(self) return b; end
# function o:greet()
#     print("call from o:greet: Hello, " .. self.name)
# end
# function alem() print(o.a, next()); end
# o.a, obj.name = 8, "bla"
# o.__index = o
# function obj:greet()
#     print("call from obj:greet: Hello, " .. self.name)
#     p = o:new("neo")
#     p:greet()
#     print(obj.name, var2)
#     print(next())
# end
# local obj = {}
# o = { name="abc"}
# local function next() return o:greet(), var1; end
# local bao = 1
# function o:new(name)
#     local instance = setmetatable({}, o)
#     instance.name = name
#     return instance
# end
# local var1, var2, var3 = 8, 9, 10
# function BuffHelper.IsRelation(from, to, relation)
#     local realRelation = GetRelation(from, to)
#     return BuffHelper.IsRelationMatched(realRelation, relation);
# end
# function BuffHelper.ForEachObjectInRange(obj, rangeType, pos, doFunc)
#     local targetRange = BuffHelper.CalculateRangeAroundObject(obj, rangeType, pos);
#     local targetObjects = BuffHelper.GetObjectsInRange(GetMission(obj), targetRange);
#
#     for _, target in ipairs(targetObjects) do
#         doFunc(target);
#     end
# end
# if _G['BuffHelper'] == nil then
#     _G['BuffHelper'] = {}
# end"""
# update_file = """
#     local bao = o
# """
