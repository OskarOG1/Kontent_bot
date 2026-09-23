FROM aiogram/telegram-bot-api:10.3

RUN deluser telegram-bot-api 2>/dev/null; delgroup telegram-bot-api 2>/dev/null; \
    addgroup -g 1000 -S telegram-bot-api \
 && adduser -S -D -H -u 1000 -h /var/lib/telegram-bot-api -s /sbin/nologin -G telegram-bot-api -g telegram-bot-api telegram-bot-api \
 && chown -R telegram-bot-api:telegram-bot-api /var/lib/telegram-bot-api /tmp/telegram-bot-api
