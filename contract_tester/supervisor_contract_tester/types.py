import decimal
import typing
import dateutil.parser
from unittest.mock import Mock
import datetime
import math
import collections
from enum import Enum
import dateutil.relativedelta
import json
import calendar

# Fixed Types
DEFAULT_ADDRESS = 'DEFAULT'
DEFAULT_ASSET = 'COMMERCIAL_BANK_MONEY'
TRANSACTION_REFERENCE_FIELD_NAME = 'description'

# Exceptions
class InvalidContractParameter(Exception):
    pass

class Rejected(Exception):
    def __init__(self, message, reason_code):
        self.message = message
        self.reason_code = reason_code


# Enums
class Level(Enum):
    GLOBAL = '1'
    INSTANCE = '3'
    TEMPLATE = '2'

class Features(Enum):
    CARD = '4'
    INVESTMENT = '7'
    JOINT_ACCOUNT = '6'
    MANDATES = '1'
    MULTIPLE_OWNERS = '3'
    SUB_ACCOUNTS = '5'

class NoteType(Enum):
    RAW_TEXT = '1'
    REASON_CODE = '2'

class NumberKind(Enum):
    MONEY = 'money'
    MONTHS = 'months'
    PERCENTAGE = 'percentage'
    PLAIN = 'plain'

class Phase(Enum):
    COMMITTED = 'committed'
    PENDING_IN = 'pending_in'
    PENDING_OUT = 'pending_out'

class PostingInstructionType(Enum):
    AUTHORISATION = 'Authorisation'
    AUTHORISATION_ADJUSTMENT = 'AuthorisationAdjustment'
    CUSTOM_INSTRUCTION = 'CustomInstruction'
    HARD_SETTLEMENT = 'HardSettlement'
    RELEASE = 'Release'
    SETTLEMENT = 'Settlement'
    TRANSFER = 'Transfer'

class RejectedReason(Enum):
    AGAINST_TNC = '3'
    CLIENT_CUSTOM_REASON = '4'
    INSUFFICIENT_FUNDS = '1'
    WRONG_DENOMINATION = '2'

class Tside(Enum):
    ASSET = '1'
    LIABILITY = '2'

class UpdatePermission(Enum):
    FIXED = '1'
    OPS_EDITABLE = '2'
    USER_EDITABLE = '3'
    USER_EDITABLE_WITH_OPS_PERMISSION = '4'

class AccountIdShape:
    pass

class AddAccountNoteDirective:
    def __init__(self, idempotency_key = None, account_id = None, body = None, note_type = None, date = None, is_visible_to_customer = None):
        self.idempotency_key = idempotency_key
        self.account_id = account_id
        self.body = body
        self.note_type = note_type
        self.date = date
        self.is_visible_to_customer = is_visible_to_customer


class AddressDetails:
    def __init__(self, account_address = None, description = None, tags = None):
        self.account_address = account_address
        self.description = description
        self.tags = tags


class AmendScheduleDirective:
    def __init__(self, event_type = None, new_schedule = None, request_id = None, account_id = None):
        self.event_type = event_type
        self.new_schedule = new_schedule
        self.request_id = request_id
        self.account_id = account_id


class Balance:
    def __init__(self, credit = None, debit = None, net = None):
        self.credit = credit
        self.debit = debit
        self.net = net


class BalanceDefaultDict(dict):
    pass

class BalanceTimeseries(list):
    def __init__(self, iterable = None):
        super().__init__(iterable)
        self.iterable = iterable
        self.at = Mock()
        self.before = Mock()
        self.latest = Mock()
        self.all = Mock()



class ClientTransaction(list):
    def __init__(self, posting_instructions=None):
        super().__init__(posting_instructions)
        self.is_custom = Mock()
        self.cancelled = Mock()
        self.start_time = Mock()
        self.effects = Mock()
        self.balances = Mock()

class ClientTransactionEffects:
    def __init__(self, authorised = None, released = None, settled = None, unsettled = None):
        self.authorised = authorised
        self.released = released
        self.settled = settled
        self.unsettled = unsettled


