import redis
import uuid
from slack_sdk.errors import SlackApiError
import logging

# clound cache set up





# local cache setup
def set_up_cache_local():
    cache = redis.Redis(host='localhost', port=6379, db=0)
    return cache

# bot message
def is_response_to_bot_message(id, original_message_id):
    # Logic to verify if the response is for the correct message
    return id == original_message_id


# verification
def request_verification(payload, client, cache, app):
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
                sub_confirmed(cache, app, dm_id)
                sent_zoom_link(cache, dm_id, client, unique_request_code)
        else:
            logging.info("No messages found in the history for the given timestamp.")
    except SlackApiError as e:
        logging.error(f"Error retrieving message in DM: {e}")
    else:
        logging.info("Payload does not contain expected 'item' structure or 'channel' key.")


def process_find_subs_command(body, logger, cache, app):

    requester_id = body['user_id']
    requester_name = cache.get(f"teacher:{requester_id}").decode('utf-8')

    acknowledge = app.client.conversations_open(users=[requester_id])
    requester_dm = acknowledge["channel"]['id']
    app.client.chat_postMessage(channel=requester_dm, text= f"Hello, {requester_name} the bot is Wokring on find subs for you now!")
    unique_id = generate_unique_id()
   

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
    cache.setex(f"request:{unique_id}", 604800, "Zoom Link")

# Function to add a teacher
def add_teacher(teacher_id, teacher_data, cache):
    cache.set(f"teacher:{teacher_id}", teacher_data)

# Function to add a request
def add_request(request_id, request_data, cache):
    cache.set(f"request:{request_id}", request_data)

# sent sub request to all the teacher
def sent_request(cache, app, requester_id):
     requester_name = ""
     for key in cache.scan_iter("teacher:*"):
        # since the cache store the data as byte data type
        # we need to decode it as utf-8
        teacher_id = cache.get(key).decode('utf-8')
        teacher_name = key.decode('utf-8').split(':')[1]
        if requester_id == teacher_id:
            requester_name = teacher_name
            continue
 
        # open the dm
        response = app.client.conversations_open(users=[teacher_id])
        dm_id = response["channel"]['id']
        app.client.chat_postMessage(channel=dm_id, text=f"hello {teacher_name}! Can you subs for this class at this time? Thumbs up the message or reply yes")

     return requester_name
     

# sub confirmed
def sub_confirmed(cache, app, user):
     for key in cache.scan_iter("teacher:*"):
        # since the cache store the data as byte then
        # we need to decode it as utf-8
        teacher_id = key.decode('utf-8').split(":")[1]
        if teacher_id == user:
            continue
        # open the dm
        response = app.client.conversations_open(users=[teacher_id])
        dm_id = response["channel"]['id']
        app.client.chat_postMessage(channel=dm_id, text="This sub request has been filled")



# sent zoom link    
def sent_zoom_link(cache, id, client, request_key):
    client.chat_postMessage(channel=id, text=f"Thanks for filling the request, Here is the zoom link{cache.get(request_key).decode('utf-8')}")
    # free the memory
    cache.delete(request_key)



# unique id
def generate_unique_id():
    return str(uuid.uuid4())


