# Scripts for Importing (Fidelity) CSV Data to Moneydance

This repository contains Python scripts for importing transaction and price data from a brokerage account.
The scripts are made specifically to work with Fidelity accounts, but it should be easy to extend to 
other brokerages. Each script reads a CSV file and produces a Jython script, which can then be run 
in the Developer Console of Moneydance to do the actual import. There is also an HTML file that assists 
in manually looking up relevant data about securities and also creates a Jython script for creating
missing securities. 

The version of Moneydance these scripts were developed for is 2024.4 but they should mostly work with other versions.

## Importing Prices

The script called `import_prices.py` can import price data, as follows.
- Log into your Fidelity account and go to the "Positions" tab.
- Choose "Download" from the menu in the upper right (look for the three dots, see pic below)
<img width="1168" height="150" alt="Screenshot 2026-02-22 163058" src="https://github.com/user-attachments/assets/d279f906-7f7f-483a-90a3-0c3201cf8c01" />

- You should now have a CSV file called something like `Portfolio_Positions_MMM-DD-YYYY.csv`
- Run `python import_prices.py Portfolio_Positions_MMM-DD-YYYY.csv`
- The output will be a file called `set_prices.py` consisting of commands for setting security prices in the Moneydance API.
- Launch Moneydance and open a Developer Console Window (Window => Show Developer Console).
- Click the "Open Script" button and load the `set_prices.py` script.
- Click "Run"

The script does not check to see whether the securities exist, but if you first import the transaction data using the 
`csv_to_moneydance.py` script, as described next, this will already be checked there. 

## Importing Transactions

This process is significatly more involved and there are many gotchas. Note that there are two (very) different approaches to importing transaction data.
One is to parse a CSV containing transaction data and produce an OFX file (essentially an XML file containing the transaction data), which can then be read
by Moneydance. The (only lightly tested) Python script called `csv_to_ofx.py` implements this approach. It would probably need a lot of work
to be bullet-proof because I decided to switch to the second approach, which is to generate a Jython script to add transactions directly using
the Moneydance API. Producing an OFX file replicates the process that occurs when downloading transaction data directly from Fidelity and this approach has
advantages, mainly that the import is orders of magnitude faster. However, it also introduces another layer of translation and I found it easier to fine-tune 
the whole process by adding the trasactions directly through the API. This means you can use Moneydance-native transaction types and also directly handle
tricky things like the number of decimal places a security uses (which can vary and is a big gotcha). 

### Basic Workflow

The basic workflow is as follows.
- Log into your Fidelity account and go to the "Activity & Orders" tab.
- Select one of your accounts in the left pane.
- Click on the "Download" icon in the upper right (see pic below)
<img width="1154" height="132" alt="Screenshot 2026-02-22 164712" src="https://github.com/user-attachments/assets/b1d45c92-56e3-47d4-9013-df5287404775" />

- You should now have a CSV file called something like `History_for_Account_123456789.csv`
- Run `python csv_to_moneydance.py History_for_Account_123456789.csv import_txns.py 'Account Name'`, where `import_txns.py` is the name that will
  be given to output script and 'Account Name' is the name of the account that transactions should be added to in Moneydance.
- The output will be a file with the name specified, consisting of two sets of commands, one for validting the securities and the other for adding
  the transactions.
- Launch Moneydance and open a Developer Console Window (Window => Show Developer Console).
- Click the "Open Script" button and load the script.
- Click "Run"
- If all securities exist in Moneydance already (more on this below), then the transactions should be added.
- If there are missing (or duplicate) securities, then these issues need to be rectified first before running the script again.

What follows next is more detailed information and some hard-won lessons learned for those who want to know more about
various aspects of this. 

### More detailed background information (Moneydance)

The Moneydance API is not very well documented and although there is a good deal with helpful information in the forums, it still
took a lot of trial and error to put together these scripts. Some thing that are useful to keep in mind.

#### Identifying securities in Moneydance

  - Securities have both a ticker symbol and a "unique identifier" associated with them. In Moneydance, the unique identfies is called the
    "Security ID." In the U.S., the security ID is what is called the CUSIP and is an SEC-registered, unique identification code for all traded securties.
    Ticker symbols are not always reliable for identifying specific securities. In other countries, the system is different.
  - It can (and does) happen that the CUSIP associated with a security changes, but it's ticker symbol remains the same (due to a merger for example) or also that
    the ticker symbol changes, while the CUSIP remains the same (companies are allowed to change their ticker synbols if they want). This
    creates a lot of pain in tracking transactions accurately and it helps to be aware of it.
  - It is not too difficult to identify the CUSIP of a given security or to find out the ticker symbol of the security for which you only have the CUSIP, but
    on the other hand, there seems to be no 100 percent reliable method either. You have to use a search engine query and hope for the best. 

