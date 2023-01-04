from ...version_360.smart_contracts.types import *   # noqa: F401, F403
from ..common.types import (
    CalendarEvent, CalendarEvents, PostingInstruction, PostingInstructionBatch,
    PostingInstructionBatchDirective, HookDirectives, TransactionCode
)
from ...version_360.smart_contracts import types as types360
from ....utils.feature_flags import (
    is_fflag_enabled, CALENDAR_SUPPORT, TRANSACTION_CODE_FFLAG,
)


def types_registry():
    TYPES = types360.types_registry()

    if is_fflag_enabled(CALENDAR_SUPPORT):
        TYPES['CalendarEvent'] = CalendarEvent
        TYPES['CalendarEvents'] = CalendarEvents

    if is_fflag_enabled(TRANSACTION_CODE_FFLAG):
        TYPES['PostingInstruction'] = PostingInstruction
        TYPES['PostingInstructionBatch'] = PostingInstructionBatch
        TYPES['PostingInstructionBatchDirective'] = PostingInstructionBatchDirective
        TYPES['HookDirectives'] = HookDirectives
        TYPES['TransactionCode'] = TransactionCode

    return TYPES
