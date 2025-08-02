import hashlib
import hmac
import os

from base58 import b58decode, b58encode

from ecdsa import SECP256k1, SigningKey, VerifyingKey
from ecdsa.util import string_to_number, number_to_string
from seedcash.gui.components import load_txt

import logging

logger = logging.getLogger(__name__)


class BitcoinFunctions:

    @staticmethod
    def sha256(data):
        return hashlib.sha256(data).digest()

    @staticmethod
    def hmac_sha512(key, data):
        return hmac.new(key, data, hashlib.sha512).digest()

    @staticmethod
    def hash160(pubkey):
        sha256_hash = hashlib.sha256(pubkey).digest()
        ripemd160_hash = hashlib.new("ripemd160", sha256_hash).digest()
        return ripemd160_hash

    @staticmethod
    def convert_bits(data, from_bits, to_bits, pad=True):
        acc = 0
        bits = 0
        ret = []
        maxv = (1 << to_bits) - 1  # Màxim valor per un bloc de to_bits
        for value in data:
            acc = (acc << from_bits) | value  # Afegeix el nou valor
            bits += from_bits
            while bits >= to_bits:
                bits -= to_bits
                ret.append((acc >> bits) & maxv)  # Extreu el bloc de to_bits
        if pad and bits:
            ret.append((acc << (to_bits - bits)) & maxv)  # Completa el bloc restant
        return ret

    @staticmethod
    def polymod(values):
        c = 1
        for d in values:
            c0 = c >> 35
            c = ((c & 0x07FFFFFFFF) << 5) ^ d
            if c0 & 0x01:
                c ^= 0x98F2BC8E61
            if c0 & 0x02:
                c ^= 0x79B76D99E2
            if c0 & 0x04:
                c ^= 0xF33E5FB3C4
            if c0 & 0x08:
                c ^= 0xAE2EABE2A8
            if c0 & 0x10:
                c ^= 0x1E4F43E470
        return c ^ 1

    @staticmethod
    def encode_base32(data):
        CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        return "".join([CHARSET[d] for d in data])

    @staticmethod
    def dictionary_BIP39():
        """Llegim el diccionari Bip39"""

        list39 = load_txt("bip39.txt")
        return list39

    @staticmethod
    def binmnemonic_to_mnemonic(bin_mnemonic):
        list39 = BitcoinFunctions.dictionary_BIP39()
        n = len(bin_mnemonic)
        mnemonic = []
        index = []
        for i in range(0, n, 11):
            block = bin_mnemonic[i : i + 11]
            index_word = int(block, 2)
            index.append(index_word)
        for index_word in index:
            word = list39[index_word]
            mnemonic.append(word)
        return mnemonic

    # calculate the last word with bits
    @staticmethod
    def get_mnemonic(incomplete_mnemonic, last_bits):
        logger.info(
            "Generating mnemonic from incomplete mnemonic: %s and last bits: %s",
            incomplete_mnemonic,
            last_bits,
        )
        string_mnemonic = " ".join(incomplete_mnemonic)

        logger.info("String mnemonic: %s", string_mnemonic)

        list39 = BitcoinFunctions.dictionary_BIP39()
        list_mnemonic = string_mnemonic.strip().split()

        list_index_bi = [
            bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic
        ]
        first_bits = "".join(list_index_bi)
        initial_bits = first_bits + last_bits

        decimal_incomplet_mnemonic = int(initial_bits, 2)
        hexa_incomplet_mnemonic = hex(decimal_incomplet_mnemonic)[2:].zfill(
            (len(initial_bits) + 7) // 8 * 2
        )
        byte_incomplet_mnemonic = bytes.fromhex(hexa_incomplet_mnemonic)

        hash_object = hashlib.sha256()
        hash_object.update(byte_incomplet_mnemonic)
        hexa_hashmnemonic = hash_object.hexdigest()
        bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

        checksum = bin_hashmnemonic[:4]

        bits_mnemonic = initial_bits + checksum
        mnemonic = BitcoinFunctions.binmnemonic_to_mnemonic(bits_mnemonic)
        print("The mnemonic:", mnemonic)
        return mnemonic

    @staticmethod
    def seed_generator(seed, passphrase):
        """mnemonic + passprhrase --> seed   (512bits=64bytes)"""

        # Convertim a bytes els inputs
        mnemonic_bytes = seed.encode("utf-8")
        passphrase_bytes = passphrase.encode("utf-8")

        # PBKDF2
        algorithm = "sha512"
        salt_bytes = b"mnemonic" + passphrase_bytes
        iterations = 2048
        key_length = 64

        bytes_seed = hashlib.pbkdf2_hmac(
            algorithm, mnemonic_bytes, salt_bytes, iterations, key_length
        )
        hexa_final_seed = bytes_seed.hex()
        return hexa_final_seed

    @staticmethod
    def get_private_and_code(seed):
        """Genera la clave privada maestra y el código de cadena a partir de una semilla en hexadecimal"""
        hmac_hash = hmac.new(
            b"Bitcoin seed", bytes.fromhex(seed), hashlib.sha512
        ).digest()
        private_master_key = hmac_hash[:32]
        private_master_code = hmac_hash[32:]
        return private_master_key, private_master_code

    @staticmethod
    def public_master_key_compressed_generaitor(private_master_key_bytes):
        """Partin duna clau privada mestre en format bytes,
        retorna una clau publica en format comprimida en bytes"""

        sk = SigningKey.from_string(private_master_key_bytes, curve=SECP256k1)
        vk = sk.verifying_key
        public_key_compressed = vk.to_string("compressed")
        return public_key_compressed

    @staticmethod
    def fingerprint_bytes(compressed_master_public_key_bytes):
        """Donada una compressed_master_public_key_bytes retorna un master fingerprint en hexadecimal"""

        sha256_hash = hashlib.sha256(compressed_master_public_key_bytes).digest()
        ripemd160 = hashlib.new("ripemd160")
        ripemd160.update(sha256_hash)
        fingerprint = ripemd160.digest()[:4]
        return fingerprint

    @staticmethod
    def child_key_hardened(parent_key, parent_chain_code, index, hardened=False):
        curve_order = SECP256k1.order
        if hardened:
            index |= 0x80000000
        index_bytes = index.to_bytes(4, "big")
        data = b"\x00" + parent_key + index_bytes
        I = BitcoinFunctions.hmac_sha512(parent_chain_code, data)

        Il = I[:32]
        chain_code = I[32:]

        number_Il = string_to_number(Il)
        number_parent = string_to_number(parent_key)
        number_derived = (number_Il + number_parent) % curve_order

        derivet_key = number_to_string(number_derived, curve_order)

        return derivet_key, chain_code

    @staticmethod
    def derivation_m_44_145_0(hexa_seed):
        # Donada una seed trobem privat key i chain code (m/)
        private_master_key, private_master_code = BitcoinFunctions.get_private_and_code(
            hexa_seed
        )

        # Derivem amb index 44'   m/ a m/44' de forma endurida i optenim una child_key i un child_chain_code,
        purpose_index = 44
        purpose_key, purpose_chain_code = BitcoinFunctions.child_key_hardened(
            private_master_key, private_master_code, purpose_index, hardened=True
        )

        # Derivem amb index 0'   m/ a m/44'/145' de forma endurida i optenim una child_key i un child_chain_code,
        coin_type_index = 145
        coin_type_key, coin_type_chain_code = BitcoinFunctions.child_key_hardened(
            purpose_key, purpose_chain_code, coin_type_index, hardened=True
        )

        # Derivem amb index 0'   m/ a m/44/145'/0' de forma endurida i optenim una child_key i un child_chain_code,
        account_index = 0
        account_key, account_chain_code = BitcoinFunctions.child_key_hardened(
            coin_type_key, coin_type_chain_code, account_index, hardened=True
        )
        account_public_key = BitcoinFunctions.public_master_key_compressed_generaitor(
            account_key
        )

        # Retornem tambe variables comunes i nessesaries en xpriv i xpub:
        # Depth
        depth = 3
        depth = depth.to_bytes(1, byteorder="big")

        # finerprint del pare
        father_acount_publickey = (
            BitcoinFunctions.public_master_key_compressed_generaitor(coin_type_key)
        )
        father_fingerprint = BitcoinFunctions.fingerprint_bytes(father_acount_publickey)

        # child_index
        child_index = 0 | 0x80000000
        child_index = child_index.to_bytes(4, byteorder="big")

        return (
            depth,
            father_fingerprint,
            child_index,
            account_chain_code,
            account_key,
            account_public_key,
        )

    @staticmethod
    def xpriv_encode(
        depth, father_fingerprint, child_index, account_chain_code, account_key
    ):
        version = b"\x04\x88\xad\xe4"  # xpriv
        data = (
            version
            + depth
            + father_fingerprint
            + child_index
            + account_chain_code
            + b"\x00"
            + account_key
        )
        checksum = BitcoinFunctions.sha256(BitcoinFunctions.sha256(data))[:4]

        return b58encode(data + checksum).decode("utf-8")

    @staticmethod
    def xpub_encode(
        depth, father_fingerprint, child_index, account_chain_code, account_public_key
    ):
        version = b"\x04\x88\xb2\x1e"  # xpub
        data = (
            version
            + depth
            + father_fingerprint
            + child_index
            + account_chain_code
            + account_public_key
        )
        checksum = BitcoinFunctions.sha256(BitcoinFunctions.sha256(data))[:4]

        return b58encode(data + checksum).decode("utf-8")

    @staticmethod
    def fingerprint_hex(hexa_seed):
        """Donada una compressed_master_public_key_bytes retorna un master fingerprint en hexadecimal"""

        (
            depth,
            father_fingerprint,
            child_index,
            account_chain_code,
            account_key,
            account_public_key,
        ) = BitcoinFunctions.derivation_m_44_145_0(hexa_seed)

        sk = SigningKey.from_string(account_key, curve=SECP256k1)
        vk = sk.verifying_key
        public_key_compressed = vk.to_string(
            "compressed"
        )  # clau publica mestre comprimida en hexadecimal

        sha256_hash = hashlib.sha256(public_key_compressed).digest()
        ripemd160 = hashlib.new("ripemd160")
        ripemd160.update(sha256_hash)
        fingerprint = ripemd160.digest()[:4]
        return fingerprint.hex()

    @staticmethod
    def xpub_decode(xpub):
        """De xpub en base 58 a components en bytes"""

        xpub_bytes = b58decode(xpub)

        version = xpub_bytes[:4]
        depth = xpub_bytes[4:5]
        fingerprint = xpub_bytes[5:9]
        child_number = xpub_bytes[9:13]
        chain_code = xpub_bytes[13:45]
        public_key = xpub_bytes[45:-4]

        return version, depth, fingerprint, child_number, chain_code, public_key

    @staticmethod
    def derive_public_child_key(parent_public_key_bytes, parent_chain_code, index):
        """Variables parent en bytes, index en int"""

        curve = SECP256k1.curve
        generator = SECP256k1.generator
        order = generator.order()

        data = parent_public_key_bytes + index.to_bytes(4, "big")
        I = hmac.new(parent_chain_code, data, hashlib.sha512).digest()
        IL, IR = I[:32], I[32:]

        IL_int = int.from_bytes(IL, "big")  # Convertir IL a un enter
        if IL_int >= order:
            raise ValueError()

        parent_public_key = VerifyingKey.from_string(
            parent_public_key_bytes, curve=SECP256k1
        )  # Obtenir el punt públic de la clau parent

        child_point = (
            generator * IL_int + parent_public_key.pubkey.point
        )  # Calcular el nou punt de la corba (IL * G + ParentPublicKey)

        child_public_key_bytes = VerifyingKey.from_public_point(
            child_point, curve=SECP256k1
        ).to_string(
            "compressed"
        )  # Convertir el punt resultant a bytes utilitzant VerifyingKey

        child_chain_code = IR

        return child_public_key_bytes, child_chain_code

    # Legacy address generator
    @staticmethod
    def public_key_to_legacy_address(public_key_bytes):

        # SHA-256 hash
        sha256 = hashlib.sha256(public_key_bytes).digest()

        # RIPEMD-160 hash
        ripemd160 = hashlib.new("ripemd160")
        ripemd160.update(sha256)
        ripemd160_hash = ripemd160.digest()

        # Add version byte (0x00 for Bitcoin addresses)
        versioned_hash = b"\x00" + ripemd160_hash

        # Compute checksum
        checksum = hashlib.sha256(hashlib.sha256(versioned_hash).digest()).digest()[:4]

        # Create final address
        address_bytes = versioned_hash + checksum
        bitcoin_address = b58encode(address_bytes).decode("utf-8")

        return bitcoin_address

    @staticmethod
    def xpub_to_legacy_address(xpub, address_index):

        (
            version,
            depth,
            fingerprint,
            child_number,
            chain_code_chain,
            public_key_chain,
        ) = BitcoinFunctions.xpub_decode(
            xpub
        )  # m/44'/145'/0'

        child_public_chain, child_chain_chain = (
            BitcoinFunctions.derive_public_child_key(
                public_key_chain, chain_code_chain, 0
            )
        )  # m/44'/145'/0'/0
        child_public_address_index, child_chain_address_index = (
            BitcoinFunctions.derive_public_child_key(
                child_public_chain, child_chain_chain, address_index
            )
        )  # m/44'/0'/0'/0/0
        address = BitcoinFunctions.public_key_to_legacy_address(
            child_public_address_index
        )

        return address

    # Cashaddr address generator
    @staticmethod
    def create_checksum(prefix, payload):
        values = [ord(x) & 0x1F for x in prefix] + [0] + payload
        polymod_result = BitcoinFunctions.polymod(values + [0, 0, 0, 0, 0, 0, 0, 0])
        return [(polymod_result >> (5 * (7 - i))) & 0x1F for i in range(8)]

    @staticmethod
    def public_key_to_cashaddr_address(pubkey):
        version_byte = 0x00  # Per P2PKH
        payload = bytes([version_byte]) + BitcoinFunctions.hash160(pubkey)
        payload_5bit = BitcoinFunctions.convert_bits(payload, 8, 5)
        checksum = BitcoinFunctions.create_checksum("bitcoincash", payload_5bit)
        address = "bitcoincash:" + BitcoinFunctions.encode_base32(
            payload_5bit + checksum
        )
        return address

    @staticmethod
    def xpub_to_cashaddr_address(xpub, address_index):

        (
            version,
            depth,
            fingerprint,
            child_number,
            chain_code_chain,
            public_key_chain,
        ) = BitcoinFunctions.xpub_decode(
            xpub
        )  # m/44'/145'/0'

        child_public_chain, child_chain_chain = (
            BitcoinFunctions.derive_public_child_key(
                public_key_chain, chain_code_chain, 0
            )
        )  # m/44'/145'/0'/0
        child_public_address_index, child_chain_address_index = (
            BitcoinFunctions.derive_public_child_key(
                child_public_chain, child_chain_chain, address_index
            )
        )  # m/44'/145'/0'/0/0
        address = BitcoinFunctions.public_key_to_cashaddr_address(
            child_public_address_index
        )
        return address

    @staticmethod
    def generate_random_seed():
        """
        Generate a random 12-word BIP39 mnemonic seed using OS random bits.

        Returns:
            list: List of 12 mnemonic words
        """
        # Generate 128 bits (16 bytes) of entropy for 12-word seed
        entropy_bits = 128
        entropy_bytes_count = entropy_bits // 8  # 16 bytes

        # Generate random entropy using os.urandom (cryptographically secure)
        entropy_bytes = os.urandom(entropy_bytes_count)

        # Convert bytes to binary string
        entropy_binary = "".join(format(byte, "08b") for byte in entropy_bytes)

        # Calculate SHA256 hash for checksum
        hash_object = hashlib.sha256()
        hash_object.update(entropy_bytes)
        hash_hex = hash_object.hexdigest()
        hash_binary = bin(int(hash_hex, 16))[2:].zfill(256)

        # Get first 4 bits as checksum for 12-word seed
        checksum = hash_binary[:4]

        # Combine entropy and checksum (128 + 4 = 132 bits total)
        full_binary = entropy_binary + checksum

        # Convert to mnemonic words using existing function
        mnemonic = BitcoinFunctions.binmnemonic_to_mnemonic(full_binary)

        logger.info("Generated 12-word mnemonic with 128 bits of entropy")

        return mnemonic


