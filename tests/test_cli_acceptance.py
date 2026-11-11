"""Installed, offline thirteen-command CLI acceptance."""

# *** imports

# ** core
from pathlib import Path
import subprocess

# ** infra
import pytest
import yaml

# ** app
from tiferet_stocks.domain import EXCHANGES

# *** functions

# ** function: assert_success
def assert_success(result):
    '''
    Require a real zero-exit response rather than merely some stdout.

    :param result: The domain answer or completed subprocess response under test.
    :type result: Any
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    assert result.returncode == 0, result.stdout + result.stderr
    assert 'Traceback' not in result.stdout + result.stderr

# ** function: assert_error
def assert_error(result, error_id):
    '''
    Require released core's configured domain-error exit and message.

    :param result: The domain answer or completed subprocess response under test.
    :type result: Any
    :param error_id: The expected configured domain error id.
    :type error_id: str
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    assert result.returncode == 1, result.stdout + result.stderr
    assert f'CLI-CONFIGURED-{error_id}: ' in result.stderr
    assert 'Traceback' not in result.stdout + result.stderr

# ** function: read_ids
def read_ids(console):
    '''
    Read persisted ordering independently of CLI rendering.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: The configured fixture value or completed response.
    :rtype: Any
    '''

    return yaml.safe_load(console['storage'].read_text())['watchlists']['etfs']['symbol_ids']

# *** fixtures

# ** fixture: console
@pytest.fixture
def console(installed_cli, tmp_path):
    '''
    Execute the installed console with static data and an audited offline lookup.

    :param installed_cli: The offline noneditable installed console environment.
    :type installed_cli: dict
    :param tmp_path: The isolated temporary data directory.
    :type tmp_path: Path
    :return: The configured fixture value or completed response.
    :rtype: Any
    '''

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / 'config.yml').read_text())
    history = tmp_path / 'history.csv'
    history.write_text((root / 'tests/repos/fixtures/static_history.csv').read_text().replace('AAPL,', 'SPY,'))
    config['services']['price_service'] = {
        'module_path': 'tiferet_stocks.repos.static',
        'class_name': 'StaticPriceRepository',
        'params': {
            'fixture_path': str(root / 'tests/repos/fixtures/static_prices.yml'),
            'history_path': str(history),
        },
    }
    storage = tmp_path / 'watchlists.yml'
    config['services']['watchlist_service']['params']['watchlist_config'] = str(storage)
    for error_id, error in config['errors'].items():
        error['message'][0]['text'] = f"CLI-CONFIGURED-{error_id}: " + error['message'][0]['text']
    config_path = tmp_path / 'selected.yml'
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    seed = {
        'name': 'ETFs',
        'description': 'Acceptance seed',
        'created_at': '2026-11-06T14:00:00-07:00',
        'updated_at': '2026-11-06T14:00:00-07:00',
        'symbol_ids': ['SPY', 'QQQ', 'XLK'],
    }
    storage.write_text('# Preserve bytes on reporting.\n' + yaml.safe_dump({'watchlists': {'etfs': seed}, 'other': {'keep': True}}, sort_keys=False))
    env = {
        **installed_cli['env'],
        'PYTHONPATH': str(root / 'tests/cli_support'),
        'PYTHONDONTWRITEBYTECODE': '1',
        'CLI_TEST_RECORDING': str(root / 'tests/repos/payloads/spy.json'),
    }

    # Only this helper directory is importable from checkout; production is installed.
    def run(*argv):
        '''
        Exercise the configured CLI bootstrap contract.

        :param *argv: The explicit command tokens.
        :type *argv: tuple
        :return: The configured fixture value or completed response.
        :rtype: Any
        '''

        return subprocess.run(
            [str(installed_cli['script']), '--config', str(config_path), *argv],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    return {'run': run, 'storage': storage, 'config': config_path, 'history': history, 'env': env, 'python': installed_cli['python'], 'cwd': tmp_path}

# *** tests

# ** test: all_thirteen_installed_commands
@pytest.mark.parametrize('argv, expected', [
    (['quotes', 'get', 'SPY', 'QQQ'], 'not_found'),
    (['quotes', 'history', 'SPY', '--start', '2026-10-19', '--end', '2026-10-23'], '2026-10-19'),
    (['symbols', 'get', 'SPY'], 'unmapped_exchange'),
    (['symbols', 'resolve', 'SPY', 'MISSING'], 'not_found'),
    (['exchanges', 'list'], 'NYSE_ARCA'),
    (['watchlists', 'list'], 'etfs'),
    (['watchlists', 'get', 'etfs'], 'ETFs'),
    (['watchlists', 'create', 'new', '--name', 'New', '--description', 'Example', '--symbol-ids', 'SPY', 'QQQ'], 'New'),
    (['watchlists', 'update', 'etfs', '--name', 'Renamed'], 'Renamed'),
    (['watchlists', 'delete', 'etfs'], 'etfs'),
    (['watchlists', 'add', 'etfs', 'DIA'], 'DIA'),
    (['watchlists', 'remove', 'etfs', 'SPY'], 'QQQ'),
    (['watchlists', 'move', 'etfs', 'SPY'], 'SPY'),
])
def test_all_thirteen_installed_commands(console, argv, expected):
    '''
    Cross the real console/parser/container/feature/presentation boundary.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :param argv: The public command tokens.
    :type argv: list
    :param expected: The required output fragment.
    :type expected: str
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = console['run'](*argv)
    assert_success(result)
    assert expected in result.stdout

# ** test: quotes_complete_rows
def test_quotes_have_one_row_per_symbol_and_all_failure_fields(console):
    '''
    Report both a successful static quote and a missing quote by id/reason.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = console['run']('quotes', 'get', 'SPY', 'QQQ')
    assert_success(result)
    lines = result.stdout.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith('symbol_id '))
    lines = lines[start:]
    assert len(lines) == 4
    assert lines[0].split()[0] == 'symbol_id'
    assert [line.split()[0] for line in lines[2:]] == ['SPY', 'QQQ']
    assert 'failure_1_reason' in lines[0]
    assert 'not_found' in lines[3]
    assert 'failure_count' in lines[0]
    assert 'warning_count' in lines[0]

