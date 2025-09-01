"""
简单的智能体示例（使用回退机制）

展示如何使用FallbackLLMClient创建智能体，支持API回退机制
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


class SimpleAgent:
    """简单的智能体类，使用回退机制"""
    
    def __init__(self, name: str = "chat_agent", system_prompt: str = "你是一个有用的助手"):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = FallbackLLMClient(project_dir=os.getcwd())
    
    def process_message(self, user_input: str) -> str:
        """处理用户消息"""
        # 构建完整的对话提示
        full_prompt = f"{self.system_prompt}\n\n用户: {user_input}\n助手: "
        
        # 使用回退机制生成回复
        try:
            result = self.llm_client._generate_single(full_prompt, max_tokens=2048, temperature=0.7)
            return result[0]  # 返回生成的文本
        except Exception as e:
            logger.error(f"生成回复时出错: {e}")
            return "抱歉，我暂时无法回答这个问题。"


def main():
    """
    主函数，展示如何使用回退机制的智能体
    """
    # 加载环境变量
    load_dotenv()
    
    # 创建智能体
    agent = SimpleAgent(
        name="chat_agent",
        system_prompt="你是一个有用的助手，可以回答各种问题。请用简洁明了的语言回答用户的问题。"
    )
    
    print("已创建支持回退机制的智能体，开始对话 (输入'退出'结束对话):")
    print("回退顺序: deepseek → doubao → qwen")
    print("=" * 50)
    
    # 进行对话
    while True:
        try:
            # 获取用户输入
            user_input = input("你: ")
            
            # 检查是否退出
            if user_input.lower() in ["退出", "quit", "exit", "bye"]:
                print("再见!")
                # 显示调用统计
                stats = agent.llm_client.get_call_statistics()
                print(f"\n对话统计：")
                print(f"总调用次数: {stats.get('total_calls', 0)}")
                print(f"成功调用: {stats.get('successful_calls', 0)}")
                print(f"失败调用: {stats.get('failed_calls', 0)}")
                print(f"API使用情况: {stats.get('api_usage', {})}")
                break
            
            # 发送消息给智能体
            response = agent.process_message(user_input)
            
            # 输出智能体的回复
            print(f"智能体: {response}")
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


if __name__ == "__main__":
    main()