# # This update aims to implement support for 15 18 21 and 24 words. You will find the backend below.
# # As for the UI, we will treat it in parts. First, let's see what modifications will be needed to
# #  load seed. Load seed now starts with a view of two labels. Delete both please. This view is gona
# #  be totalyy diferent. This view will be a view with one label of "Choose the length of your mnemonic phrase"
# # and under it a boxes (WACH THE IMAGE 1 PLEASE) with the options 12, 15, 18, 21 and 24. Also a return and
# #  continue button. Make that 12 words is the default one.
# # After this the following view is the keyboard for introduce the word1. We have to add the 15, 18, 21 and 24 views.. obiusly
# #  After all entrys we have to use g2_confirmatio in function of the number of words. g2_confirmation_12words, g2_confirmation_15words ...
# # i call it g2_confirmation_n_words for do it similar to origial bf but change it how you want
# #After confirmat mnemonic generate_seed must create the seed. We can use same generate_seed function cause is generic.
# #After generate seed (hexa_seed) we can forget about if the orignal mnemonic was 12, 15... cause it is not important. So all the code of load seed is done.


# #Now lets work in generate seed. When you click generate seed now you look a random seed button and calculate 12 words seed.

# #Firts of all change "calculate 12 words seed." for ": "Calculate 12th word"

