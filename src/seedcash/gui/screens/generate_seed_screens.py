import logging

from dataclasses import dataclass
from gettext import gettext as _


from seedcash.hardware.buttons import HardwareButtonsConstants
from seedcash.gui.components import (
    Fonts,
    IconTextLine,
    TextArea,
    GUIConstants,
    Button,
)
from seedcash.models import visual_hash as vh

from .screen import (
    RET_CODE__BACK_BUTTON,
    BaseTopNavScreen,
    ButtonListScreen,
    KeyboardScreen,
)

logger = logging.getLogger(__name__)


"""*****************************
Seed Cash Screens
*****************************"""


# SeedCashLoadSeedScreen is used to load a seed in the Seed Cash flow.
# Reminder Screen
@dataclass
class SeedCashGenerateSeedScreen(ButtonListScreen, BaseTopNavScreen):
    def __post_init__(self):
        self.is_button_text_centered = False
        self.is_top_nav = True
        self.show_back_button = True
        super().__post_init__()

    def _run(self):
        while True:
            ret = self._run_callback()
            if ret is not None:
                logging.info("Exiting ButtonListScreen due to _run_callback")
                return ret

            user_input = self.hw_inputs.wait_for(
                [
                    HardwareButtonsConstants.KEY_UP,
                    HardwareButtonsConstants.KEY_DOWN,
                    HardwareButtonsConstants.KEY_LEFT,
                    HardwareButtonsConstants.KEY_RIGHT,
                ]
                + HardwareButtonsConstants.KEYS__ANYCLICK
            )

            with self.renderer.lock:
                if not self.top_nav.is_selected and (
                    user_input == HardwareButtonsConstants.KEY_LEFT
                    or (
                        user_input == HardwareButtonsConstants.KEY_UP
                        and self.selected_button == 0
                    )
                ):
                    # SHORTCUT to escape long menu screens!
                    # OR keyed UP from the top of the list.
                    # Move selection up to top_nav
                    # Only move navigation up there if there's something to select
                    if self.top_nav.show_back_button or self.top_nav.show_power_button:
                        self.buttons[self.selected_button].is_selected = False
                        self.buttons[self.selected_button].render()

                        self.top_nav.is_selected = True
                        self.top_nav.render_buttons()

                elif user_input == HardwareButtonsConstants.KEY_UP:
                    if self.top_nav.is_selected:
                        # Can't go up any further
                        pass
                    else:
                        cur_selected_button: Button = self.buttons[self.selected_button]
                        self.selected_button -= 1
                        next_selected_button: Button = self.buttons[
                            self.selected_button
                        ]
                        cur_selected_button.is_selected = False
                        next_selected_button.is_selected = True
                        if (
                            self.has_scroll_arrows
                            and next_selected_button.screen_y
                            - next_selected_button.scroll_y
                            + next_selected_button.height
                            < self.top_nav.height
                        ):
                            # Selected a Button that's off the top of the screen
                            frame_scroll = (
                                cur_selected_button.screen_y
                                - next_selected_button.screen_y
                            )
                            for button in self.buttons:
                                button.scroll_y -= frame_scroll
                            self._render_visible_buttons()
                        else:
                            cur_selected_button.render()
                            next_selected_button.render()

                elif user_input == HardwareButtonsConstants.KEY_DOWN or (
                    self.top_nav.is_selected
                    and user_input == HardwareButtonsConstants.KEY_RIGHT
                ):
                    if self.selected_button == len(self.buttons) - 1:
                        # Already at the bottom of the list. Nowhere to go. But may need
                        # to re-render if we're returning from top_nav; otherwise skip
                        # this update loop.
                        if not self.top_nav.is_selected:
                            continue

                    if self.top_nav.is_selected:
                        self.top_nav.is_selected = False
                        self.top_nav.render_buttons()

                        cur_selected_button = None
                        next_selected_button = self.buttons[self.selected_button]
                        next_selected_button.is_selected = True

                    else:
                        cur_selected_button: Button = self.buttons[self.selected_button]
                        self.selected_button += 1
                        next_selected_button: Button = self.buttons[
                            self.selected_button
                        ]
                        cur_selected_button.is_selected = False
                        next_selected_button.is_selected = True

                    if self.has_scroll_arrows and (
                        next_selected_button.screen_y
                        - next_selected_button.scroll_y
                        + next_selected_button.height
                        > self.down_arrow_img_y
                    ):
                        # Selected a Button that's off the bottom of the screen
                        frame_scroll = (
                            next_selected_button.screen_y - cur_selected_button.screen_y
                        )
                        for button in self.buttons:
                            button.scroll_y += frame_scroll
                        self._render_visible_buttons()
                    else:
                        if cur_selected_button:
                            cur_selected_button.render()
                        next_selected_button.render()

                elif user_input in HardwareButtonsConstants.KEYS__ANYCLICK:
                    if self.top_nav.is_selected:
                        return self.top_nav.selected_button
                    return self.selected_button

                # Write the screen updates
                self.renderer.show_image()


