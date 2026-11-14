"""Tiferet Stocks CLI Request Binding"""

# *** imports

# ** core
import argparse
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# ** infra
from tiferet import TiferetError, assets as core_assets
from tiferet.assets.error import APP_SESSION_NOT_FOUND_ID
from tiferet.blueprints import app, core
from tiferet.blueprints.cli import parse_cli_args_handler as core_parse_cli_args_handler
from tiferet.blueprints.core import add_default_catalog
from tiferet.contexts.cache import CacheContext
from tiferet.contexts.cli import CliSessionContext
from tiferet.contexts.error import add_default_errors
from tiferet.contexts.feature import add_default_features
from tiferet.domain import AppServiceDependency, AppSession, CliArgument, CliCommand
from tiferet.interfaces.core import ServiceError
from tiferet.utils.file import FILE_NOT_FOUND_ID

# ** app
from tiferet_stocks import assets as a
from tiferet_stocks.contexts import StocksCliRequestContext

# *** functions

# ** function: get_stocks_cli_commands
def get_stocks_cli_commands(cache: CacheContext) -> List[CliCommand]:
    '''
    Return the stocks CLI commands seeded on the cache under the stocks prefix.

    :param cache: The cache context to read.
    :type cache: CacheContext
    :return: The seeded stocks CLI command domain objects.
    :rtype: List[CliCommand]
    '''

    # Return the seeded stocks commands as a list, in catalog order.
    return list(cache.get_by_prefix(*a.cli.STOCKS_CLI_COMMAND_CACHE_PREFIX).values())

# ** function: read_configured
def read_configured(get_dependency: Callable, event_id: str) -> List[Any]:
    '''
    Execute a configured CLI event, treating a missing configuration file as nothing configured.

    :param get_dependency: The DI resolution handler.
    :type get_dependency: Callable
    :param event_id: The app-flagged CLI event id.
    :type event_id: str
    :return: The configured records, or an empty list when the configuration file does not exist.
    :rtype: List[Any]
    '''

    # Resolve and execute the configured event at call time.
    try:
        return get_dependency(event_id, 'app').execute() or []

    # Only a missing file means nothing is configured; any other fault propagates.
    except ServiceError as error:
        if error.error_code != FILE_NOT_FOUND_ID:
            raise
        return []

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

# ** blueprint: build_cache
@add_default_catalog(
    a.cli.STOCKS_DEFAULT_COMMANDS,
    a.cli.STOCKS_CLI_COMMAND_CACHE_PREFIX,
    model=CliCommand,
)
@add_default_catalog(
    a.app.STOCKS_DEFAULT_SERVICES,
    core_assets.app.APP_SERVICE_CACHE_PREFIX,
    model=AppServiceDependency,
    id_field='service_id',
)
@add_default_catalog(
    a.symbol.STOCKS_DEFAULT_CONSTANTS,
    core_assets.app.APP_CONSTANT_CACHE_PREFIX,
)
@add_default_catalog(
    a.app.STOCKS_DEFAULT_APP_SESSIONS,
    core_assets.app.APP_SESSION_CACHE_PREFIX,
    model=AppSession,
    id_field='id',
)
@add_default_features(a.feature.STOCKS_DEFAULT_FEATURES)
@add_default_errors(a.error.DEFAULT_ERRORS)
def build_cache(cache: Dict[str, Any] = None) -> CacheContext:
    '''
    Build the stocks CLI bootstrap cache.

    Extends the standard ``app.build_cache``, as core's admin build_cache
    does, with the stocks errors, features, app sessions, app constants
    (the Yahoo default symbol aliases) and services, and the stocks CLI
    commands under the stocks cache prefix, so every stocks command runs
    with no configuration file.

    :param cache: An optional initial cache dictionary for the root namespace.
    :type cache: Dict[str, Any] | None
    :return: The pre-seeded stocks CLI cache context.
    :rtype: CacheContext
    '''

    # Delegate to the standard app cache builder; stacked decorators seed the stocks catalogs.
    return app.build_cache(cache=cache)

# ** blueprint: get_app_session
def get_app_session(cache: CacheContext, app_config: str, required: bool = False) -> AppSession:
    '''
    Load the stocks CLI session from the app config when it declares one, else from the cache.

    Configured items take precedence: core's get_app_session is called first without the cache, so
    the configured session and its service attributes win; the cache-seeded session is only the
    fallback when the config lacks the session, or when an optional config file does not exist.

    :param cache: The stocks CLI bootstrap cache.
    :type cache: CacheContext
    :param app_config: The resolved app configuration path; it need not exist unless required.
    :type app_config: str
    :param required: Whether a missing app configuration file is a fault (an explicit --config).
    :type required: bool
    :return: The app session.
    :rtype: AppSession
    '''

    # Resolve the configured session through core's app service.
    try:
        return core.get_app_session(a.STOCKS_CLI_SESSION_ID, app_config=app_config)

    # An undeclared session, or a missing optional file, falls back to the cache; any other fault propagates.
    except (TiferetError, ServiceError) as error:
        if error.error_code != APP_SESSION_NOT_FOUND_ID and (error.error_code != FILE_NOT_FOUND_ID or required):
            raise

    # Return the cache-seeded session through core's cache-first resolution.
    return core.get_app_session(a.STOCKS_CLI_SESSION_ID, cache=cache, app_config=app_config)

