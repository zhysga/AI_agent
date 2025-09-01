"""
智能体基类，定义所有智能体必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Callable
import uuid
import logging


class BaseAgent(ABC):
    """
    智能体的抽象基类，定义统一的接口规范
    
    所有智能体都应该继承此类并实现相应的方法
    """
    
    def __init__(self, agent_config: Dict[str, Any]):
        """
        初始化智能体
        
        Args:
            agent_config: 智能体配置信息
        """
        # 设置唯一ID
        self.agent_id = str(uuid.uuid4())
        self.agent_config = agent_config
        self.agent_name = agent_config.get('name', f'Agent_{self.agent_id[:8]}')
        self.logger = logging.getLogger(self.agent_name)
        
        # 初始化状态
        self.state = {
            'initialized': False,
            'ready': False,
            'error': None
        }
        
        # 初始化消息历史
        self.message_history: List[Dict[str, Any]] = []
        
        # 初始化回调函数
        self.on_message_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []
        self.on_state_change_callbacks: List[Callable] = []
        
        # 执行初始化
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """
        初始化智能体，子类必须实现
        
        用于设置智能体的初始状态、加载配置等
        """
        pass
    
    @abstractmethod
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理消息的异步方法
        
        Args:
            message: 要处理的消息
            
        Returns:
            Dict: 处理结果
        """
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成响应的异步方法
        
        Args:
            prompt: 提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        pass
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取智能体信息
        
        Returns:
            Dict: 包含智能体信息的字典
        """
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'agent_type': self.__class__.__name__,
            'state': self.state
        }
    
    def add_message_to_history(self, message: Dict[str, Any]):
        """
        添加消息到历史记录
        
        Args:
            message: 要添加的消息
        """
        # 确保消息包含必要字段
        if 'message_id' not in message:
            message['message_id'] = str(uuid.uuid4())
        
        if 'timestamp' not in message:
            import datetime
            message['timestamp'] = datetime.datetime.now().isoformat()
        
        if 'sender' not in message:
            message['sender'] = self.agent_name
        
        # 添加到历史记录
        self.message_history.append(message)
        
        # 触发回调
        self._trigger_on_message_callbacks(message)
    
    def get_message_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取消息历史记录
        
        Args:
            limit: 返回的最大消息数量
            
        Returns:
            List[Dict]: 消息历史记录
        """
        if limit is not None:
            return self.message_history[-limit:]
        return self.message_history
    
    def clear_message_history(self):
        """
        清除消息历史记录
        """
        self.message_history = []
    
    def set_state(self, new_state: Dict[str, Any]):
        """
        设置智能体状态
        
        Args:
            new_state: 新的状态
        """
        old_state = self.state.copy()
        self.state.update(new_state)
        
        # 触发状态变化回调
        if old_state != self.state:
            self._trigger_on_state_change_callbacks(old_state, self.state)
    
    def register_on_message_callback(self, callback: Callable):
        """
        注册消息回调函数
        
        Args:
            callback: 回调函数
        """
        if callback not in self.on_message_callbacks:
            self.on_message_callbacks.append(callback)
    
    def register_on_error_callback(self, callback: Callable):
        """
        注册错误回调函数
        
        Args:
            callback: 回调函数
        """
        if callback not in self.on_error_callbacks:
            self.on_error_callbacks.append(callback)
    
    def register_on_state_change_callback(self, callback: Callable):
        """
        注册状态变化回调函数
        
        Args:
            callback: 回调函数
        """
        if callback not in self.on_state_change_callbacks:
            self.on_state_change_callbacks.append(callback)
    
    def _trigger_on_message_callbacks(self, message: Dict[str, Any]):
        """
        触发消息回调函数
        
        Args:
            message: 消息
        """
        for callback in self.on_message_callbacks:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Error in message callback: {str(e)}")
    
    def _trigger_on_error_callbacks(self, error: Exception):
        """
        触发错误回调函数
        
        Args:
            error: 异常对象
        """
        for callback in self.on_error_callbacks:
            try:
                callback(error)
            except Exception as e:
                self.logger.error(f"Error in error callback: {str(e)}")
    
    def _trigger_on_state_change_callbacks(self, old_state: Dict[str, Any], new_state: Dict[str, Any]):
        """
        触发状态变化回调函数
        
        Args:
            old_state: 旧状态
            new_state: 新状态
        """
        for callback in self.on_state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {str(e)}")
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        处理智能体执行过程中的错误
        
        Args:
            error: 异常对象
            
        Returns:
            Dict: 包含错误信息的字典
        """
        # 更新状态
        self.set_state({
            'error': {
                'type': type(error).__name__,
                'message': str(error)
            }
        })
        
        # 触发错误回调
        self._trigger_on_error_callbacks(error)
        
        # 记录日志
        self.logger.error(f"Error in {self.agent_name}: {str(error)}")
        
        return {
            'error': True,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
    
    def validate_config(self) -> bool:
        """
        验证智能体配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        # 基础验证，子类可以扩展
        if not self.agent_config:
            return False
        return True