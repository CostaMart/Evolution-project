
from langchain import hub
from langchain.agents import AgentExecutor, create_react_agent
from langchain_groq import ChatGroq
from langchain.tools import tool
import os
import pandas
from icecream import ic
import re

logs = pandas.read_csv("pod_logs_3.csv")


counter_em = None
counter_api= None
coutner_admission = None
counter_wait = None

def gen_emergency_service_logs():
    dimensione_blocco = 15
    global logs
    columns = logs.columns
    column = [column for column in columns if "emergency-service" in column]
    column = column[0]
    logz= str(logs[column][0]).split("\n")
    for i in range(1, len(logz)):
        yield logz[-i*(dimensione_blocco):-((i+1)*dimensione_blocco):-1]  #scorre la lista di 15 elementi in dietro ad ogni invocazione


@tool
def check_emergency_service(input:str = "value") -> str:
  "get emergency service logs as plain text, each time you call this function you get the previous 15 lines of log"
  global counter_em
  if counter_em == None :
     counter_em = gen_emergency_service_logs()
  try:
     value = next(counter_em)
  except:
     return "log is over"
  return str (value)


def gen_api_gateway_logs():
    dimensione_blocco = 15
    global logs
    columns = logs.columns
    column = [column for column in columns if "api-gateway" in column]
    column = column[0]
    logz= str(logs[column][0]).split("\n")
    for i in range(1, len(logz)):
        if i == 1:
            yield logz[-i:-((i+1)*dimensione_blocco):-1]
        else:
           yield logz[-i*(dimensione_blocco):-((i+1)*dimensione_blocco):-1]  #scorre la lista di 15 elementi in dietro ad ogni invocazione

@tool
def check_api_gateway(input:str = "value") -> str:
  "get api gateway logs as plain text, each time you call this function you get the previous 15 lines of log"
  global counter_api
  if counter_api == None :
     counter_api = gen_api_gateway_logs()
  try:
    value = next(counter_api)
  except:
     return "no more logs to check here"
  return value


def gen_admission_manager_logs():
    dimensione_blocco = 15
    global logs
    columns = logs.columns
    column = [column for column in columns if "admission-manager" in column]
    column = column[0]
    logz= str(logs[column][0]).split("\n")
    if len(logz) < 15:
       yield str(logz)
    for i in range(1, len(logz)):
        if i == 1:
            yield logz[-i:-((i+1)*dimensione_blocco):-1]
        else:
           yield logz[-i*(dimensione_blocco):-((i+1)*dimensione_blocco):-1]  #scorre la lista di 15 elementi in dietro ad ogni invocazione

@tool
def check_admission_manager(input:str = "value") -> str:
  "get api admission-manager as plain text, each time you call this function you get the previous 15 lines of log"
  global coutner_admission
  if coutner_admission == None :
     counter_admission = gen_admission_manager_logs()
  try:
    value = next(counter_admission)
  except:
     return "no more logs to check here"
  return value


def gen_wait_estimator_logs():
    dimensione_blocco = 15
    global logs
    columns = logs.columns
    column = [column for column in columns if "wait-estimator" in column]
    column = column[0]
    logz= str(logs[column][0]).split("\n")
    if len(logz) < 15:
       yield str(logz)
    for i in range(1, len(logz)):
        if i == 1:
            yield logz[-i:-((i+1)*dimensione_blocco):-1]
        else:
           yield logz[-i*(dimensione_blocco):-((i+1)*dimensione_blocco):-1]  #scorre la lista di 15 elementi in dietro ad ogni invocazione

@tool
def check_wait_estimator(input:str = "value") -> str:
  "get api wait-estimator as plain text, each time you call this function you get the previous 15 lines of log"
  global counter_wait
  if counter_wait == None :
     counter_wait = gen_admission_manager_logs()
  try:
    value = next(counter_wait)
  except:
     return "no more logs to check here"
  return value

@tool
def check_pod_status(input:str = "none") -> str:
   """check the status of every pod in the system at the time of the incident"""
   return str(logs["pod_statuses"][0])


# Lista delle funzioni usando FunctionTool.from_defaults
tools = function_names = [
  check_emergency_service,
  check_api_gateway,
  check_admission_manager,
  check_wait_estimator,
  check_pod_status
]
  
system_description = """the whole system is on a kubernetes cluster.
- Admission-manager is a service used to create new patients in the system. it can do all sorts of operations like admitting patients, deleting from the record, updating their data etc. it is responsible to decide whether a new request is to be accepted, to make the decision
it check the available resoucrces in the ER asking emergency service and asking wait estimator for estimated waiting time. It communicates with its database containing data about past and present the ER.
- Api-gateway is where all the requests from outside the system pass. Api-gateway manages all the requests and uses a 'saga pattern' to manage distributed transaction between other services, every request made to the system must be rooted here.
Api-gateway manages authentication too.
- Emergency service is where data about the staff and their reources are managed. This system is interrogated by admission manager to check if there are enough resources free to accept new patients to the ER.
Users can communicate with emergency service to reserve resources in case a patient requires them, or to free those in case a patient leave the ER and they are not required anymore. All this data are stored in its database.
- Wait estimator this component is responsible to compute estimated waiting time in the ER. It uses Emergency serivce data and queue of patients in ER (retrieved by admission-manager) to compute this times.
"""


prompt = hub.pull("hwchase17/react-chat")
prompt.template = """
You are a root cause analysis assistant called Sherlock, you goal is to help the user find the root causes of problems in his system. Use the tools the help yourself explore the system in search of the cause. Once you find the cause report it to the user as best
as you can, do not suggest some possible solutions, just report the problem, no further details about what's not related to the problem the user is facing. 
Don't rush, thoroughly investigate the system to fully understand the causes.
Start the investigation ONLY if directly requested by the user with a question about a problem in the system.

System description:
{system_description}
""".format(system_description = system_description) + """
TOOLS:
------
Assistant has access to the following tools:
{tools}
To use a tool, please use the following format:
 
Thought: Do I need to use a tool? Yes, because...
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

Thought: Do I need to use a tool? No
Final Answer: [report your summary of the problem]

Begin!
Previous conversation history:
{chat_history}
New input: {input}
{agent_scratchpad}'
"""


ic(prompt)
if "GROQ_API_KEY" not in os.environ:
    os.environ["GROQ_API_KEY"] = "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"

llm = ChatGroq(
    model="llama-3.2-90b-vision-preview",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key= "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"
)

agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True, return_intermediate_steps= True, max_execution_time=1000)

message = input("write your message: ")
toSend = {"input":message, "chat_history":[],"agent_scratchpad":[]}
response = agent_executor.invoke(toSend)

## this transforms the single message into a continous chat
while  ".." not in message:
  toSend["chat_history"].append(f"human: {response["input"]}")
  toSend["chat_history"].append(f"Assistant: {response["output"]}")
  toSend["agent_scratchpad"].append(response["intermediate_steps"])
  message = input("write your message: ")
  if ".." in message:
     break
  toSend["input"]=message
  response = agent_executor.invoke(toSend)







