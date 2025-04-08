import pandas as pd
import datetime

import talib as ta

import matplotlib.pyplot as plt
import mplfinance as mpf

import lightgbm as lgb
from tdreader import TdxDailyBarReader 

BASE_PATH = "D:/TDX/vipdoc"

def draw_kline(df):

    # 调用make_marketcolors函数，定义K线颜色，'i'表示根据K线颜色
    mc = mpf.make_marketcolors(
                                up="red",  # 上涨K线的颜色
                                down="green",  # 下跌K线的颜色
                                edge='i',  # 蜡烛图箱体的颜色
                                volume='i',  # 成交量柱子的颜色
                                wick='i',  # 蜡烛图影线的颜色
                                )

    # 调用make_mpf_style函数，自定义图表样式 ，函数返回一个字典，查看字典包含的数据，按照需求和规范调整参数
    style = mpf.make_mpf_style(base_mpl_style="ggplot", marketcolors=mc,rc={'font.family': 'SimHei', 'axes.unicode_minus': 'False'})
    m = {1:1,0:None}
    add_plot=[
            #mpf.make_addplot(df['prd_val'].map(m), scatter=True, markersize=20, marker='^', color='r'),
            mpf.make_addplot(df['lable'].map(m), scatter=True, markersize=20, marker='v', color='g'),
            mpf.make_addplot(df[['dif',"dem"]]),
        ]
    
    
    # 开始绘图
    mpf.plot(data=df,
        type="candle",
        title="K线图",
        addplot=add_plot,
        ylabel="价格",
        style=style,
        volume=True,
        figratio=(20,14),
        figscale=1)



def prepare_stock_data(code):
    start_date = datetime.datetime.strptime("2018-01-01","%Y-%m-%d")

    company_info = pd.read_csv('./stock/company_info.csv', encoding='utf-8')
    company_info = company_info[company_info["ts_code"].str.contains("SZ|SH")]
    def JudgeST(x):
        if 'ST' in x:  # 如果存在ST则为1 否贼为0 有退市风险
            return 1
        else:
            return 0

    def date_id_map(x):
        return (x - start_date).days

    market_map = {'主板': 0, '创业板': 1, '北交所': 2, "科创板": 3}  # V

    exchange_map = {'SZSE': 0, 'SSE': 1, 'BSE': 2}  # V

    is_hs_map = {'S': 0, 'N': 1, 'H': 2, "NAN": 3}  # V

    company_info['is_ST'] = company_info['name'].apply(JudgeST)
    # 丢弃一些多余的信息
    company_info.drop(['symbol', 'fullname'], axis=1, inplace=True)

    company_info['market'] = company_info['market'].map(market_map)  # 转换编码  主板0 中小板 1
    company_info['exchange'] = company_info['exchange'].map(exchange_map)  # 转换编码  SZSE=深圳 SSE=上海 交易所
    company_info['is_hs'] = company_info['is_hs'].fillna("NAN").map(
        is_hs_map)




    reader = TdxDailyBarReader(BASE_PATH)
    def daily(code,start):
        market = code[7:].lower()
        symbol = code[:6]
        dayline = reader.get_df(BASE_PATH +"/"+market+"/lday/"+market+symbol+".day")

        dayline = dayline[dayline.index > start]
        dayline = dayline.reset_index()
        dayline.insert(loc=0,column="ts_code",value=code)
        dayline["amount"] = round(dayline["amount"]/1000,3)
        dayline["pre_close"] = dayline["close"].shift(1)
        return dayline


    tmp_list = []

    market_map = {'主板': 0, '创业板': 1, '北交所': 2, "科创板": 3}  # V
    exchange_map = {'SZSE': 0, 'SSE': 1, 'BSE': 2}  # V
    is_hs_map = {'S': 0, 'N': 1, 'H': 2, "NAN": 3}  # V

    for i in range(1):
        df = daily(code,start_date)
        company = company_info[company_info["ts_code"] == code]
        ts_code_id = company.index[0]
        df["ts_code_id"] = ts_code_id
        df["trade_date_id"] = df["trade_date"].apply(date_id_map)

        df['ts_date_id'] = (10000 + ts_code_id) * 10000 + df['trade_date_id']
        df["market"] = company["market"].values[0]
        df['is_ST']  = company["is_ST"].values[0]
        df['exchange']  = company["exchange"].values[0]
        df['is_hs'] = company['is_hs'].values[0]
        df["ma_5"] = ta.MA(df["close"],timeperiod=5)
        df["ma_10"] = ta.MA(df["close"],timeperiod=10)
        df["ma_20"] = ta.MA(df["close"],timeperiod=20)
        dif, dem, his = ta.MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)
        df["mac"] = his
        df["dif"] = dif
        df["dem"] = dem
        for i in range(30):
            n = i+1
            k = "close_shift_"+str(n)
            df[k] = df["close"].shift(n)

            df[k] = round((df["close"] - df[k])*100/df[k],2)

        df = df.sort_values("trade_date",ascending=False)
        df["mac_l"] = df["mac"].shift(1)
        df["open_transform"] = round((df["open"] - df['pre_close'])*100 / df['pre_close'],2)
        df["high_transform"] = round((df["high"] - df['pre_close']) *100/ df['pre_close'],2)
        df["low_transform"] = round((df["low"] - df['pre_close']) *100/ df['pre_close'],2)
        df["lable"] = (df["mac"] <  0) & (df["mac_l"] > 0)
        df["lable"] = df["lable"].astype("int")
        df = df.dropna()
        tmp_list.append(df)

    stock_days_info = pd.concat(tmp_list)
    stock_days_info = stock_days_info.set_index("trade_date")
    stock_days_info = stock_days_info.sort_index(ascending=True)
    return stock_days_info



def predic(data):
    def up_round(x):
        if x > 0.7:
            return 0.9
        return 0 
    feature_col = ["open_transform","high_transform","low_transform"]
    for i in range(30):
        feature_col.append('close_shift_{}'.format(i+1)) 

    g = lgb.Booster(model_file= "gdm.model")

    prd_col = ['open', 'high', 'low', 'close', 'pre_close', 'volume', 'amount', 'ts_code_id',"ma_5","ma_10","ma_20"] + feature_col
    prd_input = data[prd_col]
    prd_val = g.predict(prd_input.values, num_iteration=g.best_iteration)
    data["prd_val"] = prd_val
    data["prd_val"] = data["prd_val"].apply(up_round)

    return data


if __name__ == "__main__":
    code = '603838.SH' 

    df = prepare_stock_data(code)
    draw_kline(df.tail(160))
