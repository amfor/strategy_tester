import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import datetime

# Import other packages within strat_test
import plot_funcs
import trade_logic

@st.cache_data
def load_ticker(ticker, timeframe='max'):
    ticker_obj = yf.Ticker(ticker)
    try:
        ticker_data = ticker_obj.history(period=timeframe)
        details = ticker_obj.fast_info
        return ticker_data, list(details)
    except:
        return None, None


@st.cache_data
def get_trades(strategy, asset_data, long_bool, gap=0, spans=(None), scaling=1, start=None):
    return trade_logic.get_trades(strategy=strategy, long_bool=long_bool, asset_data=asset_data, gap=gap,
                                  spans=spans, scaling=scaling, start=start)

# Helper for Styling Trades Table
def color_negative_red(val):
    color = '#e55039' if val < 0 else '#60a3bc'
    return 'background-color: %s' % color

dollar_format = lambda  amt: '**' + (':red[' if amt < 0 else ':green[') + '{:,.2f}\$]**'.format(amt)



# Initial App Setup
st.set_page_config(page_title='Strategy Tester', layout='wide', page_icon="📈")
st.sidebar.title('Strategy Tester')
pages = ['Technical Trading', 'Dollar Cost Averaging']
selected_page = st.sidebar.radio("Strategies", pages)
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'MSFT').upper()
st.subheader(selected_page)

history, info = load_ticker(selected_ticker)  # Load in Data
if history is None and info is None:
    st.warning('The Selected Ticker is Invalid. Please select a ticker supported by Yahoo Finance.')
    st.stop()
history.name = selected_ticker
start_date = st.sidebar.slider('Select Trading Start Date',
                               min_value=history.index[0].date(),
                               max_value=history.index[-1].date(),
                               step=datetime.timedelta(days=188))

# More Sidebar Interactibles
display_candlestick = st.sidebar.checkbox('Use Candlestick Chart', value=False)
allow_fractional = st.sidebar.checkbox('Allow Fractional Shares', value=True)
sell_all = st.sidebar.checkbox('Sell All Shares on Sell Decision', value=False)
markers_bool = st.sidebar.checkbox('Use Markers for Decisions', value=False)

st.sidebar.title("About")
st.sidebar.info(
    "This app serves to backtest certain trading strategies on the chosen asset.\n\n"
    "Maintained by **Amy Forest** on [GitHub](https://github.com/amfor/strat_test)"
)
st.sidebar.warning(
    "Note that all returns are hypothetical and not indicative of future performance."
)

if selected_page == pages[0]:

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

    buy_ma_spans = [buy_ma_span_one, buy_ma_span_two]
    final_buy_spans = buy_ma_spans if pd.notnull(buy_ma_spans).all() else [buy_ma_span_one]

    sell_ma_spans = [sell_ma_span_one, sell_ma_span_two]
    final_sell_spans = sell_ma_spans if pd.notnull(sell_ma_spans).all() else [sell_ma_span_one]

    # Buy Decisions
    buy_decision, buy_point, buy_ma_lines = get_trades(strategy=buy_strategy,
                                                        long_bool=True,
                                                        asset_data=history,
                                                        gap=gap_days,
                                                        spans=final_buy_spans,
                                                        scaling=buy_scaling)
    buy_series = (buy_point * buy_decision).replace(0, np.nan).dropna()[start_date:]

    # Sell Decisions
    sell_decision, sell_point, sell_ma_lines = get_trades(strategy=sell_strategy,
                                                            long_bool=False,
                                                            asset_data=history,
                                                            gap=0,
                                                            spans=final_sell_spans,
                                                            scaling=sell_scaling,
                                                            start=start_date)
    sell_series = (sell_point * sell_decision).replace(0, np.nan).dropna()


    pnl_table = trade_logic.pnl_calc(asset_data=history,
                                     buy_series=buy_series,
                                     sell_series=sell_series,
                                     trade_size=trade_size,
                                     allow_fractional=allow_fractional,
                                     sell_all=sell_all)


    # Get the proper data to plot (What we actually end up trading)
    plot_buy = (pnl_table['Decision'] == 'Buy').astype(int)
    plot_buy_price = pnl_table.loc[plot_buy.index, 'Price']
    plot_sell = -(pnl_table['Decision'] == 'Sell').astype(int)
    plot_sell_price = pnl_table.loc[plot_sell.index, 'Price']
    combined_decisions = pd.concat([plot_buy, plot_sell])
    combined_prices = pd.concat([plot_buy_price, plot_sell_price])

    # Save and write closing position data
    shares_owned = pnl_table.iloc[-1]['Share Balance']
    balance = np.round(shares_owned, 2) if allow_fractional else int(shares_owned)
    spend_str = dollar_format(pnl_table.loc[pnl_table['Decision'] == 'Buy', 'Trade Value'].sum())
    cash_str = dollar_format(pnl_table.iloc[-1]['Cash Balance'])
    value_str = dollar_format(pnl_table.iloc[-1]['Balance Value'])
    rpnl_str = dollar_format(pnl_table.iloc[-1]['RPNL'])
    upnl_str = dollar_format(pnl_table.iloc[-1]['UPNL'])
    total_value = dollar_format(pnl_table.iloc[-1]['Cash Balance'] + pnl_table.iloc[-1]['UPNL'])

    st.markdown(
        f"""
        At the end of the trading period, **{balance} shares** remain, valued at **{value_str}**, with **{cash_str}** of fiat on hand.  

        Cumulative cash spent is **{spend_str}**, representing **{rpnl_str}** of realized PnL, with **{upnl_str}** of unrealized PnL.  

        Total Fiat Value of portfolio: **{total_value}**  
        """
    )

    # Plot our Trades and MAs along with the close data or candlesticks
    fig = plot_funcs.plot_price_data(history, display_candlestick)
    display_fig = fig
    display_fig.update_xaxes(range=[start_date, history.index[-1]])
    display_fig = plot_funcs.plot_ma(figure=display_fig, ma_dict=buy_ma_lines, long_bool=True)
    display_fig = plot_funcs.plot_ma(figure=display_fig, ma_dict=sell_ma_lines, long_bool=False)
    display_fig = plot_funcs.plot_decisions(figure=display_fig,
                                            decisions=combined_decisions,
                                            price_point=combined_prices,
                                            markers=markers_bool)

    st.plotly_chart(display_fig, use_container_width=True, height=1500)

    final_pos = dict(zip(pnl_table.columns, pnl_table.iloc[-1].values))

    with st.expander('View Trade History'):
        trades_table = pnl_table.copy().drop(['Decision'], axis=1)
        trades_table.index = trades_table.index.strftime('%Y/%m/%d')
        share_columns = ['Share Diff', 'Share Balance']
        float_columns = list(set(trades_table.dtypes[trades_table.dtypes == float].index).difference(share_columns))
        st.table(trades_table.style.format(
            "{:.2f}", subset=share_columns).format(
            '{:,.2f}$', subset=float_columns).applymap(
            color_negative_red, subset=pd.IndexSlice[:, 'Share Diff']
        ))


