#!/usr/bin/env python
# Moneydance Python Script to Import Transactions from CSV
# This generates a Jython script that can be run within Moneydance

import csv
from datetime import datetime
import sys

def parse_date(date_str):
    """Parse date from various formats and return as YYYYMMDD integer"""
    for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return int(dt.strftime('%Y%m%d'))
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")

def get_column_value(row, *possible_names):
    """Get column value trying multiple possible column names"""
    for name in possible_names:
        if name in row and row[name] is not None:
            return row[name]
    row_keys_lower = {k.lower(): v for k, v in row.items() if k is not None}
    for name in possible_names:
        name_lower = name.lower() if name else ''
        if name_lower in row_keys_lower:
            return row_keys_lower[name_lower]
    return ''

def escape_string(text):
    """Escape string for Python/Jython code"""
    if not text:
        return ''
    text = str(text)
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    return text

def map_action_type(action, type_field, quantity, amount):
    """Figure out what of transaction this is from the description, the share quantity ('quantity'), and change 
    in balance occurring ('amount')"""
    action = action.upper().strip()
    type_field = type_field.upper().strip()

    if any(sub in action for sub in ['BUY', 'BOUGHT', 'MERGER MER', 
                                     'TENDERED TEX', 'DISTRIBUTION']) and quantity > 0:
        return 'BUY'
    if any(sub in action for sub in ['SELL', 'SOLD', 'MERGER MER', 'TENDERED TEX']) and quantity < 0:
        return 'SELL'
    if any(sub in action for sub in ['DIVIDEND']):
        if quantity != 0:
            print("Warning: Non-zero quantity for DIVIDEND action: '"+action+"' / '"+type_field+"'")
        return 'DIVIDEND'
    if any(sub in action for sub in ['INTEREST', 'IN LIEU']) and amount > 0:
        if quantity != 0:
            print("Warning: Non-zero quantity for MISCINC action: '"+action+"' / '"+type_field+"'")
        return 'MISCINC'
    if any(sub in action or sub in type_field for sub in ['TAX', 'FEE', 'IN LIEU']) and amount < 0:
        if quantity != 0:
            print("Warning: Non-zero quantity for MISCEXP action: '"+action+"' / '"+type_field+"'")
        return 'MISCEXP'
    if 'REINVEST' in action:
        if quantity != 0:
            print("Warning: Non-zero quantity for DIVIDEND_REINVEST action: '"+action+"' / '"+type_field+"'")
        return 'DIVIDEND_REINVEST'

    # These are fallbacks. Fidelity provides all kinds of weird descriptions and sometimes the only way to really
    # know is to look at the quantity and amount.
    if quantity > 0:
        print("Unknown Action/Type: '"+action+"' / '"+type_field+"', defaulting to 'BUY'")
        return 'BUY'
    if quantity < 0:
        print("Unknown Action/Type: '"+action+"' / '"+type_field+"', defaulting to 'SELL'")
        return 'SELL'
    if amount < 0:
        print("Unknown Action/Type: '"+action+"' / '"+type_field+"', defaulting to 'MISCEXP'")
        return 'MISCEXP'
    if amount > 0:
        print("Unknown Action/Type: '"+action+"' / '"+type_field+"', defaulting to 'MISCINC'")
        return 'MISCINC'
    
    print("Unknown Action/Type: '"+action+"' / '"+type_field+"', defaulting to 'BANK'")
    return 'BANK'

