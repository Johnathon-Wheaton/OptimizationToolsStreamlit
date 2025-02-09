import streamlit as st
import asyncio
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import uuid
import time
import streamlit.components.v1 as components
import json
from io import BytesIO
import pandas as pd

def convert_to_dataframe(data):
    """Convert data to DataFrame based on its type"""
    if isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        return pd.DataFrame([data])
    else:
        return pd.DataFrame([{"value": data}])
    
def json_to_excel(json_data):
    # Create a BytesIO object to store the Excel file
    excel_buffer = BytesIO()
    
    # Create Excel writer object
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        # Parse JSON data
        data = json.loads(json_data)
        
        # Create summary sheet with all top-level primitive values
        summary_data = {}
        for key, value in data.items():
            if not isinstance(value, (dict, list)):
                summary_data[key] = value
        
        if summary_data:
            summary_df = pd.DataFrame([summary_data])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Process each key-value pair
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                sheet_name = key[:31]  # Excel sheet names limited to 31 chars
                df = convert_to_dataframe(value)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    # Get the value of the BytesIO buffer
    excel_buffer.seek(0)
    return excel_buffer

# Agent System Messages
CONSULTANT_SYSTEM_MSG = """You are a consultant with expertise in operations research. You do not write code.
You ask the user questions to understand their problem. Ask for one piece of information at a time 
and wait for the user to respond before asking for more information.

The user is likely unfamiliar with operations research terminology so use layman terms and be patient 
with the user to arrive at the information you would need to construct an optimization model to solve their problem.

When formulating the problem use variable names that are unambigiou and obvious to understand to any reader without needing to decode. 
These variable names can be long and descriptive such as "volume_of_product_A_to_ship_in_time_period_1".

When gathering information:
- Ask for solver time limit and optimality gap threshold
- Default to 10 minutes and 0.01 if not specified

Your summary should include:
1. Detailed optimization model description with intuitive variable names
2. Complete tables of all input sets and parameters
3. Solver parameters (time limit, optimality gap)
4. Request confirmation of accuracy

On final confirmation, provide:
1. Complete model description with intuitive naming
2. Full input parameter tables
3. A note to the user to wait while the ai team works together to provide a solution, it may take several minutes
4. Include 'TERMINATEX' to end conversation"""

STRATEGIZER_SYSTEM_MSG = """You are an expert in operations research. You will be presented with a problem that requires optimization.q

Your job is to identify the type of optimization model that is needed to solve the problem and the python library that should be used to solve it.

Read the problem in its entirety and identify the type of optimization model that is needed to solve the problem. Reread the problem to be sure you understant it completely.

Respond with the type of optimization model that is needed to solve the problem and the python library that should be used to solve it. The python library you recommend must be free to use and open source.
"""

STRATEGIZER_CRITIC_SYSTEM_MSG = """You are an expert in operations research working with another operations researcher.

Your job is to be a critic of the operations researcher you are working with who will recommend the type of optimization model and python library to use to solve a problem.
Read and fully understand every detail of the problem. Be sure the operations researcher isn't missing any details of the problem in their consideration of the type of optimization model and python library to use.

Keep your responses succinct and to the point.

When you are confident that your operations research companion has correctly identified the type of optimization model and python library to use, 
respond by restating word-for-word without any trucation the original problem message followed by a succinct and assertive statement of the type of optimization model and python library that should be used to solve the problem and the word 'TERMINATEX' to end the conversation.
"""

CODER_SYSTEM_MSG = """You are a coder. You do not run the code. Your only job is to write code. Do not do anything else.

Construct the described optimization model in python using hard-coded json data as inputs.
Be sure you all constraints, variables, parameters, and objective functions are included in the code.
Reread the problem description to ensure you have captured all details in the code.

Requirements:
- Use the recommended python library
- For package installation, provide Windows shell commands
- First line of Python code should be: # filename: <filename>
- Do not truncate any part of your code
- Include all input data directly in code
- Use intuitive variable names
- Full output results printed (using print statements) in json format
- Include all decision variables in output

Important: If using PuLP, LpVariable's cannot be divided by numbers. Instead, they can be multiplied by the reciprocal of the number. You must remember this when formulating constraints or objective functions.

A code critic will critique your code. Follow their recommendations while always remembering the original problem description.
Check to make sure any changes you make don't induce problems that you previously fixed in response to the code critic.
"""

