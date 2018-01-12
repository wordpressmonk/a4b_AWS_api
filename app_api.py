from flask import Flask,render_template,request,jsonify
import os,json,boto3
from config import *

client_iam = boto3.client('iam',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_a4b = boto3.client('alexaforbusiness',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name="us-east-1")

app=Flask(__name__)

@app.route("/")
def main():
	return render_template('login.html')

@app.route("/admin")
def admin():	
	return render_template('choices_admin.html')

@app.route("/a4b/api/v1.0/add_new_user",methods = ['POST'])
def add_new_user():
	#Create User
	response = client_iam.create_user(
	Path=request.json['Path'],
	UserName=request.json['UserName'])

	#Attach policy to user
	response_policy = client_iam.attach_user_policy(
	UserName=response['User']['UserName'],#see list IAM users to see all available users
	PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')#see get policy arn to list all available policies
	
	#Create access Key
	response_access = client_iam.create_access_key(
	UserName=response['User']['UserName'])
	
	#store access keys in a file for user created
	username_dict={}
	username_dict['aws_access_key_id']=response_access['AccessKey']['AccessKeyId']
	username_dict['aws_secret_access_key']=response_access['AccessKey']['SecretAccessKey']
	username_dict['arn']=response['User']['Arn']
	
	file=open("./users/"+response_access['AccessKey']['UserName']+".json","w")
	file.write(json.dumps(username_dict))
	file.close()
	
	#delete access keys
	# response = client_iam.delete_access_key(
	# UserName='rohit',
	# AccessKeyId='AKIAJFZYZXK3LNAPQYDA')
	
	# detach user policy
	# response = client_iam.detach_user_policy(
	# UserName='rohit',
	# PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')

	# to delete user first delete access keys and policies attached to that user and then delete user
	# delete user
	# response = client.delete_user(
	# UserName='arn:aws:iam::512990229200:user/HotelA/rohit')
	
#return("User Created")
	return jsonify(response)
@app.route("/a4b/api/v1.0/list_users",methods=['GET'])
def list_users():
	response=client_iam.list_users()
	return jsonify(response)

@app.route("/a4b/api/v1.0/add_skill_group",methods=['POST'])
def add_skill_group():
	response=client_a4b.create_skill_group(
	SkillGroupName = request.json['SkillGroupName'],
	Description = request.json['Description'],
	ClientRequestToken = request.json['ClientRequestToken'])
	#print(SkillGroupName)#,Description,ClientRequestToken)	
	return jsonify(response)
	#return ("Skill Group Added")

def create_client():
	UserName='vasaviCG'
	file = open('./users/'+UserName+'.json', 'r') 
	keys=json.loads(file.read())
	user_a4b=boto3.client('alexaforbusiness',aws_access_key_id=keys['aws_access_key_id'],aws_secret_access_key=keys['aws_secret_access_key'],region_name="us-east-1")
	return (user_a4b)
	
@app.route("/a4b/api/v1.0/add_room_profile", methods=['POST'])
def add_room_profile():
	user_a4b=create_client()#when login page is provided pass username from login page
	response = user_a4b.create_profile(
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
	
@app.route("/a4b/api/v1.0/add_rooms",methods=['POST'])
def add_rooms():
	user_a4b=create_client()
	response = user_a4b.create_room(
	RoomName=request.json['RoomName'],
	Description=request.json['Description'],
	ProfileArn=request.json['ProfileArn'],
	#ProviderCalendarId=request.json['ProviderCalendarId'],
	ClientRequestToken=request.json['ClientRequestToken'])
	
	# response = user_a4b.search_profiles(
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
			
if __name__ == "__main__":
	#app.run(debug=True)
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
