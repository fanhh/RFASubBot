import os
import slack_sdk
from slack_sdk.socket_mode import SocketModeClient
from pathlib import Path
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import requests
import logging
import time
import threading



# Set up logging
logging.basicConfig(level=logging.DEBUG)


# load paths
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = App(token=os.environ["SLACK_BOT_TOKEN"])


# Initialize WebClient and SocketModeClient
client = slack_sdk.WebClient(token=os.environ['SLACK_BOT_TOKEN'])

# global
request_status = {}
teachers = [] # working on it to find a way to auto load all the teacher info in

app_token = os.environ["SLACK_APP_TOKEN"]
socket_mode_client = SocketModeClient(
    app_token=app_token,
    web_client=client
)

@app.event("app_home_opened")
def handle_app_home_opened_events(body, logger):
    logger.info(body)

@app.event("message")
def handle_message_events(body, logger):
    global request_status
    logger.info(body)
    event = body['event']
    logger.info(request_status)

    # Check if the message is a response to a sub request
    if event['channel_type'] == 'im' and event['text'].lower() == 'yes':
        thread = threading.Thread(target=request_verification, args=(body,))
        thread.start()



def is_response_to_bot_message(id, original_message_id):
    # Logic to verify if the response is for the correct message
    return id == original_message_id


def request_verification(payload):
    event = payload['event']
    responder_id = event['user']
    if responder_id in request_status:
            request_details = request_status[responder_id]
            original_message_id = request_details["request_channel_id"]

            # Verify that the response is to the bot's message and have not yet processed
            if not request_details["processed"]:
                original_request_channel = request_details["request_channel_id"]

                # Send confirmation message to the original request channel
                client.chat_postMessage(channel=original_request_channel, text="Substitute has been confirmed!")

                # Send a separate message to the responder
                client.chat_postMessage(channel=request_details["request_channel_id"], text="A Zoom link will be dispatched to you 10 mins before the session!")

                # Optionally, remove or update the request_tracker entry
                # del request_tracker[responder_id]

                # In case of the server want keep the request history, instead of del
                # we can set the request processed as true
                request_status[responder_id]["processed"] = True


       
@app.event("reaction_added")
def handle_raction(body, logger):
    global request_status
    event = body["event"]

    # if reaction is thumbs up and the user has not reply to it yet
    if event['reaction']=='+1':
        thread = threading.Thread(target=request_verification, args=(body,))
        thread.start()
        
         

@app.command('/find-subs')
def find_subs_command(ack, body, logger):
    ack()  # acknowledge the command
    logger.info(body)

    # Spawn a new thread to handle the processing
    # Scaling requests handle
    thread = threading.Thread(target=process_find_subs_command, args=(body,))
    thread.start()


def process_find_subs_command(body):
    global request_status

    for teacher_id in teachers:
        # open the dm
        response = app.client.conversations_open(users=[teacher_id])
        dm_id = response["channel"]['id']
        message = app.client.chat_postMessage(channel=dm_id, text="Can you subs for this class at this time? Thumbs up the message or reply yes")

        # Keep track of the responses
        request_status[teacher_id] = {
        "requester" : teacher_id,
        "message_ts" : message['ts'],
        "request_channel_id": response["channel"]['id'],
        "processed": False
        }
       

    



# Add the event listener to the Socket Mode client
socket_mode_client.socket_mode_request_listeners.append(handle_message_events)

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()





