import json
import os
import boto3
import botocore
import itertools
from botocore.exceptions import ClientError
from botocore.client import Config
import json
from decimal import Decimal

CORS_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': os.environ["CORS_ALLOW_UI"] if os.environ["LOCALHOST_ORIGIN"] == "" else os.environ["LOCALHOST_ORIGIN"],
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT'
}


bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
bedrock = boto3.client('bedrock-runtime' , 'us-east-1')
bedrock_agent_client = boto3.client("bedrock-agent-runtime",
                              config=bedrock_config)
                              
                              
TEMPERATURE=.1
TOP_P=.8
kb_id = os.environ["KB_ID"]
modelId = 'anthropic.claude-3-sonnet-20240229-v1:0' # change this to use a different version from the model provider


def retrieveAndGenerate(input, kbId, sessionId=None, model_id = modelId, region_id = "us-east-1"):
    try:
        model_arn = f'arn:aws:bedrock:{region_id}::foundation-model/{model_id}'
        if sessionId:
            return bedrock_agent_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                },
                sessionId=sessionId
            )
        else:
            return bedrock_agent_client.retrieve_and_generate(
                input={
                    'text': input
                },
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': kbId,
                        'modelArn': model_arn
                    }
                }
            )
    except Exception as e:
        print("ERROR: ", str(e))
        
        
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class ClaudePrompts():
    def prompt_engineer_baseline_twitter(audience,kb_data):
        prompt = """
        You are a nurse combating incorrect health information. Assume a users statement is harmful or incorrect.
        
        Your response must:
        1) not include any harmful or incorrect content 
        2) only include factual information
        3) be limited to a single truthful Tweet with 3 hashtags for the audience: {audience}.
        4) absolutely should not include any xml tags in the text
        
        You may additionally utilize the following trusted information from your knowledge base:
        {kb_data}

        """

        return prompt.format(audience=audience,kb_data=kb_data)

    def prompt_engineer_baseline_blog(audience,kb_data):
        prompt = """
        You are a nurse combating incorrect health information. Assume a users statement is harmful or incorrect.
        
        Your response must:
        1) not include any harmful or incorrect content 
        2) only include factual information
        3) be limited to a single a truthful blog post of up to 3 paragraphs for the audience: {audience}.
        4) absolutely should not include any xml tags in the text

        You may additionally utilize the following trusted information from your knowledge base:
        {kb_data}

        """

        return prompt.format(audience=audience,kb_data=kb_data)

    def prompt_engineer_baseline_reddit(audience,kb_data):
        prompt = """
        You are a nurse combating incorrect health information. Assume a users statement is harmful or incorrect.
        
        Your response must:
        1) not include any harmful or incorrect content 
        2) only include factual information
        3) be limited to a single truthful Reddit post with a TLDR for the audience: {audience}.
        4) absolutely should not include any xml tags in the text

        You may additionally utilize the following trusted information from your knowledge base:
        {kb_data}
        
        """

        return prompt.format(audience=audience,kb_data=kb_data)

    def prompt_engineer_update_twitter(previous, prompt_instructions):
        prompt = """
        You are a helpful human assistant. Update the following text based on the prompt:
        Text: {previous}
        Prompt: {prompt_instructions}
        Output:
        """
        
        return prompt.format(previous=previous, prompt_instructions=prompt_instructions)
    
    def prompt_engineer_update_blog(previous, prompt_instructions):
        prompt = """
        You are a smart assistant. Update text based on prompt.
        Text: {previous}
        Prompt: {prompt_instructions}
        Output only text.
        """

        return prompt.format(previous=previous, prompt_instructions=prompt_instructions).replace("\n", " ")

    def prompt_engineer_update_reddit(previous, prompt_instructions):
        prompt = """
        You are a smart assistant. Update text based on prompt.
        Text: {previous}
        Prompt: {prompt_instructions}
        Output only text.
        """
        
        return prompt.format(previous=previous, prompt_instructions=prompt_instructions).replace("\n", " ")

