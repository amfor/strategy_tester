
# Helper for Styling Trades Table
def color_negative_red(val):
    color = '#e55039' if val < 0 else '#60a3bc'
    return 'background-color: %s' % color

dollar_format = lambda  amt: '**' + (':red[' if amt < 0 else ':green[') + '{:,.2f}\$]**'.format(amt)


