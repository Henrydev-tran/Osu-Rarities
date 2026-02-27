import asyncio, aiofiles
from userutils import User, UserPool
from jsontools import *
import copy

stored_users = UserPool()
stored_users_lock = asyncio.Lock()

# Returns a User object using a user's discord id. will create a new user in the database if not already created.
async def login(id):
    global stored_users
    
    strid = str(id)
    
    userdata = None
    
    try:
        userdata = stored_users.users[strid]
    except:
        new_user = User(id)
        await stored_users.update_user(id, new_user)
        
        await write_stored_variable()
        
        return new_user
        
    return userdata

async def clear_userdata_all():
    async with aiofiles.open("json/users.json", "w") as file:
        await file.write("{}")
        
    await stored_users.clear_all()
    
async def write_stored_variable():
    global stored_users
    async with stored_users_lock:
        await stored_users.save_to("json/users.json")
    
async def clear_userdata(id):
    global stored_users
    async with stored_users_lock:
        await stored_users.update_user(id, User(id))
        await write_stored_variable()

# Update the stored_users variable
async def update_stored_variables():
    global stored_users
    await stored_users.load_from("json/users.json")

async def init_user_handling():
    """Initialize user handling state (call once at startup)."""
    await update_stored_variables()
    
# Change the value of the stored_users variable
async def update_stored_users(new): 
    global stored_users
    
    stored_users = copy.deepcopy(new)

# Update user data in database using a User object
async def update_user(user):
    global stored_users

    await stored_users.update_user(user.id, user)
    
# DO NOT run initialization at import time. Call `init_user_handling()` from startup.