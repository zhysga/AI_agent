"""
LLM智能体实现
"""
import asyncio
from typing import Dict, Any, Optional, List, Union
import logging
import json

from .base_agent import BaseAgent
from ..model_clients import BaseClient, DeepSeekClient, DoubaoClient, QwenClient


class LLMAgent(BaseAgent):
    """
    基于大语言模型的智能体实现
    
    支持与DeepSeek、Doubao、Qwen等模型进行交互
    """
    
    def _initialize(self):
        """
        初始化LLM智能体
        
        设置模型客户端、系统提示词等
        """
        # 获取模型类型和配置
        self.model_type = self.agent_config.get('model_type', 'deepseek')
        self.model_config = self.agent_config.get('model_config', {})
        self.system_prompt = self.agent_config.get('system_prompt', '')
        
        # 初始化模型客户端
        self.model_client: Optional[BaseClient] = None
        self._init_model_client()
        
        # 设置默认参数
        self.default_generation_params = {
            'temperature': self.agent_config.get('temperature', 0.7),
            'max_tokens': self.agent_config.get('max_tokens', 2048),
        }
        
        # 更新状态
        if self.model_client and self.model_client.validate_config():
            self.set_state({
                'initialized': True,
                'ready': True,
                'model_type': self.model_type
            })
        else:
            self.set_state({
                'initialized': True,
                'ready': False,
                'error': 'Invalid model configuration'
            })
    
    def _init_model_client(self):
        """
        初始化模型客户端
        
        根据model_type创建相应的模型客户端实例
        """
        try:
            # 根据模型类型创建客户端
            if self.model_type.lower() == 'deepseek':
                self.model_client = DeepSeekClient(self.model_config)
            elif self.model_type.lower() == 'doubao':
                self.model_client = DoubaoClient(self.model_config)
            elif self.model_type.lower() == 'qwen':
                self.model_client = QwenClient(self.model_config)
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
            
            # 验证客户端配置
            if not self.model_client.validate_config():
                self.logger.warning(f"Model client for {self.model_type} has invalid configuration")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize model client: {str(e)}")
            self.set_state({
                'error': f'Failed to initialize model client: {str(e)}'
            })
    
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理消息
        
        Args:
            message: 要处理的消息
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 检查智能体是否就绪
            if not self.state.get('ready'):
                return {
                    'success': False,
                    'error': 'Agent not ready'
                }
            
            # 检查消息内容
            message_content = message.get('content')
            if not message_content:
                return {
                    'success': False,
                    'error': 'No message content provided'
                }
            
            # 添加到消息历史
            self.add_message_to_history(message)
            
            # 生成响应
            response = await self.generate_response(message_content)
            
            # 如果成功，将响应添加到消息历史
            if response.get('success'):
                # 构建响应消息
                response_message = {
                    'role': 'assistant',
                    'content': response.get('content', ''),
                    'sender': self.agent_name,
                    'related_to': message.get('message_id')
                }
                
                # 添加到历史记录
                self.add_message_to_history(response_message)
                
                # 返回结果
                return {
                    'success': True,
                    'response': response_message,
                    'raw_response': response
                }
            
            # 返回错误
            return response
            
        except Exception as e:
            return self.handle_error(e)
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成模型响应
        
        Args:
            prompt: 用户提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        try:
            # 检查智能体是否就绪
            if not self.state.get('ready') or not self.model_client:
                return {
                    'success': False,
                    'error': 'Agent not ready or model client not initialized'
                }
            
            # 合并参数
            params = {**self.default_generation_params, **kwargs}
            
            # 生成响应
            response = await self.model_client.generate_response(
                prompt=prompt,
                system_prompt=self.system_prompt,
                **params
            )
            
            # 处理响应
            if response.get('success'):
                return {
                    'success': True,
                    'content': response.get('content'),
                    'model': self.model_type,
                    'raw_response': response
                }
            else:
                # 添加错误信息到状态
                error_msg = response.get('error', 'Unknown error')
                self.set_state({
                    'error': error_msg
                })
                
                return {
                    'success': False,
                    'error': error_msg,
                    'model': self.model_type
                }
                
        except Exception as e:
            return self.handle_error(e)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 包含模型信息的字典
        """
        if self.model_client:
            return self.model_client.get_model_info()
        return {
            'model_type': self.model_type,
            'error': 'Model client not initialized'
        }
    
    def set_system_prompt(self, system_prompt: str):
        """
        设置系统提示词
        
        Args:
            system_prompt: 新的系统提示词
        """
        self.system_prompt = system_prompt
        self.logger.info(f"System prompt updated for {self.agent_name}")
    
    def update_model_config(self, new_config: Dict[str, Any]):
        """
        更新模型配置
        
        Args:
            new_config: 新的模型配置
        """
        # 合并新配置
        self.model_config.update(new_config)
        
        # 重新初始化模型客户端
        self._init_model_client()
        
        # 更新状态
        if self.model_client and self.model_client.validate_config():
            self.set_state({
                'ready': True,
                'error': None
            })
        else:
            self.set_state({
                'ready': False,
                'error': 'Invalid model configuration after update'
            })
    
    def create_completion(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        创建模型完成（同步方法）
        
        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含完成内容的字典
        """
        try:
            # 检查智能体是否就绪
            if not self.state.get('ready') or not self.model_client:
                return {
                    'success': False,
                    'error': 'Agent not ready or model client not initialized'
                }
            
            # 合并参数
            params = {**self.default_generation_params, **kwargs}
            
            # 创建完成
            result = self.model_client.create_completion(
                messages=messages,
                **params
            )
            
            # 处理结果
            if result.get('success'):
                # 构建响应消息
                response_message = {
                    'role': 'assistant',
                    'content': result.get('content', ''),
                    'sender': self.agent_name
                }
                
                # 添加到历史记录
                self.add_message_to_history(response_message)
                
                return {
                    'success': True,
                    'response': response_message,
                    'raw_response': result
                }
            
            # 返回错误
            return result
            
        except Exception as e:
            return self.handle_error(e)
    
    async def generate_with_tools(self, prompt: str, tools: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        使用工具生成响应
        
        Args:
            prompt: 用户提示词
            tools: 可用工具列表
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        # 实现工具调用的逻辑
        # 这是一个高级功能，需要模型支持function calling
        try:
            # 构建带工具信息的系统提示词
            tool_system_prompt = self.system_prompt
            if tools:
                tool_description = "你可以使用以下工具来帮助你回答问题：\n"
                for tool in tools:
                    tool_description += f"- {tool.get('name')}: {tool.get('description')}\n"
                tool_description += "如果需要使用工具，请返回JSON格式的调用请求。"
                tool_system_prompt = f"{self.system_prompt}\n\n{tool_description}"
            
            # 生成响应
            response = await self.model_client.generate_response(
                prompt=prompt,
                system_prompt=tool_system_prompt,
                **kwargs
            )
            
            # 处理响应
            if response.get('success'):
                content = response.get('content', '')
                
                # 尝试解析是否包含工具调用
                try:
                    tool_call = json.loads(content)
                    if isinstance(tool_call, dict) and 'tool_name' in tool_call:
                        # 这是一个工具调用请求
                        return {
                            'success': True,
                            'content': content,
                            'tool_call': tool_call,
                            'model': self.model_type
                        }
                except json.JSONDecodeError:
                    # 不是有效的JSON，作为普通响应返回
                    pass
                
                return {
                    'success': True,
                    'content': content,
                    'model': self.model_type
                }
            
            return response
            
        except Exception as e:
            return self.handle_error(e)