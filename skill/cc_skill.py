# author - Vasavi Chitlur
#manage dish and quantity in session
from __future__ import print_function
import boto3
from boto3.dynamodb.conditions import Key, Attr

##Configure Dynamodb
aws_access_key_id = "AKIAIXQSPFFFCBPHBAHQ"#You get access key and secret key from AWS console
aws_secret_access_key = "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"
region_name="eu-west-1"
client = boto3.resource('dynamodb',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
#boto3.resource only works for cloudformation,cloudwatch,dynamodb,ec2,glacier,iam,opsword,s3,sns,sqs
##Required to access table
table=client.Table('kitchen_menu')


# We'll start with a couple of globals...
CardTitlePrefix = "kitchen skill"
		# --------------- Helpers that build all of the responses ----------------------
#def build_speechlet_response(title, output, reprompt_text, should_end_session):
def build_speechlet_response(output_speech,output_content, reprompt_text,should_end_session):
    """
    Build a speechlet JSON representation of the title, output text, 
    reprompt text & end of session
    """
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output_speech
        },
        'card': {
            'type': 'Standard',
            'title': CardTitlePrefix,
            'text': output_content,
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
    """
    Build the full response JSON from the speechlet response
    """
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }
# --------------- Functions that control the skill's behavior ------------------
	
def on_launch_response():#play auto_intro
	session_attributes = {}
	menu_items=fetch_menu()
	items_list=""
	for i in menu_items['Items']:
		print(i)
		items_list+=i['menu_item']+", "
	speech_output = "What do you like to have. you can order from "+items_list
	speech_content = items_list
	# If the user either does not reply to the welcome message or says something
	# that is not understood, they will be prompted again with this text.
	reprompt_text = "What do you like to have ?"
	should_end_session = False
	return build_response(session_attributes, build_speechlet_response(speech_output,speech_content, reprompt_text, should_end_session))
    
def handle_session_end_request():
	speech_output = 'Ok Bye!'
	speech_content = "Bye!"
	# Setting this to true ends the session and exits the skill.
	should_end_session = True
	return build_response({}, build_speechlet_response(
        speech_output,speech_content, None, should_end_session))

#--------------------------- database functions---------------	
def fetch_menu():
	response = table.scan()
	return response
	
#--------------------------- other functions-----------------
def PlaceOrder(intent):
	attributes={}
	if ('value' in intent_request['intent']['slots']['dish_order']):
			attributes("dish") = intent_request['intent']['slots']['dish_order']['value']
	else:
		return RequestMenu()
	if len(intent_request['intent']['slots']['quantity_order']) > 1:
		dish=attributes("quantity")=intent_request['intent']['slots']['quantity_order']['value']
		
	else:
		return RequestQuantity()
	speech_output='your order of '+quantity+' '+order+' will arrive shortly'
	speech_content='your order of '+quantity+' '+order+' will arrive shortly'
	should_end_session=True
	return build_response({}, build_speechlet_response(speech_output,speech_content, None, should_end_session))

def RequestQuantity():
	"""
	Return a suitable greeting...
	"""
	speech_output='how much do you need?'
	speech_content='how much do you need?'
	should_end_session=False
	repromt_text="Please specify quantity"
	return build_response({}, build_speechlet_response(speech_output,speech_content, repromt_text, should_end_session))

def RequestMenu():
	"""
	Return a suitable greeting...
	"""
	speech_output='what do you like to order'
	speech_content='what do you like to order'
	should_end_session=True
	reprompt_text='what do you like to order'
	return build_response({}, build_speechlet_response(speech_output,speech_content, reprompt_text, should_end_session))



# --------------- Events ------------------
def on_session_started(session_started_request, session):
    """ Called when the session starts """
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])
def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they want """
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return on_launch_response()
def on_intent(intent_request, session):
	""" Called when the user specifies an intent for this skill """
	print("on_intent requestId=" + intent_request['requestId'] +
			", sessionId=" + session['sessionId'])
	intent = intent_request['intent']
	intent_name = intent_request['intent']['name']
	# Dispatch to your skill's intent handlers
	if intent_name == "PlaceOrderIntent":
		return PlaceOrder(intent)
def on_session_ended(session_ended_request, session):
	""" Called when the user ends the session. Is not called when the skill returns should_end_session=true """
	print("on_session_ended requestId=" + session_ended_request['requestId'] +
		", sessionId=" + session['sessionId'])
# --------------- Main handler ------------------
def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print(event['session'])
    if('session' in event):
        print("event.session.application.applicationId=" +
              event['session']['application']['applicationId'])
        if event['session']['new']:
            on_session_started({'requestId': event['request']['requestId']},
                               event['session'])
    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])