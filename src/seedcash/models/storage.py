from typing import List
from seedcash.models.wallet import Wallet
from seedcash.models.seed import Seed, InvalidSeedException
from seedcash.models.scheme import Scheme, SchemeParameters
from seedcash.models.settings import Settings
from seedcash.models.settings_definition import SettingsConstants
import logging
from seedcash.gui.components import load_txt

logger = logging.getLogger(__name__)


class SeedStorage:
    def __init__(self) -> None:
        self._mnemonic: List[str] = None
        self.scheme_params: SchemeParameters = None
        self.passphrase: str = ""
        self.scheme: Scheme = None
        self.seed: Seed = None

        self.wallet: Wallet = None

    @property
    def get_wordlist(self) -> List[str]:
        # getting world list from resource/bip39.txt
        if (
            Settings.get_instance().get_value(SettingsConstants.SETTING__SEED_PROTOCOL)
            == "BIP39"
        ):
            list39 = load_txt("bip39.txt")
        elif (
            Settings.get_instance().get_value(SettingsConstants.SETTING__SEED_PROTOCOL)
            == "SLIP39"
        ):
            list39 = load_txt("slip39.txt")

        return list39

    @property
    def _wallet(self) -> Wallet:
        if not self.wallet:
            raise InvalidSeedException("Wallet has not been initialized")
        return self.wallet

    def create_wallet(self):
        if (
            Settings.get_instance().get_value(SettingsConstants.SETTING__SEED_PROTOCOL)
            == "BIP39"
        ):
            if not self.seed:
                raise InvalidSeedException("Seed must be initialized for BIP39.")
            self.seed.generate_wallet()
            self.wallet = self.seed._wallet
        elif (
            Settings.get_instance().get_value(SettingsConstants.SETTING__SEED_PROTOCOL)
            == "SLIP39"
        ):
            if not self.scheme:
                raise InvalidSeedException("Scheme must be initialized for SLIP39.")
            self.scheme.generate_wallet()
            self.wallet = self.scheme._wallet

    def discard_wallet(self):
        """
        Discard the current wallet.
        """
        self.wallet = None
        logger.info("Wallet discarded.")

    # Mnemonic management
    @property
    def mnemonic(self) -> List[str]:
        # Always return a copy so that the internal List can't be altered
        return list(self._mnemonic)

    @property
    def mnemonic_length(self) -> int:
        return len(self._mnemonic)

    def set_mnemonic_length(self, length: int):
        if length not in [12, 15, 18, 20, 21, 24, 33]:
            raise ValueError(
                "Invalid mnemonic length. Must be one of [12, 15, 18, 20, 21, 24, 33]."
            )
        self._mnemonic = [None] * length
        logger.info(f"Mnemonic length set to {length} words.")

    def get_mnemonic_word(self, index: int) -> str:
        if index < len(self._mnemonic):
            return self._mnemonic[index]
        return None

    def update_mnemonic(self, word: str, index: int):
        """
        Replaces the nth word in the mnemonic.

        * may specify a negative `index` (e.g. -1 is the last word).
        """
        if index >= len(self._mnemonic):
            raise Exception(f"index {index} is too high")
        self._mnemonic[index] = word

    def discard_mnemonic(self):
        self._mnemonic = None

    # Seed management
    @property
    def _seed(self) -> Seed:
        if not self.seed:
            raise InvalidSeedException("Seed has not been initialized")
        return self.seed

    def convert_mnemonic_to_seed(self) -> Seed:
        self.seed = Seed(mnemonic=self._mnemonic)
        self.discard_mnemonic()

    def get_generated_seed(self) -> str:
        if not self._mnemonic:
            raise InvalidSeedException("Mnemonic has not been initialized")
        else:
            logger.info("Generating fingerprint from mnemonic: %s", self._mnemonic)
            mnemonic_seed = Seed(mnemonic=self._mnemonic)
            mnemonic_seed.generate_wallet()
            return mnemonic_seed

    # Scheme management

    @property
    def _scheme(self) -> Scheme:
        if not self.scheme:
            raise InvalidSeedException("Scheme has not been initialized")
        return self.scheme

    def set_scheme_params(self, bits: str):
        """
        Set the scheme parameters for the current seed.
        """
        if not bits:
            raise InvalidSeedException("Bits must be provided to set scheme parameters")

        self.scheme_params = SchemeParameters(bits=bits)
        logger.info("Scheme parameters set with bits: %s", bits)

    def generate_scheme_with_params(self):
        """
        Generate a scheme based on the current mnemonic and scheme parameters.
        """
        if not self.scheme_params:
            raise InvalidSeedException("Scheme parameters have not been set")

        self.scheme = Scheme(
            scheme_parameters=self.scheme_params,
        )
        self.scheme.generate_mnemonics()
        self.scheme.generate_wallet()
        logger.info("Scheme generated with parameters: %s", self.scheme_params)

    def add_share_to_scheme(self):
        """
        Generate a scheme based on the current mnemonic.
        """
        if not self._mnemonic:
            raise InvalidSeedException("Mnemonic has not been initialized")

        if not self.scheme:
            try:
                self.scheme = Scheme(
                    mnemonics=self._mnemonic,
                )
            except Exception as e:
                raise InvalidSeedException(
                    "Invalid mnemonic provided for scheme creation"
                ) from e

            self.discard_mnemonic()
            logger.info("New scheme created with the current mnemonic.")
            return

        if self.scheme.scheme_parameters:
            raise InvalidSeedException("Scheme generated with parameters already")

        self.scheme.add_share(self._mnemonic)
        self.discard_mnemonic()
        logger.info("Share added to the current scheme.")

    def discard_scheme(self):
        """
        Discard the current scheme.
        """
        self.scheme = None
        self.scheme_params = None
        logger.info("Scheme and parameters discarded.")
