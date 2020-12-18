import pandas as pd
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

pages = ['Technical Trading', 'Dollar Cost Averaging']

# Initial App Setup
st.set_page_config('Strategy Tester', layout='wide')
selected_page = st.radio("Buying Strategies", pages)
st.sidebar.title('Strategy Tester')
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'MSFT')
st.sidebar.subheader(selected_page)

history, info = load_ticker(selected_ticker) # Load in Data


if selected_page == pages[0]:

    buy_col, sell_col = st.beta_columns(2)

    with buy_col:
        buy_strategy = st.selectbox('Select Buying Strategy', list(trade_logic.buy_strategies.keys()))
        buy_strategy_span = st.number_input('Buy MA Span', value=25)

    with sell_col:
        sell_strategy = st.selectbox('Select Selling Strategy', list(trade_logic.sell_strategies.keys()))
        sell_strategy_span = st.number_input('Sell MA Span', value=25)

    fig = plot_funcs.plot_candlestick(history)

    fig = plot_funcs.plot_buys(figure=fig,
                               plot_data=history,
                               strategy=buy_strategy,
                               ma_span=buy_strategy_span,
                               scaling=0.95)

    fig = plot_funcs.plot_sells(figure=fig,
                               plot_data=history,
                               strategy=sell_strategy,
                               ma_span=sell_strategy_span,
                               scaling=1.05)

    st.plotly_chart(fig, use_container_width=True, height=900)

if selected_page == pages[1]:

    weekdays = {'Monday': 0,
                'Tuesday': 1,
                'Wednesday': 2,
                'Thursday': 3,
                'Friday': 4}

    time_strategy = ['Open', 'Close']

    weekday_col, strategy_col, interval_col = st.beta_columns(3)

    with weekday_col:
        selected_weekday = st.selectbox('Purchase Day', list(weekdays.keys()))
    with strategy_col:
        selected_strategy = st.selectbox('Purchase Time', time_strategy)
    with interval_col:
        selected_interval = st.selectbox('Purchase Day', list(trade_logic.interval_strategy.keys()))

