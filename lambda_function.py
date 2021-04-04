import generator
import boto3


def lambda_handler(event, context):
    if "domain" in event:
        domain = event["domain"]
        if domain:
            body = generator.genSecurityTxtForDomain(domain, return_body=True)
            if body:
                bucket = "gotsecuritytxt.com"
                key = f"gen/{domain}"

                s3r = boto3.resource("s3")
                s3Obj = s3r.Object(bucket, key)
                s3Obj.put(
                    ACL="public-read",
                    Body=body.encode("utf-8"),
                    ContentType="text/html",
                    CacheControl="public, max-age=60",
                )
