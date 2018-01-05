#!/usr/bin/env python

import boto3
from boto3.dynamodb.conditions import Key, Attr
from config import *

client = boto3.client('organizations',aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=region_name)

def create_account(**kwargs):
	response=client.create_account(kwargs)
	
def move_acc(**kwargs):
	response=client.move_account(kwargs)

def list_acc(**kwargs):
	response = client.list_accounts(kwargs)
	
def create_policy(**kwargs):
	response=client.create_policy(kwargs)

def create_ou(**kwargs):
	response=client.create_organizational_unit(kwargs)
	
def create_organization(FeatureSet):
	response=client.create_organization(FeatureSet='CONSOLIDATED_BILLING')
