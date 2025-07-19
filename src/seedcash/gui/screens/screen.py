import logging
import time

from dataclasses import dataclass
from gettext import gettext as _
from typing import Any, List, Tuple

from seedcash.helpers.l10n import mark_for_translation as _mft
from seedcash.gui.components import (
    GUIConstants,
    BaseComponent,
    Button,
    Icon,
    IconButton,
    LargeIconButton,
    SeedCashIconConstants,
    TopNav,
    TextArea,
    load_image,
)
from seedcash.gui.keyboard import Keyboard, TextEntryDisplay
from seedcash.hardware.buttons import HardwareButtonsConstants, HardwareButtons
from seedcash.models.encode_qr import BaseQrEncoder
from seedcash.models.settings import SettingsConstants
from seedcash.models.threads import BaseThread, ThreadsafeCounter

logger = logging.getLogger(__name__)


# Must be huge numbers to avoid conflicting with the selected_button returned by the
#   screens with buttons.
RET_CODE__BACK_BUTTON = 1000
RET_CODE__POWER_BUTTON = 1001


@dataclass
class BaseScreen(BaseComponent):
    def __post_init__(self):
        super().__post_init__()

        self.hw_inputs = HardwareButtons.get_instance()

        # Implementation classes can add their own BaseThread to run in parallel with the
        # main execution thread.
        self.threads: List[BaseThread] = []

        # Implementation classes can add additional BaseComponent-derived objects to the
        # list. They'll be called to `render()` themselves in BaseScreen._render().
        self.components: List[BaseComponent] = []

        # Implementation classes can add PIL.Image objs here. Format is a tuple of the
        # Image and its (x,y) paste coords.
        self.paste_images: List[Tuple] = []

        # Tracks position on scrollable pages, determines which elements are visible.
        self.scroll_y = 0

    def get_threads(self) -> List[BaseThread]:
        threads = self.threads.copy()
        for component in self.components:
            threads += component.threads
        return threads

    def display(self) -> Any:
        try:
            with self.renderer.lock:
                self._render()
                self.renderer.show_image()

            for t in self.get_threads():
                if not t.is_alive():
                    t.start()

            return self._run()
        except Exception as e:
            repr(e)
            raise e
        finally:
            for t in self.get_threads():
                t.stop()

            for t in self.get_threads():
                # Wait for each thread to stop; equivalent to `join()` but gracefully
                # handles threads that were never run (necessary for screenshot generator
                # compatibility, perhaps other edge cases).
                while t.is_alive():
                    time.sleep(0.01)

    def clear_screen(self):
        # Clear the whole canvas
        self.image_draw.rectangle(
            (0, 0, self.canvas_width, self.canvas_height),
            fill=0,
        )

    def _render(self):
        self.clear_screen()

        # TODO: Check self.scroll_y and only render visible elements
        for component in self.components:
            component.render()

        for img, coords in self.paste_images:
            self.canvas.paste(img, coords)

    def _run_callback(self):
        """
        Optional implementation step that's called during each _run() loop.

        Loop will continue if it returns None.
        If it returns a value, the Screen will exit and relay that return value to
        its parent View.
        """
        pass

    def _run(self):
        """
        Screen can run on its own until it returns a final exit input from the user.

        For example: A basic menu screen where the user can key up and down. The
        Screen can handle the UI updates to light up the currently selected menu item
        on its own. Only when the user clicks to make a selection would _run() exit
        and return the selected option.

        In general, _run() will be implemented as a continuous loop waiting for user
        input and redrawing the screen as needed. When it redraws, it must claim
        the `Renderer.lock` to ensure that its updates don't conflict with any other
        threads that might be updating the screen at the same time (e.g. flashing
        warning edges, auto-scrolling long titles or buttons, etc).

        Just note that this loop cannot hold the lock indefinitely! Each iteration
        through the loop should claim the lock, render, and then release it.
        """
        raise Exception("Must implement in a child class")


