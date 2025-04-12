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

client = Quotes.factory(market='std')
FLAG_STOCK_DATA_SYNC = "2025-01-01"
FLAG_STOCK_CHOOSE = "2025-01-01"
FLAG_STOCK_TIME_OUT = "2025-01-01"



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


def get_last_5days():
    days_list = []
    date_temp = datetime.datetime.today()
    while len(days_list) < 5:
        date_temp -= datetime.timedelta(days=1)
        date_temp_str = date_temp.strftime("%Y%m%d")
        if not holiday.holiday(date_temp_str,format_="%Y%m%d"):
            days_list.append(date_temp_str)
    return days_list


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

            time.sleep(10)
            print("early trade")
            continue

       if now > TRADE_TIME_START and now < TRADE_TIME_END:
            time.sleep(10)
            print("trade")
            continue
         
       if not (now >= TRADE_TIME_PREPARE_START and now <= STOCK_SYNC_START)  and FLAG_STOCK_DATA_SYNC != flag:
            print("stock sync")
            FLAG_STOCK_DATA_SYNC = flag
            continue
       
       if FLAG_STOCK_DATA_SYNC == flag and FLAG_STOCK_CHOOSE != flag:
            print("stock choose")
            FLAG_STOCK_CHOOSE = flag
            continue

       print("idle")
       time.sleep(60*5)

    



