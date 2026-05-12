import loadmaps as lm
import json
import datetime

MAP_REQUESTS = []

# Queue for map requests that have been accepted but not yet processed
MAP_REQUESTS_APPROVED_QUEUE = []

class MapRequest:
    def __init__(self, beatmap_id: int, user_id: int, status: str = "pending", time_submitted: datetime.datetime = None):
        self.beatmap_id = beatmap_id
        self.user_id = user_id
        self.status = status  # pending, approved, rejected
        self.beatmap = None  # This will hold the beatmap data once it's fetched
        
        if time_submitted is None:
            self.time_submitted = datetime.datetime.now()
        else:
            self.time_submitted = time_submitted
        
    def to_dict(self):
        return {
            "beatmap_id": self.beatmap_id,
            "user_id": self.user_id,
            "status": self.status,
            "time_submitted": self.time_submitted.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        return MapRequest(
            beatmap_id=data["beatmap_id"],
            user_id=data["user_id"],
            status=data.get("status", "pending"),
            time_submitted=datetime.datetime.fromisoformat(data["time_submitted"])
        )
    
    async def fetch_beatmap_data(self):
        self.beatmap = await lm.load_beatmapset(self.beatmap_id)
        
        return self.beatmap
        
def save_map_requests():
    global MAP_REQUESTS
    
    with open("json/map_requests.json", "w") as file:
        json.dump([request.to_dict() for request in MAP_REQUESTS], file)
        
    with open("json/approved_map_requests.json", "w") as file:
        json.dump([request.to_dict() for request in MAP_REQUESTS_APPROVED_QUEUE], file)
        
async def load_map_requests():
    global MAP_REQUESTS
    
    if len(MAP_REQUESTS) > 0:
        return MAP_REQUESTS
    
    try:
        with open("json/map_requests.json", "r") as file:
            data = json.load(file)
            MAP_REQUESTS = [MapRequest.from_dict(item) for item in data]
            
            for request in MAP_REQUESTS:
                await request.fetch_beatmap_data()
    except FileNotFoundError:
        MAP_REQUESTS = []
        
    return MAP_REQUESTS

async def clear_approved_map_requests():
    global MAP_REQUESTS_APPROVED_QUEUE
    
    MAP_REQUESTS_APPROVED_QUEUE = []
    
    save_map_requests()

async def load_approved_map_requests():
    global MAP_REQUESTS_APPROVED_QUEUE
    
    print(MAP_REQUESTS_APPROVED_QUEUE)
    
    if len(MAP_REQUESTS_APPROVED_QUEUE) > 0:
        return MAP_REQUESTS_APPROVED_QUEUE
    
    try:
        with open("json/approved_map_requests.json", "r") as file:
            data = json.load(file)
            
            print(data)
            MAP_REQUESTS_APPROVED_QUEUE = [MapRequest.from_dict(item) for item in data]
            
            for request in MAP_REQUESTS_APPROVED_QUEUE:
                await request.fetch_beatmap_data()
    except FileNotFoundError:
        MAP_REQUESTS_APPROVED_QUEUE = []
    
    print(MAP_REQUESTS_APPROVED_QUEUE)
    return MAP_REQUESTS_APPROVED_QUEUE

def get_request_queue_position(request: MapRequest):
    global MAP_REQUESTS
    
    pending_requests = [req for req in MAP_REQUESTS if req.status == "pending"]
    pending_requests.sort(key=lambda r: r.time_submitted)
    
    for index, req in enumerate(pending_requests):
        if req.beatmap_id == request.beatmap_id and req.user_id == request.user_id:
            return index + 1  # Position in queue (1-based index)
    
    return None

async def update_status(beatmap_id: int, new_status: str):
    global MAP_REQUESTS
    
    for request in MAP_REQUESTS:
        if request.beatmap_id == beatmap_id:
            request.status = new_status
            break
            
    save_map_requests()
    
async def add_to_approved_queue(request: MapRequest):
    global MAP_REQUESTS_APPROVED_QUEUE
    
    if request.status == "approved":
        MAP_REQUESTS_APPROVED_QUEUE.append(request)
        save_map_requests()
        
async def get_approved_queue():
    global MAP_REQUESTS_APPROVED_QUEUE
    
    return MAP_REQUESTS_APPROVED_QUEUE

async def clear_approved_queue():
    global MAP_REQUESTS_APPROVED_QUEUE
    
    MAP_REQUESTS_APPROVED_QUEUE = []
    save_map_requests()
    
async def approve_request(request: MapRequest):
    await update_status(request.beatmap_id, "approved")
    await add_to_approved_queue(request)
    await remove_map_request(request)
    
async def reject_request(request: MapRequest):
    await remove_map_request(request)    
    
async def clear_map_requests(status: str = None):
    global MAP_REQUESTS
    
    if status:
        MAP_REQUESTS = [request for request in MAP_REQUESTS if request.status != status]
    else:
        MAP_REQUESTS = []
        
    save_map_requests()
    
async def get_requests_by_status(status: str):
    global MAP_REQUESTS
    
    return [request for request in MAP_REQUESTS if request.status == status]

async def get_requests_by_user(user_id: int):
    global MAP_REQUESTS
    
    return [request for request in MAP_REQUESTS if request.user_id == user_id]

async def get_request_by_beatmap(beatmap_id: int):
    global MAP_REQUESTS
    
    for request in MAP_REQUESTS:
        if request.beatmap_id == beatmap_id:
            return request
            
    return None

async def can_request_beatmap(beatmap_id: int):
    global MAP_REQUESTS
    
    can_request = True
    message = ""
    
    for request in MAP_REQUESTS:
        if request.beatmap_id == beatmap_id and request.status == "pending":
            can_request = False
            message = "This beatmap is already pending approval."
            break
        
    # Cannot Request if already in the database
    if str(beatmap_id) in lm.maps.maps_json:
        can_request = False
        message = "This beatmap is already in the database."
            
    map = await lm.api.get_beatmapset(beatmap_id)
    
    # Cannot Request Ranked, Loved maps
    if map.status in [1, 4]:
        can_request = False
        message = "This beatmap is already ranked or loved."
        
    return can_request, message

async def add_map_request(request: MapRequest):
    global MAP_REQUESTS
    
    MAP_REQUESTS.append(request)
    
    save_map_requests()
    
    return request

async def remove_map_request(request: MapRequest):
    global MAP_REQUESTS
    
    MAP_REQUESTS = [req for req in MAP_REQUESTS if not (req.beatmap_id == request.beatmap_id and req.user_id == request.user_id)]
    
    save_map_requests()
    
    return request