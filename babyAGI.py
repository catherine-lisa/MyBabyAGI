import os
from collections import deque
from typing import Dict, List, Optional, Any, Deque
# from langchain import LLMChain, OpenAI, PromptTemplate
from langchain_openai import ChatOpenAI, OpenAI
from langchain import PromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain.llms import BaseLLM
from langchain.vectorstores.base import VectorStore
from pydantic import BaseModel, Field
from langchain.chains.base import Chain
from langchain.chains import LLMChain
from langchain.vectorstores import FAISS
from langchain.docstore import InMemoryDocstore
import ipdb
from dotenv import load_dotenv
load_dotenv()
from langchain.vectorstores import FAISS
import faiss    

# define embedding model
embeddings_model = OpenAIEmbeddings()

# 向量维度为1536
embedding_size = 1536
# 采用基于欧几里得距离（L2距离）的向量搜索
index = faiss.IndexFlatL2(embedding_size)
vector_store = FAISS(embeddings_model, index, InMemoryDocstore({}), {})

# BabyAGI依赖于三个LLM链:
# 任务创建链，用于选择要添加到列表中的新任务
# 任务优先级链，用于重新设置任务的优先级
# 执行链，用于执行任务

# 任务创建链
class TaskCreationChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: BaseLLM, verbose: bool = True) -> LLMChain:
        task_creation_template = (
            "You are a task creation AI that uses the result of an execution agent"
            " to create new tasks with the following objective: {objective},"
            " The last completed task has the result: {result}."
            " This result was based on this task description: {task_description}."
            " These are incomplete tasks: {incomplete_tasks}."
            " Based on the result, create new tasks to be completed"
            " by the AI system that do not overlap with incomplete tasks."
            " Return the tasks as an array."
        )
        prompt = PromptTemplate(
            template=task_creation_template,
            input_variables=[
                "result",
                "task_description",
                "incomplete_tasks",
                "objective",
            ],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)
    
# 任务优先级链
class TaskPrioritizationChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: BaseLLM, verbose: bool = True) -> LLMChain:
        task_prioritization_template = (
            "You are a task prioritization AI tasked with cleaning the formatting of and reprioritizing"
            " the following tasks: {task_names}."
            " Consider the ultimate objective of your team: {objective}."
            " Do not remove any tasks. Return the result as a numbered list, like:"
            " #. First task"
            " #. Second task"
            " Start the task list with number {next_task_id}."
        )
        prompt = PromptTemplate(
            template=task_prioritization_template,
            input_variables=["task_names", "next_task_id", "objective"],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)
    
# 执行链
class ExecutionChain(LLMChain):
    @classmethod
    def from_llm(cls, llm: BaseLLM, verbose: bool = True) -> LLMChain:
        execution_template = (
            "You are an AI who performs one task based on the following objective: {objective}."
            " Take into account these previously completed tasks: {context}."
            " Your task: {task}."
            " Response:"
        )
        prompt = PromptTemplate(
            template=execution_template,
            input_variables=["objective", "context", "task"],
        )
        return cls(prompt=prompt, llm=llm, verbose=verbose)


# 下面定义相关函数

def get_next_task(
    task_creation_chain: TaskCreationChain,
    result: Dict,
    task_description: str,
    task_list: List[str],
    objective: str,
) -> List[Dict]:
    """Get the next task"""
    incomplete_tasks = ",".join(task_list)
    # print("incomplete_tasks are", incomplete_tasks)
    input_dict = {
        "result": result,
        "task_description": task_description,
        "incomplete_tasks": incomplete_tasks,
        "objective": objective,
    }
    response = task_creation_chain.invoke(input=input_dict)
    new_tasks = response['text'].split("\n")
    Next_task = [{"task_name": task_name} for task_name in new_tasks if task_name.strip()]
    
    # for i, task in enumerate(Next_task):
    #     print(i, task)

    return Next_task


def prioritize_tasks(
    task_prioritization_chain: TaskPrioritizationChain,
    this_task_id: int,
    task_list: List[Dict],
    objective: str,
) -> List[Dict]:
    """Prioritize tasks"""
    task_names = [task["task_name"] for task in task_list]
    next_task_id = int(this_task_id) + 1
    input_dict = {
        "task_names": task_names,
        "next_task_id": next_task_id,
        "objective": objective,
    }

    response = task_prioritization_chain.invoke(input=input_dict)
    new_tasks = response['text'].split("\n")

    prioritized_task_list = []
    for task_string in new_tasks:
        if not task_string.strip():
            continue
        
        task_parts = task_string.strip().split(".", 1)
        if len(task_parts) == 2:
            task_id = task_parts[0].strip()
            task_name = task_parts[1].strip()
            prioritized_task_list.append(
                {"task_id": task_id, "task_name": task_name}
            )
    return prioritized_task_list

def _get_top_tasks(vectorstore, query: str, k: int) -> List[str]:
    """Get the top k tasks based on the query."""
    results = vectorstore.similarity_search_with_score(query, k=k)

    if not results:
        return []
    
    sorted_results, _ = zip(*sorted(results, key=lambda x: x[1], reverse=True))
    return [str(item.metadata["task"]) for item in sorted_results]

