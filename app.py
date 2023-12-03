#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, make_response, flash, session
from markupsafe import escape
import pymongo
import datetime
from bson.objectid import ObjectId
import os
import subprocess


from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

g_username=""

# instantiate the app
app = Flask(__name__)

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
import credentials
config = credentials.get()

# turn on debugging if in development mode
if config['FLASK_ENV'] == 'development':
    # turn on debugging, if in development
    app.debug = True # debug mnode

# make one persistent connection to the database
connection = pymongo.MongoClient(config['MONGO_HOST'], 27017, 
                                username=config['MONGO_USER'],
                                password=config['MONGO_PASSWORD'],
                                authSource=config['MONGO_DBNAME'])
db = connection[config['MONGO_DBNAME']] # store a reference to the database
users = connection[config['MONGO_DBNAME']]['users'] # store a reference to the users collection
# set up the routes

app.secret_key = 'your_secret_key'

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if not is_logged_in() and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))

def is_logged_in():
    return 'username' in session
 


@app.route('/')
def home():
    """
    Route for the home page
    """
    return render_template('index.html')


@app.route('/read')
def read():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    docs = db.exampleapp.find({}).sort("created_at", -1) # sort in descending order of created_at timestamp
    return render_template('read.html', docs=docs) # render the read template



@app.route('/create')
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template('create.html') # render the create template


@app.route('/create', methods=['POST'])
def create_post():
    """
    Route for POST requests to the create page.
    Accepts the form submission data for a new document and saves the document to the database.
    """
    #name = request.form['fname']
    message = request.form['fmessage']
    


    doc = {
    "name": session['username'],
    "message": message, 
    "love": 0,
    "created_at": datetime.datetime.utcnow()
    }
    db.exampleapp.insert_one(doc)


    return redirect(url_for('read')) # tell the browser to make a request for the /read route


#login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username  # 记录用户到 session
            global g_username 
            g_username=username
            return redirect(url_for('read'))
        elif not user:
            flash('User not found')
            return redirect(url_for('register'))
        else:
            flash('Wrong password')
            return redirect(url_for('login'))
    else:
        return render_template('login.html')
        

#register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)
        users.insert_one({'username': username, 'password': password_hash})
        return redirect(url_for('login'))  # 注册后重定向到登录页面
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/edit/<mongoid>')
# def edit(mongoid):
#     """
#     Route for GET requests to the edit page.
#     Displays a form users can fill out to edit an existing record.
#     """
    
#     # global g_username #如果帖子的id和用户名不一致，就不能编辑
#     # # if doc and doc.get("username") == g.get("username"):
#     doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
#     # return render_template('edit.html', mongoid=mongoid, doc=doc) # render the edit template
#     if doc.get("username") == session['username']:
#         return render_template('edit.html', mongoid=mongoid, doc=doc)
#     else:
#         flash('You are not authorized to edit this post.')
#         return redirect(url_for('read'))
    
@app.route('/edit/<mongoid>')
def edit(mongoid):
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    if 'username' in session and doc.get("name") == session['username']:
        return render_template('edit.html', mongoid=mongoid, doc=doc)
    else:
        #flash('You are not authorized to edit this post.')
        return redirect(url_for('read'))


@app.route('/edit/<mongoid>', methods=['POST'])
def edit_post(mongoid):
    """
    Route for POST requests to the edit page.
    Accepts the form submission data for the specified document and updates the document in the database.
    """
    # global g_username
    
    name = request.form['fname']
    message = request.form['fmessage']

    doc = {
        # "_id": ObjectId(mongoid), 
        "name": name, 
        "message": message, 
        "created_at": datetime.datetime.utcnow()
    }
    # if name != g_username:
    #     flash('You can only edit your own message!')
    #     return redirect(url_for('read'))
    
    db.exampleapp.update_one(
        {"_id": ObjectId(mongoid)}, # match criteria
        { "$set": doc }
    )

    return redirect(url_for('read')) # tell the browser to make a request for the /read route

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        docs = db.exampleapp.find({"$or": [{"name": {"$regex": query}}, {"message": {"$regex": query}}]}).sort("created_at", -1)
        return render_template('search.html', docs=docs)
    return redirect(url_for('read'))

# @app.route('/delete/<mongoid>')
# def delete(mongoid):
#     """
#     Route for GET requests to the delete page.
#     Deletes the specified record from the database, and then redirects the browser to the read page.
#     """
#     db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
#     return redirect(url_for('read')) # tell the web browser to make a request for the /read route.
@app.route('/delete/<mongoid>')
def delete(mongoid):
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    if 'username' in session and doc.get("name") == session['username']:
        db.exampleapp.delete_one({"_id": ObjectId(mongoid)})
        return redirect(url_for('read'))
    else:
        flash('You are not authorized to delete this post.')
        return redirect(url_for('read'))


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response('output: {}'.format(pull_output), 200)
    response.mimetype = "text/plain"
    return response
    
@app.route('/love/<mongoid>')
def love(mongoid):
    doc = db.exampleapp.find_one({"_id": ObjectId(mongoid)})
    num = doc['love'] + 1
     
    docc = { 
        "love": num 
    }

    db.exampleapp.update_one(
        {"_id": ObjectId(mongoid)}, 
        { "$set": docc }
    )
    return redirect(url_for('read')) 

@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template('error.html', error=e) # render the edit template


if __name__ == "__main__":
    #import logging
    #logging.basicConfig(filename='/home/ak8257/error.log',level=logging.DEBUG)
    app.run(debug = True)
