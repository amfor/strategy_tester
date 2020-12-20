import pandas as pd
import numpy as np
import datetime
pd.set_option('display.max_columns', 15)
pd.set_option('display.width', 150)


# Returns simple moving average with provided span
def sma_line(series, span=None):
    if span is None:
        span = 200
    return series.rolling(window=span).mean()

# Returns exponentially weighed average based on provided span
def ema_line(series, span=None):
    if span is None:
        span = 25
    return series.ewm(span).mean()

buy_strategies = {'Buy on SMA': sma_line,
                  'Buy on EMA': ema_line,
                  'Buy on SMA Crossover': sma_line}

sell_strategies = {'Sell on SMA': sma_line,
              'Sell on EMA': ema_line}

interval_strategy = {'Weekly': 1,
                 'Bi-Monthly': 2,
                 'Monthly': 4}

# Returns the buy date if the daiy price reaches the selected strategy's line.
# Gap prevents buys within small timeframes. ie: Gap of 7 = maximum of a weekly buy frequency
# Returns boolean series with Buy=1, No Buy=0 along with Respective Moving Average(s)
def get_buy_point(asset_data, strategy, gap=0, span=None, scaling=1):

    # TODO: Should the buy point depend on the last day of data (hypothetical purchase date?)
    daily_low = asset_data['Low']

    buy_point = buy_strategies.get(strategy)(asset_data['Close'], span) * scaling

    crossover_sma1 = sma_line(asset_data['Close'], span=200)
    crossover_sma2 = sma_line(asset_data['Close'], span=150)


    # Line 1 Intersects Line 2 between points 0 and 1 when l1_0 < l2_0 & l1_1 > l2_1
    crossover_line = ((daily_low < buy_point) & (daily_low.shift(1) > buy_point.shift(1))).astype(int)

    # TODO: make compatible with date index
    if gap > 0:
        new_line = [value if (value == 1 and (1 != crossover_line.values[idx + 1: idx + gap + 1]).all())
                                   else 0 for idx, value in zip(range(0, len(crossover_line)), crossover_line.values)]
        crossover_line = pd.Series(data=new_line,
                             index=crossover_line.index)
    return crossover_line, buy_point


# Returns the buy date if the daiy price reaches the selected strategy's line.
# Gap prevents buys within small timeframes. ie: Gap of 7 = maximum of a weekly buy frequency
# Returns boolean series with Buy=1, No Buy=0 along with Respective Moving Average(s)
def get_sell_point(asset_data, strategy, gap=0, span=None, scaling=1):

    # TODO: Should the buy point depend on the last day of data (hypothetical purchase date?)
    daily_high = asset_data['High']

    sell_point = sell_strategies.get(strategy)(asset_data['Close'], span) * scaling

    # Line 1 Intersects Line 2 between points 0 and 1 when l1_0 < l2_0 & l1_1 > l2_1
    crossover_line = ((daily_high > sell_point) & (daily_high.shift(1) < sell_point.shift(1))).astype(int)

    # TODO: make compatible with date index
    if gap > 0:
        new_line = [value if (value == 1 and (1 != crossover_line.values[idx + 1: idx + gap + 1]).all())
                                   else 0 for idx, value in zip(range(0, len(crossover_line)), crossover_line.values)]
        crossover_line = pd.Series(data=new_line,
                             index=crossover_line.index)
    return crossover_line, sell_point

# Returns series of -1, 0, 1 values. 1 = series_one crosses upward, -1 = series_two crosses upward, 0 = No Cross
def get_crossover_point(series_one, series_two):

    downward_cross = ((series_one > series_two) & (series_one.shift(1) < series_two.shift(1))).astype(int)
    upward_cross = ((series_one < series_two) & (series_one.shift(1) > series_two.shift(1))).astype(int)

    return upward_cross, downward_cross