@dataclass
class ToolsCoinFlipEntryScreen(KeyboardScreen):

    def __post_init__(self):
        # Override values set by the parent class
        # TRANSLATOR_NOTE: current coin-flip number vs total flips (e.g. flip 3 of 4)
        self.show_back_button = False
        # Specify the keys in the keyboard
        self.rows = 1
        self.cols = 4
        self.key_height = (
            GUIConstants.TOP_NAV_TITLE_FONT_SIZE + 2 + 2 * GUIConstants.EDGE_PADDING
        )
        self.keys_charset = "10"
        self.keyboard_start_y = 2
        # Now initialize the parent class
        super().__post_init__()

        self.components.append(
            TextArea(
                # TRANSLATOR_NOTE: How we call the "front" side result during a coin toss.
                text="Introduce the last 7 bits of entropy",
                screen_y=GUIConstants.COMPONENT_PADDING,
            )
        )


@dataclass
class ToolsCalcFinalWordScreen(ButtonListScreen):
    selected_final_word: str = None
    selected_final_bits: str = None
    checksum_bits: str = None
    actual_final_word: str = None

    def __post_init__(self):
        self.is_bottom_list = True
        super().__post_init__()

        # First what's the total bit display width and where do the checksum bits start?
        bit_font_size = (
            GUIConstants.BUTTON_FONT_SIZE + 2
        )  # bit font size should not vary by locale
        font = Fonts.get_font(
            GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME, bit_font_size
        )
        (left, top, bit_display_width, bit_font_height) = font.getbbox(
            "0" * 11, anchor="lt"
        )
        (left, top, checksum_x, bottom) = font.getbbox(
            "0" * (11 - len(self.checksum_bits)), anchor="lt"
        )
        bit_display_x = int((self.canvas_width - bit_display_width) / 2)
        checksum_x += bit_display_x

        y_spacer = GUIConstants.COMPONENT_PADDING

        # Display the user's additional entropy input
        if self.selected_final_word:
            selection_text = self.selected_final_word
            keeper_selected_bits = self.selected_final_bits[
                : 11 - len(self.checksum_bits)
            ]

            # The word's least significant bits will be rendered differently to convey
            # the fact that they're being discarded.
            discard_selected_bits = self.selected_final_bits[
                -1 * len(self.checksum_bits) :
            ]
        else:
            # User entered coin flips or all zeros
            selection_text = self.selected_final_bits
            keeper_selected_bits = self.selected_final_bits

            # We'll append spacer chars to preserve the vertical alignment (most
            # significant n bits always rendered in same column)
            discard_selected_bits = "_" * (len(self.checksum_bits))

        # TRANSLATOR_NOTE: The additional entropy the user supplied (e.g. coin flips)
        your_input = _('Your input: "{}"').format(selection_text)
        self.components.append(
            TextArea(
                text=your_input,
                screen_y=GUIConstants.COMPONENT_PADDING
                + GUIConstants.COMPONENT_PADDING
                - 2,  # Nudge to last line doesn't get too close to "Next" button
                height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
            )
        )

        # ...and that entropy's associated 11 bits
        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer
        first_bits_line = TextArea(
            text=keeper_selected_bits,
            font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
            font_size=bit_font_size,
            edge_padding=0,
            screen_x=bit_display_x,
            screen_y=screen_y,
            is_text_centered=False,
        )
        self.components.append(first_bits_line)

        # Render the least significant bits that will be replaced by the checksum in a
        # de-emphasized font color.
        if "_" in discard_selected_bits:
            screen_y += int(
                first_bits_line.height / 2
            )  # center the underscores vertically like hypens
        self.components.append(
            TextArea(
                text=discard_selected_bits,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                font_size=bit_font_size,
                edge_padding=0,
                screen_x=checksum_x,
                screen_y=screen_y,
                is_text_centered=False,
            )
        )

        # Show the checksum...
        self.components.append(
            TextArea(
                # TRANSLATOR_NOTE: A function of "x" to be used for detecting errors in "x"
                text=_("Checksum"),
                edge_padding=0,
                screen_y=first_bits_line.screen_y
                + first_bits_line.height
                + 2 * GUIConstants.COMPONENT_PADDING,
                height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
            )
        )

        # ...and its actual bits. Prepend spacers to keep vertical alignment
        checksum_spacer = "_" * (11 - len(self.checksum_bits))

        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer

        # This time we de-emphasize the prepended spacers that are irrelevant
        self.components.append(
            TextArea(
                text=checksum_spacer,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                font_color=GUIConstants.LABEL_FONT_COLOR,
                font_size=bit_font_size,
                edge_padding=0,
                screen_x=bit_display_x,
                screen_y=screen_y
                + int(
                    first_bits_line.height / 2
                ),  # center the underscores vertically like hypens
                is_text_centered=False,
            )
        )

        # And especially highlight (orange!) the actual checksum bits
        self.components.append(
            TextArea(
                text=self.checksum_bits,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                font_size=bit_font_size,
                font_color=GUIConstants.ACCENT_COLOR,
                edge_padding=0,
                screen_x=checksum_x,
                screen_y=screen_y,
                is_text_centered=False,
            )
        )

        # And now the *actual* final word after merging the bit data
        self.components.append(
            TextArea(
                # TRANSLATOR_NOTE: labeled presentation of the last word in a BIP-39 mnemonic seed phrase.
                text=_('Final Word: "{}"').format(self.actual_final_word),
                screen_y=self.components[-1].screen_y
                + self.components[-1].height
                + 2 * GUIConstants.COMPONENT_PADDING,
                height_ignores_below_baseline=True,  # Keep the next line (bits display) snugged up, regardless of text rendering below the baseline
            )
        )

        # Once again show the bits that came from the user's entropy...
        num_checksum_bits = len(self.checksum_bits)
        user_component = self.selected_final_bits[: 11 - num_checksum_bits]
        screen_y = self.components[-1].screen_y + self.components[-1].height + y_spacer
        self.components.append(
            TextArea(
                text=user_component,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                font_size=bit_font_size,
                edge_padding=0,
                screen_x=bit_display_x,
                screen_y=screen_y,
                is_text_centered=False,
            )
        )

        # ...and append the checksum's bits, still highlighted in orange
        self.components.append(
            TextArea(
                text=self.checksum_bits,
                font_name=GUIConstants.FIXED_WIDTH_EMPHASIS_FONT_NAME,
                font_color=GUIConstants.ACCENT_COLOR,
                font_size=bit_font_size,
                edge_padding=0,
                screen_x=checksum_x,
                screen_y=screen_y,
                is_text_centered=False,
            )
        )


