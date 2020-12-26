import os
import re
import json
import codecs
import locale
import requests
import datetime as dt
from typing import Any, Tuple, Dict

import tabula               # type: ignore
from tabula import read_pdf # type: ignore
import pandas as pd         # type: ignore
import numpy as np          # type: ignore

from typing import Union, Optional, Tuple, List, cast

# ----------------------------------------
# Not to be used in the notebook.
import sys
import logging
from logging.handlers import RotatingFileHandler
# ----------------------------------------
temp_content_dir = os.path.join(os.sep, 'tmp')
ok_statuses = [200, 201, 202]

# ----------------------------------------
# init_logger
# ----------------------------------------
def init_logger(log_dir:str, file_name:str, log_level, std_out_log_level=logging.ERROR) -> None :
    """
    Logger initializzation for file logging and stdout logging with
    different level.

    :param log_dir: path for the logfile;
    :param log_level: logging level for the file logger;
    :param std_out_log_level: logging level for the stdout logger;
    :return:
    """
    root = logging.getLogger()
    dap_format = '%(asctime)s %(name)s %(levelname)s %(message)s'
    formatter = logging.Formatter(dap_format)
    # File logger.
    root.setLevel(logging.DEBUG)
    fh = RotatingFileHandler(os.path.join(log_dir, file_name), maxBytes=1000000, backupCount=5)
    fh.setLevel(log_level)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Stdout logger.
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(std_out_log_level)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    for _ in ("urllib3"):
        logging.getLogger(_).setLevel(logging.CRITICAL)

def get_web_file(url:str) -> Tuple[bool, Union[Exception, bytes]] :
    """
    
    :param url: 
    :return (rv, content):
    """
    print("get_web_file >>")
    print("Url: {u}".format(u=url))
    rv = False
    result_content:bytes = bytearray()
    try:
        result = requests.get(url)
        if result.status_code not in ok_statuses:
            print("Get data failed. Received error code: {er}".format(er=str(result.status_code)))
        else:
            result_content = result.content
    except Exception as ex:
        print("get_web_file failed - {ex}".format(ex=ex))
        return (False, ex)
    else:
        rv = True
    print("get_web_file ({rv}) <<".format(rv=rv))
    return (rv, result_content)    
        
def save_content_to_file(file_name:str, content:bytes) -> bool :
    """
    
    :param file_name: 
    :return rv:
    """
    rv = False
    try:
        with open(file_name, "wb") as fh:
            fh.write(content)
    except Exception as ex:
        print("save_content_to_file failed - {ex}".format(ex=ex))
    else:
        rv = True
    return rv
   
def pdf_to_dataframe(pdf_file_name:str) -> Tuple[bool, pd.DataFrame, dt.datetime]:
    """
    """
    print("pdf_to_dataframe ({fn}) >>".format(fn=pdf_file_name))
    rv = False
    df = None
    report_date:dt.datetime = dt.datetime(1964,8,3,0,0)
    try:
        df = tabula.read_pdf(pdf_file_name, pages='all')
        #print("Df list len: {l}".format(l=len(df)))
        
        csv_file = os.path.splitext(pdf_file_name)[0] + ".csv"
        tabula.convert_into(pdf_file_name, csv_file, output_format="csv", pages='all')
        list_reg = [] 
        with open(csv_file, "r") as fh:
            start = False
            end = False
            reg = re.compile("(\d{1,3}) (\d)")
            for line in fh:
                if line.startswith("Lombardia") == True:
                    start = True
                if line.startswith("TOTALE") == True:
                    end = True
                    start = False
                if start == True:
                    line = line.replace(".", "")
                    line = line.replace("+ ", "")
                    #line = line.replace(" ", ",")
                    line = reg.sub("\\1,\\2", line)
                    line = line.replace("\n", "")
                    list_reg.append(line)
                if 'Aggiornamento casi Covid-19' in line:
                    parts = line.split(" - ")
                    if len(parts) > 1:
                        report_date_s = parts[0]
                        if parts[0][0] == "\"":
                            report_date_s = parts[0][1:]
                        #print(report_date)
                        rv, report_date_rv = translate_to_date(report_date_s.split(" "))
                        if rv == False:
                            print("Error in date translation.")
                            return (False, df, report_date)
                        else:
                            report_date = cast(dt.datetime, report_date_rv)
                elif 'AGGIORNAMENTO ' in line:
                    parts = line.split(" ")
                    if len(parts) > 1:
                        report_date = dt.datetime.strptime(parts[1], '%d/%m/%Y')
                        print("RDate: {rd}".format(rd=report_date))
        
        df = pd.DataFrame([line.split(",") for line in list_reg])
        rv = True
        
    except Exception as ex:
        print("pdf_to_dataframe failed - {ex}".format(ex=ex))
    print("pdf_to_dataframe (rv={rv} - report_date={rd}) <<".format(rv=rv, rd=report_date))
    return (rv, df, report_date)