# ** test: history_order_and_empty
def test_history_oldest_first_and_empty_trading_range(console):
    '''
    Keep native history rendering while retaining sorted bars and empty success.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = console['run']('quotes', 'history', 'SPY', '--start', '2026-10-19', '--end', '2026-10-23')
    assert_success(result)
    dates = ['2026-10-19', '2026-10-20', '2026-10-21', '2026-10-23']
    positions = [result.stdout.index(date) for date in dates]
    assert positions == sorted(positions)
    result = console['run']('quotes', 'history', 'SPY', '--start', '2026-10-24', '--end', '2026-10-25')
    assert_success(result)
    assert all(not line.strip() or 'Executed Feature - quotes.history' in line for line in result.stdout.splitlines())

# ** test: symbol_reports_preserve_messages
@pytest.mark.parametrize('argv, required', [
    (['symbols', 'get', 'SPY'], ['SPY', 'unmapped_exchange']),
    (['symbols', 'get', 'MISSING'], ['MISSING', 'not_found', 'Recorded symbol missing.']),
    (['symbols', 'resolve', 'SPY', 'MISSING'], ['SPY', 'MISSING', 'unmapped_exchange', 'not_found']),
    (['symbols', 'resolve', 'SPY', '--expected-exchanges', 'SPY=NASDAQ'], ['symbol_mismatch', 'unmapped_exchange', 'expected exchange NASDAQ']),
])
def test_symbol_reports_preserve_messages(console, argv, required):
    '''
    Show all warnings/failures, including exchange checks, not only successes.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :param argv: The public command tokens.
    :type argv: list
    :param required: Every diagnostic fragment that must be retained.
    :type required: list
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = console['run'](*argv)
    assert_success(result)
    for text in required:
        assert text in result.stdout

# ** test: exact_exchanges
def test_exchanges_print_exact_domain_ids(console):
    '''
    Compare the native table's complete data rows with the domain vocabulary.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    result = console['run']('exchanges', 'list')
    assert_success(result)
    lines = result.stdout.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == 'value')
    assert [line.strip() for line in lines[start + 2:]] == list(EXCHANGES)

# ** test: cli_indexes
@pytest.mark.parametrize('operation, flag, symbol', [('add', '--index', 'DIA'), ('move', '--to-index', 'SPY')])
@pytest.mark.parametrize('index', [None, '-1', '0', '99', '-2'])
def test_cli_indexes_and_rejected_write_invariance(console, operation, flag, symbol, index):
    '''
    Exercise omitted/default, append, absolute, past-end and rejected indices.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :param operation: The watchlist operation name.
    :type operation: str
    :param flag: The configured position flag.
    :type flag: str
    :param symbol: The symbol to add or move.
    :type symbol: str
    :param index: The explicit position, or None to exercise its default.
    :type index: str | None
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    before = console['storage'].read_bytes()
    arguments = ['watchlists', operation, 'etfs', symbol]
    if index is not None:
        arguments += [flag, index]
    result = console['run'](*arguments)
    if index == '-2':
        assert_error(result, 'WATCHLIST_INDEX_OUT_OF_RANGE')
        assert console['storage'].read_bytes() == before
    else:
        assert_success(result)
        expected = ['SPY', 'QQQ', 'XLK']
        if operation == 'move':
            expected.remove(symbol)
        expected.insert(0 if index == '0' else len(expected), symbol)
        assert read_ids(console) == expected
        assert yaml.safe_load(console['storage'].read_text())['other'] == {'keep': True}

