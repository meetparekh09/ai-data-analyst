import sys
import pandas as pd
from pathlib import Path

from clients import get_openai_client
from util import get_logger
from data_acquisition import get_data
from preliminary_analysis import preliminary_analysis
from data_cleaning import data_cleaning
logger = get_logger(__name__)

path = "data/online_retail_II.csv"

def main():
    file_type = Path(path).suffix.replace(".", "")
    df = get_data(path, file_type, logger)
    if df is None:
        logger.error("Failed to get data")
        sys.exit(1)
    
    logger.info("Running preliminary analysis")
    preliminary_results, preliminary_description = preliminary_analysis(df, logger)
    logger.info(f"Preliminary results:\n{preliminary_results}")
    logger.info(f"Preliminary description:\n{preliminary_description}")

    logger.info("Running data cleaning")
    data_cleaning_report = data_cleaning(df, preliminary_results, preliminary_description, logger)
    logger.info(f"Data cleaning report:\n{data_cleaning_report}")

if __name__ == "__main__":
    main()
