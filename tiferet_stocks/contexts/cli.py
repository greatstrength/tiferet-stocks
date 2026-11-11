"""Tiferet Stocks CLI Presentation Contexts"""

# *** imports

# ** core
from typing import Any, Dict, List

# ** infra
from tiferet.contexts.cli import CliRequestContext, build_cli_record
from tiferet.domain.cli import CliRecordList

# ** app
from tiferet_stocks.domain import Quotations, SymbolLookup

# *** functions

# ** function: build_symbol_rows
def build_symbol_rows(result: Quotations | SymbolLookup) -> List[Dict[str, Any]]:
    '''
    Make one flat row per symbol while retaining every warning and failure.

    :param result: The unchanged library answer.
    :type result: Quotations | SymbolLookup
    :return: Flat rows suitable for core's native table formatter.
    :rtype: List[Dict[str, Any]]
    '''

    # Preserve encounter order across all answer components, including failure-only ids.
    quotes = result.quotes if isinstance(result, Quotations) else {}
    ids = list(dict.fromkeys([
        *quotes,
        *result.symbols,
        *(failure.symbol_id for failure in result.failures),
        *(warning.symbol_id for warning in result.warnings),
    ]))
    rows = []

    # Scalar, prefixed columns retain complete records without nested repr cells.
    for symbol_id in ids:
        quote = quotes.get(symbol_id)
        symbol = result.symbols.get(symbol_id)
        failures = [failure for failure in result.failures if failure.symbol_id == symbol_id]
        warnings = [warning for warning in result.warnings if warning.symbol_id == symbol_id]
        succeeded = quote is not None or symbol is not None
        status = 'partial' if succeeded and failures else 'ok' if succeeded else 'failed' if failures else 'warning'
        row = {'symbol_id': symbol_id, 'status': status}

        # Prefix the quote's identity so a mismatched provider id cannot overwrite the request id.
        if quote is not None:
            for key, value in quote.model_dump(exclude_none=True).items():
                row['quote_symbol_id' if key == 'symbol_id' else key] = value
        if symbol is not None:
            row.update({'resolved_symbol_id' if key == 'id' else f'symbol_{key}': value for key, value in symbol.model_dump(exclude_none=True).items()})
        if isinstance(result, Quotations) and result.fetched_at is not None:
            row['fetched_at'] = result.fetched_at

        # Number repeated records rather than silently keeping only the first message.
        row['failure_count'] = len(failures)
        row['warning_count'] = len(warnings)
        for label, records in [('failure', failures), ('warning', warnings)]:
            for number, record in enumerate(records, start=1):
                row.update({f'{label}_{number}_{key}': value for key, value in record.model_dump(exclude_none=True).items()})
        rows.append(row)

    # Do not change, cache or replace the caller's domain result.
    return rows

# *** contexts

# ** context: stocks_cli_request_context
class StocksCliRequestContext(CliRequestContext):
    '''
    Presents complete symbol answers as readable per-symbol rows.
    Other results keep core's native CLI rendering and the library stays unchanged.
    '''

    # * method: handle_response
    def handle_response(self) -> Any:
        '''
        Adapt only quote/lookup answers without replacing the stored result.

        :return: A native CLI output model, or the unchanged primitive response.
        :rtype: Any
        '''

        # Use the existing record/table models for stock-specific flat rows.
        if isinstance(self.result, (Quotations, SymbolLookup)):
            return CliRecordList(records=[build_cli_record(row) for row in build_symbol_rows(self.result)])

        # History, exchanges and watchlists retain the framework's native behavior.
        return super().handle_response()
