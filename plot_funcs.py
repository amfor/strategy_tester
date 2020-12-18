import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import trade_logic


def plot_candlestick(plot_data):

    # plot_data should have a datetime index & associated name
    fig = go.Figure()

    fig.add_trace(go.Candlestick(x=plot_data.index,
                                       open=plot_data.Open,
                                       close=plot_data.Close,
                                       high=plot_data.High,
                                       low=plot_data.Low))

    fig.update_layout(template='plotly_white')
    fig.update_yaxes(tickformat='$')
    return fig


def plot_buys(plot_data, ma_span=200, strategy='Buy on SMA', scaling=1):

    fig = plot_candlestick(plot_data)

    decision, price_point = trade_logic.get_buy_point(strategy=strategy, asset_data=plot_data, gap=14, scaling=scaling)

    buy_series = (price_point * decision).replace(0, np.nan)
    marker_series = np.full(len(buy_series), 'triangle-up')


    fig.add_trace(go.Scatter(x=price_point.index,
                             y=price_point.values,
                             mode='lines',
                             line=dict(color='#0a3d62', width=1.5))
                  )


    fig.add_trace(go.Scatter(x=buy_series.index,
                             y=buy_series.values,
                             mode='markers',
                             marker=dict(color='#009432', size=10, symbol='triangle-up'))
                  )

    fig.update_layout(xaxis_rangeslider_visible=False)

    return fig