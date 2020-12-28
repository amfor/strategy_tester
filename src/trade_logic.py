import pandas as pd
import numpy as np
import datetime

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
def get_trades(asset_data, long_bool, strategy, gap=0, spans=(None), scaling=1, start=None):


    start = asset_data.index[0] if start is None else start
    ma_dict = {}
    if 'Hold' in strategy:
        return pd.Series(dtype=float), pd.Series(dtype=float), ma_dict
    elif strategy in ['On SMA', 'On EMA']:
        ma_type = strategy.split('On ')[-1]
        trade_func = strategies.get(strategy)
        trade_bound = (asset_data['High'] if long_bool else asset_data['Low']).loc[start:]
        trade_point = (trade_func(asset_data['Close'], span=spans[0]) * scaling).loc[start:] # Buy/Sell on the MA line
        crossover_line = get_crossover_point(trade_bound, trade_point, upward=long_bool)
        ma_dict = {f'{ma_type} ({spans[0]})': trade_point}


    elif strategy in ['On SMA Crossover', 'On EMA Crossover']:
        ma_type = strategy.split(' Crossover')[0].split('On ')[-1]
        trade_func = strategies.get(strategy)
        ma_one = trade_func(asset_data['Close'], span=spans[0])
        ma_two = trade_func(asset_data['Close'], span=spans[1])
        crossover_line = get_crossover_point(ma_one, ma_two, upward=long_bool).loc[start:]
        trade_point = asset_data.loc[crossover_line.index, 'Close']
        ma_dict = {f'{ma_type} ({spans[0]})': ma_one, f'{ma_type} ({spans[1]})': ma_two}

    elif strategy == 'TD Countdown':
        decision, trade_point = td_strategy(td_df=asset_data, long_bool=long_bool, start_date=start)
        return decision, trade_point, ma_dict

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
    buy_df['Share Balance'] = buy_df['Shares Bought'].cumsum()
    if not allow_fractional:
        buy_df['Share Balance'] = buy_df['Share Balance'].astype(int)
    buy_df['Cost Basis'] = (buy_df['Shares Bought'] * buy_df[strategy]).cumsum() / buy_df['Share Balance']
    buy_df['Cumulative Spend'] = (buy_df['Shares Bought'] * buy_df[strategy]).cumsum()
    buy_df = asset_data.merge(buy_df.drop(['Open', 'Close'], axis=1),
                              how='left', left_index=True, right_index=True)

    fill_cols = ['Share Balance', 'Cost Basis', 'Cumulative Spend']
    buy_df.loc[:, fill_cols] = buy_df.loc[:, fill_cols].fillna(method='ffill')
    buy_df.fillna(0, inplace=True)

    buy_df['Unrealized PNL'] = buy_df['Share Balance'] * (buy_df['Close'] - buy_df['Cost Basis'])
    buy_df['Value'] = buy_df['Share Balance'] * buy_df['Close']
    buy_df['ROE %'] = (buy_df['Value'] / buy_df['Cumulative Spend'] - 1) * 100

    buy_df = buy_df.drop(['Low', 'High', 'Open', 'Volume', 'Dividends', 'Stock Splits'], axis=1).fillna(0)

    return buy_df, buy_dates

# See https://oxfordstrat.com/indicators/td-sequential-3/ for more details on TD implementation
# Not implemented: Countdown Cancellation & Recycling
def td_strategy(td_df, long_bool=True, start_date=None):

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


    start_date = td_df.index[0] if start_date is None else start_date
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

    # Calculate Countdowns until 35 days after start or next TD 9 setup, whichever comes first.
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

    countdowns = pd.concat(countdown_list).dropna()
    countdowns = countdowns.loc[~countdowns.index.duplicated('first')].loc[start_date:]
    td_thirteens = countdowns.loc[countdowns==13]

    # Ensure TD Countdown meets Qualifier Criteria
    comparison_col = 'Low' if long_bool else 'High'
    prior_date = countdowns.index[0]
    for thirteen_date in td_thirteens.index:
        until_date = countdowns.index[countdowns.index.get_loc(thirteen_date) + 1]
        countdown_subset = countdowns[prior_date:until_date]
        thirteen_idx = td_df.index.get_loc(thirteen_date)
        thirteen_low = td_df.loc[thirteen_date, comparison_col]
        thirteen_close = td_df.loc[thirteen_date, 'Close']
        eight_close = td_df.loc[countdown_subset.index[countdown_subset == 8][-1], 'Close']
        eleven_low = td_df.loc[countdown_subset.index[countdown_subset == 11][-1], comparison_col]

        if long_bool:
            qualifier_bool = (thirteen_low <= eight_close) and (thirteen_close <= eleven_low)
        else:
            qualifier_bool = (thirteen_low >= eight_close) and (thirteen_close >= eleven_low)

        if not qualifier_bool:
            td_thirteens.drop(thirteen_date, inplace=True)
        prior_date = until_date

    decision = (countdowns == 13).astype(int)
    trade_point = td_df.loc[:, 'Close']


    return decision, trade_point

