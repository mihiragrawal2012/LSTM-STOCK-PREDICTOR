#We will demonmstrate quantitative momentum strategy via this project
# we will select 'x' stocks with the highest momentum and create a 
#equal-weighted portfolio using those stocks like we did in the last project
import string
from textwrap import wrap
import numpy as np
import pandas as pd
from scipy import stats
from torch import true_divide
import xlsxwriter
from statistics import mean
from sklearn.metrics import confusion_matrix
import math
import requests
def chunks(lst,batch_partition):
	for i in range (0,len(lst),batch_partition):
		yield(lst[i:i+batch_partition])

from secrets import IEX_CLOUD_API_TOKEN
stonks=pd.read_csv('stockssp.csv')

#This was the first API call
sym = 'AAPL'
api_url = f'https://sandbox.iexapis.com/stable/stock/{sym}/stats?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url)
data=data.json()
#we need year1Changepercent
sym_groups=list(chunks(stonks['Ticker'],100))
strings_id=[]
for i in range(0,len(sym_groups)):
	strings_id.append(','.join(sym_groups[i]))
mcolumns = ['Ticker  ', 'Price ','One Year Price Return  ', 'Number Of Shares to Buy ']

dataf=pd.DataFrame(columns=mcolumns)
for ss in strings_id:
	data=requests.get(f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={ss}&token={IEX_CLOUD_API_TOKEN}')
	data=data.json()
	for sy in ss.split(','):
		dataf=dataf.append(
			pd.Series([
				sy,data[sy]['quote']['latestPrice'],
 				data[sy]['stats']['year1ChangePercent'],'N/A'
			],index=mcolumns),ignore_index=True)


#lets remove low momentum after sorting the dataframe by one year size return
dataf.sort_values('One Year Price Return  ',ascending=False,inplace=True)
dataf=dataf[:50]
#now reset the indices
dataf.reset_index(drop=True,inplace=True)

#Calculate the no of shares to buy
portf=input("Enter the size of your portfolio: ")
try :
	val =float(portf)
except ValueError:
	print('Please enter a number, integers and float values only accepted')
	portf=input("Enter the size of your portfolio: ")
	val=float(portf)
position_size=float(val)/len(dataf.index)

for i in range (0,len(dataf)):
	dataf.loc[i,'Number Of Shares to Buy ']=math.floor(position_size/dataf.loc[i,'Price '])


#Improvising on the momentum strategies

"""
Differentiating between high and low quality momentum strategies
High Quality momentum is preferred as low quality momentum shifts may be 
a result of short-time news or positives, which are unlikely to be repeated 
in future. Also Low quality momentum shifts are highly unpredictable.

Our current strategy based on One-Year price returns cannot 
efficiently differentiate between a high and low quality momentum change
so will analyse our portfolio based on
returns during various shorter spans of time
namely
One-Year Price Returns
One-Month Price Returns
Three-Month Price Returns
Six-Month Price Returns

We will, at last also compare the difference in
yearly performance (last passed year,of course) of both our
portfolios .
"""
#We will modify our dataframe

hqm_cols=['Ticker ','Price ','Number of Shares to Buy ',
	'One-Year Price Returns ','One-Year Returns Percentile ',
	'Six-Month Price Returns ','Six-Month Returns Percentile ',
	'Three-Month Price Returns ','Three-Month Returns Percentile ',
	'One-Month Price Returns ','One-Month Returns Percentile ','HQM Score ']
hqm_df=pd.DataFrame(columns=hqm_cols)
convert_enc=lambda x:0 if x is None else x
for ss in strings_id:
	data=requests.get(f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={ss}&token={IEX_CLOUD_API_TOKEN}')
	data=data.json()
	for syl in ss.split(','):
		hqm_df=hqm_df.append(pd.Series([syl,data[syl]['quote']['latestPrice'],
                                                   'N/A',
                                                   convert_enc(data[syl]['stats']['year1ChangePercent']),
                                                   'N/A',
                                                   convert_enc(data[syl]['stats']['month6ChangePercent']),
                                                   'N/A',
                                                   convert_enc(data[syl]['stats']['month3ChangePercent']),
                                                   'N/A',
                                                   convert_enc(data[syl]['stats']['month1ChangePercent']),
                                                   'N/A','N/A'
                                                   ], 
                                                  index = hqm_cols), 
                                        ignore_index = True)

time_p=	['One-Year','Six-Month','Three-Month','One-Month']
for row in hqm_df.index:
	for tim in time_p:
		hqm_df.loc[row, f'{tim} Returns Percentile '] = stats.percentileofscore(hqm_df[f'{tim} Price Returns '], hqm_df.loc[row, f'{tim} Price Returns '])/100

"""now we will calculate high-quality mean scores
they will be the arithmetic means of the four momentum percentile 
scores that we calculated in the last section
"""
for row in hqm_df.index:
	mom_percentiles=[]
	for tim in time_p:
		mom_percentiles.append(hqm_df.loc[row,f'{tim} Returns Percentile '])
		hqm_df.loc[row,'HQM Score ']=mean(mom_percentiles)
 
hqm_df.sort_values('HQM Score ',ascending=False,inplace=True)
hqm_df=hqm_df[:50]
#now reset the indices
hqm_df.reset_index(drop=True,inplace=True)
position_size=float(val)/len(hqm_df.index)
for i in hqm_df.index:
	hqm_df.loc[i,'Number of Shares to Buy ']=math.floor(position_size)/hqm_df.loc[i,'Price ']

"""
Now we have the results of both the anaylses
the simple momentum based strategy and
the high quality momentum based-sorted strategy
"""


wr=pd.ExcelWriter('Momentum-Investing.xlsx',engine='xlsxwriter')
hqm_df.to_excel(wr,sheet_name='HQM-Momentum Strategy',index=False)
dataf.to_excel(wr,sheet_name='UnFiltered Momentum',index=False)
background_color = '#ffffff'
font_color = '#0a0a23'
string_format = wr.book.add_format(
        {
            'font_color': font_color,
            'bg_color': background_color,
            'border':1
        }
    )
dollar_format = wr.book.add_format(
        {
            'num_format':'$0.00',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )
integer_format = wr.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
)
percent_format = wr.book.add_format(
        {
            'num_format':'0.0%',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
	}
)
float_template = wr.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
)


column_formats={
	'A':['Ticker ',string_format],
	'B':['Price ',dollar_format],
	'C':['Number of Shares to Buy ',integer_format],
	'D':['One-Year Price Returns ',percent_format],
	'E':['One-Year Returns Percentile ',percent_format],
	'F':['Six-Month Price Returns ',percent_format],
	'G':['Six-Month Returns Percentile ',percent_format],
	'H':['Three-Month Price Returns ',percent_format],
	'I':['Three-Month Returns Percentile ',percent_format],
	'J':['One-Month Price Returns ',percent_format],
	'K':['One-Month Returns Percentile ',percent_format],
	'L':['HQM Score ',percent_format]
}

column_formats2={
	'A':['Ticker  ',string_format],
	'B': ['Price ',dollar_format],
	'C':['One Year Price Return  ',percent_format],
	'D':['Number Of Shares to Buy ',integer_format]
}
for col in column_formats.keys():
	wr.sheets['HQM-Momentum Strategy'].set_column(f'{col}:{col}',22,column_formats[col][1])
	wr.sheets['HQM-Momentum Strategy'].write(f'{col}1',column_formats[col][0],column_formats[col][1])
for col in column_formats2.keys():
	wr.sheets['UnFiltered Momentum'].set_column(f'{col}:{col}',22,column_formats2[col][1])
	wr.sheets['UnFiltered Momentum'].write(f'{col}1',column_formats2[col][0],column_formats2[col][1])
wr.save()
