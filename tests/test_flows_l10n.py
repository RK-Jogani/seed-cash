from gettext import gettext as _

# Must import test base before the Controller
from base import FlowTest, FlowStep

from seedcash.gui.screens.screen import RET_CODE__BACK_BUTTON, ButtonOption
from seedcash.models.settings_definition import SettingsConstants, SettingsDefinition
from seedcash.views import settings_views
from seedcash.views.view import MainMenuView



class TestL10nFlows(FlowTest):
    def test_change_locale(self):
        settings_entry = SettingsDefinition.get_settings_entry(SettingsConstants.SETTING__LOCALE)

        # Initially we get English
        assert _(MainMenuView.SCAN.button_label) == "Scan"

        self.run_sequence([
            FlowStep(MainMenuView, button_data_selection=MainMenuView.SETTINGS),
            FlowStep(settings_views.SettingsMenuView, button_data_selection=ButtonOption(settings_entry.display_name)),
            FlowStep(settings_views.LocaleSelectionView, screen_return_value=1),  # Any index > 0 (English)
        ])

        # Now we don't get English
        assert _(MainMenuView.SCAN.button_label) != "Scan"
