
import mysql.connector
import redis
import os
import logging


"""

scheduled script for updates of the cache with the db periodically on cloud

"""

def set_up_cache():
    # need a redis cloud server instance to retrieve the host, port and password
    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')
    return redis.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

def fetch_teachers_from_db(db_config):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        # also depends on how you name your table
        cursor.execute("SELECT Slack_ID_RFA, Teachers, zoom link ... FROM teachers_table")
        data = cursor.fetchall()
        conn.close()
        return data
    except mysql.connector.Error as e:
        logging.error(f"Error fetching data from database: {e}")
        return []

def update_redis_cache(cache, teachers):
    # empty out the current cache
    # update with new info
    cache.flushall()
    for teacher in teachers:
        try:
            cache.set(f"teacher:{teacher[0]}", teacher[1])
        except redis.RedisError as e:
            logging.error(f"Error updating Redis cache: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db_config = {
        'user': 'username',
        'password': 'password',
        'host': 'db_host',
        'database': 'dbname',
        'port': 3306
    }
    cache = set_up_cache()
    teachers = fetch_teachers_from_db(db_config)
    update_redis_cache(cache, teachers)
    logging.info("Redis cache updated with teacher data.")