#### Where Security Data is Stored in Moneydance.

  - There is a global list of securities in Moneydance across all accounts, which you can look at by going to Tools => Securities in
    the Moneydance menu.
  - In addition, there is a "subaccount" inside your brokerage account that is associated with each security you've traded in that specific
    account. It is this subaccount that contains the balance for that security in that account. In other words, you may have shares of stock XYZ
    in two different account, such as in a regular brokerage and in an IRA, these would be two subaccounts, both linked to the same security.
  - The security must exist in the global list and have an already-existing subaccount before a transaction involving that security can be added
    to a given account.

#### Adding new securities

  - Securities can be added to the global list via the Moneydance API. It seems to be more difficult to add subaccounts associated with securities and that
    has been left as a manual process in the workflow.
  - After running `csv_to_moneydance.py`, there may be securities
    1. that are missing in Moneydance altogether,
    2. that have no subaccount, or
    3. that appear to be duplicated.
  - For securities that are missing in Moneydance altogether, there is an HTML file called `cusip_lookup.html` that can assist with creating those securities.
    For most securities, what is needed is to look up the CUSIP, which is not listed in the CSV. In some cases, the CUSIP is listed (see discussion later) but
    not the ticker symbol. The helper HTML file is to get a complete list of all tickers and associated CUSIPs, then create a script for setting these in
    Moneydance for each security. To use the helper HTML file, open it in a browser. Then
    1. Cut and paste the list of securities that were indicated as missing in the output of the import script into the window
       <img width="1077" height="478" alt="Screenshot 2026-02-22 193419" src="https://github.com/user-attachments/assets/5a4b372d-0a0f-4ac7-9e9e-7d8ee4c01085" />
       and click on the "Prepare Lookup Table" button. Then you should have a table like this.
       <img width="1066" height="200" alt="Screenshot 2026-02-22 193952" src="https://github.com/user-attachments/assets/21f31715-c717-40be-939b-78e115a7e052" />
       Note that for some securities, what is listed as the "symbol" could actually be a CUSIP rather than a ticker symbol. The javascript embedded in the HTML
       file will detect whether what is listed is a ticker or a CUSIP.
    1. The resulting table will have blanks for the information about each security that is missing and needs to be looked up, along with a clickable
       URL to look that information up manually. After clicking on the "Search" link, fill out the missing information in the table for each security.
    1. Once the table is full, click on the Download Moneydance Script button to download a file called `moneydance_update_cusip.py`. Run this script in the Developer
       Console in Moneydance and it will create the securities on Moneydance.
    1. These still need to be added to each account in which they will be help as a separate manual step.

    Note that it is not strictly necessary to use the CUSIP as the unique identifier. Anything will work, as long as you are not concerned with detecting changes in
    ticker symbol or tracing multiple different securities with the saem ticker symbol.
  - For securities that are in Moneydance but haven't been traded in this account yet (are missing a subsccount), they can be added by going to the account
    in Moneydance and choosing the "Add Security" option in the "Actions" menu on the top right.
  - Finally, for securities where there is a potential duplicate (more than one security with the same ticker symbol), this requires manually sorting out what's going on. 

#### Validating securities

To validate securities, we need to first check whether they exist in the global securities list, then verify whether there is an associated subaccount.
The following helper functions do the work and are pretty self-explanatory, but with some important explanations in the function descriptions. 
```python
from com.infinitekind.moneydance.model import CurrencyType

# Get the root account and book
root = moneydance.getCurrentAccountBook()

def findAccount(name)
    """Function to find account by name"""
    account = None
    for acct in root.getRootAccount().getSubAccounts():
        if acct.getAccountName() == "Fidelity IRA":
            return(acct)
        for subacct in acct.getSubAccounts():
            if subacct.getAccountName() == "Fidelity IRA":
                return(subacct)

def findSecurity(ticker):
    """
    Function to find security with either a matching ticker symbol or a mathching CUSIP.
    Returns a list of all securities with a matching ticker symbol if there are any matches.
    If no matches are found, then the function interprets the argument as a CUSIP instead. 
    """
    currList = []
    for curr in root.getCurrencies().getAllCurrencies():
        if curr.getCurrencyType() == CurrencyType.Type.SECURITY:
            if curr.getTickerSymbol() == ticker:
                currList.append(curr)
    if len(currList) > 0:
        return(currList)
    for curr in root.getCurrencies().getAllCurrencies():
        if curr.getCurrencyType() == CurrencyType.Type.SECURITY:
            secID = curr.getIDForScheme("CUSIP")
            if secID is not None and ticker in secID:
                currList.append(curr)
    return currList

def findSecurityAcct(account, ticker):
    """
    Function to find subaccount associated with a security
    Returns a list of all subaccounts with a matching ticker symbol.
    If there are matches, then only aubaccounts with a non-zero balance are returned.
    This is because if a new security with the same ticker is created due to a change in CUSIP,
    we only want the new security. This can happen with mergers, for example.  
    """
    acctList = []
    if ticker == "CASH" or ticker == "315994103":
        return ["CASH"]
    l = findSecurity(ticker)
    for sec in l:
       name = sec.getName()
       for a in account.getSubAccounts():
           if a.getAccountName() == name:
               acctList.append(a)
    if (len(acctList) > 1):
        for a in acctList:
            if a.getBalance() == 0:
                acctList.remove(a)
    return acctList
```

