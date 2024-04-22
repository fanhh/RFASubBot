import os
import slack_sdk
from slack_sdk.socket_mode import SocketModeClient
from pathlib import Path
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
import threading
import helper
import re
import json
from slack_sdk.errors import SlackApiError
from background_worker import worker

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# set up cache
"""
To set it up to run in vm
cache = helper.set_up_cache_cloud()
path = Path to your data
data = pd.read_csv(path)
teachers = helper.clean_data(data)
for index, teacher in teachers.iterrows():
    cache.set(f"teacher:{teacher['Slack ID (RFA)']}", teacher['Teachers'])

that will set all the teacher data in the cache
"""
"""
Local
"""
cache = helper.set_up_cache_local()
cache.flushall() # empty out the cache for testing
cache.set('teacher:U06BUPTPKRU', "x1")
cache.set('teacher:U05SXKVEHMX', "x2")
logging.info(cache)

"""
once its on cloud and redis cache server set up
cache = helper.set_up_cache_cloud()
"""

# load paths
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = App(token=os.environ["SLACK_BOT_TOKEN"])


# Initialize WebClient and SocketModeClient
client = slack_sdk.WebClient(token=os.environ['SLACK_BOT_TOKEN'])

app_token = os.environ["SLACK_APP_TOKEN"]
socket_mode_client = SocketModeClient(
    app_token=app_token,
    web_client=client
)

@app.event("app_home_opened")
def handle_app_home_opened_events(body, logger):
    logger.info(body)


@app.event("reaction_added")
def handle_raction(body, logger):
    logger.info(f"Reaction added event received: {body}")

    event = body["event"]

    # if reaction is thumbs up and the user has not reply to it yet
    if event['reaction']=='+1':
        thread = threading.Thread(target=helper.request_verification, args=(body, client, cache, app))
        thread.start()
        # no need to lock the memory the redis handles it nativly
    logging.info(cache)
        
         

@app.command('/find-subs')
def find_subs_command(ack, body, logger):
    ack()  # acknowledge the command
    logger.info(body)

    # Spawn a new thread to handle the processing
    # Scaling requests handle
    thread = threading.Thread(target=helper.process_find_subs_command, args=(body, logger, cache, app))
    thread.start()
    logging.info(cache)




@app.event("message")
def handle_message(body, logger):
    helper.handle_messageZoom_event(body, logger, cache, app)
    logging.info(cache)

    


if __name__ == "__main__":
    # app = App(token=os.environ["SLACK_BOT_TOKEN"])

    # worker_thread = threading.Thread(target=worker, args=(cache, app, logging))
    # worker_thread.start()

    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()