# #This firts view will have 6 buttons: (use Calc if calculate is to long)
# # 1)Random seed
# # 2)Calculate 12th word
# # 3)Calculate 15th word
# # 4)Calculate 18th word
# # 5)Calculate 21th word
# # 6)Calculate 24th word

# #If you click random seed is not gonna show the firts 4 words of the mnemonic. Now is gona show a new view
# # like IMAGE 1 for chose the leng of the mnemonic. After select the lenng and click to continu then yes, it will chose the randmly mnemonic.
# # created. Like now, in groups of 4 words.

# #The backend for all of this is below.  Please ask me what you want to know. Maybe it has errors
# #I review the code and it seems to be correct.


# def g2_confirmation_12words(self):
#         list39=bf.dictionary_BIP39()
#         list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in self.g2_mnemonic]
#         bin_mnemonic = "".join(list_index_bi)

#         n = len(bin_mnemonic)
#         checksum = bin_mnemonic[-4:]

#         #Conversio bin-bytes
#         decimal_mnemonic = int(bin_mnemonic[:-4], 2)
#         hexa_mnemonic = hex(decimal_mnemonic)[2:].zfill((n - 4) // 4)
#         if len(hexa_mnemonic) % 2 != 0: # Ens assegurem que la longitud hexadecimal sigui múltiple de 2
#             hexa_mnemonic = '0' + hexa_mnemonic