class ClientTransactionEffectsDefaultDict(dict):
    pass

class DateShape:
    def __init__(self, min_date = None, max_date = None):
        self.min_date = min_date
        self.max_date = max_date


class DenominationShape:
    def __init__(self, permitted_denominations = None):
        self.permitted_denominations = permitted_denominations


class EventType:
    def __init__(self, name = None, scheduler_tag_ids = None, overrides_event_types = None):
        self.name = name
        self.scheduler_tag_ids = scheduler_tag_ids
        self.overrides_event_types = overrides_event_types


class EventTypesGroup:
    def __init__(self, name = None, event_types_order = None):
        self.name = name
        self.event_types_order = event_types_order


class FlagTimeseries(list):
    def __init__(self, iterable = None):
        super().__init__(iterable)
        self.iterable = iterable
        self.at = Mock()
        self.before = Mock()
        self.latest = Mock()
        self.all = Mock()


class HookDirectives:
    def __init__(self, add_account_note_directives = None, amend_schedule_directives = None, remove_schedules_directives = None, workflow_start_directives = None, posting_instruction_batch_directives = None, update_account_event_type_directives = None):
        self.add_account_note_directives = add_account_note_directives
        self.amend_schedule_directives = amend_schedule_directives
        self.remove_schedules_directives = remove_schedules_directives
        self.workflow_start_directives = workflow_start_directives
        self.posting_instruction_batch_directives = posting_instruction_batch_directives
        self.update_account_event_type_directives = update_account_event_type_directives


class NumberShape:
    def __init__(self, kind = None, min_value = None, max_value = None, step = None):
        self.kind = kind
        self.min_value = min_value
        self.max_value = max_value
        self.step = step


class OptionalShape:
    def __init__(self, shape = None):
        self.shape = shape


class OptionalValue:
    def __init__(self, value = None):
        self.value = value
        self.is_set = Mock()


class Parameter:
    def __init__(self, name = None, description = None, display_name = None, level = None, value = None, default_value = None, update_permission = None, derived = None, shape = None):
        self.name = name
        self.description = description
        self.display_name = display_name
        self.level = level
        self.value = value
        self.default_value = default_value
        self.update_permission = update_permission
        self.derived = derived
        self.shape = shape


class ParameterTimeseries(list):
    def __init__(self, iterable = None):
        super().__init__(iterable)
        self.iterable = iterable
        self.at = Mock()
        self.before = Mock()
        self.latest = Mock()
        self.all = Mock()


class PostingInstruction:
    def __init__(self, account_address = None, account_id = None, amount = None, asset = None, credit = None, denomination = None, final = None, phase = None, id = None, type = None, client_transaction_id = None, instruction_details = None, pics = None, custom_instruction_grouping_key = None, override_all_restrictions = None, advice = None, transaction_code = None):
        self.account_address = account_address
        self.account_id = account_id
        self.amount = amount
        self.asset = asset
        self.credit = credit
        self.denomination = denomination
        self.final = final
        self.phase = phase
        self.id = id
        self.type = type
        self.client_transaction_id = client_transaction_id
        self.instruction_details = instruction_details
        self.pics = pics
        self.custom_instruction_grouping_key = custom_instruction_grouping_key
        self.override_all_restrictions = override_all_restrictions
        self.advice = advice
        self.transaction_code = transaction_code
        self.batch_details = Mock()
        self.client_batch_id = Mock()
        self.client_id = Mock()
        self.value_timestamp = Mock()
        self.batch_id = Mock()
        self.insertion_timestamp = Mock()
        self.balances = Mock()


class PostingInstructionBatch(list):
    def __init__(self, batch_details = None, client_batch_id = None, value_timestamp = None, batch_id = None, client_id = None, posting_instructions = None, insertion_timestamp = None):
        super().__init__(posting_instructions)
        self.batch_details = batch_details
        self.client_batch_id = client_batch_id
        self.value_timestamp = value_timestamp
        self.batch_id = batch_id
        self.client_id = client_id
        self.posting_instructions = posting_instructions
        self.insertion_timestamp = insertion_timestamp
        self.balances = Mock()


