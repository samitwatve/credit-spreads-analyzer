import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
from yahoo_fin import stock_info as si
import matplotlib.pyplot as plt
import numpy as np


# Function to calculate days to expiration
def days_to_expiration(expiry_date):
    today = datetime.now().date()  # Use date() to get the date part only
    expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
    delta = (expiry - today).days
    return delta if delta > 0 else 1  # Return at least 1 to avoid division by zero


# Function to calculate the annualized return
def calculate_annualized_return(credit, max_loss, days):
    if max_loss > 0 and days > 0:  # Ensure neither max_loss nor days is zero
        return (credit / max_loss) / days * 365 * 100
    else:
        return 0


# Function to filter options and find put credit spreads
# Function to filter options and find put credit spreads
def find_put_credit_spreads(ticker, options, stock_price, min_days, max_days, min_return, min_volume):
    # Filter options based on days to expiration and volume
    options = options[(options['daysToExpiration'] >= min_days) &
                      (options['daysToExpiration'] <= max_days) &
                      (options['volume'] >= min_volume)]

    # Find put credit spreads
    spreads = []
    for _, sell_put in options[options['type'] == 'Put'].iterrows():
        # Find puts with a lower strike price to buy
        buy_puts = options[(options['type'] == 'Put') &
                           (options['strike'] < sell_put['strike']) &
                           (options['expiryDate'] == sell_put['expiryDate'])]
        for _, buy_put in buy_puts.iterrows():
            credit = sell_put['lastPrice'] - buy_put['lastPrice']
            max_loss = (sell_put['strike'] - buy_put['strike']) * 100 - credit
            annualized_return = calculate_annualized_return(credit, max_loss, sell_put['daysToExpiration'])

            if annualized_return >= min_return:
                spread = {
                    'ticker': ticker,
                    'sell_strike': sell_put['strike'],
                    'buy_strike': buy_put['strike'],
                    'credit': credit,
                    'max_loss': max_loss,
                    'annualized_return': annualized_return,
                    'days_to_expiration': sell_put['daysToExpiration'],
                    'expiry_date': sell_put['expiryDate'],  # Add the actual expiry date
                    'stock_price': stock_price  # Add the current stock price
                }
                spreads.append(spread)

    return pd.DataFrame(spreads)

# Main function to fetch and filter the options data
# Main function to fetch and filter the options data
def fetch_data(tickers, min_days, max_days, min_return, min_volume):
    all_spreads = []

    for ticker in tickers:
        stock = yf.Ticker(ticker)
        stock_price = stock.history(period="1d")['Close'].iloc[-1]  # Get the last closing price
        options_dates = stock.options

        for date in options_dates:
            days = days_to_expiration(date)
            if min_days <= days <= max_days:
                opt = stock.option_chain(date)
                puts = opt.puts.assign(expiryDate=date, type='Put')
                calls = opt.calls.assign(expiryDate=date, type='Call')
                options = pd.concat([puts, calls])
                options['daysToExpiration'] = days

                # Find put credit spreads
                put_spreads = find_put_credit_spreads(ticker, options, stock_price, min_days, max_days, min_return, min_volume)
                all_spreads.append(put_spreads)

    # Concatenate all spreads into a single DataFrame
    all_spreads_df = pd.concat(all_spreads, ignore_index=True)
    # Sort by annualized return and take top 5
    top_spreads = all_spreads_df.sort_values(by='annualized_return', ascending=False).head(10)
    
    # Drop the unwanted columns
    top_spreads = top_spreads.drop(columns=['sell_put_symbol', 'buy_put_symbol'], errors='ignore')
    
    return top_spreads




# Streamlit UI components
st.title('Options Search Tool')

# Ticker input
tickers = st.multiselect('Select ticker(s)', si.tickers_nasdaq() + si.tickers_sp500() + si.tickers_dow() + si.tickers_other(), help='Select up to 5 tickers.',  max_selections=5)

# Days to expiration slider
min_days, max_days = st.slider('Select Days to Expiration Range', 0, 365, (7, 45))

# Minimum Annualized Return slider
min_return = st.slider('Select Minimum Annualized Return (%)', 0.0, 100.0, 10.0)

# Minimum option volume slider
min_volume = st.slider('Select Minimum Option Volume', 0, 100, 10)

# Search button
if st.button('Search'):
    if tickers:
        # Fetch and display the data
        results = fetch_data(tickers, min_days, max_days, min_return, min_volume)
        st.session_state.results = results
        
        # Display the results in the app
        #st.dataframe(results)
    else:
        st.error('Please select at least one ticker.')

# Run this with `streamlit run your_app.py` in your command line
# Assuming 'results' is your DataFrame

if 'results' not in st.session_state:
    st.session_state.results = pd.DataFrame() 

if not st.session_state.results.empty:
# Display DataFrame with a button on each row to select it
    for i, row in  st.session_state.results.iterrows():
        cols = st.columns([0.9, 0.1])
        cols[0].write(row.to_frame().T)  # The to_frame().T converts the Series to a transposed DataFrame
        if cols[1].button('Plot', key=i):
            st.session_state.selected_row = row

    # If a row is selected, plot the data for that row
    if 'selected_row' in st.session_state:
        selected_data = st.session_state.selected_row
        row = st.session_state.selected_row
        stock_price_range = np.linspace(row['stock_price'] * 0.9, row['stock_price'] * 1.1, 100)
        credit = row['credit']
        max_loss = row['max_loss']
        breakeven = row['sell_strike'] - (credit / 100)

        # Calculate profit/loss
        profit_loss = np.where(stock_price_range <= breakeven, (stock_price_range - breakeven) * 100 + credit, credit)

        # Generate plot
        plt.figure()
        plt.plot(stock_price_range, profit_loss, label='Profit/Loss')
        plt.axhline(0, color='grey', lw=1, ls='--')
        plt.axvline(breakeven, color='green', label='Breakeven')
        plt.fill_between(stock_price_range, profit_loss, where=(profit_loss >= 0), color='blue', alpha=0.3, label='Profit')
        plt.fill_between(stock_price_range, profit_loss, where=(profit_loss <= 0), color='red', alpha=0.3, label='Loss')
        plt.xlabel('Stock Price')
        plt.ylabel('Profit / Loss')
        plt.title(f'Bull Put Spread Visualization for {row["ticker"]}')
        plt.legend()

        # Display plot
        st.pyplot(plt)
    else:
        st.write("Select a row to display the plot.")

else:
    st.write("Resuts dataframe not found")
