import logging
import logging.config
import os
import sys
import time
import schedule
import json
from datetime import datetime,timedelta
from const import *
from data_fetcher import DataFetcher


def main():
    global RETRY_TIMES_LIMIT
    if 'PYTHON_IN_DOCKER' not in os.environ:
        # 读取 .env 文件
        import dotenv
        dotenv.load_dotenv(verbose=True)
    if os.path.isfile('/data/options.json'):
        with open('/data/options.json') as f:
            options = json.load(f)
        try:
            PHONE_NUMBER = options.get("logins", {}).get("phone")
            PASSWORD = options.get("logins", {}).get("password")
            HASS_URL = options.get("has_sensor", {}).get("hass_url", "http://homeassistant.local:8123/")
            JOB_START_TIME = options.get("customize", {}).get("job_start_time", "07:00")
            LOG_LEVEL = options.get("customize", {}).get("log_level", "INFO")
            VERSION = os.getenv("VERSION")
            RETRY_TIMES_LIMIT = int(options.get("customize", {}).get("retry_times_limit", 5))

            logger_init(LOG_LEVEL)
            logging.info(f"当前以Homeassistant Add-on 形式运行.")
            
            os.environ["IGNORE_USER_ID"] = options.get("customize", {}).get("ignore_user_id", "xxxxx,xxxxx")
            db_mode = str(options.get("db_mode", "Close"))
            if db_mode == "Close":
                os.environ["ENABLE_DATABASE_SQLITE_STORAGE"] = "false"
                os.environ["ENABLE_DATABASE_MARIADB_STORAGE"] = "false"
                logging.info(f"当前 数据库 已关闭")
            elif db_mode == "Sqlite3" :
                os.environ["ENABLE_DATABASE_SQLITE_STORAGE"] = "true"
                logging.info(f"当前 数据库 为 Sqlite3 模式")
            elif db_mode == "Mysql" or db_mode == "Mariadb" :
                os.environ["ENABLE_DATABASE_MARIADB_STORAGE"] = "true"
                logging.info(f"当前 数据库 为 Mysql/Mariadb 模式")
                
            # 传感器配置
            os.environ["HA_SENSOR_ENABLED"] = str(options.get("ha_sensor_enabled", "false")).lower()
            if str(options.get("ha_sensor_enabled", "false")).lower()=="false" :
                logging.info(f"当前 Homeassistant 传感器 已关闭")
            else:
                logging.info(f"当前 Homeassistant 传感器 已开启")
            os.environ["HASS_URL"] = options.get("has_sensor", {}).get("hass_url", "http://homeassistant.local:8123/")
            os.environ["HASS_TOKEN"] = options.get("has_sensor", {}).get("hass_token")
            # sqlite配置
            os.environ["SQLITE_DB_NAME"] = options.get("sqlite", {}).get("sqlite_db_name", "home-assistant_v2.db")
            os.environ["SQLITE_DB_PATH"] = options.get("sqlite", {}).get("sqlite_db_path", "homeassistant")
            # mariadb配置
            os.environ["MARIADB_URL"] = str(options.get("mariadb", {}).get("mariadb_url", "HOMEASSISTANT.LOCAL"))
            os.environ["MARIADB_PORT"] = str(options.get("mariadb", {}).get("mariadb_port", "3306"))
            os.environ["MARIADB_USER"] = str(options.get("mariadb", {}).get("mariadb_user", "user"))
            os.environ["MARIADB_PASSWORD"] = str(options.get("mariadb", {}).get("mariadb_password", "password"))
            os.environ["MARIADB_DB_NAME"] = str(options.get("mariadb", {}).get("mariadb_db_name", "homeassistant"))
            # customize配置 driver_implicity_wait_time
            os.environ["JOB_START_TIME"] = options.get("customize", {}).get("job_start_time", "07:00")
            os.environ["DRIVER_IMPLICITY_WAIT_TIME"] = str(options.get("customize", {}).get("driver_implicity_wait_time", 60))
            os.environ["RETRY_TIMES_LIMIT"] = str(options.get("customize", {}).get("retry_times_limit", 5))
            os.environ["LOGIN_EXPECTED_TIME"] = str(options.get("customize", {}).get("login_expected_time", 10))
            os.environ["RETRY_WAIT_TIME_OFFSET_UNIT"] = str(options.get("customize", {}).get("retry_wait_time_offset_unit", 10))
            os.environ["DATA_RETENTION_DAYS"] = str(options.get("data_retention_days", 7))
            os.environ["RECHARGE_NOTIFY"] = str(options.get("customize", {}).get("recharge_notify", "false")).lower()
            os.environ["BALANCE"] = str(options.get("customize", {}).get("balance", 5.0))
            os.environ["PUSHPLUS_TOKEN"] = options.get("customize", {}).get("pushplus_token", "")
            
        except Exception as e:
            logging.error(f"Failing to read the options.json file, the program will exit with an error message: {e}.")
            sys.exit()
    else:
        try:
            PHONE_NUMBER = os.getenv("PHONE_NUMBER")
            PASSWORD = os.getenv("PASSWORD")
            HASS_URL = os.getenv("HASS_URL")
            JOB_START_TIME = os.getenv("JOB_START_TIME","07:00" )
            LOG_LEVEL = os.getenv("LOG_LEVEL","INFO")
            VERSION = os.getenv("VERSION")
            RETRY_TIMES_LIMIT = int(os.getenv("RETRY_TIMES_LIMIT", 5))
            
            logger_init(LOG_LEVEL)
            logging.info(f"The current run runs as a docker image.")
        except Exception as e:
            logging.error(f"Failing to read the .env file, the program will exit with an error message: {e}.")
            sys.exit()

    logging.info(
        f"The current repository version is {VERSION}, and the repository address is https://github.com/ARC-MX/sgcc_electricity_new.git")
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"The current date is {current_datetime}.")

    fetcher = DataFetcher(PHONE_NUMBER, PASSWORD)
    logging.info(
        f"The current logged-in user name is {PHONE_NUMBER}, the homeassistant address is {HASS_URL}, and the program will be executed every day at {JOB_START_TIME}.")

    next_run_time = datetime.strptime(JOB_START_TIME, "%H:%M") + timedelta(hours=12)
    logging.info(
        f'Run job now! The next run will be at {JOB_START_TIME} and {next_run_time.strftime("%H:%M")} every day')
    schedule.every().day.at(JOB_START_TIME).do(run_task, fetcher)
    schedule.every().day.at(next_run_time.strftime("%H:%M")).do(run_task, fetcher)
    run_task(fetcher)

    while True:
        schedule.run_pending()
        time.sleep(1)


def run_task(data_fetcher: DataFetcher):
    for retry_times in range(1, RETRY_TIMES_LIMIT + 1):
        try:
            data_fetcher.fetch()
            return
        except Exception as e:
            logging.error(
                f"state-refresh task failed, reason is [{e}], {RETRY_TIMES_LIMIT - retry_times} retry times left.")
            continue

def logger_init(level: str):
    logger = logging.getLogger()
    logger.setLevel(level)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    format = logging.Formatter("%(asctime)s  [%(levelname)-8s] ---- %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler(stream=sys.stdout)
    sh.setFormatter(format)
    logger.addHandler(sh)


if __name__ == "__main__":
    main()
