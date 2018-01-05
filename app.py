from flask import Flask,render_template,request,jsonify
import os
import json
from config import *
import boto3

client_iam = boto3.client('iam',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)
client_a4b = boto3.client('alexaforbusiness',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name="us-east-1")

app=Flask(__name__)

@app.route("/")
def main():
	return render_template('login.html')

@app.route("/admin")
def admin():	
	return render_template('choices_admin.html')

@app.route("/newuser")
def newuser():
	return render_template('create_user.html')

@app.route("/add_new_user",methods = ['POST', 'GET'])
def add_new_user(**kwargs):
	if request.method == 'POST':
		#Create User
		response = client_iam.create_user(
		Path=request.form['Path'],
		UserName=request.form['UserName'])

		#Attach policy to user
		response_policy = client_iam.attach_user_policy(
		UserName=response['User']['UserName'],#see list IAM users to see all available users
		PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess')#see get policy arn to list all available policies
		
		#Get user info
		# response = client_iam.get_user(
		# UserName='vasavichitlur')
		
		#Create access Key
		response_access = client_iam.create_access_key(
		UserName=response['User']['UserName'])
		
		# user_arn=response['User']['Arn']
		# accesskey_id=response_access['AccessKey']['AccessKeyId']
		# secret_key=response_access['AccessKey']['SecretAccessKey']
		# filename=response_access['AccessKey']['UserName']
		
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
	return("User Created")
	#return jsonify(response)
	
@app.route("/skill_group")
def skill_group():
	return render_template('create_skillgroup.html')

@app.route("/add_skill_group",methods=['POST','GET'])
def add_skill_group():
	response=client_a4b.create_skill_group(
	SkillGroupName = request.form['SkillGroupName'],
	Description = request.form['Description'],
	ClientRequestToken = request.form['ClientRequestToken'])
	
	# response = client_a4b.search_skill_groups(
    # Filters=[
        # {
            # 'Key': 'SkillGroupName',
            # 'Values': [
                # 'kitchen',
            # ]
        # },
    # ]
	# )
	#return jsonify(response)
	return ("Skill Group Added")

@app.route("/user")
def user():
	return render_template('choices_users.html')

def create_client():
	UserName='vasaviCG'
	file = open('./users/'+UserName+'.json', 'r') 
	keys=json.loads(file.read())
	user_a4b=boto3.client('alexaforbusiness',aws_access_key_id=keys['aws_access_key_id'],aws_secret_access_key=keys['aws_secret_access_key'],region_name="us-east-1")
	return (user_a4b)
	
@app.route("/room_profile")
def room_profile():
	return render_template("create_roomprofile.html")
	
@app.route("/add_room_profile", methods=['POST','GET'])
def add_room_profile():
	user_a4b=create_client()#when login page is provided pass username from login page
	response = user_a4b.create_profile(
    ProfileName=request.form['ProfileName'],
    Timezone=request.form['Timezone'],
    Address=request.form['Address'],
    DistanceUnit=request.form['DistanceUnit'],
    TemperatureUnit=request.form['TemperatureUnit'],
    WakeWord=request.form['WakeWord'],
    ClientRequestToken=request.form['ClientRequestToken'],
    SetupModeDisabled=bool(request.form['SetupModeDisabled']),
    MaxVolumeLimit=int(request.form['MaxVolumeLimit']),
    PSTNEnabled=bool(request.form['PSTNEnabled']))
	
	#return jsonify(response)
	return ("Room Profile Added")

@app.route("/rooms")
def rooms():
	return render_template("create_room.html")
	
@app.route("/add_rooms",methods=['POST','GET'])
def add_rooms():
	user_a4b=create_client()
	# response = user_a4b.create_room(
    # RoomName=request.form['RoomName'],
    # Description=request.form['Description'],
    # ProfileArn=request.form['ProfileArn'],
    # ProviderCalendarId=request.form['ProviderCalendarId'],
    # ClientRequestToken=request.form['ClientRequestToken'])
	
	response = user_a4b.search_profiles(
    Filters=[
        {
            'Key': 'ProfileName',
            'Values': [
                'kitchen',
            ]
        },
    ]
	)
	#return jsonify(response)
	return("Rooms Created")
	
@app.route("/devices")
def devices():
	return("Option to add devices and associate it to room will be available shortly")
		
if __name__ == "__main__":
	#app.run(debug=True)
    app.debug = True
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
