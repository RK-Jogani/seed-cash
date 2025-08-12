from seedcash.gui.screens.screen import RET_CODE__BACK_BUTTON
from seedcash.views.view import (
    BackStackView,
    SeedCashChooseWordsView,
    View,
    Destination,
)
from seedcash.gui.components import ButtonOption
from seedcash.models.settings_definition import SettingsConstants


class SeedSlip39EntryView(View):
    """
    View for entering a Slip39 seed phrase.
    """

    def __init__(self, num_words: int = 20):
        super().__init__()
        if num_words == 20:
            self.bits = 128
        elif num_words == 33:
            self.bits = 256
        else:
            raise ValueError("Unsupported number of words for Slip39 seed phrase.")

    def run(self):
        from seedcash.gui.screens.slip39_screens import Slip39EntryScreen

        # Display the Slip39 entry screen
        selected_menu_num = self.run_screen(
            Slip39EntryScreen,
            bits=self.bits,
        )

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)

        # Handle the entered Slip39 seed phrase
        entered_phrase = self.controller.get_entered_phrase()
        if entered_phrase:
            return Destination(
                SeedCashChooseWordsView,
                view_args=dict(is_slip39=True, phrase=entered_phrase),
            )

        return Destination(BackStackView)
