#!/bin/bash

# Authenticate ngrok with your account, 
ngrok config add-authtoken 1qpU7j7SxlDYCahmCom9l6H8dSZ_3MuoncJsBianKdL3TXLyp

# Start ngrok tunnel on port 5678
# ngrok http 4040
ngrok http --url=ibot.ngrok.app 5678
# docker run -it -e NGROK_AUTHTOKEN=1qpU7j7SxlDYCahmCom9l6H8dSZ_3MuoncJsBianKdL3TXLyp ngrok/ngrok http 5678 --url=ibot.ngrok.dev

# run: chmod +x start_ngrok.sh
# run: ./start_ngrok.sh