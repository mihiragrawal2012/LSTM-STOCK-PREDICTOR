
from codecs import ignore_errors
from tkinter import N
from turtle import position
import numpy as np
import pandas as pd
import xlsxwriter
import requests 
import matplotlib.pyplot as plt
import math
def chunks(lst,n):
	for i in range (0,len(lst),n):
		yield(lst[i:i+n])

stonks=pd.read_csv('stockssp.csv')
from secrets import IEX_CLOUD_API_TOKEN
mcolumns = ['Ticker  ', 'Price ','Market Capitalization  ', 'Number Of Shares to Buy ']
symbol_groups=list(chunks(stonks['Ticker'],100))
final_dataframe = pd.DataFrame(columns=mcolumns)
sym_str=[]
for i in range (0,len(symbol_groups)):
	sym_str.append(','.join(symbol_groups[i]))

for str in sym_str:
#     print(symbol_strings)
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch/?types=quote&symbols={str}&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for sy in str.split(','):
        final_dataframe = final_dataframe.append(
                                        pd.Series([sy, 
                                                   data[sy]['quote']['latestPrice'], 
                                                   data[sy]['quote']['marketCap'], 
                                                   'N/A'], 
                                                  index = mcolumns), 
                                        ignore_index = True)

#calculating the number of shares to buy
portfolio_size=input('Enter the value of your portfolio: ')
try:
	val=float(portfolio_size)
except:
	print('Please enter an integer')
	portfolio_size=input('Enter the value of your portfolio: ')
	val=float(portfolio_size)
position_size=val/len(final_dataframe.index)
for i in range (0,len(final_dataframe.index)):
	 final_dataframe.loc[i,'Number Of Shares to Buy ']=math.floor(position_size/final_dataframe['Price '][i])

#Now we have to save the results as XLS file (MS EXCEL)
wr=pd.ExcelWriter('invest.xlsx', engine='xlsxwriter')
final_dataframe.to_excel(wr, sheet_name='invest',index = True)
background_color = '#0a0a23'
font_color = '#ffffff'
string_format = wr.book.add_format(
        {
            'font_color': font_color,
            'bg_color': background_color,
            'border':0
        }
    )
dollar_format = wr.book.add_format(
        {
            'num_format':'$0.00',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 0
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
wr.sheets['invest'].write('A1','Ticker',string_format)
wr.sheets['invest'].write('B1','Price',dollar_format)
wr.sheets['invest'].write('C1','Market Capitalizatin',dollar_format)
wr.sheets['invest'].write('D1','Number of Shares to Buy',integer_format)
column_formats = { 
		    'A':['Sr no',integer_format],
                    'B': ['Ticker', string_format],
                    'C': ['Price  ', dollar_format],
                    'D': ['Market Capitalization', dollar_format],
                    'E': ['Number of Shares to Buy', integer_format]
                    }

for column in column_formats.keys():
    wr.sheets['invest'].set_column(f'{column}:{column}', 20, column_formats[column][1])
    wr.sheets['invest'].write(f'{column}1', column_formats[column][0], string_format)
wr.save()