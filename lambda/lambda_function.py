"""
This sample demonstrates a simple skill built with the Amazon Alexa Skills Kit.
The Intent Schema, Custom Slots, and Sample Utterances for this skill, as well
as testing instructions are located at http://amzn.to/1LzFrj6

For additional samples, visit the Alexa Skills Kit Getting Started guide at
http://amzn.to/1LGWsLG
"""

from __future__ import print_function
import ssl
import paho.mqtt.client as paho
import paho.mqtt.publish as publish


def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """

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
        return on_intent(event['request'], event['session'])
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
    return get_welcome_response()

def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "TurnOnLigth" or intent_name == "TurnOffLigth":
        return turn_ligth(intent, intent_name)
    elif intent_name == "SetColorLight":
        return set_color_light(intent, session)
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
    card_title = "Yeelight"
    speech_output = "Hi baby, tell me"
    
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


def publish_to_topic(msg):
    try:
        tls_set = {
            "ca_certs": "cert/rootCA.pem",
            "certfile": "cert/841dbd710a-certificate.pem.crt",
            "keyfile": "cert/841dbd710a-private.pem.key",
            "tls_version": ssl.PROTOCOL_SSLv23,
            "ciphers": None
        }

        publish.single("/yee/light", payload=msg, qos=1,
                       hostname="A3D2G35UDO4LZ5.iot.eu-west-1.amazonaws.com",
                       port=8883, tls=tls_set, protocol=paho.MQTTv31, )
    except Exception as e:
        print(e)


def set_color_light(intent, session):
    colors = {
        "red": "15209235",
        "blue": "1315046",
        "white": "16777215",
        "yellow": "14149136"
    }
    session_attributes = {}
    reprompt_text = None

    if 'Color' in intent['slots']:
        status = intent['slots']['Color']['value']
        msg = '{"event": "set_rgb", "action": "' + colors[status] + '"}'
        publish_to_topic(msg)
        speech_output = "Putting the light {}.".format(status)
        should_end_session = True
    else:
        speech_output = "I'm not sure"
        should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def set_crazy_light(intent, session):
    if 'CrazyLight' in intent_name:
        msg = '{"event": "start_cf", "action": " "1000, 2, 2700, 100, 500, 1,255, 10, 500, 2, 5000, 1"}'
        publish_to_topic(msg)
        speech_output = "Putting the light on."
        should_end_session = True
    else:
        speech_output = "I'm not sure"
        should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        intent['name'], speech_output, reprompt_text, should_end_session))

def turn_ligth(intent, intent_name):
    session_attributes = {}
    reprompt_text = None

    if 'TurnOnLigth' in intent_name:
        msg = '{"event": "set_power", "action": "on"}'
        publish_to_topic(msg)
        speech_output = "Putting the light on."
        should_end_session = True
    elif 'TurnOffLigth' in intent_name:
        msg = '{"event": "set_power", "action": "off"}'
        publish_to_topic(msg)
        speech_output = "Putting the light off."
        should_end_session = True
    else:
        speech_output = "I'm not sure"
        should_end_session = False

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