import logging
from seedcash.gui.screens.screen import RET_CODE__BACK_BUTTON, SeedCashButtonListWithNav
from seedcash.views.view import BackStackView, View, Destination, ButtonOption
from seedcash.models.btc_functions import BitcoinFunctions as bf


logger = logging.getLogger(__name__)


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

            self.controller.storage.set_bits(ret)
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

            self.controller.storage.set_bits(self.bits)

        self.bits = self.controller.storage.bits
        logger.info(
            "Generated random bits of len %d for Slip39 seed: %s",
            len(self.bits),
            self.bits,
        )

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
            SeedCashButtonListWithNav,
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
        self.groups = len(self.controller.storage.groups)
        self.group_threshold = self.controller.storage.group_threshold

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
            self.controller.storage.discard_groups()
            return Destination(BackStackView)

        self.controller.storage.group_threshold = result[0]
        self.controller.storage.groups = [None] * result[1]

        return Destination(ListOfGroupsView)


class ListOfGroupsView(View):
    """
    View to display the list of groups.
    """

    def __init__(self, is_view_mode: bool = False):
        super().__init__()
        self.is_view_mode = is_view_mode
        self.groups = self.controller.storage.groups

        # create button options for each group
        self.button_data = [
            ButtonOption(f"Group {i + 1}") for i in range(len(self.groups))
        ]

    def run(self):
        """
        Run the view to display the list of groups.
        """
        ret = self.run_screen(SeedCashButtonListWithNav, button_data=self.button_data)

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        return Destination(VisualSharesView, view_args={"group_index": ret})


class VisualSharesView(View):
    total_members = 1
    threshold = 1

    def __init__(self, group_index=0, is_single_level=False):
        super().__init__()
        self.group_index = group_index
        self.is_single_level = is_single_level
        self.group = self.controller.storage.get_group_at(group_index)

        if self.group:
            self.total_members = self.group[1]
            self.threshold = self.group[0]

    def run(self):
        from seedcash.gui.screens.slip_screens import VisualGroupShareScreen

        result = self.run_screen(
            VisualGroupShareScreen,
            text="Shares",
            threshold=self.threshold,
            total_members=self.total_members,
        )

        if result == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        self.controller.storage.update_groups(self.group_index, result)

        if self.is_single_level:
            self.controller.storage.generate_slip_mnemonic()
            return Destination(ListOfSharesView, view_args={"group_index": 0})

        if result == "CONFIRM":
            return Destination(ListOfGroupsView, view_args={"is_view_mode": True})

        return Destination(BackStackView)


class ListOfSharesView(View):
    """
    View to display the list of shares.
    """

    def __init__(self, group_index: int = 0):
        super().__init__()
        self.group_index = group_index
        self.shares = self.controller.storage.groups[self.group_index][1]

        # create button options for each group
        self.button_data = [ButtonOption(f"Shares {i + 1}") for i in range(self.shares)]

    def run(self):
        """
        Run the view to display the list of groups.
        """
        ret = self.run_screen(SeedCashButtonListWithNav, button_data=self.button_data)

        if ret == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        share = self.controller.storage.slip_mnemonic[self.group_index][ret].split()

        from seedcash.gui.screens.load_seed_screens import SeedCashSeedWordsScreen

        self.run_screen(SeedCashSeedWordsScreen, seed_words=share)
