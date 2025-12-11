# Simple token accounting stored in memory/file (prototype)
import json, os
STORE='tokens.json'
if not os.path.exists(STORE):
    json.dump({}, open(STORE,'w'))

def award_tokens(household, material, weight):
    data=json.load(open(STORE))
    tokens=int(weight*10)  # 10 token/kg example
    data[household]=data.get(household,0)+tokens
    json.dump(data, open(STORE,'w'))
    return tokens

def get_balance(household):
    data=json.load(open(STORE))
    return data.get(household,0)
