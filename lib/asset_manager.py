import io
import os
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from lxml import etree as et

import lib.ui_logger as logging
from lib.crypt_utils import Crypt
from lib.index_file_helper import IndexFileHelper
from lib.utils import Utils

Element = et._Element

logging.basicConfig(format="%(levelname)s - %(filename)s:%(lineno)d - %(message)s")
parser = et.XMLParser(collect_ids=False, remove_comments=True)


class ExtractionStatus(Enum):
    """Represents the result of an extraction attempt."""

    ERROR = 0
    EXTRACTED = auto()
    SKIPPED = auto()


class AssetManager:
    def __init__(self, game_root: str):
        self.root = game_root
        self.package_path = os.path.join(self.root, "Package")
        self.data_path = os.path.join(self.root, "Data")
        self.mods_path = os.path.join(self.root, "Mods")
        self.index_file = os.path.join(self.package_path, "index")
        self.index_file_backup = self.index_file + ".backup"
        self._index_root: Optional[Element] = None
        self._extraction_methods: Dict[str, Callable] = {
            "raw": AssetManager._extract_raw,
            "zip": AssetManager._extract_from_zip,
            "encrypted_zip": AssetManager._extract_from_encrypted_zip,
        }

        logging.info(f"AssetManager initialized at: {self.root}\n")

    @property
    def index_root(self) -> Element:
        if self._index_root is None:
            self._load_index()

        return self._index_root  # type: ignore

    def _load_index(self):
        # Load Package/index
        # if self.index_root is None:
        self._index_root = et.fromstring(
            IndexFileHelper.load_index(self.index_file), parser
        )
        if self._index_root is None:
            raise ValueError("Index is empty: Package/index not found or corrupted.")

        # Save a human-readable copy to Data/index.xml for reference
        self._write_xml_to_data_dir(self._index_root)

        logging.info(f"Loaded index from: {self.index_file}")

    def _write_xml_to_data_dir(self, xml_root: Element):
        data_index_xml_file = os.path.join(self.data_path, "index.xml")
        if not os.path.exists(data_index_xml_file):
            txt = et.tostring(xml_root, encoding="utf-8", xml_declaration=True)
            os.makedirs(self.data_path, exist_ok=True)
            try:
                with open(data_index_xml_file, "wb") as f:
                    f.write(txt)
            except IOError as e:
                logging.error(f"Error writing index.xml: {e}")

    def _save_index(self, mod_index_xml: Optional[Element] = None) -> None:
        if mod_index_xml is None:
            mod_index_xml = self._index_root
        if mod_index_xml is None:
            raise ValueError("Index is empty.")

        source_bytes = et.tostring(
            mod_index_xml, encoding="utf-8", xml_declaration=True
        )
        IndexFileHelper.save_index(source_bytes, self.index_file)

    @staticmethod
    def _edit_index(entry: Element, original: str):
        entry.set("method", "raw")
        entry.set("pack", f"../Data/{original.replace('\\', '/')}")
        # entry.set("pack", os.path.join("..", "Data", original))
        entry.set("virtual", os.path.basename(original))
        size = entry.get("size", "0")
        entry.set("csize", size)

    @staticmethod
    def _extract_raw(src_path: str, dst_path: str, **_):
        if Utils.should_copy(src_path, dst_path):
            shutil.copy2(src_path, dst_path)
            return ExtractionStatus.EXTRACTED
        return ExtractionStatus.SKIPPED

    @staticmethod
    def _extract_from_zip(src_path: str, dst_path: str, entry: Element, original: str):
        virtual_name = entry.get("virtual")
        if not virtual_name:
            logging.error(f"Virtual name not found for entry: {original}")
            return ExtractionStatus.ERROR

        with zipfile.ZipFile(src_path, "r") as zf:
            raw_bytes = zf.read(virtual_name)

        if Utils.should_write(raw_bytes, dst_path):
            with open(dst_path, "wb") as f:
                f.write(raw_bytes)
            return ExtractionStatus.EXTRACTED

        return ExtractionStatus.SKIPPED

    @staticmethod
    def _extract_from_encrypted_zip(
        src_path: str, dst_path: str, entry: Element, original: str
    ):
        virtual_name = entry.get("virtual")
        if not virtual_name:
            logging.error(f"Virtual name not found for entry: {original}")
            return ExtractionStatus.ERROR

        with open(src_path, "rb") as f:
            encrypted_data = f.read()

        decrypted_data = Crypt.decrypt(encrypted_data)

        with io.BytesIO(decrypted_data) as stream:
            with zipfile.ZipFile(stream, "r") as zf:
                raw_bytes = zf.read(virtual_name)

        if Utils.should_write(raw_bytes, dst_path):
            with open(dst_path, "wb") as f:
                f.write(raw_bytes)
            return ExtractionStatus.EXTRACTED

        return ExtractionStatus.SKIPPED

    def _extract_entry(self, entry: Element, original: str, pack: str):
        method = entry.get("method")
        if method is None:
            logging.error(f"Method not found for entry: {original}")
            return ExtractionStatus.ERROR

        handler = self._extraction_methods.get(method)
        if handler is None:
            logging.error(f"Unknown extraction method '{method}' for entry: {original}")
            return ExtractionStatus.ERROR

        src_path = os.path.join(self.package_path, pack)
        if not os.path.exists(src_path):
            logging.exception(f"Source file not found: {src_path}")
            return ExtractionStatus.ERROR

        dst_path = os.path.join(self.data_path, original)
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        try:
            result = handler(src_path, dst_path, entry=entry, original=original)
            if result != ExtractionStatus.ERROR:
                self._edit_index(entry, original)
            return result

        except (FileNotFoundError, zipfile.BadZipFile, KeyError) as e:
            logging.exception(f"Failed to extract {original} from {src_path}: {e}")
        except Exception as e:
            logging.exception(f"{original} catch an unknown error: {e}")

        return ExtractionStatus.ERROR

    def extract_entries(
        self, original_text: Union[str, Set[str]], match_mode: str = "prefix"
    ):
        """
        Extract entries from index where 'original' matches a given list or set.
        match_mode: 'prefix' (default) or 'exact'
        """
        self._load_index()

        if isinstance(original_text, str):
            targets = {
                p.strip().replace("\\", "/")
                # os.path.normpath(p.strip()).lower()
                for p in original_text.split(",")
                if p.strip()
            }
        else:
            targets = {p.replace("\\", "/") for p in original_text}
            # targets = {os.path.normpath(p).lower() for p in original_text}

        if not targets:
            return

        logging.info("Searching for extract...")
        entries_to_extract: List[Tuple[Element, str, str]] = []

        counters = {status: 0 for status in ExtractionStatus}
        index_modified = False

        for entry in self.index_root:
            original = entry.get("original")
            if original is None:
                continue

            pack = entry.get("pack")
            if pack is None:
                continue

            # normalized_original = os.path.normpath(original).lower()
            normalized_original = original.replace("\\", "/")

            if os.path.basename(pack) == os.path.basename(original):
                if normalized_original in targets:
                    logging.debug(f"{original} already extracted")
                continue  # already extracted

            match = (
                any(normalized_original.startswith(p) for p in targets)
                if match_mode == "prefix"
                else normalized_original in targets
            )

            if not match:
                continue

            if match_mode == "exact":
                targets.discard(normalized_original)

            entries_to_extract.append((entry, original, pack))

            # # no multithreading version
            # status = self._extract_entry(entry, original, pack)
            # if status != ExtractionStatus.ERROR:
            #     counters[status] += 1
            #     index_modified = True
            #     if status == ExtractionStatus.EXTRACTED:
            #         logging.info(f"Extracted {original}")
            #     else:
            #         logging.debug(f"{original} not changed, path updated")

            # in exact mode, exit early when done
            if match_mode == "exact" and not targets:
                break

        with ThreadPoolExecutor() as executor:
            futures = {
                # *item: unpack the tuple
                executor.submit(self._extract_entry, *item): item[1]
                for item in entries_to_extract
            }
            for future in as_completed(futures):
                original = futures[future]
                status = future.result()
                if status != ExtractionStatus.ERROR:
                    counters[status] += 1
                    index_modified = True
                    if status == ExtractionStatus.EXTRACTED:
                        logging.info(f"Extracted {original}")
                    else:
                        logging.debug(f"{original} not changed, path updated")

        extracted_count = counters[ExtractionStatus.EXTRACTED]
        identical = counters[ExtractionStatus.SKIPPED]

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
