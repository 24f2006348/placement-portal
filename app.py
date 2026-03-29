from flask import Flask, render_template, request, redirect, url_for, session   
#render_template:load html file from /templates from you Proj folder
#request:inputs data from browser
#redirect: to send user to different links
#url_for:generated a url from a fns
#session:a dict that rememebrs data throught a session
import os
from models import init_db, get_db  
#fns to connect to database but wont run cuz of __self__=__main__ contition not satisfied during import
# we calling init_db so that everytime we run app.py, models.py will automatically run


# note:
# Flask(__name__) creates the flask app
# __name__ tells flask where to look for templates/ and static/ folders
# secret_key is required for session to work
# session is like a dictionary flask stores on the browser (encrypted)
# it remembers who is logged in between requests
# os.urandom(24) generates a random secret key — fine for development

app = Flask(__name__)
app.secret_key = os.urandom(24)

# note:
# @app.route("/") means "when someone visits localhost:5000/ run this function"
# for now we just return a simple string to confirm flask is running
# we will replace this with a proper redirect to login page tomorrow

@app.route("/")  
def index():
    return "Flask is running! Placement Portal coming soon."
'''
when @ mentioned, it run the following function when run on localhost example:
@app.route("/login")      # localhost:5000/login
@app.route("/dashboard")  # localhost:5000/dashboard
@app.route("/apply")      # localhost:5000/apply
'''
# note:
# init_db() is called here so that every time we run app.py
# the database tables are created if they don't exist yet
# and admin is seeded if not already there
# this way we never need to run models.py separately again

if __name__ == "__main__":
    init_db()
    app.run(debug=True)