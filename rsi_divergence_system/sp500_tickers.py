"""
S&P 500 ticker symbols
List of S&P 500 components
"""

SP500_TICKERS = [
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'BRK.B', 'TSLA', 'LLY',
    'AVGO', 'JPM', 'V', 'UNH', 'XOM', 'WMT', 'MA', 'COST', 'HD', 'JNJ',
    'PG', 'NFLX', 'BAC', 'ABBV', 'ORCL', 'CRM', 'CVX', 'KO', 'MRK', 'AMD',
    'PEP', 'ADBE', 'TMO', 'LIN', 'WFC', 'ACN', 'CSCO', 'MCD', 'ABT', 'QCOM',
    'PM', 'DHR', 'TXN', 'IBM', 'GE', 'NEE', 'AMGN', 'ISRG', 'VZ', 'CMCSA',
    'INTU', 'CAT', 'NOW', 'PFE', 'T', 'HON', 'SPGI', 'RTX', 'GS', 'UNP',
    'BKNG', 'AXP', 'LOW', 'BLK', 'SYK', 'UPS', 'MS', 'ELV', 'PGR', 'TJX',
    'ADP', 'BA', 'VRTX', 'MDT', 'DE', 'SBUX', 'MMC', 'ADI', 'SCHW', 'GILD',
    'CI', 'AMT', 'LRCX', 'C', 'PLD', 'CB', 'AMAT', 'REGN', 'MDLZ', 'ETN',
    'BMY', 'FI', 'MO', 'PANW', 'SO', 'DUK', 'BSX', 'ITW', 'ZTS', 'WM',
    'BDX', 'EOG', 'APH', 'SLB', 'TGT', 'HCA', 'CSX', 'PH', 'CMG', 'SNPS',
    'MCK', 'MSI', 'NOC', 'COP', 'MAR', 'USB', 'MMM', 'KLAC', 'ICE', 'APO',
    'SHW', 'PNC', 'AON', 'TDG', 'PYPL', 'EMR', 'DG', 'CL', 'ECL', 'CDNS',
    'TT', 'FDX', 'TFC', 'MCO', 'WELL', 'EQIX', 'CME', 'CARR', 'WMB', 'COF',
    'FCX', 'GM', 'MU', 'NSC', 'ORLY', 'APD', 'OXY', 'AJG', 'PCAR', 'AFL',
    'PSA', 'BK', 'RSG', 'SRE', 'ROP', 'JCI', 'ADSK', 'AIG', 'HLT', 'TRV',
    'AZO', 'PAYX', 'NEM', 'ROST', 'DVN', 'NXPI', 'GWW', 'AEP', 'PRU', 'ALL',
    'MSCI', 'URI', 'HES', 'MCHP', 'SPG', 'CTVA', 'KMB', 'TEL', 'HWM', 'GIS',
    'ODFL', 'SYY', 'EA', 'D', 'YUM', 'PSX', 'KMI', 'CCI', 'FAST', 'F',
    'LHX', 'DD', 'CHTR', 'AMP', 'CTAS', 'O', 'VRSK', 'BKR', 'KR', 'EW',
    'IQV', 'CPRT', 'DLR', 'ACGL', 'DHI', 'IDXX', 'CMI', 'PCG', 'DXCM', 'LULU',
    'LEN', 'CTSH', 'VICI', 'A', 'OTIS', 'IT', 'KDP', 'AXON', 'EXC', 'AME',
    'RMD', 'PEG', 'IR', 'XEL', 'DOW', 'EXR', 'GLW', 'HIG', 'VMC', 'CBRE',
    'PWR', 'FANG', 'DAL', 'TRGP', 'KVUE', 'HPQ', 'ROK', 'GEHC', 'ANSS', 'ON',
    'MNST', 'FIS', 'VLO', 'ED', 'FITB', 'WAB', 'STZ', 'TTWO', 'MTB', 'ETR',
    'WTW', 'MLM', 'KEYS', 'STT', 'EBAY', 'DOV', 'IFF', 'EFX', 'GPN', 'DFS',
    'MPWR', 'PPG', 'LYB', 'VTR', 'TSCO', 'RJF', 'AWK', 'TSN', 'ADM', 'APTV',
    'HPE', 'TYL', 'AVB', 'BALL', 'WST', 'NTAP', 'FTV', 'ZBRA', 'BRO', 'FE',
    'MTD', 'WEC', 'DLTR', 'HBAN', 'EIX', 'CDW', 'RF', 'ALGN', 'SYF', 'PKG',
    'PTC', 'IRM', 'LUV', 'TDY', 'CSGP', 'BR', 'CFG', 'STLD', 'BAX', 'LDOS',
    'ES', 'WY', 'EQR', 'INVH', 'WBD', 'BLDR', 'EXPE', 'HOLX', 'DTE', 'GPC',
    'CNP', 'PPL', 'ARE', 'CAH', 'TROW', 'UAL', 'DRI', 'MOH', 'NTRS', 'COO',
    'VLTO', 'ZBH', 'CLX', 'MAS', 'STE', 'CRL', 'CINF', 'K', 'EXPD', 'AEE',
    'TXT', 'HUBB', 'JBHT', 'PODD', 'LVS', 'IP', 'LH', 'NVR', 'EG', 'EPAM',
    'SNA', 'MAA', 'JKHY', 'MKC', 'CTLT', 'J', 'ESS', 'DGX', 'BBY', 'CBOE',
    'HSY', 'OMC', 'SW', 'FDS', 'EVRG', 'SWKS', 'TER', 'UDR', 'EMN', 'NDAQ',
    'AKAM', 'FICO', 'WAT', 'KMX', 'VRSN', 'CPT', 'DG', 'FFIV', 'PAYC', 'CE',
    'POOL', 'WRB', 'TECH', 'LNT', 'HRL', 'ATO', 'BBWI', 'CCL', 'LYV', 'APA',
    'UHS', 'AVY', 'IEX', 'HSIC', 'NI', 'CHRW', 'RCL', 'ENPH', 'MKTX', 'CZR',
    'PHM', 'KIM', 'CPB', 'REG', 'ALLE', 'TPR', 'TAP', 'PNR', 'BG', 'BXP',
    'NDSN', 'GL', 'GNRC', 'NRG', 'AIZ', 'TFX', 'AES', 'HAS', 'LKQ', 'WYNN',
    'MHK', 'BWA', 'CMA', 'ZION', 'AAL', 'ALB', 'NWSA', 'NWS', 'MGM', 'BEN',
    'PARA', 'FOX', 'FOXA', 'FMC', 'RL', 'QRVO', 'IPG', 'PNW', 'DVA', 'ROL'
]


def get_sp500_tickers():
    """
    Returns the list of S&P 500 ticker symbols

    Returns:
    - List of ticker symbols
    """
    return SP500_TICKERS.copy()
