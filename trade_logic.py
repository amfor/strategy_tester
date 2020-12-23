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

strategies = {'Hold/None': None,
              'On SMA': sma_line,
              'On EMA': ema_line,
              'On SMA Crossover': sma_line,
              'On EMA Crossover': ema_line,
              'TD Countdown': None}

interval_strategy = {'Weekly': 1,
                 'Bi-Monthly': 2,
                 'Monthly': 4}

# Gap prevents buys/sells within small timeframes. ie: Gap of 7 = maximum of a weekly buy frequency
# Returns boolean series with Buy=1, No Buy=0 along with Respective Moving Average(s)
def get_trades(asset_data, long_bool, strategy, gap=0, spans=(None), scaling=1):

    ma_dict = {}
    if strategy in ['On SMA', 'On EMA']:
        ma_type = strategy.split('On ')[-1]
        trade_func = strategies.get(strategy)
        trade_bound = asset_data['High'] if long_bool else asset_data['Low']
        trade_point = trade_func(asset_data['Close'], span=spans[0]) * scaling # Buy/Sell on the MA line
        crossover_line = get_crossover_point(trade_bound, trade_point, upward=long_bool)
        ma_dict = {f'{ma_type} ({spans[0]})': trade_point}


    elif strategy in ['On SMA Crossover', 'On EMA Crossover']:
        ma_type = strategy.split(' Crossover')[0].split('On ')[-1]
        trade_func = strategies.get(strategy)
        ma_one = trade_func(asset_data['Close'], span=spans[0])
        ma_two = trade_func(asset_data['Close'], span=spans[1])
        crossover_line = get_crossover_point(ma_one, ma_two, upward=long_bool)
        trade_point = asset_data.loc[crossover_line.index, 'Close']
        ma_dict = {f'{ma_type} ({spans[0]})': ma_one,
                    f'{ma_type} ({spans[1]})': ma_two}

    elif strategy == 'TD Countdown':
        decision, trade_point = td_strategy(td_df=asset_data, long_bool=long_bool)
        return decision, trade_point, ma_dict

    # TODO: make compatible with date index
    if gap > 0:
        new_line = [value if (value == 1 and (1 != crossover_line.values[idx + 1: idx + gap + 1]).all())
                    else 0 for idx, value in zip(range(0, len(crossover_line)), crossover_line.values)]
        crossover_line = pd.Series(data=new_line,
                                   index=crossover_line.index)

    return crossover_line, trade_point, ma_dict


# Returns series of  0, 1 values. 1 = series_one crosses series two, 0 = No Cross
# Series one should be of a lower span than series two.
def get_crossover_point(series_one, series_two, upward=True):

    if upward:
        cross_series = ((series_one < series_two) & (series_one.shift(-1) > series_two.shift(-1))).astype(int)
    else:
        cross_series = ((series_one > series_two) & (series_one.shift(-1) < series_two.shift(-1))).astype(int)

    return cross_series


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

    # Boolean of TD; greater/lesser than last 4 closes.
    if long_bool:
        td_setup = np.append(np.full(4, np.nan),
                               [(close_df[idx] < close_df[idx - 4]) for idx in range(4, len(close_df))])
    else:
        td_setup = np.append(np.full(4, np.nan),
                                [(close_df[idx] > close_df[idx - 4]) for idx in range(4, len(close_df))])

    # Gather the setups to calculate the countdowns thereafter
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

    decision = (countdowns == 13).astype(int)
    trade_point = td_df.loc[:, 'Close']


    return decision, trade_point


def pnl_calc(buy_series, sell_series, trade_size, allow_fractional=True, sell_all=True):

    buy_df = pd.DataFrame(zip(buy_series.values, np.full(len(buy_series), 'Buy')), columns=['Price', 'Decision'],
                          index=buy_series.index)
    buy_df['Share Diff'] = (trade_size / buy_df['Price']) if allow_fractional \
        else (trade_size / buy_df['Price']).astype(int).replace(0, 1) # Buy 1 Share at minimum.
    sell_df = pd.DataFrame(zip(sell_series.values, np.full(len(sell_series), 'Sell')), columns=['Price', 'Decision'],
                           index=sell_series.index).loc[buy_df.index[0]:]
    if not sell_all:
        sell_df['Share Diff'] = -(trade_size / sell_df['Price']) if allow_fractional \
            else -(trade_size / sell_df['Price']).astype(int).replace(0, 1)

    trade_df = pd.concat([buy_df, sell_df]).sort_index()

    trade_df[['Share Balance', 'Balance Value', 'Cash Balance']] = np.nan
    ['Stock Splits', 'Shares Bought', 'Balance', 'Cost Basis', 'Cumulative Spend', 'Unrealized PNL', 'Value', 'ROE %']

    carryover_cols = ['Share Balance', 'Balance Value', 'Cash Balance']
    carryover_balance = (0, 0, 0)
    tranche_list = list()
    start_index = trade_df.index[0]
    for idx in sell_df.index:
        tranche_until = idx + datetime.timedelta(days=1)
        tranche = trade_df.loc[start_index: tranche_until].copy()
        if tranche_until <= trade_df.index[-1]:
            start_loc = trade_df.index.get_loc(tranche_until, method='bfill')
            start_index = trade_df.index[start_loc]
        else:
            break
        tranche_sell = tranche.index[-1]

        if len(tranche.loc[tranche['Decision'] == 'Buy']) == 0:
            if sell_all:
                continue
            elif carryover_balance[0] < np.abs(tranche.loc[tranche_sell, 'Share Diff']):
                tranche.at[tranche_sell, 'Share Diff'] = -carryover_balance[0] # Limit sell to available balance

        sell_price = tranche.loc[tranche_sell, 'Price']

        if sell_all:
            sell_amount = tranche['Share Diff'].sum()
            tranche.at[tranche_sell, 'Share Diff'] = -sell_amount
        else:
            sell_amount = tranche.loc[tranche_sell, 'Share Diff']

        tranche['Trade Value'] = tranche['Share Diff'].values * tranche['Price'].values

        tranche.at[:, 'Share Balance'] = tranche.loc[:, 'Share Diff'].expanding().apply(sum).values + carryover_balance[0]
        tranche.at[:, 'Balance Value'] = tranche.loc[:, 'Price'] * tranche.loc[:, 'Share Balance']
        tranche.at[tranche_sell, 'Cash Balance'] = np.abs(sell_amount) * sell_price
        tranche['Cash Balance'] = tranche['Cash Balance'].fillna(0) + carryover_balance[2]

        #tranche.loc[tranche_sell, carryover_cols] = tranche.loc[tranche_sell, carryover_cols] + carryover_balance
        carryover_balance = tuple(tranche.loc[tranche_sell, carryover_cols].values)

        tranche_list.append(tranche)

        print(tranche)

    final_pnl = pd.concat(tranche_list)