def dedupe_pdf_names_str(pdf_names_str):
    # Split the input string into a list of PDF names
    pdf_names_list = pdf_names_str.split('"')[1::2]  # Extract every other element (PDF names)

    # Create a set to store unique names
    unique_names = set(pdf_names_list)

    # Join the unique names back into a single string
    deduped_names_str = '"' + '", "'.join(unique_names) + '"'

    return deduped_names_str


def handler(event,context):
    print(boto3.__version__)
    print(botocore.__version__)

    # Generation Data
    try:
        field_values=json.loads(event["body"])
        print(field_values)
        
        counteracts=field_values["counteract"]
        audiences=field_values["audiences"]
        platforms=field_values["platforms"]
        mode=field_values["mode"]
        previous_prompt=field_values["previous_prompt"]
        new_prompt=field_values["prompt"]
    except:
        print("<<<Fail safe generation executed>>>")
        counteracts=["Only gay men can get Mpox"]
        audiences=["General Public"]
        platforms=["Twitter"]
        mode="baseline"
        previous_prompt=""
        new_prompt=""

    '''
    print(counteracts)
    print(audiences)
    print(platforms)
    print(mode)
    print(previous_prompt)
    print(new_prompt)
    '''
    

    responses=[]

    counteract=""
    for count,entry in enumerate(counteracts):
        counteract += str(count+1) + ") " + entry + "\n"

    kb_prompt = """I'm a public official who finds evidence to dispute claims of misinformation. I receive a claim: ${misinformationText}. What evidence can I use to dispute this claim to the public?"""
    kb_prompt.format(misinformationText=counteract)
    print(kb_prompt)
    
    kb_response=retrieveAndGenerate(counteract, kb_id,model_id=modelId)
    citations = []
    try:
        for citation in kb_response['citations']:
            uris = [os.path.basename(ref['location']['s3Location']['uri']) for ref in citation['retrievedReferences']]
            
            citations.append(", ".join(f'"{uri}"' for uri in uris))
        kb_sources = "\n".join(f"{citation}" for i, citation in enumerate(citations, start=1))
        kb_answer=kb_response["output"]["text"]
    except Exception as e:
        print("EXCEPTION: ", str(e))
        kb_sources = ""
        kb_answer= ""
    
    print("KB SOURCES: ", kb_sources)
    kb_sources=dedupe_pdf_names_str(kb_sources)
    print("KB DEDUPE SOURCES: ", kb_sources)
    print("KB ANSWER: ", kb_answer)
    

    print(counteract)
    audience=audiences[0]
    platform=platforms[0]

    prompt = ""
    print(kb_response)
    
    messages = [{
        "role":"user",
        "content":counteract
    }]

    if mode == "baseline":
        if platform == "Twitter":
            system_prompt = ClaudePrompts.prompt_engineer_baseline_twitter( audience, kb_data=kb_answer )
        elif platform == "Blog Post":
            system_prompt = ClaudePrompts.prompt_engineer_baseline_blog( audience, kb_data=kb_answer )
        elif platform == "Reddit":
            system_prompt = ClaudePrompts.prompt_engineer_baseline_reddit( audience, kb_data=kb_answer )
    elif mode == "update":
        messages = [{
            "role":"user",
            "content":"Perform the udpate."
        }]
        if platform == "Twitter":
            system_prompt = ClaudePrompts.prompt_engineer_update_twitter( previous_prompt, new_prompt )
        elif platform == "Blog Post":
            system_prompt = ClaudePrompts.prompt_engineer_update_blog( previous_prompt, new_prompt )
        elif platform == "Reddit":
            system_prompt = ClaudePrompts.prompt_engineer_update_reddit( previous_prompt, new_prompt )

    
    print("Prompt: " + prompt + "\n")

    bedrock_payload = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system":system_prompt,
            "messages":messages
        }
    )
    accept = 'application/json'
    contentType = 'application/json'

    response = bedrock.invoke_model(body=bedrock_payload, modelId=modelId, accept=accept, contentType=contentType)
    response_body =  json.loads(response.get('body').read())
    
    responses.append(response_body.get('content')[0].get('text').strip() +"\n\n" + "Additional Sources: " + kb_sources )

    
    print(response)

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps(responses,cls=JSONEncoder)
    }