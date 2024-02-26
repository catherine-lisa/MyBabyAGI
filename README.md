### 项目概述
`MyBabyAGI`是一个基于Python的项目，旨在创建一个简单的AI代理（BabyAGI），该代理能够根据给定的目标（objective）执行任务。它使用语言模型链（LLMChain）来创建、优先排序和执行任务。此外，该项目还使用了向量存储（VectorStore）来存储任务的执行结果，以便后续的相似性搜索。
### 核心功能
1. **任务创建链（TaskCreationChain）**:
   - 根据上一个任务的执行结果和给定的目标创建新任务。
   - 避免创建与现有未完成任务重叠的任务。
2. **任务优先级链（TaskPrioritizationChain）**:
   - 清理任务格式并重新排序任务列表。
   - 考虑到团队的整体目标，对任务进行优先级排序。
3. **执行链（ExecutionChain）**:
   - 基于给定的目标和上下文执行任务。
4. **BabyAGI控制器**:
   - 管理任务列表、任务ID计数器和任务执行流程。
   - 使用向量存储来存储和检索任务结果。
### 代码结构
- `babyAGI.py`: 包含了BabyAGI的核心逻辑和类定义。
- `__pycache__`: 存储了Python编译后的字节码文件。
- `test.py`: 可能用于测试项目功能的Python文件。
- `requirements.txt`: 列出了项目依赖的Python库。
### 运行示例
```python
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
```
在上面的示例中，BabyAGI被初始化并赋予一个目标：为旧金山今天编写一个天气预报。然后，它开始执行任务，创建新任务，优先排序任务，并存储执行结果。
### 依赖库
- `langchain`
- `pydantic`
- `faiss-cpu` 或 `faiss-gpu`（用于向量搜索）
### 注意事项
- 项目需要有效的API密钥来访问OpenAI模型。
- 项目可能需要进一步的测试和优化，以确保稳定性和性能。
- 项目需要添加自己的.env环境，配置对应的OPEN_API_KEY