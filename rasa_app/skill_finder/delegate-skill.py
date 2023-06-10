from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
from rasa.core.tracker_store import SQLTrackerStore,InMemoryTrackerStore
from rasa.shared.core.domain import Domain
from rasa.core.tracker_store import DialogueStateTracker
import asyncio
import psycopg2
import json
from datetime import datetime
import pandas as pd
import os

endpoint_url = "http://37.224.68.171:5007/webhook"
class skillFinder:
    async def get_response(self, user_message):
        agent=Agent.load("Skill_finder/models")
        parsed = await agent.parse_message(user_message)
        print("________SKILL FINDER___________",parsed)
        skill_id=parsed["intent"]["name"]
        return skill_id
    async def fetch_conversation(self, sender_id):
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

        query = "SELECT sender_id,intent_name, action_name, data FROM events WHERE timestamp >= {time} AND sender_id='{sender}' order by id DESC LIMIT 10;".format(time=timestamp_str,sender=sender_id)
        cursor.execute(query)
        rows = cursor.fetchall()
        # print(rows)
        # print(rows[0])
        # print("Current timestamp:", current_timestamp)
        cursor.close()
        conn.close()
        return rows
    
    def store_sender_skill(self,sender_id, skill_id,conversation_status):

        excel_file = 'input/sender_skill_data.xlsx'

        if not os.path.isfile(excel_file):

            df = pd.DataFrame(columns=['sender_id', 'skill_id', 'time','conversation_status'])

            df.to_excel(excel_file, index=False)

        df = pd.read_excel(excel_file)

        current_time = datetime.now()
        new_row = pd.DataFrame({'sender_id': [sender_id], 'skill_id': [skill_id], 'time': [current_time],'conversation_status':[conversation_status]})

        df = pd.concat([df, new_row], ignore_index=True)

        df.to_excel(excel_file, index=False)
        print(f"Data saved to {excel_file} successfully.")

    def get_latest_skill_id(self,sender_id):

        df = pd.read_excel('input/sender_skill_data.xlsx')

        sender_rows = df[df['sender_id'] == sender_id]

        if sender_rows.empty:

            return None

        sorted_rows = sender_rows.sort_values(by='time', ascending=False)

        latest_skill_id = sorted_rows.iloc[0]['skill_id']
        latest_status=sorted_rows.iloc[0]['conversation_status']
        data={'skill':latest_skill_id,'status':latest_status}
        print("LATESTE  SKILL DATA AND STATUS",data)
        return data


class Bot:
    def __init__(self, model_path, endpoint_url, domain,sender_id):
        endpoint = EndpointConfig(url=endpoint_url)
        tracker_store = SQLTrackerStore(
                dialect="postgresql",
                host="127.0.0.1",
                port="5432",
                username="rasa",
                password="rasa123",
                db="rasadb"
                )
        #tracker_store = InMemoryTrackerStore(max_event_history=10, domain=domain,sender_id=sender_id)
        self.agent = Agent.load(model_path, action_endpoint=endpoint, tracker_store=tracker_store, domain=domain)

    async def get_conv(self, user_message, sender_id):
        parsed = await self.agent.parse_message(user_message)
        response = await self.agent.handle_text(user_message,sender_id=sender_id)
        # print("____________________",response)
        # print("-------------------",parsed)
        result = {'text': response, 'intent': parsed}
       
    
        return result
    
    



async def main():
    
    user_message=input("Enter user message: ")
    sender_id = input("Sender id: ")
    sk=skillFinder()
    conv_list= await sk.fetch_conversation(sender_id)
    skill_id=""
    sub=False
    if(len(conv_list)>0):

        skill_status=sk.get_latest_skill_id(sender_id)
        print("LINE 131 ******",skill_status)
        if(skill_status['status']=='inprogress'):
            skill_id=skill_status['skill']
            domain = Domain.load(skill_id+"/domain.yml")
            bot = Bot(skill_id+"/models", endpoint_url, domain,sender_id)
            response = await bot.get_conv(user_message, sender_id)
            print("LINE 137 CONV CONTINUE**********",response)
            conv_list= await sk.fetch_conversation(sender_id)
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
                sk.store_sender_skill(sender_id,skill_id,"completed")
            else:
                sk.store_sender_skill(sender_id,skill_id,"inprogress")
                print("LINE 152 NO SUBMIT*****")
        # elif(skill_status['status']=='completed'):
        else:
            
            skill_id=await sk.get_response(user_message)
            print("LINE 155 SKILL COMPLETED STATUS******",skill_id)
            domain = Domain.load(skill_id+"/domain.yml")
            bot = Bot(skill_id+"/models", endpoint_url, domain,sender_id)
            response = await bot.get_conv(user_message, sender_id)
            print("*********************NEW SKILL AFTER COMPLETION  ",response)

            # sk.store_sender_skill(sender_id,skill_id,"inprogress")
            sub=False
            activeStatus=True
            conv_list= await sk.fetch_conversation(sender_id)
            for i in range(0,10):
                if((json.loads(conv_list[i][3])["event"])=="active_loop"):
                    activeStatus=False
                    break  
            for i in range(0,len(conv_list)):

                if(conv_list[i][2] is not None and ("submit_" in conv_list[i][2]) and ("_form" in conv_list[i][2])):
                    sub=True
                    print("INSIDE 143 SUBMIT****")
                    break
                    
                else:
                    sub=False
                    print("LINE 146 *******ELSE OF SUBMIT")

            if activeStatus:
                sk.store_sender_skill(sender_id,skill_id,"completed") 
            else:
                # sk.store_sender_skill(sender_id,skill_id,"inprogress")
                if(sub):
                    sk.store_sender_skill(sender_id,skill_id,"completed")
                else:
                    sk.store_sender_skill(sender_id,skill_id,"inprogress")
                print("LINE 188 FIRST CONV AND SUBMIT*****")
    else:
        print("LINE 193")
        skill_id= await sk.get_response(user_message)
        # sk.store_sender_skill(sender_id,skill_id,"inprogress")
        domain = Domain.load(skill_id+"/domain.yml")
        bot = Bot(skill_id+"/models", endpoint_url, domain,sender_id)
        response = await bot.get_conv(user_message, sender_id)
        print("*********************NO SENDER ID ",response)
        sub=False
        activeStatus=True
        conv_list= await sk.fetch_conversation(sender_id)
        for i in range(0,10):
          if((json.loads(conv_list[i][3])["event"])!="active_loop"):
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
           sk.store_sender_skill(sender_id,skill_id,"completed") 
        else:
            if(sub):
                sk.store_sender_skill(sender_id,skill_id,"completed")
            else:
                sk.store_sender_skill(sender_id,skill_id,"inprogress")
                # print("LINE 188 FIRST CONV AND SUBMIT*****")
    
asyncio.run(main())
