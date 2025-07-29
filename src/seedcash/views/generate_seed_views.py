import logging

from gettext import gettext as _
from seedcash.models.btc_functions import BitcoinFunctions as bf
from seedcash.gui.components import SeedCashIconsConstants
from seedcash.gui.screens import RET_CODE__BACK_BUTTON
from seedcash.gui.screens.screen import ButtonOption
from seedcash.models.seed import Seed
from seedcash.views.view import (
    View,
    Destination,
    BackStackView,
)


logger = logging.getLogger(__name__)

"""**************************************************
Seed Cash Updated Code
**************************************************"""


# First Generate Seed View
class SeedCashGenerateSeedView(View):
    RANDOM_SEED = ButtonOption("Random Seed")
    TWELVE_WORDS_SEED = ButtonOption("Calculate 12 Words Seed")

    def run(self):
        from seedcash.gui.screens.generate_seed_screens import (
            SeedCashGenerateSeedScreen,
        )

        button_data = [self.RANDOM_SEED, self.TWELVE_WORDS_SEED]

        selected_menu_num = self.run_screen(
            SeedCashGenerateSeedScreen,
            title="Generate Seed",
            button_data=button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == self.TWELVE_WORDS_SEED:
            from seedcash.views.load_seed_views import SeedMnemonicEntryView

            return Destination(
                SeedMnemonicEntryView, view_args=dict(is_calc_final_word=True)
            )
        elif button_data[selected_menu_num] == self.RANDOM_SEED:

            return Destination(SeedCashGenerateSeedRandomView)

        return Destination(BackStackView)


class SeedCashGenerateSeedRandomView(View):
    def run(self):
        # Generate a random mnemonic
        mnemonic = bf.generate_random_seed()
        from seedcash.views.generate_seed_views import ShowWordsView

        return Destination(ShowWordsView, view_args={"mnemonic": mnemonic})


class ShowWordsView(View):
    def __init__(self, mnemonic: list = None):
        super().__init__()
        if mnemonic:
            self.controller.storage._mnemonic = mnemonic

        self.mnemonic = self.controller.storage.mnemonic

    def run(self):
        from seedcash.gui.screens.load_seed_screens import SeedCashSeedWordsScreen

        confirm = self.run_screen(
            SeedCashSeedWordsScreen,
            seed_words=self.mnemonic,
        )

        if confirm == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        elif confirm == "CONFIRM":
            from seedcash.views.load_seed_views import SeedFinalizeView

            return Destination(
                SeedFinalizeView,
                view_args={"seed": self.controller.storage.get_generated_seed()},
            )


class ToolsCalcFinalWordCoinFlipsView(View):
    def run(self):
        from seedcash.gui.screens.generate_seed_screens import ToolsCoinFlipEntryScreen

        mnemonic_length = len(self.controller.storage._mnemonic)

        total_flips = 7

        ret_val = ToolsCoinFlipEntryScreen(
            return_after_n_chars=total_flips,
        ).display()

        if ret_val == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        else:
            return Destination(
                ToolsCalcFinalWordShowFinalWordView, view_args=dict(coin_flips=ret_val)
            )


class ToolsCalcFinalWordShowFinalWordView(View):
    CONFIRM = ButtonOption("Confirm")

    def __init__(self, coin_flips: str = None):
        super().__init__()

        wordlist = Seed.get_wordlist()
        # Prep the user's selected word / coin flips and the actual final word for
        # the display.

        self.selected_final_word = None
        self.selected_final_bits = coin_flips

        final_mnemonic = bf.get_mnemonic(
            self.controller.storage._mnemonic[:-1], coin_flips
        )

        # Update our pending mnemonic with the real final word
        self.controller.storage.update_mnemonic(final_mnemonic[-1], -1)

        mnemonic = self.controller.storage._mnemonic
        mnemonic_length = len(mnemonic)

        # And grab the actual final word's checksum bits
        self.actual_final_word = self.controller.storage._mnemonic[-1]
        num_checksum_bits = 4 if mnemonic_length == 12 else 8
        self.checksum_bits = format(wordlist.index(self.actual_final_word), "011b")[
            -num_checksum_bits:
        ]

    def run(self):
        from seedcash.gui.screens.generate_seed_screens import ToolsCalcFinalWordScreen

        button_data = [self.CONFIRM]

        # TRANSLATOR_NOTE: label to calculate the last word of a BIP-39 mnemonic seed phrase
        title = _("Final Word Calc")

        selected_menu_num = self.run_screen(
            ToolsCalcFinalWordScreen,
            button_data=button_data,
            selected_final_word=self.selected_final_word,
            selected_final_bits=self.selected_final_bits,
            checksum_bits=self.checksum_bits,
            actual_final_word=self.actual_final_word,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        elif button_data[selected_menu_num] == self.CONFIRM:
            return Destination(ShowWordsView)


class ToolsCalcFinalWordDoneView(View):
    FINISH = ButtonOption("Finish")
    PASSPHRASE = ButtonOption("Add Passphrase")

    def run(self):
        from seedcash.gui.screens.generate_seed_screens import (
            ToolsCalcFinalWordDoneScreen,
        )

        final_word = self.controller.storage.get_mnemonic_word(-1)
        generated_seed = self.controller.storage.get_generated_seed()

        button_data = [self.FINISH, self.PASSPHRASE]

        selected_menu_num = ToolsCalcFinalWordDoneScreen(
            final_word=final_word,
            fingerprint=generated_seed.fingerprint,
            button_data=button_data,
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        if button_data[selected_menu_num] == self.FINISH:
            from seedcash.views.view import MainMenuView

            # Discard the mnemonic and seed after generating the final word
            self.controller.storage.discard_mnemonic()
            self.controller.discard_seed()

            return Destination(MainMenuView)

        elif button_data[selected_menu_num] == self.PASSPHRASE:
            from seedcash.views.load_seed_views import SeedAddPassphraseView

            return Destination(
                SeedAddPassphraseView, view_args={"seed": generated_seed}
            )
