import json
from user import User
from jsontools import User_To_Dict

stored_users = None

file = open("json/users.json", "r")
stored_users = json.load(file)
file.close()

# Returns a User object using a user's discord id. will create a new user in the database if not already created.
async def login(id):
    global stored_users
    
    strid = str(id)
    
    userdata = None
    
    try:
        userdata = stored_users[strid]
    except:
        new_user = User(id)
        stored_users[strid] = await User_To_Dict(new_user)
        
        await write_stored_variable()
        
        return new_user
        
    return userdata

async def clear_userdata_all():
    file = open("json/users.json", "w")
    file.write("{}")
    file.close()
    
async def write_stored_variable():
    global stored_users
    
    file = open("json/users.json", "w")
    json.dump(stored_users, file)
    file.close()
    
async def clear_userdata(id):
    global stored_users
    
    stored_users[str(id)] = await User_To_Dict(User(id))
    
    await write_stored_variable()

# Update the stored_users variable
async def update_stored_variables():
    global stored_users
    
    file = open("json/users.json", "r")
    stored_users = json.load(file)
    file.close()

# Update user data in database using a User object
async def update_user(user):
    global stored_users

    stored_users[str(id)] = User_To_Dict(user)
    