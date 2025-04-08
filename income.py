import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import pandas as pd
from pandas.plotting import register_matplotlib_converters
from tdreader import TdxDailyBarReader
from datetime import datetime
register_matplotlib_converters()
chart_width = 0.88
##  图表布局规划
fig = plt.figure(figsize=(12, 15), facecolor=(0.82, 0.83, 0.85))
ax1 = fig.add_axes([0.05, 0.67, 0.88, 0.20])
ax2 = fig.add_axes([0.05, 0.49, 0.88, 0.13], sharex=ax1)

tdx_reader = TdxDailyBarReader('d:/TDX/vipdoc/')
income_data = pd.read_csv("income.csv")
df = tdx_reader.get_df('399300', 'sz')[["close"]]
df = df.reset_index()
df = df.rename(columns={"trade_date":"date"})
df["date"] = df['date'].apply(lambda x:x.strftime('%Y-%m-%d'))
df = pd.merge(income_data,df,how= "left",on=["date"])[["date","amount","rate","close"]]
df["base_rate"] = ((df["close"]/df["close"].head(1).max()) - 1)*100
df["date"] = df["date"].apply(lambda x: datetime.strptime(x,"%Y-%m-%d"))
df.set_index("date",inplace=True)
ams = df["amount"].values
back = []
m = ams[0]
for a in ams:
    back.append((a - m)/m)
    if a >= m:
        m = a
    pass
df["max"] =  back
ax1.set_title('income rate')
ax1.plot(df.index, df["base_rate"], linestyle='-',
         color=(0.4, 0.6, 0.8), alpha=0.85, label='Benchmark')

ax1.plot(df.index, income_data["rate"], linestyle='-',
         color=(0.8, 0.2, 0.0), alpha=0.85, label='Return')
ax1.set_ylabel('rate')

ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
underwater = df["max"]
ax2.set_title('max back: '+ str(round(df["max"].min()*100,2))+ " max lose :" +str(round(df["rate"].min(),2)) )
ax2.plot(underwater, label='underwater')
ax2.set_ylabel('Back Rate')
ax2.set_xlabel('date')
ax2.set_ylim(-1, 0)
ax2.fill_between(df.index, 0, underwater,
                     where= underwater < 0,
                     facecolor=(0.8, 0.2, 0.0), alpha=0.35)


plt.show()