class PostingInstructionBatchDirective:
    def __init__(self, request_id = None, posting_instruction_batch = None):
        self.request_id = request_id
        self.posting_instruction_batch = posting_instruction_batch


class RemoveSchedulesDirective:
    def __init__(self, account_id = None, event_types = None, request_id = None):
        self.account_id = account_id
        self.event_types = event_types
        self.request_id = request_id


class SmartContractDescriptor:
    def __init__(self, alias = None, smart_contract_version_id = None, supervise_post_posting_hook = None):
        self.alias = alias
        self.smart_contract_version_id = smart_contract_version_id
        self.supervise_post_posting_hook = supervise_post_posting_hook


class StringShape:
    pass

class UnionItem:
    def __init__(self, key = None, display_name = None):
        self.key = key
        self.display_name = display_name


class UnionItemValue:
    def __init__(self, key = None):
        self.key = key


class UnionShape:
    def __init__(self, items = None):
        self.items = items


class WorkflowStartDirective:
    def __init__(self, workflow = None, context = None, account_id = None, idempotency_key = None):
        self.workflow = workflow
        self.context = context
        self.account_id = account_id
        self.idempotency_key = idempotency_key


class CalendarEvent:
    def __init__(self, id = None, calendar_id = None, start_timestamp = None, end_timestamp = None):
        self.id = id
        self.calendar_id = calendar_id
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp


class CalendarEvents(list):
    def __init__(self, calendar_events = None):
        self.calendar_events = calendar_events


class TransactionCode:
    def __init__(self, domain = None, family = None, subfamily = None):
        self.domain = domain
        self.family = family
        self.subfamily = subfamily


class EventTypeSchedule:
    def __init__(self, day = None, day_of_week = None, hour = None, minute = None, second = None, month = None, year = None):
        self.day = day
        self.day_of_week = day_of_week
        self.hour = hour
        self.minute = minute
        self.second = second
        self.month = month
        self.year = year


class UpdateAccountEventTypeDirective:
    def __init__(self, account_id = None, event_type = None, schedule = None, end_datetime = None):
        self.account_id = account_id
        self.event_type = event_type
        self.schedule = schedule
        self.end_datetime = end_datetime


class UpdatePlanEventTypeDirective:
    def __init__(self, plan_id = None, event_type = None, schedule = None, end_datetime = None):
        self.plan_id = plan_id
        self.event_type = event_type
        self.schedule = schedule
        self.end_datetime = end_datetime



