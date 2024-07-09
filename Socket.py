from UltraDict import UltraDict
import helper_functions
from shared_memory import data,shared_memory,symbol_obj_map
import json
import datetime
import pytz


def socket():
    global subscribe_flag,socket_opened,LTP
    subscribe_flag = False
    socket_opened = False
    
    def socket_open():  # Socket open callback function
        print("Connected")
        global socket_opened
        socket_opened = True
        if subscribe_flag:  # This is used to resubscribe the script when reconnect the socket.
       
            data.alice.subscribe(data.subscribe_list)

    def socket_close():  # On Socket close this callback function will trigger
        global socket_opened, LTP
        socket_opened = False
        LTP = 0
        print("Closed")

    def socket_error(message):  # Socket Error Message will receive in this callback function
        global LTP
        LTP = 0
        print("Error :", message)

    def feed_data(message):  # Socket feed data will receive in this callback function
        global LTP, subscribe_flag
        LTP = 0

        feed_message = json.loads(message)
        if feed_message["t"] == "ck":
            print("Connection Acknowledgement status :%s (Websocket Connected)" % feed_message["s"])
            subscribe_flag = True
            print("subscribe_flag :", subscribe_flag)
            print("-------------------------------------------------------------------------------")
            pass
        elif feed_message["t"] == "tk":
            print("Token Acknowledgement status :%s " % feed_message)
            print("-------------------------------------------------------------------------------")
            Token_Acknowledgement_status = feed_message
          
            if 'ts' not in Token_Acknowledgement_status.keys():
                for index in data.todays_trading_instrument: 
                    if data.config[index]['Token'] == int(Token_Acknowledgement_status['tk']):
                        #shared_memory.dictionary[index]['LP'] = float(Token_Acknowledgement_status['lp'])
                        shared_memory.dictionary[index] = {"TOKEN": data.config[index]['Token'], "LP": float(Token_Acknowledgement_status['lp']), "POS": "", "PNL": 0.0, "LAST_ENTRY": 0, "LAST_EXIT": 0, "NOE": 1,
                            "BROKERAGE": 0, "QUANTITY": 0, "INCREMENT_ATM":False, "HOLD_ATM":False, "DECREMENT_ATM":False, "STOP_ALGO_FLAG":False,"SQUARE_OFF_ALL_POSITIONS": False,
                            "BUY_INSTRUMENT_LIST":'' ,"SELL_INSTRUMENT_LIST":''  }
                        symbol_obj_map.dictionary[Token_Acknowledgement_status['ts']] = None
            

            else:
                if Token_Acknowledgement_status["ts"] not in shared_memory.dictionary:
        
                    shared_memory.dictionary[Token_Acknowledgement_status['ts']] = {"TOKEN": int(Token_Acknowledgement_status['tk']),
                                                                    "LP": float(Token_Acknowledgement_status['lp']), "POS": "", "PNL": 0.0, "LAST_ENTRY": 0.0,
                                                                    "EMA": 0.0, "FCH": 0.0, "NOE": 0.0,
                                                                    "BROKERAGE": 0.0, "QUANTITY": 0,
                                                                    'LAST_EXIT': 0.0,
                                                                    'PNL_BOOKED': 0}
                    symbol_obj_map.dictionary[Token_Acknowledgement_status['ts']] = None
        else:
            #print("Feed :", feed_message)
            Feed = feed_message
            for x in shared_memory.dictionary.keys():
                if int(Feed["tk"]) == shared_memory.dictionary[x]["TOKEN"]:
                    shared_memory.dictionary[x]["LP"] = float(Feed['lp']) if 'lp' in feed_message else shared_memory.dictionary[x]["LP"]

    # Socket Connection Request
    data.alice.start_websocket(socket_open_callback=socket_open, socket_close_callback=socket_close,
                          socket_error_callback=socket_error, subscription_callback=feed_data, run_in_background=True)
  
    while not socket_opened:
        pass

    # Subscribe the Instrument
    print("Initial Subscribe for Index at :", datetime.datetime.now(pytz.timezone('Asia/Kolkata')))

    for index in data.todays_trading_instrument: 
        data.subscribe_list.append(data.alice.get_instrument_by_token('INDICES', int(data.config[index]['Token'])))

    data.alice.subscribe(data.subscribe_list)