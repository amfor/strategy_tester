import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st
import datetime
from data.config import app_defaults

# Initial App Setup
st.set_page_config(page_title='Strategy Tester', layout='wide', page_icon="📈")
st.session_state['config'] = app_defaults

# Import other packages within strat_test
from data.fetch_data import load_ticker
selected_ticker = st.sidebar.text_input('Input Your Ticker', 'VOO').upper()
st.session_state['history'], st.session_state['info'] = load_ticker(selected_ticker) 
st.session_state['history'].name = selected_ticker
min_date, max_date = (st.session_state['history'].index[0].date(), st.session_state['history'].index[-1].date())
historical_span = (max_date - min_date).days
default_lookback = datetime.date(2021,1, 6) if historical_span > int(15 * 12 * 365.25) else min_date + datetime.timedelta(days=int((max_date - min_date).days / 2))

st.session_state['start_date'] = st.sidebar.slider('Select Trading Start Date',
                               min_value=min_date,
                               max_value=max_date,
                               value=default_lookback,
                               step=datetime.timedelta(days=188))
Pages = [
    st.Page("sections/strategic_trading.py", title='Rule Based Trading', icon="😨"),
    st.Page("sections/dca.py", title='Dollar Cost Averaging', icon="🐢"),
]
page = st.navigation({"Strategies": Pages})
st.sidebar.title(page.title)
# More Sidebar Interactibles
st.session_state['config']['display_candlestick'] = st.sidebar.checkbox('Use Candlestick Chart', value= historical_span <= int(25 * 12 * 365.25))
st.session_state['config']['allow_fractional'] = st.sidebar.checkbox('Allow Fractional Shares')

if page.title == "Rule Based Trading":
    st.session_state['config']['sell_all'] = st.sidebar.checkbox('Sell All Shares on Sell Decision')
    st.session_state['config']['markers_bool'] = st.sidebar.checkbox('Use Markers for Decisions')


page.run()

if st.session_state['history'] is None and st.session_state['info'] is None:
    st.warning('The Selected Ticker is Invalid. Please select a ticker supported by Yahoo Finance.')
    st.stop()
st.session_state['history'].name = selected_ticker


st.sidebar.title("About")
st.sidebar.info(
    """
    This app serves to backtest certain trading strategies on the chosen asset
    #### TL;DR 
    DCA = best risk adjusted return (esp. long-term)

    [**GitHub**](https://github.com/amfor/strat_test)
    """
)