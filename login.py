import json

async def login(id):
    userdata = None

    json_object = None

    file = open("users.json", "r")
    json_object = json.load(file)
    file.close()

    try:
        userdata = json_object[str(id)]
    except:
        # notes
        # 0 - currency (pp)
        # 1 - maps
        # 2 - level 
        # 3 - xp
        # 4 - inventory (mappers, potions, buffs)
        json_object[str(id)] = ["0", [], "0", "0", []]
        file = open("users.json", "w")
        json.dump(json_object, file)
        file.close()

    file = open("users.json", "r")
    json_object = json.load(file)
    file.close()
    return json_object[str(id)]

async def replaceuserdata(id, userdata):
    file2 = open("users.json", "r")
    json_data = json.load(file2)
    json_data[str(id)] = userdata
    file2.close()
    file = open("users.json", "w")
    json.dump(json_data, file)
    file.close()