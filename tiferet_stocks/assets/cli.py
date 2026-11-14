"""Tiferet Stocks CLI Command Catalog

Command ids, the stocks cache prefix, individually named command data and
the STOCKS_DEFAULT_COMMANDS group dict seeded by the stocks CLI blueprint.
"""

# *** imports

# ** core
from typing import Any, Dict, Tuple

# ** infra
from tiferet.assets.core import create_default_cli_argument, create_default_cli_command_data

# ** app
from tiferet_stocks.assets.core import (
    QUOTES_GET_FEATURE_ID,
    QUOTES_HISTORY_FEATURE_ID,
    SYMBOLS_GET_FEATURE_ID,
    SYMBOLS_RESOLVE_FEATURE_ID,
    EXCHANGES_LIST_FEATURE_ID,
    WATCHLISTS_LIST_FEATURE_ID,
    WATCHLISTS_GET_FEATURE_ID,
    WATCHLISTS_CREATE_FEATURE_ID,
    WATCHLISTS_UPDATE_FEATURE_ID,
    WATCHLISTS_DELETE_FEATURE_ID,
    WATCHLISTS_ADD_FEATURE_ID,
    WATCHLISTS_REMOVE_FEATURE_ID,
    WATCHLISTS_MOVE_FEATURE_ID,
)

# *** constants (ids_sessions)

# ** constant: stocks_cli_session_id
STOCKS_CLI_SESSION_ID = 'stocks_cli'

# *** constants (ids_commands)

# ** constant: quotes_get_cli_cmd_id
QUOTES_GET_CLI_CMD_ID = QUOTES_GET_FEATURE_ID

# ** constant: quotes_history_cli_cmd_id
QUOTES_HISTORY_CLI_CMD_ID = QUOTES_HISTORY_FEATURE_ID

# ** constant: symbols_get_cli_cmd_id
SYMBOLS_GET_CLI_CMD_ID = SYMBOLS_GET_FEATURE_ID

# ** constant: symbols_resolve_cli_cmd_id
SYMBOLS_RESOLVE_CLI_CMD_ID = SYMBOLS_RESOLVE_FEATURE_ID

# ** constant: exchanges_list_cli_cmd_id
EXCHANGES_LIST_CLI_CMD_ID = EXCHANGES_LIST_FEATURE_ID

# ** constant: watchlists_list_cli_cmd_id
WATCHLISTS_LIST_CLI_CMD_ID = WATCHLISTS_LIST_FEATURE_ID

# ** constant: watchlists_get_cli_cmd_id
WATCHLISTS_GET_CLI_CMD_ID = WATCHLISTS_GET_FEATURE_ID

# ** constant: watchlists_create_cli_cmd_id
WATCHLISTS_CREATE_CLI_CMD_ID = WATCHLISTS_CREATE_FEATURE_ID

# ** constant: watchlists_update_cli_cmd_id
WATCHLISTS_UPDATE_CLI_CMD_ID = WATCHLISTS_UPDATE_FEATURE_ID

# ** constant: watchlists_delete_cli_cmd_id
WATCHLISTS_DELETE_CLI_CMD_ID = WATCHLISTS_DELETE_FEATURE_ID

# ** constant: watchlists_add_cli_cmd_id
WATCHLISTS_ADD_CLI_CMD_ID = WATCHLISTS_ADD_FEATURE_ID

# ** constant: watchlists_remove_cli_cmd_id
WATCHLISTS_REMOVE_CLI_CMD_ID = WATCHLISTS_REMOVE_FEATURE_ID

# ** constant: watchlists_move_cli_cmd_id
WATCHLISTS_MOVE_CLI_CMD_ID = WATCHLISTS_MOVE_FEATURE_ID

# *** constants (cache)

# ** constant: stocks_cli_command_cache_prefix
STOCKS_CLI_COMMAND_CACHE_PREFIX: Tuple[str, ...] = ('stocks', 'cli', 'commands')

# *** constants (commands)

