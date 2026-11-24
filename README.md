# Strategy explorer

Interactive companion app to our 2270 Financial Modeling group prospectus.
It backtests the portfolio described in the prospectus and lets the user change
the **transaction cost** and the **rebalancing frequency** to see how
performance and the comparison with the benchmark change.

- **Live app:** ADD-STREAMLIT-URL-HERE
- **Source code:** ADD-GITHUB-URL-HERE
- **Group:** ADD-MOODLE-GROUP-NAME-AND-MEMBERS-HERE

> Status: test version. `strategy.py` currently generates placeholder prices.
> It will be replaced by the functions from the group notebook.

## What the app shows

- Cumulative performance of the strategy against the benchmark, both starting at 1
- Annualized return, volatility, Sharpe ratio, alpha, beta and information ratio
- The value today of an amount invested at the start
- How much return is lost to trading costs, and the break-even cost at which
  the strategy stops beating the benchmark

## Files

| File | Purpose |
| --- | --- |
| `app.py` | The Streamlit page: inputs, charts and tables. No calculations. |
| `strategy.py` | Data loading, backtest and performance measures. Same functions as the notebook. |
| `requirements.txt` | Python packages the app needs. |

## Run it on your own computer

1. Install Python 3.10 or newer.
2. Download this repository and open a terminal in its folder.
3. Install the packages: `pip install -r requirements.txt`
4. Start the app: `streamlit run app.py`

The app opens in your browser at http://localhost:8501.

## Use of AI

The app was built with AI coding assistance (Claude). The group checked the
outputs by comparing the app's numbers at the default settings with the
notebook. See the AI-use log in the prospectus.
