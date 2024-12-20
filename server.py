# server.py
import os
from flask import Flask
from threading import Thread
from bot import main

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

@app.route('/_ah/warmup')
def warmup():
    return '', 200

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    server = Thread(target=run)
    server.daemon = True
    server.start()

if __name__ == "__main__":
    # Start the Flask server in a separate thread
    keep_alive()
    # Run the bot
    main()