"""
DeepSeek模型客户端实现
"""
import asyncio
import requests
from typing import Dict, Any, Optional, List
import logging

from .base_client import BaseClient


class DeepSeekClient(BaseClient):
    """
    DeepSeek模型客户端实现
    
    支持调用DeepSeek API进行文本生成、对话等操作
    """
    
    def _initialize(self):
        """
        初始化DeepSeek客户端
        
        设置API基础URL、认证信息等
        """
        # 设置日志
        self.logger = logging.getLogger('DeepSeekClient')
        
        # 获取配置信息
        self.api_key = self.model_config.get('api_key')
        self.base_url = self.model_config.get('base_url', 'https://api.deepseek.com')
        self.model_name = self.model_config.get('model_name', 'deepseek-chat')
        
        # 设置默认参数
        self.default_params = {
            'temperature': self.model_config.get('temperature', 0.7),
            'max_tokens': self.model_config.get('max_tokens', 2048),
            'top_p': self.model_config.get('top_p', 0.9),
        }
        
        # 验证配置
        if not self.validate_config():
            self.logger.warning("DeepSeek configuration validation failed")
    
    def _get_required_config_fields(self) -> List[str]:
        """
        获取必要的配置字段
        
        Returns:
            List[str]: 必要的配置字段列表
        """
        return ['api_key']
    
    async def generate_response(self, 
                               prompt: str, 
                               system_prompt: Optional[str] = None, 
                               **kwargs) -> Dict[str, Any]:
        """
        生成DeepSeek模型响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        try:
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            # 合并参数
            params = {**self.default_params, **kwargs}
            
            # 调用API
            response = await self._async_request(
                endpoint='/chat/completions',
                method='POST',
                data={
                    'model': self.model_name,
                    'messages': messages,
                    **params
                }
            )
            
            # 处理响应
            if response.get('error'):
                return response
            
            # 提取响应内容
            if response.get('choices') and len(response['choices']) > 0:
                return {
                    'success': True,
                    'content': response['choices'][0]['message']['content'],
                    'model': self.model_name,
                    'raw_response': response
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid response from DeepSeek API'
                }
                
        except Exception as e:
            self.logger.error(f"Error generating response from DeepSeek: {str(e)}")
            return self.handle_error(e)
    
    def create_completion(self, 
                         messages: List[Dict[str, str]], 
                         **kwargs) -> Dict[str, Any]:
        """
        创建DeepSeek模型完成
        
        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含完成内容的字典
        """
        try:
            # 合并参数
            params = {**self.default_params, **kwargs}
            
            # 同步调用API
            response = requests.post(
                url=f"{self.base_url}/chat/completions",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                },
                json={
                    'model': self.model_name,
                    'messages': messages,
                    **params
                }
            )
            
            # 检查响应状态
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API returned status code {response.status_code}',
                    'error_message': response.text
                }
            
            # 解析响应
            result = response.json()
            
            # 提取内容
            if result.get('choices') and len(result['choices']) > 0:
                return {
                    'success': True,
                    'content': result['choices'][0]['message']['content'],
                    'model': self.model_name,
                    'raw_response': result
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid response from DeepSeek API'
                }
                
        except Exception as e:
            self.logger.error(f"Error creating completion with DeepSeek: {str(e)}")
            return self.handle_error(e)
    
    async def _async_request(self, endpoint: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步请求方法
        
        Args:
            endpoint: API端点
            method: HTTP方法
            data: 请求数据
            
        Returns:
            Dict: API响应
        """
        try:
            # 使用线程池执行同步请求，避免阻塞事件循环
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,  # 使用默认线程池
                self._sync_request,  # 要执行的同步函数
                endpoint, method, data  # 函数参数
            )
            return response
        except Exception as e:
            self.logger.error(f"Async request failed: {str(e)}")
            return self.handle_error(e)
    
    def _sync_request(self, endpoint: str, method: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步请求方法，被_async_request调用
        
        Args:
            endpoint: API端点
            method: HTTP方法
            data: 请求数据
            
        Returns:
            Dict: API响应
        """
        try:
            # 发送请求
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data
            )
            
            # 检查响应状态
            if response.status_code != 200:
                return {
                    'error': True,
                    'status_code': response.status_code,
                    'message': response.text
                }
            
            # 返回解析后的JSON
            return response.json()
        except Exception as e:
            return self.handle_error(e)