import easytrader
from mootdx.quotes import Quotes
from mootdx.utils import holiday
from config import *
import time
import datetime
import os
import warnings
from lgdm import prepare_stock_data

import lightgbm as lgb

warnings.filterwarnings("ignore")
user = easytrader.use('universal_client')
user.connect(f'{os.getcwd()}\\..\\..\\xiadan\\xiadan.exe')
user.enable_type_keys_for_editor()

client = Quotes.factory(market='std')
MY_STOCK_POSITION = None
FLAG_STOCK_DATA_SYNC = "2025-01-01"
FLAG_STOCK_CHOOSE = "2025-01-01"
FLAG_STOCK_TIME_OUT = "2025-01-01"
FLAG_UPDATE_STOCK_POSITION = True


def get_stock_position():

    global FLAG_UPDATE_STOCK_POSITION 
    global MY_STOCK_POSITION
    
    if FLAG_UPDATE_STOCK_POSITION or MY_STOCK_POSITION == None:
        pos = user.position
        MY_STOCK_POSITION = []
        for p in pos:
            item = {"code":p["证券代码"],"avg_price":p["成本价"],"count":p["股票余额"],"avi_count":p["可用余额"]}
            if item["avi_count"] == 0:
                continue
            MY_STOCK_POSITION.append(item)
        FLAG_UPDATE_STOCK_POSITION = False
    return MY_STOCK_POSITION

def stock_choose():
    trn_col = train_col()
    if  not os.path.exists("gdm.model"):
        exit(1)
    g = lgb.Booster(model_file="gdm.model")
    data = prepare_stock_data(predic_days= 1)
    prd_input = data[trn_col]

    prd_val = g.predict(prd_input.values,num_iteration=g.best_iteration)
    data["prd_val"] = prd_val

    buy_ts = data[["ts_code", "trade_date", "open", "close", "close_shift_1","n_date_type","prd_val"]].sort_values("prd_val", ascending=False)
    ts_name = pd.read_csv("./stock/company_info.csv")[["ts_code", "name"]]
    buy_ts = buy_ts.merge(ts_name, how="left", on="ts_code")
    st = get_st_symbol()
    buy_ts = buy_ts[~buy_ts["ts_code"].isin(st)]
    buy_ts = buy_ts[buy_ts["trade_date"] == buy_ts["trade_date"].max()]
    buy_ts = buy_ts[(buy_ts["prd_val"] > CHOOSE_RATE_L) &(buy_ts["prd_val"] < CHOOSE_RATE_H)]
    buy_ts = buy_ts.head(5)
    buy_ts = buy_ts.reset_index(drop=True)
    if len(buy_ts) == 0:
        print("NO STOCK TO BUY")
    else:
        print(buy_ts)
    return buy_ts

def get_cash():
    return user.balance["可用金额"]

def order_in(stocks):
    if len(stocks) == 0:
        return
    try:
        cash = get_cash()

        for index in range(len(stocks)):
            code = stocks.loc[index,"ts_code"]
            price = stocks.loc[index,"close"]
            buy_cash = (cash - CASH_LEFT)*0.5
            if buy_cash < 100*price:
                buy_cash = cash - CASH_LEFT

            if buy_cash < 100*price:
                return

            count = int(buy_cash // price)
            count = (count//100)*100
            if count < 100:
                continue
            symbol = code[:6]
            user.buy(symbol,price,count)
            cash = cash - price*count
        global FLAG_UPDATE_STOCK_POSITION 
        FLAG_UPDATE_STOCK_POSITION = True
    except:
        print("order in fail")

def get_last_5days():
    days_list = []
    date_temp = datetime.datetime.today()
    while len(days_list) < 5:
        date_temp -= datetime.timedelta(days=1)
        date_temp_str = date_temp.strftime("%Y%m%d")
        if not holiday.holiday(date_temp_str,format_="%Y%m%d"):
            days_list.append(date_temp_str)
    return days_list

def sell_for_timeout(flag):
    global FLAG_STOCK_TIME_OUT
    global FLAG_UPDATE_STOCK_POSITION

    if FLAG_STOCK_TIME_OUT != flag:
        try:
            days = get_last_5days()
            his_data = user.history_trades
            df = pd.DataFrame(his_data)
            df["成交日期"] = df["成交日期"].astype("string")
            df = df[(df["成交日期"].isin(days))& (df["操作"]=="买入")]
            stock_keep = df["证券代码"].unique()
            my_stock = pd.DataFrame(get_stock_position())
            to_sell = my_stock[~my_stock["code"].isin(stock_keep)]
            print(to_sell)
            for i in to_sell.index:
                cde = to_sell.loc[i,"code"]
                avi_ct = to_sell.loc[i,"avi_count"]
                user.market_sell(cde,avi_ct)
                FLAG_UPDATE_STOCK_POSITION = True
            FLAG_STOCK_TIME_OUT = flag
        except:
            print("sell for timeout error")
    

if __name__ == '__main__':
    while True:
       today_offset_2hour = (datetime.datetime.now() + datetime.timedelta(hours=2)).strftime("%Y-%m-%d")
       flag = today_offset_2hour
       is_holiday = holiday.holiday(today_offset_2hour)
       if is_holiday:
            print("holiday idle")
            time.sleep(60*5)
            continue
       now = datetime.datetime.now().strftime("%H:%M:%S")
       if now > TRADE_TIME_PREPARE_START and now < TRADE_TIME_PREPARE_END:
            FLAG_UPDATE_STOCK_POSITION = True
            sell_for_timeout(flag)
            time.sleep(10)
            print("early trade")
            continue
       if now > TRADE_TIME_START and now < TRADE_TIME_END:
            stock_pos = []
            try:
                stock_pos = get_stock_position()
            except:
                MY_STOCK_POSITION = []
                FLAG_UPDATE_STOCK_POSITION = True
                print("stock position error")
                time.sleep(10)

            if len(stock_pos) == 0:
                print("stock position none")
                time.sleep(10)
                continue
            stock_df = pd.DataFrame(stock_pos)
            try:
                data = client.quotes(symbol=list(stock_df["code"].values))
                data = data[["market","code","servertime","price","open","high","low","volume","amount"]]
                data = pd.merge(data,stock_df,on="code",how="left")
                print(data)
                for_sell =  data[(data["price"] > data["avg_price"]*H )| (data["price"] < data["avg_price"]*L )]
                for i in for_sell.index:
                    cde = for_sell.loc[i,"code"]
                    pri = for_sell.loc[i,"price"]
                    avg_pri = for_sell.loc[i,"avg_price"]
                    avi_ct = for_sell.loc[i,"avi_count"]
                    if pri < avg_pri:
                        user.market_sell(cde,avi_ct)
                    else:
                        user.sell(cde,pri,avi_ct)
                    FLAG_UPDATE_STOCK_POSITION = True
            except:
                print("price fetch or sell error")

            time.sleep(2)
            continue
       flag = today_offset_2hour
       if not (now >= TRADE_TIME_PREPARE_START and now <= STOCK_SYNC_START)  and FLAG_STOCK_DATA_SYNC != flag:
            print("stock sync")
            try:
                os.system(f"{os.getcwd()}\\run_tdx.exe")
                time.sleep(5)
                FLAG_STOCK_DATA_SYNC = flag
            except:
                print("sync fail")
            continue
       
       if FLAG_STOCK_DATA_SYNC == flag and FLAG_STOCK_CHOOSE != flag:
            print("stock choose")
            stocks = stock_choose()
            order_in(stocks)
            time.sleep(5)
            FLAG_STOCK_CHOOSE = flag
            continue
       print("idle")
       time.sleep(60*5)

    



