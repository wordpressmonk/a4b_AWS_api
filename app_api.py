from flask import Flask,render_template,request,jsonify
import os,json,boto3
from config import *
from functools import wraps
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

client_iam = boto3.client('iam',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
client_a4b = boto3.client('alexaforbusiness',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_dynamodb = boto3.resource('dynamodb',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)

table=client_dynamodb.Table('IamUser')
requests_table=client_dynamodb.Table('Requests')

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
@handle_stripe
def add_room_profile():
	#user_a4b=create_client()#when login page is provided pass username from login page
	response = client_a4b.create_profile(
	ProfileName=request.json['ProfileName'],
	Timezone=request.json['Timezone'],
	Address=request.json['Address'],
	DistanceUnit=request.json['DistanceUnit'],
	TemperatureUnit=request.json['TemperatureUnit'],
	WakeWord=request.json['WakeWord'],
	#ClientRequestToken=request.json['ClientRequestToken'],
	SetupModeDisabled=bool(request.json['SetupModeDisabled']),
	MaxVolumeLimit=int(request.json['MaxVolumeLimit']),
	PSTNEnabled=bool(request.json['PSTNEnabled']))
	#return jsonify(response)
	#return ("Room Profile Added")
	return list_room_profile()
	
@app.route("/a4b/api/v1.0/list_room_profile", methods=['GET'])
@handle_stripe
def list_room_profile():
	response = client_a4b.search_profiles()
	profiles=response['Profiles']
	ProfileNameList=[]
	for profile in profiles:
		ProfileNameList.append(profile['ProfileName'])
	return jsonify(ProfileNameList)
	
	
@app.route("/a4b/api/v1.0/get_room_profile_info", methods=['POST'])
@handle_stripe
def get_room_profile_info():#ProfileName
	ProfileName=request.json['ProfileName']
	ProfileArn=get_profile_arn(ProfileName)
	
	response_p_info= client_a4b.get_profile(
		ProfileArn=ProfileArn
		)
	return jsonify(response_p_info['Profile'])
	

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
	ProfileName=request.json['ProfileName']
	ProfileArn=get_profile_arn(ProfileName)
	
	response = client_a4b.update_profile(
    ProfileArn=ProfileArn,
	ProfileName=request.json['NewProfileName'],
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

@app.route("/a4b/api/v1.0/delete_room_profile", methods=['POST'])
@handle_stripe
def delete_room_profile():
	ProfileNameList=request.json['ProfileName']
	for OneProfileName in ProfileNameList:
		ProfileName=OneProfileName
		ProfileArn=get_profile_arn(ProfileName)
		
		response = client_a4b.delete_profile(
		ProfileArn=ProfileArn
	)
		
	# return get_rooms()
	# ProfileName=request.json['ProfileName']
	# ProfileArn=get_profile_arn(ProfileName)
	
	# response = client_a4b.delete_profile(
		# ProfileArn=ProfileArn
	# )
	return list_room_profile()

#
#CRUD for rooms
#
	
@app.route("/a4b/api/v1.0/add_rooms",methods=['POST'])
@handle_stripe
def add_rooms():
	#user_a4b=create_client()
	#get profile arn from profile name
	
	ProfileName=request.json['ProfileName']
	ProfileArn=get_profile_arn(ProfileName)
	
	response = client_a4b.create_room(
	RoomName=request.json['RoomName'],
	ProfileArn=ProfileArn)
	
	#return (response['RoomArn'])
	return associate_device_room(response['RoomArn'],request.json['DeviceName'])

	

def get_room_arn(RoomName):
	response_parn= client_a4b.search_rooms(
    Filters=[
        {
            'Key':'RoomName', 
			'Values':[RoomName]
        }
			])
	return response_parn['Rooms'][0]['RoomArn']
	#return jsonify(response_parn['Rooms'])
	
		
@app.route("/a4b/api/v1.0/update_rooms",methods=['POST'])
@handle_stripe
def update_rooms():
	#client_a4b=create_client()
	
	#get roomarn from roomname
	RoomName=request.json['RoomName']
	RoomArn=get_room_arn(RoomName)
	
	#get profile arn from profile name
	ProfileName=request.json['ProfileName']
	ProfileArn=get_profile_arn(ProfileName)
	
	#call update room only for changing room profile
	response= client_a4b.update_room(
    RoomArn=RoomArn,
    #RoomName=request.json['RoomName'],
    #Description=request.json['Description'],
    #ProviderCalendarId=request.json['ProviderCalendarId'],
    ProfileArn=ProfileArn)
	
	return jsonify(response)
	
@app.route("/a4b/api/v1.0/delete_rooms",methods=['POST'])
@handle_stripe
def delete_rooms():
	#get roomarn from roomname
	RoomNameList=request.json['RoomName']
	for OneRoomName in RoomNameList:
		RoomName=OneRoomName
		RoomArn=get_room_arn(RoomName)
		
		response = client_a4b.delete_room(
		RoomArn=RoomArn)
		
	return get_rooms()
	
	
@app.route("/a4b/api/v1.0/get_rooms",methods=['POST'])
def get_rooms():	
	#client_a4b=create_client()
    if 'RoomName' in request.json:
        RoomName=request.json['RoomName']
        response = client_a4b.search_rooms(
        Filters=[
        {
            'Key':'RoomName', 
            'Values':[RoomName]
        }
        ]
        )
    else:
        response = client_a4b.search_rooms()

    DeviceDict = list_devices_with_rooms()
    rooms=response['Rooms']
    List_room_info=[]
    # RoomNameList=[]
    # RoomProfileList=[]
    for room in rooms:
        Roomdict={}
        Roomdict['RoomName']=room['RoomName']
        Roomdict['ProfileName']=room['ProfileName']
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
        if 'DeviceName' in request.json:
            DeviceName=request.json['DeviceName']
            response = client_a4b.search_devices(
            Filters=[
            {
                'Key':'DeviceName', 
                'Values':[DeviceName]
            }
            ]
            )
        else:
            response = client_a4b.search_devices()
        devices = response['Devices']
        DeviceList = []
        for device in devices:
            DeviceDict={}
            DeviceDict['DeviceName']=device['DeviceName']
            DeviceDict['DeviceSerialNumber']=device['DeviceSerialNumber']
            DeviceDict['DeviceType']=device['DeviceType']
            DeviceDict['DeviceStatus']=device['DeviceStatus']
            DeviceDict['DeviceName']=device['DeviceName']
            if "RoomName" in device.keys(): # condition to check if devices are associated with any rooms
                DeviceDict['RoomName'] = device['RoomName']	
            DeviceList.append(DeviceDict)
        return jsonify(DeviceList)
        # return jsonify(response)

@app.route("/a4b/api/v1.0/update_device",methods=['POST'])
@handle_stripe
def update_device():
		DeviceName_old = request.json['DeviceName_Old']
		DeviceName_new = request.json['DeviceName_New']
		DeviceArn = get_device_arn(DeviceName_old)
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
def disassociate_device_from_room():
	DeviceName=request.json['DeviceName']
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
	OtherDetails={}

	OtherDetails['request_name'] = request.json['RequestName'].lower()
	OtherDetails['Status']=request.json["Status"]
	OtherDetails['RequestType']=request.json["RequestType"]
	OtherDetails['NotificationTemplate']=request.json["NotificationTemplate"]
	
	if "Check_Email" in request.json and request.json["Check_Email"]== "1":
		OtherDetails['EmailID']=request.json["EmailID"]
		
	if "Check_Text" in request.json and request.json["Check_Text"]== "1":
		OtherDetails['TextNumber']=request.json["TextNumber"]
		
	if "Check_Call" in request.json and request.json["Check_Call"]== "1":
		OtherDetails['CallNumber']=request.json["CallNumber"]
		
	
	Level=int(request.json["Level"])
	OtherDetails['Level']=request.json["Level"]
	for i in range(Level):
		Q = request.json["Q"+str(i+1)]
		A = request.json["A"+str(i+1)]
		
		OtherDetails["Q"+str(i+1)]= Q
		OtherDetails["A"+str(i+1)]= A
		
	for key,value in OtherDetails.items():
		print(key+":"+value)
		
	response=requests_table.put_item(
	Item=OtherDetails)
	
	#return display_menu()
	return jsonify(response)
	
@app.route("/a4b/api/v1.0/requests_read",methods=['POST'])	
def requests_read():
	response = requests_table.query(
		KeyConditionExpression=Key('request_name').eq(request.json['request_name'])
		)
	
	return jsonify(response['Items'])

# @app.route("/a4b/api/v1.0/requests_update",methods=['POST'])	
# def requests_update():
	



if __name__ == "__main__":
	#app.run(debug=True)
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
