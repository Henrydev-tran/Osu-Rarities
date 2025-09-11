import json, aiofiles
from user import User, Dict_To_User
from jsontools import *
import copy

stored_users = None

with open("json/users.json", "r") as file:
    contents = file.read()
    stored_users = json.loads(contents)

# Returns a User object using a user's discord id. will create a new user in the database if not already created.
async def login(id):
    global stored_users
    
    strid = str(id)
    
    userdata = None
    
    try:
        userdata = stored_users[strid]
    except:
        new_user = await User(id)
        stored_users[strid] = await User_To_Dict(new_user)
        
        await write_stored_variable()
        
        return new_user
        
    return await Dict_To_User(userdata)

async def clear_userdata_all():
    async with aiofiles.open("json/users.json", "w") as file:
        await file.write("{}")
    
async def write_stored_variable():
    global stored_users
    
    await save_to_json("json/users.json", stored_users)
    
async def clear_userdata(id):
    global stored_users
    
    stored_users[str(id)] = await User_To_Dict(User(id))
    
    await write_stored_variable()

# Update the stored_users variable
async def update_stored_variables():
    global stored_users
    
    stored_users = await return_json("json/users.json")
    
# Change the value of the stored_users variable
async def update_stored_users(new): 
    global stored_users
    
    stored_users = copy.deepcopy(new)

# Update user data in database using a User object
async def update_user(user):
    global stored_users

    stored_users[str(id)] = await User_To_Dict(user)
    
    