import pandas as pd

# Returns simple moving average with provided span
def sma_line(series, span=200):
    return series.rolling(window=span).mean()

# Returns exponentially weighed average based on provided span
def ema_line(series, span=14):
    return series.ewm(span).mean()

strategies = {'Buy on SMA': sma_line,
              'Buy on EMA': ema_line}

# Returns the buy date if the daiy price reaches the selected strategy's line.
# Gap prevents buys within small timeframes. ie: Gap of 7 = maximum of a weekly buy frequency
# Returns boolean series with Buy=1, No Buy=0 along with Respective Moving Average(s)
def get_buy_point(strategy, asset_data, gap=0, scaling=1):

    # TODO: Should the buy point depend on the last day of data (hypothetical purchase date?)
    daily_low = asset_data['Low']
    buy_point = strategies.get(strategy)(asset_data['Close']) * scaling

    # Line 1 Intersects Line 2 between points 0 and 1 when l1_0 < l2_0 & l1_1 > l2_1
    crossover_line = ((daily_low < buy_point) & (daily_low.shift(1) > buy_point.shift(1))).astype(int)

    # TODO: make compatible with date index
    if gap > 0:
        new_line = [value if (value == 1 and (1 != crossover_line.values[idx + 1: idx + gap + 1]).all())
                                   else 0 for idx, value in zip(range(0, len(crossover_line)), crossover_line.values)]
        crossover_line = pd.Series(data=new_line,
                             index=crossover_line.index)
    return crossover_line, buy_point

