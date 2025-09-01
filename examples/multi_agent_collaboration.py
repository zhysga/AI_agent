"""
多智能体协作示例（使用回退机制）

展示如何使用FallbackLLMClient创建多个智能体并让它们协作完成任务
"""
import os
import sys
import logging
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入回退LLM客户端
from fallback_llm import FallbackLLMClient


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMAgent:
    """简化版的LLM智能体，使用回退机制"""
    
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = FallbackLLMClient(project_dir=os.getcwd())
    
    def process_message(self, user_input: str) -> str:
        """处理用户消息"""
        full_prompt = f"{self.system_prompt}\n\n用户问题: {user_input}\n请提供你的回答:"
        
        try:
            result = self.llm_client._generate_single(full_prompt, max_tokens=2048, temperature=0.7)
            return result[0]
        except Exception as e:
            logger.error(f"{self.name} 生成回复时出错: {e}")
            return f"抱歉，{self.name}暂时无法回答这个问题。"


class ToolAgent:
    """简化版的工具智能体"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def process_message(self, instruction: str) -> str:
        """处理工具调用指令"""
        # 这里简化实现，实际应用中应该有更复杂的工具调用逻辑
        return f"工具代理 {self.name} 收到指令: {instruction}。这是一个简化的工具调用响应。"


class UserAgent:
    """用户智能体"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description


class MultiAgentSystem:
    """
    多智能体系统类
    
    管理多个智能体并协调它们的协作
    """
    
    def __init__(self):
        """
        初始化多智能体系统
        """
        # 创建工具智能体
        self.tool_agent = ToolAgent(
            name="tool_agent",
            description="负责提供各种工具功能，帮助其他智能体完成任务"
        )
        
        # 创建专家智能体
        # 1. 代码专家
        self.code_expert = LLMAgent(
            name="code_expert",
            system_prompt="你是一名资深的Python程序员，擅长解决各种编程问题和编写高质量的代码。当遇到编程相关的问题时，你能够提供专业的指导和解决方案。"
        )
        
        # 2. 数据分析专家
        self.data_analyst = LLMAgent(
            name="data_analyst",
            system_prompt="你是一名数据分析师，擅长从数据中提取有价值的信息，并提供深入的分析和见解。当遇到数据分析相关的任务时，你能够提供专业的帮助。"
        )
        
        # 3. 研究专家
        self.researcher = LLMAgent(
            name="researcher",
            system_prompt="你是一名研究专家，擅长查找和分析各种信息，提供全面的研究结果。当需要收集信息或进行深入研究时，你能够提供专业的支持。"
        )
        
        # 4. 协调器智能体
        self.coordinator = LLMAgent(
            name="coordinator",
            system_prompt="你是多智能体系统的协调器，负责理解用户的问题，分配任务给合适的专家智能体，并综合专家们的意见给出最终的回答。当遇到复杂问题时，你能够组织多个专家智能体协作解决。"
        )
        
        # 5. 用户智能体
        self.user_agent = UserAgent(
            name="user",
            description="系统的用户，提供问题和反馈"
        )
        
        # 存储对话历史
        self.conversation_history = []
        
        logger.info("MultiAgentSystem initialized successfully")
    
    def process_query(self, query: str) -> str:
        """
        处理用户查询
        
        Args:
            query: 用户的问题
            
        Returns:
            str: 系统的回答
        """
        try:
            # 记录用户查询
            self.conversation_history.append({"role": "user", "name": "user", "content": query})
            
            # 让协调器理解问题并分配任务
            coordinator_prompt = f"""
            你是多智能体系统的协调器。请分析用户的问题，并根据问题的性质决定是否需要其他专家智能体的帮助。
            
            现有专家智能体：
            1. code_expert: 擅长编程问题和代码编写
            2. data_analyst: 擅长数据分析和解读
            3. researcher: 擅长信息收集和研究
            4. tool_agent: 提供各种工具功能
            
            用户问题：{query}
            
            请提供你的分析和决策。如果你需要咨询专家，请明确指出咨询哪个专家以及咨询的问题。
            如果不需要咨询专家，你可以直接回答用户的问题。
            """
            
            coordinator_response = self.coordinator.process_message(coordinator_prompt)
            self.conversation_history.append({"role": "assistant", "name": "coordinator", "content": coordinator_response})
            
            # 检查是否需要咨询专家
            expert_responses = {}
            
            # 检查是否需要代码专家
            if "code_expert" in coordinator_response:
                code_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                code_response = self.code_expert.process_message(code_prompt)
                expert_responses["code_expert"] = code_response
                self.conversation_history.append({"role": "assistant", "name": "code_expert", "content": code_response})
            
            # 检查是否需要数据分析专家
            if "data_analyst" in coordinator_response:
                data_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                data_response = self.data_analyst.process_message(data_prompt)
                expert_responses["data_analyst"] = data_response
                self.conversation_history.append({"role": "assistant", "name": "data_analyst", "content": data_response})
            
            # 检查是否需要研究专家
            if "researcher" in coordinator_response:
                research_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                research_response = self.researcher.process_message(research_prompt)
                expert_responses["researcher"] = research_response
                self.conversation_history.append({"role": "assistant", "name": "researcher", "content": research_response})
            
            # 检查是否需要使用工具
            if "tool_agent" in coordinator_response:
                # 提取工具调用信息
                import re
                tool_match = re.search(r"tool_agent\s*:\s*([^\n]+)", coordinator_response)
                if tool_match:
                    tool_instruction = tool_match.group(1)
                    # 这里简化处理，实际应用中可能需要更复杂的工具调用解析
                    try:
                        # 尝试解析工具调用参数
                        # 注意：这是一个简化的实现，实际应用中可能需要更复杂的解析
                        tool_response = self.tool_agent.process_message(tool_instruction)
                        expert_responses["tool_agent"] = tool_response
                        self.conversation_history.append({"role": "assistant", "name": "tool_agent", "content": tool_response})
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        expert_responses["tool_agent"] = f"工具执行出错: {str(e)}"
            
            # 如果有专家回复，让协调器综合专家意见给出最终回答
            if expert_responses:
                final_prompt = f"""
                你已经咨询了以下专家，现在请综合他们的意见，给出用户问题的最终回答：
                
                用户问题：{query}
                
                专家意见：
                {"\n".join([f"{name}: {response}" for name, response in expert_responses.items()])}
                
                请给出全面、准确的回答。
                """
                
                final_response = self.coordinator.process_message(final_prompt)
            else:
                # 如果没有咨询专家，协调器的回复就是最终回答
                final_response = coordinator_response
            
            # 记录最终回答
            self.conversation_history.append({"role": "assistant", "name": "coordinator", "content": final_response})
            
            return final_response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"处理查询时发生错误: {str(e)}"
    
    def start_conversation(self):
        """
        开始与用户的对话
        """
        print("多智能体协作系统已启动，开始对话 (输入'退出'结束对话):")
        print("=" * 50)
        print("你可以问我任何问题，我会组织多个专家智能体为你提供帮助。")
        print("=" * 50)
        print("回退顺序: deepseek → doubao → qwen")
        print("=" * 50)
        
        while True:
            try:
                # 获取用户输入
                user_input = input("你: ")
                
                # 检查是否退出
                if user_input.lower() in ["退出", "quit", "exit", "bye"]:
                    print("再见!")
                    # 显示调用统计
                    stats = self.coordinator.llm_client.get_call_statistics()
                    print(f"\n对话统计：")
                    print(f"总调用次数: {stats.get('total_calls', 0)}")
                    print(f"成功调用: {stats.get('successful_calls', 0)}")
                    print(f"失败调用: {stats.get('failed_calls', 0)}")
                    print(f"API使用情况: {stats.get('api_usage', {})}")
                    break
                
                # 处理用户查询
                print("正在处理你的问题，请稍候...")
                response = self.process_query(user_input)
                
                # 输出系统回复
                print(f"系统: {response}")
                print("=" * 50)
                
            except KeyboardInterrupt:
                # 处理Ctrl+C中断
                print("\n对话已中断。再见!")
                break
            except Exception as e:
                # 处理其他错误
                print(f"发生错误: {e}")
                logger.error(f"Error in conversation: {e}")
                print("继续对话或输入'退出'结束。")
                print("=" * 50)