#         byte_mnemonic = bytes.fromhex(hexa_mnemonic)

#         #Hash i conversio a binari
#         hash_object = hashlib.sha256()
#         hash_object.update(byte_mnemonic)
#         hexa_hashmnemonic = hash_object.hexdigest()
#         bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

#         checksum_revised = bin_hashmnemonic[:4]

#         if checksum == checksum_revised:
#             return self.show_frame(self.g2_2)


#         if not checksum == checksum_revised:
#             self.g2_word_entry.delete(0, 'end')
#             self.g2_label_1.configure(text="")
#             self.g2_label_2.configure(text="You have introduced a invalid seed, please try again")
#             self.g2_counter=0
#             self.show_frame(self.g2)

# def g2_confirmation_15words(self):
#         list39=bf.dictionary_BIP39()
#         list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in self.g2_mnemonic] #mnemonic of 15 words
#         bin_mnemonic = "".join(list_index_bi)

#         n = len(bin_mnemonic)

#         checksum = bin_mnemonic[-5:] #5 bits de checksum

#         #Conversio bin-bytes
#         decimal_mnemonic = int(bin_mnemonic[:-5], 2)
#         hexa_mnemonic = hex(decimal_mnemonic)[2:].zfill((n - 5) // 4)
#         if len(hexa_mnemonic) % 2 != 0: # Ens assegurem que la longitud hexadecimal sigui múltiple de 2
#             hexa_mnemonic = '0' + hexa_mnemonic
#         byte_mnemonic = bytes.fromhex(hexa_mnemonic)

