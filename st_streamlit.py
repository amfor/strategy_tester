import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st

# Import other packages within strat_test
import plot_funcs
import trade_logic

@st.cache
def load_ticker(ticker):
    ticker_obj = yf.Ticker(ticker)
    history = ticker_obj.history(period='max')
    details = ticker_obj.info
    return history, details

@st.cache(hash_funcs={dict: lambda _: None}) # hash_funcs because dict can't be hashed
def base_plot(history):
    return plot_funcs.plot_candlestick(history)

@st.cache
def get_trades(strategy, asset_data, long_bool, gap=0, spans=(None), scaling=1):
    return trade_logic.get_trades(strategy=strategy, long_bool=long_bool, asset_data=asset_data, gap=gap,
                                    spans=spans, scaling=scaling)

pages = ['Technical Trading', 'Dollar Cost Averaging']

# Initial App Setup
st.set_page_config('Strategy Tester', layout='wide')
selected_page = st.sidebar.radio("Buying Strategies", pages)
st.sidebar.title('Strategy Tester')
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'MSFT')
st.subheader(selected_page)

history, info = load_ticker(selected_ticker)  # Load in Data

if selected_page == pages[0]:

    buy_params_one, buy_params_two, sell_params_one, sell_params_two = st.beta_columns(4)

    available_strategies = list(trade_logic.strategies.keys())
    available_buy_strategies = available_strategies.copy()
    available_buy_strategies.remove('Hold/None')

    with buy_params_one:
        buy_strategy = st.selectbox('Select Buying Strategy', available_buy_strategies)
        buy_scaling = st.number_input('Select MA Scaling (<=1.00)', value=0.95, step=0.025) \
            if pd.Series([_ not in buy_strategy for _ in ['Crossover', 'Countdown']]).all() else None

    with buy_params_two:
        buy_ma_span_one = st.number_input('1st Buy MA Span (Short Term)', value=50, step=5) \
            if 'Crossover' in buy_strategy else st.number_input('Buy MA Span', value=25, step=5)
        buy_ma_span_two = st.number_input('2nd Buy MA Span (Long Term)', value=150, step=10) \
            if 'Crossover' in buy_strategy else None
        
    with sell_params_one:
        initial_strategy = available_strategies.index('TD Countdown')
        sell_strategy = st.selectbox('Select Selling Strategy', available_strategies, index=initial_strategy)
        sell_scaling = st.number_input('Select MA Scaling (>=1.00)', value=1.05, step=0.025) \
            if pd.Series([_ not in sell_strategy for _ in ['Crossover', 'Hold', 'Countdown']]).all() else None

    with sell_params_two:
        if 'Crossover' in sell_strategy:
            sell_ma_span_one = st.number_input('1st Sell MA Span (Short Term)', value=50, step=5)
        elif 'Hold' not in sell_strategy:
            sell_ma_span_one = st.number_input('Sell MA Span', value=25, step=5)
        else:
            sell_ma_span_one = None
        sell_ma_span_two = st.number_input('2nd Sell MA Span (Long Term)', value=150, step=10) \
            if 'Crossover' in sell_strategy else None

    buy_ma_spans = [buy_ma_span_one, buy_ma_span_two]
    final_buy_spans = buy_ma_spans if pd.notnull(buy_ma_spans).all() else [buy_ma_span_one]

    sell_ma_spans = [sell_ma_span_one, sell_ma_span_two]
    final_sell_spans = sell_ma_spans if pd.notnull(sell_ma_spans).all() else [sell_ma_span_one]

    trade_size = st.sidebar.number_input('Enter Trade Value', value=250, step=50)
    gap_days = st.sidebar.number_input('Select Minimum Day Gap Between Buys', value=7, step=1)

    # TODO: Add PNL calculation to different strategies
    # Buy Decisions
    buy_decision, buy_point, buy_ma_lines = get_trades(strategy=buy_strategy,
                                                   long_bool=True,
                                                   asset_data=history,
                                                   gap=gap_days,
                                                   spans=final_buy_spans,
                                                   scaling=buy_scaling)
    buy_series = (buy_point * buy_decision).replace(0, np.nan).dropna()

    fig = base_plot(history)
    display_fig = plot_funcs.plot_ma(figure=fig, ma_dict=buy_ma_lines)
    display_fig = plot_funcs.plot_decisions(figure=display_fig, decision=buy_decision, price_point=buy_point, long_bool=True)


    if 'Hold' not in sell_strategy:
        # Sell Decisions
        sell_decision, sell_point, sell_ma_lines = get_trades(strategy=sell_strategy,
                                                                 long_bool=False,
                                                                 asset_data=history,
                                                                 gap=0,
                                                                 spans=final_sell_spans,
                                                                 scaling=sell_scaling)
        sell_series = (sell_point * sell_decision).replace(0, np.nan).dropna()

        display_fig = plot_funcs.plot_ma(figure=display_fig, ma_dict=sell_ma_lines)
        display_fig = plot_funcs.plot_decisions(figure=display_fig, decision=sell_decision, price_point=sell_point, long_bool=False)

    st.plotly_chart(display_fig, use_container_width=True, height=1500)

# Dollar Cost Averaging
if selected_page == pages[1]:

    weekdays = {'Monday': 0,
                'Tuesday': 1,
                'Wednesday': 2,
                'Thursday': 3,
                'Friday': 4}

    time_strategy = ['Open', 'Close']

    weekday_col, strategy_col, interval_col, purchase_col, divisible_col = st.beta_columns(5)

    with weekday_col:
        selected_weekday = st.selectbox('Purchase Day', list(weekdays.keys()))
        day_number = weekdays.get(selected_weekday)
    with strategy_col:
        selected_strategy = st.selectbox('Purchase Time', time_strategy)
    with interval_col:
        selected_interval = st.selectbox('Purchase Day', list(trade_logic.interval_strategy.keys()))
        interval_number = trade_logic.interval_strategy.get(selected_interval)
    with purchase_col:
        selected_spend = st.number_input('Recurring Purchase Amount', 200)
    with divisible_col:
        divisible = 0 if 'crypto' in info.get('quoteType').lower() else 1
        selected_fractional = st.selectbox('Allow Fractional Shares', [True, False], index=divisible)

    start_date = st.slider('Select Trading Start Date',
                           min_value=history.index[0].date(),
                           max_value=history.index[-1].date())

    dca_data = history.loc[history.index >= pd.to_datetime(start_date)]
    dca_df, purchase_dates = trade_logic.dca_buy_report(asset_data=dca_data,
                                        weekday=day_number,
                                        strategy=selected_strategy,
                                        interval=interval_number,
                                        usd_buy_amount=selected_spend,
                                        allow_fractional=selected_fractional)

    pnl_amount = '{:,.2f}'.format(dca_df['Unrealized PNL'][-1])
    final_balance = dca_df['Balance'][-1]
    shares_owned = int(final_balance) if float(final_balance).is_integer() else final_balance
    share_count = '{:,.2f}'.format(dca_df['Balance'][-1])
    value_amount = '{:,.2f}'.format(dca_df['Value'][-1])

    st.markdown(f"The selected trading strategy would've yielded **{share_count} shares**, valued at **{value_amount}$**.")
    st.markdown(f"This is equivalent to **{pnl_amount}$ in unrealized profits** assuming a buy & hold strategy.")

    st.plotly_chart(plot_funcs.dca_plot(dca_df, purchase_dates), use_container_width=True, height=2000)