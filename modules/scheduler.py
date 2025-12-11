# Simple scheduler: records pickup requests to DB and returns a schedule stub
from . import db
import uuid

def create_pickup(household,address,collector,material,weight,photo_path=None):
    db.add_request(household,address,material,weight)
    return {'pickup_id':str(uuid.uuid4()), 'status':'SCHEDULED', 'collector':collector}
