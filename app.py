import os
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent, TextMessageContent
)
from openai import OpenAI

# 加載 .env 文件中的環境變數
load_dotenv()

ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
TO_YOSHIO = os.environ.get('TO_YOSHIO')
TO_YUTO = os.environ.get('TO_YUTO')
YOSHIO = os.environ.get('YOSHIO')
YUTO = os.environ.get('YUTO')

app = Flask(__name__)

configuration = Configuration(access_token=ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        user_text = event.message.text
        user_id = event.source.user_id

        if event.source.type == 'group':
            try:
                profile = line_bot_api.get_group_member_profile(event.source.group_id, user_id)
                user_name = profile.display_name
                print('Successfully obtained user id in group.')
            except Exception as e:
                print("Exception when calling MessagingApi->get_profile: %s\n" % e)
        elif event.source.type == 'user':
            try:
                profile = line_bot_api.get_profile(user_id)
                user_name = profile.display_name
                print('Successfully obtained user id.')
            except Exception as e:
                print("Exception when calling MessagingApi->get_profile: %s\n" % e)
        else:
            print("Unexpected event.source.type: " + event.source.type)

        nagada = [YUTO, YOSHIO]
        
        if user_name in nagada:
            print('you are in nagada.')
            try:
                client = OpenAI()
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "你是位翻譯員，請將使用者輸入的日文翻譯成中文。"\
                                                        "使用正體中文字，勿使用簡體字。翻譯文字內容就好，"\
                                                        "不用針對內容發表建議。"},
                        {"role": "user", "content": user_text}
                    ]
                )
                msg = completion.choices[0].message.content
            except Exception as e:
                print("Exception when calling OpenAI API: %s\n" % e)
                msg = "抱歉，處理您的請求時出現了問題。請稍後再試。"
        else:
            print('you are not in nagada.')           
            if user_text.startswith(TO_YUTO) or user_text.startswith(TO_YOSHIO):
                try:            
                    client = OpenAI()
                    completion = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "你是位翻譯員，請將使用者輸入的中文翻譯成日文。"\
                                                            "翻譯文字內容就好，不用針對內容發表建議。"},
                            {"role": "user", "content": user_text}
                        ]
                    )
                    msg = completion.choices[0].message.content
                except Exception as e:
                    print("Exception when calling OpenAI API: %s\n" % e)
                    msg = "抱歉，處理您的請求時出現了問題。請稍後再試。"
            else:
                return
            
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=msg)]
            )
        )


if __name__ == "__main__":
    app.run()
