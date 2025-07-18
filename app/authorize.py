# authorize.py (コンソール認証・最終修正版)
import google.oauth2.credentials
import google_auth_oauthlib.flow

# client_secret.json を読み込み、必要な権限（スコープ）を設定
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=SCOPES,
    redirect_uri='http://localhost/'  # リダイレクトURIを設定
)

# 1. 認証用のURLを生成する
auth_url, _ = flow.authorization_url(prompt='consent')

print('以下のURLにアクセスして、このアプリケーションを認証してください:')
print(auth_url)

# 2. ユーザーにリダイレクト先URLから認証コードを入力してもらう
code = input('表示された認証コードをここに貼り付けてEnterキーを押してください: ')

# 3. 認証コードを使ってトークンを取得する
flow.fetch_token(code=code)
credentials = flow.credentials

# 取得した認証情報（トークン）をファイルに保存
with open('token.json', 'w') as token_file:
    token_file.write(credentials.to_json())

print("認証に成功しました。token.json を作成しました。")
print("このスクリプトは一度だけ実行すればOKです。")