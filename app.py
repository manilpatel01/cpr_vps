from collections import namedtuple
from email.mime import application
import string
from this import s
from unittest import skip
import pandas as pd
from flask import Flask, redirect, render_template,request, url_for,send_file
from truedata_ws.websocket.TD import TD
import datetime
from datetime import date,timedelta
from dateutil.relativedelta import relativedelta, FR
import sqlite3
from ast import literal_eval
import webbrowser
import time

username = 'tdws215'
password = 'vinay@215' 

td_app = TD(username, password, live_port=None)
# last_updated_day = datetime.date.today()-timedelta(2)
# last_updated_week = datetime.date.today()-timedelta(2)
# last_updated_month = datetime.date.today()-timedelta(2)

conn = sqlite3.connect('stocks_data.db', check_same_thread=False,detect_types=sqlite3.PARSE_DECLTYPES)
cur = conn.cursor()

data = pd.DataFrame()
screener1D = pd.DataFrame()
screener2D = pd.DataFrame()
screener3D = pd.DataFrame()
screener1W = pd.DataFrame()
screener2W = pd.DataFrame()
screener3W = pd.DataFrame()
screener1M = pd.DataFrame()
screener2M = pd.DataFrame()
screener3M = pd.DataFrame()
screener4D = pd.DataFrame()
screener4W = pd.DataFrame()
screener4M = pd.DataFrame()
intraday = pd.DataFrame()
DateTable = pd.DataFrame()

cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='DateTable' ''')

if cur.fetchone()[0]!=1: 
    dataD={'Name':['LastDay','LastWeek','LastMonth'],'Dates':[datetime.date(2000,8,5),datetime.date(2000,8,5),datetime.date(2000,8,5)]}
    DateTable=pd.DataFrame(dataD)
    print("Does not exist")
    print(DateTable)
    DateTable.to_sql("DateTable",conn,index=True)


symbol_df = pd.read_csv("stocks.csv")
symbol = list(symbol_df['Symbol'])
# symbol = ['AARTIIND','ABB','ABBOTINDIA','ABCAPITAL','ABFRL','ACC','ADANIENT','ADANIPORTS','ALKEM','AMARAJABAT','AMBUJACEM','APLLTD',
# 'APOLLOHOSP','APOLLOTYRE','ASHOKLEY','ASIANPAINT','ASTRAL','ATUL','AUBANK','AUROPHARMA','AXISBANK','BAJAJ-AUTO','BAJAJFINSV',
# 'BAJFINANCE','BALKRISIND','BALRAMCHIN','BANDHANBNK','BANKBARODA','BATAINDIA','BEL','BERGEPAINT','BHARATFORG','BHARTIARTL','BHEL',
# 'BIOCON','BOSCHLTD','TCS','TECHM','TITAN','TORNTPHARM','TORNTPOWER','TRENT','TVSMOTOR','UBL','ULTRACEMCO','UPL','VEDL',
# 'VOLTAS','WHIRLPOOL','WIPRO','ZEEL']
# symbol = ['ALKEM']



ADR_bars = 5
CPR_width_bars = 20
minADR = .50
minCPR = 1

def pivot(h,l,c):
    return round(((h+l+c)/3),2)

def bc(h,l):
    return round(((h+l)/2),2)

def tc(p,bc):
    return round(((p-bc)+p),2)

def R1(p,l):
    return round(((2*p)-l),2)

def R2(p,h,l):
    return round(p+h-l,2)

def S1(p,h):
    return round((2*p)-h,2) 

def S2(p,h,l):
    return round(p-h+l,2) 

def CPR_width(p,tc,bc):
    return round(((abs(tc-bc)/p)*100),2)

def H3(h,l,c):
    return round((0.275*(h-l))+c,2)

def L3(h,l,c):
    return round(c-(0.275*(h-l)),2)

def daily_fetch_data(num):
    global data
    data = pd.DataFrame(None)

    if (num == 1 or num == 2 or num ==4) :
        for i in symbol:
            hist_data = td_app.get_n_historical_bars(i, no_of_bars = 1, bar_size='EOD')
            data = data.append(hist_data)
        data.drop(['v', 'oi','time'],axis=1,inplace=True)
        data.insert(0, "symbol", symbol)
        # data.insert(1, "ticker", symbol)
        data = data.set_index('symbol')

    elif num == 3:
        for i in symbol:
            temp = pd.DataFrame()
            hist_data = td_app.get_n_historical_bars(i, no_of_bars = 128)
            temp = temp.append(hist_data)
            temp = temp.set_index('time')
            temp = temp.resample('128m').agg({
                'o': lambda s: s[0],
                'h': lambda df: df.max(),
                'l': lambda df: df.min(),
                'c': lambda df: df[-1],
            })
            data = data.append(temp)
        data.insert(0, "symbol", symbol)
        # data.insert(1, "ticker", symbol)
        data = data.set_index('symbol')

def weekly_fetch_data(num):
    global data
    today = datetime.date.today()
    idx = (today.weekday()+1) % 7
    dateIdx = datetime.date.today().weekday()
    mon=None
    sat=None

    if dateIdx != 4:
        if idx<6: 
            mon = today - datetime.timedelta(6+idx)
            sat = today - datetime.timedelta(7+idx-6)
        else:
            mon = today - datetime.timedelta(5)
            sat = today

    else:
        mon = today - datetime.timedelta(4)
        sat = today + datetime.timedelta(1)

    data = pd.DataFrame(None)

    for i in symbol:
        hist_data_4 = td_app.get_historic_data(i, start_time=mon,end_time=sat, bar_size='EOD')
        if len(hist_data_4)>0:
            temp = pd.DataFrame(hist_data_4)
            temp = temp.set_index('time')
            temp = temp.resample('1W').agg({
                'o': lambda s: s[0],
                'h': lambda df: df.max(),
                'l': lambda df: df.min(),
                'c': lambda df: df[-1],
            })
            data = data.append(temp)
    
    data.insert(0, "symbol", symbol)
    # data.insert(1, "ticker", symbol)
    data = data.set_index('symbol')

def monthly_fetch_data(num):
    global data
    current_day = datetime.date.today()
    last_date_of_month = current_day + relativedelta(month=datetime.date.today().month+1, day=1, days=-1)
    
    if current_day != last_date_of_month:
        last_date = current_day.replace(day=1) - timedelta(days=1)
        start_date = current_day.replace(day=1) - timedelta(days=last_date.day)
    else:
        last_date = current_day
        start_date = current_day + relativedelta(month=current_day.month, day=1)

    data = pd.DataFrame(None)
    for i in symbol:
        hist_data_4 = td_app.get_historic_data(i, start_time=start_date,end_time=last_date, bar_size='EOD')
        if len(hist_data_4)>0:
            temp = pd.DataFrame(hist_data_4)
            temp = temp.set_index('time')
            temp = temp.resample('1M').agg({
                'o': lambda s: s[0],
                'h': lambda df: df.max(),
                'l': lambda df: df.min(),
                'c': lambda df: df[-1],
            })
            data = data.append(temp)
    data.insert(0, "symbol", symbol)
    # data.insert(1, "ticker", symbol)
    data = data.set_index('symbol')

def intraday_fetch_data(total,fsymbol):
    global intraday
    if total == 377:
        intraday = pd.DataFrame(None)
        for i in fsymbol:
            data = pd.DataFrame()
            hist_data = td_app.get_n_historical_bars(i, no_of_bars = 1, bar_size='EOD')
            data = data.append(hist_data)
            intraday = intraday.append(data)
        intraday.insert(0, "symbol", fsymbol)
        intraday = intraday.set_index('symbol')
        print('Intraday' + str(total) , intraday)
    
    elif total == 475:
        intraday = pd.DataFrame(None)
        for i in fsymbol:
            hist_data = td_app.get_n_historical_bars(i, no_of_bars = 475)
            temp = pd.DataFrame(hist_data)
            if temp.shape[0]>0:
                temp = temp.set_index('time')
                temp = temp.resample('1W').agg({
                    'o': lambda s: s[0],
                    'h': lambda df: df.max(),
                    'l': lambda df: df.min(),
                    'c': lambda df: df[-1],
                })
                intraday = intraday.append(temp)
        intraday.insert(0, "symbol", fsymbol)
        intraday = intraday.set_index('symbol')
        print('Intraday' + str(total) , intraday)

    else:
        intraday = pd.DataFrame(None)
        print(fsymbol)
        for i in fsymbol:
            hist_data = td_app.get_n_historical_bars(i, no_of_bars = total)
            temp = pd.DataFrame(hist_data)
            if temp.shape[0]>0:
                temp = temp.set_index('time')
                temp = temp.resample('3D').agg({
                    'o': lambda s: s[0],
                    'h': lambda df: df.max(),
                    'l': lambda df: df.min(),
                    'c': lambda df: df[-1],
                })
                intraday = intraday.append(temp)
                # print(i,temp)
        intraday.insert(0, "symbol", fsymbol)
        intraday = intraday.set_index('symbol')
        print('Intraday' + str(total) , intraday)



def get_adr():
    ADR_list = []
    for i in symbol:
        daily_range = []
        hist_data_3 = td_app.get_n_historical_bars(i, no_of_bars = ADR_bars, bar_size='EOD')
        newdf = pd.DataFrame.from_dict(hist_data_3)
        for column in range(len(newdf)):      
            daily_range.append(newdf["h"][column]-newdf["l"][column])
        adr = round((sum(daily_range)/ADR_bars)/100,4)
        print(i,adr)
        ADR_list.append(adr)
    return ADR_list

def get_weekly_adr():
    today = datetime.date.today()
    # tempsat = dt.strptime("29/01/22",'%d/%m/%y')
    # print(tempsat.date())
    idx = (today.weekday()+1) % 7 # MON = 0, SUN = 6 -> SUN = 0 .. SAT = 6
    ADR_list = []
    count = 0
    for s in symbol:
        count +=1
        fiveWeek = pd.DataFrame()
        for i in range(ADR_bars):
            days = 7*i
            if idx<5: 
                mon = today - datetime.timedelta(6+idx+days)
                sat = today - datetime.timedelta(7+idx-6+days)
            elif idx == 5:
                mon = today - datetime.timedelta(4+days)
                sat = today - datetime.timedelta(days-1)
            else:
                mon = today - datetime.timedelta(5+days)
                sat = today - datetime.timedelta(days)
            hist_data_4 = td_app.get_historic_data(s, start_time=mon,end_time=sat, bar_size='EOD')
            df = pd.DataFrame(hist_data_4)
            if df.shape[0]>0:
                df = df.set_index('time')
                df = df.resample('1W').agg({
                    'o': lambda s: s[0],
                    'h': lambda df: df.max(),
                    'l': lambda df: df.min(),
                    'c': lambda df: df[-1],
                })
                fiveWeek = fiveWeek.append(df)
        daily_range = []
        for column in range(len(fiveWeek)):      
            daily_range.append(fiveWeek["h"][column]-fiveWeek["l"][column])

        adr = round((sum(daily_range)/ADR_bars)/100,4)
        print(s,adr)
        ADR_list.append(adr)

    return ADR_list

def get_monthly_adr():
    d = date.today()
    ADR_list = []
    for s in symbol:
        newdf = pd.DataFrame(None)
        d = date.today()
        for i in range(ADR_bars):
            last_date = d.replace(day=1) - timedelta(days=1)
            start_date = d.replace(day=1) - timedelta(days=last_date.day)
            d = d.replace(
                year=d.year if d.month > 1 else d.year - 1,
                month=d.month - 1 if d.month > 1 else 12,
                day=1
            )

            hist_data_4 = td_app.get_historic_data(s, start_time=start_date,end_time=last_date, bar_size='EOD')
            temp = pd.DataFrame(hist_data_4)
            if temp.shape[0]>0:
                temp = temp.set_index('time')
                temp = temp.resample('1M').agg({
                    'o': lambda s: s[0],
                    'h': lambda df: df.max(),
                    'l': lambda df: df.min(),
                    'c': lambda df: df[-1],
                })
                newdf = newdf.append(temp)
        daily_range = []
        for column in range(len(newdf)):      
            daily_range.append(newdf["h"][column]-newdf["l"][column])

        adr = round((sum(daily_range)/ADR_bars)/100,4)
        # print(s,adr)
        ADR_list.append(adr)

    return ADR_list
    
def get_cpr():
    finalCPR = []
    for i in symbol:
        hist_data_3 = td_app.get_n_historical_bars(i, no_of_bars = CPR_width_bars, bar_size='EOD')
        newdf = pd.DataFrame.from_dict(hist_data_3)
        tempCPR = []
        for row in range(len(newdf)):
            p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
            bc1 = bc(newdf["h"][row],newdf["l"][row])
            tc1 = tc(p,bc1)
            CPR = CPR_width(p,tc1,bc1)
            print("CPR>>>>>>>>>>>>>",i,CPR)
            tempCPR.append(CPR)
        finalCPR.append(tempCPR)
    return finalCPR

def get_weekly_cpr():
    finalCPR = []
    today = datetime.date.today()
    # tempsat = dt.strptime("29/01/22",'%d/%m/%y')
    # print(tempsat.date())
    idx = (today.weekday()+1) % 7 # MON = 0, SUN = 6 -> SUN = 0 .. SAT = 6
    for s in symbol:
        newdf = pd.DataFrame()
        tempCPR = []
        for i in range(CPR_width_bars):
            days = 7*i
            if idx<6: 
                mon = today - datetime.timedelta(6+idx+days)
                sat = today - datetime.timedelta(7+idx-6+days)
            else:
                mon = today - datetime.timedelta(5+days)
                sat = today - datetime.timedelta(days)
            hist_data_4 = td_app.get_historic_data(s, start_time=mon,end_time=sat, bar_size='EOD')
            if len(hist_data_4)>0:
                df = pd.DataFrame(hist_data_4)
                if df.shape[0]>0:
                    df = df.set_index('time')
                    df = df.resample('1W').agg({
                        'o': lambda s: s[0],
                        'h': lambda df: df.max(),
                        'l': lambda df: df.min(),
                        'c': lambda df: df[-1],
                    })
                    newdf = newdf.append(df)


        for row in range(len(newdf)):
            p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
            bc1 = bc(newdf["h"][row],newdf["l"][row])
            tc1 = tc(p,bc1)
            CPR = CPR_width(p,tc1,bc1)
            print("wheeeeeeeeeeeeeee>>>>",s,CPR)
            tempCPR.append(CPR)

        finalCPR.append(tempCPR)    

    return finalCPR

def get_monthly_cpr():
    finalCPR = []
    for s in symbol:
        d = date.today()
        newdf = pd.DataFrame()
        tempCPR = []
        for i in range(CPR_width_bars):
            last_date = d.replace(day=1) - timedelta(days=1)
            start_date = d.replace(day=1) - timedelta(days=last_date.day)
            d = d.replace(
                year=d.year if d.month > 1 else d.year - 1,
                month=d.month - 1 if d.month > 1 else 12,
                day=1
            )

            hist_data_4 = td_app.get_historic_data(s, start_time=start_date,end_time=last_date, bar_size='EOD')
            if len(hist_data_4)>0:
                temp = pd.DataFrame(hist_data_4)
                if temp.shape[0]>0:
                    temp = temp.set_index('time')
                    temp = temp.resample('1M').agg({
                        'o': lambda s: s[0],
                        'h': lambda df: df.max(),
                        'l': lambda df: df.min(),
                        'c': lambda df: df[-1],
                    })
                    newdf = newdf.append(temp)

        for row in range(len(newdf)):
            p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
            bc1 = bc(newdf["h"][row],newdf["l"][row])
            tc1 = tc(p,bc1)
            CPR = CPR_width(p,tc1,bc1)
            # print(s,CPR)
            tempCPR.append(CPR)
    
        finalCPR.append(tempCPR)

    return finalCPR

# def get_adrcpr4(symbols,minADR,minCPR,DWM,TT):
#     adrSymbol = {}
#     if TT == "Daily":
#         newDWM = {}
#     else:
#         newDWM = DWM
#     daily_range = []
#     for i in symbols:
#         hist_data_3 = td_app.get_n_historical_bars(i, no_of_bars = ADR_bars, bar_size='EOD')
#         newdf = pd.DataFrame.from_dict(hist_data_3)
#         for column in range(len(newdf)):      
#             daily_range.append(newdf["h"][column]-newdf["l"][column])
#         adr = round((sum(daily_range)/ADR_bars)/100,4)

#         print("ADR  Dailyyyyyyyyy",i,adr)

#         if adr <= minADR:
#             hist_data_3 = td_app.get_n_historical_bars(i, no_of_bars = CPR_width_bars, bar_size='EOD')
#             newdf = pd.DataFrame.from_dict(hist_data_3)
#             validCPR = True
#             for row in range(len(newdf)):
#                 p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
#                 bc1 = bc(newdf["h"][row],newdf["l"][row])
#                 tc1 = tc(p,bc1)
#                 CPR = CPR_width(p,tc1,bc1)
#                 print("CPR  Dailyyyyyyyyy",i,CPR)
#                 if CPR > minCPR:
#                     validCPR = False
#                     break
#             if validCPR:
#                 adrSymbol[i] = adr
#                 newDWM[i] = DWM[i] + "D" 
#         daily_range = []
#     return adrSymbol,newDWM

# def get_weekly_adrcpr4(symbols,minADR,minCPR,DWM,TT):
#     today = datetime.date.today()
#     if TT == "Weekly":
#         newDWM = {}
#     else:
#         newDWM = DWM
#     # tempsat = dt.strptime("29/01/22",'%d/%m/%y')
#     # print(tempsat.date())
#     idx = (today.weekday()+1) % 7 # MON = 0, SUN = 6 -> SUN = 0 .. SAT = 6
#     adrSymbol = {}
#     count = 0
#     for s in symbols:
#         count +=1
#         fiveWeek = pd.DataFrame()
#         for i in range(ADR_bars):
#             days = 7*i
#             if idx<6: 
#                 mon = today - datetime.timedelta(6+idx+days)
#                 sat = today - datetime.timedelta(7+idx-6+days)
#             else:
#                 mon = today - datetime.timedelta(5+days)
#                 sat = today - datetime.timedelta(days)
#             hist_data_4 = td_app.get_historic_data(s, start_time=mon,end_time=sat, bar_size='EOD')
#             if len(hist_data_4)>0:
#                 df = pd.DataFrame(hist_data_4)
#                 if df.shape[0]>0:
#                     df = df.set_index('time')
#                     df = df.resample('1W').agg({
#                         'o': lambda s: s[0],
#                         'h': lambda df: df.max(),
#                         'l': lambda df: df.min(),
#                         'c': lambda df: df[-1],
#                     })
#                     fiveWeek = fiveWeek.append(df)
#         daily_range = []
#         for column in range(len(fiveWeek)):      
#             daily_range.append(fiveWeek["h"][column]-fiveWeek["l"][column])

#         adr = round((sum(daily_range)/ADR_bars)/100,4)
#         print("ADR  Weeklyyyyyyyyyy",s,adr)
#         if adr <= minADR:
#             today = datetime.date.today()
#             # tempsat = dt.strptime("29/01/22",'%d/%m/%y')
#             # print(tempsat.date())
#             idx = (today.weekday()+1) % 7 # MON = 0, SUN = 6 -> SUN = 0 .. SAT = 6
#             newdf = pd.DataFrame()
#             for i in range(CPR_width_bars):
#                 days = 7*i
#                 if idx<6: 
#                     mon = today - datetime.timedelta(6+idx+days)
#                     sat = today - datetime.timedelta(7+idx-6+days)
#                 else:
#                     mon = today - datetime.timedelta(5+days)
#                     sat = today - datetime.timedelta(days)
#                 hist_data_4 = td_app.get_historic_data(s, start_time=mon,end_time=sat, bar_size='EOD')
#                 if len(hist_data_4)>0:
#                     df = pd.DataFrame(hist_data_4)
#                     if df.shape[0]>0:
#                         df = df.set_index('time')
#                         df = df.resample('1W').agg({
#                             'o': lambda s: s[0],
#                             'h': lambda df: df.max(),
#                             'l': lambda df: df.min(),
#                             'c': lambda df: df[-1],
#                         })
#                         newdf = newdf.append(df)

#             validCPR = True
#             for row in range(len(newdf)):
#                 p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
#                 bc1 = bc(newdf["h"][row],newdf["l"][row])
#                 tc1 = tc(p,bc1)
#                 CPR = CPR_width(p,tc1,bc1)
#                 print("CPR  weeklllllllyy>>>>",s,CPR)
#                 if CPR > minCPR:
#                     validCPR = False
#                     break
        
#             if validCPR:
#                 adrSymbol[s] = adr
#                 newDWM[s] = DWM[s] + "W"
#         daily_range = []
#     return adrSymbol,newDWM

# def get_monthly_adrcpr4(symbols,minADR,minCPR,DWM,TT):
#     d = date.today()
#     adrSymbol = {}
#     if TT == "Monthly":
#         newDWM = {}
#     else:
#         newDWM = DWM

#     for s in symbols:
#         newdf = pd.DataFrame(None)
#         d = date.today()
#         for i in range(ADR_bars):
#             last_date = d.replace(day=1) - timedelta(days=1)
#             start_date = d.replace(day=1) - timedelta(days=last_date.day)
#             d = d.replace(
#                 year=d.year if d.month > 1 else d.year - 1,
#                 month=d.month - 1 if d.month > 1 else 12,
#                 day=1
#             )

#             hist_data_4 = td_app.get_historic_data(s, start_time=start_date,end_time=last_date, bar_size='EOD')
#             temp = pd.DataFrame(hist_data_4)
#             if temp.shape[0]>0:
#                 temp = temp.set_index('time')
#                 temp = temp.resample('1M').agg({
#                     'o': lambda s: s[0],
#                     'h': lambda df: df.max(),
#                     'l': lambda df: df.min(),
#                     'c': lambda df: df[-1],
#                 })
#                 newdf = newdf.append(temp)
#         daily_range = []
#         for column in range(len(newdf)):      
#             daily_range.append(newdf["h"][column]-newdf["l"][column])

#         adr = round((sum(daily_range)/ADR_bars)/100,4)
#         print("ADR  monthlyyyyyyyyyyyyyyyy",s,adr)
#         if adr <= minADR:
#             d = date.today()
#             newdf = pd.DataFrame()
#             for i in range(CPR_width_bars):
#                 last_date = d.replace(day=1) - timedelta(days=1)
#                 start_date = d.replace(day=1) - timedelta(days=last_date.day)
#                 d = d.replace(
#                     year=d.year if d.month > 1 else d.year - 1,
#                     month=d.month - 1 if d.month > 1 else 12,
#                     day=1
#                 )

#                 hist_data_4 = td_app.get_historic_data(s, start_time=start_date,end_time=last_date, bar_size='EOD')
#                 if temp.shape[0]>0:
#                     temp = pd.DataFrame(hist_data_4)
#                     temp = temp.set_index('time')
#                     temp = temp.resample('1M').agg({
#                         'o': lambda s: s[0],
#                         'h': lambda df: df.max(),
#                         'l': lambda df: df.min(),
#                         'c': lambda df: df[-1],
#                     })
#                     newdf = newdf.append(temp)

#             validCPR = True
#             for row in range(len(newdf)):
#                 p = pivot(newdf["h"][row],newdf["l"][row],newdf["c"][row])
#                 bc1 = bc(newdf["h"][row],newdf["l"][row])
#                 tc1 = tc(p,bc1)
#                 CPR = CPR_width(p,tc1,bc1)
#                 print("CPR  monthlyyyyyyyyyyyyyyyy",s,CPR)
#                 if CPR > minCPR:
#                     validCPR = False
#                     break
#             if validCPR:
#                 adrSymbol[s] = adr
#                 newDWM[s] = DWM[s] + "M"
#         daily_range = []
#     return(adrSymbol,newDWM)

def construct_daily_data(num,minCPR,minADR):
    global data,screener1D,screener2D,screener3D,screener4D,screener4W,screener4M
    daily_fetch_data(num)
    for i in symbol:
        data.loc[i,"pivot"] = pivot(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"bc"] = bc(data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"tc"] = tc(data.loc[i,"pivot"],data.loc[i,"bc"])
        data.loc[i,"S1"] = S1(data.loc[i,"pivot"],data.loc[i,"h"])
        data.loc[i,"S2"] = S2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"R1"] = R1(data.loc[i,"pivot"],data.loc[i,"l"])
        data.loc[i,"R2"] = R2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"H3"] = H3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"L3"] = L3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"CPR_width"] = CPR_width(data.loc[i,"pivot"],data.loc[i,"tc"],data.loc[i,"bc"])
    data['ADR'] = get_adr()
    data['CPR'] = get_cpr()
    screener1D = data.copy()
    screener2D= data.copy()
    screener3D = data.copy()
    screener4D = data.copy()  
    
    screener2D = data.loc[(((data['H3'] <= data['tc']) & (data['H3'] >= data['bc'])) | ((data['L3'] <= data['tc']) & (data['L3'] >= data['bc'])))]

    intraday_fetch_data(127,symbol)
    for i in symbol:
        intraday.loc[i,"i_pivot"] = pivot(intraday.loc[i,"h"],intraday.loc[i,"l"],intraday.loc[i,"c"])
        intraday.loc[i,"i_bc"] = bc(intraday.loc[i,"h"],intraday.loc[i,"l"])
        intraday.loc[i,"i_tc"] = tc(intraday.loc[i,"i_pivot"],intraday.loc[i,"i_bc"])
    # print(data)
    screener3D = data.loc[((data['tc'] <intraday['i_tc']) & (intraday['i_bc'] <data['bc']))]

    # screener4D['ADRW'] = get_weekly_adr()
    # screener4D['CPRW'] = get_weekly_cpr()
    # screener4D['ADRM'] = get_monthly_adr()
    # screener4D['CPRM'] = get_monthly_cpr()

    screener1D['CPR']=screener1D['CPR'].astype('str')
    screener2D['CPR']=screener2D['CPR'].astype('str')
    screener3D['CPR']=screener3D['CPR'].astype('str')
    screener4D['CPR']=screener4D['CPR'].astype('str')
    # screener4D['CPRW']=screener4D['CPRW'].astype('str')
    # screener4D['CPRM']=screener4D['CPRM'].astype('str')

    screener1D.to_sql('Screener1D', conn, if_exists='replace', index=True)
    screener2D.to_sql('Screener2D', conn, if_exists='replace', index=True)
    screener3D.to_sql('Screener3D', conn, if_exists='replace', index=True)
    screener4D.to_sql('Screener4D', conn, if_exists='replace', index=True)


def construct_weekly_data(num,minCPR,minADR):
    global data,screener1W,screener2W,screener3W,screener4D,screener4W,screener4M
    # if friday and 3:45

    weekly_fetch_data(num)
    for i in symbol:
        data.loc[i,"pivot"] = pivot(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"bc"] = bc(data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"tc"] = tc(data.loc[i,"pivot"],data.loc[i,"bc"])
        data.loc[i,"S1"] = S1(data.loc[i,"pivot"],data.loc[i,"h"])
        data.loc[i,"S2"] = S2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"R1"] = R1(data.loc[i,"pivot"],data.loc[i,"l"])
        data.loc[i,"R2"] = R2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"H3"] = H3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"L3"] = L3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"CPR_width"] = CPR_width(data.loc[i,"pivot"],data.loc[i,"tc"],data.loc[i,"bc"])
    data['ADR'] = get_weekly_adr()
    data['CPR'] = get_weekly_cpr()
    screener1W = data.copy()
    screener2W = data.copy()  
    screener3W = data.copy()
    screener4W = data.copy()
    screener2W = data.loc[(((data['H3'] <= data['tc']) & (data['H3'] >= data['bc'])) | ((data['L3'] <= data['tc']) & (data['L3'] >= data['bc'])))]
    
    intraday_fetch_data(377,symbol)
    for i in symbol:
        intraday.loc[i,"i_pivot"] = pivot(intraday.loc[i,"h"],intraday.loc[i,"l"],intraday.loc[i,"c"])
        intraday.loc[i,"i_bc"] = bc(intraday.loc[i,"h"],intraday.loc[i,"l"])
        intraday.loc[i,"i_tc"] = tc(intraday.loc[i,"i_pivot"],intraday.loc[i,"i_bc"])
    # print(data)
    screener3W = data.loc[((data['tc'] <intraday['i_tc']) & (intraday['i_bc'] <data['bc']))]


    screener1W['CPR']=screener1W['CPR'].astype('str')
    screener2W['CPR']=screener2W['CPR'].astype('str')
    screener3W['CPR']=screener3W['CPR'].astype('str')
    screener4W['CPR']=screener4W['CPR'].astype('str')

    screener1W.to_sql('Screener1W', conn, if_exists='replace', index=True)
    screener2W.to_sql('Screener2W', conn, if_exists='replace', index=True)
    screener3W.to_sql('Screener3W', conn, if_exists='replace', index=True)
    screener4W.to_sql('Screener4W', conn, if_exists='replace', index=True)
    
    
    
def construct_monthly_data(num,minCPR,minADR):
    global data,screener1M,screener2M,screener3M,screener4D,screener4W,screener4M

    monthly_fetch_data(num)
        
    for i in symbol:
        data.loc[i,"pivot"] = pivot(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"bc"] = bc(data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"tc"] = tc(data.loc[i,"pivot"],data.loc[i,"bc"])
        data.loc[i,"S1"] = S1(data.loc[i,"pivot"],data.loc[i,"h"])
        data.loc[i,"S2"] = S2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"R1"] = R1(data.loc[i,"pivot"],data.loc[i,"l"])
        data.loc[i,"R2"] = R2(data.loc[i,"pivot"],data.loc[i,"h"],data.loc[i,"l"])
        data.loc[i,"H3"] = H3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"L3"] = L3(data.loc[i,"h"],data.loc[i,"l"],data.loc[i,"c"])
        data.loc[i,"CPR_width"] = CPR_width(data.loc[i,"pivot"],data.loc[i,"tc"],data.loc[i,"bc"])
    data['ADR'] = get_monthly_adr()
    data['CPR'] = get_monthly_cpr()
    screener1M = data.copy()
    screener2M = data.copy()
    screener3M = data.copy()
    screener4M = data.copy()

    screener2M = data.loc[(((data['H3'] <= data['tc']) & (data['H3'] >= data['bc'])) | ((data['L3'] <= data['tc']) & (data['L3'] >= data['bc'])))]

    intraday_fetch_data(475,symbol)
    for i in symbol:
        intraday.loc[i,"i_pivot"] = pivot(intraday.loc[i,"h"],intraday.loc[i,"l"],intraday.loc[i,"c"])
        intraday.loc[i,"i_bc"] = bc(intraday.loc[i,"h"],intraday.loc[i,"l"])
        intraday.loc[i,"i_tc"] = tc(intraday.loc[i,"i_pivot"],intraday.loc[i,"i_bc"])
    print(data)
    screener3M = data.loc[((data['tc'] < intraday['i_tc']) & (intraday['i_bc'] <data['bc']))]

    # screener4M['ADRD'] = get_adr()
    # screener4M['CPRD'] = get_cpr()
    # screener4M['ADRW'] = get_weekly_adr()
    # screener4M['CPRW'] = get_weekly_cpr()

    screener1M['CPR']=screener1M['CPR'].astype('str')
    screener2M['CPR']=screener2M['CPR'].astype('str')
    screener3M['CPR']=screener3M['CPR'].astype('str')
    screener4M['CPR']=screener4M['CPR'].astype('str')
    # screener4M['CPRD']=screener4M['CPRD'].astype('str')
    # screener4M['CPRW']=screener4M['CPRW'].astype('str')

    screener1M.to_sql('Screener1M', conn, if_exists='replace', index=True)
    screener2M.to_sql('Screener2M', conn, if_exists='replace', index=True)
    screener3M.to_sql('Screener3M', conn, if_exists='replace', index=True)
    screener4M.to_sql('Screener4M', conn, if_exists='replace', index=True)

def Screener1(minADR,minCPR,TableT):
    global screener1D,screener1W,screener1M

    screener1D = pd.read_sql('select * from screener1D', conn)
    screener1W = pd.read_sql('select * from screener1W', conn)
    screener1M = pd.read_sql('select * from screener1M', conn)

    screener1D.CPR = screener1D.CPR.apply(literal_eval)
    screener1W.CPR = screener1W.CPR.apply(literal_eval)
    screener1M.CPR = screener1M.CPR.apply(literal_eval)

    #Editing the columns 
    screener1D.drop(['o'],axis=1,inplace=True)
    screener1W.drop(['o'],axis=1,inplace=True)
    screener1M.drop(['o'],axis=1,inplace=True)
    screener1D.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener1W.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener1M.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)


    if screener1D.shape[0]>0:
        screener1D = screener1D.loc[(screener1D['ADR'] <= minADR)]
        for i, j in screener1D.iterrows():
            # print(i,screener1D["CPR"][i])
            if any(cpr > minCPR for cpr in screener1D["CPR"][i]):
                print(screener1D["CPR"][i])
                screener1D = screener1D.drop(i)  
        print("1d",screener1D)

    if screener1W.shape[0]>0:
        screener1W = screener1W.loc[(screener1W['ADR'] <= minADR)]
        for i, j in screener1W.iterrows():
            # print(i,screener1D["CPR"][i])
            if any(cpr > minCPR for cpr in screener1W["CPR"][i]):
                print(screener1W["CPR"][i])
                screener1W = screener1W.drop(i) 
        print("1W",screener1W)

    if screener1M.shape[0]>0:
        screener1M = screener1M.loc[(screener1M['ADR'] <= minADR)]
        for i, j in screener1M.iterrows():
            # print(i,screener1D["CPR"][i])
            if any(cpr > minCPR for cpr in screener1M["CPR"][i]):
                print(screener1M["CPR"][i])
                screener1M = screener1M.drop(i)  
        print("1M",screener1M)


def Screener2(minADR,minCPR,TableT):
    global screener2D,screener2W,screener2M
    
    screener2D = pd.read_sql('select * from screener2D', conn)
    screener2W = pd.read_sql('select * from screener2W', conn)
    screener2M = pd.read_sql('select * from screener2M', conn)

    screener2D.CPR = screener2D.CPR.apply(literal_eval)
    screener2W.CPR = screener2W.CPR.apply(literal_eval)
    screener2M.CPR = screener2M.CPR.apply(literal_eval)

    #Editing the columns 
    screener2D.drop(['o'],axis=1,inplace=True)
    screener2W.drop(['o'],axis=1,inplace=True)
    screener2M.drop(['o'],axis=1,inplace=True)
    screener2D.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener2W.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener2M.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)



    if screener2D.shape[0]>0:
        screener2D = screener2D.loc[(screener2D['ADR'] <= minADR)]
        for i, j in screener2D.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener2D["CPR"][i]):
                print(screener2D["CPR"][i])
                screener2D = screener2D.drop(i)  
        print("2d",screener2D)

    if screener2W.shape[0]>0:
        screener2W = screener2W.loc[(screener2W['ADR'] <= minADR)]
        for i, j in screener2W.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener2W["CPR"][i]):
                print(screener2W["CPR"][i])
                screener2W = screener2W.drop(i)  
        print("2W",screener2W)

    if screener2M.shape[0]>0:
        screener2M = screener2M.loc[(screener2M['ADR'] <= minADR)]
        for i, j in screener2M.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener2M["CPR"][i]):
                print(screener2M["CPR"][i])
                screener2M = screener2M.drop(i)  
        print("2m",screener2M)

def Screener3(minADR,minCPR,TableT):
    global screener3D,screener3W,screener3M
    
    screener3D = pd.read_sql('select * from screener3D', conn)
    screener3W = pd.read_sql('select * from screener3W', conn)
    screener3M = pd.read_sql('select * from screener3M', conn)

    screener3D.CPR = screener3D.CPR.apply(literal_eval)
    screener3W.CPR = screener3W.CPR.apply(literal_eval)
    screener3M.CPR = screener3M.CPR.apply(literal_eval)

    #Editing the columns 
    screener3D.drop(['o'],axis=1,inplace=True)
    screener3W.drop(['o'],axis=1,inplace=True)
    screener3M.drop(['o'],axis=1,inplace=True)
    screener3D.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener3W.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener3M.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)

    if screener3D.shape[0]>0:
        screener3D = screener3D.loc[(screener3D['ADR'] <= minADR)]
        for i, j in screener3D.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener3D["CPR"][i]):
                print(screener3D["CPR"][i])
                screener3D = screener3D.drop(i)  
        print("3d",screener3D)
    
    if screener3W.shape[0]>0:
        screener3W = screener3W.loc[(screener3W['ADR'] <= minADR)]
        for i, j in screener3W.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener3W["CPR"][i]):
                print(screener3W["CPR"][i])
                screener3W = screener3W.drop(i)  
        print("3W",screener3W)

    if screener3M.shape[0]>0:
        screener3M = screener3M.loc[(screener3M['ADR'] <= minADR)]
        for i, j in screener3M.iterrows():
            # print(i,screener2D["CPR"][i])
            if any(cpr > minCPR for cpr in screener3M["CPR"][i]):
                print(screener3M["CPR"][i])
                screener3M = screener3M.drop(i)  
        print("3m",screener3M)  


def Screener4(minADR,minCPR,TableT):
    global screener4D,screener4W,screener4M
    
    screener4D = pd.read_sql('select * from screener4D', conn)
    screener4W = pd.read_sql('select * from screener4W', conn)
    screener4M = pd.read_sql('select * from screener4M', conn)

    screener4D.CPR = screener4D.CPR.apply(literal_eval)
    screener4W.CPR = screener4W.CPR.apply(literal_eval)
    screener4M.CPR = screener4M.CPR.apply(literal_eval)
    # screener4D.CPRW = screener4D.CPRW.apply(literal_eval)
    # screener4D.CPRM = screener4D.CPRM.apply(literal_eval)

    screener4D['ADRW'] = screener4W['ADR']
    screener4D['CPRW'] = screener4W['CPR']
    screener4D['ADRM'] = screener4M['ADR']
    screener4D['CPRM'] =screener4M['CPR']

    
    screener4W['ADRD'] = screener4D['ADR']
    screener4W['CPRD'] = screener4D['CPR']
    screener4W['ADRM'] = screener4M['ADR']
    screener4W['CPRM'] = screener4M['CPR']
    # screener4W.CPRD = screener4W.CPRD.apply(literal_eval)
    # screener4W.CPRM = screener4W.CPRM.apply(literal_eval)

    screener4M['ADRD'] = screener4D['ADR']
    screener4M['CPRD'] = screener4D['CPR']
    screener4M['ADRW'] = screener4W['ADR']
    screener4M['CPRW'] = screener4W['CPR']


   
    # screener4M.CPRD = screener4M.CPRD.apply(literal_eval)
    # screener4M.CPRW = screener4M.CPRW.apply(literal_eval)

    #Editing the columns 
    screener4D.drop(['o'],axis=1,inplace=True)
    screener4W.drop(['o'],axis=1,inplace=True)
    screener4M.drop(['o'],axis=1,inplace=True)
    screener4D.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener4W.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)
    screener4M.rename(columns={'symbol': 'Ticker','c': 'LTP','h': 'P.High','l': 'P.Low','pivot': 'PP','bc': 'BC','tc': 'TC'}, inplace=True)

    if screener4D.shape[0]>0:
        screener4D = screener4D.loc[(screener4D['ADR'] <= minADR)]
        for i, j in screener4D.iterrows():
            if any(cpr > minCPR for cpr in screener4D["CPR"][i]):
                print(screener4D["CPR"][i])
                screener4D = screener4D.drop(i)  

        screener4D["DWM"] = "D"

        for i, j in screener4D.iterrows():
            # print(i,screener4D["CPR"][i])
            if any(cpr > minCPR for cpr in screener4D["CPRW"][i]):
                print(screener4D["CPRW"][i])
            else:
                screener4D["DWM"][i]=screener4D["DWM"][i]+"W"

        for i, j in screener4D.iterrows():
            # print(i,screener4D["CPR"][i])
            if any(cpr > minCPR for cpr in screener4D["CPRM"][i]):
                print(screener4D["CPRM"][i])
            else:
                screener4D["DWM"][i]=screener4D["DWM"][i]+"M"

        screener4D['lenDWM'] = [len(lDWM) for lDWM in list(screener4D["DWM"])]
        screener4D = screener4D.sort_values(by=["lenDWM"],ascending=False)
        screener4D.drop(['lenDWM'],axis=1,inplace=True)

        print("4d",screener4D)

    if screener4W.shape[0]>0:
        screener4W = screener4W.loc[(screener4W['ADR'] <= minADR)]
        for i, j in screener4W.iterrows():
            # print(i,screener4D["CPR"][i])
            if any(cpr > minCPR for cpr in screener4W["CPR"][i]):
                print(screener4W["CPR"][i])
                screener4W = screener4W.drop(i)  

        screener4W["DWM"] = "W"

        for i, j in screener4W.iterrows():
            # print(i,screener4W["CPR"][i])
            if any(cpr > minCPR for cpr in screener4W["CPRD"][i]):
                print(screener4W["CPRD"][i])
            else:
                screener4W["DWM"][i]=screener4W["DWM"][i]+"D"

        for i, j in screener4W.iterrows():
            # print(i,screener4W["CPR"][i])
            if any(cpr > minCPR for cpr in screener4W["CPRM"][i]):
                print(screener4W["CPRM"][i])
            else:
                screener4W["DWM"][i]=screener4W["DWM"][i]+"M"

        screener4W['lenDWM'] = [len(lDWM) for lDWM in list(screener4W["DWM"])]
        screener4W = screener4W.sort_values(by=["lenDWM"],ascending=False)
        screener4W.drop(['lenDWM'],axis=1,inplace=True)
        print("4W",screener4W)

    if screener4M.shape[0]>0:
        screener4M = screener4M.loc[(screener4M['ADR'] <= minADR)]
        for i, j in screener4M.iterrows():
            # print(i,screener4D["CPR"][i])
            if any(cpr > minCPR for cpr in screener4M["CPR"][i]):
                print(screener4M["CPR"][i])
                screener4M = screener4M.drop(i)  

        screener4M["DWM"] = "M"

        for i, j in screener4M.iterrows():
            # print(i,screener4M["CPR"][i])
            if any(cpr > minCPR for cpr in screener4M["CPRD"][i]):
                print(screener4M["CPRD"][i])
            else:
                screener4M["DWM"][i]=screener4M["DWM"][i]+"D"

        for i, j in screener4M.iterrows():
            # print(i,screener4M["CPR"][i])
            if any(cpr > minCPR for cpr in screener4M["CPRW"][i]):
                print(screener4M["CPRW"][i])
            else:
                screener4M["DWM"][i]=screener4M["DWM"][i]+"W"

        screener4M['lenDWM'] = [len(lDWM) for lDWM in list(screener4M["DWM"])]
        screener4M = screener4M.sort_values(by=["lenDWM"],ascending=False)
        screener4M.drop(['lenDWM'],axis=1,inplace=True)
        print("4m",screener4M)

app = Flask(__name__)
app.jinja_env.globals.update(zip=zip)

@app.route("/", methods = ["GET","POST"])
def index():
    if request.method == "POST":
        scrn = request.form["Screeners"]
        mc,ma = request.form["MyminCPR"],request.form["MyminADR"]
        return redirect(url_for("table", MyScreener = scrn, MyminCPR = mc, MyminADR = ma))
    else:
        return render_template("home.html")

@app.route("/table/<MyScreener>/<MyminCPR>/<MyminADR>")
def table(MyScreener,MyminCPR,MyminADR):
    start_time = time.perf_counter ()
    global minADR,minCPR,last_updated_day,last_updated_week,last_updated_month,DateTable
    DateTable = pd.read_sql('select * from DateTable', conn)
    print(DateTable)
    current_hour = int(datetime.datetime.now().strftime("%H"))
    current_min = int(datetime.datetime.now().strftime("%M"))
    dateIdx = datetime.date.today().weekday()
    current_day = datetime.date.today()
    last_friday = current_day + relativedelta(weekday=FR(-1))
    last_date_of_previous_month = current_day + relativedelta(day=1, days=-1)
    last_date_of_month = current_day + relativedelta(month=datetime.date.today().month+1, day=1, days=-1)


    minADR = float(MyminADR)
    minCPR = float(MyminCPR)

    # if (current_hour < 5 or current_hour > 15) or (current_hour == 15 and current_min >45):
        #   DAILY CONDITIONS>>>>>>>>>
    if ((current_hour > 15) and (DateTable["Dates"][0] < current_day)):
        print("daily update Oneeeeeeeeeeeeeeeeeeeee: ", dateIdx)
        construct_daily_data(1,minCPR,minADR)
        DateTable["Dates"][0] = current_day

    elif ((current_hour == 15 and current_min >= 45) and (DateTable["Dates"][0] < current_day)):
        print("daily update Oneeeeeeeeeeeeeeeeeeeee: ", dateIdx)
        construct_daily_data(1,minCPR,minADR)
        DateTable["Dates"][0] = current_day
    
    elif (DateTable["Dates"][0] < current_day-timedelta(1)) and dateIdx != 6 and dateIdx != 0:
        construct_daily_data(1,minCPR,minADR)
        print("daily update Twoooooooooooooooooooooooooooo: ", dateIdx)
        DateTable["Dates"][0] = current_day-timedelta(1)

    elif (dateIdx == 0) and (DateTable["Dates"][0] < current_day-timedelta(3)): 
        construct_daily_data(1,minCPR,minADR)
        print("daily update Threeeeeeeeeeeeeeeeeeeeeeee")
        DateTable["Dates"][0] = current_day-timedelta(3)
    
    elif (dateIdx == 6) and (DateTable["Dates"][0] < current_day-timedelta(2)): 
        construct_daily_data(1,minCPR,minADR)
        print("daily update Fourrrrrrrrrrrrrrrrrrrr")
        DateTable["Dates"][0] = current_day-timedelta(2)
    
    #   WEEKLY CONDITIONS>>>>>>>>>
    if ((current_hour > 15) and (DateTable["Dates"][1] < current_day) and dateIdx==4):
        construct_weekly_data(1,minCPR,minADR)
        print("weekly update")
        DateTable["Dates"][1] = current_day

    elif ((current_hour == 15 and current_min >= 45) and (DateTable["Dates"][1] < current_day) and dateIdx==4):
        construct_weekly_data(1,minCPR,minADR)
        print("weekly update")
        DateTable["Dates"][1] = current_day

    elif DateTable["Dates"][1] != last_friday and dateIdx != 4:
        construct_weekly_data(1,minCPR,minADR)
        print("weekly update")
        DateTable["Dates"][1] = last_friday

    #   MONTHLY CONDITIONS>>>>>>>>>
    if ((current_hour > 15) and (DateTable["Dates"][2] < current_day) and (current_day == last_date_of_month)):
        construct_monthly_data(1,minCPR,minADR)
        print("monthly update")
        DateTable["Dates"][2] = current_day

    elif (current_hour == 15 and current_min >=45 and (DateTable["Dates"][2] < current_day) and (current_day == last_date_of_month)):
        construct_monthly_data(1,minCPR,minADR)
        print("monthly update")
        DateTable["Dates"][2] = current_day


    elif (DateTable["Dates"][2] != last_date_of_previous_month) and current_day != last_date_of_month:
        construct_monthly_data(1,minCPR,minADR)
        print("monthly update")
        DateTable["Dates"][2] = last_date_of_previous_month

    DateTable.to_sql("DateTable",conn,if_exists='replace',index=False)
    end_time = time.perf_counter ()
    if MyScreener == "Screener1":
        global screener1D,screener1W,screener1M
        Screener1(minADR,minCPR,"TT")
        # if screener1D.shape[0]>0:  
        # if Download == "Yes":
        #     ct = datetime.datetime.now()
        #     current = str(ct.date())+" "+str(ct.hour)+"-"+str(ct.minute)+"-"+str(ct.second)
        #     screener1D.to_excel("Screener1D "+current+".xlsx")
        #     screener1W.to_excel("Screener1W "+current+".xlsx")
        #     screener1M.to_excel("Screener1M "+current+".xlsx")
        return render_template("Table.html",sNum= MyScreener, Screener = "Next DWM Screener", column_namesD = screener1D.columns.values, row_dataD = list(screener1D.values.tolist()), 
                                column_namesW = screener1W.columns.values, row_dataW = list(screener1W.values.tolist()),
                                column_namesM = screener1M.columns.values, row_dataM = list(screener1M.values.tolist()), LastDay = DateTable["Dates"][0], LastWeek = DateTable["Dates"][1], LastMonth = DateTable["Dates"][2], TotalTime = end_time - start_time)

    elif MyScreener == "Screener2":
        global screener2D,screener2W,screener2M
        Screener2(minADR,minCPR,"TT")
        # if screener2D.shape[0]>0:  
        # if Download == "Yes":
        #     ct = datetime.datetime.now()
        #     current = str(ct.date())+" "+str(ct.hour)+"-"+str(ct.minute)+"-"+str(ct.second)
        #     screener2D.to_excel("screener2D "+current+".xlsx")
        #     screener2W.to_excel("screener2W "+current+".xlsx")
        #     screener2M.to_excel("screener2M "+current+".xlsx")
        return render_template("Table.html", sNum= MyScreener, Screener = "Camarilla Confluence Screener", column_namesD = screener2D.columns.values, row_dataD = list(screener2D.values.tolist()), 
                                column_namesW = screener2W.columns.values, row_dataW = list(screener2W.values.tolist()),
                                column_namesM = screener2M.columns.values, row_dataM = list(screener2M.values.tolist()),LastDay = DateTable["Dates"][0], LastWeek = DateTable["Dates"][1], LastMonth = DateTable["Dates"][2], TotalTime = end_time - start_time)
   
    elif MyScreener == "Screener3":
        global screener3D,screener3W,screener3M
        Screener3(minADR,minCPR,"TT")
        # if screener3D.shape[0]>0:  
        # if Download == "Yes":
        #     ct = datetime.datetime.now()
        #     current = str(ct.date())+" "+str(ct.hour)+"-"+str(ct.minute)+"-"+str(ct.second)
        #     screener3D.to_excel("screener3D "+current+".xlsx")
        #     screener3W.to_excel("screener3W "+current+".xlsx")
        #     screener3M.to_excel("screener3M "+current+".xlsx")
        return render_template("Table.html",sNum= MyScreener, Screener = "Intraday Confluence Screener", column_namesD = screener3D.columns.values, row_dataD = list(screener3D.values.tolist()), 
                                column_namesW = screener3W.columns.values, row_dataW = list(screener3W.values.tolist()),
                                column_namesM = screener3M.columns.values, row_dataM = list(screener3M.values.tolist()), LastDay = DateTable["Dates"][0], LastWeek = DateTable["Dates"][1], LastMonth = DateTable["Dates"][2], TotalTime = end_time - start_time)

    elif MyScreener == "Screener4":
        global screener4D,screener4W,screener4M
        Screener4(minADR,minCPR,"TT")
        # if screener4D.shape[0]>0:  
        #     if Order == "Ascending":
        #         screener4D = screener4D.sort_values(by=[MyAttribute])
        #     else:
        #         screener4D = screener4D.sort_values(by=[MyAttribute],ascending=False)
        # if Download == "Yes":
        #     ct = datetime.datetime.now()
        #     current = str(ct.date())+" "+str(ct.hour)+"-"+str(ct.minute)+"-"+str(ct.second)
        #     screener4D.to_excel("screener4D "+current+".xlsx")
        #     screener4W.to_excel("screener4W "+current+".xlsx")
        #     screener4M.to_excel("screener4M "+current+".xlsx")
        return render_template("Table.html",sNum= MyScreener, Screener = "Multi Time Frame Screener", column_namesD = screener4D.columns.values, row_dataD = list(screener4D.values.tolist()), 
                                column_namesW = screener4W.columns.values, row_dataW = list(screener4W.values.tolist()),
                                column_namesM = screener4M.columns.values, row_dataM = list(screener4M.values.tolist()), LastDay = DateTable["Dates"][0], LastWeek = DateTable["Dates"][1], LastMonth = DateTable["Dates"][2], TotalTime = end_time - start_time)

@app.route('/download/<sNum>/<dwnld>')
def download(sNum,dwnld):
    ct = datetime.datetime.now()
    current = str(ct.date())+" "+str(ct.hour)+"-"+str(ct.minute)+"-"+str(ct.second)
    if sNum == "Screener1":
        global screener1D,screener1W,screener1M
        Screener1(minADR,minCPR,"TT")   
        if dwnld == "Daily":
            screener1D.to_excel("Screener1D "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameD = "Screener1D "+current+".xlsx"
            return send_file(nameD, as_attachment=True)

        elif dwnld == "Weekly":
            screener1W.to_excel("Screener1W "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameW = "Screener1W "+current+".xlsx"
            return send_file(nameW, as_attachment=True)
        
        elif dwnld == "Monthly":
            screener1M.to_excel("Screener1M "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameM = "Screener1M "+current+".xlsx"
            return send_file(nameM, as_attachment=True)

    elif sNum == "Screener2":
        global screener2D,screener2W,screener2M
        Screener2(minADR,minCPR,"TT")   
        if dwnld == "Daily":
            screener2D.to_excel("screener2D "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameD = "screener2D "+current+".xlsx"
            return send_file(nameD, as_attachment=True)

        elif dwnld == "Weekly":
            screener2W.to_excel("screener2W "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameW = "screener2W "+current+".xlsx"
            return send_file(nameW, as_attachment=True)
        
        elif dwnld == "Monthly":
            screener2M.to_excel("Screener2M "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameM = "Screener2M "+current+".xlsx"
            return send_file(nameM, as_attachment=True)

    elif sNum == "Screener3": 
        global screener3D,screener3W,screener3M
        Screener3(minADR,minCPR,"TT")  
        if dwnld == "Daily":
            screener3D.to_excel("screener3D "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameD = "screener3D "+current+".xlsx"
            return send_file(nameD, as_attachment=True)

        elif dwnld == "Weekly":
            screener3W.to_excel("screener3W "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameW = "screener3W "+current+".xlsx"
            return send_file(nameW, as_attachment=True)
        
        elif dwnld == "Monthly":
            screener3M.to_excel("Screener3M "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameM = "Screener3M "+current+".xlsx"
            return send_file(nameM, as_attachment=True)

    elif sNum == "Screener4": 
        global screener4D,screener4W,screener4M
        Screener4(minADR,minCPR,"TT")  
        if dwnld == "Daily":
            screener4D.to_excel("screener4D "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameD = "screener4D "+current+".xlsx"
            return send_file(nameD, as_attachment=True)

        elif dwnld == "Weekly":
            screener4W.to_excel("screener4W "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameW = "screener4W "+current+".xlsx"
            return send_file(nameW, as_attachment=True)
        
        elif dwnld == "Monthly":
            screener4M.to_excel("Screener4M "+current+".xlsx",index=False,columns=["Ticker","P.High","P.Low","LTP","PP","BC","TC","S1","S2","R1","R2","H3","L3","CPR_width","ADR"])
            nameM = "Screener4M "+current+".xlsx"
            return send_file(nameM, as_attachment=True)
            

if __name__ ==  "__main__":
    #webbrowser.open('http://127.0.0.1:5000/', new=0, autoraise=True)
    app.run()
