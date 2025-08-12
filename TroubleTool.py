import os
import shutil
import subprocess
import sys
from typing import Optional

# Conditional import for winreg (Windows only)
if sys.platform == "win32":
    import winreg

# from PIL import Image  # Pillow
# from tkinter import filedialog

import customtkinter as ctk  # type: ignore

from lib import config_utils, progress_bar
from lib import ui_logger as logging
from lib.asset_manager import AssetManager
from lib.mod_utils import ModUtils
from lib.mods_model import ModsModel
from lib.utils import Utils
from lib.mod_manager_ui import ModManagerWindow

ctk.set_appearance_mode("Dark")  # Dark mode
ctk.set_default_color_theme("dark-blue")  # "blue" (default), "green", "dark-blue"
ctk.ThemeManager.theme["CTkFont"]["family"] = "Consolas"
ctk.ThemeManager.theme["CTkFont"]["size"] = 16


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TroubleTool inspired by github.com/K0lb3/TroubleTool")
        self.update_idletasks()  # ensures geometry info is available
        Utils.center_window(self, 800, 600)
        # font = ("consolas", 16)  # Define font
        # txt.configure(font=font)  # Apply font

        self._am: Optional[AssetManager] = None
        self.mod_utils: Optional[ModUtils] = None
        self.mods_model: Optional[ModsModel] = None
        self.mod_manager_window: Optional[ModManagerWindow] = None

        self._create_widgets()
        logging.setup_ui_logging(self.rich_text_box_log)
        logging.info("Application Start")
        progress_bar.init(self.progress_bar)
        # self.am = AssetManager(self)
        # if not self.am:
        self._find_troubleshooter()
        self._load_extract_files()

    @property
    def am(self) -> AssetManager:
        if not self._am:
            raise ValueError("AssetManager not initialized")
        return self._am

    @am.setter
    def am(self, value: AssetManager):
        self._am = value

    def _create_widgets(self):
        """Initializes all GUI components."""
        # Main frame for layout
        self.grid_columnconfigure((0, 1), weight=1)  # mean 2 columns auto grow same
        self.grid_rowconfigure(2, weight=1)  # only row x auto grow

        # Path section
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(columnspan=2, padx=10, pady=10, sticky="ew")
        self.path_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(self.path_frame, text="Troubleshooter Path:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )

        self.button_browse_path = ctk.CTkButton(
            self.path_frame,
            text="Browse",
            command=self._button_browse_troubleshooter_path_click,
        )
        self.button_browse_path.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.button_open_game_folder = ctk.CTkButton(
            self.path_frame,
            text="Open Game Folder",
            command=self._button_open_game_folder_click,
        )
        self.button_open_game_folder.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.troubleshooter_path_var = ctk.StringVar(self)
        self.troubleshooter_path_var.trace_add(
            "write", self._on_troubleshooter_path_change
        )
        self.text_box_troubleshooter_path = ctk.CTkEntry(
            self.path_frame, textvariable=self.troubleshooter_path_var
        )
        self.text_box_troubleshooter_path.grid(
            row=1, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        ctk.CTkLabel(
            self.path_frame, text="Extract Files (separated by comma ','):"
        ).grid(row=3, column=0, padx=5, pady=5, sticky="w")

        self.button_extract_files = ctk.CTkButton(
            self.path_frame,
            text="Extract",
            command=lambda: Utils.task(self._button_extract_files_click),
            state="disabled",
        )
        self.button_extract_files.grid(row=3, column=2, padx=5, pady=5, sticky="e")

        # 2 ways bind, get, set
        # self.extract_path_var = ctk.StringVar(self)
        # self.extract_path_var.trace_add("write", self._on_extract_path_change)
        self.text_box_extract_files = ctk.CTkEntry(
            self.path_frame,
            placeholder_text="CEGUI/datafiles/lua_scripts, script, stage, xml",
        )
        self.text_box_extract_files.grid(
            row=4, columnspan=3, padx=5, pady=5, sticky="ew"
        )
        # bind: can only get the value via typing
        # self.text_box_extract_path.bind("<KeyRelease>", self._on_extract_path_change)

        self.button_backup_index = ctk.CTkButton(
            self.path_frame,
            text="Backup Index",
            command=lambda: Utils.task(self._button_backup_index_click),
            state="disabled",
        )
        self.button_backup_index.grid(row=5, column=0, padx=5, pady=5, sticky="w")

        self.button_restore_index = ctk.CTkButton(
            self.path_frame,
            text="Restore Index",
            command=lambda: Utils.task(self._button_restore_index_click),
            state="disabled",
        )
        self.button_restore_index.grid(row=5, column=0, padx=5, pady=5, sticky="e")

        self.button_mod_manager = ctk.CTkButton(
            self.path_frame,
            text="Mods",
            command=self._button_mod_manager_click,
            state="disabled",
        )
        self.button_mod_manager.grid(row=5, column=2, padx=5, pady=5, sticky="e")

        # # Actions section
        # self.actions_frame = ctk.CTkFrame(self)
        # self.actions_frame.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        # self.actions_frame.grid_columnconfigure((0, 1, 2), weight=1)
        #
        # # self.button_extract = ctk.CTkButton(self.actions_frame, text="Extract Assets", command=lambda: Utils.task(self._button_extract_click), state="disabled")
        # # self.button_extract.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        # #
        # # self.button_apply = ctk.CTkButton(self.actions_frame, text="Apply Changes", command=lambda: Utils.task(self._button_apply_click), state="disabled")
        # # self.button_apply.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        #
        # self.button_repack_index = ctk.CTkButton(
        #     self.actions_frame,
        #     text="Repack index",
        #     command=lambda: Utils.task(self._button_repack_index_click),
        #     state="disabled",
        # )
        # self.button_repack_index.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # self.button_imagesets = ctk.CTkButton(
        #     self.actions_frame,
        #     text="Extract ImageSets",
        #     command=self._button_imagesets_click,
        #     state="disabled",
        # )
        # self.button_imagesets.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        #
        # # self.button_uninstall = ctk.CTkButton(self.actions_frame, text="Uninstall Mods", command=self._button_uninstall_click, state="disabled")
        # # self.button_uninstall.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        #
        # self.button_launch = ctk.CTkButton(
        #     self.actions_frame,
        #     text="Launch Game",
        #     command=self._button_launch_click,
        #     state="disabled",
        # )
        # self.button_launch.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        #
        # # Radio buttons (Data / Mods / Console)
        # self.options_frame = ctk.CTkFrame(self)
        # self.options_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        # self.options_frame.grid_columnconfigure((0, 1), weight=1)
        #
        # ctk.CTkLabel(self.options_frame, text="Game Data Source:").grid(
        #     row=0, column=0, columnspan=2, padx=5, pady=5, sticky="w"
        # )
        # self.data_source_var = ctk.StringVar(value="vanilla")  # Default
        # self.radio_button_vanilla = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="Vanilla Package",
        #     variable=self.data_source_var,
        #     value="vanilla",
        # )
        # self.radio_button_vanilla.grid(row=1, column=0, padx=5, pady=2, sticky="w")
        # self.radio_button_data = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="Use /Data Folder",
        #     variable=self.data_source_var,
        #     value="data",
        #     state="disabled",
        # )
        # self.radio_button_data.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        #
        # ctk.CTkLabel(self.options_frame, text="Mods:").grid(
        #     row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w"
        # )
        # self.mods_enabled_var = ctk.StringVar(value="no")
        # self.radio_button_mods_no = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="No Mods",
        #     variable=self.mods_enabled_var,
        #     value="no",
        # )
        # self.radio_button_mods_no.grid(row=3, column=0, padx=5, pady=2, sticky="w")
        # self.radio_button_mods_yes = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="Enable Mods",
        #     variable=self.mods_enabled_var,
        #     value="yes",
        # )
        # self.radio_button_mods_yes.grid(row=3, column=1, padx=5, pady=2, sticky="w")
        #
        # ctk.CTkLabel(self.options_frame, text="Console:").grid(
        #     row=4, column=0, columnspan=2, padx=5, pady=5, sticky="w"
        # )
        # self.console_enabled_var = ctk.StringVar(value="no")
        # self.radio_button_console_no = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="No Console",
        #     variable=self.console_enabled_var,
        #     value="no",
        # )
        # self.radio_button_console_no.grid(row=5, column=0, padx=5, pady=2, sticky="w")
        # self.radio_button_console_yes = ctk.CTkRadioButton(
        #     self.options_frame,
        #     text="Show Console",
        #     variable=self.console_enabled_var,
        #     value="yes",
        # )
        # self.radio_button_console_yes.grid(row=5, column=1, padx=5, pady=2, sticky="w")

        # Log RichTextBox
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(
            row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew"
        )  # Spans across both columns
        self.log_frame.grid_rowconfigure(
            0, weight=1
        )  # Allow textbox INSIDE its frame to expand
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.rich_text_box_log = ctk.CTkTextbox(self.log_frame, wrap="word")
        self.rich_text_box_log.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.log_frame, mode="determinate")

    def _button_browse_troubleshooter_path_click(self):
        """Allows user to select the Troubleshooter game folder."""
        folder_selected = ctk.filedialog.askdirectory()
        if folder_selected:
            self.troubleshooter_path_var.set(folder_selected)

    def _enable_all_buttons(self):
        # self.button_repack_index.configure(state="normal")
        # self.button_launch.configure(state="normal")
        # self.button_imagesets.configure(state="normal")
        self.button_open_game_folder.configure(state="normal")
        self.button_extract_files.configure(state="normal")
        self.button_backup_index.configure(state="normal")
        self.button_restore_index.configure(state="normal")
        self.button_mod_manager.configure(state="normal")

    def _disable_all_buttons(self):
        # self.button_repack_index.configure(state="disabled")
        # self.button_launch.configure(state="disabled")
        # self.button_imagesets.configure(state="disabled")
        self.button_open_game_folder.configure(state="disabled")
        self.button_extract_files.configure(state="disabled")
        self.button_backup_index.configure(state="disabled")
        self.button_restore_index.configure(state="disabled")
        self.button_mod_manager.configure(state="disabled")

    def _on_troubleshooter_path_change(self, *args):
        path = self.troubleshooter_path_var.get()
        package_path = os.path.join(path, "Package")
        if os.path.isdir(path) and os.path.exists(package_path):
            if not self._am or self._am.root != os.path.abspath(path):
                try:
                    self._am = AssetManager(path)
                    # Enable buttons
                    self._enable_all_buttons()
                except Exception as e:
                    logging.exception(f"Failed to initialize AssetManager: {e}")
                    self._disable_all_buttons()
            try:
                config_utils.save_troubleshooter_path(path)
            except Exception as e:
                logging.exception(f"Failed to save Troubleshooter path: {e}")
        else:
            logging.exception(f"Invalid path: {path}")
            self._disable_all_buttons()
            self._am = None

    def _parse_steam_library_folders(self, vdf_path: str) -> list[str]:
        """
        Parses the libraryfolders.vdf file to extract additional Steam library paths.
        This is a simple parser for the Valve KeyValue format (VDF).
        """
        paths: list[str] = []
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Simple regex to find "path" values within any "digit" block
            # This is a very basic parser and might not handle all VDF complexities.
            # A more robust solution might involve a dedicated VDF parser library.
            import re

            path_pattern = re.compile(
                r'"\d+"\s*\{\s*[^}]*?"path"\s*?"([^"]+)"', re.DOTALL
            )

            for match in path_pattern.finditer(content):
                found_path = match.group(1).replace(
                    "\\\\", os.sep
                )  # Normalize path separators
                paths.append(found_path)
        except Exception as e:
            logging.exception(f"Error parsing VDF file '{vdf_path}': {e}")
        return paths

    def _get_steam_library_paths(self) -> list[str]:
        """
        Attempts to locate Steam installation paths on different operating systems.
        Returns a list of steamapps directories.
        """
        lib_paths: list[str] = []
        logging.info("Attempting to locate Steam installation...")

        if sys.platform == "win32":
            try:
                # Try 64-bit registry first, then 32-bit
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Valve\Steam"
                    )
                except FileNotFoundError:
                    key = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"
                    )

                steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                winreg.CloseKey(key)

                logging.info(f"Steam found via registry: {steam_path}")
                lib_paths.append(os.path.join(steam_path, "steamapps"))

                # Add all library paths from steamapps/libraryfolders.vdf
                library_folders_vdf = os.path.join(
                    steam_path, "steamapps", "libraryfolders.vdf"
                )
                if os.path.exists(library_folders_vdf):
                    logging.info(
                        f"Parsing '{library_folders_vdf}' for additional libraries..."
                    )
                    additional_libs = self._parse_steam_library_folders(
                        library_folders_vdf
                    )
                    for lib in additional_libs:
                        steamapps_path = os.path.join(lib, "steamapps")
                        if os.path.isdir(steamapps_path):
                            lib_paths.append(steamapps_path)
                            logging.info(f"Added Steam library: {lib}")
                        else:
                            logging.warning(
                                f"Skipping invalid Steam library path: {lib}"
                            )
                else:
                    logging.warning(
                        f"'{library_folders_vdf}' not found. No additional Steam libraries will be searched."
                    )

            except FileNotFoundError:
                logging.error("Couldn't find Steam path in Windows registry.")
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred finding Steam on Windows: {e}"
                )
        elif sys.platform == "darwin":  # macOS
            mac_steam_path = os.path.expanduser(
                "~/Library/Application Support/Steam/steamapps"
            )
            if os.path.isdir(mac_steam_path):
                lib_paths.append(mac_steam_path)
                logging.info(f"Steam found on macOS: {mac_steam_path}")
            else:
                logging.warning("Common Steam path not found on macOS.")
        else:  # Linux and other Unix-like systems
            linux_steam_paths = [
                os.path.expanduser("~/.steam/steam/steamapps"),
                os.path.expanduser("~/.local/share/Steam/steamapps"),
                # Add other common Linux paths if needed
            ]
            found_linux_steam = False
            for p in linux_steam_paths:
                if os.path.isdir(p):
                    lib_paths.append(p)
                    logging.info(f"Steam found on Linux: {p}")
                    found_linux_steam = True
            if not found_linux_steam:
                logging.warning("Common Steam paths not found on Linux.")

        return lib_paths

    def _find_troubleshooter(self) -> None:
        """
        Attempts to locate the Troubleshooter game installation, primarily via Steam.
        """
        try:
            trouble_path = config_utils.load_troubleshooter_path()
            if trouble_path and os.path.isdir(trouble_path):
                self.troubleshooter_path_var.set(trouble_path)
                return
        except Exception as e:
            logging.exception(
                f"Error loading Troubleshooter path from AssetManager: {e}"
            )

        lib_paths: list[str] = []
        steam_app_paths = self._get_steam_library_paths()

        if not steam_app_paths:
            logging.error("No Steam installations.")
            return

        # Try to find "appmanifest_470310.acf" in the paths
        logging.info("Searching through the Steam libraries...")
        found_game = False
        for lib_path in lib_paths:
            logging.info(f"Checking: {lib_path}")
            appmanifest_path = os.path.join(lib_path, "appmanifest_470310.acf")
            if os.path.exists(appmanifest_path):
                game_common_path = os.path.join(lib_path, "common", "Troubleshooter")
                if os.path.isdir(game_common_path):
                    self.troubleshooter_path_var.set(game_common_path)
                    logging.info(f"Troubleshooter found: {game_common_path}")
                    found_game = True
                    break
                else:
                    logging.warning(
                        f"Found appmanifest, but game common folder '{game_common_path}' does not exist."
                    )

        if not found_game:
            logging.exception("Troubleshooter not found in Steam libraries.")
            # If path not found, text_box_troubleshooter_path will remain empty,
            # triggering the _on_troubleshooter_path_change logic to disable buttons.

    def _load_extract_files(self):
        """Loads the extract paths from the config file."""
        try:
            files = config_utils.load_extract_files()
            if files:
                self.text_box_extract_files.insert(0, files)
        except Exception as e:
            logging.exception(f"Error loading extract paths: {e}")

    def _button_extract_files_click(self) -> None:
        """Handles the 'Extract Path' button click."""
        self._disable_all_buttons()
        try:
            files = self.text_box_extract_files.get()
            if files:
                self.am.extract_entries(files)
                config_utils.save_extract_files(files)
        except Exception as e:
            logging.exception(f"Error during extraction: {e}")
        self._enable_all_buttons()

    def _initialize_mod_data(self):
        """Prepares ModUtils and ModsModel if they don't exist."""
        # Discover mod directories
        mod_dirs = set()
        for root, dirs, _ in os.walk(self.am.mods_path):
            for d in dirs:
                if os.listdir(os.path.join(root, d)):
                    mod_dirs.add(d)
            break  # Only scan top-level of mods_dir

        # Load mods from settings, tracking which ones are found
        mod_list = []
        settings_mods = {ele.get("name") for ele in self.mod_utils.settings_root}  # pyright: ignore
        for ele in self.mod_utils.settings_root:  # pyright: ignore
            if name := ele.get("name"):
                mod_path = os.path.join(self._am.mods_path, name)  # pyright: ignore
                if not os.path.exists(mod_path) or not os.listdir(mod_path):
                    continue
                mod_list.append(
                    {"name": name, "enabled": ele.get("enabled") == "1", "element": ele}
                )
        # Add newly found mods that are not in the settings file
        new_dirs = mod_dirs - settings_mods
        for name in sorted(list(new_dirs)):
            mod_list.append({"name": name, "enabled": False})
        return ModsModel(mod_list)

    def on_mod_manager_close(self):
        """Callback for when the ModManagerWindow is closed."""
        if self.mod_manager_window:
            self.mod_manager_window.destroy()
        self.mod_manager_window = None

        # Make sure main_ui's visible and not minimized
        self.deiconify()

    def _button_mod_manager_click(self) -> None:
        if self.mod_manager_window and self.mod_manager_window.winfo_exists():
            Utils.move_to_top(self.mod_manager_window)
            return

        try:
            if not self.mod_utils:
                self.mod_utils = ModUtils(self.am)
            # if not self.mods_model:
            self.mod_utils.load_settings()
            self.mods_model = self._initialize_mod_data()
            self.mod_manager_window = ModManagerWindow(
                self,
                self.mods_model,
                self.mod_utils,
            )
            self.mod_manager_window.protocol(
                "WM_DELETE_WINDOW", self.on_mod_manager_close
            )
        except Exception as e:
            logging.exception(f"Error opening Mod Manager: {e}")

    # def _button_launch_click(self) -> None:
    #     """Handles the 'Launch Game' button click."""
    #     if not self.troubleshooter_path_var.get():
    #         logging.exception("Troubleshooter path not set. Cannot launch.")
    #         return
    #
    #     game_path = self.troubleshooter_path_var.get()
    #     exe_path = os.path.join(game_path, "Release", "bin", "ProtoLion.exe")
    #
    #     if not os.path.exists(exe_path):
    #         logging.exception(f"Game executable not found at '{exe_path}'. Cannot launch.")
    #         return
    #
    #     # The C# code has commented out patching logic.
    #     # If you enable patching in C#, uncomment and implement it here using ExePatcher.
    #     # Example of commented C# part:
    #     """
    #     String exe_mod = Path.Combine(textBoxTroubleshooterPath.Text, "Release\\bin\\ProtoLion_mod.exe");
    #     if (!File.Exists(exe_mod))
    #     {
    #         byte[] index_pattern = Encoding.ASCII.GetBytes("\x00index\x00");
    #         byte[] replacement = Encoding.ASCII.GetBytes("\x00ind_m\x00");
    #         ExePatcher.PatchExe(exe_ori, exe_mod, index_pattern, replacement);
    #     }
    #     String index_ori = Path.Combine(textBoxTroubleshooterPath.Text, "Package\\index");
    #     String index_mod = Path.Combine(textBoxTroubleshooterPath.Text, "Package\\ind_m");
    #     File.Copy(index_ori, index_mod, true);
    #     """
    #     # If the commented C# patch were active, you'd do:
    #     # exe_mod_path = os.path.join(game_path, "Release", "bin", "ProtoLion_mod.exe")
    #     # index_pattern = b"\x00index\x00"
    #     # replacement = b"\x00ind_m\x00"
    #     # try:
    #     #     if not os.path.exists(exe_mod_path):
    #     #         ExePatcher.patch_exe(exe_path, exe_mod_path, index_pattern, replacement)
    #     #     # Also copy the index file if needed by the patch
    #     #     original_index_file = os.path.join(game_path, "Package", "index")
    #     #     mod_index_file = os.path.join(game_path, "Package", "ind_m")
    #     #     shutil.copy2(original_index_file, mod_index_file)
    #     #     exe_to_launch = exe_mod_path # Launch the modified exe
    #     # except Exception as e:
    #     #     logging.exception(f"Error patching executable: {e}")
    #     #     exe_to_launch = exe_path # Fallback to original
    #
    #     # For now, we launch the original EXE as per active C# code.
    #     exe_to_launch = exe_path
    #
    #     # Prepare arguments
    #     args = ["--pack", "--usedic"]
    #     if self.console_enabled_var.get() == "yes":  # C# radioButtonConsoleYes.Checked
    #         args.append("--console")
    #
    #     logging.info(f"Launching game: {exe_to_launch} with args: {' '.join(args)}")
    #
    #     try:
    #         # Prepare process start info
    #         process_env = os.environ.copy()
    #         process_env["SteamAPPID"] = "470310"  # Set environment variable
    #
    #         subprocess.Popen(
    #             [exe_to_launch] + args,
    #             cwd=os.path.join(game_path, "Release", "bin"),
    #             env=process_env,
    #             # For `UseShellExecute = false` in C#, typically `shell=False` in Python. default False in Python 3.8+
    #             # For `ProcessWindowStyle.Hidden` or `CreateNoWindow = true`, use `creationflags=subprocess.CREATE_NO_WINDOW`
    #             # However, C# had these commented, implying it showed the window.
    #             # _ = Process.Start(start) in C# is non-blocking. Popen is non-blocking by default.
    #         )
    #         logging.info("Game launched successfully.")
    #     except FileNotFoundError:
    #         logging.exception(f"Executable not found: {exe_to_launch}")
    #     except Exception as e:
    #         logging.exception(f"Error launching game: {e}")

    # def _button_imagesets_click(self) -> None:
    #     """Handles the 'Extract ImageSets' button click."""
    #     if not self.am:
    #         logging.error("AssetManager not initialized. Cannot extract imagesets.")
    #         return
    #
    #     imagesets_path = os.path.join(
    #         self.am.data_dir, "CEGUI", "datafiles", "imagesets"
    #     )
    #     if not os.path.isdir(imagesets_path):
    #         logging.exception(f"Imagesets directory not found: {imagesets_path}")
    #         return
    #
    #     logging.info("Starting ImageSets extraction...")
    #
    #     try:
    #         for file_info in os.listdir(imagesets_path):
    #             file_path = os.path.join(imagesets_path, file_info)
    #             if not file_path.lower().endswith(".imageset"):
    #                 continue
    #
    #             logging.info(f"Processing imageset file: {file_info}")
    #
    #             try:
    #                 imageset_xml = ET.parse(file_path)
    #                 root = imageset_xml.getroot()
    #
    #                 image_file_name = root.get("imagefile")
    #                 if not image_file_name:
    #                     logging.warning(
    #                         f"Imageset '{file_info}' missing 'imagefile' attribute."
    #                     )
    #                     continue
    #
    #                 image_path = os.path.join(
    #                     os.path.dirname(file_path), image_file_name
    #                 )
    #                 if not os.path.exists(image_path):
    #                     logging.exception(
    #                         f"Cannot find image file for imageset: {image_path}"
    #                     )
    #                     continue
    #
    #                 # Open the source image using Pillow
    #                 src_image = Image.open(image_path)
    #
    #                 output_dir_name = root.get("name")
    #                 if not output_dir_name:
    #                     logging.warning(
    #                         f"Imageset '{file_info}' missing 'name' attribute for output directory."
    #                     )
    #                     continue
    #
    #                 output_path = os.path.join(
    #                     os.path.dirname(file_path), output_dir_name
    #                 )
    #                 os.makedirs(
    #                     output_path, exist_ok=True
    #                 )  # Ensure output directory exists
    #
    #                 logging.info(f"Extracting images from: {image_path}")
    #
    #                 for entry in root.findall(
    #                     ".//Image"
    #                 ):  # Iterate over 'Image' elements in XML
    #                     image_name = entry.get("name")
    #                     x_pos = int(entry.get("xPos", "0"))
    #                     y_pos = int(entry.get("yPos", "0"))
    #                     width = int(entry.get("width", "0"))
    #                     height = int(entry.get("height", "0"))
    #
    #                     if not image_name or width == 0 or height == 0:
    #                         logging.warning(
    #                             f"Skipping invalid imageset entry in '{file_info}'."
    #                         )
    #                         continue
    #
    #                     logging.info(f"\tExtracting: {image_name}")
    #
    #                     # Define the bounding box for cropping (left, upper, right, lower)
    #                     crop_box = (x_pos, y_pos, x_pos + width, y_pos + height)
    #
    #                     # Crop the image
    #                     cropped_image = src_image.crop(crop_box)
    #
    #                     # Save the cropped image as PNG
    #                     output_image_path = os.path.join(
    #                         output_path, image_name.strip() + ".png"
    #                     )
    #                     cropped_image.save(output_image_path)
    #
    #             except ET.ParseError as pe:
    #                 logging.exception(f"Error parsing imageset XML '{file_info}': {pe}")
    #             except Exception as e:
    #                 logging.exception(f"An error occurred processing '{file_info}': {e}")
    #
    #         logging.info("ImageSets Extraction Done")
    #
    #     except Exception as e:
    #         logging.exception(f"Overall error during ImageSets extraction: {e}")

    def _button_open_game_folder_click(self) -> None:
        """Opens the game's root folder in the system's file explorer."""
        game_folder_path = self.troubleshooter_path_var.get()
        if not os.path.isdir(game_folder_path):
            logging.exception(f"Game folder not found: {game_folder_path}")
            return

        logging.info(f"Opening game folder: {game_folder_path}")
        try:
            if sys.platform == "win32":
                os.startfile(game_folder_path)  # Opens directory on Windows
            elif sys.platform == "darwin":  # macOS
                subprocess.Popen(["open", game_folder_path])
            else:  # Linux
                subprocess.Popen(
                    ["xdg-open", game_folder_path]
                )  # Common for many Linux desktops
            logging.info("Game folder opened.")
        except Exception as e:
            logging.exception(f"Error opening game folder: {e}")

    def _button_backup_index_click(self):
        if self._am is None:
            logging.error("AssetManager not initialized. Cannot backup index.")
            return

        if os.path.exists(self._am.index_file_backup):
            txt = "Package/index already backed up at: "
            logging.warning(txt + self._am.index_file_backup)
            return

        logging.info(f"Backing up Package/index to {self._am.index_file_backup}")

        try:
            shutil.copy2(self._am.index_file, self._am.index_file_backup)
            logging.info("Done!")
        except Exception as e:
            logging.exception(f"{e}")

    def _button_restore_index_click(self):
        if self._am is None:
            logging.error("AssetManager not initialized. Cannot restore index.")
            return

        if not os.path.exists(self._am.index_file_backup):
            logging.warning("Backup index file not found.")
            return

        try:
            if not Utils.should_copy(self._am.index_file_backup, self._am.index_file):
                logging.warning("Not different from backup. Skip.")
                return
            logging.info(f"Restoring {self._am.index_file_backup}")
            shutil.copy2(self._am.index_file_backup, self._am.index_file)
            logging.info("Restored.")
        except Exception as e:
            logging.exception(f"{e}")

    # def _button_repack_index_click(self):
    #     if self.am is None:
    #         logging.error("AssetManager not initialized. Cannot repack index.")
    #         return
    #     file_path = filedialog.askopenfilename(
    #         title="Select Index XML File To Pack",
    #         filetypes=[("Index XML File", "index.xml")],
    #         initialdir=os.path.join(self.am.data_dir, "index.xml"),
    #     )
    #
    #     if not file_path:
    #         return
    #
    #     logging.info(f"Preparing Repack 'Data/index.xml' to '{file_path}.enc'")
    #
    #     try:
    #         with open(file_path, "rb") as f:
    #             xml_bytes = f.read()
    #         IndexFileHelper.save_index(xml_bytes, file_path + ".enc", True)
    #         logging.info("Done!")
    #     except Exception as e:
    #         logging.exception(f"{e}")
    #     # finally:
    #     #     self.after(0, self.enable_controls) # safely re-enable controls from background thread.

    # def choose_outdir(self):
    #     path = filedialog.askdirectory(title="Select output directory")
    #     if path:
    #         self.out_dir = path
    #         self.out_label.configure(text=path)
    #         logging.info(f"Output folder: {path}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(os.getcwd())
    app = App()
    app.mainloop()