# ** constant: quotes_get_cli_cmd_data
QUOTES_GET_CLI_CMD_DATA = create_default_cli_command_data(
    'get',
    'quotes',
    'Quotes Get',
    description='Run the quotes.get feature.',
    arguments=[
        create_default_cli_argument(
            ['symbols'],
            description='One or more symbol tickers.',
            type='list',
            nargs='+',
        ),
    ],
)

# ** constant: quotes_history_cli_cmd_data
QUOTES_HISTORY_CLI_CMD_DATA = create_default_cli_command_data(
    'history',
    'quotes',
    'Quotes History',
    description='Run the quotes.history feature.',
    arguments=[
        create_default_cli_argument(
            ['symbol'],
            description='The symbol ticker.',
            type='str',
        ),
        create_default_cli_argument(
            ['--start'],
            description='The first inclusive ISO date.',
            type='str',
            required=True,
        ),
        create_default_cli_argument(
            ['--end'],
            description='The last inclusive ISO date.',
            type='str',
            required=True,
        ),
    ],
)

# ** constant: symbols_get_cli_cmd_data
SYMBOLS_GET_CLI_CMD_DATA = create_default_cli_command_data(
    'get',
    'symbols',
    'Symbols Get',
    description='Run the symbols.get feature.',
    arguments=[
        create_default_cli_argument(
            ['symbol'],
            description='The symbol ticker.',
            type='str',
        ),
    ],
)

# ** constant: symbols_resolve_cli_cmd_data
SYMBOLS_RESOLVE_CLI_CMD_DATA = create_default_cli_command_data(
    'resolve',
    'symbols',
    'Symbols Resolve',
    description='Run the symbols.resolve feature.',
    arguments=[
        create_default_cli_argument(
            ['symbols'],
            description='One or more symbol tickers.',
            type='list',
            nargs='+',
        ),
        create_default_cli_argument(
            ['--expected-exchanges'],
            description='Expected exchanges as SYM=EXCHANGE tokens.',
            type='dict',
            nargs='+',
        ),
    ],
)

# ** constant: exchanges_list_cli_cmd_data
EXCHANGES_LIST_CLI_CMD_DATA = create_default_cli_command_data(
    'list',
    'exchanges',
    'Exchanges List',
    description='Run the exchanges.list feature.',
)

# ** constant: watchlists_list_cli_cmd_data
WATCHLISTS_LIST_CLI_CMD_DATA = create_default_cli_command_data(
    'list',
    'watchlists',
    'Watchlists List',
    description='Run the watchlists.list feature.',
)

# ** constant: watchlists_get_cli_cmd_data
WATCHLISTS_GET_CLI_CMD_DATA = create_default_cli_command_data(
    'get',
    'watchlists',
    'Watchlists Get',
    description='Run the watchlists.get feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The watchlist id.',
            type='str',
        ),
    ],
)

# ** constant: watchlists_create_cli_cmd_data
WATCHLISTS_CREATE_CLI_CMD_DATA = create_default_cli_command_data(
    'create',
    'watchlists',
    'Watchlists Create',
    description='Run the watchlists.create feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The new watchlist id.',
            type='str',
        ),
        create_default_cli_argument(
            ['--name'],
            description='The display name.',
            type='str',
            required=True,
        ),
        create_default_cli_argument(
            ['--description'],
            description='The optional description.',
            type='str',
        ),
        create_default_cli_argument(
            ['--symbol-ids'],
            description='The initial ordered tickers.',
            type='list',
            nargs='+',
        ),
    ],
)

# ** constant: watchlists_update_cli_cmd_data
WATCHLISTS_UPDATE_CLI_CMD_DATA = create_default_cli_command_data(
    'update',
    'watchlists',
    'Watchlists Update',
    description='Run the watchlists.update feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The existing watchlist id.',
            type='str',
        ),
        create_default_cli_argument(
            ['--name'],
            description='The new display name.',
            type='str',
        ),
        create_default_cli_argument(
            ['--description'],
            description='The new description.',
            type='str',
        ),
    ],
)

