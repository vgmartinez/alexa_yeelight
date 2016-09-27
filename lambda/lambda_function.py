"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

from __future__ import print_function
import ssl
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import sys


def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """

    logger = None
    if sys.version_info[0] == 3:
        logger = logging.getLogger("core")  # Python 3
    else:
        logger = logging.getLogger("AWSIoTPythonSDK.core")  # Python 2
    logger.setLevel(logging.INFO)
    streamHandler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    streamHandler.setFormatter(formatter)
    logger.addHandler(streamHandler)


    myAWSIoTMQTTClient = AWSIoTMQTTClient("alexa_light_pub", useWebsocket=True)
    myAWSIoTMQTTClient.configureEndpoint("a3d2g35udo4lz5.iot.eu-west-1.amazonaws.com", 443)
    myAWSIoTMQTTClient.configureCredentials("/opt/cert/rootCA.pem")

    # AWSIoTMQTTClient connection configuration
    myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
    myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
    myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
    myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

    

    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    if (event['session']['application']['applicationId'] !=
            "amzn1.ask.skill.1863db7d-53a9-4abd-9c15-74c719f894d9"):
        raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'], myAWSIoTMQTTClient)
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])


def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session, myAWSIoTMQTTClient):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "TurnTheLigths":
        print(intent)
        return turn_the_ligths(intent, session, myAWSIoTMQTTClient)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here

# --------------- Functions that control the skill's behavior ------------------


def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Hi baby, tell me the color you want"
    
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Please tell me white, red or blue"
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Alexa Skills Kit sample. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def create_favorite_color_attributes(favorite_color):
    return {"favoriteColor": favorite_color}


def publish(msg, myAWSIoTMQTTClient):
    print(msg)
    myAWSIoTMQTTClient.connect()
    myAWSIoTMQTTClient.publish("/yee/light", str(msg), 0)


def turn_the_ligths(intent, session, myAWSIoTMQTTClient):
    session_attributes = {}
    reprompt_text = None

    status = ''
    if 'State' in intent['slots']:
        status = intent['slots']['State']['value']

    if status == 'off':
        msg = '{"event": "set_power", "action": "off"}'
        print(msg)
        publish(msg, myAWSIoTMQTTClient)
        speech_output = "Putting the lights off."
        should_end_session = True
    elif status == 'red':
        msg = '{"event": "set_rgb", "action": "15209235"}'
        print(msg)
        publish(msg, myAWSIoTMQTTClient)
        speech_output = "Putting the lights red."
        should_end_session = True
    elif status == 'white':
        msg = '{"event": "set_rgb", "action": "16777215"}'
        print(msg)
        publish(msg, myAWSIoTMQTTClient)
        speech_output = "Putting the lights white."
        should_end_session = True
    elif status == 'on':
        msg = '{"event": "set_power", "action": "on"}'
        print(msg)
        publish(msg, myAWSIoTMQTTClient)
        speech_output = "Putting the lights on."
        should_end_session = True
    else:
        speech_output = "I'm not sure"
        should_end_session = False

    # Setting reprompt_text to None signifies that we do not want to reprompt
    # the user. If the user does not respond or says something that is not
    # understood, the session will end.
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))
    


# --------------- Helpers that build all of the responses ----------------------


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': 'SessionSpeechlet - ' + title,
            'content': 'SessionSpeechlet - ' + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }