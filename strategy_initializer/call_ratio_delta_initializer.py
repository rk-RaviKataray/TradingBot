import helper_functions
import multiprocessing
from multiprocessing import Process
from strategies.call_ratio_delta_strategy import delta_neutral, initiale_hedges, Call_Ratio_Delta_Base, delta_updater
from UltraDict import UltraDict
from shared_memory import shared_memory,data,symbol_obj_map,Shared_Memory,Symbol_Obj_Map, delta_dict_current, delta_dict_expected, delta_dict
from strategies.trading_strategy import TradingStrategy
from shared_memory import expected_strikes_dict, current_strikes_dict, initial_short_quantity
import time



        

def Call_Ratio_Delta_Initializer(atm_dict):

    global days_to_expiry
    days_to_expiry = dict()

    for index in data.todays_trading_instrument:
        
        delta_dict_current.dictionary[index] = dict()
        delta_dict_expected.dictionary[index] = dict()
        delta_dict.dictionary[index] = dict()
        days = helper_functions.calculate_dates_to_expiry(data.expiries_dict[index])
        days_to_expiry[index] = days

        for delta in data.config[index]['Delta']:
            delta_dict_current.dictionary[index][delta] = {'CE': None, 'PE': None}
            delta_dict_expected.dictionary[index][delta] = {'CE': None, 'PE': None}

        delta_updater(index)

  
    pairs = [(index, delta) for index in delta_dict_expected.dictionary.keys() for delta in
             delta_dict_expected.dictionary[index].keys()]

    for pair in pairs:
        index = pair[0]
        delta = pair[1]

        while True:

            if delta_dict_expected.dictionary[index][delta]['CE'] != None and delta_dict_expected.dictionary[index][delta]['PE'] != None:

                atm_call_symbol = str(
                    helper_functions.get_symbol(index, atm_dict[index], 0, 'CE', data.expiries_dict[index]))

                ATM_CE_quantity = int( data.config[index]['OTM_quantity'] / round(shared_memory.dictionary[atm_call_symbol]['LP'] / shared_memory.dictionary[delta_dict_expected.dictionary[index][delta]['CE']]['LP'], 1))


                ATM_CE = Call_Ratio_Delta_Base(atm_call_symbol, ATM_CE_quantity * data.lot_size_dict[index] , True)

                ATM_CE.start()
             

                symbol_obj_map.dictionary[atm_call_symbol] = ATM_CE
        
                HEDGE_CE_quantity = data.config[index]['OTM_quantity'] - ATM_CE_quantity 

                initiale_hedges(index, atm_dict, HEDGE_CE_quantity)

                process = delta_neutral(index, delta)
                process.start()

                break

