from src.bot.telegram_bot import setup_bot
from src.api.webhook import set_webhook
import os

if __name__ == '__main__':
    bot = setup_bot()
    # Use your EC2 public DNS or Elastic IP
    ec2_public_dns = "http://ec2-xx-xx-xx-xx.compute-1.amazonaws.com"
    set_webhook(ec2_public_dns)
    print("Webhook set. Bot is ready.")