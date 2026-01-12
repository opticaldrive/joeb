import os
from dotenv import load_dotenv
from slack_bolt import App
load_dotenv()
SLACKBOT_TOKEN = os.environ["SLACKBOT_TOKEN"]
LOG_CHANNEL =  os.environ["LOG_CHANNEL"]
slackbot = App(token=SLACKBOT_TOKEN)
slackbot.client.chat_postMessage(channel=LOG_CHANNEL, text="Hello, world :3")
