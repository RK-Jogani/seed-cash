import logging

from gettext import gettext as _
from seedcash.gui.screens.load_seed_screens import SeedMnemonicEntryScreen
from seedcash.gui.screens.screen import (
    RET_CODE__BACK_BUTTON,
    RET_CODE__CHECK_BUTTON,
    DireWarningScreen,
)

from seedcash.views.view import (
    BackStackView,
    View,
    Destination,
    ButtonOption,
    MainMenuView,
)
from seedcash.views.load_seed_views import (
    SeedFinalizeView,
    SeedMnemonicInvalidView,
)

from seedcash.models.btc_functions import BitcoinFunctions as bf
from seedcash.gui.screens.slip_screens import (
    GroupShareListScreen,
    VisualLoadedSchemeScreen,
)

logger = logging.getLogger(__name__)


# For Loading Slip39 Seed Views
# groups = shamir.decode_mnemonics
class SeedSlipMnemonicEntryView(View):
    """
    View for entering a Slip39 seed phrase.
    """

    def __init__(self, cur_word_index: int = 0):
        super().__init__()
        # counter
        self.cur_word_index = cur_word_index
        # getting the index
        self.cur_word = self.controller.storage.get_mnemonic_word(cur_word_index)
        # for the generation of seed

    def run(self):
        ret = self.run_screen(
            SeedMnemonicEntryScreen,
            # TRANSLATOR_NOTE: Inserts the word number (e.g. "Seed Word #6")
            title=_("Seed Word #{}").format(
                self.cur_word_index + 1
            ),  # Human-readable 1-indexing!
            initial_letters=list(self.cur_word) if self.cur_word else ["a"],
            wordlist=self.controller.storage.get_wordlist,
        )

        if ret == RET_CODE__BACK_BUTTON:
            # remove the cur_word
            self.controller.storage.update_mnemonic(None, self.cur_word_index)

            if (
                self.cur_word_index == 0
                and self.controller.storage.mnemonic
                != [None] * self.controller.storage.mnemonic_length
            ):
                return Destination(SeedMnemonicInvalidView, skip_current_view=True)

            return Destination(BackStackView)

        # ret will be our new mnemonic word
        self.controller.storage.update_mnemonic(ret, self.cur_word_index)

        if self.cur_word_index < (self.controller.storage.mnemonic_length - 1):
            return Destination(
                SeedSlipMnemonicEntryView,
                view_args={
                    "cur_word_index": self.cur_word_index + 1,
                },
            )
        else:
            # Display the seed words for confirmation
            from seedcash.gui.screens.load_seed_screens import SeedCashSeedWordsScreen

            confirm = self.run_screen(
                SeedCashSeedWordsScreen,
                seed_words=self.controller.storage._mnemonic,
            )

            if confirm == "CONFIRM":
                # User confirmed the seed words
                try:
                    self.controller.storage.add_share_to_scheme()

                except Exception as e:
                    for i in range(self.controller.storage.mnemonic_length):
                        self.controller.back_stack.pop()

                    return Destination(SeedMnemonicInvalidView)

                return Destination(VisualLoadedSchemeView)


class VisualLoadedSchemeView(View):
    """
    View to display the loaded scheme.
    """

    def run(self):
        """
        Run the view to display the loaded scheme.
        """

        # Display the seed words for confirmation
        self.run_screen(
            VisualLoadedSchemeScreen,
        )

        # Finalize the seed generation
        return Destination(SeedFinalizeView)


# For Generating Slip39 Seed Views
class SeedSlipEntryView(View):
    """
    View for entering a Slip39 seed phrase.
    """

    def __init__(self):
        super().__init__()
        num_words = self.controller.storage.mnemonic_length

        if num_words == 20:
            self.bits = 128
        elif num_words == 33:
            self.bits = 256
        else:
            raise ValueError("Unsupported number of words for Slip39 seed phrase.")

    def run(self):
        """
        Run the view to enter the Slip39 seed phrase.
        """
        from seedcash.gui.screens.slip_screens import SlipEntryScreen

        ret = self.run_screen(SlipEntryScreen, bits=self.bits)

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if len(ret) == 128 or len(ret) == 256:
            from seedcash.views.slip_views import SeedSlipBitsView

            self.controller.storage.set_scheme_params(ret)
            return Destination(SeedSlipBitsView)