# 自定义工具示例
def custom_tool_example(text: str, repeat: int = 2) -> str:
    """
    自定义工具示例
    
    将文本重复指定的次数
    
    Args:
        text: 要重复的文本
        repeat: 重复次数
        
    Returns:
        str: 重复后的文本
    """
    return text * repeat


# 演示如何扩展多智能体系统
class ExtendedMultiAgentSystem(MultiAgentSystem):
    """
    扩展的多智能体系统类
    
    在基础多智能体系统上添加更多专家智能体
    """
    
    def __init__(self):
        """
        初始化扩展的多智能体系统
        """
        # 调用父类初始化
        super().__init__()
        
        # 添加创意写作专家
        self.writing_expert = LLMAgent(
            name="writing_expert",
            system_prompt="你是一名创意写作专家，擅长撰写各种文体的文章、故事、诗歌等。当需要创作内容时，你能够提供专业的写作帮助。"
        )
        
        # 添加调试专家
        self.debug_expert = LLMAgent(
            name="debug_expert",
            system_prompt="你是一名调试专家，擅长分析和解决各种程序错误和异常。当遇到程序问题时，你能够提供专业的调试建议和解决方案。"
        )
        
        logger.info("ExtendedMultiAgentSystem initialized successfully")
    
    # 重写process_query方法以支持新的专家智能体
    def process_query(self, query: str) -> str:
        """
        处理用户查询（支持新的专家智能体）
        """
        try:
            # 记录用户查询
            self.conversation_history.append({"role": "user", "name": "user", "content": query})
            
            # 更新协调器提示以包含新的专家智能体
            coordinator_prompt = f"""
            你是多智能体系统的协调器。请分析用户的问题，并根据问题的性质决定是否需要其他专家智能体的帮助。
            
            现有专家智能体：
            1. code_expert: 擅长编程问题和代码编写
            2. data_analyst: 擅长数据分析和解读
            3. researcher: 擅长信息收集和研究
            4. tool_agent: 提供各种工具功能
            5. writing_expert: 擅长创意写作和文案创作
            
            用户问题：{query}
            
            请提供你的分析和决策。如果你需要咨询专家，请明确指出咨询哪个专家以及咨询的问题。
            如果不需要咨询专家，你可以直接回答用户的问题。
            """
            
            coordinator_response = self.coordinator.process_message(coordinator_prompt)
            self.conversation_history.append({"role": "assistant", "name": "coordinator", "content": coordinator_response})
            
            # 检查是否需要咨询专家
            expert_responses = {}
            
            # 检查是否需要代码专家
            if "code_expert" in coordinator_response:
                code_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                code_response = self.code_expert.process_message(code_prompt)
                expert_responses["code_expert"] = code_response
                self.conversation_history.append({"role": "assistant", "name": "code_expert", "content": code_response})
            
            # 检查是否需要数据分析专家
            if "data_analyst" in coordinator_response:
                data_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                data_response = self.data_analyst.process_message(data_prompt)
                expert_responses["data_analyst"] = data_response
                self.conversation_history.append({"role": "assistant", "name": "data_analyst", "content": data_response})
            
            # 检查是否需要研究专家
            if "researcher" in coordinator_response:
                research_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                research_response = self.researcher.process_message(research_prompt)
                expert_responses["researcher"] = research_response
                self.conversation_history.append({"role": "assistant", "name": "researcher", "content": research_response})
            
            # 检查是否需要写作专家
            if "writing_expert" in coordinator_response:
                writing_prompt = f"用户的问题是：{query}\n协调器需要你提供的帮助是：{coordinator_response}"
                writing_response = self.writing_expert.process_message(writing_prompt)
                expert_responses["writing_expert"] = writing_response
                self.conversation_history.append({"role": "assistant", "name": "writing_expert", "content": writing_response})
            
            # 检查是否需要使用工具
            if "tool_agent" in coordinator_response:
                # 提取工具调用信息
                import re
                tool_match = re.search(r"tool_agent\s*:\s*([^\n]+)", coordinator_response)
                if tool_match:
                    tool_instruction = tool_match.group(1)
                    # 这里简化处理，实际应用中可能需要更复杂的工具调用解析
                    try:
                        tool_response = self.tool_agent.process_message(tool_instruction)
                        expert_responses["tool_agent"] = tool_response
                        self.conversation_history.append({"role": "assistant", "name": "tool_agent", "content": tool_response})
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        expert_responses["tool_agent"] = f"工具执行出错: {str(e)}"
            
            # 如果有专家回复，让协调器综合专家意见给出最终回答
            if expert_responses:
                final_prompt = f"""
                你已经咨询了以下专家，现在请综合他们的意见，给出用户问题的最终回答：
                
                用户问题：{query}
                
                专家意见：
                {"\n".join([f"{name}: {response}" for name, response in expert_responses.items()])}
                
                请给出全面、准确的回答。
                """
                
                final_response = self.coordinator.process_message(final_prompt)
            else:
                # 如果没有咨询专家，协调器的回复就是最终回答
                final_response = coordinator_response
            
            # 记录最终回答
            self.conversation_history.append({"role": "assistant", "name": "coordinator", "content": final_response})
            
            return final_response
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"处理查询时发生错误: {str(e)}"


# 主函数

def main():
    """
    主函数，运行多智能体协作示例
    """
    print("多智能体协作系统启动选项:")
    print("1. 基础版多智能体系统")
    print("2. 扩展版多智能体系统")
    print("3. 退出")
    
    while True:
        try:
            choice = input("请选择 (1/2/3): ").strip()
            
            if choice == "1":
                system = MultiAgentSystem()
                print("已启动基础版多智能体协作系统")
                system.start_conversation()
                break
            elif choice == "2":
                system = ExtendedMultiAgentSystem()
                print("已启动扩展版多智能体协作系统")
                system.start_conversation()
                break
            elif choice == "3":
                print("再见!")
                break
            else:
                print("无效选择，请输入 1、2 或 3")
                
        except KeyboardInterrupt:
            print("\n程序已中断。再见!")
            break
        except Exception as e:
            print(f"启动系统时发生错误: {e}")
            logger.error(f"Error starting system: {e}")


if __name__ == "__main__":
    main()