#         #Hash i conversio a binari
#         hash_object = hashlib.sha256()
#         hash_object.update(byte_mnemonic)
#         hexa_hashmnemonic = hash_object.hexdigest()
#         bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

#         checksum_revised = bin_hashmnemonic[:5] #5 bits de checksum

#         if checksum == checksum_revised:
#             return self.show_frame(self.g2_2)


#         if not checksum == checksum_revised:
#             self.g2_word_entry.delete(0, 'end')
#             self.g2_label_1.configure(text="")
#             self.g2_label_2.configure(text="You have introduced a invalid seed, please try again")
#             self.g2_counter=0
#             self.show_frame(self.g2)


# def g2_confirmation_18words(self):
#         list39=bf.dictionary_BIP39()
#         list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in self.g2_mnemonic] #mnemonic of 18words
#         bin_mnemonic = "".join(list_index_bi)

#         n = len(bin_mnemonic)

#         checksum = bin_mnemonic[-6:] #6 bits de checksum

#         #Conversio bin-bytes
#         decimal_mnemonic = int(bin_mnemonic[:-6], 2)
#         hexa_mnemonic = hex(decimal_mnemonic)[2:].zfill((n - 6) // 4)
#         if len(hexa_mnemonic) % 2 != 0: # Ens assegurem que la longitud hexadecimal sigui múltiple de 2
#             hexa_mnemonic = '0' + hexa_mnemonic
#         byte_mnemonic = bytes.fromhex(hexa_mnemonic)

#         #Hash i conversio a binari
#         hash_object = hashlib.sha256()
#         hash_object.update(byte_mnemonic)
#         hexa_hashmnemonic = hash_object.hexdigest()
#         bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

#         checksum_revised = bin_hashmnemonic[:6]

#         if checksum == checksum_revised:
#             return self.show_frame(self.g2_2)


#         if not checksum == checksum_revised:
#             self.g2_word_entry.delete(0, 'end')
#             self.g2_label_1.configure(text="")
#             self.g2_label_2.configure(text="You have introduced a invalid seed, please try again")
#             self.g2_counter=0
#             self.show_frame(self.g2)


# def g2_confirmation_21words(self):
#         list39=bf.dictionary_BIP39()
#         list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in self.g2_mnemonic] #mnemonic of 21words
#         bin_mnemonic = "".join(list_index_bi)

#         n = len(bin_mnemonic)

#         checksum = bin_mnemonic[-7:] #7 bits de checksum

