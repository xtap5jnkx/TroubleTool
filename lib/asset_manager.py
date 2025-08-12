import io
import os
import shutil
import zipfile
from typing import Optional

from lxml import etree as et

import lib.ui_logger as logging
from lib.crypt_utils import Crypt
from lib.index_file_helper import IndexFileHelper
from lib.utils import Utils

logging.basicConfig(format="%(levelname)s - %(filename)s:%(lineno)d - %(message)s")


class AssetManager:
    def __init__(self, game_root: str):
        self.root = game_root
        self.package_path = os.path.join(self.root, "Package")
        self.data_path = os.path.join(self.root, "Data")
        self.mods_path = os.path.join(self.root, "Mods")
        self.index_file = os.path.join(self.package_path, "index")
        self.index_file_backup = self.index_file + ".backup"
        self._index_root: Optional[et._Element] = None

        logging.info(f"AssetManager initialized at: {self.root}\n")

    @property
    def index_root(self) -> et._Element:
        if self._index_root is None:
            raise ValueError("Index is empty: Package/index not found or corrupted.")
        return self._index_root

    def _load_index(self):
        # Load Package/index
        # if self.index_root is None:
        self._index_root = et.fromstring(IndexFileHelper.load_index(self.index_file))
        if self._index_root is None:
            raise ValueError("Index is empty: Package/index not found or corrupted.")

        # Save index to Data/index.xml
        data_index_xml_file = os.path.join(self.data_path, "index.xml")
        if not os.path.exists(data_index_xml_file):
            txt = et.tostring(self._index_root, encoding="utf-8", xml_declaration=True)
            os.makedirs(self.data_path, exist_ok=True)
            try:
                with open(data_index_xml_file, "wb") as f:
                    f.write(txt)
            except IOError as e:
                logging.error(f"Error writing: {e}")
                return

        logging.info(f"Loaded index from: {self.index_file}")

    def _save_index(self, mod_index_xml: Optional[et._Element] = None) -> None:
        if mod_index_xml is None:
            mod_index_xml = self._index_root
        if mod_index_xml is None:
            raise ValueError("Index is empty.")

        bstr = et.tostring(mod_index_xml, encoding="utf-8", xml_declaration=True)
        IndexFileHelper.save_index(bstr, self.index_file)

    def _edit_index(self, entry: et._Element, original):
        entry.set("method", "raw")
        entry.set("pack", f"../Data/{original.replace('\\', '/')}")
        # entry.set("pack", os.path.join("..", "Data", original))
        entry.set("virtual", os.path.basename(original))
        size = entry.get("size")
        if size is None:
            size = "0"
        entry.set("csize", size)

    def _extract_entry(self, entry: et._Element):
        """
        Extracts a single asset entry from its package file to the Data directory.
        Returns:
            0 = error
            1 = extracted
            2 = skipped (already up-to-date)
        """
        original = entry.get("original")
        method = entry.get("method")
        pack = entry.get("pack")
        src_path = os.path.join(self.package_path, pack)  # pyright: ignore
        if not os.path.exists(src_path):
            logging.exception(f"Source file not found: {src_path}")
            return 0
        dst_path = os.path.join(self.data_path, original)  # pyright: ignore
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        virtual_name = entry.get("virtual")  # entry folder name in zip

        result = 2
        try:
            if method == "raw":
                if Utils.should_copy(src_path, dst_path):
                    shutil.copy2(src_path, dst_path)
                    result = 1
            elif method == "zip":
                if not virtual_name:
                    logging.error(f"Virtual name not found for entry: {original}")
                    return 0
                with zipfile.ZipFile(src_path, "r") as zf:
                    with zf.open(virtual_name) as zf_member:
                        raw_bytes = zf_member.read()
                if Utils.should_write(raw_bytes, dst_path):
                    result = 1
                    with open(dst_path, "wb") as f:
                        f.write(raw_bytes)
            elif method == "encrypted_zip":
                if not virtual_name:
                    logging.error(f"Virtual name not found for entry: {original}")
                    return 0
                encrypted_data = b""
                with open(src_path, "rb") as f:
                    encrypted_data = f.read()

                decrypted_data = Crypt.decrypt(encrypted_data)

                # Use BytesIO as an in-memory file for ZipFile
                with io.BytesIO(decrypted_data) as stream:
                    with zipfile.ZipFile(stream, "r") as zf:
                        with zf.open(virtual_name) as zf_member:
                            raw_bytes = zf_member.read()
                if Utils.should_write(raw_bytes, dst_path):
                    result = 1
                    with open(dst_path, "wb") as f:
                        f.write(raw_bytes)
            else:
                logging.error(f"Unknown extraction method '{method}': {original}")
                return 0

            self._edit_index(entry, original)
            # self._edit_index_source(entry, original)
            return result

        except FileNotFoundError:
            logging.exception(f"Source file not found during extraction: {src_path}")
        except zipfile.BadZipFile:
            logging.exception(f"Bad zip file for entry {original} at {src_path}")
        except Exception as e:
            logging.exception(f"{e}")
        return 0

    def extract_entries(
        self, original_text: str | set[str], match_mode: str = "prefix"
    ):
        """
        Extract entries from index where 'original' matches a given list or set.
        match_mode: 'prefix' (default) or 'exact'
        """
        if not original_text:
            return
        self._load_index()

        if isinstance(original_text, str):
            targets = {
                os.path.normpath(p.strip()).lower()
                for p in original_text.split(",")
                if p.strip()
            }
        else:
            targets = {os.path.normpath(p).lower() for p in original_text}

        extracted_count = 0
        identical = 0
        index_modified = False

        logging.info("Searching for extract...")

        for entry in self.index_root:
            original = entry.get("original")
            if not original:
                continue

            normalized_original = os.path.normpath(original).lower()

            match = (
                any(normalized_original.startswith(p) for p in targets)
                if match_mode == "prefix"
                else normalized_original in targets
            )

            if not match:
                continue

            # remove from target if exact match
            if match_mode == "exact":
                targets.discard(normalized_original)

            if os.path.basename(entry.get("pack") or "") == os.path.basename(original):
                continue  # already extracted

            result = self._extract_entry(entry)
            if result > 0:
                index_modified = True
                if result == 1:
                    extracted_count += 1
                    logging.info(f"Extracted {original}")
                else:
                    identical += 1
                    logging.debug(f"{original} not changed, skip extract")

            # in exact mode, exit early when done
            if match_mode == "exact" and not targets:
                break

        # Logging summary
        if match_mode == "exact" and targets:
            logging.warning(f"{len(targets)} files not found in index: {targets}")
        if extracted_count == 0:
            logging.info("No files extracted.")
        else:
            logging.info(f"{extracted_count} entries extracted.")

        if index_modified:
            self._save_index(self._index_root)
            if identical > 0:
                logging.info(
                    f"{identical} identical entries skipped; their path updated to 'data'."
                )
