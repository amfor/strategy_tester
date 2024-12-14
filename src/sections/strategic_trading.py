import streamlit as st 
from logic.styling import color_negative_red, dollar_format
from logic import plot_funcs, trade_logic
import pandas as pd 
import numpy as np

from data.config import app_defaults
other_params, buy_params_one, buy_params_two, sell_params_one, sell_params_two = st.columns(5)

available_strategies = list(trade_logic.strategies.keys())
available_buy_strategies = available_strategies.copy()
available_buy_strategies.remove('Hold/None')

with other_params:
    trade_size = st.number_input('Enter Trade Value', value=250, step=50)
    gap_days = st.number_input('Minimum Gap Days Between Buys', value=7, step=1)

with buy_params_one:
    buy_strategy = st.selectbox('Select Buying Strategy', available_buy_strategies)
    buy_scaling = st.number_input('MA Scaling (<=1.00)', value=0.95, step=0.025) \
        if pd.Series([_ not in buy_strategy for _ in ['Crossover', 'Countdown']]).all() else None

with buy_params_two:
    if 'Crossover' in buy_strategy:
        buy_ma_span_one = st.number_input('1st MA Span (Short Term)', value=50, step=5, key='buy_ma_1')
        buy_ma_span_two = st.number_input('2nd MA Span (Long Term)', value=150, step=10, key='buy_ma_2')
    elif 'MA' in buy_strategy:
        buy_ma_span_one = st.number_input('Buy MA Span', value=25, step=5)
        buy_ma_span_two = None
    else:
        buy_ma_span_one, buy_ma_span_two = None, None

with sell_params_one:
    initial_strategy = available_strategies.index('TD Countdown')
    sell_strategy = st.selectbox('Select Selling Strategy', available_strategies, index=initial_strategy)
    sell_scaling = st.number_input('MA Scaling (>=1.00)', value=1.05, step=0.025) \
        if pd.Series([_ not in sell_strategy for _ in ['Crossover', 'Hold', 'Countdown']]).all() else None

with sell_params_two:
    if 'Crossover' in sell_strategy:
        sell_ma_span_one = st.number_input('1st MA Span (Short Term)', value=50, step=5, key='sell_ma_1')
    elif pd.Series([_ not in sell_strategy for _ in ['Hold', 'Countdown']]).all():
        sell_ma_span_one = st.number_input('Sell MA Span', value=25, step=5)
    else:
        sell_ma_span_one = None
    sell_ma_span_two = st.number_input('2nd MA Span (Long Term)', value=150, step=10, key='sell_ma_2') \
        if 'Crossover' in sell_strategy else None

pnl_table, buy_ma_lines, sell_ma_lines = trade_logic.process_pnl_table(buy_ma_span_one=buy_ma_span_one,
                buy_ma_span_two=buy_ma_span_two,
                sell_ma_span_one=sell_ma_span_one,
                sell_ma_span_two=sell_ma_span_two,
                buy_strategy=buy_strategy,
                sell_strategy=sell_strategy,
                history=st.session_state['history'],
                gap_days=gap_days,
                    buy_scaling=buy_scaling,
                    sell_scaling=sell_scaling,
                    start_date=st.session_state['start_date'],
                        trade_size=trade_size,
                    allow_fractional=st.session_state.get('allow_fractional', app_defaults['allow_fractional']),
                        sell_all=st.session_state.get('sell_all', app_defaults['sell_all']))



# Get the proper data to plot (What we actually end up trading)
plot_buy = (pnl_table['Decision'] == 'Buy').astype(int)
plot_buy_price = pnl_table.loc[plot_buy.index, 'Price']
plot_sell = -(pnl_table['Decision'] == 'Sell').astype(int)
plot_sell_price = pnl_table.loc[plot_sell.index, 'Price']
combined_decisions = pd.concat([plot_buy, plot_sell])
combined_prices = pd.concat([plot_buy_price, plot_sell_price])

# Save and write closing position data
shares_owned = pnl_table.iloc[-1]['Share Balance']
balance = np.round(shares_owned, 2) if st.session_state.get('allow_fractional', app_defaults['allow_fractional']) else int(shares_owned)
spend_str = dollar_format(pnl_table.loc[pnl_table['Decision'] == 'Buy', 'Trade Value'].sum())
cash_str = dollar_format(pnl_table.iloc[-1]['Cash Balance'])
value_str = dollar_format(pnl_table.iloc[-1]['Balance Value'])
rpnl_str = dollar_format(pnl_table.iloc[-1]['RPNL'])
upnl_str = dollar_format(pnl_table.iloc[-1]['UPNL'])
total_value = dollar_format(pnl_table.iloc[-1]['Cash Balance'] + pnl_table.iloc[-1]['UPNL'])

# Plot our Trades and MAs along with the close data or candlesticks
fig = plot_funcs.plot_price_data(st.session_state['history'], st.session_state.get('display_candlestick', app_defaults['display_candlestick']))
display_fig = fig
display_fig.update_xaxes(range=[st.session_state['start_date'], st.session_state['history'].index[-1]])
display_fig = plot_funcs.plot_ma(figure=display_fig, ma_dict=buy_ma_lines, long_bool=True)
display_fig = plot_funcs.plot_ma(figure=display_fig, ma_dict=sell_ma_lines, long_bool=False)
display_fig = plot_funcs.plot_decisions(figure=display_fig,
                                        decisions=combined_decisions,
                                        price_point=combined_prices,
                                        markers=st.session_state.get('markers_bool', app_defaults['markers_bool']))

st.plotly_chart(display_fig, use_container_width=True, height=1500)

final_pos = dict(zip(pnl_table.columns, pnl_table.iloc[-1].values))

summary_cols = st.columns(2)
with summary_cols[0]:
    st.markdown(
        f"""
        ## Portfolio Summary 📒
        - **Remaining Shares:** {balance}
        - **Realized PnL:** {rpnl_str}
        - **Unrealized PnL:** {upnl_str}
        """
    )

with summary_cols[1]: 

    st.markdown(f"""
        ## **Total Portfolio Value:** {total_value}
        - **Total Cash Spent:** {spend_str}
        - **Share Value:** {value_str}
        - **Cash on Hand:** {cash_str}
    """)    

with st.expander('View Trade History'):
    trades_table = pnl_table.copy().drop(['Decision'], axis=1)
    trades_table.index = trades_table.index.strftime('%Y/%m/%d')
    share_columns = ['Share Diff', 'Share Balance']
    float_columns = list(set(trades_table.dtypes[trades_table.dtypes == float].index).difference(share_columns))
    st.table(trades_table.style.format(
        "{:.2f}", subset=share_columns).format(
        '{:,.2f}$', subset=float_columns).map(
        color_negative_red, subset=pd.IndexSlice[:, 'Share Diff']
    ))
