import pandas as pd
CHOOSE_RATE_L = 0.6
CHOOSE_RATE_H = 1
CASH_LEFT = 100
L = 0.97
H = 1.05
TRADE_TIME_PREPARE_START = "09:15:00"
TRADE_TIME_PREPARE_END = "09:20:00"
TRADE_TIME_START = "09:31:00"
TRADE_TIME_END = "15:00:00"

STOCK_SYNC_START = "22:00:00"

def train_col():
    transform_col = ["open_transform","high_transform","low_transform"]
    trn_col = ["open","high","low","close","pre_close","volume","amount","is_hs","market","industry","exchange","macd","rsi","date_type","n_date_type","ts_code_id"] + transform_col
    for i in range(10):
        trn_col.append("macd_"+str(i+1))

    for i in range(30):  
        trn_col.append('close_shift_{}'.format(i + 1))  
    return trn_col

def  get_st_symbol():
    from mootdx.quotes import Quotes
    from mootdx import consts
    client = Quotes.factory(market='std')
    sh = client.stocks(market=consts.MARKET_SH)
    sh = sh[sh["name"].str.contains("ST")]
    sh = sh["code"]+".SH"
    sz = client.stocks(market=consts.MARKET_SZ)
    sz = sz[sz["name"].str.contains("ST")]
    sz = sz["code"]+".SZ"
    symbol = pd.DataFrame()
    symbol["code"] = pd.concat([sh,sz])
    return symbol["code"].values