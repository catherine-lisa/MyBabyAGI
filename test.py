import os
from collections import deque
from typing import List, Dict, Optional, Any, Tuple

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain, SimpleSequentialChain
from dotenv import load_dotenv
import ipdb
load_dotenv()

template = "我的邻居姓{lastname}，他生了个儿子，给他儿子起个名字"

prompt = PromptTemplate(
    input_variables=["lastname"],
    template=template,
)
llm = ChatOpenAI(temperature=0.9)

chain = LLMChain(llm = llm,  prompt = prompt)
# 执行链
print(chain.invoke("王"))

# 创建第二条链
second_prompt = PromptTemplate(
    input_variables=["child_name"],
    template="邻居的儿子名字叫{child_name}，给他起一个小名",
)

chain_two = LLMChain(llm=llm, prompt=second_prompt)

# 链接两条链 
overall_chain = SimpleSequentialChain(chains=[chain, chain_two], verbose=True)
# ipdb.set_trace()  .
# 执行链，只需要传入第一个参数
catchphrase = overall_chain.invoke("王")