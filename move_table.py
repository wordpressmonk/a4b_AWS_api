import boto3
import os

dynamoclient = boto3.client('dynamodb', region_name='us-east-1',
    aws_access_key_id="AKIAIXVXHEY3RVLB4HSQ",
    aws_secret_access_key='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')

dynamotargetclient = boto3.client('dynamodb', region_name='us-east-1',
    aws_access_key_id='AKIAITOJBMXAV5S5IWEA',
    aws_secret_access_key='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')

dynamopaginator = dynamoclient.get_paginator('scan')
tabname='abacies_quotes'
targettabname='abacies_quotes'
dynamoresponse = dynamopaginator.paginate(
    TableName=tabname,
    Select='ALL_ATTRIBUTES',
    ReturnConsumedCapacity='NONE',
    ConsistentRead=True
)
for page in dynamoresponse:
    for item in page['Items']:
        dynamotargetclient.put_item(
            TableName=targettabname,
            Item=item
        )