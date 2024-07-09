from pya3 import *
import pandas as pd
import datetime
from datetime import timedelta
import pytz
import json
from UltraDict import UltraDict
from shared_memory import data,symbol_obj_map,shared_memory,InstrumentTuple
import mibian


def start_thread(obj_list):
    [x.start() for x in obj_list]

def get_atm(base_symbol):
   
    return int(round(float(shared_memory.dictionary[base_symbol]['LP']) / data.config[base_symbol]['Strike_difference']) * data.config[base_symbol]['Strike_difference'])

def get_subscribe_list(ATM_dict):
    
    subscribe_list = []
    for index in data.todays_trading_instrument:

        exch_ = 'NFO' if data.config[index]['Exchange'] == 'NSE' else 'BFO'

        for x in range(-20, 20):
            for is_ce in [True,False]:
                instrument = data.alice.get_instrument_for_fno(exch=exch_, symbol=index,
                                                            expiry_date=str(data.expiries_dict[index]),
                                                            is_fut=False,
                                                            strike=int(ATM_dict[index] + (x * data.config[index]['Strike_difference'])),
                                                            is_CE=is_ce)
                if instrument != {'stat': 'Not_ok', 'emsg': 'No Data'}:                                          
                    subscribe_list.append(instrument)

    return subscribe_list


def get_symbol(base_symbol, spot_price, strike, option_type,expiry_):

    exch = 'NFO' if data.config[base_symbol]['Exchange'] == 'NSE' else 'BFO'
    striki = int(((spot_price / data.config[base_symbol]['Strike_difference']) *data. config[base_symbol]['Strike_difference']) + strike)

    instrument = data.alice.get_instrument_for_fno(exch=exch, symbol=base_symbol, expiry_date=str(expiry_), is_fut=False,
                                                    strike=striki, is_CE=True if option_type == "CE" else False)

    return instrument[InstrumentTuple.NAME]

def calculate_dates_to_expiry(expiry):
    expiry = datetime.datetime.strptime(expiry, "%Y-%m-%d") + timedelta(hours=15, minutes=30)
    current_date = datetime.datetime.now()
    days_to_expiry = (expiry - current_date).total_seconds() / (24 * 60 * 60)
    return round(days_to_expiry, 2)

def calculate_delta(underlyingPrice, StrikePrice, interestRate, daysToExpiration, option_type, option_price):
    if option_type == 'CE':
        c = mibian.BS([underlyingPrice, StrikePrice, interestRate, daysToExpiration], callPrice=option_price)

        a = mibian.BS([underlyingPrice, StrikePrice, interestRate, daysToExpiration], volatility=c.impliedVolatility)

        return round(a.callDelta, 2)

    elif option_type == 'PE':
        c = mibian.BS([underlyingPrice, StrikePrice, interestRate, daysToExpiration], putPrice=option_price)

        a = mibian.BS([underlyingPrice, StrikePrice, interestRate, daysToExpiration], volatility=c.impliedVolatility)

        return round(a.putDelta, 2)

def get_option_type(instrument):


    if instrument[-6] == 'C':
        return 'CE'
    elif instrument[-6] == 'P':
        return 'PE'

    elif instrument[-5] == 'C':
        return 'CE'
    elif instrument[-5] == 'P':
        return 'PE'

    elif instrument[-2] == 'C':
        return 'CE'
    elif instrument[-2] == 'P':
        return 'PE'

def get_strike_from_instrument(instrument):
    try:
        return int(instrument[-5:]) if get_exchange_fron_instrument(instrument) == 'NSE' else int(instrument[-7:-2])
    except:
        return int(instrument[-4:])   # MIDCPNIFTY

def get_exchange_fron_instrument(instrument):
    if instrument.startswith(('NIFTY','BANKNIFTY','FINNIFTY','MIDCPNIFTY')):
        return 'NSE'
    else:
        return 'BSE'

def square_off_all_positions(index):

    if index == 'MARKET_CLOSING':
        index = data.todays_trading_instrument
        for index_ in index:
            shared_memory.dictionary[index_]['SQUARE_OFF_ALL_POSITIONS'] = True 

    else:
        shared_memory.dictionary[index]['SQUARE_OFF_ALL_POSITIONS'] = True 
    
    return 