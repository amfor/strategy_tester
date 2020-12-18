import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import trade_logic


def plot_candlestick(plot_data):

    # plot_data should have a datetime index & associated name
    figure = go.Figure()

    figure.add_trace(go.Candlestick(x=plot_data.index,
                                       open=plot_data.Open,
                                       close=plot_data.Close,
                                       high=plot_data.High,
                                       low=plot_data.Low))

    figure.update_layout(template='plotly_white', xaxis_rangeslider_visible=True)
    figure.update_yaxes(tickformat='$')
    return figure


def plot_buys(figure, plot_data, ma_span=200, strategy='Buy on SMA', scaling=1):

    decision, price_point = trade_logic.get_buy_point(strategy=strategy, asset_data=plot_data, gap=14, scaling=scaling)
    buy_series = (price_point * decision).replace(0, np.nan)
    marker_series = np.full(len(buy_series), 'triangle-up')

    figure.add_trace(go.Scatter(x=price_point.index,
                             y=price_point.values,
                             mode='lines',
                             line=dict(color='#0a3d62', width=1.5))
                  )

    figure.add_trace(go.Scatter(x=buy_series.index,
                             y=buy_series.values,
                             mode='markers',
                             marker=dict(color='#009432', size=8, symbol='triangle-up'))
                  )

    return figure

def plot_sells(figure, plot_data, ma_span=200, strategy='Buy on SMA', scaling=1):

    decision, price_point = trade_logic.get_sell_point(strategy=strategy, asset_data=plot_data, gap=14, scaling=scaling)
    buy_series = (price_point * decision).replace(0, np.nan)
    marker_series = np.full(len(buy_series), 'triangle-down')

    figure.add_trace(go.Scatter(x=price_point.index,
                             y=price_point.values,
                             mode='lines',
                             line=dict(color='#6F1E51', width=1.5))
                  )

    figure.add_trace(go.Scatter(x=buy_series.index,
                             y=buy_series.values,
                             mode='markers',
                             marker=dict(color='#EA2027', size=10, symbol='triangle-down'))
                  )

    return figure