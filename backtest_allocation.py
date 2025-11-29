"""
Asset allocation backtest using yfinance data.

Usage:
    python backtest_allocation.py --strategy 공격형

Strategies:
- 공격형: BTC 40%, ETH 30%, GLD 15%, TLT 15%
- 중립형: BTC 25%, ETH 25%, GLD 25%, TLT 25%
- 안정형: BTC 10%, ETH 10%, GLD 40%, TLT 40%
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

START_DATE = "2018-01-01"
INITIAL_CAPITAL = 10_000.0
TRANSACTION_COST = 0.001  # 0.1%
ASSETS = ["BTC-USD", "ETH-USD", "GLD", "TLT"]
BENCHMARK = "SPY"


@dataclass(frozen=True)
class Strategy:
    name: str
    weights: Dict[str, float]


STRATEGIES: Dict[str, Strategy] = {
    "공격형": Strategy("공격형", {"BTC-USD": 0.40, "ETH-USD": 0.30, "GLD": 0.15, "TLT": 0.15}),
    "중립형": Strategy("중립형", {"BTC-USD": 0.25, "ETH-USD": 0.25, "GLD": 0.25, "TLT": 0.25}),
    "안정형": Strategy("안정형", {"BTC-USD": 0.10, "ETH-USD": 0.10, "GLD": 0.40, "TLT": 0.40}),
}


@dataclass
class BacktestResult:
    portfolio_values: pd.Series
    benchmark_prices: pd.Series
    daily_returns: pd.Series
    benchmark_returns: pd.Series

    @property
    def cagr(self) -> float:
        start_value = self.portfolio_values.iloc[0]
        end_value = self.portfolio_values.iloc[-1]
        duration_days = (self.portfolio_values.index[-1] - self.portfolio_values.index[0]).days
        years = duration_days / 365.25
        if years <= 0:
            return np.nan
        return (end_value / start_value) ** (1 / years) - 1

    @property
    def mdd(self) -> float:
        running_max = self.portfolio_values.cummax()
        drawdown = self.portfolio_values / running_max - 1
        return drawdown.min()

    @property
    def sharpe_ratio(self) -> float:
        if self.daily_returns.std() == 0:
            return np.nan
        return np.sqrt(252) * self.daily_returns.mean() / self.daily_returns.std()


def fetch_price_data(start: str, end: str) -> pd.DataFrame:
    tickers: List[str] = ASSETS + [BENCHMARK]
    data = yf.download(tickers, start=start, end=end, progress=False)["Adj Close"]
    # Forward-fill to smooth over occasional gaps while keeping only dates with at least
    # one valid price (e.g., holidays when all markets are closed).
    data = data.ffill()
    return data.dropna(how="all")


def first_business_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    first_days = index.to_series().groupby(index.to_period("M")).idxmin()
    return pd.DatetimeIndex(first_days)


def run_backtest(strategy: Strategy, start: str, end: str) -> BacktestResult:
    prices = fetch_price_data(start, end)
    # Forward-fill again after slicing to ensure no NaNs within the asset or benchmark
    # series while keeping the same trading calendar.
    asset_prices = prices[ASSETS].ffill().dropna(how="all")
    benchmark_prices = prices[BENCHMARK].ffill().dropna()

    aligned_index = asset_prices.index.intersection(benchmark_prices.index)
    asset_prices = asset_prices.loc[aligned_index]
    benchmark_prices = benchmark_prices.loc[aligned_index]

    rebal_dates = set(first_business_days(asset_prices.index))

    holdings = pd.Series(0.0, index=ASSETS)
    cash = INITIAL_CAPITAL
    portfolio_values = []

    for date, price_row in asset_prices.iterrows():
        prices_today = price_row
        if date == asset_prices.index[0] or date in rebal_dates:
            portfolio_value = cash + float((holdings * prices_today).sum())
            target_values = pd.Series(strategy.weights) * portfolio_value
            desired_holdings = target_values / prices_today
            trades = desired_holdings - holdings
            trade_values = trades * prices_today
            transaction_fee = TRANSACTION_COST * np.abs(trade_values).sum()

            cash -= trade_values.sum() + transaction_fee
            holdings = desired_holdings
            portfolio_value = cash + float((holdings * prices_today).sum())
        else:
            portfolio_value = cash + float((holdings * prices_today).sum())

        portfolio_values.append((date, portfolio_value))

    portfolio_series = pd.Series({d: v for d, v in portfolio_values}).sort_index()
    portfolio_returns = portfolio_series.pct_change().dropna()
    benchmark_returns = benchmark_prices.pct_change().dropna()

    return BacktestResult(
        portfolio_values=portfolio_series,
        benchmark_prices=benchmark_prices,
        daily_returns=portfolio_returns,
        benchmark_returns=benchmark_returns,
    )


def plot_cumulative_returns(result: BacktestResult, output_path: Path) -> None:
    portfolio_cum = (1 + result.daily_returns).cumprod()
    benchmark_cum = (1 + result.benchmark_returns).cumprod()

    plt.figure(figsize=(10, 6))
    plt.plot(portfolio_cum.index, portfolio_cum, label="Portfolio")
    plt.plot(benchmark_cum.index, benchmark_cum, label=BENCHMARK)
    plt.title("Cumulative Returns: Portfolio vs. SPY")
    plt.xlabel("Date")
    plt.ylabel("Cumulative Return (Base=1.0)")
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def format_percent(value: float) -> str:
    return f"{value * 100:,.2f}%" if pd.notna(value) else "N/A"


def main() -> None:
    parser = argparse.ArgumentParser(description="Asset allocation backtest with monthly rebalancing.")
    parser.add_argument(
        "--strategy",
        default="중립형",
        choices=list(STRATEGIES.keys()),
        help="포트폴리오 전략을 선택하세요 (공격형/중립형/안정형)",
    )
    parser.add_argument("--start", default=START_DATE, help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"), help="Backtest end date (YYYY-MM-DD)")
    parser.add_argument(
        "--plot-path",
        default="plots/cumulative_returns.png",
        type=Path,
        help="Path to save cumulative returns plot",
    )
    args = parser.parse_args()

    strategy = STRATEGIES[args.strategy]
    result = run_backtest(strategy, args.start, args.end)
    plot_cumulative_returns(result, Path(args.plot_path))

    final_value = result.portfolio_values.iloc[-1]
    print(f"전략: {strategy.name}")
    print(f"최종 자산 금액: ${final_value:,.2f}")
    print(f"CAGR: {format_percent(result.cagr)}")
    print(f"MDD: {format_percent(result.mdd)}")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"그래프 저장 위치: {args.plot_path}")


if __name__ == "__main__":
    main()
