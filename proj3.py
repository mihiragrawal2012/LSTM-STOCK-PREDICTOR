import numpy as np
import pandas as pd
import xlsxwriter
import requests
from torch import tril_indices, triplet_margin_loss
from sklearn.metrics import top_k_accuracy_score
import math
from scipy.stats import percentileofscore as sco

from statistics import mean

from secrets import IEX_CLOUD_API_TOKEN
stonks = pd.read_csv('stockssp.csv')


def chunks(list1, batch_size):
    for i in range(0, len(list1), batch_size):
        yield(list1[i:i+batch_size])


"""
The first value metric we will use is the earnings to value ratio,
Like the previous project we will add more composite metrics later on.

For calculating our value metric we will use the annual earnings for 
each S&P 500 index

IEX cloud natively provides the price to index ratio now
"""

sym1 = 'AAPL'
single_url = f'https://sandbox.iexapis.com/stable/stock/{sym1}/quote?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(single_url)
data = data.json()

price = data['latestPrice']
per = data['peRatio']

# We can also use trailing earnings
sym_batch = list(chunks(stonks['Ticker'], 100))
sym_str = []

for i in range(0, len(sym_batch)):
    sym_str.append(','.join(sym_batch[i]))

mcolumns = ['Ticker ', 'Price ',
            'Price-to-Earnings Ratio ', 'Number of Shares to Buy ']
dataf = pd.DataFrame(columns=mcolumns)
def convert_enc(x): return 0 if x is None else x


def run_e(x, y):
    if (y != 0):
        return x/y
    else:
        return np.NaN


