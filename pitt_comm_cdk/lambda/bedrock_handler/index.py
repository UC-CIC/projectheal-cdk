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


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)
    
def handler(event,context):
    print(boto3.__version__)
    print(botocore.__version__)

    

    # Generation Data
    try:
        field_values=json.loads(event["body"])
        counteracts=field_values["counteract"]
        audiences=field_values["audiences"]
        platforms=field_values["platforms"]
    except:
        print("Fail safe generation executed")
        counteracts=["Only gay men can get Mpox"]
        audiences=["General Public"]
        platforms=["Twitter"]


    
    combos_choices = [counteracts,audiences,platforms]
    combos=list(itertools.product(*combos_choices))

    responses = []

    i = 1
    for combo in combos:
        counteract=combo[0]
        audience=combo[1]
        platform=combo[2]
        bedrock_payload = json.dumps(
            {
                "inputText": "what is 5 multiplied by 5",
                "textGenerationConfig": {
                    "maxTokenCount": 512,
                    "stopSequences": [],
                    "temperature": 0,
                    "topP": 0.9
                } 
            }
        )
        modelId = 'amazon.titan-tg1-large' # change this to use a different version from the model provider
        accept = 'application/json'
        contentType = 'application/json'

        response = bedrock.invoke_model(body=bedrock_payload, modelId=modelId, accept=accept, contentType=contentType)
        response_body =  json.loads(response.get('body').read())
        print( response_body )
        # short circuit
        i += 1
        if i > 5:
            break

    
        

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps({},cls=JSONEncoder)
    }