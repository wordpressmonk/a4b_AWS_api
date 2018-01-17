from flask import Flask,render_template,request,jsonify
import os,json,boto3
from config import *

client_iam = boto3.client('iam',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key)
client_a4b = boto3.client('alexaforbusiness',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_dynamodb = boto3.resource('dynamodb',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
table=client_dynamodb.Table('IamUser')

app=Flask(__name__)

# def create_a4b_client():
	# UserName='vasaviCG'
	# file = open('./users/'+UserName+'.json', 'r') 
	# keys=json.loads(file.read())
	# user_a4b=boto3.client('alexaforbusiness',aws_access_key_id=keys['aws_access_key_id'],aws_secret_access_key=keys['aws_secret_access_key'],region_name="us-east-1")
	# return (user_a4b)

	
@app.route("/")
def main():
	return render_template('login.html')

#
#CRUD for IAM Users
#
@app.route("/a4b/api/v1.0/add_new_user",methods = ['POST'])
def add_new_user():
    print(request.json)
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
def delete_users():
    if 'UserName' in request.json:
        try:
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
        except Exception as e:
            pass
    return list_users()

@app.route("/a4b/api/v1.0/list_users",methods=['GET'])
def list_users():
	response=client_iam.list_users()
	return jsonify(response)
	
@app.route("/a4b/api/v1.0/update_users",methods=['POST'])
def update_users():
	response=client_iam.update_user(
	UserName = request.json['UserName'],
	NewPath = request.json['NewPath'],
	NewUserName = request.json['NewUserName'])
	
	return jsonify(response)

#
#CRUD for Skill group	
#
	
@app.route("/a4b/api/v1.0/add_skill_group",methods=['POST'])
def add_skill_group():
	response=client_a4b.create_skill_group(
	SkillGroupName = request.json['SkillGroupName'],
	Description = request.json['Description'],
	ClientRequestToken = request.json['ClientRequestToken'])
	#print(SkillGroupName)#,Description,ClientRequestToken)	
	return jsonify(response)
	
#
#CRUD for roomprofile
#
	
@app.route("/a4b/api/v1.0/add_room_profile", methods=['POST'])
def add_room_profile():
	#user_a4b=create_client()#when login page is provided pass username from login page
	response = client_a4b.create_profile(
	ProfileName=request.json['ProfileName'],
	Timezone=request.json['Timezone'],
	Address=request.json['Address'],
	DistanceUnit=request.json['DistanceUnit'],
	TemperatureUnit=request.json['TemperatureUnit'],
	WakeWord=request.json['WakeWord'],
	ClientRequestToken=request.json['ClientRequestToken'],
	SetupModeDisabled=bool(request.json['SetupModeDisabled']),
	MaxVolumeLimit=int(request.json['MaxVolumeLimit']),
	PSTNEnabled=bool(request.json['PSTNEnabled']))
	return jsonify(response)
	#return ("Room Profile Added")
	
@app.route("/a4b/api/v1.0/list_room_profile", methods=['POST'])
def list_room_profile():
	response = client_a4b.create_profile()
	return jsonify(response)
#
#CRUD for rooms
#
	
@app.route("/a4b/api/v1.0/add_rooms",methods=['POST'])
def add_rooms():
	#user_a4b=create_client()
	response = client_a4b.create_room(
	RoomName=request.json['RoomName'],
	ProfileArn=request.json['ProfileArn'])
	
	# response = client_a4b.search_profiles(
    # Filters=[
        # {
            # 'Key': 'ProfileName',
            # 'Values': [
                # 'Hotel A',
            # ]
        # },
    # ]
	# )
	return jsonify(response)
	#return("Rooms Created")
@app.route("/a4b/api/v1.0/list_rooms",methods=['GET'])
def list_rooms():	
	#client_a4b=create_client()
	response = client_a4b.search_rooms(
	)
	return jsonify(response)
@app.route("/a4b/api/v1.0/update_rooms",methods=['POST'])
def update_rooms():
	#client_a4b=create_client()
	response= client_a4b.update_room(
    #RoomArn=request.json['RoomArn'],
    RoomName=request.json['RoomName']
    #Description=request.json['Description'],
    #ProviderCalendarId=request.json['ProviderCalendarId'],
    #ProfileArn=request.json['ProfileArn'])
	)
	return jsonfiy(response)


if __name__ == "__main__":
	#app.run(debug=True)
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
