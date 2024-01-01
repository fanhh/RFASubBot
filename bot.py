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



# Set up logging
logging.basicConfig(level=logging.DEBUG)

# set up cache
"""
Local testing cache

"""

cache = helper.set_up_cache_local()
cache.flushall() # empty out the cache for testing
cache.set('teacher:slack id', "full name")
cache.set('teacher:slack id', "full name")
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
        
         

@app.command('/find-subs')
def find_subs_command(ack, body, logger):
    ack()  # acknowledge the command
    logger.info(body)

    # Spawn a new thread to handle the processing
    # Scaling requests handle
    thread = threading.Thread(target=helper.process_find_subs_command, args=(body, logger, cache, app))
    thread.start()




"""
Time Eplashed del in the request to free up memory
Scale up the request handling and have threading prevention since the
convert the entire server into a statless server so that it can scale within cloud
"""
    


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()





"""

Functions that I moved to a different py file for code readablity and maintainablitry

"""

"""def is_response_to_bot_message(id, original_message_id):
    # Logic to verify if the response is for the correct message
    return id == original_message_id"""


"""def request_verification(payload):
    logging.info(f"Payload: {payload}")
    item = payload['event']['item']
    channel_id = item.get('channel')
    message_ts = item.get('ts')
    dm_id = payload['event']['user']

    if not channel_id or not message_ts:
        logging.error("Required keys 'channel' or 'ts' not found in the payload's 'item'.")
        return

    try:
        # Fetching the original message using Slack API
        result = client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
        if result['messages']:
            original_message = result['messages'][0]['text']
            unique_request_code = original_message.split(",")[0]
            logging.info(f"Original code in DM: {unique_request_code}")
            logging.info("Original code in DM: " + unique_request_code)
            if cache.exists(unique_request_code):
                helper.sub_confirmed(cache, app, dm_id)
                helper.sent_zoom_link(cache, dm_id, client, unique_request_code)
        else:
            logging.info("No messages found in the history for the given timestamp.")
    except SlackApiError as e:
        logging.error(f"Error retrieving message in DM: {e}")
    else:
        logging.info("Payload does not contain expected 'item' structure or 'channel' key.")"""


"""def process_find_subs_command(body, logger):
    global cache

    requester_id = body['user_id']
    requester_name = cache.get(f"teacher:{requester_id}").decode('utf-8')

    acknowledge = app.client.conversations_open(users=[requester_id])
    requester_dm = acknowledge["channel"]['id']
    app.client.chat_postMessage(channel=requester_dm, text= f"Hello, {requester_name} the bot is Wokring on find subs for you now!")
    unique_id = helper.generate_unique_id()
   

    for key in cache.scan_iter("teacher:*"):
        # since the cache store the data as byte then
        # we need to decode it as utf-8
        teacher_name = cache.get(key).decode('utf-8')
        teacher_id = key.decode('utf-8').split(':')[1]
        logging.info(f"teacher info{teacher_id}")
        try:
            if teacher_id == requester_id:
                continue
        except SlackApiError as e:
            logger.error(f"Error with user ID {teacher_id}: {e}")
 
        logging.info(f"{teacher_id} : {teacher_name}")
        # open the dm
        response = app.client.conversations_open(users=[teacher_id])
        dm_id = response["channel"]['id']
        req = app.client.chat_postMessage(channel=dm_id, text=f"request:{unique_id}, hello {teacher_name}! Can you subs for {requester_name} class? Thumbs up the message or reply yes")
        logging.info(req)

    # cached the request
    # expires in 7 days, free up memory
    cache.setex(f"request:{unique_id}", 604800, "Zoom Link")"""


"""

leaving this out for now, since the reaction handles it all
@app.event("message")
def handle_message_events(body, logger):
    logger.info(f"message{body}")
    event = body['event']
  

    # Check if the message is a response to a sub request
    if event['channel_type'] == 'im' and event['text'].lower() == 'yes':
        thread = threading.Thread(target=request_verification, args=(body,))
        thread.start()
        # no need to lock the memory the redis handles it nativly
        
"""
