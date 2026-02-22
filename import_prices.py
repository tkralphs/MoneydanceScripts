import pandas as pd
from datetime import date
from re import sub
from decimal import Decimal

header = '''
global moneydance  # Entry point into the Moneydance API
mdGUI = moneydance.getUI()  # Entry point into the GUI
book = moneydance.getCurrentAccountBook()  # Entry point into your dataset
root = moneydance.getCurrentAccount()

currencies = book.getCurrencies()

def setPriceForSecurity(symbol, price, dateint):
    price = 1.0 / price
    security = currencies.getCurrencyByTickerSymbol(symbol)
    if not security:
        print("No security with symbol/name: %s" %(symbol))
        return
    if dateint:
        security.setSnapshotInt(dateint, price).syncItem()
    security.setUserRate(price)
    security.syncItem()
    print("Successfully set price for %s" % (security))
'''

# Load your CSV
df = pd.read_csv('Portfolio_Positions_Feb-13-2026.csv', index_col=False) 

today = '20' + date.today().strftime("%y%m%d")

with open('set_prices.py', 'w') as f:
    print(header, file=f)
    
    # Iterate through rows of the DataFrame
    for idx, row in df.iterrows():
        symbol = row['Symbol']
        price = row['Last Price']
        
        print(symbol)
        
        # Skip invalid entries
        if pd.isna(symbol) or 'FCASH' in str(symbol):
            continue
            
        # Skip pending entries
        if 'Pending' in str(symbol):
            continue
        
        # Convert price to Decimal
        if pd.notna(price):
            money = str(price)
            cleaned = sub(r'[^\d.]', '', money)
            
            # Skip if no valid numeric data remains
            if not cleaned or cleaned == '.':
                print(f"  Warning: Could not parse price '{money}' for {symbol}")
                continue
            
            try:
                value = Decimal(cleaned)
                print(f"setPriceForSecurity('{symbol}',{value},{today})", file=f)
            except InvalidOperation:
                print(f"  Warning: Invalid decimal '{cleaned}' for {symbol}")
                continue