#### Adding transactions

The easiest way to add transactions to an invest account seems to be the following recipe. 
```python
    from com.infinitekind.moneydance.model import AccountUtil, ParentTxn, InvestFields, InvestTxnType

    # Get the root account and book 
    root = moneydance.getCurrentAccountBook()

    # Find the investment account: Fidelity IRA
    account = findAccount("Account Name")

    txn = ParentTxn(root)
    txn.setAccount(account)
    txn.setDateInt(20260130)
    # We should have already checked that findSecurityAcct returns a list of length 1 
    security = findSecurityAcct("XYZ")[0]
    # The name of the security subaccount is in the form "Account Name:Security Name"
    txn.setDescription("DIVIDEND " + str(security).split(':')[1])
    txn.setMemo("DIVIDEND RECEIVED XYZ COMPANY (XYZ) (Cash)")
    fields = InvestFields()
    fields.setFieldStatus(InvestTxnType.DIVIDEND, txn)
    fields.security = security
    fields.amount = 489
    fields.shares = 0
    fields.price = 1
    fields.category = AccountUtil.getDefaultCategoryForAcct(account)
    fields.storeFields(txn)
    txn.syncItem()
```
This recipe uses an `InvestFields` object to load the data. The interface is a bit strange, but
this recipe should work. A few notes.
- `fields.security` is set to the associated subaccount, not the security itself. 
- Obviously, the transaction type is different for different types of transactions so the argument to 
`setFieldStatus` needs to be set appropriately to one of
  - `InvestTxnType.SELL`
  - `InvestTxnType.BUY`
  - `InvestTxnType.DIVIDEND`
  - `InvestTxnType.DIVIDEND_REINVEST`
  - `InvestTxnType.MISCEXP`
  - `InvestTxnType.MISCINC`

  (there are others, but these are the ones used in these scripts). 
- It is important to note that each of `amount`, `shares`, and `price` need to be set, regardless of the
transaction type. If the transaction is a cash transaction, then `price` is 1 and `shares` is zero.
In general, the following should be the case.
  - For `BUY` transactions, `shares` should be positive (typically, `price` and `amount` should be also, but not always) 
  - For `SELL` transactions, `shares` should be negative (typically, `price` and `amount` should be positive, but not always)
  - For `DIVIDEND` and `MISCINC` transactions, `shares` should be zero, `price` should be 1, and `amount` should be positive.
  - For `MISCEXP`, `shares` should be zero, `price` should be 1, and `amount` should be positive

#### Some other gotchas

Two other things I ran into were as follows.
- There is a limitation on the size of a single function in Jython (inherited from the similar limitation in Java). This necessitates
  batching the addition of transactions into many smaller functions when there are a lot of transactions. The actual code is quite
  verbose, since it cannot read in data directly from the CSV when running.
- All numbers are passed to be Moneydance as integers, so $12.30 is passed as 1230 and Moneydance converts it when displaying
  and doing computations. For this conversion, Moneydance uses an internally maintained precision that is specific to the subaccount
  associated with each security. This is set when the security is created and all transaction data has to be scaled appropriately.
  This is the purpose of the helper function `getShareScale()`.
  ```python
  def getShareScale(ticker):
    try: return 10 ** findSecurity(ticker)[0].getDecimalPlaces()
    except: return 10000
  ```
  
### More detailed background information (Fidelity)

Fidelity has a lot of weird stuff in its transaction data and writing a bullet-proof script to automatically interpret it all is
not that easy. After a LOT of debugging, the script here have been working well, even with a fairly high volume of trades on
individual stocks (which produce the most weirdness). Some things that you might notice when looking at the transaction data in the
downloaded CSV.

- The transaction type is embedded in the `DESCRIPTION` column in the CSV, though you cannot always tell exactly what kind of transaction it is from this
  field alone.
- In general, it is best to deduce what the transaction must be by looking at how the cash balance changes as a result of the transactions, along with
  whether any shares were transacted.  
- Sometimes, what is lited in the "Symbol" columns is a CUSIP instead of a ticker symbol. This seems pretty random at first, but it's usually an indicator
  that there has been a change in CUSIP due to a merger or something like that and this is their very obscure way of telling you this.
- Miscellaneous weird stuff in the `Description` column that you would not expect includes
  - There are transactions with the description `REINVESTMENT CASH` that are about investing the cah balance in FDRXX, which can essentially be ignored.
  - There are transactions that have `DISTRIBUTION` in the description that have a non-zero amount listed and so look as though they change the cash balance,
    but they are in fact distributions of additional shares.
  - Transactions with the string `MERGER MER PAYOUT` in the description can either have a positive share quantity, which is a change in shares with no cash
    transacted or have a negative share quantity, which means a decrease in shares and a cash payout.
  - Transactions with the string `IN LIEU OF FRX SHARE` in the description can have either a positive or a negative cash amount associated with them, although
    you would think it could be only the former.
  - Transactions with the string `TENEDERED TEX PAYOUT` usually don't have an actual cash payout (as you would expect) but instead are a change in shares.

