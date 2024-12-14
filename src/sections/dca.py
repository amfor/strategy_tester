import streamlit as st 
from logic import trade_logic, plot_funcs
from logic.styling import dollar_format
import pandas as pd 
import numpy as np

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

divisible = True if 'crypto' in st.session_state['info'].get('quoteType').lower() else st.session_state.get('allow_fractional', True)

dca_data = st.session_state['history'].loc[st.session_state['history'].index.tz_localize(None) >= pd.to_datetime(st.session_state['start_date'])]
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


st.plotly_chart(plot_funcs.dca_plot(dca_df, purchase_dates), use_container_width=True, height=2000)

summary_cols = st.columns(2)
with summary_cols[0]:
    st.markdown(
        f"""
        ## Portfolio Summary 📒
        - **Shares Accumulated:** {share_count}
        - **Unrealized PnL:** {pnl_amount}
        """
    )

with summary_cols[1]: 

    st.markdown(f"""
        ## **Total Portfolio Value:** {value_amount}
    """)    


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

