
from shared_memory import data, shared_memory
import threading
import logging
import os
import datetime
import pytz
import time
import json
import order_manager
from order_manager import order_type
import math

class Base_Strategy(threading.Thread):
    symbol_list = []

    def __init__(self, symbol, quantity, is_hedge):

        threading.Thread.__init__(self)
        self.symbol = str(symbol)
        Base_Strategy.symbol_list.append(self.symbol)
        
        self.quantity = quantity
        self.is_hedge = is_hedge
        
        
        self.pnl_list_for_dynamic_graph = []
        self.logger = logging.getLogger(self.symbol)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        self.base_log_file = f'./instrument_data/{data.strategy}/{self.symbol}'

        if not os.path.exists(self.base_log_file):
            # Create the folder
            os.makedirs(self.base_log_file)

        # Create a console handler and add it to the logger
        log_file = os.path.join(self.base_log_file, f"{self.symbol}.log")
        ch = logging.FileHandler(filename=log_file)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        for index in data.todays_trading_instrument:
            if self.symbol.startswith(index):
                self.exchange = 'NFO' if data.config[index]['Exchange'] == 'NSE' else 'BFO'
                self.index = index

        self.freeze_limit = data.quantity_freeze_dict[self.index]
        self.lot_size = data.lot_size_dict[self.index]

        self.sl = 9999
        self.sl_ranges = {
                            (100, float('inf')): 0.27,
                            (75, 100): 0.32,
                            (30, 75): 0.42,
                            (20, 30): 0.52,
                            (15, 20): 0.62,
                            (10, 15): 0.77,
                            (5, 10): 0.82,
                            (2, 5): 1.2,
                            (0, 2): 4.2,
                         }



    def run(self):

        self.logger.debug('***********************************NEW SESSION*************************************')

        if not os.path.exists(self.base_log_file):
            os.makedirs(self.base_log_file)

        with open(f"{self.base_log_file}/candle_data.jsonl", 'a') as self.candle_data_file:


            start_time = int(9) * 60 * 60 + int(15) * 60 + int(58)
            time_now = (datetime.datetime.now(pytz.timezone('Asia/Kolkata')).hour * 60 * 60 + datetime.datetime.now(
                pytz.timezone('Asia/Kolkata')).minute * 60 + datetime.datetime.now(
                pytz.timezone('Asia/Kolkata')).second)
            end_time = int(15) * 60 * 60 + int(30) * 60 + int(59)

            shared_memory.dictionary[self.symbol]["QUANTITY"] = self.quantity

   
            if self.is_hedge:
                self.go_long()
            else:
                self.go_short()

            while True:
                while start_time < \
                        (datetime.datetime.now(pytz.timezone('Asia/Kolkata')).hour * 60 * 60 + datetime.datetime.now(
                            pytz.timezone('Asia/Kolkata')).minute * 60 + datetime.datetime.now(
                            pytz.timezone('Asia/Kolkata')).second) \
                        < end_time and not shared_memory.dictionary[self.index]['STOP_ALGO_FLAG']:

                    time.sleep(0.3)
                    self.pnl_list_for_dynamic_graph.append(float(shared_memory.dictionary[self.symbol]["PNL"]))

                    if datetime.datetime.now(pytz.timezone('Asia/Kolkata')).second == 00:
                        time_ = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%s')
                        open_ = self.pnl_list_for_dynamic_graph[0]
                        high_ = max(self.pnl_list_for_dynamic_graph)
                        low_ = min(self.pnl_list_for_dynamic_graph)
                        close_ = int(shared_memory.dictionary[self.symbol]["PNL"])
                        self.pnl_list_for_dynamic_graph.clear()
                        candle_data_to_append = {"time": int(time_) , "open": open_, "high": high_, "low": low_,
                                                 "close": close_}
                        json.dump(candle_data_to_append, self.candle_data_file)
                        self.candle_data_file.write('\n')
                        self.candle_data_file.flush()
                        os.fsync(self.candle_data_file)
                        time.sleep(1)


                    if shared_memory.dictionary[self.symbol]['POS'] == 'LONG':
                        shared_memory.dictionary[self.symbol]['PNL'] = shared_memory.dictionary[self.symbol]['PNL_BOOKED'] + (
                                (float(shared_memory.dictionary[self.symbol]["LP"]) - shared_memory.dictionary[self.symbol][
                                    'LAST_ENTRY']) * self.quantity)


                    elif shared_memory.dictionary[self.symbol]['POS'] == 'SHORT':
                        shared_memory.dictionary[self.symbol]['PNL'] = shared_memory.dictionary[self.symbol]['PNL_BOOKED'] + (
                                (shared_memory.dictionary[self.symbol]['LAST_ENTRY'] - float(
                                    shared_memory.dictionary[self.symbol]["LP"])) * self.quantity)
                        
                    if shared_memory.dictionary[self.symbol]["LP"] > self.sl:
                        self.close_short_pos()
                        
                break

    def go_long(self):
        if shared_memory.dictionary[self.symbol]["POS"] != "LONG":
            
            if not self.quantity % self.lot_size == 0:
                raise Exception(f'{self.symbol} Quantity not a multiple of lot size, expected a multiple of {self.lot_size} got {self.quantity}.')

            no_of_orders = math.ceil(self.quantity / self.freeze_limit)
            last_order_quantity = self.quantity % self.freeze_limit

            for order in range(no_of_orders):
                
                qunatity_ = last_order_quantity if order == no_of_orders - 1 else self.freeze_limit
                if not data.paper_trade:
                    order_manager.place_order(self.symbol,qunatity_,self.exchange,order_type.BUY)

            shared_memory.dictionary[self.symbol]["NOE"] = shared_memory.dictionary[self.symbol]["NOE"] + 1
            shared_memory.dictionary[self.symbol]["POS"] = "LONG"
            self.logger.debug('{} went long at price-{}'.format(self.symbol, shared_memory.dictionary[self.symbol]["LP"]))
            shared_memory.dictionary[self.symbol]['LAST_ENTRY'] = float(shared_memory.dictionary[self.symbol]["LP"])

    def go_short(self):
     
        if shared_memory.dictionary[self.symbol]["POS"] != "SHORT":

            if not self.quantity % self.lot_size == 0:
                raise Exception(f'{self.symbol} Quantity not a multiple of lot size, expected a multiple of {self.lot_size} got {self.quantity}.')

            no_of_orders = math.ceil(self.quantity / self.freeze_limit)
            last_order_quantity = self.quantity % self.freeze_limit

            for order in range(no_of_orders):
                
                qunatity_ = last_order_quantity if order == no_of_orders - 1 else self.freeze_limit
                if not data.paper_trade:
                    order_manager.place_order(self.symbol,qunatity_,self.exchange,order_type.SELL)


            shared_memory.dictionary[self.symbol]["NOE"] = shared_memory.dictionary[self.symbol]["NOE"] + 1
            shared_memory.dictionary[self.symbol]["POS"] = "SHORT"
            self.logger.debug('{}  -  {} went short at price-{}'.format(datetime.datetime.now(pytz.timezone('Asia/Kolkata')) , self.symbol,
                                                                 shared_memory.dictionary[self.symbol]["LP"]
                                                                 ))
            shared_memory.dictionary[self.symbol]['LAST_ENTRY'] = float(shared_memory.dictionary[self.symbol]["LP"])
            self.set_sl(shared_memory.dictionary[self.symbol]['LAST_ENTRY'])
       
    def close_long_pos(self):

        if shared_memory.dictionary[self.symbol]['POS'] == 'LONG':

            if not self.quantity % self.lot_size == 0:
                    raise Exception(f'{self.symbol} Quantity not a multiple of lot size, expected a multiple of {self.lot_size} got {self.quantity}.')

            self.logger.debug('{}  -  square-off {} long_position at price {}'.format(datetime.datetime.now(pytz.timezone('Asia/Kolkata')),
                                                                                      self.symbol, shared_memory.dictionary[self.symbol]['LP']))
            shared_memory.dictionary[self.symbol]['POS'] = ' '
            shared_memory.dictionary[self.symbol]['LAST_EXIT'] = shared_memory.dictionary[self.symbol]['LP']

            no_of_orders = math.ceil(self.quantity / self.freeze_limit)
            last_order_quantity = self.quantity % self.freeze_limit
            last_transaction_brokerage = 0

            for order in range(no_of_orders):
                
                qunatity_ = last_order_quantity if order == no_of_orders - 1 else self.freeze_limit
                if not data.paper_trade:
                    order_manager.place_order(self.symbol,qunatity_,self.exchange,order_type.BUY)

                last_transaction_brokerage = last_transaction_brokerage + self.calc_brokerage(
                shared_memory.dictionary[self.symbol]['LAST_ENTRY'],
                shared_memory.dictionary[self.symbol]['LAST_EXIT'], "SHORT",qunatity_)

        
            self.logger.debug(
                f"last entry was at : {shared_memory.dictionary[self.symbol]['LAST_ENTRY']} and exit at: {shared_memory.dictionary[self.symbol]['LAST_EXIT']}")

            last_transaction_pnl = (shared_memory.dictionary[self.symbol]['LAST_EXIT'] -
                                    shared_memory.dictionary[self.symbol]['LAST_ENTRY']) * self.quantity 
            

            self.logger.debug(f"long pnl booked for last transaction:{last_transaction_pnl}")

            shared_memory.dictionary[self.symbol]['PNL_BOOKED'] = shared_memory.dictionary[self.symbol]['PNL_BOOKED'] + last_transaction_pnl

            self.logger.debug(f"pnl booked until now:{shared_memory.dictionary[self.symbol]['PNL_BOOKED']}")

            shared_memory.dictionary[self.symbol]['BROKERAGE'] = shared_memory.dictionary[self.symbol]['BROKERAGE'] + last_transaction_brokerage
            self.logger.debug(f"Brokerage for last transaction:{last_transaction_brokerage}")
            self.logger.debug(f"Total Brokerage:{shared_memory.dictionary[self.symbol]['BROKERAGE']}")
            self.logger.debug('-----------------------------------------------------------------------')

        

    def close_short_pos(self):

        if shared_memory.dictionary[self.symbol]['POS'] == 'SHORT':

            if not self.quantity % self.lot_size == 0:
                    raise Exception(f'{self.symbol} Quantity not a multiple of lot size, expected a multiple of {self.lot_size} got {self.quantity}.')

            self.logger.debug('square-off {} short_position at price {}'.format(self.symbol, shared_memory.dictionary[self.symbol]['LP']))
            
            shared_memory.dictionary[self.symbol]['LAST_EXIT'] = shared_memory.dictionary[self.symbol]['LP']

            no_of_orders = math.ceil(self.quantity / self.freeze_limit)
            last_order_quantity = self.quantity % self.freeze_limit
            last_transaction_brokerage = 0

            for order in range(no_of_orders):
                
                qunatity_ = last_order_quantity if order == no_of_orders - 1 else self.freeze_limit
                if not data.paper_trade:
                    order_manager.place_order(self.symbol,qunatity_,self.exchange,order_type.BUY)

                last_transaction_brokerage = last_transaction_brokerage + self.calc_brokerage(
                shared_memory.dictionary[self.symbol]['LAST_ENTRY'],
                shared_memory.dictionary[self.symbol]['LAST_EXIT'], "LONG", qunatity_)
            
            shared_memory.dictionary[self.symbol]['POS'] = ' '
            self.sht = False
            self.sl = 9999

            self.logger.debug(
                f"last entry was at : {shared_memory.dictionary[self.symbol]['LAST_ENTRY']} and exit at: {shared_memory.dictionary[self.symbol]['LAST_EXIT']}")


            last_transaction_pnl = (shared_memory.dictionary[self.symbol]['LAST_ENTRY'] -
                                    shared_memory.dictionary[self.symbol]['LAST_EXIT']) * self.quantity
        

            self.logger.debug(f"short pnl booked for last transaction:{last_transaction_pnl}")

            shared_memory.dictionary[self.symbol]['PNL_BOOKED'] = shared_memory.dictionary[self.symbol]['PNL_BOOKED'] + last_transaction_pnl

            self.logger.debug(f"short pnl booked until now:{shared_memory.dictionary[self.symbol]['PNL_BOOKED']}")

            shared_memory.dictionary[self.symbol]['BROKERAGE'] = shared_memory.dictionary[self.symbol]['BROKERAGE'] + last_transaction_brokerage
            self.logger.debug(f"Brokerage for last transaction:{last_transaction_brokerage}")
            self.logger.debug(f"Total Brokerage:{shared_memory.dictionary[self.symbol]['BROKERAGE']}")
            self.logger.debug('-----------------------------------------------------------------------')

    def hedge(self):
        self.go_long()
        self.logger.debug('HEDGE-{} went long at price-{}'.format(self.symbol,
                                                                  shared_memory.dictionary[self.symbol]["LP"]))

        start_time = int(9) * 60 * 60 + int(19) * 60 + int(30)
        time_now = (datetime.datetime.now(pytz.timezone('Asia/Kolkata')).hour * 60 * 60 + datetime.datetime.now(
            pytz.timezone('Asia/Kolkata')).minute * 60 + datetime.datetime.now(pytz.timezone('Asia/Kolkata')).second)
        end_time = int(15) * 60 * 60 + int(30) * 60 + int(59)

        while start_time <= time_now <= end_time:
            time_now = (datetime.datetime.now(pytz.timezone('Asia/Kolkata')).hour * 60 * 60 + datetime.datetime.now(
                pytz.timezone('Asia/Kolkata')).minute * 60 + datetime.datetime.now(
                pytz.timezone('Asia/Kolkata')).second)
            self.pnl_list_for_dynamic_graph.append(float(shared_memory.dictionary[self.symbol]["PNL"]))
            if shared_memory.dictionary[self.symbol]['POS'] == 'LONG':
                shared_memory.dictionary[self.symbol]['PNL'] = (
                        (shared_memory.dictionary[self.symbol]['LP'] - shared_memory.dictionary[self.symbol]['LAST_ENTRY']) * self.quantity)

                if datetime.datetime.now(pytz.timezone('Asia/Kolkata')).second == 00:
                    time_ = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%s')
                    open_ = self.pnl_list_for_dynamic_graph[0]
                    high_ = max(self.pnl_list_for_dynamic_graph)
                    low_ = min(self.pnl_list_for_dynamic_graph)
                    close_ = int(shared_memory.dictionary[self.symbol]["PNL"])
                    self.pnl_list_for_dynamic_graph.clear()
                    candle_data_to_append = {"time": int(time_) + 19800, "open": open_, "high": high_, "low": low_,
                                             "close": close_}  # we add 19800 to get time in IST
                    json.dump(candle_data_to_append, self.candle_data_file)
                    self.candle_data_file.write('\n')
                    self.candle_data_file.flush()
                    os.fsync(self.candle_data_file)
                    time.sleep(1)
                time.sleep(1)

    def exit_open_positions(self):
        self.current_time = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        if self.lng:
            self.long_exit_price.append(shared_memory.dictionary[self.symbol]["LP"])
            print("exited long - {} at price-{}, time {}:{}:{}".format(self.symbol,
                                                                       shared_memory.dictionary[self.symbol]["LP"],
                                                                       datetime.datetime.now(
                                                                           pytz.timezone('Asia/Kolkata')).hour,
                                                                       datetime.datetime.now(
                                                                           pytz.timezone(
                                                                               'Asia/Kolkata')).minute,
                                                                       datetime.datetime.now(
                                                                           pytz.timezone(
                                                                               'Asia/Kolkata')).second))
            self.long_brokerage = self.long_brokerage + self.calc_brokerage(
                self.long_entry_price[len(self.long_entry_price) - 1], self.long_exit_price[
                    len(self.long_exit_price) - 1], "LONG")

            self.lng = False

        elif self.sht:
            self.short_exit_price.append(shared_memory.dictionary[self.symbol]["LP"])
            print("exited short - {} at price-{}".format(self.symbol, shared_memory.dictionary[self.symbol]["LP"]))

            self.short_brokerage = self.short_brokerage + self.calc_brokerage(
                self.short_entry_price[len(self.short_entry_price) - 1], self.short_exit_price[
                    len(self.short_exit_price) - 1], "SHORT")

            self.sht = False

    def calc_brokerage(self, entry_, exit_, pos, quantity):
        Brokerage = 30
        STT = (float(exit_) if pos == "LONG" else float(entry_)) * 0.0005 * float(quantity)
        ex_tsn_chg = ((float(entry_ + exit_) * 0.00053) if self.exchange == 'NFO' else (float(entry_ + exit_) * 0.00037)) * float(quantity)
        SEBI_charges = (float(entry_ + exit_)) * quantity * 0.000001
        GST = (Brokerage + SEBI_charges + ex_tsn_chg) * 0.18
        stamp_duty = (float(entry_) if pos == "LONG" else float(exit_)) * 0.00003 * float(quantity)
        totalcharges = Brokerage + SEBI_charges + ex_tsn_chg + stamp_duty + GST + STT
        return totalcharges
    
    def set_sl(self,LP):
        
        for (start, end), percentage in self.sl_ranges.items():
            if start <= LP < end:
                self.sl =  (percentage * LP) + LP
                self.logger.debug('SL set for {} at {}'.format(self.symbol, self.sl))

   