# Calculates PNL and associated balance data
# Rejects excess sells (ie: when Share Balance == 0) and returns a proper trade history.
def pnl_calc(asset_data, buy_series, sell_series, trade_size, allow_fractional=True, sell_all=True):

    # Bring sells/buys together in a DataFrame & fetch closing price
    buy_df = pd.DataFrame(zip(buy_series.values, np.full(len(buy_series), 'Buy')), columns=['Price', 'Decision'],
                          index=buy_series.index)
    buy_df['Share Diff'] = (trade_size / buy_df['Price']) if allow_fractional \
        else (trade_size / buy_df['Price']).astype(int).replace(0, 1) # Buy 1 Share at minimum.

    # Return empty DF if no buys occur
    table_columns = ['Price', 'Decision', 'Share Diff', 'Closing Price', 'Share Balance', 'Balance Value',
                     'Cash Balance', 'Cost Basis', 'Trade Value', 'UPNL', 'RPNL']
    if buy_series.empty:
        return pd.DataFrame(np.full((1, len(table_columns)), 0), columns=table_columns, index=[datetime.date.today()])

    proper_sells = sell_series[buy_series.index[0]:]  # Remove all sells ovvuring prior to first buy date
    statement_end_entry = asset_data.iloc[-1]  # The last date in asset history (to calculate most recent PNLs)

    if proper_sells.empty:
        trade_df = buy_df.copy()
        trade_df['Closing Price'] = asset_data.loc[trade_df.index, 'Close']

        # Add in Closing Statement
        trade_df.loc[statement_end_entry.name, ['Price', 'Closing Price']] = statement_end_entry['Close']
        trade_df.loc[statement_end_entry.name, ['Share Diff', 'Trade Value']] = 0
        trade_df.loc[statement_end_entry.name, ['Decision']] = 'Closing Statement'

        # Calculate Share Balance, Fiat Value, Trade Value, Cost Basis
        trade_df['Trade Value'] = np.round(trade_df['Share Diff'].values * trade_df['Price'].values, 2)
        trade_df.at[:, 'Share Balance'] = trade_df.loc[:, 'Share Diff'].cumsum()
        trade_df.at[:, 'Cost Basis'] = np.divide((trade_df.loc[:, 'Price'] * trade_df.loc[:, 'Share Diff']).cumsum(),
                                                    trade_df.loc[:, 'Share Balance'])
        trade_df.at[:, 'Balance Value'] = trade_df['Price'].values * trade_df['Share Balance'].values
        trade_df.loc[:, ['Cash Balance', 'RPNL']] = 0
        trade_df.loc[:, ['Share Balance', 'Cost Basis']] = \
            trade_df.loc[:, ['Share Balance', 'Cost Basis']].ffill()
        trade_df.loc[:, 'UPNL'] = np.multiply(trade_df.loc[:, 'Price'] - trade_df.loc[:, 'Cost Basis'],
                                              trade_df.loc[:, 'Share Balance'])
        return trade_df

    sell_df = pd.DataFrame(zip(proper_sells.values, np.full(len(proper_sells), 'Sell')), columns=['Price', 'Decision'],
                           index=proper_sells.index).loc[buy_df.index[0]:]
    if not sell_all:
        sell_df['Share Diff'] = -(trade_size / sell_df['Price']) if allow_fractional \
            else -(trade_size / sell_df['Price']).astype(int).replace(0, 1)

    trade_df = pd.concat([buy_df, sell_df]).sort_index()
    trade_df['Closing Price'] = asset_data.loc[trade_df.index, 'Close']

    # Compute PNL while removing unmatched sells
    carryover_cols = ['Share Balance', 'Balance Value', 'Cash Balance', 'Cost Basis']
    trade_df[carryover_cols] = np.nan
    carryover_balance = (0, 0, 0, 0)
    tranche_list = list()
    start_index = trade_df.index[0]
    # Split DF into subsets, depending on sell indices. Perform PNL calc on subsets serially & carryover data.
    for idx in sell_df.index:
        # Select subset based on next sell date.
        tranche_until = idx + datetime.timedelta(days=1)
        tranche = trade_df.loc[start_index: tranche_until].copy()
        if tranche_until <= trade_df.index[-1]:
            start_loc = trade_df.index.get_loc(tranche_until, method='bfill')
            start_index = trade_df.index[start_loc]
        else:
            break
        tranche_sell = tranche.index[-1]

        if len(tranche.loc[tranche['Decision'] == 'Buy']) == 0:

            # Do not Carry Over Cost Basis is we have shares remaining
            if carryover_balance[0] == 0:
                tranche.at[tranche_sell, 'Cost Basis'] = 0  # Limit sell to available balance
            else:
                tranche.at[tranche_sell, 'Cost Basis'] = carryover_balance[3]  # Limit sell to available balance

            if sell_all:
                continue
            elif carryover_balance[0] < np.abs(tranche.loc[tranche_sell, 'Share Diff']):
                tranche.at[tranche_sell, 'Share Diff'] = -carryover_balance[0] # Limit sell to available balance

        sell_price = tranche.loc[tranche_sell, 'Price']

        if sell_all:
            sell_amount = tranche['Share Diff'].sum().round(2)
            tranche.at[tranche_sell, 'Share Diff'] = -sell_amount
        else:
            sell_amount = tranche.loc[tranche_sell, 'Share Diff'].round(2)

        # Calculate Share Balance, Fiat Value, Trade Value, Cost Basis
        tranche['Trade Value'] = np.round(tranche['Share Diff'].values * tranche['Price'].values, 2)
        tranche.at[:, 'Share Balance'] = tranche.loc[:, 'Share Diff'].cumsum().round(2) + carryover_balance[0]
        tranche.at[:, 'Balance Value'] = tranche['Price'].values * tranche['Share Balance'].values
        tranche.at[:, 'Balance Value'] = tranche['Price'].values * tranche['Share Balance'].values

        mask = tranche['Decision'] == 'Buy'
        acb_worth = carryover_balance[0] * carryover_balance[3]
        tranche.loc[mask, 'Cost Basis'] = np.round(np.divide((acb_worth +
                                           (tranche.loc[mask, 'Price'] * tranche.loc[mask, 'Share Diff']).cumsum()),
                                          tranche.loc[mask, 'Share Balance']), 4)
        tranche.fillna(method='ffill', inplace=True)  # Fill forward the cost basis (into the sell index)

        #  Calculate Sell Amount w/ Carryover Cash Balance
        tranche.at[tranche_sell, 'Cash Balance'] = np.round(np.abs(sell_amount) * sell_price, 2)
        tranche['Cash Balance'] = np.round(tranche['Cash Balance'].fillna(0) + carryover_balance[2], 2)

        carryover_balance = tuple(tranche.loc[tranche_sell, carryover_cols].values)
        tranche_list.append(tranche)

    final_pnl = pd.concat(tranche_list)
    if not final_pnl.index[final_pnl['Trade Value'] == 0].empty:
        final_pnl.drop(final_pnl.index[final_pnl['Trade Value'] == 0], inplace=True)  # Remove excess sells

    # Add in Closing Statement for proper valuation
    final_pnl.loc[statement_end_entry.name, ['Price', 'Closing Price']] = statement_end_entry['Close']
    final_pnl.loc[statement_end_entry.name, ['Share Diff', 'Trade Value']] = 0
    final_pnl.loc[statement_end_entry.name, ['Decision']] = 'Closing Statement'
    final_pnl.loc[:, ['Share Balance', 'Cost Basis']] = \
        final_pnl.loc[:, ['Share Balance', 'Cost Basis']].ffill()

    mask = final_pnl['Decision'] == 'Sell'
    profit_margin = (final_pnl.loc[:, 'Price'] - final_pnl.loc[:, 'Cost Basis'])
    final_pnl.loc[mask, 'RPNL'] = (profit_margin.loc[mask] * -final_pnl.loc[mask, 'Share Diff']).cumsum()
    final_pnl.loc[:, 'UPNL'] = np.multiply(profit_margin, final_pnl.loc[:, 'Share Balance'])
    final_pnl = final_pnl.ffill().fillna(0)

    return final_pnl
