from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore, InMemoryTrackerStore
from rasa.shared.core.domain import Domain
from rasa.core.tracker_store import DialogueStateTracker
import asyncio
import requests
import pandas as pd
import psycopg2
from datetime import datetime
import yaml
import os 
from flask import Flask, jsonify, request
import json


app = Flask(__name__)
class AgentSkillFinder:
    def __init__(self):
        self.agent = Agent.load("agent/agent_bot/models")
       
    async def agent_get_response(self, user_message):
        parsed = await self.agent.parse_message(user_message)
        skill_id = parsed["intent"]["name"]
        return skill_id
    

class DelegateSkillFinder:
    def __init__(self,delegate_id):
        self.agent = Agent.load(f"delegate/{delegate_id}/models")

    async def delegate_get_response(self, user_message):
        
        parsed = await self.agent.parse_message(user_message)
        skill_id = parsed["intent"]["name"]
        return skill_id

class SkillProcessor:
    def __init__(self,skill_id,message,sender_id):
        # endpoint = EndpointConfig(url=endpoint_url)
        self.skill_id=skill_id
        self.message=message
        self.sender_id=sender_id

    def skill_processor(self):
        config_path = "input/db_config.yml"
        with open(config_path, 'r') as config_file:
            config = yaml.safe_load(config_file)

        skill_url = config['endpoints']['skill_url']

        payload = {
            "skill_id": self.skill_id,
            "message": self.message,
            "sender_id": self.sender_id
        }

        try:
            response = requests.post(skill_url, json=payload)
            response.raise_for_status()  
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
            return None


class FetchRecords:
    def __init__(self,sender_id):
        import datetime
        self.sender_id=sender_id
        # self.file_location='input/sender_skill_data.xlsx'
        self.config_path = "input/db_config.yml"
        with open(self.config_path, 'r') as config_file:
            self.config = yaml.safe_load(config_file)
        self.conn = psycopg2.connect(
            host=self.config['database']['host'],
            database=self.config['database']['database_name'],
            user=self.config['database']['username'],
            password=self.config['database']['password']
            )    

    async def fetch_conversation(self,query_type):
        try:
            import datetime
            cursor = self.conn.cursor()

            cursor.execute("SELECT current_timestamp;")

            # Fetch the result of the query
            current_timestamp = cursor.fetchone()[0]
            one_hour_ago = current_timestamp - datetime.timedelta(hours=1)
            print(one_hour_ago)
            timestamp_unix = one_hour_ago.timestamp()
            timestamp_str = '{:.10f}'.format(timestamp_unix)

            print("Unix timestamp:", query_type)
            query = self.config['query'][query_type].format(time=timestamp_str,sender=self.sender_id)
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
            return rows

        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL:", error)
             
    def store_sender_skill(self,skill_id,conversation_status):
        try:

            current_time = datetime.now()
            cursor = self.conn.cursor()
            insert_query = """
                INSERT INTO conversation_info(sender_id, skill_id, time, conversation_status)
                VALUES (%s, %s, %s, %s);
            """

            data = [
                (self.sender_id, skill_id,current_time , conversation_status),
            ]
            cursor.executemany(insert_query, data)
            self.conn.commit()
            print("Table created successfully!")
            cursor.close()
            self.conn.close()

        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL:", error)

    async def fetchData_UpdateStatus(self,skill_id):
        skill_records=FetchRecords(self.sender_id)
        sub=False
        activeStatus=True
        conv_list= await skill_records.fetch_conversation("query_data")
        print("_------------------------------------",conv_list)
        for i in range(0,len(conv_list)):
            if((json.loads(conv_list[i][3])["event"])=="active_loop"):
                activeStatus=False  
        for i in range(0,len(conv_list)):

            if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                sub=True
                break
                    
            else:
                sub=False

        if activeStatus:
            self.store_sender_skill(skill_id,"completed") 
        else:
            if(sub):
                self.store_sender_skill(skill_id,"completed")
            else:
                self.store_sender_skill(skill_id,"inprogress")
    
    async def delegate_info(self,delegate_id,skill_id):
        return_data=False
        with open('delegate/'+delegate_id+'/data/nlu.yml', 'r') as file:
            config = yaml.safe_load(file)

        for intent in config['nlu']:
            if(skill_id==intent['intent']):
                return_data= True
                break
            else:
                return_data=False
        return return_data

    async def active_delegate_fxn(self,skill_id):
        delegate_values = [f for f in os.listdir('delegate') if os.path.isdir(os.path.join('delegate', f))]
        return_active_delegate=""
        for delegate_id in delegate_values:
            print(delegate_id)
            value=await self.delegate_info(delegate_id,skill_id)
            if(value):
                return_active_delegate=delegate_id
                break
            else:
                return_active_delegate=None
        return return_active_delegate


