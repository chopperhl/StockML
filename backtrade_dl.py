from datetime import timedelta, datetime

import pandas as pd

import lightgbm as lgb
import numpy as np

from config import CHOOSE_RATE_H,CHOOSE_RATE_L,L,H,train_col

START_CASH = 10000
MDOEL_NAME = "gdm.model"

class Backtrader(object):

    def __init__(self,log=True):
        self.cash = START_CASH
        self.cache_data = {}
        self.stock_info = pd.read_csv("prepared_data.csv")
        self.stock_info = self.stock_info[self.stock_info["trade_date"]>20231218]
        self.workdays = self.stock_info["trade_date"].drop_duplicates().values
        self.stock_data = pd.DataFrame(data={"tscode": [], "count": [], "price": [],"day":[] ,"lock":[]})
        self.income_rate = 0
        self.income_table = pd.DataFrame(data={"date":[],"amount":[],"rate":[]})
        self.log_enable = log
        self.ts_name = None
        self.loss = 0
        self.win = 0
        self.g = lgb.Booster(model_file= MDOEL_NAME)

    def log(self,msg):
        if self.log_enable:
            print(msg)

    def predic(self,tdate):
        
        data = self.stock_info[self.stock_info["trade_date"] == int(tdate)].copy()
        trn_col = train_col()
        prd_input = data[trn_col]
        prd_val = self.g.predict(prd_input.values, num_iteration=self.g.best_iteration)
        data["prd_val"] = prd_val

        buy_ts = data[["ts_code", "trade_date", "open", "close", "prd_val"]].sort_values("prd_val", ascending=False)
        if self.ts_name is None:
            self.ts_name = pd.read_csv("./stock/company_info.csv")[["ts_code", "name"]]

        buy_ts = buy_ts.merge(self.ts_name, how="left", on="ts_code")
        buy_ts = buy_ts[buy_ts["name"].str.contains("ST") == False]
        buy_ts = buy_ts[(buy_ts["prd_val"] > CHOOSE_RATE_L)&(buy_ts["prd_val"] < CHOOSE_RATE_H)]
        return buy_ts[["ts_code","prd_val"]]
        

        

    def income(self,date):
        stocks = self.stock_data["tscode"].values
        all_price = 0
        for tscode in stocks:
            price = self.__get_price(tscode, date)
            if price is  None:
                continue

            index =self.stock_data[self.stock_data["tscode"] == tscode].index.tolist()[0]
            hold_count = self.stock_data.loc[index, "count"]
            if hold_count > 0:
                hold_price = price * hold_count
                all_price += hold_price
                pass
        all_price += self.cash
        self.income_rate = (all_price - START_CASH)*100/ START_CASH
        str_data = datetime.strftime(date, "%Y%m%d")

        self.income_table = self.income_table.append(pd.DataFrame({"date":[date],"amount":[round(all_price,2)],"rate":[round(self.income_rate,2)]}),ignore_index=True)
        self.log(f"{str_data}: 当前账户总值：{round(all_price,2)},其中账户余额：{round(self.cash,2)}，账户收益率：{round(self.income_rate,2)}%")


    def run(self,data_time,d):

        stocks = self.stock_data["tscode"].values

        for tscode in stocks:
            self.force_sell(tscode,data_time,d)
        self.order_in(data_time,d)

    def start(self,start = "20241212",days = 500):
        start_date = datetime.strptime(start, "%Y%m%d").date()
        for day in range(days):
            run_date = start_date - timedelta(days=days - day)
            d =  run_date.strftime("%Y%m%d")
            if int(d) in self.workdays:
                self.run(run_date,day)
                self.income(run_date)
        rate = self.win*100 /(self.win +self.loss)
        print(f"win:{self.win},lose: {self.loss} win rate {round(rate,2)}%")


    def order_in(self,date,d):
        if self.cash < 400:
            return
        str_data = datetime.strftime(date, "%Y%m%d")



        buy_stocks = self.predic(str_data)
        buy_tscode = buy_stocks["ts_code"].values
        if len(buy_tscode) == 0:
            return
        for tscode in buy_tscode:
            if self.cash < 400:
                return
            day_line = self.stock_info[(self.stock_info["ts_code"] == tscode) & (self.stock_info["trade_date"] == int(str_data))]
            price = day_line["close"].values[0]
            if self.cash -50 < 100*price:
                continue

            buy_cash = (self.cash - 50)*0.5
            if buy_cash < 100*price:
                buy_cash = self.cash - 50 

            count = int(buy_cash // price)
            count = (count//100)*100

            cost = price * count
            other_cost =  max(5,cost*0.0008) +cost*0.00001
            self.cash -= cost
            self.cash -= other_cost
            self.log(f"{str_data}: 买入股票：{tscode} {count}股，每股{price} ,花费: {round(cost,2)},手续费：{round(other_cost,2)},资金剩余：{round(self.cash,2)}")


            stocks = list(self.stock_data["tscode"].values)
            if tscode in stocks:
                index =self.stock_data[self.stock_data["tscode"] == tscode].index.tolist()[0]
                hold = self.stock_data.loc[index,"count"]
                pre_price = self.stock_data.loc[index,"price"]
                p = (hold * pre_price + cost)/(hold + count)
                self.stock_data.loc[index,"count"] = hold + count
                self.stock_data.loc[index,"price"] = p
                self.stock_data.loc[index,"day"] = d
                self.stock_data.loc[index,"lock"] = 1


            else:
                self.stock_data = self.stock_data.append(pd.DataFrame({"tscode":[tscode],"count":[count],"price":[price],"day":[d],"lock":[1]}),ignore_index=True)


    def force_sell(self,tscode,date,d):
        stocks = self.stock_data["tscode"].values

        if tscode not in stocks:
            return

        index =self.stock_data[self.stock_data["tscode"] == tscode].index.tolist()[0]
        hold_count = self.stock_data.loc[index, "count"]
        day = d - self.stock_data.loc[index, "day"]
        lock = self.stock_data.loc[index, "lock"]
        if hold_count < 1:
            return
        if lock == 1:
            self.stock_data.loc[index, "lock"] = 0
            return
        price_data = self.__get_price_high_low(tscode, date)
        if len(price_data) == 0:
            return
        high_price = price_data["high"].values[0]
        low_price = price_data["low"].values[0]
        close_price = price_data["close"].values[0]
        open_price = price_data["open"].values[0]
        pre_price = price_data["pre_close"].values[0]
        ave_price = self.stock_data.loc[index, "price"]
        lp = L*ave_price
        hp = H*ave_price

        str_data = datetime.strftime(date, "%Y%m%d")
        if open_price < lp or low_price < lp or open_price >hp or high_price > hp or day > 6:
            price = ave_price
            if high_price > hp or open_price > hp:
                if open_price > hp:
                    price = open_price
                else:
                    price = hp
                tag = "盈利"
            elif low_price < lp or open_price < lp:
                if open_price < lp:
                    price = open_price
                else:
                    price = lp
                tag = "亏损"
            else:
                if high_price < pre_price:
                    print("----未卖出----")
                    price = close_price
                else: 
                    price = pre_price
                tag = "持有时间过长"

            rise_percent = (price - ave_price)/ ave_price
            if rise_percent > 0 :
                self.win += 1
            else:
                self.loss += 1 

            count = hold_count
            amount = count * price
            other_cost = max(5, amount * 0.0008) + amount * 0.0051
            self.cash += amount
            self.cash -= other_cost

            index =self.stock_data[self.stock_data["tscode"] == tscode].index.tolist()[0]
            self.log(
                f"{str_data}: 卖出股票：{tscode} {tag}：{round(rise_percent * 100, 2)}% {count}股，每股{price} ,收入: {round(amount, 2)},手续费：{round(other_cost, 2)}资金剩余：{round(self.cash, 2)}")
            self.stock_data.loc[index, "count"] = 0


    def order_out(self,tscode,date,percent = 1):
        self.force_sell(tscode, date)
       

    def __get_price(self,tscode,date):
        str_date = date.strftime("%Y%m%d")

        vals = self.stock_info[(self.stock_info["ts_code"] == tscode) &(self.stock_info["trade_date"] == int(str_date))]["close"].values
        if len(vals) == 0:
            return None
        else:
            return vals[0]

    def __get_price_high_low(self,tscode,date):
        str_date = date.strftime("%Y%m%d")

        return self.stock_info[(self.stock_info["ts_code"] == tscode) &(self.stock_info["trade_date"] == int(str_date))][["close","pre_close","high","low","open"]]

trader = Backtrader()
trader.start(days=180)
trader.income_table.to_csv("income.csv")