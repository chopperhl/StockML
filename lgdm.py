


import pandas as pd
import tqdm
import datetime
from tdreader import TdxDailyBarReader

import os
import numpy as np
import talib as ta

import lightgbm as lgb
from sklearn import metrics
import pandas_market_calendars as mcal
from config import CHOOSE_RATE_H,CHOOSE_RATE_L,L,H,train_col,get_st_symbol
MODEL_FILE  = "gdm.model" 


def prepare_stock_data(predic_days = -1):

    company_info = pd.read_csv('./stock/company_info.csv', encoding='utf-8')
    company_info = company_info[company_info["ts_code"].str.contains("SZ|SH")]
    
    m = company_info["industry"].unique()
    industry_map = dict(zip(m,range(len(m))))
    
    market_map = {'主板': 0, '创业板': 1, '北交所': 2, "科创板": 3}  # V
    exchange_map = {'SZSE': 0, 'SSE': 1, 'BSE': 2}  # V
    is_hs_map = {'S': 0, 'N': 1, 'H': 2, "NAN": 3}  # V
    
    company_info['market'] = company_info['market'].map(market_map)  # 转换编码  主板0 中小板 1
    company_info['exchange'] = company_info['exchange'].map(exchange_map)  # 转换编码  SZSE=深圳 SSE=上海 交易所
    company_info["industry"] = company_info["industry"].map(industry_map)
    company_info['is_hs'] = company_info['is_hs'].fillna("NAN").map(is_hs_map)


    ts_codes = company_info["ts_code"]

    BASE_PATH = f"{os.getcwd()}/../../TDX/vipdoc"

    reader = TdxDailyBarReader(BASE_PATH)
    def daily(code,days):
        market = code[7:].lower()
        symbol = code[:6]
        dayline = reader.get_df(symbol,market,days)

        dayline = dayline.reset_index()
        dayline.insert(loc=0,column="ts_code",value=code)
        dayline = dayline.sort_values("trade_date",ascending=True)
        dayline["amount"] = round(dayline["amount"]/1000,3)
        dayline["pre_close"] = dayline["close"].shift(1)
        return dayline


    tmp_list = []

    def to_days(x):
        if pd.isnull(x):
            return 0
        return int(x.days - 1)


    today = daily("000001.SZ",1)["trade_date"]
    endday = today + datetime.timedelta(10)
    sse = mcal.get_calendar("SSE")
    next_date = sse.schedule(start_date=today.values[0],end_date=endday.values[0]).index[1]
    holidays = (next_date - today).apply(lambda x: x.days -1).values[0]
    for code in tqdm.tqdm(ts_codes):
        if predic_days < 0:
            df = daily(code,-1)
        else:
            df = daily(code,predic_days+43)
        if (predic_days > 100 or predic_days == -1) and len(df) < 100:
            continue

        company = company_info[company_info["ts_code"] == code]
        ts_code_id = company.index[0]
        df["ts_code_id"] = ts_code_id
        df["date_type"] =  (df["trade_date"] - df["trade_date"].shift(1)).apply(to_days)

        df["market"] = company["market"].values[0]
        df['exchange']  = company["exchange"].values[0]
        df['is_hs'] = company['is_hs'].values[0]
        df['industry'] = company['industry'].values[0]

        df["rsi"] = ta.RSI(df["close"],timeperiod=6)
        dif, dem, his = ta.MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)
        df["macd"] = his
        for i in range(10):
            k = "macd_"+str(i+1)
            df[k] = his.shift(i+1)
        for i in range(30):
            k = "close_shift_"+str(i+1)
            df[k] = df["close"].shift(i+1)

            df[k] = round((df["close"] - df[k])*100/df[k],2)
        df = df.sort_values("trade_date",ascending=False)
        df["n_date_type"] =  (df["trade_date"].shift(1)-df["trade_date"]).apply(to_days)
        df.loc[df.index.max(),"n_date_type"] = holidays
        df["open_transform"] = round((df["open"] - df['pre_close'])*100 / df['pre_close'],2)
        df["high_transform"] = round((df["high"] - df['pre_close']) *100/ df['pre_close'],2)
        df["low_transform"] = round((df["low"] - df['pre_close']) *100/ df['pre_close'],2)
        if predic_days == -1:
            for i in range(6):
                k = "h"+str(i+1)
                df[k] = df["high"].shift(i+1)
            df["lable"] = ((df["h2"] > H*df["close"]) & (df["low"].shift(2).rolling(1).min() > L*df["close"] )) | ((df["h3"] > H*df["close"]) & (df["low"].shift(2).rolling(2).min() > L*df["close"] )) |((df["h4"] > H *df["close"]) & (df["low"].shift(2).rolling(3).min() > L*df["close"] )) | ((df["h5"] > H *df["close"]) & (df["low"].shift(2).rolling(4).min() > L*df["close"] )) | ((df["h6"] > H *df["close"]) & (df["low"].shift(2).rolling(5).min() > L*df["close"] ))  
            df["lable"] = (df["lable"] == True) & (df["close_shift_1"] < 9.85)
            df["lable"] = (df["lable"] == True) & (df["rsi"] < 25)
            df["lable"] = df["lable"].astype("int")
            df = df.dropna()
            df = df.drop(columns=["h1","h2","h3","h4","h5","h6"])
        else:
            df = df.dropna()
        tmp_list.append(df)

    stock_days_info = pd.concat(tmp_list)
    stock_days_info = stock_days_info.reset_index(drop=True)
    return stock_days_info