class LoadingScreenThread(BaseThread):
    def __init__(self, text: str = None):
        super().__init__()
        self.text = text

    def run(self):
        from seedcash.gui.renderer import Renderer

        renderer: Renderer = Renderer.get_instance()

        center_image = load_image("btc_logo_60x60.png")
        orbit_gap = 2 * GUIConstants.COMPONENT_PADDING
        bounding_box = (
            int((renderer.canvas_width - center_image.width) / 2 - orbit_gap),
            int((renderer.canvas_height - center_image.height) / 2 - orbit_gap),
            int((renderer.canvas_width + center_image.width) / 2 + orbit_gap),
            int((renderer.canvas_height + center_image.height) / 2 + orbit_gap),
        )
        position = 0
        arc_sweep = 45
        arc_color = "#ff9416"
        arc_trailing_color = "#80490b"

        # Need to flush the screen
        with renderer.lock:
            renderer.draw.rectangle(
                (0, 0, renderer.canvas_width, renderer.canvas_height),
                fill=GUIConstants.BACKGROUND_COLOR,
            )
            renderer.canvas.paste(
                center_image, (bounding_box[0] + orbit_gap, bounding_box[1] + orbit_gap)
            )

            if self.text:
                TextArea(
                    text=self.text,
                    font_size=GUIConstants.get_top_nav_title_font_size(),
                    screen_y=int((renderer.canvas_height - bounding_box[3]) / 2),
                ).render()

        while self.keep_running:
            with renderer.lock:
                # Render leading arc
                renderer.draw.arc(
                    bounding_box,
                    start=position,
                    end=position + arc_sweep,
                    fill=arc_color,
                    width=GUIConstants.COMPONENT_PADDING,
                )

                # Render trailing arc
                renderer.draw.arc(
                    bounding_box,
                    start=position - arc_sweep,
                    end=position,
                    fill=arc_trailing_color,
                    width=GUIConstants.COMPONENT_PADDING,
                )

                # Erase previous trailing arc leading arc
                renderer.draw.arc(
                    bounding_box,
                    start=position - 2 * arc_sweep,
                    end=position - arc_sweep,
                    fill=GUIConstants.BACKGROUND_COLOR,
                    width=GUIConstants.COMPONENT_PADDING,
                )

                renderer.show_image()
            position += arc_sweep


@dataclass
class ButtonOption:
    """
    Note: The babel config in setup.cfg will extract the `button_label` string for translation
    """

    button_label: str
    icon_name: str = None
    icon_color: str = None
    right_icon_name: str = None
    button_label_color: str = None
    return_data: Any = None
    active_button_label: str = (
        None  # Changes displayed button label when button is active
    )
    font_name: str = None  # Optional override
    font_size: int = None  # Optional override