def execute_task(vectorstore, execution_chain: LLMChain, objective: str, task: str, k: int = 5) -> str:
    """Execute the task"""
    context = _get_top_tasks(vectorstore, query=objective, k=k)
    # result = execution_chain.invoke(objective=objective, context=context, task=task).content
    input_dict = {
        "objective": objective,
        "context": context,
        "task": task
    }
    result = execution_chain.invoke(input=input_dict)
    return result['text']

# 下面定义BabyAGI类
class BabyAGI:
    """Controller model for the BabyAGI agent."""
    # task_list: deque = Field(default_factory=deque)
    task_list: Deque[Dict[str, Any]] = Field(default_factory=deque)
    task_creation_chain: TaskCreationChain = Field(...)
    task_prioritization_chain: TaskPrioritizationChain = Field(...)
    execution_chain: ExecutionChain = Field(...)
    task_id_counter: int = Field(1)
    vectorstore: VectorStore = Field(init=False)
    max_iterations: Optional[int] = Field(None)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, task_creation_chain: TaskCreationChain, task_prioritization_chain: TaskPrioritizationChain, execution_chain: ExecutionChain, vectorstore: VectorStore, max_iterations: Optional[int] = None, **kwargs):
        self.task_list = deque()
        self.task_id_counter = 1
        self.task_creation_chain = task_creation_chain
        self.task_prioritization_chain = task_prioritization_chain
        self.execution_chain = execution_chain
        self.vectorstore = vectorstore
        self.max_iterations = max_iterations

    def add_task(self, task: Dict) -> None:
        """Add a task to the task list."""
        self.task_list.append(task)

    def print_task_list(self):
        print("\033[95m\033[1m" + "*****TASK LIST*****" + "\033[0m\033[0m")
        for t in self.task_list:
            print(str(t["task_id"]) + ": " + t["task_name"])

    def print_next_task(self, task: Dict):
        print("\033[95m\033[1m" + "*****NEXT TASK*****" + "\033[0m\033[0m")
        print(str(task["task_id"]) + ": " + task["task_name"])

    def print_task_result(self, result: str):
        print("\033[95m\033[1m" + "*****TASK RESULT*****" + "\033[0m\033[0m")
        print(result)

    @property
    def input_keys(self) -> List[str]:
        return ["objective"]

    @property
    def output_keys(self) -> List[str]:
        return []
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent"""
        objective = inputs["objective"]
        first_task = inputs.get("first_task", "Make a todo list")
        self.add_task({"task_id": 1, "task_name": first_task})
        num_iters = 0

        while True:
            if self.task_list:
                self.print_task_list()

                # Step 1: Pull the first task
                task = self.task_list.popleft()
                self.print_next_task(task)

                # Step 2: Execute the task
                result = execute_task(
                    self.vectorstore, self.execution_chain, objective, task["task_name"]
                )
                this_task_id = int(task["task_id"])
                self.print_task_result(result)

                # Step 3: Store the result in Pinecone
                result_id = f"result_{task['task_id']}"
                self.vectorstore.add_texts(
                    texts=[result],
                    metadatas=[{"task": task["task_name"]}],
                    ids=[result_id],
                )

                # Step 4: Create new tasks and reprioritize task list
                new_tasks = get_next_task(
                    self.task_creation_chain,
                    result,
                    task["task_name"],
                    [t["task_name"] for t in self.task_list],
                    objective,
                )

                for new_task in new_tasks:
                    self.task_id_counter += 1
                    new_task.update({"task_id": self.task_id_counter})
                    self.add_task(new_task)

                self.task_list = deque(
                    prioritize_tasks(
                        self.task_prioritization_chain,
                        this_task_id,
                        list(self.task_list),
                        objective,
                    )
                )
            
            num_iters += 1
            if self.max_iterations is not None and num_iters == self.max_iterations:
                print("\033[91m\033[1m" + "*****TASK ENDING*****" + "\033[0m\033[0m")
                break

        return {}
        
    @classmethod
    def from_llm(
        cls,
        llm: BaseLLM,
        vectorstore: VectorStore,
        verbose: bool = False,
        **kwargs,
    ) -> "BabyAGI":
        """Initialize the BabyAGI Controller."""
        task_creation_chain = TaskCreationChain.from_llm(llm, verbose=verbose)
        task_prioritization_chain = TaskPrioritizationChain.from_llm(
            llm, verbose=verbose
        )
        execution_chain = ExecutionChain.from_llm(llm, verbose=verbose)
        return cls(
            task_creation_chain=task_creation_chain,
            task_prioritization_chain=task_prioritization_chain,
            execution_chain=execution_chain,
            vectorstore=vectorstore,
            verbose=verbose,
            **kwargs,
        )


OBJECTIVE = "Write a weather report for SF today"
llm = OpenAI(temperature=0)
verbose = False
max_iterations: Optional[int] = 10

baby_agi = BabyAGI.from_llm(
    llm=llm,
    vectorstore=vector_store,
    verbose=verbose,
    max_iterations=max_iterations,
)

baby_agi._call({"objective": OBJECTIVE})