def training(stock_info_copy,trn_col):
    print(" start traning...")
    """
    sample_data = stock_info_copy.sample(axis=0, frac=1)
    sample_data.reset_index()
    choose_table = sample_data.sample(axis=0, frac=0.1)
    train_table = sample_data[~sample_data.index.isin(choose_table.index)]
    """
    choose_table = stock_info_copy[stock_info_copy["trade_date"] > "2024-06-01"]
    train_table = stock_info_copy[stock_info_copy["trade_date"] <="2024-06-01"]

    trn = train_table[trn_col].values
    trn_label = train_table["lable"].values

    val = choose_table[trn_col].values
    val_label = choose_table["lable"].values

    params = {
        "device" : "gpu",
        'learning_rate': 1e-3,  # 学习率
        'boosting_type': 'gbdt',  # 提升类型，这里使用的是'gbdt'，即传统的梯度提升决策树。
        'objective': 'binary',  # 分类问题 这里是'binary'，表示是二分类问题。
        'metric': 'mse',  # mse 性能评估方式，这里使用的是'mse'（均方误差），通常用于回归任务；对于分类任务可能更常见的是使用'binary_logloss'（二分类对数损失）。
        'num_leaves': 128,  # 树中叶子的数量，这里设置为128。叶子数量越多，模型可能越复杂，能学习到更细致的数据特征，但也可能导致过拟合。
        'feature_fraction': 0.8,  # 在每次迭代中，随机选择80%的特征用于训练，有助于加速训练和防止过拟合。
        'bagging_fraction': 0.8,  # 每次迭代时用的数据比例，这里设置为80%。即每次构建树时，从所有训练数据中随机抽样80%的样本来进行训练，可以防止模型过拟合。
        'bagging_freq': 5,  # 频率为5，意味着每5次迭代执行一次bagging。 随机抽样
        'seed': 1,  # 用于确保模型可复现。设置为1。
        'bagging_seed': 1,  # bagging的随机数种子，设置为1。
        'lambda_l1': 0.1,  # L1正则化系数，用于减少模型的复杂度，并进行特征选择，设置为0.1。
        'feature_fraction_seed': 7,  # 控制特征抽样的随机种子，设置为7。
        'min_data_in_leaf': 20,  # 叶子节点上的最小数据量，这里为20，可以用于防止树在数据量少的叶子节点上生长，从而防止过拟合。
        'nthread': 10,  # 使用的线程数，-1表示使用全部线程。
        'verbose': -1  # 是否显示详细输出信息，-1表示不输出任何结果。
    }

    trn_data = lgb.Dataset(trn, trn_label)
    val_data = lgb.Dataset(val, val_label)
    num_round = 6000  # 迭代次数
    if os.path.exists(MODEL_FILE):
        clf = lgb.Booster(model_file=MODEL_FILE)
    else:
        clf = lgb.train(params, trn_data, num_round, valid_sets=[trn_data, val_data])
        # valid_sets参数设定了验证数据集，用来在训练过程中评估模型的表现并进行早停（early stopping）以防过拟合。
        clf.save_model(MODEL_FILE)

    prd_val = clf.predict(val,
                          num_iteration=clf.best_iteration)  # 验证集预测。 clf.best_iteration 指定使用表现最好的迭代次数进行预测，这通常是通过早停得到的。
    def up_round(x):
        if x > CHOOSE_RATE_L and x < CHOOSE_RATE_H:
            return 1
        return 0

    # 验证
    prd_val_final = np.round(prd_val)  # 获取验证集的label
    print(metrics.accuracy_score(val_label, prd_val_final))
    pp = pd.DataFrame({"p":prd_val,"l":val_label})
    pp["p"] = pp["p"].apply(up_round)
    n1 = len(pp[(pp["p"]  == 1 ) & (pp["l"] == 1)])  # 两者都相同为1的
    n2 = len(pp[pp["p"] == 1])  # 总体的
    print(f'{n1}/{n2}')
    print('sensitivity:%.3f' % (n1 / n2))  # 占比。 准确率
FORCE_TRAINING = False
if __name__ == '__main__':

    trn_col = train_col()

    if  os.path.exists(MODEL_FILE) and not FORCE_TRAINING:
        g = lgb.Booster(model_file=MODEL_FILE)
        data = prepare_stock_data(predic_days= 1)
        #data = prepare_stock_data(predic_days= 400)
        prd_input = data[trn_col]

        prd_val = g.predict(prd_input.values,
                            num_iteration=g.best_iteration)  # 验证集预测。 clf.best_iteration 指定使用表现最好的迭代次数进行预测，这通常是通过早停得到的。
        data["prd_val"] = prd_val

        buy_ts = data[["ts_code", "trade_date", "open", "close", "close_shift_1","n_date_type","prd_val"]].sort_values("prd_val", ascending=False)
        ts_name = pd.read_csv("./stock/company_info.csv")[["ts_code", "name"]]
        buy_ts = buy_ts.merge(ts_name, how="left", on="ts_code")
        st = get_st_symbol()
        buy_ts = buy_ts[~buy_ts["ts_code"].isin(st)]
        buy_ts = buy_ts[buy_ts["trade_date"] == buy_ts["trade_date"].max()]
        if buy_ts["prd_val"].max() <= CHOOSE_RATE_L or buy_ts["prd_val"].max() >= CHOOSE_RATE_H:
            print(buy_ts.head(5))
            print("No stock to buy")
        else:
            buy_ts = buy_ts[(buy_ts["prd_val"] > CHOOSE_RATE_L) &(buy_ts["prd_val"] < CHOOSE_RATE_H)]
            #buy_ts[["trade_date","ts_code"]].to_csv("buy_ts.csv")
            print(buy_ts)
    else:
        p_stock_data =  prepare_stock_data()
        print(p_stock_data.head(10))
        training(p_stock_data,trn_col)

