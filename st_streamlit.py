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
selected_page = st.sidebar.radio("Buying Strategies", pages)
st.sidebar.title('Strategy Tester')
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'MSFT')
st.subheader(selected_page)

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

    st.plotly_chart(fig, use_container_width=True, height=1500)

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