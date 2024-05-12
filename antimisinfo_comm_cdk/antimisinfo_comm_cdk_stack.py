import os

from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    Duration,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3
)

import cdklabs.generative_ai_cdk_constructs

class AntiMisinfoCommCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #######################################################
        #hardcoded -- fix later
        ALLOW_LOCALHOST_ORIGIN=True
        FULL_CFRONT_URL=""
        LOCALHOST_ORIGIN="http://localhost:3000"
        #######################################################


        kb = cdklabs.generative_ai_cdk_constructs.bedrock.KnowledgeBase(self, 'KnowledgeBase', 
                    embeddings_model= cdklabs.generative_ai_cdk_constructs.bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V1,
                    instruction= 'This KB contains trusted information about health topics.'                     
                )

        docBucket = s3.Bucket(self, 'DockBucket')

        cdklabs.generative_ai_cdk_constructs.bedrock.S3DataSource(self, 'DataSource',
            bucket= docBucket,
            knowledge_base=kb,
            data_source_name='trusted',
            chunking_strategy=cdklabs.generative_ai_cdk_constructs.bedrock.ChunkingStrategy.FIXED_SIZE,
            max_tokens=500,
            overlap_percentage=20   
        )

        '''
        layer_bedrock_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_sdk",
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda/custom_packages/layers","bedrock-boto3-1.26.162.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_sdk"
        )

        layer_bedrock_botocore_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_botocore_sdk",
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda/custom_packages/layers","bedrock-botocore-1.26.162.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_botocore_sdk"
        )
        '''

        layer_bedrock_boto3_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_botocore_sdk",
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda/custom_packages/layers","boto3.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_botocore_sdk"
        )

        bedrock_lambda_role = iam.Role(self, "bedrock-lambda-role",
          assumed_by=iam.CompositePrincipal(
            iam.ServicePrincipal("lambda.amazonaws.com"),
            )
        )

 
        fn_bedrock_handler = lambda_.Function(
            self,"fn-bedrock-handler",
            description="fn-bedrock-handler", #microservice tag
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            role=bedrock_lambda_role,
            timeout=Duration.seconds(300),  
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda","bedrock_handler")),
            environment={
                "CORS_ALLOW_UI":FULL_CFRONT_URL,
                "LOCALHOST_ORIGIN":LOCALHOST_ORIGIN if ALLOW_LOCALHOST_ORIGIN else "",
                "KB_ID":kb.knowledge_base_id
            },
            layers=[ layer_bedrock_boto3_sdk ]
        )



        #######################################################
        #hardcoded -- fix later (origin vars)
        #######################################################
        fn_bedrock_vector_handler = lambda_.Function(
            self,"fn-bedrock-vector-handler",
            description="fn-bedrock-vector-handler", #microservice tag
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.handler",
            role=bedrock_lambda_role,
            timeout=Duration.seconds(300),  
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda","bedrock_vector_handler")),
            environment={
                "CORS_ALLOW_UI":"",
                "LOCALHOST_ORIGIN":"*",
            },
            layers=[ layer_bedrock_boto3_sdk ]
        )


        bedrock_lambda_role.attach_inline_policy(iam.Policy(self, "bedrock-allow-policy",
            statements=[iam.PolicyStatement(
                actions=["bedrock:InvokeModel","bedrock:RetrieveAndGenerate","bedrock:Retrieve"],
                resources=["*"]
            )             
            ]
        ))
        bedrock_lambda_role.attach_inline_policy(iam.Policy(self, "bedrock-basic-execution-logging",
            statements=[iam.PolicyStatement(
                actions=["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
                resources=["*"]
            )             
            ]
        ))



        #######################################################
        #hardcoded -- fix later (allow origin)
        #######################################################
        core_api = apigateway.RestApi(
            self,"core-api",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_methods=['GET', 'OPTIONS','PUT','PATCH','POST'],
                #allow_origins=[FULL_CFRONT_URL, LOCALHOST_ORIGIN if ALLOW_LOCALHOST_ORIGIN else ""])
                allow_origins=["*"])
        )

        ###### Route Base = /api [match for cloud front purposes]
        api_route = core_api.root.add_resource("api")

        # /generate/communication

        # /generate/
        public_route_generate=api_route.add_resource("generate")
        # /generate/communication
        public_route_communication=public_route_generate.add_resource("communication")
        # POST: /generate/communication
        communication_post_integration=apigateway.LambdaIntegration(fn_bedrock_handler)
        method_uploader_post=public_route_communication.add_method(
            "POST",communication_post_integration,
            api_key_required=True
        )       
        # POST: /generate/embeddings
        public_route_embeddings=public_route_generate.add_resource("embeddings")
        embeddings_post_integration=apigateway.LambdaIntegration(fn_bedrock_vector_handler)
        method_embeding_post=public_route_embeddings.add_method(
            "POST",embeddings_post_integration,
            api_key_required=True
        )     

        #################################################################################
        # Usage plan and api key to "lock" API to only CFRONT calls (or local in our case)
        #################################################################################
        plan = core_api.add_usage_plan(
            "UsagePlan",name="public plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=10,
                burst_limit=2
            )
        )

        core_key=core_api.add_api_key("core-api-key")
        plan.add_api_key(core_key)
        plan.add_api_stage(api=core_api,stage=core_api.deployment_stage)