# ** test: configured_error_parity
@pytest.mark.parametrize('argv, error_id', [
    (['quotes', 'get', 'MISSING'], 'QUOTES_UNAVAILABLE'),
    (['quotes', 'history', 'MISSING', '--start', '2026-10-19', '--end', '2026-10-23'], 'HISTORY_UNAVAILABLE'),
    (['quotes', 'history', 'SPY', '--start', 'bad', '--end', '2026-10-23'], 'INVALID_HISTORY_RANGE'),
    (['watchlists', 'get', 'absent'], 'WATCHLIST_NOT_FOUND'),
    (['watchlists', 'create', 'etfs', '--name', 'Duplicate'], 'WATCHLIST_EXISTS'),
    (['watchlists', 'create', 'new', '--name', 'New', '--symbol-ids', 'SPY', 'SPY'], 'WATCHLIST_SYMBOL_EXISTS'),
    (['watchlists', 'add', 'etfs', 'SPY'], 'WATCHLIST_SYMBOL_EXISTS'),
    (['watchlists', 'remove', 'etfs', 'MISSING'], 'WATCHLIST_SYMBOL_NOT_FOUND'),
    (['watchlists', 'move', 'etfs', 'MISSING'], 'WATCHLIST_SYMBOL_NOT_FOUND'),
])
def test_configured_errors_exit_one_and_never_write(console, argv, error_id):
    '''
    Prove selected catalog messages and no writes on rejected domain requests.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :param argv: The public command tokens.
    :type argv: list
    :param error_id: The expected configured domain error id.
    :type error_id: str
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    before = console['storage'].read_bytes()
    result = console['run'](*argv)
    assert_error(result, error_id)
    assert console['storage'].read_bytes() == before

# ** test: parser_error_exit_two
@pytest.mark.parametrize('argv', [[], ['unknown'], ['quotes', 'history', 'SPY'], ['watchlists', 'add', 'etfs', 'DIA', '--index', 'bad']])
def test_parser_errors_exit_two_and_never_write(console, argv):
    '''
    Retain core argparse syntax handling separately from domain error handling.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :param argv: The public command tokens.
    :type argv: list
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    before = console['storage'].read_bytes()
    result = console['run'](*argv)
    assert result.returncode == 2, result.stdout + result.stderr
    assert 'Traceback' not in result.stdout + result.stderr
    assert console['storage'].read_bytes() == before

# ** test: reporting_is_read_only
def test_all_reporting_commands_leave_files_byte_identical(console):
    '''
    Snapshot mutable storage, configuration and fixtures across all reports.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    paths = [console['storage'], console['config'], console['history']]
    before = {path: path.read_bytes() for path in paths}
    before_tree = {path.relative_to(console['cwd']): path.read_bytes() for path in console['cwd'].rglob('*') if path.is_file()}
    commands = [
        ['quotes', 'get', 'SPY', 'QQQ'],
        ['quotes', 'history', 'SPY', '--start', '2026-10-19', '--end', '2026-10-23'],
        ['symbols', 'get', 'SPY'],
        ['symbols', 'resolve', 'SPY', 'MISSING'],
        ['exchanges', 'list'],
        ['watchlists', 'list'],
        ['watchlists', 'get', 'etfs'],
    ]
    for argv in commands:
        assert_success(console['run'](*argv))
        assert {path: path.read_bytes() for path in paths} == before
        assert {path.relative_to(console['cwd']): path.read_bytes() for path in console['cwd'].rglob('*') if path.is_file()} == before_tree

# ** test: first_save_missing_file
def test_cli_missing_file_reads_then_first_save(console):
    '''
    Preserve the Chief's first-run rule through installed feature dispatch.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    console['storage'].unlink()
    assert_success(console['run']('watchlists', 'list'))
    assert not console['storage'].exists()
    assert_error(console['run']('watchlists', 'get', 'absent'), 'WATCHLIST_NOT_FOUND')
    assert not console['storage'].exists()
    assert_success(console['run']('watchlists', 'create', 'first', '--name', 'First'))
    assert yaml.safe_load(console['storage'].read_text())['watchlists']['first']['symbol_ids'] == []

# ** test: offline_guard_is_live
def test_subprocess_network_guard_blocks_before_dns(console):
    '''
    Positively verify the guard used by every installed acceptance command.

    :param console: The isolated installed command runner and storage paths.
    :type console: dict
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    probe = subprocess.run(
        [str(console['python']), '-c', 'import socket; socket.create_connection(("example.invalid", 80))'],
        cwd=console['cwd'],
        env=console['env'],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert probe.returncode != 0
    assert 'CLI_NETWORK_BLOCKED' in probe.stderr