def generate_moneydance_script(csv_file, output_script, account_name):
    """Generate Jython script for Moneydance"""
    
    with open(csv_file, 'r', encoding='utf-8-sig') as csvf:
        # Skip blank lines at the beginning
        lines = []
        for line in csvf:
            if line.strip():
                lines.append(line)
                break
        lines.extend(csvf.readlines())
        
        first_line = lines[0] if lines else ''
        delimiter = '\t' if '\t' in first_line and first_line.count('\t') > first_line.count(',') else ','
        
        print(f"Using delimiter: {'TAB' if delimiter == chr(9) else 'COMMA'}")
        
        reader = csv.DictReader(lines, delimiter=delimiter)
        reader.fieldnames = [field.strip().replace('\t', '').replace('\n', '').replace('\r', '') for field in reader.fieldnames]
        
        print("Detected columns:", reader.fieldnames)
        print()
        
        # Collect all transactions
        transactions_data = []
        transaction = {}
        
        for idx, row in enumerate(reader, start=1):
            try:
                run_date_str = get_column_value(row, 'Run Date', 'RunDate', 'Date', 'Trade Date')
                if not run_date_str or not run_date_str.strip():
                    continue
                # Fidelity has a disclaimer at the end that we can use to detect the end of transaction data
                if 'The data and information' in run_date_str:
                    print("Reached end of transaction data at row", idx)
                    break
                
                run_date = parse_date(run_date_str)
                
                action = get_column_value(row, 'Action')
                name = get_column_value(row, 'Description')
                symbol = get_column_value(row, 'Symbol', 'Ticker')
                symbol = symbol.strip() if symbol else ''       
                description = get_column_value(row, 'Action', 'Memo', 'Details')
                description = description.strip() if description else ''
                trans_type = get_column_value(row, 'Type', 'Transaction Type', 'Category')
                trans_type = trans_type.strip() if trans_type else ''
                
                balance_str = get_column_value(row, 'Cash Balance ($)', 'Balance')
                if balance_str == 'Processing':
                    continue
                else:
                    balance = float(balance_str.replace(',', '').replace('$', '').strip()) if balance_str and balance_str.strip() else 0.0
                price_str = get_column_value(row, 'Price ($)', 'Price', 'Unit Price')
                price = float(price_str.replace(',', '').replace('$', '').strip()) if price_str and price_str.strip() else 0.0
                
                quantity_str = get_column_value(row, 'Quantity', 'Shares', 'Units')
                quantity = float(quantity_str.replace(',', '').strip()) if quantity_str and quantity_str.strip() else 0.0
                
                amount_str = get_column_value(row, 'Amount ($)', 'Amount', 'Total')
                amount = float(amount_str.replace(',', '').replace('$', '').strip()) if amount_str and amount_str.strip() else 0.0
                
                commission_str = get_column_value(row, 'Commission ($)', 'Commission', 'Fee')
                commission = float(commission_str.replace(',', '').replace('$', '').strip()) if commission_str and commission_str.strip() else 0.0
                
                md_type = map_action_type(action, trans_type, quantity, amount)

                # We have to check whether the actual change in balance matches the amount. SOmetimes it doesn't and 
                # it's the change in balance that's correct, not Fidelity'e reported amount.
                if 'balance' in transaction and round(transaction['balance'] - balance, 2) != transaction['amount']:
                    print(f"Warning: Calculated amount {transaction['balance'] - balance} does not match amount {transaction['amount']} for transaction {idx}")
                    transaction['amount'] = transaction['balance'] - balance

                # Here, we are appending the transaction associated with the previous row. We have to do it like thi
                # because we need to compute the cnage in balance by looking ahead at the next row. 
                #
                # Also, not that Fidelity sometimes associates the symbol 315994103 (the CUSIP of FDRXX, 
                # Fidelity Government Cash Reserves) with cash transactions, so we have to filter these out 
                # of they have a 0 amount associated with them. These are effectively "empty" transactions.
                if transaction != {} and not (symbol == '315994103' and transaction['amount'] == 0):
                    transactions_data.append(transaction)
                    if transaction['amount'] == 0:
                        print(f"Skipping transaction with symbol '315994103' and amount 0 at row {idx}")

                transaction = {
                    'balance': balance,
                    'idx': idx,
                    'run_date': run_date,
                    'symbol': symbol,
                    'name': name,
                    'description': description,
                    'md_type': md_type,
                    'price': price,
                    'quantity': quantity,
                    'amount': amount,
                    'commission': commission
                }
                
            except Exception as e:
                print(f"Error processing row {idx}: {e}", file=sys.stderr)
                print(row)

        transactions_data.append(transaction)

        # Start building the Jython script
        script_lines = []
        script_lines.append("# Moneydance Transaction Import Script")
        script_lines.append("# Generated from CSV file")
        script_lines.append("")
        script_lines.append("from com.infinitekind.moneydance.model import AccountUtil, ParentTxn, SplitTxn, AbstractTxn, CurrencyType, Account, InvestFields, InvestTxnType")
        script_lines.append("from java.lang import Long")
        script_lines.append("import sys")
        script_lines.append("")
        script_lines.append("# Get the root account and book")
        script_lines.append("root = moneydance.getCurrentAccountBook()")
        script_lines.append("")
        script_lines.append("# Find the investment account: " + account_name)
        script_lines.append("account = None")
        script_lines.append("for acct in root.getRootAccount().getSubAccounts():")
        script_lines.append("    if acct.getAccountName() == \"" + escape_string(account_name) + "\":")
        script_lines.append("        account = acct")
        script_lines.append("        break")
        script_lines.append("    for subacct in acct.getSubAccounts():")
        script_lines.append("        if subacct.getAccountName() == \"" + escape_string(account_name) + "\":")
        script_lines.append("            account = subacct")
        script_lines.append("            break")
        script_lines.append("")
        script_lines.append("if account is None:")
        script_lines.append("    print(\"ERROR: Account \\\"" + escape_string(account_name) + "\\\" not found!\")")
        script_lines.append("    print(\"Available accounts:\")")
        script_lines.append("    for acct in root.getRootAccount().getSubAccounts():")
        script_lines.append("        print(\"  - \" + acct.getAccountName())")
        script_lines.append("        for subacct in acct.getSubAccounts():")
        script_lines.append("            print(\"    - \" + subacct.getAccountName())")
        script_lines.append("else:")
        script_lines.append("    print(\"Found account: " + escape_string(account_name) + "\")")
        script_lines.append("")
        script_lines.append("# Function to find security")
        script_lines.append("def findSecurity(ticker):")
        script_lines.append("    currList = []")
        script_lines.append("    for curr in root.getCurrencies().getAllCurrencies():")
        script_lines.append("        if curr.getCurrencyType() == CurrencyType.Type.SECURITY:")
        script_lines.append("            if curr.getTickerSymbol() == ticker:")
        script_lines.append("                currList.append(curr)")
        script_lines.append("    if len(currList) > 0:")
        script_lines.append("        return(currList)")
        script_lines.append("    for curr in root.getCurrencies().getAllCurrencies():")
        script_lines.append("        if curr.getCurrencyType() == CurrencyType.Type.SECURITY:")
        script_lines.append("            secID = curr.getIDForScheme(\"CUSIP\")")
        script_lines.append("            if secID is not None and ticker in secID:")
        script_lines.append("                currList.append(curr)")
        script_lines.append("    return currList")
        script_lines.append("")
        script_lines.append("def findSecurityAcct(ticker):")
        script_lines.append("    acctList = []")
        script_lines.append("    if ticker == \"CASH\" or ticker == \"315994103\":")
        script_lines.append("        return [\"CASH\"]")
        script_lines.append("    l = findSecurity(ticker)")
        script_lines.append("    for sec in l:")
        script_lines.append("       name = sec.getName()")
        script_lines.append("       for a in account.getSubAccounts():")
        script_lines.append("           if a.getAccountName() == name:")
        script_lines.append("               acctList.append(a)")
        script_lines.append("    if (len(acctList) > 1):")
        script_lines.append("        for a in acctList:")
        script_lines.append("            if a.getBalance() == 0:")
        script_lines.append("                acctList.remove(a)")
        script_lines.append("    return acctList")
        script_lines.append("")
        script_lines.append("def getShareScale(ticker):")
        script_lines.append("    try: return 10 ** findSecurity(ticker)[0].getDecimalPlaces()")
        script_lines.append("    except: return 10000")
        script_lines.append("")
        
        # Validation - split into batches to avoid functions that exceed Java's maximum allowed size.
        securities_to_validate = sorted(set(
            (txn_data['symbol'], txn_data['name'])
            for txn_data in transactions_data 
            if txn_data['md_type'] in ['BUY', 'SELL', 'DIVIDEND', 'DIVIDEND_REINVEST'] and txn_data['symbol']
        ))
        
        # Create validation functions
        SEC_BATCH_SIZE = 20
        num_sec_batches = (len(securities_to_validate) + SEC_BATCH_SIZE - 1) // SEC_BATCH_SIZE
        
        for sec_batch_idx in range(num_sec_batches):
            start_idx = sec_batch_idx * SEC_BATCH_SIZE
            end_idx = min(start_idx + SEC_BATCH_SIZE, len(securities_to_validate))
            sec_batch = securities_to_validate[start_idx:end_idx]
            
            script_lines.append("def validateSecurities" + str(sec_batch_idx) + "():")
            script_lines.append("    missing = []")
            script_lines.append("    duplicate = []")
            for (symbol, name) in sec_batch:
                script_lines.append("    security = findSecurityAcct(\"" + escape_string(symbol) + "\")")
                script_lines.append("    if len(security) == 0:")
                script_lines.append("        missing.append(\"" + escape_string(symbol) + " " + escape_string(name) + "\")")
                script_lines.append("    if len(security) > 1:")
                script_lines.append("        print(\"" + escape_string(symbol)+ "\")")
                script_lines.append("        for sec in security:")
                script_lines.append("            print(\" - \" + sec.getAccountName(), sec.getBalance())")
                script_lines.append("        duplicate.append(\"" + escape_string(symbol) + " " + escape_string(name) + "\")")
            script_lines.append("    return missing, duplicate")
            script_lines.append("")
        
        # Generate transaction import functions. Again, we match these to avoid the maximum function size.
        BATCH_SIZE = 50
        num_batches = (len(transactions_data) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(transactions_data))
            batch = transactions_data[start_idx:end_idx]
            
            script_lines.append("def importBatch" + str(batch_idx) + "():")
            script_lines.append("    # Batch " + str(batch_idx + 1) + " of " + str(num_batches))
            script_lines.append("    batch_count = 0")
            
            for txn_data in batch:
                idx = txn_data['idx']
                run_date = txn_data['run_date']
                symbol = txn_data['symbol']
                description = escape_string(txn_data['description'])
                md_type = txn_data['md_type']
                price = txn_data['price']
                quantity = txn_data['quantity']
                amount = txn_data['amount']
                commission = txn_data['commission']

                script_lines.append("    # Transaction " + str(idx) + ": " + md_type + " " + symbol)
                script_lines.append("    txn = ParentTxn(root)")
                script_lines.append("    txn.setAccount(account)")
                script_lines.append("    txn.setDateInt(" + str(run_date) + ")")
                if md_type in ['BUY', 'SELL', 'DIVIDEND', 'DIVIDEND_REINVEST']:
                    script_lines.append("    security = findSecurityAcct(\"" + escape_string(symbol) + "\")[0]")
                    script_lines.append("    if security is None:")
                    script_lines.append("        print(\"ERROR: Missing security " + escape_string(symbol) + "\")")
                    script_lines.append("        sys.exit(1)")
                    script_lines.append("    txn.setDescription(\"" + md_type + " \" + str(security).split(':')[1])")
                elif md_type == 'MISCEXP':
                    script_lines.append("    txn.setDescription(\"MISC EXPENSE\")")
                else: #md_type == 'MISCINC':
                    script_lines.append("    txn.setDescription(\"MISC INCOME\")")
                script_lines.append("    txn.setMemo(\"" + description + "\")")
                script_lines.append("    fields = InvestFields()")
                script_lines.append("    fields.setFieldStatus(InvestTxnType."+md_type+", txn)")
             
                if md_type in ['BUY', 'SELL']:
                    amount_long = int(round(abs(amount) * 100))
                    commission_long = int(round(commission * 100))
                    script_lines.append("    fields.security = security")
                    script_lines.append("    scale = getShareScale(\"" + escape_string(symbol) + "\")")
                    script_lines.append("    qty = int(round(abs(" + str(quantity) + ") * scale))")
                    script_lines.append("    prc = int(round(abs(" + str(price) + ") * scale))")
                    script_lines.append("    fields.shares = qty")
                    script_lines.append("    fields.price = prc")
                    script_lines.append("    fields.fee = " + str(commission_long))
                    script_lines.append("    fields.amount = " + str(amount_long))
                    script_lines.append("    fields.storeFields(txn)")
                    script_lines.append("    txn.syncItem()")
                    script_lines.append("    batch_count += 1")
                    
                elif md_type == 'DIVIDEND':
                    amount_long = int(round(amount * 100))
                    script_lines.append("    fields.security = security")
                    script_lines.append("    fields.amount = " + str(amount_long))
                    script_lines.append("    fields.shares = 0")
                    script_lines.append("    fields.price = 1")
                    script_lines.append("    fields.category = AccountUtil.getDefaultCategoryForAcct(account)")
                    script_lines.append("    fields.storeFields(txn)")
                    script_lines.append("    txn.syncItem()")
                    script_lines.append("    batch_count += 1")
                    
                elif md_type == 'DIVIDEND_REINVEST':
                    amount_long = int(round(amount * 100))
                    script_lines.append("    fields.security = security")
                    script_lines.append("    scale = getShareScale(\"" + escape_string(symbol) + "\")")
                    script_lines.append("    qty = int(round(abs(" + str(quantity) + ") * scale))")
                    script_lines.append("    prc = int(round(abs(" + str(price) + ") * scale))")
                    script_lines.append("    fields.shares = qty")
                    script_lines.append("    fields.price = prc")
                    script_lines.append("    fields.amount = " + str(amount_long))
                    script_lines.append("    fields.shares = 0")
                    script_lines.append("    fields.price = 1")
                    script_lines.append("    fields.feeAcct = AccountUtil.getDefaultCategoryForAcct(account)")
                    script_lines.append("    fields.category = AccountUtil.getDefaultCategoryForAcct(account)")
                    script_lines.append("    fields.storeFields(txn)")
                    script_lines.append("    txn.syncItem()")
                    script_lines.append("    batch_count += 1")
                    
                elif md_type in ['MISCEXP','MISCINC']:
                    amount_long = int(round(abs(amount) * 100))
                    script_lines.append("    fields.amount = " + str(amount_long))
                    script_lines.append("    fields.shares = 0")
                    script_lines.append("    fields.price = 1")
                    script_lines.append("    fields.feeAcct = AccountUtil.getDefaultCategoryForAcct(account)")
                    script_lines.append("    fields.category = AccountUtil.getDefaultCategoryForAcct(account)")
                    script_lines.append("    fields.storeFields(txn)")
                    script_lines.append("    txn.syncItem()")
                    script_lines.append("    batch_count += 1")
                    
                else:
                    amount_long = int(round(amount * 100))
                    script_lines.append("    fields.amount = " + str(amount_long))
                    script_lines.append("    fields.storeFields(txn)")
                    script_lines.append("    txn.syncItem()")
                    script_lines.append("    batch_count += 1")
                
                script_lines.append("")
            
            script_lines.append("    return batch_count")
            script_lines.append("")
        
        # Main execution code
        script_lines.append("# Validate all securities")
        script_lines.append("if account is not None:")
        script_lines.append("    print(\"Validating securities...\")")
        script_lines.append("    missing_securities = []")
        script_lines.append("    duplicate_securities = []")
        for sec_batch_idx in range(num_sec_batches):
            script_lines.append("    m, d = validateSecurities" + str(sec_batch_idx) + "()")
            script_lines.append("    missing_securities.extend(m)")
            script_lines.append("    duplicate_securities.extend(d)")
        
        script_lines.append("")
        script_lines.append("    if len(missing_securities) > 0:")
        script_lines.append("        print(\"ERROR: The following securities are not found in Moneydance:\")")
        script_lines.append("        for sec in missing_securities:")
        script_lines.append("            if len(findSecurity(sec)) == 0:")    
        script_lines.append("                print(\"  - \" + sec)")
        script_lines.append("        print(\"ERROR: The following securities have no subaccount:\")")
        script_lines.append("        for sec in missing_securities:")
        script_lines.append("            if len(findSecurity(sec)) > 0:") 
        script_lines.append("                print(\"  - \" + sec)")
        script_lines.append("        print(\"Please add these securities to Moneydance before importing.\")")
        script_lines.append("")
        script_lines.append("    if len(duplicate_securities) > 0:")
        script_lines.append("        print(\"ERROR: The following securities are duplicated in Moneydance:\")")
        script_lines.append("        for sec in duplicate_securities:")
        script_lines.append("            print(\"  - \" + sec)")
        script_lines.append("        print(\"Please repair this in Moneydance before importing.\")")
        script_lines.append("")
        script_lines.append("    if len(missing_securities) == 0 and len(duplicate_securities) == 0:")
        script_lines.append("        print(\"All securities found. Beginning import...\")")
        script_lines.append("        total_count = 0")
        
        # Call each batch function
        for batch_idx in range(num_batches):
            script_lines.append("        print(\"Processing batch " + str(batch_idx + 1) + " of " + str(num_batches) + "...\")")
            script_lines.append("        total_count += importBatch" + str(batch_idx) + "()")
        
        script_lines.append("")
        script_lines.append("        print(\"Import complete: \" + str(total_count) + \" transactions added\")")
        
        # Write the script
        with open(output_script, 'w') as f:
            f.write('\n'.join(script_lines))
        
        print(f"\nGenerated Moneydance script: {output_script}")
        print(f"Processed {len(transactions_data)} transactions in {num_batches} batches")
        print(f"Validated {len(securities_to_validate)} securities in {num_sec_batches} batches")
        print(f"\nTo use: Extensions -> Show Moneybot Console -> Open Script -> Select {output_script} -> Run")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python csv_to_moneydance.py input.csv output.py account_name")
        print("Example: python csv_to_moneydance.py transactions.csv import_txns.py 'My Brokerage'")
        print("\nThis generates a Jython script that you run in Moneydance's Moneybot Console")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    output_script = sys.argv[2]
    account_name = sys.argv[3]
    
    generate_moneydance_script(csv_file, output_script, account_name)