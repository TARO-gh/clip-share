# clip-share
ゲームクリップを即座に別PCへ転送，さらにYoutube配信にもタイムスタンプを残します．

## こんな人におすすめ
- ゲームクリップを直ぐに簡単にスマホで確認・共有したい
- ゲーミングPCと別に24時間稼働のPCを持っている
- NVIDIA appやOBSでインスタントリプレイを使用している
- 記録用にYoutubeにも配信している

## 何ができるの
- 別PCのディレクトリを監視．新しいクリップを即座に転送．
- ブラウザですぐに閲覧・ダウンロード可能
- Youtubeの配信アーカイブにも，クリップ時のタイムスタンプをコメントで記録

## セットアップ方法
### 1.クリックが保存されるディレクトリをマウント
マウントポイントを作成
```bash
sudo mkdir -p /mnt/shared_folder
```
`/etc/fstab`に以下を追記
```bash
//<クリップが保存されるPCのIP>/Users/you/Videos/clips /mnt/shared_folder cifs username=<Microsoftアカウントのユーザ名>,password=<Microsoftアカウントのパスワード>,uid=1000,gid=1000,iocharset=utf8 0 0
```
マウント
```bash
sudo mount -a
```

### 2. リポジトリを自身の環境にクローン
```bash
git clone https://github.com/TARO-gh/clip-share.git
cd clip-share
```

### 3. Google CloudでOAuth2.0クライアントIDを発行
Google CloudでYoutube Data API v3を有効にしたプロジェクトを作成．
OAuth 2.0 クライアント IDを発行し，client_secret.jsonをダウンロード．
`app/`直下に配置してください．

### 4. .envと各ディレクトリの作成
`app/.env.example`を参考に`app/.env`を作成してください．

### 5. dockerコンテナのビルド&アタッチ
```bash
docker compose up -d --build
docker compose exec clip_share_monitoring bash
```
### 6. authorized.pyの実行
以下を実行．
```bash
python3 authorized.py
```
ここでターミナルに表示されるリンクをクリックし，自身のGoogleアカウントで認証
進めると「ページが表示できません」となるので，そのページのURLに含まれる`code`をコピー．
ターミナルにペーストし認証を完了すると，`app/`直下にtoken.jsonが保存される．
あとはデタッチしてセットアップ完了．
```bash
exit
```


## Youtube Data APIについて
使用は完全無料．ただし1日あたりの上限が設定されており，超過するとストップする．
APIごとに使用するクォータが定められている．1日あたり10,000クォータまで使用可能

#### 本サービスで使用するAPIとそのクォータ

| API 名                                 | メソッド                       | 用途                                      | クォータコスト |
|----------------------------------------|--------------------------------|------------------------------------------|----------------|
| `liveBroadcasts.list`                  | `youtube.liveBroadcasts().list`| 自分のライブ配信情報の取得                 | 1              |
| `videos.list`                          | `youtube.videos().list`        | 動画の詳細（開始時刻）取得                 | 1              |
| `commentThreads.insert`                | `youtube.commentThreads().insert`| 通常コメントの投稿                      | 50             |

#### 本サービスでのクォータ消費の流れ
- 配信開始
- クリップ保存するごとに2クォータ
- 以降配信終了検知まで10分ごとに1クォータ (クリップの本数によらず，1配信で10分ごとに1クォータ)
- コメント投稿に50クォータ