CODE_CRITIC_SYSTEM_MSG = """You provide feedback on code alignment with problem description.
You and you alone are responsible for ensuring that the problem description is accurately and completely captured in the code.

- Specify required changes if code doesn't match requirements
- Explicitly state needed modifications
- Only give feedback if a change is required. Do not include feedback on what is 'good' or 'correct'.
- Only give feedback if the code is incorrect. Do not provide feedback on code quality or clarity.
- Do not ask for or insist on knowing any additional information about the problem
- If the coder responds to you without any changes to their code, then rephrasing your feedback.
- If the code uses PuLP, remember that LpVariable's cannot be divided by numbers. However, they can be multiplied by the reciprocal of the number.
  For example, "variable_a / 3" can instead be written as "variable_a * (1/3)". Even though 1/3 is a division operation, because it is in parentheses, it is a multiplication operation with regard to the LpVariable.
- Verify code will have intended outcome (e.g. verify the sense of the optimization is correct according to library documentation, verify the code will run without errors, verify the code will output the solution correctly, verify the printed output is correct according to library documentation)
- Double check to make sure every detail of the problem is captured in the code. If the problem is not fully captured, provide feedback on what is missing.
- Tell user to proceed if code is acceptable. If the code is acceptable, then say nothing except "User, proceed with running the code."

Read all fo the above again.
"""

INITIAL_MSG = """I need to optimize something. Consultant, I will begin conversing with you, and when you fully understand my problem then the coder can begin writing the model. 
                Reply to this message with 'Welcome! I am your optimization consultant. I will be your liaison to translate 
                your problem into a mathematical model. After I have a clear understanding of your problem, 
                I will summarize it and work with my team in the backend to provide a solution.
                Let's get started! Please describe, in as much detail as possible, the problem you are trying to solve.'"""

CHECKER_MSG = """Only reply when the code runs successfully without errors, or after 8 unsuccessful attempts to run the code. 
        If the code runs successfully and the solution is feasible (as indicated by the code output saying something along the lines of 'Result - Optimal solution found', 'solution found', or 'status optimal' then the only thing you are allowed reply with is the full json output of the code without any trucation followed by 'TERMINATEX'.
        Use the following as a template for your response:
        '{untruncated json code from previous message written as text (ie do not include "'''json")} TERMINATEX'
        If the code runs successfully and the solution is infeasible, as indicated by the output saying something along the lines of 'infeasible',  then the only thing you are allowed reply with is telling the user the problem was found to be infeasible and 'TERMINATEX'.
        Use the following as a template for your response:
        'Based on our formulation there is no feasible solution to your problem. Please validate your inputs and/or work with the consultant to reformulate your problem. TERMINATEX'
        If the code runs successfully but the solver ran out of time before finding a solution, as indicated by the output saying something along the lines of 'solution not found',  then the only thing you are allowed reply with is telling the user the solver ran out of time before finding a solution and 'TERMINATEX'.
        Use the following as a template for your response:
        'The solver hit the time limit before finding a solution. This does not necessarily mean your problem is infeasible. Try working with the consultant again and set the time limit to be longer. TERMINATEX'
        If the code fails after 4 attempts then reply with 'Unfortunately our team struggled to get our code to run successfully. 
        This could be caused by a misunderstanding of the problem or system dependency issues. Please try again later. TERMINATEX'"""

# Initialize session state for storing agents and messages
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'in_progress' not in st.session_state:
    st.session_state.in_progress = False
if 'agents' not in st.session_state:
    st.session_state.agents = None
if 'manager' not in st.session_state:
    st.session_state.manager = None
if 'printed_messages' not in st.session_state:
    st.session_state.printed_messages = []
if 'latest_update_time' not in st.session_state:
    st.session_state.latest_update_time = time.time()
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = 1
if 'loop' not in st.session_state:
    st.session_state.loop = None
if 'output_json' not in st.session_state:
    st.session_state.output_json = None

# Set page config to use full height
st.set_page_config(initial_sidebar_state="expanded")

# Custom CSS to handle layout
st.markdown("""
    <style>
        .main > div {
            padding-bottom: 100px;
        }
        .stChatInput {
            position: fixed;
            bottom: 0;
            background-color: white;
            padding: 1rem 1rem;
            z-index: 1000;
        }
        .chat-message-container {
            margin-bottom: 100px;
        }
    </style>
""", unsafe_allow_html=True)

st.write("""# AutoGen Chat Agents""")
with open("instructions.md", "r") as f:
    instructions = f.read()
with st.expander("📚 Instructions & Examples", expanded=False):
    st.markdown(instructions)
chat_container = st.container()

selected_model = None
selected_key = None
with st.sidebar:
    st.header("OpenAI Configuration")
    max_rounds = st.number_input("Maximum Rounds", min_value=0, max_value=100, value = 40)
    selected_model = st.selectbox("Model", ['gpt-4o', 'gpt-4o-mini'], index=1)
    selected_key = st.text_input("API Key", type="password")

