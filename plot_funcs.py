import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
                             marker=dict(color='#EA2027', size=8, symbol='triangle-down'))
                  )

    return figure

def dca_plot(dca_data, purchase_dates):

    figure = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           specs=[[{"secondary_y": False}],
                                  [{"secondary_y": True}]],
                           row_width=[0.65, 0.35]
                           )
    figure.update_layout(template='plotly_white')


    figure.add_trace(go.Scatter(x=dca_data.index, y=dca_data['Close'],
                                name='Close Price',
                                mode='lines',
                                line=dict(color='black')
                                ),
                     row=1, col=1)

    buy_series = dca_data.loc[purchase_dates]

    figure.add_trace(go.Scatter(x=buy_series.index,
                                y=buy_series['Balance'],
                                mode='lines',
                                line=dict(color='#ff793f'),
                                name='Share Count'), row=2, col=1, secondary_y=False)

    figure.add_trace(go.Scatter(x=buy_series.index,
                                y=buy_series['Value'],
                                mode='lines',
                                line=dict(color='#1289A7'),
                                name='Investment Value',
                                fill='tonexty'),
                     row=2, col=1, secondary_y=True)

    figure.add_trace(go.Scatter(x=buy_series.index,
                                y=buy_series['Cumulative Spend'],
                                mode='lines',
                                line=dict(color='#ED4C67'),
                                name='Amount Invested'),
                     row=2, col=1, secondary_y=True)

    figure.update_yaxes(row=1, col=1, tickprefix='$', title='Unit Price')
    figure.update_yaxes(row=2, col=1, title='Shares Owned', showgrid=False)
    figure.update_yaxes(row=2, col=1, tickprefix='$', title='Cumulative Worth', secondary_y=True)
    figure['layout']['yaxis2']['showgrid'] = False
    figure['layout']['title'] = '<b>Performance Over Time</b>'

    return figure