_ALL_TYPES = {
    'CalendarEvents': CalendarEvents,
    'Set': typing.Set,
    'ROUND_HALF_UP': decimal.ROUND_HALF_UP,
    'UpdatePermission': UpdatePermission,
    'OptionalShape': OptionalShape,
    'math': math,
    'EventTypeSchedule': EventTypeSchedule,
    'calendar': calendar,
    'Tside': Tside,
    'EventType': EventType,
    'Rejected': Rejected,
    'Callable': typing.Callable,
    'ROUND_HALF_DOWN': decimal.ROUND_HALF_DOWN,
    'Mapping': typing.Mapping,
    'NumberKind': NumberKind,
    'UnionShape': UnionShape,
    'parse_to_datetime': dateutil.parser.parse,
    'DEFAULT_ADDRESS': DEFAULT_ADDRESS,
    'PostingInstruction': PostingInstruction,
    'ROUND_FLOOR': decimal.ROUND_FLOOR,
    'ClientTransactionEffects': ClientTransactionEffects,
    'UnionItem': UnionItem,
    'json_dumps': json.dumps,
    'Features': Features,
    'ROUND_CEILING': decimal.ROUND_CEILING,
    'json_loads': json.loads,
    'UnionItemValue': UnionItemValue,
    'UpdatePlanEventTypeDirective': UpdatePlanEventTypeDirective,
    'List': typing.List,
    'NewType': typing.NewType,
    'Phase': Phase,
    'BalanceTimeseries': BalanceTimeseries,
    'NoReturn': typing.NoReturn,
    'RejectedReason': RejectedReason,
    'ClientTransaction': ClientTransaction,
    'Iterator': typing.Iterator,
    'Dict': typing.Dict,
    'Type': typing.Type,
    'Parameter': Parameter,
    'AddressDetails': AddressDetails,
    'EventTypesGroup': EventTypesGroup,
    'ROUND_05UP': decimal.ROUND_05UP,
    'Decimal': decimal.Decimal,
    'BalanceDefaultDict': BalanceDefaultDict,
    'ParameterTimeseries': ParameterTimeseries,
    'CalendarEvent': CalendarEvent,
    'Any': typing.Any,
    'HookDirectives': HookDirectives,
    'TransactionCode': TransactionCode,
    'timedelta': dateutil.relativedelta.relativedelta,
    'PostingInstructionBatchDirective': PostingInstructionBatchDirective,
    'FlagTimeseries': FlagTimeseries,
    'OptionalValue': OptionalValue,
    'PostingInstructionType': PostingInstructionType,
    'DenominationShape': DenominationShape,
    'AccountIdShape': AccountIdShape,
    'Level': Level,
    'Iterable': typing.Iterable,
    'defaultdict': collections.defaultdict,
    'UpdateAccountEventTypeDirective': UpdateAccountEventTypeDirective,
    'Union': typing.Union,
    'SmartContractDescriptor': SmartContractDescriptor,
    'ROUND_DOWN': decimal.ROUND_DOWN,
    'StringShape': StringShape,
    'AddAccountNoteDirective': AddAccountNoteDirective,
    'NumberShape': NumberShape,
    'AmendScheduleDirective': AmendScheduleDirective,
    'ClientTransactionEffectsDefaultDict': ClientTransactionEffectsDefaultDict,
    'Tuple': typing.Tuple,
    'NoteType': NoteType,
    'TRANSACTION_REFERENCE_FIELD_NAME': TRANSACTION_REFERENCE_FIELD_NAME,
    'DateShape': DateShape,
    'InvalidContractParameter': InvalidContractParameter,
    'WorkflowStartDirective': WorkflowStartDirective,
    'DefaultDict': typing.DefaultDict,
    'ROUND_HALF_EVEN': decimal.ROUND_HALF_EVEN,
    'datetime': datetime.datetime,
    'NamedTuple': typing.NamedTuple,
    'Optional': typing.Optional,
    'DEFAULT_ASSET': DEFAULT_ASSET,
    'PostingInstructionBatch': PostingInstructionBatch,
    'RemoveSchedulesDirective': RemoveSchedulesDirective,
    'Balance': Balance,
}

_WHITELISTED_BUILTINS = {
    'all',
    'iter',
    'dir',
    'float',
    'tuple',
    'list',
    'min',
    'sorted',
    'max',
    'set',
    'complex',
    'id',
    'round',
    'dict',
    'bool',
    'reversed',
    'False',
    'None',
    'map',
    'int',
    'oct',
    'ord',
    'filter',
    'bin',
    'format',
    'hex',
    'frozenset',
    'range',
    'bytes',
    'any',
    'print',
    'abs',
    'bytearray',
    'repr',
    'len',
    'str',
    'True',
    'slice',
    'divmod',
    'hash',
    'next',
    'zip',
    'enumerate',
    'sum',
    'chr',
    'pow',
}

_SUPPORTED_HOOK_NAMES = {
    'post_activate_code',
    'execution_schedules',
    'scheduled_code',
    'close_code',
    'upgrade_code',
    'post_parameter_change_code',
    'pre_parameter_change_code',
    'pre_posting_code',
    'post_posting_code',
    'derived_parameters',
}

