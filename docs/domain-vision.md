# Domain Vision Statement - Tiferet Stocks

**Status:** Draft (pre-implementation) - **Domain:** `tiferet-stocks` - **Code:** none yet

> Pre-implementation note: the tiferet-stocks repository currently holds only a README, a license and a .gitignore. This statement describes the intended domain and its value, not existing code.

## The bet: one honest answer about a symbol, from a source you can swap

Most small investing tools get market data the quick way: a script calls one provider directly and passes its codes and gaps straight into the rest of the program. That works until the provider changes its format, a symbol quietly goes missing from the results, or someone wants to try a different source and finds the provider's habits spread through every file that touches a price.

Tiferet Stocks takes the opposite bet. What a symbol is, what it is worth right now, and which symbols a person follows are described once, in the library's own plain terms. The market data provider is a replaceable supplier behind that description, chosen in a settings file. Its codes are translated at the door, and anything it fails to deliver is reported by name rather than dropped.

## What this domain makes real

Tiferet Stocks is a small library, built on the Tiferet framework, that answers "what is this symbol and what is it worth?" for any program that asks. It looks up what a symbol is (its ticker, its exchange, its name, what kind of asset it is, such as a stock or an ETF, and its currency), fetches current quotes and daily price history from a provider chosen in settings, and keeps named, ordered watchlists of the symbols a user follows. A small command line covers reporting and watchlist edits. Everything except watchlists is read-only: it asks, answers and keeps nothing.

## What we get for it

**No silent gaps.** When a quote cannot be fetched, the symbol is listed as a failure with its reason, such as not found or timed out, instead of disappearing from the results. A report built on these quotes can say exactly what it is missing.

**Freedom to change data providers.** Yahoo's chart service is the default source, but it is one entry in the settings file. A different or paid provider can be added later as a new supplier, and the programs that ask for quotes do not change.

**One meaning for "exchange".** A symbol's exchange is one value from a short fixed list: NYSE, NASDAQ, NYSE Arca, Cboe BZX or NYSE American in the first release. Provider codes, such as Yahoo's NYQ, NMS, PCX, BTS and ASE, are translated where the data arrives and never reach the rest of the system. Exchange-traded funds are ordinary symbols marked as ETFs, so their quotes work like any stock's. Money market and mutual funds have no exchange. An unrecognized code leaves the exchange empty with a warning, so one odd listing never fails a batch. Adding an exchange later is a small, local change.

**Watchlists that keep their order and stay readable.** A watchlist has a name, an optional description, when it was created and last changed, and its symbols in the order the user chose, each at most once. A user can keep several, in one plain YAML or JSON file that a person can read, with no database.

**Predictable editing rules.** Positions in a watchlist are counted from 0. Leaving out a position, or giving -1, means "at the end", and a position past the end also lands last. Anything below -1 is refused with a named error, so a mistaken count from the end never puts a symbol somewhere surprising.

**Nothing stored by accident.** Quotes and lookups are never saved, so there is no stale copy of market data to expire, reconcile or protect. The watchlists file is the only thing this library writes.

## The core of the work

The domain follows two short paths:

> **Ask** about symbols, quotes or history -> **fetch** from the configured provider -> **translate** the provider's codes into the library's own terms -> **answer** with results and named failures.

> **Change** a watchlist (create, rename, delete, add, remove or move a symbol) -> **check** the change against the ordering rules -> **save** the watchlists file with an updated change time.

The central design commitment is **read-only by default, with watchlists as the single exception.** Every question about symbols and prices leaves no trace behind. A watchlist holds tickers only; what a symbol is always comes from a fresh lookup, never from a copy kept in the watchlist. That keeps the stored data small and gives each fact exactly one source.

The ticker is a symbol's identity. A key that also names the exchange could come in a later release.

## What it deliberately does not do

It does not track money. Accounts, holdings, tax lots, cash, investment policy rules and decision records belong to tiferet-ledger, which builds on this library and refers to symbols only by ticker.

It does not own market data. Prices and symbol details come from the quote provider, which owns their accuracy and availability. Tiferet Stocks reports what the provider said and what it could not get; it does not correct or fill in the numbers.

It does not provide its own framework. Request handling, error messages, settings files and the wiring that lets a provider be swapped come from Tiferet core. This library supplies only the stock-specific terms, rules and suppliers on top.

It does not trade, store prices, keep results between calls, or cover company fundamentals or news in the first release.

---

*Companion document:* `docs/core-domain-distillation.md` - the detailed walkthrough of the domain's vocabulary, behaviors, and the relationships between its parts (drafted after this statement).
