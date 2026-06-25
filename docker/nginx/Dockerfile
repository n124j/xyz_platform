FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY proxy_params.conf /etc/nginx/proxy_params.conf
RUN mkdir -p /etc/nginx/certs
EXPOSE 80 443
