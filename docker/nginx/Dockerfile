FROM nginx:1.15.12-alpine

# デフォルトのconfを消して、別の設定を追加
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx_file/nginx.conf /etc/nginx/conf.d