import json
import yaml
import asyncio
class NluCreate:
    async def readJson():
        with open('payload3.json', 'r') as f:
            data = json.load(f)
        new_data = {"nlu":{},'version': '3.1'}
        for intent in data['intents']:
            new_data["nlu"][intent['name']] = {'examples': intent['utterances']}
        return new_data
    
    async def createNlu():
       
        jsonData=  await asyncio.readJson()
        yaml_data = yaml.dump(jsonData)
        with open('nlu.yml', 'w') as yaml_file:
            yaml_file.write(yaml_data)
        return "success"


instance=NluCreate()
asyncio.run(instance.createNlu())
