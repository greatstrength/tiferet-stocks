"""Tiferet Stocks CLI Request Binding"""

# *** imports

# ** core
from typing import Any, Callable, Dict, Tuple

# ** infra
from tiferet.blueprints.cli import parse_cli_args_handler as core_parse_cli_args_handler

# ** app
from tiferet_stocks import assets as a

# *** functions

# ** function: bind_cli_request
def bind_cli_request(feature_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Translate public CLI argument names without changing domain contracts.

    :param feature_id: The command's matching feature id.
    :type feature_id: str
    :param data: The parsed CLI request values.
    :type data: Dict[str, Any]
    :return: A new request dictionary using the feature's existing names.
    :rtype: Dict[str, Any]
    '''

    # Keep the parser-owned dictionary unchanged.
    bound = dict(data)

    # Positional symbol vocabulary differs from the existing library contracts.
    if feature_id == a.SYMBOLS_GET_FEATURE_ID:
        bound['id'] = bound.pop('symbol')
    elif feature_id == a.SYMBOLS_RESOLVE_FEATURE_ID:
        bound['ids'] = bound.pop('symbols')
        bound['exchanges'] = bound.pop('expected_exchanges', None)

    # All other commands already use the feature's parameter names.
    return bound

# *** blueprints

# ** blueprint: parse_cli_args_handler
def parse_cli_args_handler(list_commands: Callable, get_parent_args: Callable) -> Callable:
    '''
    Adapt the released core parser through its public callable factory.

    :param list_commands: The configured command catalog reader.
    :type list_commands: Callable
    :param get_parent_args: The configured parent-argument reader.
    :type get_parent_args: Callable
    :return: A parser returning feature id, headers and bound request data.
    :rtype: Callable
    '''

    # Delegate argument validation, scalar/list/dict interpretation and ids to core.
    parse = core_parse_cli_args_handler(list_commands=list_commands, get_parent_args=get_parent_args)

    # Add only the consumer-facing name translation after core parsing succeeds.
    def handler(argv: list | None = None) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
        '''
        Parse argv and bind it to the unchanged feature signature.

        :param argv: The explicit CLI tokens, or None for process argv.
        :type argv: list | None
        :return: The feature id, headers and adapted request data.
        :rtype: Tuple[str, Dict[str, str], Dict[str, Any]]
        '''

        # Preserve core headers while copying and adapting only request data.
        feature_id, headers, data = parse(argv=argv)
        return feature_id, headers, bind_cli_request(feature_id, data)

    # Return a real callable for subsequent public CLI session composition.
    return handler
