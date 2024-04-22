import json
from datetime import datetime, timedelta
from typing import List
from langchain.docstore import InMemoryDocstore
from langchain.retrievers import TimeWeightedVectorStoreRetriever
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from termcolor import colored
from langchain_experimental.generative_agents import (
    GenerativeAgent,
    GenerativeAgentMemory,
)
import math
import faiss
import os

os.environ["OPENAI_API_KEY"] = "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"
LLM = ChatOpenAI(model="gpt-4", max_tokens=2500, temperature=0.8)  # Can be any LLM you want.


def relevance_score_fn(score: float) -> float:
    """Return a similarity score on a scale [0, 1]."""
    # This will differ depending on a few things:
    # - the distance / similarity metric used by the VectorStore
    # - the scale of your embeddings (OpenAI's are unit norm. Many others are not!)
    # This function converts the euclidean norm of normalized embeddings
    # (0 is most similar, sqrt(2) most dissimilar)
    # to a similarity function (0 to 1)
    return 1.0 - score / math.sqrt(2)


def create_new_memory_retriever():
    """Create a new vector store retriever unique to the agent."""
    # Define your embedding model
    embeddings_model = OpenAIEmbeddings()
    # Initialize the vectorstore as empty
    embedding_size = 1536
    index = faiss.IndexFlatL2(embedding_size)
    vectorstore = FAISS(
        embeddings_model.embed_query,
        index,
        InMemoryDocstore({}),
        {},
        relevance_score_fn=relevance_score_fn,
    )
    return TimeWeightedVectorStoreRetriever(
        vectorstore=vectorstore, other_score_keys=["importance"], k=15
    )


def agent_dialogue(agent: GenerativeAgent, new_message: str) -> str:
    """Help the notebook user interact with the agent."""
    # new_message = f"{USER_NAME} says {message}"
    return agent.generate_dialogue_response(new_message)[1]


def run_conversation(agents: List[GenerativeAgent], initial_observation: str) -> None:
    """Runs a conversation between agents."""
    _, observation = agents[1].generate_reaction(initial_observation)
    print("Starting conversation.")
    print(observation)
    turns = 0
    while True:
        break_dialogue = False
        for agent in agents:
            stay_in_dialogue, observation = agent.generate_dialogue_response(
                observation
            )
            print(observation)
            # observation = f"{agent.name} said {reaction}"
            if not stay_in_dialogue:
                break_dialogue = True
        if break_dialogue:
            break
        turns += 1


def creating_scenario(scenario_name: str):
    with open("scenarios.json", "r") as setup_file:
        scenario_data = json.load(setup_file)

    # Creating agent One
    agent_one_memory = GenerativeAgentMemory(
        llm=LLM,
        memory_retriever=create_new_memory_retriever(),
        verbose=False,
        reflection_threshold=3,  # we will give this a relatively low number to show how reflection works
    )

    agent_one = GenerativeAgent(
        name=scenario_data[scenario_name]['agent_one_name'],
        age=scenario_data[scenario_name]['agent_one_age'],
        traits=scenario_data[scenario_name]['agent_one_traits'],
        # You can add more persistent traits here
        status=scenario_data[scenario_name]['agent_one_status'],
        # When connected to a virtual world, we can have the characters update their status
        memory_retriever=create_new_memory_retriever(),
        llm=LLM,
        memory=agent_one_memory,
    )

    # We can add memories directly to the memory object
    for observation in scenario_data[scenario_name]['agent_one_observations']:
        agent_one.memory.add_memory(observation)

    # Now that agent_one has 'memories', their self-summary is more descriptive, though still rudimentary.
    # We will see how this summary updates after more observations to create a more rich description.
    print(agent_one.get_summary(force_refresh=True))

    # starting a conversation as an example
    agent_one_dialog = agent_dialogue(agent_one,
                                      "tell me about your thoughts, what do you think?")

    # Creating agent Two
    agent_two_memory = GenerativeAgentMemory(
        llm=LLM,
        memory_retriever=create_new_memory_retriever(),
        verbose=False,
        reflection_threshold=5,
    )

    agent_two = GenerativeAgent(
        name=scenario_data[scenario_name]['agent_two_name'],
        age=scenario_data[scenario_name]['agent_two_age'],
        traits=scenario_data[scenario_name]['agent_two_traits'],
        # You can add more persistent traits here
        status=scenario_data[scenario_name]['agent_two_status'],
        llm=LLM,
        # You Can also add list of daily observations summary
        # daily_summaries=,
        memory=agent_two_memory,
        verbose=False,
    )

    for observation in scenario_data[scenario_name]['agent_two_observations']:
        agent_two.memory.add_memory(observation)

    print(agent_two.get_summary())

    # starting a conversation as an example
    agent_two_dialog = agent_dialogue(agent_two,
                                      agent_one_dialog)

    agents = [agent_two, agent_one]
    run_conversation(
        agents,
        "start a conversation regarding to status and situation. stay creative in conversation.",
    )


if __name__ == "__main__":
    creating_scenario("Matthew Perry's Therapy Session")
