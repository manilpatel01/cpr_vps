
import string
from this import s
from unittest import skip
import pandas as pd
from flask import Flask, redirect, render_template,request, url_for,send_file
from truedata_ws.websocket.TD import TD
import datetime
from datetime import date,timedelta
from dateutil.relativedelta import relativedelta, FR
from io import BytesIO
import sqlite3
from ast import literal_eval
import webbrowser
import pytz 
import time
import os


username = 'tdws215'
password = 'vinay@215' 
td_app = TD(username, password, live_port=None)
intraday = pd.DataFrame()
symbol_df = pd.read_csv("stocks.csv")
symbol = pd.DataFrame(symbol_df)



IST = pytz.timezone('Asia/Kolkata')
current_hour = int(datetime.datetime.now(IST).strftime('%H'))
current_min = int(datetime.datetime.now(IST).strftime('%M'))

print(current_hour,current_min)