#         #Conversio bin-bytes
#         decimal_mnemonic = int(bin_mnemonic[:-7], 2)
#         hexa_mnemonic = hex(decimal_mnemonic)[2:].zfill((n - 7) // 4)
#         if len(hexa_mnemonic) % 2 != 0: # Ens assegurem que la longitud hexadecimal sigui múltiple de 2
#             hexa_mnemonic = '0' + hexa_mnemonic
#         byte_mnemonic = bytes.fromhex(hexa_mnemonic)

#         #Hash i conversio a binari
#         hash_object = hashlib.sha256()
#         hash_object.update(byte_mnemonic)
#         hexa_hashmnemonic = hash_object.hexdigest()
#         bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

#         checksum_revised = bin_hashmnemonic[:7]

#         if checksum == checksum_revised:
#             return self.show_frame(self.g2_2)


#         if not checksum == checksum_revised:
#             self.g2_word_entry.delete(0, 'end')
#             self.g2_label_1.configure(text="")
#             self.g2_label_2.configure(text="You have introduced a invalid seed, please try again")
#             self.g2_counter=0
#             self.show_frame(self.g2)


# def g2_confirmation_24words(self):
#         list39=bf.dictionary_BIP39()
#         list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in self.g2_mnemonic] #mnemonic of 24words
#         bin_mnemonic = "".join(list_index_bi)

#         n = len(bin_mnemonic)

#         checksum = bin_mnemonic[-8:] #8 bits de checksum

#         #Conversio bin-bytes
#         decimal_mnemonic = int(bin_mnemonic[:-8], 2)
#         hexa_mnemonic = hex(decimal_mnemonic)[2:].zfill((n - 8) // 4)
#         if len(hexa_mnemonic) % 2 != 0: # Ens assegurem que la longitud hexadecimal sigui múltiple de 2
#             hexa_mnemonic = '0' + hexa_mnemonic
#         byte_mnemonic = bytes.fromhex(hexa_mnemonic)

#         #Hash i conversio a binari
#         hash_object = hashlib.sha256()
#         hash_object.update(byte_mnemonic)
#         hexa_hashmnemonic = hash_object.hexdigest()
#         bin_hashmnemonic = bin(int(hexa_hashmnemonic, 16))[2:].zfill(256)

#         checksum_revised = bin_hashmnemonic[:8]

#         if checksum == checksum_revised:
#             return self.show_frame(self.g2_2)


#         if not checksum == checksum_revised:
#             self.g2_word_entry.delete(0, 'end')
#             self.g2_label_1.configure(text="")
#             self.g2_label_2.configure(text="You have introduced a invalid seed, please try again")
#             self.g2_counter=0
#             self.show_frame(self.g2)


# #After verify the mnemonic, we need to generate the seed and the private key.
# #The seed is generated using the mnemonic and the passphrase.
# #The private key is generated using the seed.
# #In this case nothing change in the implementation of the seed generation and the private key generation.
# #The only change is the number of words in the mnemonic. but we dont have to change nothing cause is the
# #variable that we use who change (mnemonic string)

# def seed_generator(seed,passphrase):
#     """ mnemonic + passprhrase --> seed   (512bits=64bytes)"""

#     #This functions should calll (mnemonic,passphrase) instead of (seed,passphrase) cause
#     # calle seed to passphrase might be confusing. Better dont touch it.. just for you to know

#     #as you see, this function is generic.  cause it does not take in consideration the number of words.
#     #It just take the mnemonic and the passphrase (indiferent of the number of words) and generate the seed.

#     #Convertim a bytes els inputs
#     mnemonic_bytes = seed.encode('utf-8')
#     passphrase_bytes = passphrase.encode('utf-8')

#     #PBKDF2
#     algorithm="sha512"
#     salt_bytes = b"mnemonic" + passphrase_bytes
#     iterations = 2048
#     key_length = 64

#     bytes_seed=hashlib.pbkdf2_hmac(algorithm,mnemonic_bytes,salt_bytes,iterations,key_length)
#     hexa_final_seed=bytes_seed.hex()
#     return hexa_final_seed

# def get_private_and_code(seed):
#     """Genera la clave privada maestra y el código de cadena a partir de una semilla en hexadecimal"""
#     hmac_hash = hmac.new(b'Bitcoin seed', bytes.fromhex(seed), hashlib.sha512).digest()
#     private_master_key = hmac_hash[:32]
#     private_master_code = hmac_hash[32:]
#     return private_master_key, private_master_code


# #With this  we have the backend of load seed menu with the inplementations of 12,15,18,21 and 24 words.
# #Now we need to implement the backend of generate seed menu.


