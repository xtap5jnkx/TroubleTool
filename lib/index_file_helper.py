import os, io, zipfile

from lib.crypt_utils import Crypt
import lib.ui_logger as logging


class IndexFileHelper:
    """
    Helper class for loading and saving XML index files, handling encryption,
    decryption, and optional ZIP compression/decompression.
    """

    # Class-level variable to store if the last loaded index was zipped.
    # This mimics the static 'zipped' variable in the C# original.
    _was_zipped_on_load: bool = False

    @classmethod
    def load_index(cls, file_path: str):
        """
        Loads an XML index file from the given path.
        It decrypts the file, checks for ZIP compression, decompresses if necessary,
        removes null padding

        Args:
            file_path (str): The path to the XML index file.

        Returns:
            bytearray: The decrypted and unpadded XML data.

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file content is invalid or malformed
            zipfile.BadZipFile: If it's detected as a zip but is corrupted
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Index file not found: {file_path}")

        raw_data: bytes = b""
        try:
            with open(file_path, "rb") as f:
                raw_data = f.read()
        except IOError as e:
            raise IOError(f"Error reading file {file_path}: {e}")

        # Decrypt the data first
        decrypted_data = Crypt.decrypt(raw_data)

        # Check for ZIP magic bytes (PK\x03\x04) at the beginning
        # C# checks len > 2 and data[0] == 0x50 and data[1] == 0x4b.
        # A full ZIP magic number is 0x50 0x4B 0x03 0x04.
        if len(decrypted_data) >= 4 and decrypted_data[:4] == b"PK\x03\x04":
            cls._was_zipped_on_load = True
            logging.debug(
                f"File {file_path} detected as zipped, decompressing 'index' entry..."
            )
            try:
                # Use BytesIO to treat the decrypted data as a file in memory
                with io.BytesIO(decrypted_data) as stream:
                    with zipfile.ZipFile(stream, "r") as zf:
                        # GetEntry("index") is equivalent to zf.open("index")
                        # You can also use zf.read("index") to get content directly.
                        if "index" in zf.namelist():
                            xml_bytes = zf.read("index")
                        else:
                            raise ValueError(
                                f"Zip archive {file_path} does not contain an 'index' entry."
                            )
            except zipfile.BadZipFile as e:
                raise zipfile.BadZipFile(
                    f"Error decompressing zip file {file_path}: {e}"
                )
            except Exception as e:  # Catch other potential errors during zip processing
                raise ValueError(
                    f"An unexpected error occurred during zip processing for {file_path}: {e}"
                )
        else:
            cls._was_zipped_on_load = False
            xml_bytes = decrypted_data

        return Crypt.unpad(xml_bytes)

    @classmethod
    def save_index(cls, data_to_encrypt: bytes, file_path: str, zipped=False):
        """
        Saves bytes to the specified file path.
        Applies padding, optionally zips it, encrypts, and then writes to file.

        Args:
            data_to_encrypt (bytes): The bytes to save.
            file_path (str): The path where the XML file will be saved.
        """
        if not zipped and cls._was_zipped_on_load:
            zipped = cls._was_zipped_on_load

        data_to_encrypt = Crypt.pad(data_to_encrypt)
        # Conditionally zip the data if the original file was zipped
        if zipped:
            with io.BytesIO() as stream_zip:
                # 'w' mode for writing, ZIP_DEFLATED for compression
                with zipfile.ZipFile(
                    stream_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=False
                ) as zf:
                    # 'index' is the entry name inside the zip
                    zf.writestr("index", data_to_encrypt)
                data_to_encrypt = stream_zip.getvalue()

        encrypted_data = Crypt.encrypt(data_to_encrypt)

        try:
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
        except IOError as e:
            raise IOError(f"Error writing to file {file_path}: {e}")
        logging.info(f"Index saved successfully to: {file_path}")
