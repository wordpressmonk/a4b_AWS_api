from flask import Flask,render_template,request,jsonify
import os,json,boto3
from config import *
from functools import wraps
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import time

client_iam = boto3.client('iam',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
client_a4b = boto3.client('alexaforbusiness',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_dynamodb = boto3.resource('dynamodb',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_ses = boto3.client('ses',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)

table=client_dynamodb.Table('IamUser')
requests_table=client_dynamodb.Table('Requests')
ResponseTable=client_dynamodb.Table('Response')
Request_TypeTable=client_dynamodb.Table('Request_Types')
Notification_TemplateTable=client_dynamodb.Table('Notification_Template')
Room_Profile = client_dynamodb.Table('Room_Profiles_By')
Rooms_By     = client_dynamodb.Table('Rooms_By')

app=Flask(__name__)

# def create_a4b_client():
	# UserName='vasaviCG'
	# file = open('./users/'+UserName+'.json', 'r') 
	# keys=json.loads(file.read())
	# user_a4b=boto3.client('alexaforbusiness',aws_access_key_id=keys['aws_access_key_id'],aws_secret_access_key=keys['aws_secret_access_key'],region_name="us-east-1")
	# return (user_a4b)
def handle_stripe(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (TypeError,IndexError,KeyError) as e:
            return ("Some value in the operation doesn't exist")
        except ClientError  as e:
            #return jsonify(e)
            return e.response['Error']['Message']

    return decorated

	
@app.route("/")
def main():
	return render_template('login.html')

#
#CRUD for IAM Users
#
@app.route("/a4b/api/v1.0/add_new_user",methods = ['POST'])
@handle_stripe
def add_new_user():
    #Create User
    response = client_iam.create_user(
	Path='/'+request.json['Path']+'/',
	UserName=request.json['UserName'])

    #Attach only A4B policy to user 
    response_policy = client_iam.attach_user_policy(
	UserName=response['User']['UserName'],#see list IAM users to see all available users
	PolicyArn='arn:aws:iam::aws:policy/AlexaForBusinessFullAccess')#see get policy arn to list all available policies
	
    #Create access Key
    response_access = client_iam.create_access_key(
	UserName=response['User']['UserName'])
	
	
    #store access keys in a database for user created
    response_table=table.put_item(
	Item={
		'UserName':response['User']['UserName'],
		'aws_access_key_id':response_access['AccessKey']['AccessKeyId'],
		'aws_secret_access_key':response_access['AccessKey']['SecretAccessKey'],
		'userarn':response['User']['Arn']
	})
    #return jsonify(response)
    return list_users()
	
@app.route("/a4b/api/v1.0/delete_users",methods=['POST'])
@handle_stripe
def delete_users():
	UserNameList=request.json['UserName']
	for OneUserName in UserNameList:
		response_table = table.get_item(
		Key={
			'UserName':OneUserName
		})
		
		#delete access keys
		response_access = client_iam.delete_access_key(
		UserName=OneUserName,
		AccessKeyId=response_table['Item']['aws_access_key_id'])
		
		# detach user policy
		response_policy = client_iam.detach_user_policy(
		UserName=OneUserName,
		PolicyArn='arn:aws:iam::aws:policy/AlexaForBusinessFullAccess')

		#to delete user first delete access keys and policies attached to that user and then delete user
		response = client_iam.delete_user(
		UserName=OneUserName)
		
		#delete entry in dynamodb
		table.delete_item(
		Key={
				'UserName':OneUserName	
		})
	return list_users()

@app.route("/a4b/api/v1.0/list_users",methods=['GET'])
@handle_stripe
def list_users():
	response=client_iam.list_users()
	return jsonify(response)
    
@app.route("/a4b/api/v1.0/get_users",methods=['POST'])
@handle_stripe
def get_users():
    response = client_iam.get_user(
        UserName=request.json['UserName']
    )
    return jsonify(response)  
	
@app.route("/a4b/api/v1.0/update_users",methods=['POST'])
@handle_stripe
def update_users():
	response=client_iam.update_user(
	UserName = request.json['UserName'],
	NewPath = '/'+request.json['NewPath']+'/',
	NewUserName = request.json['NewUserName'])
	
	return jsonify(response)

#
#CRUD for Skill group	
#
	
@app.route("/a4b/api/v1.0/add_skill_group",methods=['POST'])
@handle_stripe
def add_skill_group():
	response=client_a4b.create_skill_group(
	SkillGroupName = request.json['SkillGroupName'],
	Description = request.json['Description'],
	ClientRequestToken = request.json['ClientRequestToken'])
	#print(SkillGroupName)#,Description,ClientRequestToken)	
	return jsonify(response)
	
#
#CRUD for Room Profile
#
	
@app.route("/a4b/api/v1.0/add_room_profile", methods=['POST'])
#@handle_stripe
def add_room_profile():
    try:
        #user_a4b=create_client()#when login page is provided pass username from login page
        ProfileName = str(request.json['userid'])+'_@_'+str(request.json['ProfileName'])
        response = client_a4b.create_profile(
        ProfileName=ProfileName,
        Timezone=request.json['Timezone'],
        Address=request.json['Address'],
        DistanceUnit=request.json['DistanceUnit'],
        TemperatureUnit=request.json['TemperatureUnit'],
        WakeWord=request.json['WakeWord'],
        #ClientRequestToken=request.json['ClientRequestToken'],
        SetupModeDisabled=bool(request.json['SetupModeDisabled']),
        MaxVolumeLimit=int(request.json['MaxVolumeLimit']),
        PSTNEnabled=bool(request.json['PSTNEnabled']))
        
        response_table=Room_Profile.put_item(
        Item={
            'profile_arn':response['ProfileArn'],
            'username':request.json['username']
        })
    
        return jsonify(response)
        #return ("Room Profile Added")
        #return jsonify({'profile_list':list_room_profile()})
    except Exception as e:
        return jsonify({'error':str(e)})
	
@app.route("/a4b/api/v1.0/list_room_profile", methods=['GET','POST'])
#@handle_stripe
def list_room_profile():
    response = client_a4b.search_profiles(SortCriteria=[
        {
            'Key': 'ProfileName',
            'Value': 'ASC'
        },
    ])
    username = request.json['username']
    
    #return jsonify(response)
    
    profiles=response['Profiles']
    ProfileNameList=[]
    for profile in profiles:
        room_profile_response = Room_Profile.get_item(
        Key={
            'profile_arn':str(profile['ProfileArn'])
        })
        if 'Item' in room_profile_response:
            Username_RP =room_profile_response['Item']['username']
            if str(username)==str(Username_RP):
                ProfileName = profile['ProfileName'].split('_@_')[1]
                ProfileNameList.append(ProfileName)
    return jsonify(ProfileNameList)
	
	
@app.route("/a4b/api/v1.0/get_room_profile_info", methods=['POST'])
#@handle_stripe
def get_room_profile_info():#ProfileName
    ProfileName=str(request.json['userid'])+'_@_'+str(request.json['ProfileName'])
    ProfileArn=get_profile_arn(ProfileName)

    response_p_info= client_a4b.get_profile(
        ProfileArn=ProfileArn
        )
    response = response_p_info['Profile']
    response['ProfileName'] = response_p_info['Profile']['ProfileName'].split('_@_')[1]    
    return jsonify(response)
	

def get_profile_arn(ProfileName):
	
	response_parn= client_a4b.search_profiles(
    Filters=[
        {
            'Key':'ProfileName', 
			'Values':[ProfileName]
        }
			])
	profiles=response_parn['Profiles']
	ProfileNameList=[]
	
	return response_parn['Profiles'][0]['ProfileArn']
	
@app.route("/a4b/api/v1.0/update_room_profile", methods=['POST'])
@handle_stripe	
def update_room_profile():
    try:
        OldProfileName= str(request.json['userid'])+'_@_'+str(request.json['OldProfileName'])
        ProfileName   = str(request.json['userid'])+'_@_'+str(request.json['ProfileName'])
        ProfileArn=get_profile_arn(OldProfileName)
        #return jsonify(ProfileArn)
        response = client_a4b.update_profile(
        ProfileArn=ProfileArn,
        ProfileName=ProfileName,
        Timezone=request.json['Timezone'],
        Address=request.json['Address'],
        DistanceUnit=request.json['DistanceUnit'],
        TemperatureUnit=request.json['TemperatureUnit'],
        WakeWord=request.json['WakeWord'],
        #ClientRequestToken=request.json['ClientRequestToken'],
        SetupModeDisabled=bool(request.json['SetupModeDisabled']),
        MaxVolumeLimit=int(request.json['MaxVolumeLimit']),
        PSTNEnabled=bool(request.json['PSTNEnabled']))
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error':str(e)})    

@app.route("/a4b/api/v1.0/delete_room_profile", methods=['POST'])
#@handle_stripe
def delete_room_profile():
    try:
        ProfileNameList=request.json['ProfileName']
        for ProfileName in ProfileNameList:
            Profile_Name = str(request.json['userid'])+'_@_'+str(ProfileName)
            ProfileArn=get_profile_arn(Profile_Name)
            try:
                response = client_a4b.delete_profile(
                    ProfileArn=ProfileArn
                )
            except Exception as e:
                return jsonify({"error":str(e)}) 
            else:
                response = Room_Profile.delete_item(
                    Key={
                            'profile_arn': ProfileArn
                        }
                )
    except Exception as e:
        return jsonify({"error":str(e)}) 

        
    # return get_rooms()
    # ProfileName=request.json['ProfileName']
    # ProfileArn=get_profile_arn(ProfileName)

    # response = client_a4b.delete_profile(
        # ProfileArn=ProfileArn
    # )
    #return list_room_profile()
    return ''

#
#CRUD for rooms
#
	
@app.route("/a4b/api/v1.0/add_rooms",methods=['POST'])
#@handle_stripe
def add_rooms():
    #user_a4b=create_client()
    #get profile arn from profile name
    try:
        ProfileName=str(request.json['userid'])+'_@_'+str(request.json['ProfileName'])
        ProfileArn=get_profile_arn(ProfileName)
    except Exception as e:
        return jsonify({'error':str(e)})    
    else:    
        try:
            response = client_a4b.create_room(
            RoomName=str(request.json['userid'])+'_@_'+str(request.json['RoomName']),
            ProfileArn=ProfileArn)
            response_table=Rooms_By.put_item(
            Item={
                'room_arn':response['RoomArn'],
                'Username':request.json['username']
            })
            
            #return (response['RoomArn'])
            if 'DeviceName' in request.json and 'RoomArn' in response:
                if request.json['DeviceName']:
                    return associate_device_room(response['RoomArn'],request.json['DeviceName'])
        except Exception as e:
            return jsonify({'error':str(e)})

	
@app.route("/a4b/api/v1.0/get_room_arn",methods=['POST'])
def get_room_arn(RoomName):
#def get_room_arn():
	response_parn= client_a4b.search_rooms(
    Filters=[
        {
            'Key':'RoomName', 
			'Values':[RoomName]
			#'Values':[request.json['RoomName']]
        }
			])
	return response_parn['Rooms'][0]['RoomArn']
	#return jsonify(response_parn['Rooms'])
	
		
@app.route("/a4b/api/v1.0/update_rooms",methods=['POST'])
#@handle_stripe
def update_rooms():
    try:
        #client_a4b=create_client()
        #get roomarn from roomname
        RoomName=str(request.json['userid'])+'_@_'+str(request.json['OldRoomName'])
        RoomArn=get_room_arn(RoomName)
        
        #get profile arn from profile name
        ProfileName=str(request.json['userid'])+'_@_'+str(request.json['ProfileName'])
        ProfileArn=get_profile_arn(ProfileName)
        
        #call update room only for changing room profile
        response= client_a4b.update_room(
        RoomArn=RoomArn,
        RoomName=str(request.json['userid'])+'_@_'+str(request.json['RoomName']),
        #Description=request.json['Description'],
        #ProviderCalendarId=request.json['ProviderCalendarId'],
        ProfileArn=ProfileArn)
        
        if request.json['DeviceName']:
            associate_device_room(RoomArn,request.json['DeviceName'])
        elif request.json['OldDeviceName']:
            disassociate_device_from_room(request.json['OldDeviceName'])
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error':str(e)})
	
@app.route("/a4b/api/v1.0/delete_rooms",methods=['POST'])
#@handle_stripe
def delete_rooms():
    #get roomarn from roomname
    RoomNameList=request.json['RoomName']
    for RoomName in RoomNameList:
        try:
            Room_Name = str(request.json['userid'])+'_@_'+str(RoomName)
            RoomArn=get_room_arn(Room_Name)
            response = client_a4b.delete_room(
            RoomArn=RoomArn)
            response = Rooms_By.delete_item(
                Key={
                    'room_arn': RoomArn
                }
            )
        except Exception as e:  
            return str(e)
    #return get_rooms()
    return ''
	
	
@app.route("/a4b/api/v1.0/get_rooms",methods=['POST'])
def get_rooms():	
	#client_a4b=create_client()
    if 'RoomName' in request.json:
        RoomName = str(request.json['userid'])+'_@_'+str(request.json['RoomName'])
        response = client_a4b.search_rooms(
        Filters=[
        {
            'Key':'RoomName', 
            'Values':[RoomName]
        }
        ],
        SortCriteria=[
            {
                'Key': 'RoomName',
                'Value': 'ASC'
            },
        ]
        )
    else:
        response = client_a4b.search_rooms(SortCriteria=[
            {
                'Key': 'RoomName',
                'Value': 'ASC'
            },
        ])
    username = request.json['username']
        
    DeviceDict = list_devices_with_rooms()
    rooms=response['Rooms']
    List_room_info=[]
    # RoomNameList=[]
    # RoomProfileList=[]
    for room in rooms:
        room_response = Rooms_By.get_item(
        Key={
            'room_arn':str(room['RoomArn'])
        })
        if 'Item' in room_response:
            Username_R = room_response['Item']['Username']
            if str(username)==str(Username_R):
                Roomdict={}
                Roomdict['RoomName']    =room['RoomName'].split('_@_')[1]
                Roomdict['ProfileName'] =room['ProfileName'].split('_@_')[1]
                if room['RoomName'] in DeviceDict.keys():
                    Roomdict['DeviceName'] = DeviceDict[room['RoomName']]
                else:
                    Roomdict['DeviceName'] = ""
                List_room_info.append(Roomdict)
                #RoomNameList.append(room['RoomName'])
                #RoomProfileList.append(room['ProfileName'])
    #List_room_info={"RoomNames":RoomNameList,"ProfileName":RoomProfileList}
    return jsonify(List_room_info)
	

#
#Devices
#
	
@app.route("/a4b/api/v1.0/get_devices",methods=['POST'])
@handle_stripe
def get_devices():
        if 'Serial_number' in request.json:
            Serial_number=request.json['Serial_number']
            response = client_a4b.search_devices(
            Filters=[
            {
                'Key':'DeviceSerialNumber', 
                'Values':[Serial_number]
            }
            ]
            )
        else:
            response = client_a4b.search_devices()
        devices = response['Devices']
        DeviceList = []
        for device in devices:
            DeviceDict={}
            DeviceDict['DeviceName']=device['DeviceName'] if 'DeviceName' in device else ''
            DeviceDict['DeviceSerialNumber']=device['DeviceSerialNumber'] if 'DeviceSerialNumber' in device else ''
            DeviceDict['DeviceType']=device['DeviceType'] if 'DeviceType' in device else ''
            DeviceDict['DeviceStatus']=device['DeviceStatus'] if 'DeviceStatus' in device else ''
            DeviceDict['DeviceName']=device['DeviceName'] if 'DeviceName' in device else ''
            if "RoomName" in device.keys(): # condition to check if devices are associated with any rooms
                DeviceDict['RoomName'] = device['RoomName'].split('_@_')[1]	
            DeviceList.append(DeviceDict)
        return jsonify(DeviceList)
        # return jsonify(response)

@app.route("/a4b/api/v1.0/update_device",methods=['POST'])
@handle_stripe
def update_device():
		#DeviceName_old = request.json['DeviceName_Old']
		Serial_Number = request.json['Serial_Number']
		DeviceName_new = request.json['DeviceName_New']
		#DeviceArn = get_device_arn(DeviceName_old)
		DeviceArn = get_device_arn_by_serialNo(Serial_Number)
		response = client_a4b.update_device(
			DeviceArn=DeviceArn,
			DeviceName=DeviceName_new
			)
		return jsonify(response)
		
# @app.route("/a4b/api/v1.0/display_device_info",methods=['POST'])
# @handle_stripe
# def display_device_info(DeviceName):
	

def get_device_arn(DeviceName):
	response = client_a4b.search_devices(
	Filters=[
        {
            'Key':'DeviceName', 
			'Values':[DeviceName]
        }
			]
	)
	return response['Devices'][0]['DeviceArn']
    
def get_device_arn_by_serialNo(serialno):
	response = client_a4b.search_devices(
	Filters=[
        {
            'Key':'DeviceSerialNumber', 
			'Values':[serialno]
        }
			]
	)
	return response['Devices'][0]['DeviceArn']    

@app.route("/a4b/api/v1.0/add_room_to_device",methods=['POST'])
@handle_stripe
def add_room_to_device():
    RoomName    = request.json["RoomName"]
    RoomArn     = get_room_arn(RoomName)
    DeviceName  = request.json["DeviceName"]
    return associate_device_room(RoomArn,DeviceName)
	
#@app.route("/a4b/api/v1.0/associate_device_room",methods=['POST'])
def associate_device_room(RoomArn,DeviceName):
	#RoomName = request.json["RoomName"]
	#RoomArn = get_room_arn(RoomName)
	
	#DeviceName =  request.json["DeviceName"]
	DeviceArn = get_device_arn(DeviceName)
	
	response = client_a4b.associate_device_with_room(
    DeviceArn=DeviceArn,
    RoomArn=RoomArn)
	
	return jsonify(response)

#@app.route("/a4b/api/v1.0/list_devices_with_rooms",methods=['GET'])
def list_devices_with_rooms():
	response = client_a4b.search_devices()
	devices = response['Devices']
	DeviceDict = {}
	for device in devices:
		if "RoomName" in device.keys(): # condition to check if devices are associated with any rooms
			DeviceDict[device['RoomName']] = device['DeviceName']
	return DeviceDict
	#return jsonify(response)
	
@app.route("/a4b/api/v1.0/start_device_sync",methods=['POST'])
@handle_stripe
def start_device_sync():
	DeviceName=request.json['DeviceName']	
	DeviceArn = get_device_arn(DeviceName)
	
	response = client_a4b.start_device_sync(
		DeviceArn=DeviceArn,
		Features=[
			'ALL',
		]
	)	
	return jsonify(response)


@app.route("/a4b/api/v1.0/disassociate_device_from_room",methods=['POST'])
@handle_stripe
def disassociate_device_from_room(devicename=''):
    if request.json['DeviceName']:
        DeviceName=request.json['DeviceName']
    else:
        DeviceName=devicename
    DeviceArn = get_device_arn(DeviceName)
    response = client_a4b.disassociate_device_from_room(
        DeviceArn=DeviceArn
    )

    return jsonify(response)

    #
    #Database functions
    #

@app.route("/a4b/api/v1.0/requests_insert",methods=['POST'])
def requests_insert():
    verified_email = json.loads(list_verified_emails())
    request_name = str(request.json['userid'])+'_@_'+str(request.json['request_name'].lower())
    #to verify if the request is duplicate
    response=requests_table.query(
        KeyConditionExpression=Key('request_name').eq(request_name)
        )
    request_exist=response['Items']
    if not request_exist:
        #if the request_name not in dynamodb, then create the request
        OtherDetails={}
        OtherDetails['request_name'] = request_name.strip()
        OtherDetails['RequestStatus']=request.json["Status"].lower()
        OtherDetails['RequestType']=request.json["RequestType"]
        if "NotificationTemplate" in request.json:
            if request.json["NotificationTemplate"]:
                OtherDetails['NotificationTemplate']=request.json["NotificationTemplate"]
        if "Conversation" in request.json:
            OtherDetails['Conversation']=str(request.json["Conversation"])
        OtherDetails['username']=str(request.json["username"])
        OtherDetails['userid']=str(request.json["userid"])
        
        if "Check_Email" in request.json:
            if request.json["Check_Email"]== "1":
                OtherDetails['EmailID']=request.json["EmailID"]
                
                if 'VerifiedEmailAddresses' in verified_email:
                    if verified_email['VerifiedEmailAddresses']:
                        if not OtherDetails['EmailID'] in verified_email['VerifiedEmailAddresses']:
                            return jsonify({"error":"Your E-mail address is not verified with Alexa For Business."})
            
        if "Check_Text" in request.json:
            if request.json["Check_Text"]== "1":
                OtherDetails['TextNumber']=request.json["TextNumber"]
            
        if "Check_Call" in request.json:
            if request.json["Check_Call"]== "1":
                OtherDetails['CallNumber']=request.json["CallNumber"]
            
        
        #Level=int(request.json["Level"])
        # OtherDetails['Level']=request.json["Level"]
        # for i in range(Level):
            # Q = request.json["Q"+str(i+1)]
            # A = request.json["A"+str(i+1)]
            
            # OtherDetails["Q"+str(i+1)]= Q
            # OtherDetails["A"+str(i+1)]= A
        response=requests_table.put_item(Item=OtherDetails)
        
        #return display_menu()
        return jsonify(response)
    else:
        return jsonify({"error":"Request with the name already exists."})

@app.route("/a4b/api/v1.0/request_info",methods=['POST'])	
def request_info():
# For particular request
    request_name = str(request.json['userid'])+'_@_'+str(request.json['request_name'])
    response = requests_table.query(
        KeyConditionExpression=Key('request_name').eq(request_name)
        )   
    if response['Items']:
        if 'Conversation' in response['Items'][0]:
            conversation = 	response['Items'][0]['Conversation']
            del response['Items'][0]['Conversation']
            response['Items'][0]['Conversation'] = eval(conversation)
    #for value in eval(response['Items'][0]['Conversation']):
    return jsonify(response['Items'])
    #return type(response['Items'])

@app.route("/a4b/api/v1.0/requests_read",methods=['POST'])	
def requests_read():
#To get information of all requests in table
    filter_expression = Key('username').eq(request.json['username'])
    response=requests_table.scan(
        FilterExpression=filter_expression
    )
    return jsonify(response['Items'])
	
@app.route("/a4b/api/v1.0/requests_delete",methods=['POST'])
def requests_delete():
    # response = requests_table.delete_item(
        # Key={
            # 'request_name': 'api-request'
        # }
    # )
    # return jsonify(response)
	
	RequestDeleteList=request.json['request_name']
	for OneRequestDelete in RequestDeleteList:
		request_name=OneRequestDelete
		
		
		response = requests_table.delete_item(
        Key={
            'request_name': str(request.json['userid'])+'_@_'+str(request_name)
        }
    )
		
	return jsonify(response)

@app.route("/a4b/api/v1.0/requests_update",methods=['POST'])
def requests_update():
    verified_email = json.loads(list_verified_emails())
    request_name = str(request.json['userid'])+'_@_'+str(request.json['request_name'].lower())
    oldrequest_name = str(request.json['userid'])+'_@_'+str(request.json['oldrequest_name'].lower())
    response=requests_table.query(
        KeyConditionExpression=Key('request_name').eq(request_name)
    )
    request_exist=response['Items']

    OtherDetails={}
    OtherDetails['request_name'] = request_name.strip()
    OtherDetails['RequestStatus']=request.json["Status"].lower()
    OtherDetails['RequestType']=request.json["RequestType"]
    if request.json["NotificationTemplate"] !="":
        OtherDetails['NotificationTemplate']=request.json["NotificationTemplate"]
    OtherDetails['Conversation']=str(request.json["Conversation"])
    OtherDetails['username']=str(request.json["username"])
    OtherDetails['userid']=str(request.json["userid"])

    if "Check_Email" in request.json and request.json["Check_Email"]== "1":
        OtherDetails['EmailID']=request.json["EmailID"]
        if 'VerifiedEmailAddresses' in verified_email:
            if verified_email['VerifiedEmailAddresses']:
                if not OtherDetails['EmailID'] in verified_email['VerifiedEmailAddresses']:
                    return jsonify({"error":"Your E-mail address is not verified with Alexa For Business."})
    elif "Check_Email" in request.json and request.json["Check_Email"]== "0": 
        OtherDetails['EmailID']=False    
        
    if "Check_Text" in request.json and request.json["Check_Text"]== "1":
        OtherDetails['TextNumber']=request.json["TextNumber"]
    elif "Check_Text" in request.json and request.json["Check_Text"]== "0": 
        OtherDetails['TextNumber']=False
        
    if "Check_Call" in request.json and request.json["Check_Call"]== "1":
        OtherDetails['CallNumber']=request.json["CallNumber"]
    elif "Check_Call" in request.json and request.json["Check_Call"]== "0": 
        OtherDetails['CallNumber']=False    
        
    if not request_exist: #create new request

        response = requests_table.delete_item(
            Key={
                'request_name': oldrequest_name
            }
        )

        response=requests_table.put_item(
            Item=OtherDetails)
        
        return jsonify(response)
        #return jsonify("Creating new item")
        
    else:
        if(request_name == oldrequest_name): #update request
            del OtherDetails['request_name']
            up_ex="Set "
            ex_attr_values = {}
            i=0
            for OD in OtherDetails:
                up_ex+=OD+" = :val"+str(i)+","
                ex_attr_values[':val'+str(i)]=OtherDetails[OD]
                i=i+1
            up_ex=up_ex[:-1]
            response = requests_table.update_item(
                Key={
                    'request_name': request_name
                    },
                UpdateExpression= up_ex,
                ExpressionAttributeValues=ex_attr_values
                )
            return jsonify(response)
        else:#to verify if the request is duplicate
            return jsonify({"error":"Request with the request name already exists"})
            
#
#Skill Parameter
#
@app.route("/a4b/api/v1.0/put_room_skill_parameter",methods=['GET'])
def put_room_skill_parameter():
	response = client_a4b.put_room_skill_parameter(
		RoomArn='arn:aws:a4b:us-east-1:512990229200:room/a6aff17cde32fc80af99aeda76ce9f98/f8b07f823e96757a2d9b4556a0916452',
		SkillId='cnkdjncsdjcnjdsnd',
		RoomSkillParameter={
			'ParameterKey': 'SCOPE',
			'ParameterValue': 'dcdcd'
		}
	)
	return jsonify(response)

@app.route("/a4b/api/v1.0/put_response",methods=['GET'])
def put_response():	
	scan_response=ResponseTable.scan()
	response=ResponseTable.put_item(
	Item={
		'ResponseID':scan_response['Count']+1,
		'ResquestType':'Valet'
	})
	return jsonify(response)
	
@app.route("/a4b/api/v1.0/scan_response",methods=['POST'])
def scan_response():    
    if 'startdate' in request.json and 'enddate' in request.json:
        startdate = request.json['startdate']
        enddate = request.json['enddate']
        response=ResponseTable.scan()
        result={}
        result['Items']=[]
        count=0
        for k,row in enumerate(response['Items']):
            date =  row['Date']
            olddate = date.split(",")
            
            if startdate and enddate=="":
                if startdate == olddate[0]:
                    count+=1
                    result['Items'].append(row)
            elif startdate and enddate:
                if olddate[0] >= startdate and olddate[0] <= enddate:
                    count+=1
                    result['Items'].append(row)
                
        result['Count']=count
        
        return jsonify(result)
    else:
        response=ResponseTable.scan()
        return jsonify(response)
        
@app.route("/a4b/api/v1.0/delete_response",methods=['POST'])
def delete_response(): 
    try:
        if 'responses' in request.json:
            responses = request.json['responses']
            for res_id in responses:            
                response = ResponseTable.delete_item(
                    Key={
                        'ResponseID': int(res_id)
                    }
                )
        return ''    
    except Exception as e:
        return str(e)
    
@app.route("/a4b/api/v1.0/add_request_types",methods=['POST'])
def add_request_template():
    if 'request_type' in request.json:
        request_type = request.json['request_type']
        response=Request_TypeTable.put_item(
        Item={
            'request_type':request_type
        })
        return jsonify(response)
    else:
        return jsonify({'error':'No Request Type in the request'})
        
        
@app.route("/a4b/api/v1.0/get_request_types",methods=['POST'])
def get_request_template():
    if request.json['request_type']:
        request_type = request.json['request_type']
        filter_expression = Key('request_type').eq(request_type)
        response=Request_TypeTable.scan(
            FilterExpression=filter_expression
        )
        return jsonify(response)
    else:
        response=Request_TypeTable.scan()
        return jsonify(response)

@app.route("/a4b/api/v1.0/update_request_type",methods=['POST'])
def update_request_template():   
    request_type = request.json['old_request_type']
    response = Request_TypeTable.delete_item(
        Key={
            'request_type': request_type
        }
    )
    #return jsonify(response)
    if 'request_type' in request.json:
        request_type = request.json['request_type']
        response=Request_TypeTable.put_item(
        Item={
            'request_type':request_type
        })
        return jsonify(response)
    else:
        return jsonify({'error':'No Request Templates in the request'})
        
@app.route("/a4b/api/v1.0/request_type_delete",methods=['POST'])
def request_temp_delete():
	Request_Type_List=request.json['request_type']
	for request_type in Request_Type_List:	
		response = Request_TypeTable.delete_item(
            Key={
                'request_type': request_type
            }
        )
		
	return jsonify(response)            
        
@app.route("/a4b/api/v1.0/add_notification_template",methods=['POST'])
def add_notification_template():
    if 'template_name' in request.json:
        TemplateName = str(request.json['userid'])+'_@_'+str(request.json['template_name'])
        filter_expression = Key('template_name').eq(TemplateName)
        response=Notification_TemplateTable.scan(
            FilterExpression=filter_expression
        )
        if response['Count']>0:
            return jsonify({'error':'Notification Template with the name already exist'})
        else:
            template_name = TemplateName
            template      = request.json['template']
            username      = request.json['username']
            response=Notification_TemplateTable.put_item(
            Item={
                'template_name':template_name,
                'template':template,
                'username':username
            })
            return jsonify(response)
    else:
        return jsonify({'error':'No Notification Templates in the request'})
        
        
@app.route("/a4b/api/v1.0/get_notification_template",methods=['POST'])
def get_notification_template():
    if request.json['template_name']:
        template_name = str(request.json['userid'])+'_@_'+str(request.json['template_name'])
        username = request.json['username']
        filter_expression = Key('template_name').eq(template_name)&Key('username').eq(username)
        response=Notification_TemplateTable.scan(
            FilterExpression=filter_expression
        )
        return jsonify(response)
    else:
        username = request.json['username']
        filter_expression = Key('username').eq(username)
        response=Notification_TemplateTable.scan(
            FilterExpression=filter_expression
        )
        if response:
            return jsonify(response)
        else:
            return jsonify({'error':'No Result Found'})

@app.route("/a4b/api/v1.0/update_notification_template",methods=['POST'])
def update_notification_template():   
    #return jsonify(response)
    if 'template_name' in request.json:
        template_name = str(request.json['userid'])+'_@_'+(request.json['template_name'])
        template      = request.json['template']
        username      = request.json['username']
        old_template_name = str(request.json['userid'])+'_@_'+str(request.json['old_template_name'])
        filter_expression = Key('template_name').eq(template_name)
        response=Notification_TemplateTable.scan(
            FilterExpression=filter_expression
        )
        if response['Count']>0 and template_name!=old_template_name:
            return jsonify({'error':'Notification Template with the name already exist'})
        else:
            filter_expression = Key('NotificationTemplate').eq(request.json['old_template_name'])
            req_response=requests_table.scan(
                FilterExpression=filter_expression
            )
            request_exist=req_response['Items']
            if not request_exist:
                response = Notification_TemplateTable.delete_item(
                    Key={
                        'template_name': old_template_name
                    }
                )
                response=Notification_TemplateTable.put_item(
                Item={
                    'template_name':template_name,
                    'template':template,
                    'username':username
                })
                return jsonify(response)
            else:
                return jsonify({'error':'Cannot Update Template Name while it is still associated to existing Request(s)'}) 
    else:
        return jsonify({'error':'No Notification Templates in the request'})        

@app.route("/a4b/api/v1.0/notification_temp_delete",methods=['POST'])
def notification_temp_delete():
    Notification_Temp_List=request.json['Notification_Temp']
    error = {}
    for Template in Notification_Temp_List:	
        filter_expression = Key('NotificationTemplate').eq(Template.strip())
        req_response=requests_table.scan(
            FilterExpression=filter_expression
        )
        request_exist=req_response['Items']
        if not request_exist:
            response = Notification_TemplateTable.delete_item(
                Key={
                    'template_name': str(request.json['userid'])+'_@_'+str(Template)
                }
            )
            pass    
        else:
            error["error"]="Cannot delete Template(s) while it is still associated to existing Requests"
    return jsonify(error)

#
#-----------------------SES--------------------------------------
#

@app.route("/a4b/api/v1.0/add_verify_email",methods=['POST'])
def add_verify_email():
	resp_add_verify_email = client_ses.verify_email_identity(
								EmailAddress=str(request.json['EmailID'])
							)
	return jsonify(resp_add_verify_email)

@app.route("/a4b/api/v1.0/delete_verify_email",methods=['POST'])
def delete_verify_email():
	resp_delete_verify_email = client_ses.delete_verified_email_address(
								EmailAddress=request.json['EmailID']
							)
	return jsonify(resp_delete_verify_email)

#@app.route("/a4b/api/v1.0/list_verified_emails",methods=['GET'])
def list_verified_emails():
	resp_list_verified_emails = client_ses.list_verified_email_addresses()
	return json.dumps(resp_list_verified_emails)
	
#------------------------End SES-------------------------------
    
if __name__ == "__main__":
	#app.run(debug=True)
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
