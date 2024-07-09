from shared_memory import data, shared_memory
import os
import datetime
import pytz
import json
import time
import helper_functions

global pnl_list_for_dynamic_graph, html
pnl_list_for_dynamic_graph = dict()

for index in data.todays_trading_instrument:
    pnl_list_for_dynamic_graph[index] = list()


class frontend_data:

    def __init__(self, index):
        self.index = index
        self.TOTAL_PNL_list = []
        self.TOTAL_BROKERAGE_list = []
        self.TOTAL_ENTRIES_list = []
        self.TOTAL_PNL = 0
        self.NET_PNL = 0
        self.TOTAL_BROKERAGE=0
        self.TOTAL_ENTRIES=0

    def generate_individual_instrument_table_data(self):
        updated_html = ''
        
        for instrument in reversed(shared_memory.dictionary.keys()):

            if instrument.startswith(self.index) and shared_memory.dictionary[instrument]['NOE'] > 0:

                buttons_for_options = f"""
                    <td> 
                        <div style="display: flex; gap: 1px;">
                            <form action="/buy?instrument={instrument}" method="post">
                                <button id="buy-button" type="submit">B</button>
                            </form>

                            <form action="/sell?instrument={instrument}" method="post">
                                <button id="sell-button" type="submit">S</button>
                            </form>
                            
                            <button onclick="showPopup('{instrument}')" type="submit" id="pnl_graph_button"> 
                                <i class="fa fa-line-chart"></i> 
                            </button>
                            
                            <button onclick="showPopup_positionalData('{instrument}')" type="submit" id="positional_data_button"> 
                                <i class="fa fa-align-center"></i> 
                            </button>
                            
                        </div>
                        
                    </td>
                
                """
                buttons_for_index = f"""
                    <td> 
                        <div style="display: flex; gap: 1px;">
                            

                            <form action="/increment_atm?index={self.index}" method="post">
                                <button id="increment-atm" type="submit">
                                    <i class="fa fa-plus-circle"></i>
                                </button>
                            </form>

                            <form action="/hold_atm?index={self.index}" method="post">
                               <button id="hold-atm" type="submit" onclick="changeButtonText()">Hold ATM</button>
                            </form>

                             <form action="/decrement_atm?index={self.index}" method="post">
                                <button id="decrement-atm" type="submit">
                                    <i class="fa fa-minus-circle"></i>
                                </button>
                            </form>
                            
                            
                        </div>

                        <div style="display: flex; gap: 1px;">
                            <button onclick="showPopup('{instrument}')" type="submit" id="pnl_graph_button"> 
                                    <i class="fa fa-line-chart"></i> 
                            </button>
                            
                            <form action="/square_off_all_positions?index={self.index}" method="post">
                                    <button id="square-off-button" type="submit">Square off</button>
                            </form>
                            <form action="/refresh_feed" method="post">
                                    <button id="refersh_feed" type="submit">
                                        <i class="fa fa-refresh" ></i>
                                    </button>
                            </form>
                        </div>
                        
                    </td>
                
                """
                
                background_color = ''
                if shared_memory.dictionary[instrument]["POS"] == 'LONG':
                    background_color = '#D6EEEE'

                elif shared_memory.dictionary[instrument]["LAST_ENTRY"] == 0:
                    background_color = '#f6efc6'

                font_color = '#009900' if shared_memory.dictionary[instrument]["PNL"] > 0 else '#fa2723'

                action_buttons = buttons_for_index if instrument == self.index else buttons_for_options
                
                updated_html = updated_html + f"""
                <tr style="background-color: {background_color};">   
                    <td onclick="showPopup_positionalData('{instrument}')">  {instrument}   </td>
                    <td>  {round(shared_memory.dictionary[instrument]["LP"], 2)}   </td>
                    <td>  {shared_memory.dictionary[instrument]["POS"]}   </td>
                    <td onclick="showPopup('{instrument}')" style="color:{font_color}">  {round(shared_memory.dictionary[instrument]["PNL"], 2)}   </td>
                    <td>  {round(shared_memory.dictionary[instrument]["BROKERAGE"], 2)}   </td>
                    <td>  {round(shared_memory.dictionary[instrument]["LAST_ENTRY"], 2)}   </td>
                    <td>  {int(shared_memory.dictionary[instrument]["NOE"])}   </td>
                    <td>  {int(shared_memory.dictionary[instrument]["QUANTITY"])}   </td>
                """ + action_buttons + "</tr>"

                self.TOTAL_PNL_list.append(shared_memory.dictionary[instrument]["PNL"])
                self.TOTAL_BROKERAGE_list.append(shared_memory.dictionary[instrument]["BROKERAGE"])
                self.TOTAL_ENTRIES_list.append(shared_memory.dictionary[instrument]["NOE"])

        return updated_html

    def generate_summary_table_data(self):
        self.TOTAL_PNL = round(sum(self.TOTAL_PNL_list), 2)
        self.NET_PNL = round((sum(self.TOTAL_PNL_list) - sum(self.TOTAL_BROKERAGE_list)), 2)
        self.TOTAL_BROKERAGE = round(sum(self.TOTAL_BROKERAGE_list), 2)
        self.TOTAL_ENTRIES = sum(self.TOTAL_ENTRIES_list)

        if self.NET_PNL <= -50000:
            helper_functions.square_off_all_positions(self.index)


    def push_candle_data_to_database(self,pnl_list):
        if not os.path.exists(f"./instrument_data/{data.strategy}/{self.index}"):
            os.makedirs(f"./instrument_data/{data.strategy}/{self.index}")

        if datetime.datetime.now(pytz.timezone('Asia/Kolkata')).second == 00:
            
            with open(f"./instrument_data/{data.strategy}/{self.index}/candle_data.jsonl", 'a') as candle_data_file:
                time_ = int(datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%s'))
             
                open_ = pnl_list[0]
                high_ = max(pnl_list)
                low_ = min(pnl_list)
                close_ = int(self.TOTAL_PNL)
                candle_data_to_append = {"time": int(time_), "open": open_, "high": high_,
                                           "low": low_,
                                           "close": close_}
                json.dump(candle_data_to_append, candle_data_file)
                candle_data_file.write('\n')
                candle_data_file.flush()
                os.fsync(candle_data_file)
                time.sleep(1)
                return True

        return False

    def generate_summary_table_html(self):
        font_kolor_total = '#009900' if self.NET_PNL > 0 else '#fa2723'

        html_ = f"""
           
                    <td>  {self.TOTAL_PNL}   </td>
                    <td>  {self.TOTAL_BROKERAGE}   </td>
                    <td onclick="showPopup({self.index})" style="color:{font_kolor_total}">  {self.NET_PNL}   </td>
                    <td>  {self.TOTAL_ENTRIES}   </td>
           
            """
        return html_

    def generate_summary_table_html_header_rows(self):

        html_header_rows = f"""
                    <td>  <strong> {self.index}_TOTAL_PNL  </strong> </td>
                    <td>  <strong> {self.index}_TOTAL_BROKERAGE  </strong>  </td>
                    <td>  <strong> {self.index}_NET_PNL  </strong>  </td>
                    <td>  <strong> {self.index}_TOTAL_ENTRIES  </strong>  </td>
            """
        return html_header_rows


def get_frontend_data_():

    obj_list = []
    for index in data.todays_trading_instrument: 
        obj = frontend_data(index)
        obj_list.append(obj)

    consolidated_tbody_data_individual= ''
    summary_table_html_header_rows = ''

    for obj in obj_list:
        consolidated_tbody_data_individual = consolidated_tbody_data_individual + obj.generate_individual_instrument_table_data()
        summary_table_html_header_rows = summary_table_html_header_rows + obj.generate_summary_table_html_header_rows()


    individual_table_html = f"""
     
        <table class="table table-striped" id="rearrangeable-table">
            <thead class="bg-light sticky-top top-0">
                <tr>
                    <td>  <strong> INSTRUMENT  </strong> </td>
                    <td>  <strong> LP  </strong>  </td>
                    <td>  <strong> POS  </strong>  </td>
                    <td>  <strong> PNL  </strong>  </td>
                    <td>  <strong> BROKERAGE  </strong>  </td>
                    <td>  <strong> LAST_ENTRY </strong>   </td>
                    <td>  <strong> NOE  </strong>  </td>
                    <td>  <strong> QUANTITY  </strong>  </td>
                    <td>  <strong> ACTION  </strong>  </td>

                </tr>
            </thead>
            <tbody>
                {consolidated_tbody_data_individual}
            </tbody>
        </table>

    """

    for obj in obj_list:
        obj.generate_summary_table_data()

    consolidated_tbody_data_summary = ''
    for obj in obj_list:
        consolidated_tbody_data_summary = consolidated_tbody_data_summary + obj.generate_summary_table_html()

    consolidated_tbody_data_summary = "<tr class='bg-light sticky-top top-0'>" + consolidated_tbody_data_summary + "</tr>"

    summary_table_html_header_rows = ''
    for obj in obj_list:
        summary_table_html_header_rows = summary_table_html_header_rows + obj.generate_summary_table_html_header_rows()
        
        pnl_list_for_dynamic_graph[obj.index].append(obj.TOTAL_PNL)
        res = obj.push_candle_data_to_database(pnl_list_for_dynamic_graph[obj.index])
        if res:
            pnl_list_for_dynamic_graph[obj.index].clear()

    summary_table_html = f"""
    <table class="table table-striped">
            <thead>
                <tr>
                    {summary_table_html_header_rows}
                </tr>
            </thead>
            {consolidated_tbody_data_summary}
        </table>
        """

    html = {"individual_html": individual_table_html, "summary_html": summary_table_html}
    for obj in obj_list:
        del obj

    return html

