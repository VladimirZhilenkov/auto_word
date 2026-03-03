"""Dialogs module for Document Generator application."""

from .listener_form import ListenerFormDialog
from .program_form import ProgramFormDialog
from .import_dialog import ImportDialog
from .generate_dialog import GenerateDialog
from .program_listeners_dialog import ProgramListenersDialog
from .template_help_dialog import TemplateHelpDialog
from .backup_dialog import BackupDialog
from .database_config_dialog import DatabaseConfigDialog
from .journal_entry_dialog import JournalEntryDialog
from .order_create_dialog import OrderCreateDialog
from .order_edit_dialog import OrderEditDialog

__all__ = [
    'ListenerFormDialog',
    'ProgramFormDialog',
    'ImportDialog',
    'GenerateDialog',
    'ProgramListenersDialog',
    'TemplateHelpDialog',
    'BackupDialog',
    'DatabaseConfigDialog',
    'JournalEntryDialog',
    'OrderCreateDialog',
    'OrderEditDialog',
]
