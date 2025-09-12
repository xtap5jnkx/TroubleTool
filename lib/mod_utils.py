# import importlib
import os
import runpy
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import NamedTuple, Optional
from unittest.mock import patch

from lxml import etree as et

import lib.ui_logger as logging
from lib import config_utils
from lib.asset_manager import AssetManager
from lib.dic_utils import DicUtils
from lib.lua_utils import LuaUtils
from lib.utils import Utils
from lib.xml_utils import XmlUtils

Element = et._Element
ElementTree = et._ElementTree


class ModData(NamedTuple):
    relative_paths: set[str]
    mod_data_path: str
    has_main_py: bool


class ModUtils:
    def __init__(self, am: AssetManager):
        self.am = am
        self.scripts: dict[str, LuaUtils] = {}
        self.xmls: dict[str, XmlUtils] = {}
        self.dics: dict[str, DicUtils] = {}
        self.settings_file: str = os.path.join(self.am.mods_path, "ModSettings.xml")
        self.settings_tree: Optional[ElementTree] = None
        self.settings_root: Optional[Element] = None

        self._handler_getters = {
            XmlUtils: self.xml,
            LuaUtils: self.script,
            DicUtils: self.dic,
        }
        self.lua = self.script

    def xml(self, rel_path: str, file_path=None):
        norm_rel_path = os.path.normpath(rel_path)
        ext = os.path.splitext(norm_rel_path)[1]
        first_dir = norm_rel_path.split(os.sep, 1)[0]

        if not ext:
            ext_map = {"xml": ".xml", "stage": ".stage", "Dictionary": ".dkm"}
            if ext := ext_map.get(first_dir):
                norm_rel_path += ext

        xml_util = self.xmls.get(norm_rel_path)
        if xml_util:
            return xml_util

        if not file_path:
            base_dir = self.am.root if first_dir == "Dictionary" else self.am.data_path
            file_path = os.path.join(base_dir, norm_rel_path)

        xml_util = XmlUtils(file_path)
        self.xmls[norm_rel_path] = xml_util
        return xml_util

    def _get_util(
        self,
        rel_path: str,
        file_path: Optional[str],
        cache: dict,
        util_class: type[LuaUtils | DicUtils],
        default_ext: str,
        base_dir: str,
    ):
        norm_rel_path = os.path.normpath(rel_path)

        if not os.path.splitext(norm_rel_path)[1]:
            norm_rel_path += default_ext

        util = cache.get(norm_rel_path)
        if util:
            return util

        if not file_path:
            file_path = os.path.join(base_dir, norm_rel_path)

        util = util_class(file_path)
        cache[norm_rel_path] = util
        return util

    def script(self, rel_path: str, file_path=None):
        return self._get_util(
            rel_path, file_path, self.scripts, LuaUtils, ".lua", self.am.data_path
        )

    def dic(self, rel_path: str, file_path=None):
        return self._get_util(
            rel_path, file_path, self.dics, DicUtils, ".dic", self.am.root
        )

    def _clear_cache(self):
        self.scripts.clear()
        self.xmls.clear()
        self.dics.clear()

    def _create_settings(self, dest: str):
        xml_str = "<mods></mods>"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(xml_str)
        logging.info(f"ModSettings.xml created at: {dest}")

    def load_settings(self):
        if self.settings_tree is not None:
            return
        if not os.path.exists(self.settings_file):
            logging.warning("ModSettings.xml not found, creating...")
            self._create_settings(self.settings_file)
        try:
            self.settings_tree = et.parse(self.settings_file)
            self.settings_root = self.settings_tree.getroot()
        except Exception:
            try:
                self._create_settings(self.settings_file)
                self.settings_tree = et.parse(self.settings_file)
                self.settings_root = self.settings_tree.getroot()
            except Exception as e:
                raise IOError("Failed to create/load ModSettings.xml") from e

    def save_settings(self, data: list[dict] | None = None):
        if data:
            root = et.Element("mods")
            for mod in data:
                ele = mod.get("element")
                if ele is None:
                    ele = et.Element("mod", {"name": mod["name"]})
                ele.set("enabled", "1" if mod["enabled"] else "0")
                root.append(ele)
            self.settings_tree = et.ElementTree(root)
            self.settings_root = root
        if self.settings_tree is None or self.settings_root is None:
            logging.warning("not load or nothing to save")
            return
        et.indent(self.settings_root, space="\t")
        self.settings_tree.write(
            self.settings_file, encoding="utf-8", xml_declaration=True
        )
        logging.info(f"Mod settings saved successfully at {self.settings_file}")

    def _collect_mod_data(self, mod_names: list[str]):
        mod_file_map: dict[str, ModData] = {}
        extract_paths: set[str] = set()
        quick_extract = False

        for mod_name in mod_names:
            logging.debug(f"mod: {mod_name}")
            mod_path = os.path.join(self.am.mods_path, mod_name)
            if not os.path.exists(mod_path):
                logging.warning(f"Mod '{mod_name}' not found in Mods folder.")
                continue
            mod_data_path = os.path.join(mod_path, "Data")
            if not os.path.exists(mod_data_path):
                mod_data_path = mod_path

            relative_paths = set()
            main_py_found = False
            for root, dirs, files in os.walk(mod_data_path):
                if main_py_found:
                    break
                dirs[:] = [d for d in dirs if d not in ("__pycache__", "lua")]
                for filename in files:
                    file_path = os.path.join(root, filename)
                    extension = os.path.splitext(file_path)[1]
                    rel_path = os.path.relpath(file_path, mod_data_path)

                    # add xml, lua, dict, dkm for merge, stage for override, py for patch
                    relative_paths.add(rel_path)

                    if extension == ".py":
                        quick_extract = True
                        if filename == "main.py":
                            mod_data_path = root
                            main_py_found = True
                            break

                    if extension == ".dic" or extension == ".dkm" or quick_extract:
                        continue

                    # only add xml, lua, stage for extract
                    extract_paths.add(rel_path)

            if relative_paths:
                mod_file_map[mod_name] = ModData(
                    relative_paths=relative_paths,
                    mod_data_path=mod_data_path,
                    has_main_py=main_py_found,
                )
        return extract_paths, mod_file_map, quick_extract

    def _write_all_files(self):
        from itertools import chain

        all_files = chain(
            self.xmls.values(),
            self.scripts.values(),
            self.dics.values()
        )

        def write_task(file_obj: XmlUtils | LuaUtils | DicUtils):
            try:
                if file_obj.writeto(file_obj.file_path):
                    logging.info(f"Patched {file_obj.file_path}")
                    return
                logging.debug(f"no changes in {file_obj.file_path}")
            except Exception as e:
                logging.error(f"{e} in {file_obj.file_path}")

        with ThreadPoolExecutor() as executor:
            executor.map(write_task, all_files)

        self._clear_cache()

    def _patch_main(self, mod_dir: str):
        self._write_all_files()
        with Utils.temp_sys_path(mod_dir):
            try:
                file_path = os.path.join(mod_dir, "main.py")
                # main_py = importlib.import_module("main")
                main_py = Utils.load_module_from_filepath(file_path)
                if hasattr(main_py, "settings"):
                    setattr(main_py.settings, "GAME_FOLDER", self.am.root)

                # avoid wait for input prompt
                with patch("builtins.input", return_value=""):
                    # If it has a callable `main` function, use it
                    if hasattr(main_py, "main") and callable(main_py.main):
                        main_py.main()

                    # No `main()` — run the module as __main__ so the
                    # `if __name__ == "__main__":` block executes
                    else:
                        runpy.run_module("main", run_name="__main__")
            except ModuleNotFoundError:
                logging.error(f"main.py not found in: {mod_dir}")
            except Exception as e:
                logging.exception(f"Error running main.py: {e}")

    def _patch(self, mod_file: str):
        logging.info(f"Running patch: {mod_file}")
        # module_name = os.path.splitext(os.path.basename(mod_file))[0]
        with Utils.temp_sys_path(os.path.dirname(mod_file)):
            try:
                # mod = importlib.import_module(module_name)
                mod = Utils.load_module_from_filepath(mod_file)
                if not hasattr(mod, "patch"):
                    logging.warning(f"No 'patch' function in {mod_file}")
                    return
                mod.patch(self)
            except ModuleNotFoundError:
                logging.error(f"Module not found in: {mod_file}")
            except Exception as e:
                logging.exception(f"Error patching {mod_file}: {e}")

    def _override(self, base_file: str, mod_file: str):
        # dir must exist before copy
        os.makedirs(os.path.dirname(base_file), exist_ok=True)
        if not Utils.should_copy(mod_file, base_file):
            logging.debug(f"No changes in '{base_file}', skip")
            return
        try:
            shutil.copy2(mod_file, base_file)
        except Exception as e:
            logging.error(f"{e}")
        logging.info(f"Copied '{mod_file}' to '{base_file}'")

    def _merge(
        self,
        FileHandlerCls: type[XmlUtils | LuaUtils | DicUtils],
        base_file: str,
        mod_file: str,
        rel_path: str,
        is_create_patch: Optional[bool] = None,
    ):
        try:
            handler_getter = self._handler_getters[FileHandlerCls]
            file_handle = handler_getter(rel_path, base_file)

            file_handle.merge_with(mod_file, is_create_patch)
            if is_create_patch is None:
                return
            if isinstance(file_handle, DicUtils):
                rs = file_handle.create_patch(mod_file)
            else:
                py_file = os.path.splitext(mod_file)[0] + ".py"
                rs = file_handle.create_patch(py_file, rel_path)
                os.remove(mod_file)
                if rs == 3:
                    logging.debug(f"{py_file} not change, skip")
                    return

            log_map = {
                1: lambda: logging.info(f"Rewritten {mod_file}"),
                2: lambda: logging.debug(f"{mod_file} make no changes"),
                3: lambda: logging.debug(f"{mod_file} not change, skip"),
            }

            if rs in log_map:
                log_map[rs]()
        except Exception as e:
            logging.exception(f"{mod_file} error: {e}")

    def _process_mods(self, mod_file_map: dict[str, ModData], is_create_patch=None):
        log_action = "Rewriting" if is_create_patch else "Applying"
        logging.debug(f"{log_action} mod files...")
        original_cwd = os.getcwd()

        for mod_name, mod_data in mod_file_map.items():
            if is_create_patch is None:
                os.chdir(mod_data.mod_data_path)

            if mod_data.has_main_py:
                if is_create_patch is None:
                    logging.debug(f"Running main.py in mod: {mod_name}")
                    self._patch_main(mod_data.mod_data_path)
                continue

            logging.debug(f"{log_action} files for mod: '{mod_name}'")

            # def process_file(rel_path: str):
            for rel_path in mod_data.relative_paths:
                mod_file = os.path.join(mod_data.mod_data_path, rel_path)
                extension = os.path.splitext(mod_file)[1]

                if extension == ".py":
                    if is_create_patch is None:
                        self._patch(mod_file)
                    continue

                base_file = (
                    os.path.join(self.am.root, rel_path)
                    if extension in (".dic", ".dkm")
                    else os.path.join(self.am.data_path, rel_path)
                )
                if extension == ".stage":
                    if is_create_patch is None:
                        self._override(base_file, mod_file)
                    continue

                handler_map = {".dic": DicUtils, ".lua": LuaUtils}
                FileHandlerCls = handler_map.get(extension, XmlUtils)

                self._merge(
                    FileHandlerCls, base_file, mod_file, rel_path, is_create_patch
                )

            # with ThreadPoolExecutor() as executor:
            #     executor.map(process_file, mod_data.relative_paths)

        if is_create_patch is None:
            logging.info("Save changes...")
            os.chdir(original_cwd)
            self._write_all_files()

    def _run_mod_processing(self, mod_names: list[str], is_create_patch=None):
        extract_paths, mod_file_map, quick_extract = self._collect_mod_data(mod_names)
        if not mod_file_map:
            logging.warning("No mods found.")
            return

        auto_extract_files = config_utils.load_auto_extract_files()
        if auto_extract_files:
            if quick_extract and is_create_patch is None:
                self.am.extract_entries(auto_extract_files)
            elif extract_paths:
                self.am.extract_entries(extract_paths, "exact")

        self._clear_cache()
        self._process_mods(mod_file_map, is_create_patch)

    def install(self, mod_names: list[str]):
        logging.info("Preparing Install Mods")
        self._run_mod_processing(mod_names)
        logging.info("Install Mods Done")

    def create_patch(self, mod_names: list[str]):
        logging.info("Preparing Create Patch Mods")
        self._run_mod_processing(mod_names, True)
        logging.info("Create Patch Mods Done")
