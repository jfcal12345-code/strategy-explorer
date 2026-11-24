"""
app.py - the Streamlit app (what the user sees).

This file contains NO financial calculations of its own. It reads the user's
choices, calls the functions in strategy.py, and shows the results.

Run on your own computer with:   streamlit run app.py
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import strategy as s

# Chart colours (kept the same everywhere so each line is easy to recognise)
COLOR_STRATEGY = "#2a78d6"   # blue   - strategy after costs
COLOR_BENCHMARK = "#eb6834"  # orange - benchmark
COLOR_GROSS = "#8a8a86"      # grey   - strategy before costs

st.set_page_config(page_title="Strategy explorer", page_icon="📈", layout="wide")


# ---------------------------------------------------------------------------
# Data: downloaded once and remembered for a day, so moving a slider does not
# call the data API again.
# ---------------------------------------------------------------------------
@st.cache_data(ttl=86_400)
def get_prices():
    return s.load_prices(s.TICKERS + [s.BENCHMARK], s.START_DATE, s.END_DATE)


@st.cache_data
def run_backtest(rebalance, tc_bps):
    return s.backtest(get_prices(), s.WEIGHTS, rebalance, tc_bps)


def euro(x):
    return f"€{x:,.0f}"


# ---------------------------------------------------------------------------
# Sidebar: what the user can change
# ---------------------------------------------------------------------------
st.sidebar.header("Your assumptions")

tc_bps = st.sidebar.slider(
    "Transaction cost (basis points per trade)",
    min_value=0, max_value=100, value=s.DEFAULT_COST_BPS, step=5,
    help="10 basis points = 0.10% of the amount bought or sold.",
)
rebalance = st.sidebar.selectbox(
    "Rebalancing frequency",
    list(s.REBALANCE_OPTIONS),
    index=list(s.REBALANCE_OPTIONS).index(s.DEFAULT_REBALANCE),
    help="How often the portfolio is traded back to its target weights.",
)
investment = st.sidebar.number_input(
    "Amount invested at the start (€)",
    min_value=1_000, max_value=10_000_000, value=10_000, step=1_000,
)
st.sidebar.caption(
    "The prospectus uses "
    f"{s.DEFAULT_COST_BPS} bps and {s.DEFAULT_REBALANCE.lower()} rebalancing."
)

# ---------------------------------------------------------------------------
# Calculations (all done by strategy.py)
# ---------------------------------------------------------------------------
prices = get_prices()
net = run_backtest(rebalance, tc_bps)          # with the user's cost
gross = run_backtest(rebalance, 0)             # same strategy, zero cost
bench_ret = prices[s.BENCHMARK].pct_change().dropna()

port_ret = net["return"]
m_port = s.performance_metrics(port_ret, bench_ret)
m_gross = s.performance_metrics(gross["return"], bench_ret)
m_bench = s.performance_metrics(bench_ret, bench_ret)

# Growth of 1 unit invested; all series start at exactly 1.
def growth(returns):
    g = (1 + returns).cumprod()
    start = pd.Series([1.0], index=[prices.index[0]])
    return pd.concat([start, g])

g_net, g_gross, g_bench = growth(port_ret), growth(gross["return"]), growth(bench_ret)

years = len(port_ret) / s.PERIODS_PER_YEAR
turnover_per_year = net["turnover"].sum() / years
trades_per_year = (net["turnover"] > 0).sum() / years
cost_drag = m_gross["Annualized return"] - m_port["Annualized return"]
cost_in_euro = (g_gross.iloc[-1] - g_net.iloc[-1]) * investment

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("Strategy explorer")
st.write(
    "See how the portfolio from our prospectus would have performed, and how "
    "much of the result survives once trading costs are taken into account. "
    "Change the assumptions in the sidebar."
)
if s.USING_PLACEHOLDER_DATA:
    st.warning(
        "Test version: the prices are randomly generated placeholders, not "
        "real market data. The numbers below mean nothing yet."
    )
st.caption(
    f"Backtest from {prices.index[0]:%d %b %Y} to {prices.index[-1]:%d %b %Y}, "
    "daily data. Past performance does not predict future returns."
)

# --- Headline numbers ------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric(
    f"{euro(investment)} became",
    euro(g_net.iloc[-1] * investment),
    f"{euro((g_net.iloc[-1] - g_bench.iloc[-1]) * investment)} vs benchmark",
)
c2.metric(
    "Annualized return",
    f"{m_port['Annualized return']:.1%}",
    f"{(m_port['Annualized return'] - m_bench['Annualized return']) * 100:+.1f} pts vs benchmark",
)
c3.metric(
    "Sharpe ratio",
    f"{m_port['Sharpe ratio']:.2f}",
    f"{m_port['Sharpe ratio'] - m_bench['Sharpe ratio']:+.2f} vs benchmark",
)
c4.metric(
    "Lost to trading costs",
    euro(cost_in_euro),
    f"-{cost_drag * 100:.2f} pts of return per year",
    delta_color="off",
)

# --- Cumulative performance ------------------------------------------------
st.subheader("Cumulative performance")
fig = go.Figure()
fig.add_scatter(x=g_bench.index, y=g_bench, name="Benchmark",
                line=dict(color=COLOR_BENCHMARK, width=2))
fig.add_scatter(x=g_gross.index, y=g_gross, name="Strategy before costs",
                line=dict(color=COLOR_GROSS, width=1.5, dash="dot"))
fig.add_scatter(x=g_net.index, y=g_net, name="Strategy after costs",
                line=dict(color=COLOR_STRATEGY, width=2))
fig.update_traces(hovertemplate="%{y:.2f}")
fig.update_layout(
    hovermode="x unified", height=420, margin=dict(l=0, r=0, t=10, b=0),
    yaxis_title="Value of 1 invested at the start",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)
st.plotly_chart(fig, width="stretch")

# --- Performance table -----------------------------------------------------
st.subheader("Performance measures")
percent_rows = {"Annualized return", "Annualized volatility", "Alpha (annualized)"}


def show(name, value, is_benchmark=False):
    # Alpha, beta and information ratio compare a portfolio WITH the
    # benchmark, so they have no meaning for the benchmark itself.
    if is_benchmark and name in {"Alpha (annualized)", "Beta", "Information ratio"}:
        return "–"
    return f"{value:.2%}" if name in percent_rows else f"{value:.2f}"


table = pd.DataFrame(
    {
        "Strategy (after costs)": [show(k, v) for k, v in m_port.items()],
        "Benchmark": [show(k, v, True) for k, v in m_bench.items()],
    },
    index=list(m_port.keys()),
)
left, right = st.columns([3, 2])
left.table(table)
right.markdown(
    f"""