@dataclass
class ToolsCalcFinalWordDoneScreen(ButtonListScreen):
    final_word: str = None
    fingerprint: str = None

    def __post_init__(self):
        # Manually specify 12 vs 24 case for easier ordinal translation
        self.is_bottom_list = True

        super().__post_init__()

        self.components.append(
            TextArea(
                text=f"""\"{self.final_word}\"""",
                font_size=26,
                is_text_centered=True,
                screen_y=2 * GUIConstants.COMPONENT_PADDING,
            )
        )

        # Generate fingerprint image using visual hash
        fingerprint_image = vh.generate_lifehash(self.fingerprint)

        # Calculate the icon size to match the original icon size
        icon_size = GUIConstants.ICON_FONT_SIZE + 12

        # Calculate position for the fingerprint display
        fingerprint_y = (
            self.components[-1].screen_y
            + self.components[-1].height
            + 3 * GUIConstants.COMPONENT_PADDING
        )

        self.components.append(
            IconTextLine(
                icon_name=None,  # No icon since we're using the actual image
                # TRANSLATOR_NOTE: a label for the shortened Key-id of a BIP-32 master HD wallet
                label_text=_("fingerprint"),
                value_text=self.fingerprint,
                is_text_centered=True,
                screen_y=fingerprint_y,
            )
        )

        # Calculate position for the fingerprint image (to the left of the text)
        image_x = (self.canvas_width - icon_size) // 2 - 60  # Offset to left of text
        image_y = fingerprint_y - (icon_size // 4)  # Align with text baseline

        # Add the fingerprint image to paste_images
        self.paste_images.append(
            (fingerprint_image.resize((icon_size, icon_size)), (image_x, image_y))
        )