for i in sym_str:
    data = requests.get(
        f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=quote&symbols={i}&token={IEX_CLOUD_API_TOKEN}')
    data = data.json()
    for j in i.split(','):
        dataf = dataf.append(
            pd.Series([j,
                       convert_enc(data[j]['quote']['latestPrice']),
                       convert_enc(data[j]['quote']['peRatio']),
                       'Nil'
                       ],
                      index=mcolumns),
            ignore_index=True
        )

"""
We will first filter out glamour stocks from our data.
Glamour stocks are the exact polar opposites of value stocks,
i.e. , the stocks that trade way above their intrinsic value.
"""

"""We do not want any stocks in our portfolio with negative 
price to earnings ratio"""
dataf.sort_values('Price-to-Earnings Ratio ', inplace=True)
dataf = dataf[dataf['Price-to-Earnings Ratio '] > 0]
dataf = dataf[:50]
dataf.reset_index(drop=True, inplace=True)

# calculating the number of shares to buy

portf = input("Enter the size of your portfolio: ")
try:
    val = float(portf)
except ValueError:
    print('Please enter a number, integers and float values only accepted')
    portf = input("Enter the size of your portfolio: ")
    val = float(portf)
position_size = float(val)/len(dataf.index)

for i in dataf.index:
    dataf.loc[i, 'Number of Shares to Buy '] = math.floor(
        position_size/dataf.loc[i, 'Price '])

"""
Above was a naive implementation which only used price to earnings ratio
to invest our portfolio, now we will build a composite strategy using a variety of metrics
to reinforce and strengthen our existing strategy,
The metrics we will use will be :
Price-to-Earnings Ratio,
Price-to-Book Ratio,
Price-to-Sales Ratio,
Enterprise Value/EBITDA 
(here EBIDTA stands for Earnings Before Interest,Taxes,Depreciation,Amortization)
Enterprise Value divided by Gross Profit
"""

"""
Here we will create a batch API call not for pulling the data 
for various stocks at once, but for pulling all the metrics related to
a particular stock at once, as all the metrics required are parts of 
different API enpoints.So technically, we will create a batch call of batch calls for
multiple stocks.
"""

data = requests.get(
    f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=advanced-stats,quote&symbols={sym1}&token={IEX_CLOUD_API_TOKEN}')
data = data.json()

pe_ratio = data[sym1]['quote']['peRatio']
pb_ratio = data[sym1]['advanced-stats']['priceToBook']
ps_ratio = data[sym1]['advanced-stats']['priceToSales']
ent_value = data[sym1]['advanced-stats']['enterpriseValue']
ebitda = data[sym1]['advanced-stats']['EBITDA']
ev_ebitda = ent_value/ebitda
gross_profit = data[sym1]['advanced-stats']['grossProfit']
ev_gp = ent_value/gross_profit

adva_columns = [
    'Ticker ',
    'Price ',
    'Number of Shares to Buy ',
    'Price-to-Earnings Ratio ',
    'Price-Earnings Percentile ',
    'Price-to-Book-Value Ratio ',
    'Price-Book-Value Percentile ',
    'Price-to-Sales Ratio ',
    'Price-Sales Percentile ',
    'EV/EBITDA Ratio ',
    'EV/EBITDA Percentile ',
    'EV/GP Ratio ',
    'EV/GP Percentile ',
    'RV Score '
]
adva_df = pd.DataFrame(columns=adva_columns)

for i in sym_str:
    data = requests.get(
        f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={i}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}')
    data = data.json()
    for j in i.split(','):
        ent_value = data[j]['advanced-stats']['enterpriseValue']
        ebitda = data[j]['advanced-stats']['EBITDA']
        gross_profit = data[j]['advanced-stats']['grossProfit']
        try:
            ev_ebitda = ent_value/ebitda
        except TypeError:
            ev_ebitda = np.NaN
        try:
            ev_gp = ent_value/gross_profit
        except TypeError:
            ev_gp = np.NaN

        adva_df = adva_df.append(
            pd.Series([
                j, convert_enc(data[j]['quote']['latestPrice']),
                'N/A',
                convert_enc(data[j]['quote']['peRatio']),
                'N/A',
                convert_enc(data[j]['advanced-stats']['priceToBook']),
                'N/A',
                convert_enc(data[j]['advanced-stats']['priceToSales']),
                'N/A',
                ev_ebitda,
                'N/A',
                ev_gp,
                'N/A',
                'N/A'
            ], index=adva_columns), ignore_index=True
        )

"""
We encountered a lot of missing data, 
so we are dealing with here
, we will fill the missing data with the average values 
of all non null data in that particular column of the dataframe
"""
for col in ['Price-to-Earnings Ratio ',
            'Price-to-Book-Value Ratio ',
            'Price-to-Sales Ratio ',
            'EV/EBITDA Ratio ',
            'EV/GP Ratio ']:
    adva_df[col].fillna(adva_df[col].mean(), inplace=True)


# This should return an empty dataframe

"""
Now we will move on to calculating value percentiles
"""
dict_ref = {
    'Price-to-Earnings Ratio ': 'Price-Earnings Percentile ',
    'Price-to-Book-Value Ratio ': 'Price-Book-Value Percentile ',
    'Price-to-Sales Ratio ': 'Price-Sales Percentile ',
    'EV/EBITDA Ratio ': 'EV/EBITDA Percentile ',
    'EV/GP Ratio ': 'EV/GP Percentile '
}
for j in adva_df.index:
    for i in dict_ref.keys():
        adva_df.loc[j, dict_ref[i]] = sco(adva_df[i], adva_df.loc[j, i])/100

for j in adva_df.index:
    value_per = []
    for i in dict_ref.keys():
        value_per.append(adva_df.loc[j, dict_ref[i]])
    adva_df.loc[j, 'RV Score '] = mean(value_per)

adva_df.sort_values('RV Score ', inplace=True)
adva_df = adva_df[:50]
adva_df.reset_index(drop=True, inplace=True)

# Now we calculate the 50 best stocks to buy
position_size = float(val)/len(adva_df.index)

for i in adva_df.index:
    adva_df.loc[i, 'Number of Shares to Buy '] = math.floor(
        position_size/adva_df.loc[i, 'Price '])

wr = pd.ExcelWriter('Value-Based Investing.xlsx', engine='xlsxwriter')
adva_df.to_excel(wr, sheet_name='Composite-Values', index=False)
dataf.to_excel(wr, sheet_name='Price-Earnings', index=False)

background_color = '#ffffff'
font_color = '#0a0a23'
string_format = wr.book.add_format(
    {
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)
dollar_format = wr.book.add_format(
    {
        'num_format': '$0.00',
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)
integer_format = wr.book.add_format(
    {
        'num_format': '0',
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)
percent_format = wr.book.add_format(
    {
        'num_format': '0.0%',
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)
float_template = wr.book.add_format(
    {
        'num_format': '0',
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)

column_formats = {
    'A': ['Ticker ', string_format],
    'B': ['Price ', dollar_format],
    'D': ['Number of Shares to Buy ', integer_format],
    'E': ['Price-to-Earnings Ratio ', float_template],
    'F': ['Price-Earnings Percentile ', percent_format],
    'G': ['Price-to-Book-Value Ratio ', float_template],
    'H': ['Price-Book-Value Percentile ', percent_format],
    'I': ['Price-to-Sales Ratio ', float_template],
    'J': ['Price-Sales Percentile ', percent_format],
    'K': ['EV/EBITDA Ratio ', float_template],
    'L': ['EV/EBITDA Percentile ', percent_format],
    'M': ['EV/GP Ratio ', float_template],
    'N': ['EV/GP Percentile ', percent_format],
    'O': ['RV Score ', percent_format]
}

col_f = {
    'A': ['Ticker ', string_format],
    'B': ['Price ', dollar_format],
    'C': ['Price-to-Earnings Ratio ', float_template],
    'D': ['Number of Shares to Buy ', integer_format]
}
for i in column_formats.keys():
    wr.sheets['Composite-Values'].set_column(
        f'{i}:{i}', 22, column_formats[i][1])
    wr.sheets['Composite-Values'].write(f'{i}1',
                                        column_formats[i][0], column_formats[i][1])
for i in col_f.keys():
    wr.sheets['Price-Earnings'].set_column(f'{i}:{i}', 22, col_f[i][1])
    wr.sheets['Price-Earnings'].write(f'{i}1', col_f[i][0], col_f[i][1])

wr.save()
