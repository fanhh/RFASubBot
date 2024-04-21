import redis
import uuid
from slack_sdk.errors import SlackApiError
import logging
import os
import time
import json
import pandas as pd
import re

# clound cache set up
def set_up_cache_cloud():
    # need a redis cloud server instance to retrieve the host, port and password
    redis_host = os.getenv('REDIS_HOST')
    redis_port = os.getenv('REDIS_PORT')
    redis_password = os.getenv('REDIS_PASSWORD')
    return redis.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

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
    # logging.info(f"Payload: {payload}")
    # item = payload['event']['item']
    # channel_id = item.get('channel')
    # message_ts = item.get('ts')
    # dm_id = payload['event']['user']

    # if not channel_id or not message_ts:
    #     logging.error("Required keys 'channel' or 'ts' not found in the payload's 'item'.")
    #     return

    # try:
    #     # Fetching the original message using Slack API
    #     result = client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
    #     if result['messages']:
    #         original_message = result['messages'][0]['text']
    #         unique_request_code = original_message.split(",")[0]
    #         logging.info(f"Original code in DM: {unique_request_code}")
    #         logging.info("Original code in DM: " + unique_request_code)
    #         if cache.exists(unique_request_code):
    #             sub_confirmed(cache, app, dm_id)
    #             sent_zoom_link(cache, dm_id, client, unique_request_code)
    #     else:
    #         logging.info("No messages found in the history for the given timestamp.")
    # except SlackApiError as e:
    #     logging.error(f"Error retrieving message in DM: {e}")
    # else:
    #     logging.info("Payload does not contain expected 'item' structure or 'channel' key.")

    logging.info(f"Payload: {payload}")

    # Assuming 'event' is always present, check for 'item' inside it
    event = payload.get('event', {})
    item = event.get('item', {})
    channel_id = item.get('channel')
    message_ts = item.get('ts')
    dm_id = event.get('user')

    # Validate presence of necessary keys
    if not channel_id or not message_ts:
        logging.error("Required keys 'channel' or 'ts' not found in the payload's 'item'.")
        return

    try:
        # Fetching the original message using Slack API
        result = client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
        if result['ok'] and result['messages']:
            original_message = result['messages'][0]['text']
            unique_request_code = original_message.split(",")[0].split(":")[1].strip()
            logging.info(f"Original code in DM: {unique_request_code}")

            # Verify the request exists in cache and process it
            if cache.get(f"request:{unique_request_code}"):
                sub_confirmed(cache, app, dm_id)
                sent_zoom_link(cache, dm_id, client, unique_request_code)
            else:
                logging.info("No matching request found in cache.")
        else:
            logging.info("No messages found in the history for the given timestamp.")
    except SlackApiError as e:
        logging.error(f"Error retrieving message history: {e}")



def process_find_subs_command(body, logger, cache, app):

    requester_id = body['user_id']
    requester_name = cache.get(f"teacher:{requester_id}").decode('utf-8')

    try:
        acknowledge = app.client.conversations_open(users=[requester_id])
        requester_dm = acknowledge["channel"]['id']
        
        # Send messages to the requester
        app.client.chat_postMessage(
            channel=requester_dm,
            text=f"Hello, {requester_name} the bot is working on finding subs for you now!"
        )
        app.client.chat_postMessage(
            channel=requester_dm,
            text="Hello, can you provide the zoom link and time in the following format: " 
                 "Example: zoom link: https://zoom.us/id/1234567890, time: 12:00pm PST (Time Zone)"
        )
    except Exception as e:
        logger.error(f"Failed to send message via Slack API: {str(e)}")
        return  # Exit if we cannot communicate with the user

    data = {
        "zoom_link": "",
        "time": "",
        "status": "pending",
        "requester_id": requester_id,
        "requester_name": requester_name
    }
    serialized_data = json.dumps(data)

    # Store in Redis with unique ID to prevent collisions
    try:
        cache.setex(f"request:{requester_id}", 3600, serialized_data)  # 1 hour expiration
    except Exception as e:
        logger.error(f"Failed to store request data in Redis: {str(e)}")
   

# Function to add a teacher
def add_teacher(teacher_id, teacher_data, cache):
    cache.set(f"teacher:{teacher_id}", teacher_data)

# Function to add a request
def add_request(request_id, request_data, cache):
    cache.set(f"request:{request_id}", 604800, request_data)
     

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



# # sent zoom link    
def sent_zoom_link(cache, id, client, request_key):
    
    serialized_data = cache.get(f"request:{request_key}")
    
    # Check if the data exists
    if serialized_data:
        # Deserialize the JSON string back into a Python dictionary
        data = json.loads(serialized_data.decode('utf-8'))
        
        # Access the Zoom link and time from the dictionary
        zoom_link = data.get("zoom_link", "No Zoom link provided")
        meeting_time = data.get("time", "No time provided")
        
        client.chat_postMessage(channel=id, text=f"Here is the Zoom link: {zoom_link}, and the time: {meeting_time}.")
        
        # Free the memory
        cache.delete(f"request:{request_key}")
    else:
        # Handle the case where data might not be found (e.g., expired or never set)
        client.chat_postMessage(channel=id, text="Sorry, This request has expired.")

def handle_messageZoom_event(body, logger, cache, app):
    logger.info(f"Body: {body}")
    user_id = body['event']['user']
    text = body['event']['text']

    # Regular expression to match a Zoom link and time
    logger.info(f"Text: {text}")
    zoom_link_pattern = r'zoom link:\s*<(\S+?)>,\s*time:\s*(.+)'
    match = re.search(zoom_link_pattern, text, re.IGNORECASE)
    logger.info(f"Match: {match}")

    if match:
        zoom_link = match.group(1)
        meeting_time = match.group(2)
        logger.info(f"Zoom link: {zoom_link}, Time: {meeting_time}")
        logger.info(cache.scan_iter("request:*"))

        # Update the correct cache entry
        for key in cache.scan_iter("request:*"):
            logger.info(f"Key: {key}")
            logger.info(f"User ID: {user_id}")
            serialized_data = cache.get(key).decode('utf-8')
            logger.info(f"Serialized data: {serialized_data}")
            data = json.loads(serialized_data)
            
            # Check if this request corresponds to the user_id
            # This requires your request data to have a 'user_id' key or a similar mechanism
            if data['requester_id'] == user_id:
                # Update the data with the new Zoom link and time
                data.update({
                    "zoom_link": zoom_link,
                    "time": meeting_time,
                    'status': 'ready'
                })
                
                # Serialize the updated dictionary and save it back to Redis
                cache.setex(key, 604800, json.dumps(data))
                # dequeu the request

                
                # Send a confirmation message back to the user
                acknowledge = app.client.conversations_open(users=[user_id])
                requester_dm = acknowledge["channel"]['id']
                app.client.chat_postMessage(
                    channel=requester_dm,
                    text="Thank you for providing the Zoom link and time. Your request has been processed."
                )
                break



# unique id
def generate_unique_id():
    return str(uuid.uuid4())


def clean_data(csv_file):
    df = pd.read_csv(csv_file, skiprows=1)
    teachers = df.loc[(df['Teacher?'] == True) & (df['Teacher Inactive'] == False),
                      ['First Name', 'Last Name', 'TFA/RFA Email', 'Slack ID (RFA)']]
    teachers['Teachers'] = teachers['First Name'] + " " + teachers['Last Name']
    return teachers

