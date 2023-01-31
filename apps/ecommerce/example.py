# Source: https://github.com/aws-samples/amazon-textract-code-samples/blob/master/python/01-detect-text-local.py

import os

import boto3

from project.settings import BASE_DIR

# Document

documentName = os.path.join(BASE_DIR, "apps", "ecommerce", "purchase-receipt-jpg.jpg")

# Read document content
with open(documentName, 'rb') as document:
    imageBytes = bytearray(document.read())

# Amazon Textract client
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
textract = boto3.client('textract', aws_access_key_id = AWS_ACCESS_KEY_ID, aws_secret_access_key = AWS_SECRET_ACCESS_KEY)

# Call Amazon Textract
response = textract.detect_document_text(Document={'Bytes': imageBytes})

# print(response)

# Print detected text
for item in response["Blocks"]:
    if item["BlockType"] == "LINE":
        print ('\033[94m' +  item["Text"] + '\033[0m')