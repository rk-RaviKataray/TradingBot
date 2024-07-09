from shared_memory import symbol_obj_map, delta_dict, delta_dict_current, delta_dict_expected,shared_memory,data
import multiprocessing
from multiprocessing import Process
import time
import threading
from strategies.base_strategy import Base_Strategy
import helper_functions
import schedule
from functools import partial

def get_delta_neutral_strikes(index, delta):
    return delta_dict_expected.dictionary[index][delta]


def get_current_short_strikes(index, delta):
    return delta_dict_current.dictionary[index][delta]

def initiale_hedges(index, atm, HEDGE_CE_quantity):
   

    call_hedge_instruemt = helper_functions.get_symbol(index, atm[index], data.config[index]['Hedge_strikes_away_from_atm'], 'CE', data.expiries_dict[index])
    call_hedge_obj = Call_Ratio_Delta_Base(call_hedge_instruemt,
                                                quantity=HEDGE_CE_quantity * data.lot_size_dict[index], is_hedge=True)
    symbol_obj_map.dictionary[call_hedge_instruemt] = call_hedge_obj
    call_hedge_obj.start()


def update_delta_dict_expected(index, target_delta_list, o_type_list):
  
    global delta_dict_expected

    for target_delta in target_delta_list:
        for o_type in o_type_list:
            compatible_keys = [key for key in delta_dict.dictionary[index] if helper_functions.get_option_type(key) == o_type]
            target_key = min(compatible_keys, key=lambda compatible_keys: abs(abs(delta_dict.dictionary[index][compatible_keys]) - target_delta))
            delta_dict_expected.dictionary[index][target_delta][o_type] = target_key



def delta_updater(index):        
    
    atm = helper_functions.get_atm(index)
    strikes = {'CE': [atm + x * data.config[index]['Strike_difference'] for x in range(-2,11)],
        'PE':[atm - x * data.config[index]['Strike_difference'] for x in range(-2,11)]}
    days_to_expiry = helper_functions.calculate_dates_to_expiry(data.expiries_dict[index])
    
    for instrument in shared_memory.dictionary.keys():
            
        if instrument.startswith(index) and instrument != index:

            o_type = helper_functions.get_option_type(instrument) 
            strike_price = helper_functions.get_strike_from_instrument(instrument)

            if strike_price in strikes[o_type]:

                #underlyingPrice, StrikePrice, interestRate, daysToExpiration,option_type, option_price
                delta_dict.dictionary[index][instrument] = helper_functions.calculate_delta(underlyingPrice=shared_memory.dictionary[index]["LP"],
                                                        StrikePrice=strike_price,
                                                        interestRate=data.config[index]['Interest_rate'],
                                                        daysToExpiration=days_to_expiry,
                                                        option_type=o_type, option_price=shared_memory.dictionary[instrument]["LP"])
                                                        
    update_delta_dict_expected(index,list(delta_dict_expected.dictionary[index].keys()), ['CE', 'PE'])
    print(delta_dict_expected.dictionary)
 

class delta_neutral(Process):

    def __init__(self, index, delta):
        super(delta_neutral, self).__init__()
        self.delta = delta
        self.index = index
       
   

    def run(self):
        partial_delta_updater = partial(delta_updater, self.index)
        schedule.every(10).seconds.do(partial_delta_updater)

        while True:
            if not shared_memory.dictionary[self.index]['STOP_ALGO_FLAG']:

                if shared_memory.dictionary[self.index]['SELL_INSTRUMENT_LIST'] != '':
                    symbol_obj_map.dictionary[shared_memory.dictionary[self.index]['SELL_INSTRUMENT_LIST']].close_long_pos() if shared_memory.dictionary[shared_memory.dictionary[self.index]['SELL_INSTRUMENT_LIST']]['POS'] == 'LONG' else symbol_obj_map.dictionary[shared_memory.dictionary[self.index]['SELL_INSTRUMENT_LIST']].go_short()
                    shared_memory.dictionary[self.index]['SELL_INSTRUMENT_LIST'] = ''

                if shared_memory.dictionary[self.index]['BUY_INSTRUMENT_LIST'] != '':
                    symbol_obj_map.dictionary[shared_memory.dictionary[self.index]['BUY_INSTRUMENT_LIST']].close_short_pos() if shared_memory.dictionary[shared_memory.dictionary[self.index]['BUY_INSTRUMENT_LIST']]['POS'] == 'SHORT' else symbol_obj_map.dictionary[shared_memory.dictionary[self.index]['BUY_INSTRUMENT_LIST']].go_long()
                    shared_memory.dictionary[self.index]['BUY_INSTRUMENT_LIST'] = ''

                if shared_memory.dictionary[self.index]['SQUARE_OFF_ALL_POSITIONS']:
                    for instrument in symbol_obj_map.dictionary.values():
                        if instrument != None and instrument.symbol.startswith(self.index):
                    
                            if shared_memory.dictionary[instrument.symbol]['POS'] == "SHORT":
                                instrument.close_short_pos()
                            elif shared_memory.dictionary[instrument.symbol]['POS'] == "LONG":
                                instrument.close_long_pos()
                        
                    shared_memory.dictionary[self.index]['STOP_ALGO_FLAG'] = True
                    break 

                schedule.run_pending()
                
                temp_dict = get_delta_neutral_strikes(index=self.index, delta=self.delta)
                expected_call_strike = temp_dict['CE']

                temp_dict_ = get_current_short_strikes(self.index, delta=self.delta)
                current_call_strike = temp_dict_['CE']

                if expected_call_strike != None and expected_call_strike != current_call_strike:
                    expected_call_strike_obj = symbol_obj_map.dictionary[expected_call_strike]

                    try:
                        if not symbol_obj_map.dictionary[expected_call_strike].is_hedge:

                            if current_call_strike != None:
                                current_call_strike_obj = symbol_obj_map.dictionary[current_call_strike]
                                if isinstance(current_call_strike_obj, Call_Ratio_Delta_Base):
                                    current_call_strike_obj.close_short_pos()

                            if not isinstance(expected_call_strike_obj, Call_Ratio_Delta_Base):
                                expected_call_strike_obj = Call_Ratio_Delta_Base(expected_call_strike,
                                                                        quantity= data.config[self.index]['OTM_quantity'] * data.lot_size_dict[self.index], is_hedge=False)
                                symbol_obj_map.dictionary[expected_call_strike] = expected_call_strike_obj
                                expected_call_strike_obj.start()
                            else:    
                                expected_call_strike_obj.go_short()

                            delta_dict_current.dictionary[self.index][self.delta]['CE'] = expected_call_strike

                    except:
                        if current_call_strike != None:
                                current_call_strike_obj = symbol_obj_map.dictionary[current_call_strike]
                                if isinstance(current_call_strike_obj, Call_Ratio_Delta_Base):
                                    current_call_strike_obj.close_short_pos()

                        if not isinstance(expected_call_strike_obj, Call_Ratio_Delta_Base):
                            expected_call_strike_obj = Call_Ratio_Delta_Base(expected_call_strike,
                                                                    quantity= data.config[self.index]['OTM_quantity'] * data.lot_size_dict[self.index], is_hedge=False)
                            symbol_obj_map.dictionary[expected_call_strike] = expected_call_strike_obj
                            expected_call_strike_obj.start()
                        else:    
                            expected_call_strike_obj.go_short()

                        delta_dict_current.dictionary[self.index][self.delta]['CE'] = expected_call_strike

                time.sleep(0.5)



class Call_Ratio_Delta_Base(Base_Strategy):

    def __init__(self,symbol, quantity, is_hedge):
        super().__init__(symbol, quantity, is_hedge)