# Dollar Cost Averaging
if selected_page == pages[1]:

    weekdays = {'Monday': 0,
                'Tuesday': 1,
                'Wednesday': 2,
                'Thursday': 3,
                'Friday': 4}

    time_strategy = ['Open', 'Close']

    weekday_col, strategy_col, interval_col, purchase_col = st.columns(4)

    with weekday_col:
        selected_weekday = st.selectbox('Purchase Day', list(weekdays.keys()))
        day_number = weekdays.get(selected_weekday)
    with strategy_col:
        selected_strategy = st.selectbox('Purchase Time', time_strategy)
    with interval_col:
        selected_interval = st.selectbox('Purchase Day', list(trade_logic.interval_strategy.keys()))
        interval_number = trade_logic.interval_strategy.get(selected_interval)
    with purchase_col:
        selected_spend = st.number_input('Recurring Purchase Amount', 250, step=50)

    divisible = True if 'crypto' in info.get('quoteType').lower() else allow_fractional

    dca_data = history.loc[history.index.tz_localize(None) >= pd.to_datetime(start_date)]
    dca_df, purchase_dates = trade_logic.dca_buy_report(asset_data=dca_data,
                                                        weekday=day_number,
                                                        strategy=selected_strategy,
                                                        interval=interval_number,
                                                        usd_buy_amount=selected_spend,
                                                        allow_fractional=divisible)

    pnl_amount = dollar_format(dca_df['Unrealized PNL'][-1])
    final_balance = dca_df['Share Balance'][-1]
    shares_owned = int(final_balance) if float(final_balance).is_integer() else final_balance
    share_count = dollar_format(final_balance)
    value_amount = dollar_format(dca_df['Value'][-1])

    st.markdown(
        f"The selected trading strategy would've yielded {share_count} shares, valued at {value_amount}.<br>  "
        f"This is equivalent to {pnl_amount} in unrealized profits assuming a buy & hold strategy.",
        unsafe_allow_html=True
    )

    st.plotly_chart(plot_funcs.dca_plot(dca_df, purchase_dates), use_container_width=True, height=2000)

    with st.expander('View Trade History'):
        trades_table = dca_df.loc[dca_df['Shares Bought'] > 0]
        trades_table.index = trades_table.index.strftime('%Y/%m/%d')
        pct_columns = ['ROE %']
        share_columns = ['Shares Bought', 'Share Balance']
        float_columns = ['Close', 'Cost Basis', 'Cumulative Spend', 'Unrealized PNL', 'Value']
        st.table(
            trades_table.style.format(
                "{:.2f}", subset=share_columns).format(
                "{:,.2f}$", subset=float_columns).format(
                "{:.2%}", subset=pct_columns)
        )