async def main(user_message,sender_id):
# async def main():
#     user_message=input("Enter user message: ")
#     sender_id = input("Sender id: ")
    skill_records=FetchRecords(sender_id)
    conv_list= await skill_records.fetch_conversation("query_data")
    print("__________________",conv_list)
    default_delegate_id="faq_delegate"
    skill_id=""
    
    if(len(conv_list)>0):
    # if(conv_list!=None):

        # skill_status=store_and_fetch.get_latest_skill_id()
        skill_status= await skill_records.fetch_conversation("context_data")
        if(skill_status[0][3]=='inprogress'):
            skill_id=skill_status[0][1]

            skill_process=SkillProcessor(skill_id,user_message,sender_id)
            response={"Response from skill":skill_process.skill_processor(),"Current deletage":await skill_records.active_delegate_fxn(skill_id)}
            conv_list= await skill_records.fetch_conversation("query_data")
            sub=False
            for i in range(0,len(conv_list)):
                if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                    sub=True
                    break
                    
                else:
                    sub=False

            if(sub):
                skill_records.store_sender_skill(skill_id,"completed")
            else:
                skill_records.store_sender_skill(skill_id,"inprogress")
        else: #COMPLETED STATUS
            agent=AgentSkillFinder()
            skill_id=skill_status[0][1]
            active_delegate=await skill_records.active_delegate_fxn(skill_id)
            delegate=DelegateSkillFinder(active_delegate)
            skill_id=await delegate.delegate_get_response(user_message)
            if(skill_id=="nlu_fallback"):
                
                agent_skill_id=await agent.agent_get_response(user_message)
                print("delegate_id",agent_skill_id)
                if(agent_skill_id=="nlu_fallback"):
                    response={"Response":"No Skill, Could you please rephrase your query","Current deletage":default_delegate_id}

                else:
                    skill_process=SkillProcessor(agent_skill_id,user_message,sender_id)
                    response={"Response from skill":skill_process.skill_processor(),"Current deletage":await skill_records.active_delegate_fxn(agent_skill_id)}
                    print(response)
                    await skill_records.fetchData_UpdateStatus(agent_skill_id)
            else:
                skill_process=SkillProcessor(skill_id,user_message,sender_id)
                response={"Response from skill":skill_process.skill_processor(),"Current deletage":await skill_records.active_delegate_fxn(skill_id)}
                
                await skill_records.fetchData_UpdateStatus(skill_id)
            
    else:       #When first message arrives
        agent=AgentSkillFinder()
        delegate=DelegateSkillFinder(default_delegate_id)
        skill_id=await delegate.delegate_get_response(user_message)
        print(skill_id)
        
        if(skill_id=="nlu_fallback"):
            
            agent_skill_id=await agent.agent_get_response(user_message)
            if(agent_skill_id=="nlu_fallback"):
                response={"Response":"No Skill, Could you please rephrase your query","Current deletage":default_delegate_id}
                print("delegate_id",agent_skill_id)
            else:
                skill_process=SkillProcessor(agent_skill_id,user_message,sender_id)
                response={"Response from skill":skill_process.skill_processor(),"Current deletage":await skill_records.active_delegate_fxn(agent_skill_id)}
                print(response)
                await skill_records.fetchData_UpdateStatus(agent_skill_id)
            

        else:
            skill_process=SkillProcessor(skill_id,user_message,sender_id)
            response={"Response from skill":skill_process.skill_processor(),"Current deletage":default_delegate_id}

            print(response)

            await skill_records.fetchData_UpdateStatus(skill_id)
           

    return response   

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data['message']
    sender_id = data['sender_id']
    response=asyncio.run(main(user_message,sender_id))
    
    return response
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5008)

# response=asyncio.run(main())       
    


