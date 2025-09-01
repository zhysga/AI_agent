"""
基础工具类定义
"""
import inspect
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic
import abc
import logging
from pydantic import BaseModel, Field, create_model, ValidationError
import json


class ToolResponse(BaseModel):
    """
    工具执行结果模型
    """
    success: bool = Field(..., description="工具执行是否成功")
    result: Any = Field(None, description="工具执行结果")
    error: Optional[str] = Field(None, description="错误信息，如果执行失败")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")
    tool_name: Optional[str] = Field(None, description="工具名称")


class BaseTool(abc.ABC):
    """
    工具的抽象基类
    
    所有自定义工具都应该继承这个类并实现相应的方法
    """
    
    def __init__(self):
        """
        初始化工具
        """
        # 工具名称，默认为类名
        self.name = self.__class__.__name__
        
        # 工具描述，从类文档字符串中提取
        self.description = inspect.getdoc(self) or ""
        
        # 输入参数模型
        self.input_schema = None
        
        # 输出参数模型
        self.output_schema = ToolResponse
        
        # 日志记录器
        self.logger = logging.getLogger(f"tool.{self.name}")
        
        # 初始化
        self._initialize()
        
        # 自动构建输入参数模型
        self._build_input_schema()
    
    @abc.abstractmethod
    def _initialize(self):
        """
        初始化工具的具体实现
        
        子类需要实现这个方法来设置工具的具体参数
        """
        pass
    
    @abc.abstractmethod
    async def _execute(self, **kwargs) -> ToolResponse:
        """
        执行工具的具体实现
        
        子类需要实现这个方法来定义工具的核心逻辑
        
        Args:
            **kwargs: 工具的输入参数
            
        Returns:
            ToolResponse: 工具执行结果
        """
        pass
    
    def _build_input_schema(self):
        """
        构建输入参数模型
        
        根据_execute方法的参数定义构建Pydantic模型
        """
        # 获取_execute方法的参数签名
        sig = inspect.signature(self._execute)
        
        # 排除self参数和*args, **kwargs等可变参数
        fields = {}
        for name, param in list(sig.parameters.items())[1:]:  # 跳过self参数
            # 处理基本类型的参数
            if param.annotation != inspect.Parameter.empty:
                # 设置字段描述
                description = f"参数 {name}"
                
                # 设置默认值
                if param.default != inspect.Parameter.empty:
                    fields[name] = (param.annotation, Field(default=param.default, description=description))
                else:
                    fields[name] = (param.annotation, Field(..., description=description))
            else:
                # 如果没有类型注解，使用Any类型
                if param.default != inspect.Parameter.empty:
                    fields[name] = (Any, Field(default=param.default, description=f"参数 {name}"))
                else:
                    fields[name] = (Any, Field(..., description=f"参数 {name}"))
        
        # 创建输入参数模型
        if fields:
            self.input_schema = create_model(
                f"{self.name}Input",
                **fields
            )
    
    def get_tool_info(self) -> Dict[str, Any]:
        """
        获取工具信息
        
        Returns:
            Dict: 工具的元信息
        """
        # 获取输入参数信息
        input_params = {}
        if self.input_schema:
            for name, field_info in self.input_schema.model_fields.items():
                input_params[name] = {
                    'type': field_info.annotation.__name__ if hasattr(field_info.annotation, '__name__') else str(field_info.annotation),
                    'description': field_info.description,
                    'required': field_info.is_required(),
                    'default': field_info.get_default() if not field_info.is_required() else None
                }
        
        # 构建工具信息
        return {
            'name': self.name,
            'description': self.description,
            'input_params': input_params,
            'has_input_schema': self.input_schema is not None
        }
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """
        验证输入参数
        
        Args:
            **kwargs: 要验证的输入参数
            
        Returns:
            Dict: 验证后的参数
            
        Raises:
            ValidationError: 如果输入参数验证失败
        """
        if self.input_schema:
            # 使用Pydantic模型验证输入参数
            validated_input = self.input_schema(**kwargs).model_dump()
            return validated_input
        else:
            # 如果没有输入参数模型，直接返回原始参数
            return kwargs
    
    async def execute(self, **kwargs) -> ToolResponse:
        """
        执行工具
        
        这是对外提供的工具执行接口，包含参数验证、日志记录等功能
        
        Args:
            **kwargs: 工具的输入参数
            
        Returns:
            ToolResponse: 工具执行结果
        """
        try:
            # 记录执行开始日志
            self.logger.info(f"Executing tool: {self.name} with params: {kwargs}")
            
            # 验证输入参数
            validated_params = self.validate_input(**kwargs)
            
            # 执行工具
            result = await self._execute(**validated_params)
            
            # 确保返回的是ToolResponse类型
            if not isinstance(result, ToolResponse):
                # 尝试将结果转换为ToolResponse
                if isinstance(result, dict):
                    result = ToolResponse(**result)
                else:
                    result = ToolResponse(success=True, result=result)
            
            # 设置工具名称
            if result.tool_name is None:
                result.tool_name = self.name
            
            # 记录执行成功日志
            self.logger.info(f"Tool execution completed: {self.name}, success: {result.success}")
            
            return result
            
        except ValidationError as e:
            # 输入参数验证失败
            error_msg = f"Input validation error: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(
                success=False,
                error=error_msg,
                tool_name=self.name
            )
        except Exception as e:
            # 其他执行错误
            error_msg = f"Tool execution error: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(
                success=False,
                error=error_msg,
                tool_name=self.name
            )
    
    def __str__(self) -> str:
        """
        工具的字符串表示
        """
        return f"Tool(name={self.name}, description={self.description})"
    
    def __repr__(self) -> str:
        """
        工具的详细字符串表示
        """
        return self.__str__()
    
    # ===== 工具装饰器 =====
    
    @classmethod
    def tool(cls, func: Callable) -> Callable:
        """
        将普通函数转换为工具的装饰器
        
        这个装饰器可以将普通函数标记为工具函数
        
        Args:
            func: 要转换的函数
            
        Returns:
            Callable: 转换后的函数
        """
        # 设置工具描述
        func.tool_description = inspect.getdoc(func) or ""
        
        # 记录原始函数信息
        func.is_tool = True
        func.original_func = func
        
        return func
    
    # ===== 工具辅助方法 =====
    
    def format_response(self, success: bool, result: Any = None, error: str = None, **kwargs) -> ToolResponse:
        """
        格式化工具响应
        
        Args:
            success: 是否成功
            result: 执行结果
            error: 错误信息
            **kwargs: 其他元数据
            
        Returns:
            ToolResponse: 格式化后的响应
        """
        metadata = kwargs.copy()
        
        return ToolResponse(
            success=success,
            result=result,
            error=error,
            metadata=metadata,
            tool_name=self.name
        )
    
    def handle_error(self, error: Exception, include_traceback: bool = False) -> ToolResponse:
        """
        处理工具执行错误
        
        Args:
            error: 异常对象
            include_traceback: 是否包含堆栈跟踪信息
            
        Returns:
            ToolResponse: 错误响应
        """
        error_msg = str(error)
        
        if include_traceback:
            import traceback
            error_msg += f"\n{traceback.format_exc()}"
        
        return ToolResponse(
            success=False,
            error=error_msg,
            tool_name=self.name
        )
    
    def set_log_level(self, level: Union[int, str]):
        """
        设置日志级别
        
        Args:
            level: 日志级别
        """
        self.logger.setLevel(level)
    
    def get_logger(self) -> logging.Logger:
        """
        获取日志记录器
        
        Returns:
            logging.Logger: 日志记录器实例
        """
        return self.logger
    
    # ===== 异步工具执行 =====
    
    def execute_sync(self, **kwargs) -> ToolResponse:
        """
        同步执行工具
        
        这个方法可以在同步上下文中执行异步工具
        
        Args:
            **kwargs: 工具的输入参数
            
        Returns:
            ToolResponse: 工具执行结果
        """
        import asyncio
        
        try:
            # 检查是否已经在事件循环中
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建一个新的任务并等待完成
                future = asyncio.run_coroutine_threadsafe(self.execute(**kwargs), loop)
                return future.result()
            else:
                # 如果事件循环没有运行，直接运行协程
                return loop.run_until_complete(self.execute(**kwargs))
        except RuntimeError:
            # 如果没有找到事件循环，创建一个新的事件循环
            return asyncio.run(self.execute(**kwargs))
    
    # ===== 工具序列化 =====
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将工具信息序列化为字典
        
        Returns:
            Dict: 序列化后的工具信息
        """
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': self.input_schema.model_json_schema() if self.input_schema else None,
            'output_schema': self.output_schema.model_json_schema()
        }
    
    def to_json(self) -> str:
        """
        将工具信息序列化为JSON字符串
        
        Returns:
            str: 序列化后的JSON字符串
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to serialize tool to JSON: {str(e)}")
            return '{}'
    
    # ===== 工具参数处理 =====
    
    def get_default_params(self) -> Dict[str, Any]:
        """
        获取工具的默认参数
        
        Returns:
            Dict: 默认参数字典
        """
        default_params = {}
        
        if self.input_schema:
            for name, field_info in self.input_schema.model_fields.items():
                if not field_info.is_required():
                    default_params[name] = field_info.get_default()
        
        return default_params
    
    def merge_params(self, user_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并用户参数和默认参数
        
        Args:
            user_params: 用户提供的参数
            
        Returns:
            Dict: 合并后的参数
        """
        # 获取默认参数
        default_params = self.get_default_params()
        
        # 合并参数，用户参数优先级更高
        merged_params = default_params.copy()
        merged_params.update(user_params)
        
        return merged_params
    
    # ===== 工具状态管理 =====
    
    def is_available(self) -> bool:
        """
        检查工具是否可用
        
        Returns:
            bool: 工具是否可用
        """
        # 基础实现，始终返回True
        # 子类可以根据需要重写这个方法
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取工具状态
        
        Returns:
            Dict: 工具状态信息
        """
        return {
            'name': self.name,
            'available': self.is_available(),
            'description': self.description
        }