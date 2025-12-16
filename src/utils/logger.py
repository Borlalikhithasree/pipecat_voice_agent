
import os
import logging
from datetime import datetime

# logging file format
LOG_FILE=f"{datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.log"

# logging file
log_files=os.path.join(os.getcwd(),'logs',LOG_FILE)

os.makedirs(log_files,exist_ok=True)

# complete file path
LOG_FILE_PATH=os.path.join(log_files,LOG_FILE)

logging.basicConfig(filename=LOG_FILE_PATH,
                    format="[ %(asctime)s ] %(lineno)d %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)

if __name__=='__main__':
    logging.info('logging started')