@dataclass
class LargeButtonScreen(BaseScreen):
    button_data: list = None
    button_font_name: str = None
    button_font_size: int = None
    button_selected_color: str = GUIConstants.ACCENT_COLOR
    selected_button: int = 0

    def __post_init__(self):
        if not self.button_font_name:
            self.button_font_name = GUIConstants.BUTTON_FONT_NAME
        if not self.button_font_size:
            self.button_font_size = GUIConstants.BUTTON_FONT_SIZE + 2

        super().__post_init__()

        if not self.button_data:
            raise Exception("button_data must be provided")

        # Calculate available height for main buttons (excluding bottom power button)
        num_main_buttons = len(self.button_data)
        total_padding = (num_main_buttons - 1) * GUIConstants.COMPONENT_PADDING
        max_button_height = (
            self.canvas_height
            - total_padding
            - 2 * GUIConstants.EDGE_PADDING
            - GUIConstants.TOP_NAV_BUTTON_SIZE
        ) // num_main_buttons
        button_size = min(
            self.canvas_width - 2 * GUIConstants.EDGE_PADDING, max_button_height
        )

        # Center the column of buttons
        total_buttons_height = num_main_buttons * button_size + total_padding
        button_start_y = (
            self.canvas_height - GUIConstants.EDGE_PADDING - total_buttons_height
        ) // 2
        button_start_x = (self.canvas_width - button_size) // 2

        self.buttons = []
        for i, button_option in enumerate(self.button_data):
            # Support both ButtonOption and dict for button_data
            if isinstance(button_option, ButtonOption):
                button_label = button_option.button_label
                icon_name = button_option.icon_name
            elif isinstance(button_option, dict):
                button_label = button_option.get("button_label", "")
                icon_name = button_option.get("icon_name", None)
            else:
                raise Exception("button_data must be ButtonOption or dict")

            button_args = {
                "text": _(button_label),
                "screen_x": button_start_x,
                "screen_y": button_start_y,
                "width": button_size,
                "height": button_size,
                "is_text_centered": True,
                "font_name": self.button_font_name,
                "font_size": self.button_font_size,
                "selected_color": self.button_selected_color,
            }
            if icon_name:
                button_args["icon_name"] = icon_name
                button_args["text_y_offset"] = (
                    int(48 / 240 * self.renderer.canvas_height)
                    + GUIConstants.COMPONENT_PADDING
                )
                button = LargeIconButton(**button_args)
            else:
                button = Button(**button_args)

            self.buttons.append(button)
            self.components.append(button)

            # set the button as selected if it's the first one
            if i == 0:
                button.is_selected = True
                self.selected_button = 0

            button_start_y += button_size + GUIConstants.COMPONENT_PADDING

        # Add the small setting button at the bottom left
        self.settings_button = IconButton(
            icon_name=SeedCashIconConstants.SETTINGS,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            screen_x=GUIConstants.EDGE_PADDING,
            screen_y=self.canvas_height
            - GUIConstants.TOP_NAV_BUTTON_SIZE
            - GUIConstants.EDGE_PADDING,
            width=GUIConstants.TOP_NAV_BUTTON_SIZE,
            height=GUIConstants.TOP_NAV_BUTTON_SIZE,
        )

        self.buttons.append(self.settings_button)  # Now selectable
        self.components.append(self.settings_button)

        # Add the small power button at the bottom right as a selectable button
        self.bottom_button = IconButton(
            icon_name=SeedCashIconConstants.POWER,
            icon_size=GUIConstants.ICON_INLINE_FONT_SIZE,
            screen_x=self.canvas_width
            - GUIConstants.TOP_NAV_BUTTON_SIZE
            - GUIConstants.EDGE_PADDING,
            screen_y=self.canvas_height
            - GUIConstants.TOP_NAV_BUTTON_SIZE
            - GUIConstants.EDGE_PADDING,
            width=GUIConstants.TOP_NAV_BUTTON_SIZE,
            height=GUIConstants.TOP_NAV_BUTTON_SIZE,
        )

        self.buttons.append(self.bottom_button)  # Now selectable
        self.components.append(self.bottom_button)

    def _run(self):
        def swap_selected_button(new_selected_button: int):
            self.buttons[self.selected_button].is_selected = False
            self.buttons[self.selected_button].render()
            self.selected_button = new_selected_button
            self.buttons[self.selected_button].is_selected = True
            self.buttons[self.selected_button].render()

        while True:
            ret = self._run_callback()
            if ret is not None:
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
                if (
                    user_input == HardwareButtonsConstants.KEY_UP
                    or user_input == HardwareButtonsConstants.KEY_LEFT
                ):
                    # Navigation wraps through all buttons, including the power button at the bottom.
                    if self.selected_button == 0:
                        pass  # Already at top button
                    else:
                        swap_selected_button(self.selected_button - 1)

                elif (
                    user_input == HardwareButtonsConstants.KEY_DOWN
                    or user_input == HardwareButtonsConstants.KEY_RIGHT
                ):
                    # After the last main button, next down selects the power button.
                    if self.selected_button < len(self.buttons) - 1:
                        swap_selected_button(self.selected_button + 1)

                elif user_input in HardwareButtonsConstants.KEYS__ANYCLICK:
                    return self.selected_button

                self.renderer.show_image()


@dataclass
class MainMenuScreen(LargeButtonScreen):
    # Override LargeButtonScreen defaults
    show_back_button: bool = False
    show_power_button: bool = True
    button_font_size: int = 16
