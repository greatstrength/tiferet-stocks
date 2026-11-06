"""Tiferet Stocks CLI Request Binding"""

# *** imports

# ** core
import argparse
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

# ** infra
from tiferet import assets as core_assets
from tiferet.blueprints import cli as core_cli
from tiferet.blueprints import core
from tiferet.blueprints.cli import parse_cli_args_handler as core_parse_cli_args_handler
from tiferet.contexts.cli import CliSessionContext

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.contexts import StocksCliRequestContext

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

# ** blueprint: create_cli_request_context
def create_cli_request_context(interface_id: str,
                               feature_id: str,
                               headers: Dict[str, str] | None = None,
                               data: Dict[str, Any] | None = None) -> StocksCliRequestContext:
    '''
    Compose a stock-aware response context through the normal request contract.

    :param interface_id: The active CLI session id.
    :type interface_id: str
    :param feature_id: The unchanged dispatched feature id.
    :type feature_id: str
    :param headers: Core command headers.
    :type headers: Dict[str, str] | None
    :param data: The bound feature request.
    :type data: Dict[str, Any] | None
    :return: The stock-aware CLI request context.
    :rtype: StocksCliRequestContext
    '''

    # Preserve the core request construction shape while specializing only presentation.
    return StocksCliRequestContext(
        headers={**(headers or {}), 'interface_id': interface_id},
        data=data,
        feature_id=feature_id,
    )

# ** blueprint: build_cli
def build_cli(app_config: str = 'config.yml', argv: list | None = None) -> Any:
    '''
    Run the stocks CLI using public released-core composition factories.

    :param app_config: The CWD-relative or explicit configuration path.
    :type app_config: str
    :param argv: Command tokens, or None for process argv.
    :type argv: list | None
    :return: The native CLI output model or primitive response.
    :rtype: Any
    '''

    # Resolve only the configuration path; resource paths retain core's CWD semantics.
    config_path = str(Path(app_config).resolve())
    cache = core_cli.build_cli_cache()
    session = core.get_app_session(a.STOCKS_CLI_SESSION_ID, cache=cache, app_config=config_path)

    # Point all core configuration readers at the explicitly selected document.
    session.constants = {
        **(session.constants or {}),
        **{key: config_path for key in core_assets.app.CORE_DEFAULT_CONSTANTS},
    }

    # Build the same container/resolver and catalog handlers as the public core CLI.
    container = core.build_app_service_container(cache, session)
    resolver = core.build_service_resolver(container)
    commands = core_cli.list_commands_handler(cache, resolver.get_dependency)
    parent_args = core_cli.get_parent_args_handler(resolver.get_dependency)
    parse = parse_cli_args_handler(list_commands=commands, get_parent_args=parent_args)

    # Inject the approved request/presentation adapters, without assigning private slots.
    context = core.compose_session_context(
        CliSessionContext,
        session,
        cache,
        resolver,
        create_request_handler=create_cli_request_context,
        response_handler=core.response_handler,
        parse_cli_args=parse,
        list_commands_handler=commands,
        get_parent_args_handler=parent_args,
    )

    # Core owns final printing, configured error handling and exit codes.
    return context.run(argv=argv)

# ** blueprint: main
def main(argv: list | None = None) -> None:
    '''
    Preparse only --config, then delegate the command line to core composition.

    :param argv: Explicit tokens, or None for the console script's process argv.
    :type argv: list | None
    :return: None so a successful console script exits zero.
    :rtype: None
    '''

    # Mirror core's admin entrypoint without replacing its command parser.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--config', default='config.yml', help='Path to the app configuration file (default: config.yml).')
    selected, remaining = parser.parse_known_args(args=argv)

    # Ignore the returned output model; setuptools must not treat it as an exit status.
    build_cli(app_config=selected.config, argv=remaining)