class SeedSlipBitsView(View):
    """
    View for entering a Slip39 seed phrase in bits.
    """

    def __init__(self, is_random_seed: bool = False):
        super().__init__()

        if is_random_seed:
            self.bits = bf.get_random_bits_for_slip(
                self.controller.storage.mnemonic_length
            )

            self.controller.storage.set_scheme_params(self.bits)

        self.bits = self.controller.storage.scheme_params._bits

    def run(self):
        """
        Run the view to enter the Slip39 seed phrase in bits.
        """
        from seedcash.gui.screens.slip_screens import SlipBitsScreen

        ret = self.run_screen(SlipBitsScreen, bits=self.bits)

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if ret == "CONFIRM":
            return Destination(SeedSlipSchemeView)


class SeedSlipSchemeView(View):
    """
    View for displaying the Slip39 group scheme.
    """

    SINGLE_LEVEL = ButtonOption("Single Level Backup")
    TWO_LEVEL = ButtonOption("Two Level Backup")

    def __init__(self):
        super().__init__()

        self.button_data = [
            self.SINGLE_LEVEL,
            self.TWO_LEVEL,
        ]

    def run(self):
        """
        Run the view to display the Slip39 group scheme.
        """

        selected_menu_num = self.run_screen(
            GroupShareListScreen,
            button_data=self.button_data,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        elif self.button_data[selected_menu_num] == self.SINGLE_LEVEL:
            return Destination(VisualSharesView, view_args={"is_single_level": True})
        elif self.button_data[selected_menu_num] == self.TWO_LEVEL:
            return Destination(VisualGroupView)


class VisualGroupView(View):
    """
    View for visualizing the groups in a Slip39 scheme.
    """

    def __init__(self):
        super().__init__()
        self.groups = self.controller.storage.scheme_params._groups_length
        self.group_threshold = self.controller.storage.scheme_params._group_threshold

    def run(self):
        """
        Run the view to visualize the groups.
        """
        from seedcash.gui.screens.slip_screens import VisualGroupShareScreen

        # Show the visual group share screen
        result = self.run_screen(
            VisualGroupShareScreen,
            text="Groups",
            threshold=self.group_threshold,
            total_members=self.groups,
        )

        if result == RET_CODE__BACK_BUTTON:
            return Destination(DiscardGroupsView, skip_current_view=True)

        self.controller.storage.scheme_params.set_group_threshold(result[0])
        self.controller.storage.scheme_params.set_groups_length(result[1])

        return Destination(ListOfGroupsView)


class ListOfGroupsView(View):
    """
    View to display the list of groups.
    """

    def __init__(self, is_view_mode: bool = False):
        super().__init__()
        self.is_view_mode = is_view_mode
        self.fingerprint: str = None

        self.groups = self.controller.storage.scheme_params._groups_length

        # create button options for each group
        self.button_data = [ButtonOption(f"Group {i + 1}") for i in range(self.groups)]

        if self.controller.storage.scheme:
            self.fingerprint = self.controller.storage._scheme._wallet.fingerprint

    def run(self):
        """
        Run the view to display the list of groups.
        """
        ret = self.run_screen(
            GroupShareListScreen,
            title=("Groups"),
            fingerprint=self.fingerprint,
            show_back_button=not self.is_view_mode,
            show_check_button=self.is_view_mode,
            button_data=self.button_data,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if ret == RET_CODE__CHECK_BUTTON:
            # If in view mode, finalize the groups
            if self.is_view_mode:
                self.controller.storage.discard_scheme()
                return Destination(MainMenuView)

            # If not in view mode, proceed to share generation
            return Destination(VisualSharesView, view_args={"group_index": 0})

        if self.is_view_mode:
            return Destination(ListOfSharesView, view_args={"group_index": ret})

        return Destination(VisualSharesView, view_args={"group_index": ret})


class VisualSharesView(View):
    threshold = 1
    total_members = 1

    def __init__(self, group_index=0, is_single_level=False):
        super().__init__()
        self.group_index = group_index
        self.is_single_level = is_single_level

        self.group = self.controller.storage.scheme_params.get_group_at(
            self.group_index
        )

        if self.group:
            self.threshold = self.group[0]
            self.total_members = self.group[1]

    def run(self):
        from seedcash.gui.screens.slip_screens import VisualGroupShareScreen

        result = self.run_screen(
            VisualGroupShareScreen,
            text="Shares",
            threshold=self.threshold,
            total_members=self.total_members,
        )

        if result == RET_CODE__BACK_BUTTON:
            return Destination(
                DiscardSharesView,
                view_args={
                    "group_index": self.group_index,
                    "is_single_level": self.is_single_level,
                },
                skip_current_view=True,
            )

        self.controller.storage.scheme_params.update_groups(self.group_index, result)

        if self.is_single_level:
            self.controller.storage.generate_scheme_with_params()
            return Destination(
                ListOfSharesView, view_args={"group_index": 0, "is_single_level": True}
            )

        if self.controller.storage.scheme_params.scheme_is_complete():
            self.controller.storage.generate_scheme_with_params()
            return Destination(ListOfGroupsView, view_args={"is_view_mode": True})

        return Destination(ListOfGroupsView, view_args={"is_view_mode": False})


class ListOfSharesView(View):
    """
    View to display the list of shares.
    """

    def __init__(self, group_index: int = 0, is_single_level: bool = False):
        super().__init__()
        self.group_index = group_index
        self.shares = self.controller.storage.scheme.get_shares_indices_of_group(
            group_index
        )
        logger.info("Shares in group %d: %s", group_index, self.shares)

        self.fingerprint = None
        if is_single_level:
            if self.controller.storage.scheme:
                self.fingerprint = self.controller.storage._scheme._wallet.fingerprint

        # create button options for each group
        self.button_data = [ButtonOption(f"Shares {i}") for i in self.shares]

    def run(self):
        """
        Run the view to display the list of groups.
        """
        ret = self.run_screen(
            GroupShareListScreen,
            title=(f"Group {self.group_index}"),
            fingerprint=self.fingerprint,
            button_data=self.button_data,
            show_check_button=True if self.fingerprint else False,
            show_back_button=False if self.fingerprint else True,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if ret == RET_CODE__CHECK_BUTTON:
            # If not in view mode, proceed to mnemonic generation
            self.controller.storage.discard_scheme()
            return Destination(MainMenuView)

        share = self.controller.storage.scheme.get_mnemonics_share_of_group(
            ret, self.group_index
        )
        return Destination(MnemonicView, view_args={"words": share})


class MnemonicView(View):
    """
    View to display the mnemonic.
    """

    def __init__(self, words):
        super().__init__()
        self.words = words

    def run(self):
        """
        Run the view to display the mnemonic.
        """

        from seedcash.gui.screens.load_seed_screens import SeedCashSeedWordsScreen

        self.run_screen(SeedCashSeedWordsScreen, seed_words=self.words)

        return Destination(BackStackView)


class DiscardGroupsView(View):
    """
    View to discard the groups.
    """

    KEEP_GROUPS = ButtonOption("Keep Groups Scheme")
    DISCARD_GROUPS = ButtonOption("Discard Groups Scheme", icon_color="red")

    def __init__(self):
        super().__init__()
        self.groups = self.controller.storage.scheme_params._groups_length
        self.group_threshold = self.controller.storage.scheme_params._group_threshold

        self.button_data = [
            self.KEEP_GROUPS,
            self.DISCARD_GROUPS,
        ]

    def run(self):
        """
        Run the view to discard the groups.
        """

        ret = self.run_screen(
            DireWarningScreen,
            text="Discard Groups Scheme",
            button_data=self.button_data,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if self.button_data[ret] == self.KEEP_GROUPS:
            # Keep groups scheme
            return Destination(VisualGroupView, skip_current_view=True)
        elif self.button_data[ret] == self.DISCARD_GROUPS:
            # Discard groups scheme
            self.controller.storage.scheme_params.discard_groups()
            return Destination(BackStackView)


class DiscardSharesView(View):
    """
    View to discard the shares.
    """

    KEEP_SHARES = ButtonOption("Keep Shares Scheme")
    DISCARD_SHARES = ButtonOption("Discard Shares Scheme", icon_color="red")

    def __init__(self, group_index: int = 0, is_single_level: bool = False):
        super().__init__()
        self.group_index = group_index
        self.is_single_level = is_single_level

        self.button_data = [
            self.KEEP_SHARES,
            self.DISCARD_SHARES,
        ]

    def run(self):
        """
        Run the view to discard the shares.
        """

        ret = self.run_screen(
            DireWarningScreen,
            text="Discard Shares Scheme",
            button_data=self.button_data,
        )

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        if self.button_data[ret] == self.KEEP_SHARES:
            # Keep shares scheme
            return Destination(
                VisualSharesView,
                view_args={
                    "group_index": self.group_index,
                    "is_single_level": self.is_single_level,
                },
                skip_current_view=True,
            )
        elif self.button_data[ret] == self.DISCARD_SHARES:
            # Discard shares scheme
            self.controller.storage.scheme_params.update_groups(self.group_index, None)
            return Destination(BackStackView)
