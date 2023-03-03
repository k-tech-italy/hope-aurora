worker_processes 1;
events {
  worker_connections 512;
}
daemon on;
error_log /dev/stdout;

http {
    include    /conf/mime.types;
    proxy_cache_path /data/nginx/cache keys_zone=one:10m max_size=50m inactive=1d ;
    proxy_cache_key '${DOLLAR}host${DOLLAR}request_uri${DOLLAR}cookie_user';
    proxy_cache_methods GET HEAD;
    proxy_cache_min_uses 5;
    map ${DOLLAR}status ${DOLLAR}status_text {
      400 'Bad Request';
      401 'Unauthorized';
      402 'Payment Required';
      403 'Forbidden';
      404 'Not Found';
      405 'Method Not Allowed';
      406 'Not Acceptable';
      407 'Proxy Authentication Required';
      408 'Request Timeout';
      409 'Conflict';
      410 'Gone';
      411 'Length Required';
      412 'Precondition Failed';
      413 'Payload Too Large';
      414 'URI Too Long';
      415 'Unsupported Media Type';
      416 'Range Not Satisfiable';
      417 'Expectation Failed';
      418 'I\'m a teapot';
      421 'Misdirected Request';
      422 'Unprocessable Entity';
      423 'Locked';
      424 'Failed Dependency';
      425 'Too Early';
      426 'Upgrade Required';
      428 'Precondition Required';
      429 'Too Many Requests';
      431 'Request Header Fields Too Large';
      451 'Unavailable For Legal Reasons';
      500 'Internal Server Error';
      501 'Not Implemented';
      502 'Bad Gateway';
      503 'Service Unavailable';
      504 'Gateway Timeout';
      505 'HTTP Version Not Supported';
      506 'Variant Also Negotiates';
      507 'Insufficient Storage';
      508 'Loop Detected';
      510 'Not Extended';
      511 'Network Authentication Required';
      default 'Something is wrong';
    }
    server {
        client_max_body_size ${NGINX_MAX_BODY_SIZE};
        large_client_header_buffers 4 16k;
        access_log /dev/stdout;
        listen 80;
        proxy_cache one;
        error_page 502 503 504 /50x.html;

        location /50x.html {
          ssi on;
          internal;
          auth_basic off;
          root /var/nginx/;
        }
        location /error/502  {
            return 502;
        }
        location /error/503  {
            return 503;
        }
        location /error/504  {
            return 504;
        }
        location /favicon.ico {
            alias ${STATIC_URL}favicon/favicon.ico;
            etag off;
            if_modified_since off;
            add_header Cache-Control "public, no-transform, immutable";
            expires 1d;
         }
         location ${STATIC_URL} {
            root ${STATIC_ROOT};
            autoindex off;
            etag off;
            if_modified_since off;
            add_header Cache-Control "public, no-transform, immutable";
            expires 1y;
            gzip on;
            gzip_disable "MSIE [1-6]\.";
            gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml;
         }

        location / {
            http2_push https://browser.sentry-cdn.com/5.30.0/bundle.min.js;
            http2_push https://unpkg.com/tailwindcss@1.9.6/dist/tailwind.min.css;

            add_header X-Cache-Status ${DOLLAR}upstream_cache_status;

            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host ${DOLLAR}host;
            proxy_set_header X-Forwarded-For ${DOLLAR}proxy_add_x_forwarded_for;
            proxy_set_header X-Scheme ${DOLLAR}scheme;
        }
    }
}
