import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import trade_logic

# TODO: remove plot padding and simplify available plotly overlay options
# TODO: fix color template for ma lines particularly

def plot_candlestick(plot_data, candlesticks=True):

    # plot_data should have a datetime index & associated name
    figure = go.Figure()

    if candlesticks:
        figure.add_trace(go.Candlestick(x=plot_data.index,
                                           open=plot_data.Open,
                                           close=plot_data.Close,
                                           high=plot_data.High,
                                           low=plot_data.Low,
                                        name=f'{plot_data.name} Close Price'))
    else:
        figure.add_trace(go.Scatter(x=plot_data.index,
                                        y=plot_data.Close,
                                        mode='lines',
                                        line=dict(color='black'),
                                    name=plot_data.name,

                                    ))

    figure.update_layout(template='plotly_white', xaxis_rangeslider_visible=True)
    figure.update_yaxes(tickformat='$')
    return figure

def plot_decisions(figure, decision, price_point, long_bool):

    new_fig = go.Figure(figure)

    marker_dicts = {
        True: dict(color='#009432', size=8, symbol='triangle-up'),
        False: dict(color='#EA2027', size=8, symbol='triangle-down')
                    }

    decision_price = (price_point * decision).replace(0, np.nan)

    # Add Marker
    marker_name = 'Long Entry' if long_bool else 'Short Entry'
    new_fig.add_trace(go.Scatter(x=decision_price.index,
                                y=decision_price.values,
                                mode='markers',
                                marker=marker_dicts.get(long_bool),
                                name=marker_name)
                     )

    return new_fig

def plot_ma(figure, ma_dict):

    new_fig = go.Figure(figure)

    for moving_average in list(ma_dict.keys()):
        ma_line = ma_dict.get(moving_average)
        new_fig.add_trace(go.Scatter(x=ma_line.index,
                                    y=ma_line.values,
                                    mode='lines',
                                    name=moving_average)
                         )

    return new_fig

# Used on the DCA page to track performance over time
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