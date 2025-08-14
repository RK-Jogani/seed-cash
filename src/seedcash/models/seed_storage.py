from typing import List
from seedcash.models.seed import Seed, InvalidSeedException
from seedcash.helper import shamir_mnemonic as shamir
import logging

logger = logging.getLogger(__name__)


class SeedStorage:
    def __init__(self) -> None:
        self._mnemonic: List[str] = [None] * 12
        self.slip_mnemonic: List[List[str]] = []
        self.bytes: bytes = b""
        self.groups: list[tuple] = [None]
        self.group_threshold: int = 1
        self.seed: Seed = None

    @property
    def mnemonic(self) -> List[str]:
        # Always return a copy so that the internal List can't be altered
        return list(self._mnemonic)

    @property
    def mnemonic_length(self) -> int:
        return len(self._mnemonic)

    @property
    def bits(self) -> str:
        if not self.bytes:
            raise InvalidSeedException("Bits have not been initialized")
        return bin(int.from_bytes(self.bytes, byteorder="big"))[2:].zfill(
            len(self.bytes) * 8
        )

    @property
    def groups_length(self) -> int:
        return len(self.groups)

    def update_mnemonic(self, word: str, index: int):
        """
        Replaces the nth word in the mnemonic.

        * may specify a negative `index` (e.g. -1 is the last word).
        """
        if index >= len(self._mnemonic):
            raise Exception(f"index {index} is too high")
        self._mnemonic[index] = word

    def get_mnemonic_word(self, index: int) -> str:
        if index < len(self._mnemonic):
            return self._mnemonic[index]
        return None

    def convert_mnemonic_to_seed(self) -> Seed:
        self.seed = Seed(mnemonic=self._mnemonic)
        self.discard_mnemonic()

    def discard_mnemonic(self):
        self._mnemonic = [None] * 12

    def get_seed(self) -> Seed:
        if not self.seed:
            raise InvalidSeedException("Seed has not been initialized")
        return self.seed

    def get_generated_seed(self) -> str:
        if not self._mnemonic:
            raise InvalidSeedException("Mnemonic has not been initialized")
        else:
            logger.info("Generating fingerprint from mnemonic: %s", self._mnemonic)
            mnemonic_seed = Seed(mnemonic=self._mnemonic)
            mnemonic_seed.generate_seed()
            return mnemonic_seed

    def set_mnemonic_length(self, length: int):
        if length not in [12, 15, 18, 20, 21, 24, 33]:
            raise ValueError(
                "Invalid mnemonic length. Must be one of [12, 15, 18, 20, 21, 24, 33]."
            )
        self._mnemonic = [None] * length
        logger.info(f"Mnemonic length set to {length} words.")

    def set_bits(self, bits: str):
        if len(bits) not in [128, 256]:
            raise ValueError("Bits must be either 128 or 256.")
        # Convert str to bytes
        self.bytes = int(bits, 2).to_bytes((len(bits) + 7) // 8, byteorder="big")

    def get_group_at(self, index: int) -> tuple:
        if index >= len(self.groups):
            raise IndexError("Index out of range for groups")
        return self.groups[index]

    def update_groups(self, index: int, group: tuple):
        if not group:
            raise ValueError("Invalid group")
        if group[0] > group[1]:
            raise ValueError("Invalid group")
        if index > len(self.groups):
            raise ("Index is out of group change")
        self.groups[index] = group

    def discard_groups(self):
        self.groups = [None]
        self.group_threshold = 1

    def generate_slip_mnemonic(self):
        self.slip_mnemonic = shamir.generate_mnemonics(
            group_threshold=self.group_threshold,
            groups=self.groups,
            master_secret=self.bytes,
            passphrase=b"",
        )
        logger.info("The Slip mnemonic:", self.slip_mnemonic)