def translate_to_date(report_date:List[str])-> Tuple[bool, Union[Exception, dt.datetime]]:
    #print("translate_to_date {p} >>".format(p=str(dt)))
    rv = False
    date = None
    months_names = {
        "gennaio":    1
        ,"febbraio":  2
        ,"marzo":     3
        ,"aprile":    4
        ,"maggio":    5
        ,"giugno":    6
        ,"luglio":    7
        ,"agosto":    8
        ,"settembre": 9
        ,"ottobre":  10
        ,"novembre": 11
        ,"dicembre": 12
    }
    if len(report_date) >= 3 :
        try:
            day = report_date[0]
            year = report_date[2]
            month = months_names.get(report_date[1].lower())
            if month is not None:
                #print("Dt: {d}/{m}/{y}".format(d=day,m=month,y=year))
                date = dt.datetime(year=int(year), month=int(month), day=int(day))
                rv = True
            else:
                ex = Exception("Unknown month: {m}".format(m=report_date[1]))
                print("Error in date translation - {e}".format(e=ex))
                return (False, ex)
        except Exception as ex:
            print("Exception - {e}".format(e=ex))
            return (False, ex)
    else:
        exc = Exception("Wrong format: {dt}".format(dt=str(dt)))
        print("Error in date translation - {e}".format(e=exc))
        return (False, exc)
    #print("translate_to_date rv:{rv} - dt:{dt} <<".format(rv=rv,dt=str(date)))
    return (rv, date)
    