# #def get_mnemonic(incomplete_mnemonic,last_bits):

# #    string_mnemonic = ' '.join(incomplete_mnemonic)
# #    list39=dictionary_BIP39()
# #    list_mnemonic = string_mnemonic.strip().split()
# #    list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
# #    first_bits = "".join(list_index_bi)
# #    initial_bits = first_bits + last_bits

# #    decimal_incomplet_mnemonic=int(initial_bits,2)
# #    hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2) #WE DO NOTneed to change this cause is generic
# #    byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

# #    hash_object=hashlib.sha256()
# #    hash_object.update(byte_incomplet_mnemonic)
# #    hexa_hashmnemonic=hash_object.hexdigest()
# #    bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

# #    checksum=bin_hashmnemonic[:4] #WE need to change this in the case of 12,15,18,21 and 24 words

# #    bits_mnemonic= initial_bits + checksum
# #    mnemonic=binmnemonic_to_mnemonic(bits_mnemonic)
# #    return mnemonic


# #take in consideration that "last bits" in funcition of number of words should be..

# #| Words | Last bits                  | Checksum   |
# #|-------|--------------------------|----------------|
# #| 12    | 7                        | 4              |
# #| 15    | 6                        | 5              |
# #| 18    | 5                        | 6              |
# #| 21    | 4                        | 7              |
# #| 24    | 3                        | 8              |

# #and this would effect the function get_bits or how you call it


# def submit_bits(self):
#     bits = self.bits_entry.get()
#     if all(bit in "01" for bit in bits) and len(bits) == 7: #WE NEED TO CHANGE THIS FOR THE NUMBER OF WORDS
#         self.word_entry.delete(0, 'end')
#         self.bits=bits
#         self.bits_entry.delete(0, 'end')
#         self.show_frame(self.g1_3)
#     else:
#         self.g1_2_label_1.configure(text="Introduce correctamente una secuencia de siete 0 y 1")
#         self.bits_entry.delete(0, 'end')


# #we have to take in consideration also that function binmnemonic_to_mnemonic should be changed in the case of 12,15,18,21 and 24 words.

# #def binmnemonic_to_mnemonic(bin_mnemonic):
# #    list39=dictionary_BIP39()
# #    n=len(bin_mnemonic)
# #    mnemonic=[]
# #    index=[]
# #    for i in range(0,n, 11):
# #        block=bin_mnemonic[i:i+11]
# #        index_word=int(block,2)
# #        index.append(index_word)
# #    for index_word in index:
# #        word=list39[index_word]
# #        mnemonic.append(word)
# #    return mnemonic

# #the final version would be:
# #take in consideration that the number of words is the number of bits(of complete mnemonic) divided by 11.
# def binmnemonic_to_mnemonic_n_words(bin_mnemonic):
#     list39=dictionary_BIP39()
#     n=len(bin_mnemonic)
#     number_of_words=n//11
#     mnemonic=[]
#     index=[]
#     for i in range(0,n, number_of_words-1):
#         block=bin_mnemonic[i:i+11]
#         index_word=int(block,2)
#         index.append(index_word)
#     for index_word in index:
#         word=list39[index_word]
#         mnemonic.append(word)
#     return mnemonic


# # RETURNING TO get_mnemonic function. THAT WE DIDNT CHANGE.
# #WE NEED TO CHANGE THE FUNCTION TO TAKE IN CONSIDERATION THE NUMBER OF WORDS.

# #def get_mnemonic(incomplete_mnemonic,last_bits):

# #    string_mnemonic = ' '.join(incomplete_mnemonic)
# #    list39=dictionary_BIP39()
# #    list_mnemonic = string_mnemonic.strip().split()
# #    list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
# #    first_bits = "".join(list_index_bi)
# #    initial_bits = first_bits + last_bits

# #    decimal_incomplet_mnemonic=int(initial_bits,2)
# #    hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2) #WE do NOT need to change this cause is a generic expresion
# #    byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

# #    hash_object=hashlib.sha256()
# #    hash_object.update(byte_incomplet_mnemonic)
# #    hexa_hashmnemonic=hash_object.hexdigest()
# #    bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

# #    checksum=bin_hashmnemonic[:4] #WE need to change this in the case of 12,15,18,21 and 24 words

# #    bits_mnemonic= initial_bits + checksum
# #    mnemonic=binmnemonic_to_mnemonic(bits_mnemonic)
# #    return mnemonic

# #so the final version would be:

# def get_mnemonic_12_words(incomplete_mnemonic,last_bits):

#     string_mnemonic = ' '.join(incomplete_mnemonic)
#     list39=dictionary_BIP39()
#     list_mnemonic = string_mnemonic.strip().split()
#     list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
#     first_bits = "".join(list_index_bi)
#     initial_bits = first_bits + last_bits

