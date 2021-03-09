#!/bin/bash

usage="Usage: run-data-downloader.sh [data|vac|etl]"

VIRTUALENV=/home/giovanni/add-on/venv/bin/activate
source ${VIRTUALENV}

DATA_SCRIPT_PATH=./src/DataDownloader.py
VAC_SCRIPT_PATH=./src/VacciniDownload.py
ETL_SCRIPT_PATH=./src/ETL.py

case $1 in
data)
  echo "Download regional COVID19 data."
  python ${DATA_SCRIPT_PATH} $2 $3 $4 $5
  ;;
etl)
  echo "Run etl."
  python ${ETL_SCRIPT_PATH}
  ;;
vac)
  echo "Download vaccination dataset."
  python ${VAC_SCRIPT_PATH} --download
  ;;
help|h)
  echo $usage
  ;;
*)
  echo "Download regional COVID19 data."
  python ${DATA_SCRIPT_PATH} $1 $2 $3 $4
  ;;
esac

