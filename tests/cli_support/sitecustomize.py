"""Process-local offline fixtures; never shipped in the stocks wheel."""

# *** imports

# ** core
import io
import json
import os
from pathlib import Path
import sys
from urllib import parse, request

# *** functions

# ** function: deny_network
def deny_network(event, args):
    '''
    Fail before DNS/socket I/O if a subprocess attempts real network access.

    :param event: The Python audit event name.
    :type event: str
    :param args: The audit event arguments.
    :type args: tuple
    :return: None; assertions enforce the contract.
    :rtype: None
    '''

    if event in ('socket.connect', 'socket.getaddrinfo'):
        raise AssertionError('CLI_NETWORK_BLOCKED')

# ** function: recorded_urlopen
def recorded_urlopen(req, timeout=None):
    '''
    Serve a recorded chart with an unmapped exchange, or an explicit failure.

    :param req: The Yahoo chart request to serve from a local recording.
    :type req: urllib.request.Request
    :param timeout: The provider timeout, unused for local recordings.
    :type timeout: float | None
    :return: The configured fixture value or completed response.
    :rtype: Any
    '''

    url = parse.urlsplit(req.full_url)
    assert url.netloc == 'query1.finance.yahoo.com', 'Unexpected endpoint'
    symbol = parse.unquote(url.path.rsplit('/', 1)[-1])
    if symbol == 'SPY':
        payload = json.loads(Path(os.environ['CLI_TEST_RECORDING']).read_text())
        payload['chart']['result'][0]['meta']['exchangeName'] = 'UNMAPPED_TEST'
    else:
        payload = {'chart': {'result': None, 'error': {'code': 'Not Found', 'description': 'Recorded symbol missing.'}}}
    return io.BytesIO(json.dumps(payload).encode())

# *** setup

sys.addaudithook(deny_network)
request.urlopen = recorded_urlopen
