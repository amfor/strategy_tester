import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def plot_price_data(plot_data, candlesticks=True):

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
                                        line=dict(color='#1e272e'),
                                    name=plot_data.name,

                                    ))

    figure.update_layout(template='plotly_white', margin=dict(l=20, r=20, t=20, b=20), xaxis_rangeslider_visible=True)
    figure.update_yaxes(tickformat='$')
    return figure

def plot_decisions(figure, decisions, price_point,  markers=True):

    new_fig = go.Figure(figure)

    line_dicts = {
        'Buys': '#009432',
        'Sells': '#EA2027'
    }
    marker_dicts = {
        'Buys': dict(color='#009432', size=8, symbol='triangle-up'),
        'Sells': dict(color='#EA2027', size=8, symbol='triangle-down')
    }

    trades = {'Buys': decisions == 1, 'Sells': decisions == -1}
    if markers:
        for decision in list(trades.keys()):
            mask = trades.get(decision)
            # Add Markers
            decision_price = (price_point.loc[mask] * decisions.loc[mask].abs()).replace(0, np.nan)
            marker_name = 'Long Entry' if decision == 'Buy' else 'Short Entry'
            new_fig.add_trace(go.Scatter(x=decision_price.index,
                                        y=decision_price.values,
                                        mode='markers',
                                        marker=marker_dicts.get(decision),
                                        name=marker_name)
                             )
    else:
        shapes = {}
        for decision in list(trades.keys()):
            mask = trades.get(decision)

            line_color = line_dicts.get(decision)
            decision_series = decisions.loc[mask]

            if not decision_series.empty:
                for date in tuple(decision_series.index.date):
                    shapes[date.strftime('%Y-%m-%d')] = go.layout.Shape(line=dict(color=line_color, width=1),
                                 opacity=0.6, type='line', x0=date, x1=date, xref='x', y0=0, y1=1, yref='y domain')
        new_fig.update_layout(shapes=list(shapes.values()))

    return new_fig

def plot_ma(figure, ma_dict, long_bool):

    new_fig = go.Figure(figure)

    ma_keys = list(ma_dict.keys())
    if len(ma_keys) == 0:
        return new_fig
    else:
        colors = ("#006266", "#05c46b") if long_bool else ("#6F1E51", "#ff5e57")
        ma_colors = dict(zip(ma_keys, colors))

        for moving_average in ma_keys:
            ma_line = ma_dict.get(moving_average)
            new_fig.add_trace(go.Scatter(x=ma_line.index,
                                            y=ma_line.values,
                                            mode='lines',
                                            line=dict(color=ma_colors.get(moving_average), width=1),
                                            name=moving_average)
                             )
        return new_fig

# Used on the DCA page to track performance over time
def dca_plot(dca_data, purchase_dates):

    figure = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           specs=[[{"secondary_y": False}],
                                  [{"secondary_y": True}]],
                           row_width=[0.65, 0.35],
                           vertical_spacing=0.02
                           )
    figure.update_layout(template='plotly_white', margin=dict(l=0, t=25), height=600)


    figure.add_trace(go.Scatter(x=dca_data.index, y=dca_data['Close'],
                                name='Close Price',
                                mode='lines',
                                line=dict(color='black')
                                ),
                     row=1, col=1)

    buy_series = dca_data.loc[purchase_dates]

    figure.add_trace(go.Scatter(x=buy_series.index,
                                y=buy_series['Share Balance'],
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