def refactor_region_df(df:pd.DataFrame, report_date:dt.datetime, pdf_version:str="v1") -> Tuple[bool, Any]:
    """
    
    :param df: 
    :param repord_date:
    :pdf_version: valid values are v1, v2, v3, v4, v5, v6;
    :return (rv, df_region):
    """
    print("refactor_region_df ({ver} - {dt}) >>".format(dt=report_date,ver=pdf_version))
    rv = False
    df_res = None
    try:
        df_res = df
        if pdf_version == "v1":
            df_res.rename(columns={df_res.columns[ 0]: "Regione"
                                  ,df_res.columns[ 1]: "Ricoverati con sintomi"
                                  ,df_res.columns[ 2]: "Terapia intensiva"
                                  ,df_res.columns[ 3]: "Isolamento domiciliare"
                                  ,df_res.columns[ 4]: "Totale attualmente positivi"
                                  ,df_res.columns[ 5]: "DIMESSI/GUARITI"
                                  ,df_res.columns[ 6]: "DECEDUTI"
                                  ,df_res.columns[ 7]: "CASI TOTALI - A"
                                  ,df_res.columns[ 8]: "INCREMENTO CASI TOTALI (rispetto al giorno precedente)"
                                  ,df_res.columns[ 9]: "Casi identificatidal sospettodiagnostico"
                                  ,df_res.columns[10]: "Casi identificatida attività discreening"
                                  ,df_res.columns[11]: "CASI TOTALI - B"
                                  ,df_res.columns[12]: "Totale casi testati"
                                  ,df_res.columns[13]: "Totale tamponi effettuati"
                                  ,df_res.columns[14]: "INCREMENTO TAMPONI" 
                          },
                      inplace = True)
        elif pdf_version in ["v6"]:
            df_res.rename(columns={df_res.columns[ 0]: "Regione"
                                  ,df_res.columns[ 1]: "Ricoverati con sintomi"
                                  ,df_res.columns[ 2]: "Terapia intensiva"
                                  ,df_res.columns[ 3]: "Ingressi delgiorno"
                                  ,df_res.columns[ 3]: "Terapia intensiva - INGRESSI del GIORNO"
                                  ,df_res.columns[ 4]: "Isolamento domiciliare"
                                  ,df_res.columns[ 5]: "Totale attualmente positivi"
                                  ,df_res.columns[ 6]: "DIMESSI/GUARITI"
                                  ,df_res.columns[ 7]: "DECEDUTI"
                                  ,df_res.columns[ 8]: "CASI TOTALI - A"
                                  ,df_res.columns[ 9]: "INCREMENTO CASI TOTALI (rispetto al giorno precedente)"
                                  ,df_res.columns[10]: "Totale persone testate"
                                  ,df_res.columns[11]: "Totale tamponi effettuati"
                                  ,df_res.columns[12]: "INCREMENTO TAMPONI" 
                          },
                      inplace = True)         

        elif pdf_version in ["v2", "v3"]:
            if pdf_version == "v3" and len(df.columns) == 12:
                df.drop([10], axis=1, inplace=True)
            df_res.rename(columns={df_res.columns[ 0]: "Regione"
                                  ,df_res.columns[ 1]: "Ricoverati con sintomi"
                                  ,df_res.columns[ 2]: "Terapia intensiva"
                                  ,df_res.columns[ 3]: "Isolamento domiciliare"
                                  ,df_res.columns[ 4]: "Totale attualmente positivi"
                                  ,df_res.columns[ 5]: "DIMESSI/GUARITI"
                                  ,df_res.columns[ 6]: "DECEDUTI"
                                  ,df_res.columns[ 7]: "CASI TOTALI - A"
                                  ,df_res.columns[ 8]: "INCREMENTO CASI TOTALI (rispetto al giorno precedente)"
                                  ,df_res.columns[ 9]: "Totale tamponi effettuati" 
                                  ,df_res.columns[10]: "Totale casi testati" 
                          },
                      inplace = True)
            
            df_res["Casi identificatidal sospettodiagnostico"] = np.nan
            df_res["Casi identificatida attività discreening"] = np.nan
            df_res["CASI TOTALI - B"] = np.nan
            df_res["INCREMENTO TAMPONI"] = np.nan

        elif pdf_version in ["v4"]:
            print("Columns num: {n}".format(n=len(df_res.columns)))
            if len(df_res.columns) == 11:
                df.drop([10], axis=1, inplace=True)
            df_res.rename(columns={df_res.columns[ 0]: "Regione"
                                  ,df_res.columns[ 1]: "Ricoverati con sintomi"
                                  ,df_res.columns[ 2]: "Terapia intensiva"
                                  ,df_res.columns[ 3]: "Isolamento domiciliare"
                                  ,df_res.columns[ 4]: "Totale attualmente positivi"
                                  ,df_res.columns[ 5]: "DIMESSI/GUARITI"
                                  ,df_res.columns[ 6]: "DECEDUTI"
                                  ,df_res.columns[ 7]: "CASI TOTALI - A"
                                  ,df_res.columns[ 8]: "INCREMENTO CASI TOTALI (rispetto al giorno precedente)"
                                  ,df_res.columns[ 9]: "Totale tamponi effettuati" 
                          },
                      inplace = True)
            
            df_res["Casi identificatidal sospettodiagnostico"] = np.nan
            df_res["Casi identificatida attività discreening"] = np.nan
            df_res["CASI TOTALI - B"] = np.nan
            df_res["INCREMENTO TAMPONI"] = np.nan
            df_res["Totale casi testati"] = np.nan
            
        elif pdf_version in ["v5"]:
            df_res.rename(columns={df_res.columns[ 0]: "Regione"
                                  ,df_res.columns[ 1]: "Ricoverati con sintomi"
                                  ,df_res.columns[ 2]: "Terapia intensiva"
                                  ,df_res.columns[ 3]: "Isolamento domiciliare"
                                  ,df_res.columns[ 4]: "Totale attualmente positivi"
                                  ,df_res.columns[ 5]: "DIMESSI/GUARITI"
                                  ,df_res.columns[ 6]: "DECEDUTI"
                                  ,df_res.columns[ 7]: "CASI TOTALI - A"
                                  ,df_res.columns[ 8]: "Totale tamponi effettuati" 
                          },
                      inplace = True)
            
            df_res["Casi identificatidal sospettodiagnostico"] = np.nan
            df_res["Casi identificatida attività discreening"] = np.nan
            df_res["CASI TOTALI - B"] = np.nan
            df_res["INCREMENTO TAMPONI"] = np.nan
            df_res["Totale casi testati"] = np.nan 
            df_res["INCREMENTO CASI TOTALI (rispetto al giorno precedente)"] = np.nan
  
        else:
            ex = Exception("Unknown pdf version: {pv}".format(pv=pdf_version))
            print("Error - {ex}".format(ex=ex))
            rv = False
            df_res = ex
        
        df_res["REPORT DATE"] = report_date #pd.to_datetime(report_date, format="%d/%m/%Y")
        rv = True  
        
    except Exception as ex:
        print("refactor_region_df failed - {ex}".format(ex=ex))
        rv = False
        df_res = ex
    print("refactor_region_df ({rv}) <<".format(rv=rv))
    return (rv, df_res)

