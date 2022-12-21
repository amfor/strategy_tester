
# strategy_tester
**strategy_tester** is a trading strategy tester built on [streamlit](https://github.com/streamlit/streamlit) utilizing [yfinance](https://github.com/ranaroussi/yfinance/) for historical data import. 

[Hosted on fly.io](https://strategy-tester.fly.dev/)

## Technical Trading
The following trading strategies are supported on the buy/sell sides:

 1. Trade on SMA or EMA - with parameters Scaling / Span Parameters
 2. Trade on SMA or EMA Crossovers - with parameters Span 1 / Span 2 
 3. Trade on Tom DeMark Countdown (13)

Excess/unmatched sell decisions will be removed to generate a PNL table, along with a closing account statement. 
Decisions are visualized on a plot.ly graph along with vertical lines representing the Buy / Sell decisions (markers are also available). 

Other parameters include:

 - Trading Start Date
 - $ Trade Amount (1 share minimum using whole shares)
 - Fractional / Whole Shares
 - Gap Days between buys (Frequency limitation)

## Dollar Cost Averaging
**strategy_tester** also features a Dollar Cost Averaging page which facilitates the simulation of buying on a recurring schedule during with the following parameters:

 - Trading Start Date
 - Recurring purchase amount
 - Weekday
 - At open/close
 - On a weekly/bi-monthly/monthly basis

_Note that all returns are hypothetical and not indicative of future performance.
Furthermore, dividend calculations are not included and some stock prices may be inaccurate due to Yahoo Finance 
not properly accounting for stock splits due to updating delays._

