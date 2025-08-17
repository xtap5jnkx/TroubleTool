from typing import Optional

import customtkinter as ctk  # type: ignore

from lib.mod_utils import ModUtils
from lib.mods_model import ModsModel
from lib.utils import Utils
from lib import config_utils


class ModManagerWindow(ctk.CTkToplevel):
    """
    A dedicated window for managing mods, including reordering via drag-and-drop.
    """

    def __init__(self, master, mods_model: ModsModel, mod_utils: ModUtils):
        super().__init__(master)
        self.mods_model = mods_model
        self.mod_utils = mod_utils

        self.title("Mod Manager")
        self.update_idletasks()
        Utils.center_window(self, 800, 600)
        Utils.move_to_top(self)

        # Initialize drag-and-drop state
        self.drag_start_index: Optional[int] = None
        self.placeholder: Optional[ctk.CTkFrame] = None
        self.mod_row_frames: list[ctk.CTkFrame] = []
        self.big_font = ctk.CTkFont(size=22)
        self.bold_font = ctk.CTkFont(weight="bold")

        self._create_widgets()
        self.mods_model.on_change = self._render_mod_list
        self._render_mod_list()
        self._load_auto_extract_paths()

    def _create_widgets(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Auto extract files
        self.auto_extract_frame = ctk.CTkFrame(self)
        self.auto_extract_frame.grid(columnspan=3, padx=5, pady=5, sticky="ew")
        self.auto_extract_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.auto_extract_frame, text="Auto extract files for patch '.py' files:"
        ).grid(padx=5, pady=5, sticky="w")
        self.tbo_auto_extract_files = ctk.CTkEntry(
            self.auto_extract_frame,
            # placeholder_text="CEGUI/datafiles/lua_scripts, script, stage, xml",
        )
        self.tbo_auto_extract_files.grid(row=1, sticky="ew")
        cmd = lambda: self._load_default_auto_extract_files()
        ctk.CTkButton(
            self.auto_extract_frame,
            font=self.bold_font,
            text="↻",
            width=22,
            command=cmd,
        ).grid(row=1, column=1, padx=3)

        # Mods frame
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=3)
        self.scroll_frame.grid_columnconfigure((1, 2), weight=1, uniform="group1")

        # Header
        headers = ["Name", "Select", "Order"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(self.scroll_frame, text=header, font=self.bold_font)
            sticky_val = "w" if i == 0 else ""
            label.grid(row=0, column=i, padx=10, pady=5, sticky=sticky_val)

        # Bottom frame for controls
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="e", padx=10, pady=(5, 10))

        ctk.CTkLabel(bottom_frame, text="Drag & Drop to Reorder").pack(
            side="left", padx=(0, 9)
        )
        cmd = lambda: Utils.task(self._process, "install")
        ctk.CTkButton(bottom_frame, text="Install", command=cmd).pack(
            side="left", padx=(0, 9)
        )
        cmd = lambda: Utils.task(self._process, "create_patch")
        ctk.CTkButton(bottom_frame, text="Create Patch", command=cmd).pack(
            side="left", padx=(0, 9)
        )
        ctk.CTkButton(bottom_frame, text="Close", command=self._destroy).pack(
            side="left"
        )
        ctk.CTkLabel(
            self,
            text="""Each file is merged in mod priority order.
Mods later in the list have higher priority and
their changes override earlier ones when conflicts occur.""",
        ).grid(row=3, column=0, padx=5, pady=5, sticky="ew")

    def _render_mod_list(self):
        # Clear only the old mod entry rows and frames
        for widget in self.scroll_frame.winfo_children():
            if widget.grid_info()["row"] > 0:  # Skip header row
                widget.destroy()
        # for frame in self.mod_row_frames:
        #     frame.destroy()
        self.mod_row_frames.clear()

        n = len(self.mods_model.data) - 1
        for i, mod in enumerate(self.mods_model.data):
            row_index = i + 1  # Start rows after the header
            bg_color = "#2a2a2a" if row_index % 2 == 1 else "transparent"

            # 🧱 Create a row frame just for background color (spans full row)
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color, height=1)
            row_frame.grid(row=row_index, column=0, columnspan=3, sticky="nsew")
            row_frame.grid_propagate(False)  # ⛔ prevent growing to content
            row_frame.lower()  # ⬅️ Send it to back
            self.mod_row_frames.append(row_frame)
            self._bind_drag_events(row_frame, i)

            # 🔠 Name
            ctk.CTkLabel(self.scroll_frame, text=mod["name"], fg_color=bg_color).grid(
                row=row_index, column=0, padx=9, pady=9, sticky="w"
            )

            # ☑️ Enabled, ✍️ Create Patch checkbox
            cb_frame = ctk.CTkFrame(self.scroll_frame, fg_color=bg_color)
            cb_frame.grid(row=row_index, column=1)
            cmd = lambda idx=i: self.mods_model.toggle_enable(idx)
            cb = ctk.CTkCheckBox(cb_frame, text="", command=cmd)
            cb.select() if mod["enabled"] else cb.deselect()
            cb.pack(padx=(33, 1))

            # ⬆⬇ Order buttons
            order_frame = ctk.CTkFrame(self.scroll_frame)
            order_frame.grid(row=row_index, column=2)
            if i > 0:
                cmd = lambda idx=i: self.mods_model.swap(idx, -1)
                ctk.CTkButton(
                    order_frame, text="🡅", font=self.big_font, width=33, command=cmd
                ).pack(side="left", padx=(0, 9))
            if i < n:
                cmd = lambda idx=i: self.mods_model.swap(idx, 1)
                ctk.CTkButton(
                    order_frame, text="🡇", font=self.big_font, width=33, command=cmd
                ).pack(side="left")

    def _load_auto_extract_paths(self):
        """Loads the auto extract paths from the config file."""
        try:
            files = config_utils.load_auto_extract_files()
            if files:
                self.tbo_auto_extract_files.insert(0, files)
        except Exception as e:
            raise Exception(f"Error loading auto extract paths: {e}")

    def _load_default_auto_extract_files(self):
        """Loads the default auto extract paths from the config file."""
        try:
            files = config_utils.load_default_auto_extract_files()
            self.tbo_auto_extract_files.delete(0, "end")
            self.tbo_auto_extract_files.insert(0, files)
        except Exception as e:
            raise Exception(f"Error loading default auto extract paths: {e}")

    def _process(self, mode: str):
        """Processes enabled mods for 'install' or 'create_patch' actions."""
        mod_names = [data["name"] for data in self.mods_model.data if data["enabled"]]
        if not mod_names:
            return
        # self.master.deiconify() # show main ui
        self._save_data()
        try:
            process_func = getattr(self.mod_utils, mode)
            self._destroy()
            process_func(mod_names)
        except AttributeError:
            raise AttributeError(f"ModUtils has no method '{mode}'")
        except Exception as e:
            raise Exception(f"Failed to {mode} mods: {e}")

    def _save_data(self):
        try:
            self.mod_utils.save_settings(self.mods_model.data)
            config_utils.save_auto_extract_files(self.tbo_auto_extract_files.get())
        except Exception as e:
            raise Exception(f"Failed to save mod settings, config: {e}")

    def _destroy(self):
        # delay destroy until idle, to prevent Tcl errors
        # self.after_idle(self.destroy)
        self.after_idle(self.master.on_mod_manager_close)
        # self.mods_model.on_change = None
        # super().destroy()

    # --- Drag and Drop Methods ---
    def _bind_drag_events(self, widget, index):
        """Recursively binds drag-and-drop events to a widget and its children."""
        widget.bind("<ButtonPress-1>", lambda e, i=index: self._on_drag_start(e, i))
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<ButtonRelease-1>", self._on_drop)
        for child in widget.winfo_children():
            self._bind_drag_events(child, index)

    def _on_drag_start(self, event, index):
        self.drag_start_index = index
        self.placeholder = ctk.CTkFrame(self.scroll_frame, height=2, fg_color="yellow")

    def _on_drag_motion(self, event):
        """Updates the placeholder position as the mouse moves."""
        if self.drag_start_index is None or not self.placeholder:
            return

        target_y = self.scroll_frame.winfo_pointery() - self.scroll_frame.winfo_rooty()
        target_index = -1

        for i, frame in enumerate(self.mod_row_frames):
            if frame.winfo_y() < target_y < frame.winfo_y() + frame.winfo_height():
                target_index = i
                break

        if target_index != -1:
            self.placeholder.grid(
                row=target_index + 1, column=0, columnspan=4, sticky="ew"
            )

    def _on_drop(self, event):
        if self.drag_start_index is None or not self.placeholder:
            return

        drop_info = self.placeholder.grid_info()
        self.placeholder.destroy()
        self.placeholder = None

        if not drop_info:
            self.drag_start_index = None
            return

        # +1 for header row, -1 for drop_index being 0-based
        drop_index = drop_info["row"] - 1  # Adjust for header
        start_index = self.drag_start_index

        if start_index != drop_index:
            self.mods_model.move(start_index, drop_index)

        self.drag_start_index = None