# ** constant: watchlists_delete_cli_cmd_data
WATCHLISTS_DELETE_CLI_CMD_DATA = create_default_cli_command_data(
    'delete',
    'watchlists',
    'Watchlists Delete',
    description='Run the watchlists.delete feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The watchlist id.',
            type='str',
        ),
    ],
)

# ** constant: watchlists_add_cli_cmd_data
WATCHLISTS_ADD_CLI_CMD_DATA = create_default_cli_command_data(
    'add',
    'watchlists',
    'Watchlists Add',
    description='Run the watchlists.add feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The watchlist id.',
            type='str',
        ),
        create_default_cli_argument(
            ['symbol_id'],
            description='The ticker to add.',
            type='str',
        ),
        create_default_cli_argument(
            ['--index'],
            description='The zero-based insertion position or -1 for the end.',
            type='int',
            default='-1',
        ),
        create_default_cli_argument(
            ['--create'],
            description='Create the watchlist, named by its id, when it does not exist; without it a missing watchlist fails.',
            type='bool',
        ),
    ],
)

# ** constant: watchlists_remove_cli_cmd_data
WATCHLISTS_REMOVE_CLI_CMD_DATA = create_default_cli_command_data(
    'remove',
    'watchlists',
    'Watchlists Remove',
    description='Run the watchlists.remove feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The watchlist id.',
            type='str',
        ),
        create_default_cli_argument(
            ['symbol_id'],
            description='The ticker to remove.',
            type='str',
        ),
    ],
)

# ** constant: watchlists_move_cli_cmd_data
WATCHLISTS_MOVE_CLI_CMD_DATA = create_default_cli_command_data(
    'move',
    'watchlists',
    'Watchlists Move',
    description='Run the watchlists.move feature.',
    arguments=[
        create_default_cli_argument(
            ['id'],
            description='The watchlist id.',
            type='str',
        ),
        create_default_cli_argument(
            ['symbol_id'],
            description='The ticker to move.',
            type='str',
        ),
        create_default_cli_argument(
            ['--to-index'],
            description='The final zero-based position or -1 for the end.',
            type='int',
            default='-1',
        ),
    ],
)

# *** constants (groups)

# ** constant: stocks_default_commands
STOCKS_DEFAULT_COMMANDS: Dict[str, Dict[str, Any]] = {
    QUOTES_GET_CLI_CMD_ID: QUOTES_GET_CLI_CMD_DATA,
    QUOTES_HISTORY_CLI_CMD_ID: QUOTES_HISTORY_CLI_CMD_DATA,
    SYMBOLS_GET_CLI_CMD_ID: SYMBOLS_GET_CLI_CMD_DATA,
    SYMBOLS_RESOLVE_CLI_CMD_ID: SYMBOLS_RESOLVE_CLI_CMD_DATA,
    EXCHANGES_LIST_CLI_CMD_ID: EXCHANGES_LIST_CLI_CMD_DATA,
    WATCHLISTS_LIST_CLI_CMD_ID: WATCHLISTS_LIST_CLI_CMD_DATA,
    WATCHLISTS_GET_CLI_CMD_ID: WATCHLISTS_GET_CLI_CMD_DATA,
    WATCHLISTS_CREATE_CLI_CMD_ID: WATCHLISTS_CREATE_CLI_CMD_DATA,
    WATCHLISTS_UPDATE_CLI_CMD_ID: WATCHLISTS_UPDATE_CLI_CMD_DATA,
    WATCHLISTS_DELETE_CLI_CMD_ID: WATCHLISTS_DELETE_CLI_CMD_DATA,
    WATCHLISTS_ADD_CLI_CMD_ID: WATCHLISTS_ADD_CLI_CMD_DATA,
    WATCHLISTS_REMOVE_CLI_CMD_ID: WATCHLISTS_REMOVE_CLI_CMD_DATA,
    WATCHLISTS_MOVE_CLI_CMD_ID: WATCHLISTS_MOVE_CLI_CMD_DATA,
}