#     decimal_incomplet_mnemonic=int(initial_bits,2)
#     hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2) #WE do NOT need to change this cause is a generic expresion
#     byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

#     hash_object=hashlib.sha256()
#     hash_object.update(byte_incomplet_mnemonic)
#     hexa_hashmnemonic=hash_object.hexdigest()
#     bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

#     checksum=bin_hashmnemonic[:4] # 4 bits of checksum for 12 words

#     bits_mnemonic= initial_bits + checksum
#     mnemonic=binmnemonic_to_mnemonic_n_words(bits_mnemonic)
#     return mnemonic

# def get_mnemonic_15_words(incomplete_mnemonic,last_bits):

#     string_mnemonic = ' '.join(incomplete_mnemonic)
#     list39=dictionary_BIP39()
#     list_mnemonic = string_mnemonic.strip().split()
#     list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
#     first_bits = "".join(list_index_bi)
#     initial_bits = first_bits + last_bits

#     decimal_incomplet_mnemonic=int(initial_bits,2)
#     hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2)
#     byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

#     hash_object=hashlib.sha256()
#     hash_object.update(byte_incomplet_mnemonic)
#     hexa_hashmnemonic=hash_object.hexdigest()
#     bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

#     checksum=bin_hashmnemonic[:5] # 5 bits of checksum for 15 words

#     bits_mnemonic= initial_bits + checksum
#     mnemonic=binmnemonic_to_mnemonic_n_words(bits_mnemonic)
#     return mnemonic

# def get_mnemonic_18_words(incomplete_mnemonic,last_bits):

#     string_mnemonic = ' '.join(incomplete_mnemonic)
#     list39=dictionary_BIP39()
#     list_mnemonic = string_mnemonic.strip().split()
#     list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
#     first_bits = "".join(list_index_bi)
#     initial_bits = first_bits + last_bits

#     decimal_incomplet_mnemonic=int(initial_bits,2)
#     hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2)
#     byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

#     hash_object=hashlib.sha256()
#     hash_object.update(byte_incomplet_mnemonic)
#     hexa_hashmnemonic=hash_object.hexdigest()
#     bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

#     checksum=bin_hashmnemonic[:6] # 6 bits of checksum for 18 words

#     bits_mnemonic= initial_bits + checksum
#     mnemonic=binmnemonic_to_mnemonic_n_words(bits_mnemonic)
#     return mnemonic

# def get_mnemonic_21_words(incomplete_mnemonic,last_bits):

#     string_mnemonic = ' '.join(incomplete_mnemonic)
#     list39=dictionary_BIP39()
#     list_mnemonic = string_mnemonic.strip().split()
#     list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
#     first_bits = "".join(list_index_bi)
#     initial_bits = first_bits + last_bits

#     decimal_incomplet_mnemonic=int(initial_bits,2)
#     hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2)
#     byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

#     hash_object=hashlib.sha256()
#     hash_object.update(byte_incomplet_mnemonic)
#     hexa_hashmnemonic=hash_object.hexdigest()
#     bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

#     checksum=bin_hashmnemonic[:7] # 7 bits of checksum for 21 words

#     bits_mnemonic= initial_bits + checksum
#     mnemonic=binmnemonic_to_mnemonic_n_words(bits_mnemonic)
#     return mnemonic

# def get_mnemonic_24_words(incomplete_mnemonic,last_bits):

#     string_mnemonic = ' '.join(incomplete_mnemonic)
#     list39=dictionary_BIP39()
#     list_mnemonic = string_mnemonic.strip().split()
#     list_index_bi = [bin(list39.index(word))[2:].zfill(11) for word in list_mnemonic]
#     first_bits = "".join(list_index_bi)
#     initial_bits = first_bits + last_bits

#     decimal_incomplet_mnemonic=int(initial_bits,2)
#     hexa_incomplet_mnemonic=hex(decimal_incomplet_mnemonic)[2:].zfill((len(initial_bits) + 7) // 8 * 2)
#     byte_incomplet_mnemonic=bytes.fromhex(hexa_incomplet_mnemonic)

#     hash_object=hashlib.sha256()
#     hash_object.update(byte_incomplet_mnemonic)
#     hexa_hashmnemonic=hash_object.hexdigest()
#     bin_hashmnemonic=bin(int(hexa_hashmnemonic,16))[2:].zfill(256)

#     checksum=bin_hashmnemonic[:8] # 8 bits of checksum for 24 words

#     bits_mnemonic= initial_bits + checksum
#     mnemonic=binmnemonic_to_mnemonic_n_words(bits_mnemonic)
#     return mnemonic
