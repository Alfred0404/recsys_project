"""Daily returns, expected returns (mu), covariance (Sigma) and asset risk classes.

Every function that computes from the data takes a `before` date and only uses prices
strictly before it (no leakage). mu and Sigma are annualised.
"""
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from src.data.holdings import latest_before

TRADING_DAYS = 252
MIN_HISTORY = 60  # fewer daily returns than this: volatility is not reliable
# Upper bounds of annualised volatility for SRRI classes 1 to 6 (class 7 above), ESMA CESR/10-673.
SRRI_BANDS = [0.005, 0.02, 0.05, 0.10, 0.15, 0.25]


def drop_price_glitches(wide: pd.DataFrame, jump=0.5, back=0.2, within=5) -> pd.DataFrame:
    """Erase price errors: a jump above `jump` that comes back within `back` of the previous
    price in at most `within` quotes (e.g. 1.8 -> 0.6 -> 1.8). Real moves that stay are kept.

    shortcut: looks up to `within` quotes ahead, so on a matrix built from all dates an erroneous
    price just before `before` can be erased using later prices; cut the prices first if that matters.
    """
    wide = wide.copy()
    for isin in wide.columns:
        col = wide[isin].dropna()
        r = col.pct_change().to_numpy()
        for i in np.flatnonzero(np.abs(r) > jump):
            after = col.iloc[i + 1:i + 1 + within].to_numpy()
            returned = np.flatnonzero(np.abs(after / col.iloc[i - 1] - 1) < back)
            if len(returned):
                wide.loc[col.index[i:i + 1 + returned[0]], isin] = np.nan
    return wide


def price_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Dates x ISIN close prices, glitches removed, gaps of up to 5 days filled with the last price."""
    wide = prices.pivot(index="timestamp", columns="ISIN", values="closePrice").sort_index()
    return drop_price_glitches(wide).ffill(limit=5)


def returns_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    return price_matrix(prices).pct_change(fill_method=None)


def expected_returns(returns: pd.DataFrame, before, span=60) -> pd.Series:
    """mu: exponentially weighted mean of daily returns, annualised. Assets with too short a history are dropped."""
    r = returns[returns.index < pd.Timestamp(before)]
    mu = r.ewm(span=span).mean().iloc[-1] * TRADING_DAYS
    return mu[r.count() >= MIN_HISTORY].dropna()


def covariance(returns: pd.DataFrame, before, window=TRADING_DAYS) -> pd.DataFrame:
    """Sigma over the last `window` days, Ledoit-Wolf shrinkage so it stays usable by the MPT score.

    Only assets with at least MIN_HISTORY returns in the window are kept; missing returns count as 0.
    """
    r = returns[returns.index < pd.Timestamp(before)].tail(window)
    r = r.loc[:, r.count() >= MIN_HISTORY]
    sigma = LedoitWolf().fit(r.fillna(0).to_numpy()).covariance_ * TRADING_DAYS
    return pd.DataFrame(sigma, index=r.columns, columns=r.columns)


def asset_risk(prices: pd.DataFrame, assets: pd.DataFrame, before) -> pd.DataFrame:
    """Per asset: n_returns, volatility, max_drawdown, risk_class (1-7), risk_class_imputed.

    Assets with too short a history get the median class of their subcategory (else of all assets).
    """
    wide = price_matrix(prices[prices["timestamp"] < pd.Timestamp(before)])
    r = wide.pct_change(fill_method=None)
    out = pd.DataFrame({
        "n_returns": r.count(),
        "volatility": r.std() * np.sqrt(TRADING_DAYS),
        "max_drawdown": (wide / wide.cummax() - 1).min(),
    }).rename_axis("ISIN").reset_index()
    out["risk_class"] = np.searchsorted(SRRI_BANDS, out["volatility"].fillna(0), side="right") + 1
    out["risk_class_imputed"] = out["n_returns"] < MIN_HISTORY

    sub = latest_before(assets, "ISIN", before).set_index("ISIN")["assetSubCategory"]
    out["sub"] = out["ISIN"].map(sub)
    reliable = out[~out["risk_class_imputed"]]
    by_sub = reliable.groupby("sub")["risk_class"].median()
    fallback = out.loc[out["risk_class_imputed"], "sub"].map(by_sub).fillna(reliable["risk_class"].median())
    out.loc[out["risk_class_imputed"], "risk_class"] = fallback.round().astype(int)
    return out.drop(columns="sub")
