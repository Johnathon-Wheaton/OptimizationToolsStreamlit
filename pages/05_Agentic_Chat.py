import streamlit as st
import autogen
from typing import Dict

def create_agents(api_key: str) -> Dict:
    """Create and return the agent configurations"""
    llm_config = {"model": "gpt-4o-mini", "api_key": api_key}
    llm_config_4 = {"model": "gpt-4o-mini", "api_key": api_key}

    user_proxy = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human.",
        human_input_mode="ALWAYS",
        code_execution_config=False,
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    user_proxy2 = autogen.UserProxyAgent(
        name="User_proxy",
        system_message="A human.",
        human_input_mode="NEVER",
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    coder = autogen.AssistantAgent(
        name="Coder",
        system_message="""You are a coder. Construct the described optimization model in python using the json data as inputs. You do not the run code. 

        If the user needs to install any packages, respond with the installation shell commands before the python code. The user is using windows.
        
        The first line in any block of python code should be # filename: <filename> so the user will save the code in a file before executing it. 

        Do not ask the user to replace any part of the code. The user will not make any edites to your code before running, so do not write any comments suggesting the user needs to populate more inputs.
        Hard-code all of the input data directly in the python code. Do not write any comments suggesting the user needs to populate portions of the input data. Never concatenate the code.

        Preserve the user's labeling of sets in the outputs, use variable names that are intuitive for a layman reading the outputs. Try to anticipate what other output data the user might want and include it in additional sheets of the output file.

        The code must output results to an excel file named 'output.xlsx' and saved in the same directory as the code. Include the solution for all decision variables in the output file.
        """,
        llm_config=llm_config_4,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    codecritic = autogen.AssistantAgent(
        name="CodeCritic",
        system_message="""You provide feedback to the coder to verify that the code aligns with the description of the problem.

        State changes to make the code if it does not align with the problem description. If the code is not acceptable then explicitely tell the coder what changes need to be made. Do not merely provide suggestions to consider. Rather, state the change that need to be made.
        
        If the code is acceptable then explicitely tell the user to proceed with running the code.

        After the code successfully runs and you are satisfied with the output then reply with 'TERMINATE' to end the chat.
        """,
        llm_config=llm_config_4,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    checker = autogen.AssistantAgent(
        name="Checker",
        system_message="""Only replay when the code runs successfully without errors. The only thing you are allowed to say is 'TERMINATE'
        """,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    consultant = autogen.ConversableAgent(
        name="Consultant",
        system_message="""You are a consultant with expertise in operations research. You do not write code. You ask the user questions to understand their problem. Ask for one piece of information at a time and wait for the user to respond before asking for more information.
        The user is likely unfamiliar with operations research terminology so use layman terms and be patient with the user to arrive at the information you would need to construct an optimization model to solve their problem.
        When you feel you have fully understood the user's problem, constraints, variables, and parameters, send one message back to the user that contains all of the following:
         1. A full detailed description of the optimization model that will be coded. Preserve the user's labeling of sets in the outputs, use variable names that are descriptive and intuitive for a layman reading the outputs. 
         2. Tables of all user input sets and parameters, structured in a way that can be used as an input to the optmization model. Do not simply summarize or list the table names, but rather write out the entire tables with data. Do not simply describe parameters, but rather write out all numeric parameters the user provided. Do not truncate any data, list it all in its entirety.
         3. Ask the user if anything is missing or incorrect in your summary. Do not include the word "terminate" in your response.

        If the user provides more information, ask for clarification on the new information and summarize the model again.
        
        When the user confirms your summary is correct, send one message directed to coder that contains all of the following:
         1. A full detailed description of the optimization model that will be coded. Preserve the user's labeling of sets in the outputs, use variable names that are descriptive and intuitive for a layman reading the outputs. 
         2. Tables of all user input sets and parameters, structured in a way that can be used as an input to the optmization model. Do not simply summarize or list the table names, but rather write out the entire tables with data. Do not simply describe parameters, but rather write out all numeric parameters the user provided. Do not truncate any data, list it all in its entirety.
         3. The word 'TERMINATE' to end the conversation.
        """,
        llm_config=llm_config_4,
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
        human_input_mode="NEVER",
    )

    return {
        "user_proxy": user_proxy,
        "user_proxy2": user_proxy2,
        "coder": coder,
        "codecritic": codecritic,
        "checker": checker,
        "consultant": consultant,
        "llm_config": llm_config,
        "llm_config_4": llm_config_4
    }

def create_groupchats(agents: Dict):
    """Create and return the group chats"""
    groupchat1 = autogen.GroupChat(
        agents=[agents["consultant"], agents["user_proxy"]], 
        messages=[], 
        max_round=20,
        speaker_transitions_type="allowed",
        allowed_or_disallowed_speaker_transitions={
            agents["consultant"]: [agents["user_proxy"]],
            agents["user_proxy"]: [agents["consultant"]],
        }
    )
    
    groupchat2 = autogen.GroupChat(
        agents=[agents["coder"], agents["user_proxy2"], agents["checker"], agents["codecritic"]], 
        messages=[], 
        max_round=20,
        speaker_transitions_type="allowed",
        allowed_or_disallowed_speaker_transitions={
            agents["coder"]: [agents["codecritic"]],
            agents["codecritic"]: [agents["coder"], agents["user_proxy2"]],
            agents["user_proxy2"]: [agents["coder"], agents["checker"]],
        }
    )

    return {
        "groupchat1": groupchat1,
        "groupchat2": groupchat2
    }

def create_managers(groupchats: Dict, llm_config: Dict, llm_config_4: Dict):
    """Create and return the group chat managers"""
    manager1 = autogen.GroupChatManager(
        groupchat=groupchats["groupchat1"], 
        llm_config=llm_config,
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )
    
    manager2 = autogen.GroupChatManager(
        groupchat=groupchats["groupchat2"], 
        llm_config=llm_config_4,
        is_termination_msg=lambda msg: "terminate" in msg["content"].lower(),
    )

    return {
        "manager1": manager1,
        "manager2": manager2
    }

def agentic_chat_page():
    st.title("Optimization Problem Solver Chat (COMING SOON)")

    # Overview
    with st.expander("📃 Overview", expanded=True):
        st.markdown("""
        ### Overview
        This chat interface helps you formulate and solve optimization problems through conversation. 
        The system uses multiple AI agents:
        
        1. **Consultant**: Helps understand your problem and formulate it mathematically
        2. **Coder**: Writes the optimization model code
        3. **CodeCritic**: Reviews the code for accuracy
        4. **Checker**: Verifies code execution
        
        #### How it works:
        1. First, you'll discuss your problem with the Consultant
        2. Once the problem is well-defined, the Coder will implement it
        3. The CodeCritic will review the implementation
        4. Finally, the code will be executed and checked
        
        #### Getting Started:
        1. Enter your OpenAI API key below
        2. Start by describing your optimization problem
        3. Follow the Consultant's questions to fully define the problem
        """)

    with st.expander("Example Prompt", expanded=False):
        st.markdown("""
        I have 2 warehouse facilities and I need to know how to best utilize the space to achieve the lowest cost. Each facility has indoor and outdoor storage bins.
        Facility 1 has 100,000 sq ft of indoor storage space and 100,000 sq ft of outdoor storage space.
        Facility 2 has 75,000 sq ft of indoor storage space and 200,000 sq ft of outdoor storage space.
        There are three different types of products: product A, product B, and product C. Product A must be stored indoor, either in an indoor on-ground storage bin or an indoor rack storage bin. A single storage bin can hold 10 of product A. Products B and C can be stored either indoor or outdoor, either in an indoor on-ground storage bin, an indoor rack storage bin, or outdoor on-ground storage bin. A single storage bin can hold 3 of product B. Product C requires 2 bins per product (0.5 units per bin).
        Storage bins can be located either directly on the ground, or on racks. Storage bins on the ground consume 32 sq ft each. Storage racks also consume 32 sq ft each but hold 3 storage bins each.
        Facility 1 currently has 2,000 indoor storage racks (equating to 6,000 storage bins consuming 64,000 sq ft of indoor space), 1,125 indoor on-ground storage bins (equating to 1,125 storage bins consuming 36,000 sq ft), and 3,125 outdoor on-ground storage bins (equating to 3,125 storage bins consuming 100,000 sq ft of outdoor space).
        Facility 2 currently has 2,343 indoor on-ground storage bins (equating to 2,343 storage bins consuming 75,000 sq ft of indoor space), and 6,250 outdoor on-ground storage bins (equating to 6,250 storage bins consuming 200,000 sq ft of outdoor space).
        Storage racks can be added to indoor facilities to expand storage bin capacity. It costs 3,000 per storage rack to add new racks. Storage racks can only be added indoor. For each storage rack added, an indoor on-ground storage bin must be removed. On-ground storage bins have no cost. It does not cost money to remove storage racks or on-ground storage bins.
        There must be enough storage space to hold at least 90,000 units of product A, 10,000 units of product B, and 1,000 units of product C.
        I need to know how many storage racks to add to or remove from each facility, how much of each product to store in each facility, and how many bins by type (indoor on-ground, indoor rack, or outdoor on-ground) to allocate to each product in each facility such that total cost will be minimized.
        Be sure to specify that indoor racks, indoor on-ground storage, and outdoor on-ground storage locations all consume 32sq ft. However, indoor racks hold 3 bins while on-ground storage locations only hold 1 bin.

        1. the limit is only constrained by the available indoor space once bins are removed for rack installation
        1.	the main focus is simply to minimize the cost of adding racks while meeting the product storage requirements
        Be sure to specify that indoor racks consume 32 sq ft and hold 3 bins while outdoor on-ground and indoor on-ground locations consume 32 sq ft and hold 1 bin. Also, state the number of units per bin for each product.
        """)


    # API Key Input
    api_key = st.text_input("Enter your OpenAI API Key:", type="password")
    if not api_key:
        st.warning("Please enter your OpenAI API key to continue.")
        return

    # Initialize session state for chat
    if "chat_initialized" not in st.session_state:
        st.session_state.chat_initialized = False
        st.session_state.messages = []
        st.session_state.current_phase = "consultant"

    # Initialize chat if not already done
    if not st.session_state.chat_initialized and api_key:
        agents = create_agents(api_key)
        groupchats = create_groupchats(agents)
        managers = create_managers(groupchats, agents["llm_config"], agents["llm_config_4"])
        
        st.session_state.agents = agents
        st.session_state.managers = managers
        st.session_state.chat_initialized = True
        st.session_state.messages = []

    # Chat interface
    if st.session_state.chat_initialized:
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Type your message here..."):
            # Add user message to chat history
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            

            user_proxy = st.session_state.agents["user_proxy"]
            manager1 = st.session_state.managers["manager1"]
            manager2 = st.session_state.managers["manager2"]

            # Display and store the response
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Get the response
            response = user_proxy.initiate_chats(
                [
                    {
                    "recipient": manager1,
                    "message": prompt,
                    "clear_history": True,
                    "silent": False,
                    "summary_method": "last_msg"
                    },
                    {
                    "recipient": manager2,
                    "message": "Write the code for this model",
                    "clear_history": True,
                    "silent": False,
                    "summary_method": "last_msg",
                    }
                ]
            )
            

            # Check if consultant phase is complete
            if "TERMINATE" in response:
                st.session_state.current_phase = "complete"
                st.success("Optimization problem has been solved! Check the output.xlsx file for results.")


            st.rerun()

if __name__ == "__main__":
    agentic_chat_page()