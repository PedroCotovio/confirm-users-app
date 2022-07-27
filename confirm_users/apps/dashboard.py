from confapp import conf
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.expressions import F
from pyforms.basewidget import BaseWidget
from pyforms.controls import ControlLabel
from pyforms.controls import ControlButton
from pyforms.controls import ControlQueryList

from ..utils import import_attribute
from .. import app_settings


User = get_user_model()

UserForm = import_attribute(app_settings.USER_EDIT_FORM)


class Dashboard(BaseWidget):

    UID = "dashboard-app"
    TITLE = "Requests"

    ########################################################
    #### ORQUESTRA CONFIGURATION ###########################
    ########################################################
    LAYOUT_POSITION = conf.ORQUESTRA_HOME
    ORQUESTRA_MENU = "user"
    ORQUESTRA_MENU_ICON = "clipboard outline"
    ORQUESTRA_MENU_ORDER = 10
    ########################################################

    AUTHORIZED_GROUPS = ["superuser"]

    def __init__(self, *args, **kwargs):
        super(Dashboard, self).__init__(*args, **kwargs)

        self._label = ControlLabel()

        self._list = ControlQueryList(
            list_display=["date_joined", "username", "email", "email_confirmed"],
            headers=["Date joined", "Username", "Email", "Email verified"],
        )

        self._edit_btn_label = '<i class="ui edit icon"></i>Edit'
        self._approve_btn_label = '<i class="ui check icon"></i>Approve'
        self._remove_btn_label = '<i class="ui times icon"></i>Remove'

        self._edit = ControlButton(
            self._edit_btn_label,
            label_visible=False,
            css="fluid secondary",
            visible=False,
            default=self._edit_evt,
        )

        self._approve = ControlButton(
            self._approve_btn_label,
            label_visible=False,
            css="fluid green",
            visible=False,
            default=self._approve_evt,
        )

        self._remove = ControlButton(
            self._remove_btn_label,
            label_visible=False,
            css="fluid red",
            field_css="",
            visible=False,
            default=self._remove_evt,
        )

        self.formset = [" ", "_label", ("_remove", "_edit", "_approve"), "_list"]

        self._enable_actions()

        self._list.item_selection_changed_event = self._user_selected_evt

        self.populate_users_list()

    def populate_users_list(self):
        queryset = User.objects.filter(is_active=False)

        self._update_label(queryset)

        if queryset.exists():
            self._list.value = queryset.annotate(
                email_confirmed=F("emailaddress_verified")
            )
            self._show_actions()
            self._disable_actions()
        else:
            self._list.hide()
            self._edit.hide()
            self._approve.hide()
            self._remove.hide()

    def _show_actions(self):
        self._edit.show()
        self._approve.show()
        self._remove.show()

    def _enable_actions(self, user=None):
        if user:
            try:
                user.full_clean()
            except ValidationError:
                user_is_valid = False
            else:
                user_is_valid = True

            self._edit.enabled = True if app_settings.USER_EDIT_FORM else False
            self._approve.enabled = user_is_valid
            self._remove.enabled = True
        else:
            self._disable_actions()

    def _disable_actions(self):
        self._edit.enabled = False
        self._approve.enabled = False
        self._remove.enabled = False

    def _update_label(self, queryset):
        if queryset.exists():
            icon = '<i class="ui info circle icon"></i>'
            msg = "Users listed below require approval for accessing the database."
            css = "info"
        else:
            icon = '<i class="ui check icon"></i>'
            msg = "No users waiting account approval."
            css = "green"
        self._label.value = icon + msg
        self._label.css = css

    def _user_selected_evt(self):
        user_id = self._list.selected_row_id
        user = User.objects.get(pk=user_id)

        self._edit.label = self._edit_btn_label + f" [{user.username}]"
        self._approve.label = self._approve_btn_label + f" [{user.username}]"
        self._remove.label = self._remove_btn_label + f" [{user.username}]"

        self._enable_actions(user=user)

    def _edit_evt(self):
        app = UserForm(pk=self._list.selected_row_id)
        app.LAYOUT_POSITION = conf.ORQUESTRA_NEW_TAB

    def _approve_evt(self):
        user_id = self._list.selected_row_id
        user = User.objects.get(pk=user_id)
        user.is_active = True

        try:
            user.full_clean()
        except ValidationError as e:
            title = "Can not approve user '%s'" % user.username
            self.alert(e.messages, title=title)
            return

        user.save()

        self.populate_users_list()
        self._disable_actions()

    def _remove_evt(self):
        user_id = self._list.selected_row_id
        user = User.objects.get(pk=user_id)

        user.delete()

        self.populate_users_list()
        self._disable_actions()