def create_dataframe(pdf_url:str, local_file_path:str, pdf_version:str) -> Tuple[bool, Union[Exception, pd.DataFrame]] :
    print("create_dataframe >>")
    rv = False
    ret_data_frame:pd.DataFrame = None
    try:
        file_downloaded_rv = get_web_file(pdf_url)
        if file_downloaded_rv[0] == True:
            if save_content_to_file(local_file_path, cast(bytes, file_downloaded_rv[1])) == True:
                to_df_rv, df, report_date = pdf_to_dataframe(local_file_path)
                if to_df_rv == True:
                    rv, ret_data_frame = refactor_region_df(df, report_date, pdf_version)

    except Exception as ex:
        print("refactor_region_df failed - {ex}".format(ex=ex))
        return (False, ex)
        
    print("create_dataframe <<")
    return (rv, ret_data_frame)

def save_df_to_csv() -> bool :
    columns = "Regione","Ricoverati con sintomi,Terapia intensiva,Isolamento domiciliare,Totale attualmente positivi,DIMESSI/GUARITI,DECEDUTI,CASI TOTALI - A,INCREMENTO CASI TOTALI (rispetto al giorno precedente),Casi identificatidal sospettodiagnostico,Casi identificatida attività discreening,CASI TOTALI - B,Totale casi testati,Totale tamponi effettuati,INCREMENTOTAMPONI,REPORT DATE"

# ----------------------------------------
# Notebook content - END.
# ----------------------------------------

def main( args ) -> bool:
    log = logging.getLogger('Main')
    log.info("Main >>")
    rv = False
    try:
        pdf_file_name = "dpc-covid19-ita-scheda-regioni-20201202.pdf"
        pdf_url = "https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/schede-riepilogative/regioni/{fn}".format(fn=pdf_file_name)
        
        pdf_file = os.path.join(temp_content_dir, pdf_file_name)
        rv, region_df = create_dataframe(pdf_url=pdf_url, local_file_path=pdf_file, pdf_version="v1")
        print(read_pdf.shape)

    except Exception as ex:
        log.error("Exception caught - {ex}".format(ex=ex))
        rv = False
    log.info("Main ({rv}) <<".format(rv=rv))
    return rv

if __name__ == "__main__":
    init_logger('/tmp', "virus.log",log_level=logging.DEBUG, std_out_log_level=logging.DEBUG)
    rv = main(sys.argv)

    ret_val = 0 if rv == True else 1
    sys.exit(ret_val)

