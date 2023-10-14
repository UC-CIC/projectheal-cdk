import json
import os
import boto3
import botocore
import itertools
from botocore.exceptions import ClientError
import json
from decimal import Decimal

CORS_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': os.environ["CORS_ALLOW_UI"] if os.environ["LOCALHOST_ORIGIN"] == "" else os.environ["LOCALHOST_ORIGIN"],
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT'
}

bedrock = boto3.client('bedrock' , 'us-east-1')
TEMPERATURE=.1
TOP_P=.8

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

def get_embedding(body, modelId, accept, contentType):
    response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    response_body = json.loads(response.get('body').read())
    embedding = response_body.get('embedding')
    return embedding


def handler(event,context):
    print(boto3.__version__)
    print(botocore.__version__)

    # Generation Data
    try:
        field_values=json.loads(event["body"])
        print(field_values)
        
        content=field_values["inputText"]
    except:
        print("<<<Fail safe generation executed>>>")
        content="Hello world!"


    body = json.dumps({'inputText': content})
    modelId = 'amazon.titan-embed-g1-text-02' # change this to use a different version from the model provider
    accept = 'application/json'
    contentType = 'application/json'
    embedding = get_embedding(body, modelId, accept, contentType)
    print(embedding)

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps(embedding,cls=JSONEncoder)
    }