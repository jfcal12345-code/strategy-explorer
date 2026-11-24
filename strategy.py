"""
strategy.py - all the calculations of the app live here.

IMPORTANT FOR THE GROUP
-----------------------
The app (app.py) only DISPLAYS results. Every number comes from the three
functions in this file:

    load_prices(...)          -> owner: Matilde (data)
    backtest(...)             -> owner: Joana   (portfolio returns)
    performance_metrics(...)  -> owner: Maria   (performance table)

Right now this file is a PLACEHOLDER so the app can be built and deployed
before the real work is finished:

  * load_prices() invents random prices instead of calling an API.
  * TICKERS, WEIGHTS, BENCHMARK, dates and the risk-free rate are examples.

When the notebook is ready, paste the notebook's versions of these functions
here WITHOUT changing them, so the app and the notebook always give the same
numbers. Keep the function names and inputs the same and app.py needs no edits.
"""

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 1. Strategy settings (PLACEHOLDERS - replace with the group's decisions)
# ---------------------------------------------------------------------------
START_DATE = "2015-01-01"      # sample start, set explicitly as the brief asks
END_DATE = "2025-12-31"        # sample end
TICKERS = ["Asset A", "Asset B", "Asset C"]                    # P3 decides
WEIGHTS = {"Asset A": 0.50, "Asset B": 0.30, "Asset C": 0.20}  # P4 decides
BENCHMARK = "Benchmark"                                         # P4 decides
RISK_FREE_RATE = 0.02          # annual risk-free rate, P4 decides the source
DEFAULT_REBALANCE = "Quarterly"  # P4 decides
DEFAULT_COST_BPS = 10          # transaction cost in basis points, P6 decides
PERIODS_PER_YEAR = 252         # trading days per year (daily data)

# Set this to False once load_prices() downloads real data. While it is True
# the app shows a warning that the numbers are invented.
USING_PLACEHOLDER_DATA = True

# Options offered in the app -> pandas period code used to detect a new period
REBALANCE_OPTIONS = {"Monthly": "M", "Quarterly": "Q", "Yearly": "Y", "Never": None}


# ---------------------------------------------------------------------------
# 2. Data  (PLACEHOLDER: random prices. Matilde's API download replaces this)
# ---------------------------------------------------------------------------
def load_prices(tickers, start, end):
    """Return a table of daily prices: one row per day, one column per asset.

    The real version downloads adjusted prices from an API. This placeholder
    simulates prices with a fixed random seed, so the result is the same on
    every run.
    """
    dates = pd.bdate_range(start, end)          # business days only
    rng = np.random.default_rng(42)             # fixed seed = reproducible
    n = len(dates)

    # One common "market" movement plus an individual movement per asset.
    market = rng.normal(0.00030, 0.0095, n)
    settings = {  # name: (sensitivity to the market, own drift, own noise)
        "Asset A": (1.10, 0.00012, 0.0070),
        "Asset B": (0.80, 0.00008, 0.0050),
        "Asset C": (0.20, 0.00010, 0.0040),
        "Benchmark": (1.00, 0.00000, 0.0015),
    }
    prices = {}
    for name in tickers:
        beta, drift, noise = settings.get(name, (1.0, 0.0, 0.006))
        daily_returns = beta * market + drift + rng.normal(0, noise, n)
        prices[name] = 100 * np.cumprod(1 + daily_returns)
    return pd.DataFrame(prices, index=dates)


# ---------------------------------------------------------------------------
# 3. Backtest
# ---------------------------------------------------------------------------
def backtest(prices, weights, rebalance="Quarterly", tc_bps=0.0):
    """Daily portfolio returns for a fixed-weight strategy, after trading costs.

    prices    : table of prices (from load_prices), one column per asset
    weights   : dict of target weights, e.g. {"Asset A": 0.5, ...}, summing to 1
    rebalance : "Monthly", "Quarterly", "Yearly" or "Never"
    tc_bps    : cost per trade in basis points (10 bps = 0.10% of amount traded)

    Returns a table with two columns:
        "return"   - the portfolio's net return each day
        "turnover" - share of the portfolio traded that day (0 on most days)

    No look-ahead: the weights held during a day were fixed BEFORE that day's
    returns were known. Rebalancing happens at the close of the first trading
    day of each new period, using only prices known at that moment.
    """
    assets = list(weights.keys())
    target = np.array([weights[a] for a in assets], dtype=float)
    asset_returns = prices[assets].pct_change().dropna()
    cost_rate = tc_bps / 10_000

    # Mark the first trading day of each new month / quarter / year.
    code = REBALANCE_OPTIONS[rebalance]
    if code is None:
        is_rebalance_day = np.zeros(len(asset_returns), dtype=bool)
    else:
        period = asset_returns.index.to_period(code)
        is_rebalance_day = np.r_[False, period[1:] != period[:-1]]

    current = target.copy()   # weights held at the start of the day
    net_returns, turnovers = [], []

    for day_returns, rebalance_today in zip(asset_returns.to_numpy(), is_rebalance_day):
        # (a) Earn today's return with the weights chosen earlier.
        gross = float(current @ day_returns)
        # (b) Prices moved, so the weights drift away from the target.
        current = current * (1 + day_returns) / (1 + gross)
        # (c) At the close of a rebalancing day, trade back to the target.
        turnover = 0.0
        if rebalance_today:
            turnover = float(np.abs(target - current).sum())
            current = target.copy()
        # (d) Trading costs reduce today's return.
        net_returns.append((1 + gross) * (1 - turnover * cost_rate) - 1)
        turnovers.append(turnover)

    return pd.DataFrame(
        {"return": net_returns, "turnover": turnovers}, index=asset_returns.index
    )


# ---------------------------------------------------------------------------
# 4. Performance measures
# ---------------------------------------------------------------------------
def performance_metrics(port_ret, bench_ret, rf_annual=RISK_FREE_RATE,
                        periods=PERIODS_PER_YEAR):
    """The six measures the assignment asks for, as a dictionary.

    Conventions (state these in the prospectus):
      * average return : mean daily return x 252
      * volatility     : standard deviation of daily returns x sqrt(252)
      * Sharpe ratio   : annualized average excess return / annualized volatility
      * beta, alpha    : regression of portfolio excess returns on benchmark
                         excess returns; alpha is annualized (x 252), beta is not
      * information ratio : annualized average active return / tracking error
    """
    rf_daily = rf_annual / periods
    port_excess = port_ret - rf_daily
    bench_excess = bench_ret - rf_daily
    active = port_ret - bench_ret           # return above the benchmark

    ann_return = port_ret.mean() * periods
    ann_vol = port_ret.std() * np.sqrt(periods)
    sharpe = port_excess.mean() * periods / ann_vol
    beta = port_excess.cov(bench_excess) / bench_excess.var()
    alpha = (port_excess.mean() - beta * bench_excess.mean()) * periods
    tracking_error = active.std() * np.sqrt(periods)
    info_ratio = active.mean() * periods / tracking_error if tracking_error > 0 else np.nan

    return {
        "Annualized return": ann_return,
        "Annualized volatility": ann_vol,
        "Sharpe ratio": sharpe,
        "Alpha (annualized)": alpha,
        "Beta": beta,
        "Information ratio": info_ratio,
    }