**Reading the table**

- **Return and volatility**: what the investor earned per year on average, and
  how bumpy the ride was.
- **Sharpe ratio**: return above the risk-free rate per unit of risk taken.
- **Beta** of {m_port['Beta']:.2f}: for a 1% move in the benchmark, the
  portfolio moved about {m_port['Beta']:.2f}% on average.
- **Alpha**: the yearly return not explained by simply holding the benchmark.
- **Information ratio**: how consistently the portfolio beat the benchmark.
"""
)

# --- What makes this app different: how much cost can the strategy absorb? --
st.subheader("How much trading cost can the strategy absorb?")

cost_grid = np.arange(0, 101, 10)
ret_grid = [
    s.performance_metrics(run_backtest(rebalance, int(c))["return"], bench_ret)[
        "Annualized return"
    ]
    for c in cost_grid
]
bench_level = m_bench["Annualized return"]

# Break-even cost: the cost per trade at which the strategy's return falls to
# the benchmark's. The return falls in a straight line as costs rise, so we
# extend the line through the 0 bps and 100 bps points.
loss_per_bp = (ret_grid[0] - ret_grid[-1]) / 100
edge_before_costs = ret_grid[0] - bench_level
if edge_before_costs <= 0:
    breakeven_text = (
        "The strategy earned less than the benchmark even before costs, so "
        "there is no break-even cost."
    )
elif loss_per_bp <= 0:
    breakeven_text = (
        "With no rebalancing there is no trading, so costs do not reduce the return."
    )
else:
    breakeven = edge_before_costs / loss_per_bp
    breakeven_text = (
        f"The strategy keeps beating the benchmark until costs reach about "
        f"**{breakeven:,.0f} basis points per trade**. You have set {tc_bps} bps."
    )

left, right = st.columns([3, 2])
fig2 = go.Figure()
fig2.add_scatter(x=cost_grid, y=ret_grid, name="Strategy after costs",
                 mode="lines", line=dict(color=COLOR_STRATEGY, width=2),
                 hovertemplate="%{x} bps: %{y:.2%}<extra>Strategy</extra>")
fig2.add_scatter(x=cost_grid, y=[bench_level] * len(cost_grid), name="Benchmark",
                 mode="lines", line=dict(color=COLOR_BENCHMARK, width=2),
                 hovertemplate="%{y:.2%}<extra>Benchmark</extra>")
fig2.add_scatter(x=[tc_bps], y=[m_port["Annualized return"]], name="Your setting",
                 mode="markers",
                 marker=dict(color=COLOR_STRATEGY, size=12,
                             line=dict(color="white", width=2)),
                 hovertemplate="Your setting: %{y:.2%}<extra></extra>")
fig2.update_layout(
    height=340, margin=dict(l=0, r=0, t=10, b=0),
    xaxis_title="Transaction cost (basis points per trade)",
    yaxis_title="Annualized return", yaxis_tickformat=".1%",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)
left.plotly_chart(fig2, width="stretch")
right.markdown(breakeven_text)
right.markdown(
    f"""
With **{rebalance.lower()}** rebalancing the portfolio trades about
**{trades_per_year:.0f} times a year** and replaces
**{turnover_per_year:.0%}** of its value per year. Rebalancing more often keeps
the portfolio closer to its target weights but costs more.
"""
)

# --- Assumptions -----------------------------------------------------------
with st.expander("Assumptions and method"):
    weights_text = ", ".join(f"{a} {w:.0%}" for a, w in s.WEIGHTS.items())
    st.markdown(
        f"""
- **Holdings and target weights:** {weights_text}
- **Benchmark:** {s.BENCHMARK}
- **Sample:** {s.START_DATE} to {s.END_DATE}, daily data
- **Risk-free rate:** {s.RISK_FREE_RATE:.1%} per year
- **Annualization:** {s.PERIODS_PER_YEAR} trading days per year; beta is not annualized
- **Rebalancing:** at the close of the first trading day of each period, using
  only prices known at that time
- **Transaction costs:** charged on the value traded at each rebalancing
- The calculations are the same functions used in the group's notebook.
"""
    )
