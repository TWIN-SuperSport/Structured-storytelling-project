FROM php:8.4-fpm-alpine

RUN apk add --no-cache bash git unzip

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/entrypoint.sh"]
