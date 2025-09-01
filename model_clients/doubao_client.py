"""
Doubao模型客户端实现
"""
import asyncio
import requests
from typing import Dict, Any, Optional, List
import logging
import json

from .base_client import BaseClient


class DoubaoClient(BaseClient):
    """
    Doubao模型客户端实现
    
    支持调用百度文心一言API进行文本生成、对话等操作
    """
    
    def _initialize(self):
        """
        初始化Doubao客户端
        
        设置API基础URL、认证信息等
        """
        # 设置日志
        self.logger = logging.getLogger('DoubaoClient')
        
        # 获取配置信息
        self.api_key = self.model_config.get('api_key')
        self.secret_key = self.model_config.get('secret_key')
        self.base_url = self.model_config.get('base_url', 'https://aip.baidubce.com')
        self.model_name = self.model_config.get('model_name', 'ERNIE-Bot-4')
        
        # 设置默认参数
        self.default_params = {
            'temperature': self.model_config.get('temperature', 0.7),
            'top_p': self.model_config.get('top_p', 0.95),
            'penalty_score': self.model_config.get('penalty_score', 1.0),
            'max_output_tokens': self.model_config.get('max_output_tokens', 2048),
        }
        
        # 初始化访问令牌
        self.access_token = None
        
        # 验证配置
        if not self.validate_config():
            self.logger.warning("Doubao configuration validation failed")
        else:
            # 尝试获取访问令牌
            self._get_access_token()
    
    def _get_required_config_fields(self) -> List[str]:
        """
        获取必要的配置字段
        
        Returns:
            List[str]: 必要的配置字段列表
        """
        return ['api_key', 'secret_key']
    
    def _get_access_token(self) -> Optional[str]:
        """
        获取百度AI平台的访问令牌
        
        Returns:
            Optional[str]: 访问令牌，如果获取失败则返回None
        """
        try:
            # 构建获取访问令牌的请求
            url = f"{self.base_url}/oauth/2.0/token"
            params = {
                'grant_type': 'client_credentials',
                'client_id': self.api_key,
                'client_secret': self.secret_key
            }
            
            response = requests.get(url=url, params=params)
            result = response.json()
            
            if 'access_token' in result:
                self.access_token = result['access_token']
                self.logger.info("Successfully obtained Doubao access token")
                return self.access_token
            else:
                self.logger.error(f"Failed to get access token: {result}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting access token: {str(e)}")
            return None
    
    async def generate_response(self, 
                               prompt: str, 
                               system_prompt: Optional[str] = None, 
                               **kwargs) -> Dict[str, Any]:
        """
        生成Doubao模型响应
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        try:
            # 检查访问令牌
            if not self.access_token:
                self._get_access_token()
                if not self.access_token:
                    return {
                        'success': False,
                        'error': 'Failed to get access token'
                    }
            
            # 构建消息列表
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            # 合并参数
            params = {**self.default_params, **kwargs}
            
            # 调用API
            response = await self._async_request(
                endpoint='/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions',
                method='POST',
                data={
                    'model': self.model_name,
                    'messages': messages,
                    **params
                }
            )
            
            # 处理响应
            if response.get('error'):
                # 检查是否是令牌过期
                if response.get('status_code') == 401:
                    self.logger.info("Access token expired, refreshing...")
                    self.access_token = None
                    self._get_access_token()
                    # 重新尝试请求
                    if self.access_token:
                        response = await self._async_request(
                            endpoint='/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions',
                            method='POST',
                            data={
                                'model': self.model_name,
                                'messages': messages,
                                **params
                            }
                        )
                    else:
                        return {'success': False, 'error': 'Failed to refresh access token'}
                else:
                    return response
            
            # 提取响应内容
            if response.get('result'):
                return {
                    'success': True,
                    'content': response['result'],
                    'model': self.model_name,
                    'raw_response': response
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid response from Doubao API',
                    'raw_response': response
                }
                
        except Exception as e:
            self.logger.error(f"Error generating response from Doubao: {str(e)}")
            return self.handle_error(e)
    
    def create_completion(self, 
                         messages: List[Dict[str, str]], 
                         **kwargs) -> Dict[str, Any]:
        """
        创建Doubao模型完成
        
        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含完成内容的字典
        """
        try:
            # 检查访问令牌
            if not self.access_token:
                self._get_access_token()
                if not self.access_token:
                    return {
                        'success': False,
                        'error': 'Failed to get access token'
                    }
            
            # 合并参数
            params = {**self.default_params, **kwargs}
            
            # 同步调用API
            url = f"{self.base_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={self.access_token}"
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(
                url=url,
                headers=headers,
                json={
                    'model': self.model_name,
                    'messages': messages,
                    **params
                }
            )
            
            # 检查响应状态
            if response.status_code != 200:
                # 尝试刷新令牌
                if response.status_code == 401:
                    self.logger.info("Access token expired, refreshing...")
                    self.access_token = None
                    self._get_access_token()
                    if self.access_token:
                        url = f"{self.base_url}/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={self.access_token}"
                        response = requests.post(
                            url=url,
                            headers=headers,
                            json={
                                'model': self.model_name,
                                'messages': messages,
                                **params
                            }
                        )
                    else:
                        return {'success': False, 'error': 'Failed to refresh access token'}
                else:
                    return {
                        'success': False,
                        'error': f'API returned status code {response.status_code}',
                        'error_message': response.text
                    }
            
            # 解析响应
            result = response.json()
            
            # 提取内容
            if result.get('result'):
                return {
                    'success': True,
                    'content': result['result'],
                    'model': self.model_name,
                    'raw_response': result
                }
            else:
                return {
                    'success': False,
                    'error': 'No valid response from Doubao API',
                    'raw_response': result
                }
                
        except Exception as e:
            self.logger.error(f"Error creating completion with Doubao: {str(e)}")
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
            # 确保有访问令牌
            if not self.access_token:
                self._get_access_token()
                if not self.access_token:
                    return {'error': True, 'message': 'No access token available'}
            
            # 发送请求
            url = f"{self.base_url}{endpoint}?access_token={self.access_token}"
            headers = {'Content-Type': 'application/json'}
            
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