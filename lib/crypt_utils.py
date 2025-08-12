from typing import Final

from cryptography.hazmat.backends import default_backend  # type: ignore
from cryptography.hazmat.primitives import padding  # type: ignore
from cryptography.hazmat.primitives.ciphers import (  # type: ignore
    Cipher,
    algorithms,
    modes,
)


class Crypt:
    """
    Implements AES encryption and decryption using a custom key and IV generation
    logic, mirroring the C# original, using the cryptography library.
    The key and IV are generated once as class attributes for efficiency.
    """

    _KEY_INIT: Final[str] = "d4152d461ab5308429e49774a042a318"
    _IV_INIT: Final[str] = "86afc43868fea6abd40fbf6d5ed50905"
    # Generate key and IV once when the class is defined
    _AES_KEY: bytes = b""  # Placeholder for type hinting
    _AES_IV: bytes = b""  # Placeholder for type hinting

    @staticmethod
    def _generate_key(a1):
        key = bytearray(16)

        r9_1 = len(a1)
        rax1 = len(a1)

        if rax1 == 16:
            ebx5 = 0
            if r9_1 > 0:
                r11_6 = 0
                while True:
                    dl7 = a1[r11_6]
                    r8_7 = a1[ebx5 + 1]

                    if (dl7 & 0x40) != 0:
                        if (dl7 & 0x20) != 0:
                            al9 = dl7 - 87
                        else:
                            al9 = dl7 - 55
                    else:
                        al9 = dl7 - 48

                    if (r8_7 & 0x40) != 0:
                        if (r8_7 & 0x20) != 0:
                            cl14 = r8_7 - 87
                        else:
                            cl14 = r8_7 - 55
                    else:
                        cl14 = r8_7 - 48

                    ebx5 += 2
                    rax1 = cl14 | (16 * al9)
                    key[r11_6 >> 1] = rax1 & 0xFF  # Equivalent to (byte)rax1
                    r11_6 = ebx5

                    if ebx5 >= r9_1:
                        break

        return bytes(key)

    @staticmethod
    def _generate_iv(word):
        # word = bytes.fromhex(word)
        if isinstance(word, str):
            word = word.encode("utf-8")  # ord() is for single char
        iv = bytearray(16)
        v4 = 0
        v5 = 0

        while v4 < 0x20:
            v6 = word[v5]
            v7 = word[v4 + 1]

            if (v6 & 0x40) != 0:
                if (v6 & 0x20) != 0:
                    v8 = v6 - 87
                else:
                    v8 = v6 - 55
            else:
                v8 = v6 - 48

            if (v7 & 0x40) != 0:
                if (v7 & 0x20) != 0:
                    v9 = v7 - 87
                else:
                    v9 = v7 - 55
            else:
                v9 = v7 - 48

            iv[v5 >> 1] = v9 | (16 * v8)
            v4 += 2
            v5 = v4

        return bytes(iv)

    _AES_KEY = _generate_key(_KEY_INIT)
    _AES_IV = _generate_iv(_IV_INIT)

    @staticmethod
    def encrypt(plaintext: bytes) -> bytes:
        """
        Encrypts the given plaintext using AES in CBC mode with PKCS7 padding.
        Uses the pre-generated class-level key and IV.

        Args:
            plaintext (bytes): The data to be encrypted. This data is expected
                               to have already been padded with null bytes to a
                               multiple of 16 bytes by the caller (e.g., IndexHelper).

        Returns:
            bytes: The encrypted ciphertext.
        """
        # Create a new Cipher object for each encryption operation.
        # This is crucial for maintaining proper cryptographic state.
        cipher = Cipher(
            algorithms.AES(Crypt._AES_KEY),
            modes.CBC(Crypt._AES_IV),
            backend=default_backend(),
        )
        encryptor = cipher.encryptor()

        # Apply PKCS7 padding.
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_plaintext = padder.update(plaintext) + padder.finalize()

        # Encrypt the padded data
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

        return ciphertext

    @staticmethod
    def decrypt(ciphertext: bytes) -> bytes:
        """
        Decrypts the given ciphertext using AES in CBC mode.
        Uses the pre-generated class-level key and IV.
        It removes PKCS7 padding.

        Args:
            ciphertext (bytes): The data to be decrypted.

        Returns:
            bytes: The decrypted plaintext. Note: This plaintext will still
                   contain the original null padding added by the C# IndexHelper,
                   which should be stripped by the caller (IndexFileHelper).
        """
        # Create a new Cipher object for each decryption operation.
        cipher = Cipher(
            algorithms.AES(Crypt._AES_KEY),
            modes.CBC(Crypt._AES_IV),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()

        # Decrypt the ciphertext
        decrypted_padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # logging.debug(f"Decrypted data length: {len(decrypted_data)} bytes")
        return decrypted_padded_data

        # Unpad the data using PKCS7.
        # try:
        #     unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        #     decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
        # except ValueError as e:
        #     raise ValueError(f"Error unpadding decrypted data (PKCS7): {e}. Data might be corrupted or key/IV is incorrect.")

    @staticmethod
    def pad(data: bytes) -> bytes:
        """
        Pads the given data with null bytes to a multiple of 16 bytes.
        This is a simple wrapper around the PKCS7 padding function.

        Args:
            data (bytes): The data to be padded.

        Returns:
            bytes: The padded data.
        """
        # Apply padding to make length a multiple of 16 (for encryption block size)
        pad_length = 16 - (len(data) % 16)
        if (
            pad_length != 16
        ):  # If current_length is already a multiple of 16, no padding
            data += b"\0" * pad_length
        return data

    @staticmethod
    def unpad(xml_bytes: bytes) -> bytearray:
        """
        Unpads the given data using PKCS7 padding.
        This is a simple wrapper around the PKCS7 unpadding function.

        Args:
            data (bytes): The data to be unpadded.

        Returns:
            str: The padded data.
        """
        i = len(xml_bytes) - 1
        data = bytearray(xml_bytes)  # Convert to bytearray for mutability
        while i >= 0 and data[i] == 0:
            data[i] = ord(" ")
            i -= 1
        return data

    # @staticmethod
    # def decrypt_use_dll(data: bytes) -> bytes:
    #     if troublecrypt_library is None:
    #         raise ValueError("TroubleCrypt library not loaded.")
    #     try:
    #         troublecrypt_library.decrypt(data, len(data))
    #         return data
    #     except Exception as e:
    #         raise Exception(f"Error loading TroubleCrypt library: {e}")


# import os, sys, ctypes
# from typing import Optional, Any
#
# TroubleCryptLibrary = Any
#
#
# def load_troublecrypt_library(
#     library_name: str = "troublecrypt.dll",
# ) -> Optional[TroubleCryptLibrary]:
#     """
#     Loads the TroubleCrypt library from a specified file path,
#     handling different operating systems.
#
#     Args:
#         library_name (str): The name of the library file to load.
#                             Defaults to "troublecrypt.dll".
#
#     Returns:
#         Optional[TroubleCryptLibrary]: The loaded ctypes library object, or None if loading fails.
#     """
#     script_dir = os.path.dirname(os.path.realpath(__file__))
#     library_path = os.path.join(script_dir, library_name)
#
#     _dll: Optional[TroubleCryptLibrary] = None
#
#     try:
#         # Check the operating system and use the appropriate ctypes function
#         if sys.platform.startswith("win"):
#             # On Windows, use WinDLL
#             print(f"Loading '{library_path}' using ctypes.WinDLL...")
#             _dll = ctypes.WinDLL(library_path)
#         elif sys.platform.startswith("darwin"):
#             # On macOS, use CDLL
#             print(f"Loading '{library_path}' using ctypes.CDLL...")
#             _dll = ctypes.CDLL(library_path)
#         elif sys.platform.startswith("linux"):
#             # On Linux, use CDLL
#             print(f"Loading '{library_path}' using ctypes.CDLL...")
#             _dll = ctypes.CDLL(library_path)
#         else:
#             print(
#                 f"Warning: Unsupported operating system '{sys.platform}'. Skipping library load."
#             )
#     except (OSError, AttributeError) as e:
#         print(f"Error: Failed to load library at '{library_path}'. Reason: {e}")
#         # The function will return None on failure
#
#     return _dll
#
#
# # --- Example Usage ---
# # Use better variable names for clarity, like 'troublecrypt_library'
# troublecrypt_library = load_troublecrypt_library()
#
# if troublecrypt_library:
#     print("TroubleCrypt library loaded successfully.")
#     # You can now call functions from the library, e.g.:
#     # troublecrypt_library.some_function(...)
# else:
#     print("Failed to load the TroubleCrypt library.")
