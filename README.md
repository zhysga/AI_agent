# AutoGen智能Agent模板项目

## 📚 项目概述

这是一个基于AutoGen架构设计的通用智能Agent模板项目，支持DeepSeek、Doubao和Qwen等多种大语言模型API。本项目提供了完整的Agent框架，包括模型客户端、智能体实现、工具系统和示例代码，方便开发者快速构建和扩展自己的智能Agent应用。

## 🚀 快速开始

### 环境要求

- Python 3.8+ 
- 安装依赖：`pip install -r requirements.txt`

### 配置环境变量

在项目根目录创建`.env`文件，并添加以下内容（根据需要使用的模型进行配置）：

```
# DeepSeek API配置
DEEPSEEK_API_KEY=your_deepseek_api_key

# 文心一言(Doubao) API配置
DOUBAO_API_KEY=your_doubao_api_key
DOUBAO_SECRET_KEY=your_doubao_secret_key

# 通义千问(Qwen) API配置
QWEN_API_KEY=your_qwen_api_key
QWEN_API_SECRET=your_qwen_api_secret
```

### 运行示例

1. **单个智能体示例**

```bash
cd examples
python simple_agent_example.py
```

2. **多智能体协作示例**

```bash
cd examples
python multi_agent_collaboration.py
```

## 📁 项目结构

项目采用模块化设计，主要包含以下几个核心模块：

```
myPythonExample/
├── agents/              # 智能体实现
│   ├── __init__.py      # 智能体包初始化
│   ├── base_agent.py    # 智能体基类
│   ├── llm_agent.py     # LLM智能体
│   ├── tool_agent.py    # 工具智能体
│   └── user_agent.py    # 用户智能体
├── model_clients/       # 模型客户端
│   ├── __init__.py      # 模型客户端包初始化
│   ├── base_client.py   # 模型客户端基类
│   ├── deepseek_client.py # DeepSeek模型客户端
│   ├── doubao_client.py # 文心一言模型客户端
│   └── qwen_client.py   # 通义千问模型客户端
├── tools/               # 工具系统
│   ├── __init__.py      # 工具包初始化
│   ├── base_tool.py     # 工具基类
│   ├── llm_tools.py     # LLM相关工具
│   ├── web_tools.py     # Web相关工具
│   ├── system_tools.py  # 系统相关工具
│   └── tool_functions.py # 工具函数集合
├── examples/            # 示例代码
│   ├── simple_agent_example.py # 单个智能体示例
│   └── multi_agent_collaboration.py # 多智能体协作示例
├── requirements.txt     # 项目依赖
├── README.md            # 项目文档
└── prompt_records.md    # 提示词记录
```

## 🔧 核心模块详解

### 1. 模型客户端（model_clients）

模型客户端模块负责与各种大语言模型API进行交互，提供统一的接口。

- **BaseClient**: 所有模型客户端的基类，定义了通用接口和方法
- **DeepSeekClient**: DeepSeek模型的客户端实现
- **DoubaoClient**: 文心一言模型的客户端实现
- **QwenClient**: 通义千问模型的客户端实现

每个客户端都支持同步和异步请求处理，包括生成响应、创建完成等功能，并提供统一的错误处理机制。

### 2. 智能体（agents）

智能体模块实现了不同类型的智能体，负责处理用户输入、与模型交互、调用工具等。

- **BaseAgent**: 智能体的基类，提供通用功能如消息历史管理、状态管理等
- **LLMAgent**: 基于大语言模型的智能体，负责与模型交互生成响应
- **ToolAgent**: 工具智能体，负责管理和执行各种工具
- **UserAgent**: 用户智能体，模拟用户行为或处理用户输入

### 3. 工具系统（tools）

工具系统提供了丰富的工具功能，使智能体能够执行各种任务。

- **BaseTool**: 工具的基类，定义了工具的基本接口
- **ToolRegistry**: 工具注册表，用于管理和查找工具
- **各类专用工具**: 包括LLM工具、Web工具、系统工具等
- **工具函数集合**: 提供了常用的函数工具，如文本处理、文件操作、网络请求等

### 4. 示例代码（examples）

示例代码展示了如何使用本框架构建和运行智能Agent应用：

- **simple_agent_example.py**: 演示如何创建和使用单个智能体
- **multi_agent_collaboration.py**: 演示如何创建多个智能体并让它们协作完成任务

## 🛠️ 使用指南

### 创建和使用智能体

1. **初始化模型客户端**

```python
from model_clients import DeepSeekClient

client = DeepSeekClient(
    api_key="your_api_key",
    model="deepseek-chat",
    max_tokens=2048,
    temperature=0.7
)
```

2. **创建LLM智能体**

```python
from agents import LLMAgent

llm_agent = LLMAgent(
    name="my_agent",
    model_client=client,
    system_prompt="你是一名助手，能够回答各种问题。"
)
```

3. **处理消息**

```python
response = llm_agent.process_message("你好，请问今天天气如何？")
print(response)
```

### 多智能体协作

```python
from agents import LLMAgent, ToolAgent, UserAgent
from model_clients import DeepSeekClient
from tools import ToolSet

# 创建模型客户端
client = DeepSeekClient(api_key="your_api_key")

# 创建工具集合和工具智能体
tool_set = ToolSet()
tool_agent = ToolAgent(name="tool_agent", tool_set=tool_set)

# 创建多个专家智能体
code_expert = LLMAgent(name="code_expert", model_client=client)
data_analyst = LLMAgent(name="data_analyst", model_client=client)

# 实现协作逻辑
# ...
```

## 📝 扩展指南

### 添加新的模型客户端

要添加新的模型客户端，只需继承`BaseClient`类并实现必要的方法：

```python
from model_clients import BaseClient

class NewModelClient(BaseClient):
    def __init__(self, api_key, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        # 其他初始化代码
    
    async def generate_response(self, prompt, **kwargs):
        # 实现异步生成响应的逻辑
        # ...
    
    def create_completion(self, prompt, **kwargs):
        # 实现同步创建完成的逻辑
        # ...
```

### 添加新的工具

要添加新的工具，可以创建一个新的工具类或使用`FunctionTool`：

```python
from tools import FunctionTool

# 定义工具函数
def my_custom_tool(param1, param2):
    """我的自定义工具描述"""
    # 工具实现
    return f"处理结果: {param1} + {param2}"

# 创建工具实例
my_tool = FunctionTool(my_custom_tool)

# 添加到工具集合
tool_set.add_tool(my_tool)
```

### 创建新的智能体类型

要创建新的智能体类型，只需继承`BaseAgent`类并实现必要的方法：

```python
from agents import BaseAgent

class MyCustomAgent(BaseAgent):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        # 其他初始化代码
    
    def process_message(self, message, **kwargs):
        # 实现消息处理逻辑
        # ...
        return response
```

## ⚠️ 注意事项

1. **API密钥保护**：请不要将API密钥直接硬编码到代码中，应通过环境变量或配置文件管理
2. **错误处理**：使用时请注意处理可能的错误，如网络问题、API限制等
3. **性能优化**：对于大规模应用，请考虑使用异步方法和批处理请求
4. **依赖管理**：确保安装了所有必要的依赖，可以通过`requirements.txt`安装

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议。如果您有任何改进建议，请提交Pull Request或Issue。

## 📄 许可证

本项目采用MIT许可证。