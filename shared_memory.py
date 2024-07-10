from pya3 import *
from UltraDict import UltraDict
import datetime
import pytz
from strategies.trading_strategy import TradingStrategy
import pandas as pd
import json
from retrying import retry
import os

global shared_memory, symbol_obj_map, data
global expected_strikes_dict, current_strikes_dict, initial_short_quantity

class InstrumentTuple:

    EXCHANGE = 0 
    TOKEN = 1
    SYMBOL = 2
    NAME = 3
    EXPIRY = 4
    LOT_SIZE = 5

class Shared_Memory:

    def __init__(self, dictionary_name):
        UltraDict.unlink_by_name(dictionary_name, ignore_errors=True)
        UltraDict.unlink_by_name(f'{dictionary_name}_memory', ignore_errors=True)
        self.dictionary = UltraDict(recurse=True, create=True, name=dictionary_name)


class Symbol_Obj_Map:
    def __init__(self,dictionary):
        self.dictionary = dict()
     


class DataGenerator:
    def __init__(self,strategy,is_paper_trade):
        self.strategy = strategy
        self.config = self.get_configuration_file()
        self.indices = list(self.config.keys())
        self.alice = self.get_alice_blue_session()
        self.get_contract()
        self.df_nse,self.df_bse = self.get_contarct_dataframe()
        self.expiries_dict = self.get_expiries()
        self.todays_trading_instrument, self.colliding_expiries_instrument_list =  self.get_todays_instruments()
        self.lot_size_dict = self.get_lot_size()
        self.subscribe_list = list()
        self.paper_trade = is_paper_trade
        if self.strategy == TradingStrategy.EMA:
            self.ema_data = self.get_ema_data()
        self.quantity_freeze_dict = dict()


   

    def get_configuration_file(self):
        with open(f'Configuration_files/{self.strategy}_Configuration.json', 'r') as openfile:
            config = json.load(openfile)
            return config

    def get_alice_blue_session(self):

        with open('credentials.json', 'r') as openfile:
            file_content = json.load(openfile)

        user_id = file_content['user_id']
        api_key = file_content['api_key']

        # Connect and get session Id
        alice = Aliceblue(user_id=user_id, api_key=api_key)
        print(alice.get_session_id())
        return alice

    def get_contract(self):
        self.alice.get_contract_master("NFO")
        self.alice.get_contract_master("BFO")
        print("master contract downloaded")
    
    def get_contarct_dataframe(self):
        df_nse = pd.read_csv('NFO.csv')
        df_bse = pd.read_csv('BFO.csv')
        return df_nse, df_bse

    def get_expiries(self):
      

        def is_current_date_greater_than_latest_expiry(string_input_with_date):
            # string_input_with_date = "2023-08-03"
            past = datetime.datetime.strptime(string_input_with_date, "%Y-%m-%d")
            present = datetime.datetime.now()
            return past.date() < present.date()

        expiries_dict = {}
        for index in self.indices:
            df = self.df_nse if self.config[index]['Exchange'] == 'NSE' else self.df_bse
            expiry_df = df[df['Symbol'] == index]
            expiry_list = expiry_df['Expiry Date'].sort_values().drop_duplicates().reset_index(drop=True)
            expiry = expiry_list[1] if is_current_date_greater_than_latest_expiry(expiry_list[0]) else expiry_list[0]
            expiries_dict[index] = str(expiry)

        return expiries_dict
    
    def get_todays_instruments(self):
       
        instrument_today_expiry = []
        today_date = datetime.datetime.now().strftime('%Y-%m-%d')
        for index in self.indices:
            if  self.expiries_dict[index] == today_date:
                instrument_today_expiry.append(index)

        priority = 9999
        instrument = []
        for index in instrument_today_expiry:
            if self.config[index]['Priority'] < priority:
                priority = self.config[index]['Priority']
                instrument = [index]

        return instrument, instrument_today_expiry 

    def get_lot_size(self):
        lot_size_dict = {}
    
        for index in self.indices:
            df = self.df_nse if self.config[index]['Exchange'] == 'NSE' else self.df_bse
            #expiry_df = df[(df['Symbol'] == index) & (df['Instrument Type'] == 'OPTIDX')].sort_values(by='Expiry Date')
            expiry_df = df[df['Symbol'] == index].sort_values(by='Expiry Date')
            if expiry_df.empty:
                continue
            lot_size = int(expiry_df['Lot Size'].iloc[0])
            lot_size_dict[index] = lot_size
    
        return lot_size_dict

    def get_ema_data(self):
        
        ema_data_dic = {}   

        def pull_ema_data(index, strike, option_type):
            try:
                
                date_ = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
                if date_.strftime('%A') == 'Monday':
                    days = 3
                else:
                    days = 1                                                  #                <-----------------------------

                
                exch = 'NFO' if self.config[index]['Exchange'] == 'NSE' else 'BFO'
                instrument = self.alice.get_instrument_for_fno(exch=exch, symbol=index, expiry_date=self.expiries_dict[index], is_fut=False,
                                                        strike=strike, is_CE=True if option_type == "CE" else False)

             

                from_datetime = datetime.datetime.now(pytz.timezone('Asia/Kolkata')) - datetime.timedelta(
                    days=2)  # From last & days
                to_datetime = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))  # To now
                interval = "1"  # ["1", "D"]
                is_indices = False  # For Getting index data
                df_ = self.alice.get_historical(instrument, from_datetime, to_datetime, interval, is_indices)
                print(df_)

                df_['datetime'] = pd.to_datetime(df_['datetime'])

                # Extract minutes from 'datetime'
                minutes = df_['datetime'].dt.minute

                target_minutes = [14, 29, 44, 59]

                # Filter rows where the minute is in the list
                filtered_df = df_[minutes.isin(target_minutes)]
                print(filtered_df['close'])

                # Create a dictionary entry with trading_symbol and close values
                ema_data_dic[instrument[InstrumentTuple.NAME]] = filtered_df['close'].tolist()


                #lst = []
                #for i in range(len(df_)):
                #    if (int(df_['datetime'][i].split(' ')[1].split(':')[1])) % 15 == 14:
                #        lst.append(df_['close'][i])

                #dic[trading_symbol] = lst

            except Exception as e:
                print(e)
                print("{} instrument not tradable".format(InstrumentTuple.NAME))


        for index in self.todays_trading_instrument:

            instruemnt = self.alice.get_scrip_info(self.alice.get_instrument_by_token('INDICES', int(self.config[index]['Token'])))

            atm = round(float(instruemnt['LTP']), -2)

            print(f"GENERATING EMA DATA FOR {index}........")
            print(f"NON TRADABLE INSTRUMENTS {index}:")

            for x in range(-15, 15):
                pull_ema_data(index, int(atm) + (x * self.config[index]['Strike_difference']), "CE")
                pull_ema_data(index, int(atm) + (x * self.config[index]['Strike_difference']), "PE")
            
            sleep(65)

            if os.path.exists("data_ema.json"):
                os.remove("data_ema.json")

            with open("data_ema.json", "w") as outfile:
                json.dump(ema_data_dic, outfile, indent=3)

            print('NEW "data_ema.json" GENERATED')

            return ema_data_dic

    def get_freeze_quantity(self,price):
        csv_file_path = 'quantity_freeze_nse.csv'

        df = pd.read_csv(csv_file_path)
        row = df[(df['FROM'] <= price) & (df['UP_TO'] >= price)].iloc[0]
        return int(row['QUANTITY_FREEZE_LIMIT'])


shared_memory = Shared_Memory('shared_memory')
symbol_obj_map = Symbol_Obj_Map('symbol_obj_map')


#RATIO, STRADDLE, STRADLE_STRANGLE COMBO related variables
expected_strikes_dict =   Shared_Memory('expected_strikes_dict')
current_strikes_dict = Shared_Memory('current_strikes_dict')
initial_short_quantity = Symbol_Obj_Map('initial_short_quantity') # Only for RATIO


#DELTA_NEUTRAL related variables

delta_dict_current = Shared_Memory('delta_dict_current')
delta_dict_expected = Shared_Memory('delta_dict_expected')
delta_dict = Shared_Memory('delta_dict')


data = DataGenerator(strategy = TradingStrategy.CALL_RATIO_DELTA , is_paper_trade = True)
