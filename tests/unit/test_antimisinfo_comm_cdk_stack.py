import aws_cdk as core
import aws_cdk.assertions as assertions
from antimisinfo_comm_cdk.antimisinfo_comm_cdk_stack import AntiMisinfoCommCdkStack


def test_sqs_queue_created():
    app = core.App()
    stack = AntiMisinfoCommCdkStack(app, "antimisinfo-comm-cdk")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::SQS::Queue", {
        "VisibilityTimeout": 300
    })


def test_sns_topic_created():
    app = core.App()
    stack = AntiMisinfoCommCdkStack(app, "antimisinfo-comm-cdk")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::SNS::Topic", 1)