class TrackableGroupChatManager(GroupChatManager):
        def a_receive(self, message, sender, request_reply = None, silent = False):
            if len(st.session_state.messages) >=  max_rounds:
                for message in st.session_state.messages:
                    if message.get("role") == "Consultant" or message.get("role") == "Checker":
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                        with st.chat_message("System"):
                            st.markdown("The maximum rounds have been reached before a solution was found. Please try again or increase the maximum rounds.")
            elif sender.name == 'Consultant' or sender.name == 'Checker' or sender.name == "OperationsResearcherCritic":
                if st.session_state.latest_update_time < time.time() - 1:
                    st.session_state.latest_update_time=time.time()
                    for message in st.session_state.messages:
                        if message.get("role") in ["Consultant", "user"]:
                            with st.chat_message(message["role"]):
                                st.markdown(message["content"])
                    if "terminatex" in st.session_state.messages[-1]["content"].lower():
                        if st.session_state.chat_id == 3:
                            # get json part of last message in st.sessionstate.messages
                            if st.session_state.messages[-1]["content"][0].strip() == "{":
                                st.session_state.output_json = st.session_state.messages[-1]["content"].split("TERMINATEX")[0].strip()
                        st.session_state.chat_id += 1
                        st.session_state.in_progress = False
                        print("Terminating chat")
                        if st.session_state.chat_id==3 or st.session_state.chat_id==2:
                            with chat_container:
                                if message.get("role") in ["Consultant", "user"]:
                                    for message in st.session_state.messages:
                                        with st.chat_message(message["role"]):
                                            st.markdown(message["content"])
                            st.rerun()
            return super().a_receive(message, sender, request_reply, silent)

class TrackableAssistantAgent(AssistantAgent):
    def a_send(self,message, recipient, request_reply, silent):
        new_message = {"role": self.name, "content": message, "id": uuid.uuid4()}
        st.session_state.messages.append(new_message)
        print(f"Sending {self.name} message: {new_message}")
        print(f"Number of rounds completed {len(st.session_state.messages)}" )
        return super().a_send(message, recipient, request_reply, silent)
class TrackableUserProxyAgent(UserProxyAgent):
    def a_send(self,message,recipient,request_reply = None,silent = False):
        print(f"Sending {self.name} message: {message}")
        print(f"Number of rounds completed {len(st.session_state.messages)}" )
        return super().a_send(message, recipient, request_reply, silent)