# ** blueprint: build_service_resolver
def build_service_resolver(app_container: Any) -> Any:
    '''
    Compose the stocks service resolver: the app container serves both the app flag and feature steps with no flag.

    :param app_container: The built app service container, holding the cached stocks services.
    :type app_container: DIAppServiceContainer
    :return: The service resolver.
    :rtype: ServiceResolver
    '''

    # Compose the core resolver, which registers the app container under the app flag.
    resolver = core.build_service_resolver(app_container)

    # Feature steps carry no flag, so the cached stocks services must answer them without a DI config read.
    resolver.add_container(app_container)

    # Return the resolver.
    return resolver

# ** blueprint: list_commands_handler
def list_commands_handler(cache: CacheContext, get_dependency: Callable) -> Callable:
    '''
    Build a zero-arg handler that assembles the stocks commands from the cache and the configured CLI service.

    :param cache: The stocks CLI bootstrap cache.
    :type cache: CacheContext
    :param get_dependency: The DI resolution handler.
    :type get_dependency: Callable
    :return: A closure that returns the CLI commands.
    :rtype: Callable
    '''

    # Return the handler closure bound to the cache and resolver.
    def handler() -> List[CliCommand]:

        # The cached stocks commands, then whatever the session's CLI service lists.
        return get_stocks_cli_commands(cache) + read_configured(get_dependency, core_assets.app.LIST_COMMANDS_EVT_ID)

    # Return the closure.
    return handler

# ** blueprint: get_parent_args_handler
def get_parent_args_handler(get_dependency: Callable) -> Callable:
    '''
    Build a zero-arg handler that returns the configured parent CLI arguments.

    :param get_dependency: The DI resolution handler.
    :type get_dependency: Callable
    :return: A closure that returns the parent arguments.
    :rtype: Callable
    '''

    # Return the handler closure bound to the resolver.
    def handler() -> List[CliArgument]:

        # The stocks catalog declares no parent arguments; only configured ones apply.
        return read_configured(get_dependency, core_assets.app.GET_PARENT_ARGS_EVT_ID)

    # Return the closure.
    return handler

# ** blueprint: build_cli
def build_cli(app_config: str = 'config.yml', argv: list | None = None, required: bool = False) -> Any:
    '''
    Run the stocks CLI from the stocks bootstrap cache; the app configuration file is optional unless required.

    :param app_config: The CWD-relative or explicit configuration path.
    :type app_config: str
    :param argv: Command tokens, or None for process argv.
    :type argv: list | None
    :param required: Whether a missing app configuration file is a fault (an explicit --config).
    :type required: bool
    :return: The native CLI output model or primitive response.
    :rtype: Any
    '''

    # The stocks session, services, features, errors, commands and aliases are seeded on the cache;
    # a session the app config declares takes precedence, and the cached session is the fallback.
    config_path = str(Path(app_config).resolve())
    cache = build_cache()
    session = get_app_session(cache, config_path, required=required)

    # Point all core configuration readers at the selected document.
    session.constants = {
        **(session.constants or {}),
        **{key: config_path for key in core_assets.app.CORE_DEFAULT_CONSTANTS},
    }

    # Build the container/resolver and the stocks catalog handlers.
    container = core.build_app_service_container(cache, app_instance=session)
    resolver = build_service_resolver(container)
    commands = list_commands_handler(cache, resolver.get_dependency)
    parent_args = get_parent_args_handler(resolver.get_dependency)
    parse = parse_cli_args_handler(list_commands=commands, get_parent_args=parent_args)

    # Inject the request/presentation adapters through public composition.
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
    Preparse only --config, then delegate the command line to the stocks CLI.

    :param argv: Explicit tokens, or None for the console script's process argv.
    :type argv: list | None
    :return: None so a successful console script exits zero.
    :rtype: None
    '''

    # Mirror core's admin entrypoint without replacing its command parser.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('--config', default=None, help='Path to the app configuration file (default: config.yml, optional).')
    selected, remaining = parser.parse_known_args(args=argv)

    # An explicit --config must exist; the default config.yml is optional.
    # Ignore the returned output model; setuptools must not treat it as an exit status.
    build_cli(app_config=selected.config or 'config.yml', argv=remaining, required=selected.config is not None)
