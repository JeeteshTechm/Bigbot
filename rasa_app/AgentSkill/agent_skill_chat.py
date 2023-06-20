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

class FetchRecords:
    def __init__(self,sender_id):
        self.sender_id=sender_id
    
    async def fetch_conversation(self):
        import datetime
        conn = psycopg2.connect(
        host="127.0.0.1",
        database="rasadb",
        user="rasa",
        password="rasa123"
        )
        cursor = conn.cursor()

        # Execute the SQL query to get the current timestamp
        cursor.execute("SELECT current_timestamp;")

        # Fetch the result of the query
        current_timestamp = cursor.fetchone()[0]
        one_hour_ago = current_timestamp - datetime.timedelta(hours=1)
        print(one_hour_ago)
        timestamp_unix = one_hour_ago.timestamp()
        timestamp_str = '{:.10f}'.format(timestamp_unix)

        print("Unix timestamp:", timestamp_str)

        query = "SELECT sender_id,intent_name, action_name, data FROM events WHERE timestamp >= {time} AND sender_id='{sender}' order by id DESC LIMIT 10;".format(time=timestamp_str,sender=self.sender_id)
        cursor.execute(query)
        rows = cursor.fetchall()
        print(rows)
        # print(rows[0])
        # print("Current timestamp:", current_timestamp)
        cursor.close()
        conn.close()
        return rows


class SkillFinder:
    def __init__(self):
        self.agent = Agent.load("agent/agent_bot/models")
       
    async def get_response(self, user_message):
        parsed = await self.agent.parse_message(user_message)
        skill_id = parsed["intent"]["name"]
        return skill_id

# class SkillFinder:
#     def __init__(self,delegate_id):
#         self.agent = Agent.load(f"delegate/{delegate_id}/models")

#     async def get_response(self, user_message):
#         parsed = await self.agent.parse_message(user_message)
#         skill_id = parsed["intent"]["name"]
#         return skill_id

class SkillProcessor:
    def __init__(self,skill_id,message,sender_id):
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
            # skillData={"skill_identified":self.skill_id}
            # return data + skillData
            data["skill_id"]=self.skill_id
            return data
        except requests.exceptions.RequestException as e:
            print("An error occurred:", e)
            return None

class SkillStoreandFetch:
    def __init__(self,sender_id):
        self.sender_id=sender_id
        self.file_location='input/sender_skill_data.xlsx'

    def store_sender_skill(self,skill_id,conversation_status):
        if not os.path.isfile(self.file_location):
            df = pd.DataFrame(columns=['sender_id', 'skill_id', 'time','conversation_status'])
            df.to_excel(self.file_location, index=False)
        df = pd.read_excel(self.file_location)
        current_time = datetime.now()
        new_row = pd.DataFrame({'sender_id': [self.sender_id], 'skill_id': [skill_id], 'time': [current_time],'conversation_status':[conversation_status]})
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.file_location, index=False)
        print(f"Data saved to {self.file_location} successfully.")

    def get_latest_skill_id(self):
        if not os.path.isfile(self.file_location):
            df = pd.DataFrame(columns=['sender_id', 'skill_id', 'time','conversation_status'])
            df.to_excel(self.file_location, index=False)

        df = pd.read_excel(self.file_location)
        sender_rows = df[df['sender_id'] == self.sender_id]
        if sender_rows.empty:
            return None

        sorted_rows = sender_rows.sort_values(by='time', ascending=False)
        latest_skill_id = sorted_rows.iloc[0]['skill_id']
        latest_status=sorted_rows.iloc[0]['conversation_status']
        data={'skill':latest_skill_id,'status':latest_status}
        print("LATESTE  SKILL DATA AND STATUS",data)
        return data


async def main(user_message,sender_id):

    skill_records=FetchRecords(sender_id)
    conv_list= await skill_records.fetch_conversation()
    print("........................................................")
    print(conv_list)

    store_and_fetch=SkillStoreandFetch(sender_id) 
    skill_id=""
    
    if(len(conv_list)>0):

        skill_status=store_and_fetch.get_latest_skill_id()
        print("LINE 131 ******",skill_status)
        if(skill_status['status']=='inprogress'):
            skill_id=skill_status['skill']
            skill_process=SkillProcessor(skill_id,user_message,sender_id)
            response=skill_process.skill_processor()
            print("LINE 137 CONV CONTINUE**********",response)
            conv_list= await skill_records.fetch_conversation()
            sub=False
            for i in range(0,len(conv_list)):
                if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                    sub=True
                    print("INSIDE 143 SUBMIT****")
                    break
                    
                else:
                    sub=False
                    print("LINE 146 *******ELSE OF SUBMIT")

            if(sub):
                store_and_fetch.store_sender_skill(skill_id,"completed")
                #sk.store_sender_skill(sender_id,skill_id,"completed")
            else:
                store_and_fetch.store_sender_skill(skill_id,"inprogress")
                #sk.store_sender_skill(sender_id,skill_id,"inprogress")
                print("LINE 152 NO SUBMIT*****")
        # elif(skill_status['status']=='completed'):
        else:
            agent=SkillFinder()
            skill_id=await agent.get_response(user_message)
            print("else loop ....")
            # delegate=SkillFinder(delegate_id)
            # skill_id=await delegate.get_response(user_message)

            skill_process=SkillProcessor(skill_id,user_message,sender_id)
            response=skill_process.skill_processor()
            print(response)

            # store_and_fetch.store_sender_skill(skill_id,"inprogress")
            print("inprogress")
            sub=False
            activeStatus=True
            conv_list= await skill_records.fetch_conversation()
            for i in range(0,len(conv_list)):
                if((json.loads(conv_list[i][3])["event"])=="active_loop"):
                    activeStatus=False  
            for i in range(0,len(conv_list)):

                if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                    sub=True
                    print("INSIDE 210 SUBMIT****")
                    break
                    
                else:
                    sub=False
                    print("LINE 215 *******ELSE OF SUBMIT")

            if activeStatus:
                store_and_fetch.store_sender_skill(skill_id,"completed") 
            else:
                if(sub):
                    store_and_fetch.store_sender_skill(skill_id,"completed")
                else:
                    store_and_fetch.store_sender_skill(skill_id,"inprogress")
    else:
        agent=SkillFinder()
        skill_id=await agent.get_response(user_message)

        # delegate=SkillFinder(delegate_id)
        # skill_id=await delegate.get_response(user_message)
        # print(skill_id)
        skill_process=SkillProcessor(skill_id,user_message,sender_id)
        response=skill_process.skill_processor()
        print(response)

        # store_and_fetch.store_sender_skill(skill_id,"inprogress")
        print("inprogress")
        sub=False
        activeStatus=True
        conv_list= await skill_records.fetch_conversation()
        for i in range(0,len(conv_list)):
          if((json.loads(conv_list[i][3])["event"])=="active_loop"):
              activeStatus=False  
        for i in range(0,len(conv_list)):

                if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                    sub=True
                    print("INSIDE 210 SUBMIT****")
                    break
                    
                else:
                    sub=False
                    print("LINE 215 *******ELSE OF SUBMIT")

        if activeStatus:
           store_and_fetch.store_sender_skill(skill_id,"completed") 
        else:
            if(sub):
                store_and_fetch.store_sender_skill(skill_id,"completed")
            else:
                store_and_fetch.store_sender_skill(skill_id,"inprogress")

    return response   

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data['message']
    sender_id = data['sender_id']
    response=asyncio.run(main(user_message,sender_id))
    
    return response
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5007)

        
    