with st.container():
    if not selected_key or not selected_model:
            st.warning(
                'You must provide valid OpenAI API key and choose preferred model', icon="⚠️")
            st.stop()
    else:
        llm_config = {"config_list": [
                        {
                        "model": selected_model,
                        "api_key": selected_key
                        }
                    ]
                 }
        if st.session_state.in_progress == False:
            if st.session_state.chat_id == 1:
                print("Creating agents for chat 1")
                INITIAL_MSG = """I need to optimize something. Consultant, I will begin conversing with you, and when you fully understand my problem then the coder can begin writing the model. 
                Reply to this message with 'Welcome! I am your optimization consultant. I will be your liaison to translate 
                your problem into a mathematical model. After I have a clear understanding of your problem, 
                I will summarize it and work with my team in the backend to provide a solution.
                Let's get started! Please describe, in as much detail as possible, the problem you are trying to solve.'"""

                consultant = TrackableAssistantAgent(
                        name="Consultant", llm_config=llm_config, 
                        system_message=CONSULTANT_SYSTEM_MSG,          
                        human_input_mode="NEVER",
                        is_termination_msg=lambda msg: "terminatex" in msg["content"].lower()
                        )
                user_proxy = TrackableUserProxyAgent(
                        name="user",
                        system_message="A human.",  
                        human_input_mode="ALWAYS",
                        code_execution_config=False, 
                        llm_config=llm_config)
                
                groupchat1 = GroupChat(
                    agents=[consultant, user_proxy],
                    messages=[],
                    max_round=max_rounds,
                    speaker_transitions_type="allowed",
                    allowed_or_disallowed_speaker_transitions={
                        consultant: [user_proxy],
                        user_proxy: [consultant],
                    }
                )
            
                st.session_state.manager = TrackableGroupChatManager(
                    groupchat=groupchat1,
                    llm_config=llm_config,
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                )
                st.session_state.agents = (consultant, user_proxy,  None, None, None, None, None)
            elif st.session_state.chat_id == 2:
                print("Creating agents for chat 2")
                st.session_state.loop.close()
                INITIAL_MSG = st.session_state.messages[-1]["content"].replace('TERMINATEX', '').replace('terminatex', '').replace('Terminatex', '') 
                
                user_proxy = TrackableUserProxyAgent(
                    name="User_proxy",
                    system_message="A human.",
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                        code_execution_config=False, 
                    # silent = True
                )

                strategizer = TrackableAssistantAgent(
                    name="OperationsResearcher",
                    system_message=STRATEGIZER_SYSTEM_MSG,
                    llm_config=llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                    # silent = True
                )
                
                strategizer_critic = TrackableAssistantAgent(
                    name="OperationsResearcherCritic",
                    system_message=STRATEGIZER_CRITIC_SYSTEM_MSG,
                    llm_config=llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                    # silent = True
                )

                groupchat2 = GroupChat(
                    agents=[strategizer, strategizer_critic, user_proxy],
                    messages=[],
                    max_round=max(0,max_rounds-len(st.session_state.messages))
                )
                st.session_state.manager = TrackableGroupChatManager(
                    groupchat=groupchat2,
                    llm_config=llm_config,
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                )
                st.session_state.agents = (None, user_proxy, None,  None, None, strategizer, strategizer_critic)
            elif st.session_state.chat_id == 3:
                print("Creating agents for chat 3")
                st.session_state.loop.close()
                INITIAL_MSG = st.session_state.messages[-1]["content"].replace('TERMINATEX', '').replace('terminatex', '').replace('Terminatex', '') 

                user_proxy = TrackableUserProxyAgent(
                    name="User_proxy",
                    system_message="A human. Only run code provided by the coder.",
                    human_input_mode="NEVER",
                    code_execution_config={
                        "last_n_messages": 2,
                        "work_dir": "groupchat",
                        "use_docker": False,
                    },
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                    # silent = True
                )
                
                coder = TrackableAssistantAgent(
                    name="Coder",
                    system_message=CODER_SYSTEM_MSG,
                    llm_config=llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                    # silent = True
                )
                
                code_critic = TrackableAssistantAgent(
                    name="CodeCritic",
                    system_message=CODE_CRITIC_SYSTEM_MSG,
                    llm_config=llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                    # silent = True
                )
                
                checker = TrackableAssistantAgent(
                    name="Checker",
                    system_message=CHECKER_MSG,
                    llm_config=llm_config,
                    human_input_mode="NEVER",
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                )

                groupchat3 = GroupChat(
                    agents=[coder, user_proxy, checker, code_critic],
                    messages=[],
                    max_round=max(0,max_rounds-len(st.session_state.messages)),
                    speaker_transitions_type="allowed",
                    allowed_or_disallowed_speaker_transitions={
                        coder: [code_critic],
                        code_critic: [coder, user_proxy],
                        user_proxy: [coder, checker],
                    }
                )
                st.session_state.manager = TrackableGroupChatManager(
                    groupchat=groupchat3,
                    llm_config=llm_config,
                    is_termination_msg=lambda msg: "terminatex" in msg["content"].lower(),
                )
                st.session_state.agents = (None, user_proxy, coder,  checker, code_critic, None, None)
        
        consultant, user_proxy, coder, checker, code_critic, strategizer, strategizer_critic = st.session_state.agents
        manager = st.session_state.manager
        
        # Create an event loop
        st.session_state.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(st.session_state.loop)

        async def continue_chat(user_input):
            await manager.a_receive(message=user_input, sender=user_proxy)

        async def initiate_chat():
            await user_proxy.a_initiate_chats(
                [
                    {
                        "chat_id": 1,
                        "recipient": manager,
                        "message": INITIAL_MSG,
                        "silent": False,
                        "summary_method": "last_msg"
                    }
                ]
            )

        user_input = st.chat_input("Type something...")
        if not st.session_state.in_progress and st.session_state.chat_id <4:
            st.session_state.in_progress = True
            with chat_container:
                for message in st.session_state.messages:
                    if message.get("role") in ["Consultant", "Checker", "user"]:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                if st.session_state.chat_id == 3 or st.session_state.chat_id == 2:
                    with st.chat_message("System"):
                        col1, col2 = st.columns([0.85, 0.15])
                        with col1:
                            st.markdown("A team of AI agents is working on solving this problem. This may take several minutes. When finished, they will reply with an excel output to view the results.")
                        with col2:
                            with st.spinner(""):
                                 st.empty()

            st.session_state.loop.run_until_complete(initiate_chat())
        if st.session_state.chat_id >= 4:
            for message in st.session_state.messages:
                if message.get("role") in ["Consultant","Checker", "user"]:
                    if message.get("role") == "Checker" and not st.session_state.output_json:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                    elif message.get("role") != "Checker":
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
            if st.session_state.output_json:
                with st.chat_message("System"):
                    st.markdown("The AI team has finished working on the problem. You can download the output below.")
                print(st.session_state.output_json)
                excel_file = json_to_excel(st.session_state.output_json)
                # Create download button
                st.download_button(
                    label="Click to Download",
                    data=excel_file,
                    file_name="AI_Agent_Optimization_Output.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    if user_input:
        # Create agents if they don't exist or if configuration changed
        
        
        # Add user input to messages
        st.session_state.messages.append({"role": "user", "content": user_input, "id": uuid.uuid4()})

        # Run the asynchronous function within the event loop
        # try:
        st.session_state.loop.run_until_complete(continue_chat(user_input))
