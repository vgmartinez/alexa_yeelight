#!/usr/bin/env bash
rm yeelight_control.zip
cd lambda/
zip -r ../yeelight_control.zip *
cd ..

#use this command to upload from CLI.
aws lambda update-function-code --function-name yeelight_control --zip-file fileb://yeelight_control.zip