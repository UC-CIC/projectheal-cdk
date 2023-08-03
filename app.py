#!/usr/bin/env python3

import aws_cdk as cdk

from antimisinfo_comm_cdk.antimisinfo_comm_cdk_stack import AntiMisinfoCommCdkStack


app = cdk.App()
AntiMisinfoCommCdkStack(app, "antimisinfo-comm-cdk")

app.synth()
