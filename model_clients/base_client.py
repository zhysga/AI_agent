"""
模型客户端基类，定义所有模型客户端必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class BaseClient(ABC):
    """
    模型客户端的抽象基类，定义统一的接口规范
    
    所有模型客户端都应该继承此类并实现相应的方法
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化模型客户端
        
        Args:
            model_config: 模型配置信息，包含API密钥、模型名称等
        """
        self.model_config = model_config
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """
        初始化模型客户端，子类必须实现
        
        用于设置认证信息、创建API客户端实例等
        """
        pass
    
    @abstractmethod
    async def generate_response(self, 
                               prompt: str, 
                               system_prompt: Optional[str] = None, 
                               **kwargs) -> Dict[str, Any]:
        """
        生成模型响应的异步方法
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        pass
    
    @abstractmethod
    def create_completion(self, 
                         messages: List[Dict[str, str]], 
                         **kwargs) -> Dict[str, Any]:
        """
        创建模型完成的同步方法
        
        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含完成内容的字典
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取模型信息
        
        Returns:
            Dict: 包含模型名称、版本等信息的字典
        """
        return {
            'model_type': self.__class__.__name__,
            'model_config': self.model_config
        }
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        处理模型调用过程中的错误
        
        Args:
            error: 异常对象
            
        Returns:
            Dict: 包含错误信息的字典
        """
        return {
            'error': True,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }

    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            bool: 配置是否有效
        """
        # 基础验证，子类可以扩展
        if not self.model_config:
            return False
        
        # 检查必要的配置项
        required_fields = self._get_required_config_fields()
        for field in required_fields:
            if field not in self.model_config:
                return False
        
        return True
    
    def _get_required_config_fields(self) -> List[str]:
        """
        获取必要的配置字段
        
        Returns:
            List[str]: 必要的配置字段列表
        """
        # 基础实现，子类可以扩展
        return []