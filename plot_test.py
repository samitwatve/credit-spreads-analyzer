import matplotlib
import matplotlib.pyplot as plt
import numpy as np

# Example data
stock_prices = np.linspace(250, 350, 100)  # Range of stock prices
credit = 2  # Net credit received
max_loss = -3  # Max loss
breakeven = 280  # Breakeven stock price

# Calculate profit/loss
profit_loss = np.where(stock_prices <= breakeven, (stock_prices - breakeven) + credit, credit)

# Plot
plt.plot(stock_prices, profit_loss, label='Profit/Loss')
plt.axhline(0, color='grey', lw=1, ls='--')
plt.axvline(breakeven, color='green', label='Breakeven')
plt.fill_between(stock_prices, profit_loss, where=(profit_loss >= 0), color='blue', alpha=0.3, label='Profit')
plt.fill_between(stock_prices, profit_loss, where=(profit_loss <= 0), color='red', alpha=0.3, label='Loss')
plt.xlabel('Stock Price')
plt.ylabel('Profit / Loss')
plt.title('Bull Put Spread Visualization')
plt.legend()
plt.savefig('plot.png')
plt.show()
