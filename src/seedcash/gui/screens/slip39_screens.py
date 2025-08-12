from attr import dataclass
from seedcash.gui.screens.screen import BaseTopNavScreen
from seedcash.gui.components import (
    GUIConstants,
)
from seedcash.hardware.buttons import HardwareButtonsConstants
from seedcash.gui.keyboard import Keyboard, TextEntryDisplay


@dataclass
class Slip39EntryScreen(BaseTopNavScreen):
    bits: int = 128  # Default to 128 bits for 20 words

    def __post_init__(self):
        super().__post_init__()

        keys_number = "01"

        # Initialize the top navigation bar
        # i is the number of bits entered so far
        self.title = f"{i}/{self.bits} Entropy Bits"
        text_entry_display_y = self.top_nav.height
        text_entry_display_height = 30

        keyboard_start_y = (
            text_entry_display_y
            + text_entry_display_height
            + GUIConstants.COMPONENT_PADDING
        )

        self.keyboard_digits = Keyboard(
            draw=self.renderer.draw,
            charset=keys_number,
            rows=1,
            cols=5,
            rect=(
                GUIConstants.COMPONENT_PADDING,
                keyboard_start_y,
                self.canvas_width
                - GUIConstants.COMPONENT_PADDING
                - self.right_panel_buttons_width,
                self.canvas_height - GUIConstants.EDGE_PADDING,
            ),
            additional_keys=[
                Keyboard.KEY_CURSOR_LEFT,
                Keyboard.KEY_CURSOR_RIGHT,
            ],
            auto_wrap=[Keyboard.WRAP_LEFT, Keyboard.WRAP_RIGHT],
            render_now=False,
        )

        self.text_entry_display = TextEntryDisplay(
            canvas=self.renderer.canvas,
            rect=(
                GUIConstants.EDGE_PADDING,
                text_entry_display_y,
                self.canvas_width - self.right_panel_buttons_width,
                text_entry_display_y + text_entry_display_height,
            ),
            cursor_mode=TextEntryDisplay.CURSOR_MODE__BAR,
            is_centered=False,
            cur_text="".join(self.passphrase),
        )

    def _run(self):
        cursor_position = len(self.passphrase)
        cur_keyboard = self.keyboard_abc
        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT
        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT

        # Start the interactive update loop
        while True:
            input = self.hw_inputs.wait_for(HardwareButtonsConstants.ALL_KEYS)

            keyboard_swap = False

            with self.renderer.lock:
                # Check our two possible exit conditions
                # TODO: note the unusual return value, consider refactoring to a Response object in the future
                if input == HardwareButtonsConstants.KEY3:
                    # Save!
                    # First light up key3
                    self.hw_button3.is_selected = True
                    self.hw_button3.render()
                    self.renderer.show_image()
                    return dict(passphrase=self.passphrase)

                elif (
                    input == HardwareButtonsConstants.KEY_PRESS
                    and self.top_nav.is_selected
                ):
                    # Back button clicked
                    return dict(passphrase=self.passphrase, is_back_button=True)

                # Check for keyboard swaps
                if input == HardwareButtonsConstants.KEY1:
                    # First light up key1
                    self.hw_button1.is_selected = True
                    self.hw_button1.render()

                    # Return to the same button2 keyboard, if applicable
                    if cur_keyboard == self.keyboard_digits:
                        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_symbols_1:
                        cur_button2_text = self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_symbols_2:
                        cur_button2_text = self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT

                    if cur_button1_text == self.KEYBOARD__LOWERCASE_BUTTON_TEXT:
                        self.keyboard_abc.set_selected_key_indices(
                            x=cur_keyboard.selected_key["x"],
                            y=cur_keyboard.selected_key["y"],
                        )
                        cur_keyboard = self.keyboard_abc
                        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT
                    else:
                        self.keyboard_ABC.set_selected_key_indices(
                            x=cur_keyboard.selected_key["x"],
                            y=cur_keyboard.selected_key["y"],
                        )
                        cur_keyboard = self.keyboard_ABC
                        cur_button1_text = self.KEYBOARD__LOWERCASE_BUTTON_TEXT
                    cur_keyboard.render_keys()

                    # Show the changes; this loop will have two renders
                    self.renderer.show_image()

                    keyboard_swap = True
                    ret_val = None

                elif input == HardwareButtonsConstants.KEY2:
                    # First light up key2
                    self.hw_button2.is_selected = True
                    self.hw_button2.render()
                    self.renderer.show_image()

                    # And reset for next redraw
                    self.hw_button2.is_selected = False

                    # Return to the same button1 keyboard, if applicable
                    if cur_keyboard == self.keyboard_abc:
                        cur_button1_text = self.KEYBOARD__LOWERCASE_BUTTON_TEXT
                    elif cur_keyboard == self.keyboard_ABC:
                        cur_button1_text = self.KEYBOARD__UPPERCASE_BUTTON_TEXT

                    if cur_button2_text == self.KEYBOARD__DIGITS_BUTTON_TEXT:
                        self.keyboard_digits.set_selected_key_indices(
                            x=cur_keyboard.selected_key["x"],
                            y=cur_keyboard.selected_key["y"],
                        )
                        cur_keyboard = self.keyboard_digits
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT
                    elif cur_button2_text == self.KEYBOARD__SYMBOLS_1_BUTTON_TEXT:
                        self.keyboard_symbols_1.set_selected_key_indices(
                            x=cur_keyboard.selected_key["x"],
                            y=cur_keyboard.selected_key["y"],
                        )
                        cur_keyboard = self.keyboard_symbols_1
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT
                    elif cur_button2_text == self.KEYBOARD__SYMBOLS_2_BUTTON_TEXT:
                        self.keyboard_symbols_2.set_selected_key_indices(
                            x=cur_keyboard.selected_key["x"],
                            y=cur_keyboard.selected_key["y"],
                        )
                        cur_keyboard = self.keyboard_symbols_2
                        cur_keyboard.render_keys()
                        cur_button2_text = self.KEYBOARD__DIGITS_BUTTON_TEXT
                    cur_keyboard.render_keys()

                    # Show the changes; this loop will have two renders
                    self.renderer.show_image()

                    keyboard_swap = True
                    ret_val = None

                else:
                    # Process normal input
                    if (
                        input
                        in [
                            HardwareButtonsConstants.KEY_UP,
                            HardwareButtonsConstants.KEY_DOWN,
                        ]
                        and self.top_nav.is_selected
                    ):
                        # We're navigating off the previous button
                        self.top_nav.is_selected = False
                        self.top_nav.render_buttons()

                        # Override the actual input w/an ENTER signal for the Keyboard
                        if input == HardwareButtonsConstants.KEY_DOWN:
                            input = Keyboard.ENTER_TOP
                        else:
                            input = Keyboard.ENTER_BOTTOM
                    elif (
                        input
                        in [
                            HardwareButtonsConstants.KEY_LEFT,
                            HardwareButtonsConstants.KEY_RIGHT,
                        ]
                        and self.top_nav.is_selected
                    ):
                        # ignore
                        continue

                    ret_val = cur_keyboard.update_from_input(input)

                # Now process the result from the keyboard
                if ret_val in Keyboard.EXIT_DIRECTIONS:
                    self.top_nav.is_selected = True
                    self.top_nav.render_buttons()

                elif (
                    ret_val in Keyboard.ADDITIONAL_KEYS
                    and input == HardwareButtonsConstants.KEY_PRESS
                ):
                    if ret_val == Keyboard.KEY_BACKSPACE["code"]:
                        if cursor_position == 0:
                            pass
                        elif cursor_position == len(self.passphrase):
                            self.passphrase = self.passphrase[:-1]
                            cursor_position -= 1
                        else:
                            self.passphrase = (
                                self.passphrase[: cursor_position - 1]
                                + self.passphrase[cursor_position:]
                            )
                            cursor_position -= 1

                    elif ret_val == Keyboard.KEY_CURSOR_LEFT["code"]:
                        cursor_position -= 1
                        if cursor_position < 0:
                            cursor_position = 0

                    elif ret_val == Keyboard.KEY_CURSOR_RIGHT["code"]:
                        cursor_position += 1
                        if cursor_position > len(self.passphrase):
                            cursor_position = len(self.passphrase)

                    elif ret_val == Keyboard.KEY_SPACE["code"]:
                        if cursor_position == len(self.passphrase):
                            self.passphrase += " "
                        else:
                            self.passphrase = (
                                self.passphrase[:cursor_position]
                                + " "
                                + self.passphrase[cursor_position:]
                            )
                        cursor_position += 1

                    # Update the text entry display and cursor
                    self.text_entry_display.render(self.passphrase, cursor_position)

                elif (
                    input == HardwareButtonsConstants.KEY_PRESS
                    and ret_val not in Keyboard.ADDITIONAL_KEYS
                ):
                    # User has locked in the current letter
                    if cursor_position == len(self.passphrase):
                        self.passphrase += ret_val
                    else:
                        self.passphrase = (
                            self.passphrase[:cursor_position]
                            + ret_val
                            + self.passphrase[cursor_position:]
                        )
                    cursor_position += 1

                    # Update the text entry display and cursor
                    self.text_entry_display.render(self.passphrase, cursor_position)

                elif (
                    input in HardwareButtonsConstants.KEYS__LEFT_RIGHT_UP_DOWN
                    or keyboard_swap
                ):
                    # Live joystick movement; haven't locked this new letter in yet.
                    # Leave current spot blank for now. Only update the active keyboard keys
                    # when a selection has been locked in (KEY_PRESS) or removed ("del").
                    pass

                if keyboard_swap:
                    # Show the hw buttons' updated text and not active state
                    self.hw_button1.text = cur_button1_text
                    self.hw_button2.text = cur_button2_text
                    self.hw_button1.is_selected = False
                    self.hw_button2.is_selected = False
                    self.hw_button1.render()
                    self.hw_button2.render()

                self.renderer.show_image()