# Logic for a naive buying strategy on a specific weekday at certain intervals.
# If the buy amount is < share price, the share quantity bought will be 1. Assumes no fractional shares.
def dca_buy_report(asset_data, weekday, strategy, interval, usd_buy_amount, allow_fractional=False):

    buy_dates = asset_data.index[asset_data.index.weekday == weekday][::interval]
    buy_df = asset_data.loc[buy_dates, ['Open', 'Close']]

    prelim_share_amount = (usd_buy_amount / buy_df[strategy])
    buy_df['Shares Bought'] = prelim_share_amount if allow_fractional else prelim_share_amount.astype(int).replace(0, 1)
    buy_df['Balance'] = buy_df['Shares Bought'].expanding().apply(sum)
    if not allow_fractional:
        buy_df['Balance'] = buy_df['Balance'].astype(int)
    buy_df['Cost Basis'] = (buy_df['Shares Bought'] * buy_df[strategy]).expanding().apply(sum) / buy_df['Balance']
    buy_df['Cumulative Spend'] = (buy_df['Shares Bought'] * buy_df[strategy]).expanding().apply(sum)
    buy_df = asset_data.merge(buy_df.drop(['Open', 'Close'], axis=1),
                              how='left', left_index=True, right_index=True)

    fill_cols = ['Balance', 'Cost Basis', 'Cumulative Spend']
    buy_df.loc[:, fill_cols] = buy_df.loc[:, fill_cols].fillna(method='ffill')
    buy_df.fillna(0, inplace=True)

    buy_df['Unrealized PNL'] = buy_df['Balance'] * (buy_df['Close'] - buy_df['Cost Basis'])
    buy_df['Value'] = buy_df['Balance'] * buy_df['Close']
    buy_df['ROE %'] = (buy_df['Value'] / buy_df['Cumulative Spend'] - 1) * 100

    return buy_df, buy_dates

# See https://oxfordstrat.com/indicators/td-sequential-2/ for more details on TD implementation
def td_strategy(td_df, long_bool=True):

    def td_setup_func(bool_arr):
        # O(n) loop. Could likely improve on complexity, but am unsure how.
        new_arr = list()
        count = 0

        for obs in bool_arr:
            if obs == True:
                count = count + 1
            else:
                count = 0
            new_arr.append(count)
        return new_arr

    def td_countdown_func(bool_arr):
        # O(n) loop. Could likely improve on complexity, but am unsure how.
        new_arr = list()
        count = 0

        for obs in bool_arr:
            if obs == True:
                count = count + 1
                new_arr.append(count)
            else:
                new_arr.append(np.nan)
        return new_arr


    close_df = td_df['Close'].to_numpy()
    countdown_df = td_df[['Close', 'Low', 'High']]

    # Intersection
    # Boolean of TD; greater/lesser than last 4 closes.

    if long_bool:
        td_setup = np.append(np.full(4, np.nan),
                               [(close_df[idx] < close_df[idx - 4]) for idx in range(4, len(close_df))])
    else:
        td_setup = np.append(np.full(4, np.nan),
                                [(close_df[idx] > close_df[idx - 4]) for idx in range(4, len(close_df))])
        
    setup_count = pd.Series(td_setup_func(td_setup), index=td_df.index)
    td_nines = setup_count.index[setup_count == 9]

    countdown_list = list()
    for idx in range(0, len(td_nines)):
        start = td_nines[idx]
        start_idx = td_df.index[td_df.index.get_loc(start) - 2]

        if idx + 1 == len(td_nines):
            end = start_idx + datetime.timedelta(days=35)
        else:
            end = min(td_nines[idx + 1], start_idx + datetime.timedelta(days=35))

        countdown_span = countdown_df.loc[start_idx:end + datetime.timedelta(days=1)]

        if long_bool:
            td_countdown = [(countdown_span.loc[:, 'Close'][idx] < countdown_span.loc[:, 'Low'][idx - 2])
                              for idx in range(2, len(countdown_span))]
        else:
            td_countdown = [(countdown_span.loc[:, 'Close'][idx] > countdown_span.loc[:, 'High'][idx - 2])
                            for idx in range(2, len(countdown_span))]
        countdown_list.append(pd.Series(td_countdown_func(td_countdown), index=countdown_span.index[2:]))

    countdowns = pd.concat(countdown_list)
