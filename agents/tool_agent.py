"""
工具智能体实现
"""
import asyncio
import subprocess
import os
import json
import re
from typing import Dict, Any, Optional, List, Union, Callable
import logging
import datetime

from .base_agent import BaseAgent


class ToolAgent(BaseAgent):
    """
    工具智能体实现
    
    提供各种实用工具功能，如执行代码、查询信息等
    """
    
    def _initialize(self):
        """
        初始化工具智能体
        
        注册可用工具、设置执行环境等
        """
        # 设置默认工具目录
        self.tools_dir = self.agent_config.get('tools_dir', './tools')
        
        # 初始化工具注册表
        self.tools_registry = {
            'execute_python': self.execute_python,
            'execute_bash': self.execute_bash,
            'read_file': self.read_file,
            'write_file': self.write_file,
            'list_files': self.list_files,
            'search_text': self.search_text,
            'get_current_time': self.get_current_time,
            'calculate': self.calculate,
            'get_weather': self.get_weather,
        }
        
        # 加载自定义工具
        self._load_custom_tools()
        
        # 更新状态
        self.set_state({
            'initialized': True,
            'ready': True,
            'available_tools': list(self.tools_registry.keys())
        })
    
    def _load_custom_tools(self):
        """
        加载自定义工具
        
        从tools_dir目录加载自定义工具模块
        """
        try:
            # 检查工具目录是否存在
            if not os.path.exists(self.tools_dir):
                os.makedirs(self.tools_dir)
                return
            
            # 遍历目录中的所有.py文件
            for filename in os.listdir(self.tools_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    # 提取模块名
                    module_name = filename[:-3]
                    
                    try:
                        # 动态导入模块
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(module_name, os.path.join(self.tools_dir, filename))
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            
                            # 查找工具函数
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                # 检查是否是可调用对象且有tool_description属性
                                if callable(attr) and hasattr(attr, 'tool_description'):
                                    self.tools_registry[attr_name] = attr
                                    self.logger.info(f"Loaded custom tool: {attr_name}")
                    except Exception as e:
                        self.logger.error(f"Failed to load custom tool {filename}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to load custom tools: {str(e)}")
    
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
            
            # 添加到消息历史
            self.add_message_to_history(message)
            
            # 解析消息内容，提取工具调用请求
            content = message.get('content', '')
            
            # 尝试解析JSON格式的工具调用
            try:
                tool_request = json.loads(content)
                if isinstance(tool_request, dict) and 'tool_name' in tool_request:
                    return await self._handle_tool_request(tool_request)
            except json.JSONDecodeError:
                # 不是JSON格式，尝试从文本中提取工具调用
                pass
            
            # 尝试从文本中提取工具调用
            tool_call_match = re.search(r'\b(\w+)\(\s*(.*?)\s*\)', content)
            if tool_call_match:
                tool_name = tool_call_match.group(1)
                try:
                    # 尝试解析参数
                    args_str = tool_call_match.group(2)
                    args = json.loads(f'[{args_str}]') if args_str.strip() else []
                    tool_request = {'tool_name': tool_name, 'params': args}
                    return await self._handle_tool_request(tool_request)
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'Failed to parse tool parameters: {str(e)}'
                    }
            
            # 如果没有找到工具调用，返回可用工具列表
            return {
                'success': True,
                'content': f"Available tools: {', '.join(self.tools_registry.keys())}",
                'available_tools': list(self.tools_registry.keys())
            }
            
        except Exception as e:
            return self.handle_error(e)
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成响应
        
        Args:
            prompt: 提示词
            **kwargs: 其他可选参数
            
        Returns:
            Dict: 包含响应内容的字典
        """
        try:
            # 构建消息
            message = {'content': prompt}
            
            # 处理消息
            result = await self.process_message(message)
            
            # 构建响应消息
            if result.get('success'):
                return {
                    'success': True,
                    'content': result.get('content', ''),
                    'tool_result': result
                }
            
            return result
            
        except Exception as e:
            return self.handle_error(e)
    
    async def _handle_tool_request(self, tool_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理工具请求
        
        Args:
            tool_request: 工具请求信息
            
        Returns:
            Dict: 工具执行结果
        """
        try:
            # 获取工具名称和参数
            tool_name = tool_request.get('tool_name')
            params = tool_request.get('params', {})
            
            # 检查工具是否存在
            if tool_name not in self.tools_registry:
                return {
                    'success': False,
                    'error': f'Tool not found: {tool_name}',
                    'available_tools': list(self.tools_registry.keys())
                }
            
            # 获取工具函数
            tool_func = self.tools_registry[tool_name]
            
            # 执行工具函数
            self.logger.info(f"Executing tool: {tool_name} with params: {params}")
            
            # 判断是同步函数还是异步函数
            if asyncio.iscoroutinefunction(tool_func):
                # 异步执行
                result = await tool_func(**params)
            else:
                # 同步执行（在事件循环中运行）
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, 
                    lambda: tool_func(**params) if isinstance(params, dict) else tool_func(*params)
                )
            
            # 构建响应消息
            response_message = {
                'role': 'tool',
                'content': json.dumps(result) if isinstance(result, (dict, list)) else str(result),
                'tool_name': tool_name,
                'tool_result': result
            }
            
            # 添加到历史记录
            self.add_message_to_history(response_message)
            
            return {
                'success': True,
                'response': response_message,
                'tool_name': tool_name,
                'result': result
            }
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error executing tool {tool_request.get('tool_name')}: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'tool_name': tool_request.get('tool_name')
            }
    
    def register_tool(self, name: str, tool_func: Callable):
        """
        注册新工具
        
        Args:
            name: 工具名称
            tool_func: 工具函数
        """
        if callable(tool_func):
            self.tools_registry[name] = tool_func
            self.logger.info(f"Tool registered: {name}")
            # 更新可用工具列表
            self.set_state({
                'available_tools': list(self.tools_registry.keys())
            })
        else:
            self.logger.error(f"Cannot register {name}: not a callable function")
    
    def unregister_tool(self, name: str):
        """
        注销工具
        
        Args:
            name: 工具名称
        """
        if name in self.tools_registry:
            del self.tools_registry[name]
            self.logger.info(f"Tool unregistered: {name}")
            # 更新可用工具列表
            self.set_state({
                'available_tools': list(self.tools_registry.keys())
            })
        else:
            self.logger.warning(f"Cannot unregister {name}: tool not found")
    
    def get_available_tools(self) -> List[str]:
        """
        获取可用工具列表
        
        Returns:
            List[str]: 可用工具名称列表
        """
        return list(self.tools_registry.keys())
    
    # ===== 内置工具实现 =====
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """
        执行Python代码
        
        Args:
            code: 要执行的Python代码
            
        Returns:
            Dict: 执行结果
        """
        try:
            # 创建临时模块
            namespace = {}
            
            # 执行代码
            exec(code, namespace)
            
            # 收集结果（简单实现，仅返回最后一个表达式的值）
            result = namespace.get('result', 'Code executed successfully')
            
            return {
                'success': True,
                'result': result,
                'code': code
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'code': code
            }
    
    def execute_bash(self, command: str, cwd: str = '.') -> Dict[str, Any]:
        """
        执行Bash命令
        
        Args:
            command: 要执行的Bash命令
            cwd: 工作目录
            
        Returns:
            Dict: 执行结果
        """
        try:
            # 执行命令
            result = subprocess.run(
                command, 
                shell=True, 
                check=False, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                cwd=cwd,
                text=True
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'command': command,
                'cwd': cwd
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'command': command,
                'cwd': cwd
            }
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 文件内容
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': f'File not found: {file_path}'
                }
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                'success': True,
                'content': content,
                'file_path': file_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def write_file(self, file_path: str, content: str, append: bool = False) -> Dict[str, Any]:
        """
        写入文件内容
        
        Args:
            file_path: 文件路径
            content: 要写入的内容
            append: 是否追加模式
            
        Returns:
            Dict: 写入结果
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 写入文件
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'message': f'File {"appended" if append else "written"} successfully',
                'file_path': file_path
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def list_files(self, directory: str = '.', pattern: str = '*') -> Dict[str, Any]:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            Dict: 文件列表
        """
        try:
            # 检查目录是否存在
            if not os.path.exists(directory):
                return {
                    'success': False,
                    'error': f'Directory not found: {directory}'
                }
            
            # 列出文件
            import glob
            files = glob.glob(os.path.join(directory, pattern))
            
            # 格式化结果
            result = []
            for file in files:
                file_info = {
                    'name': os.path.basename(file),
                    'path': file,
                    'is_directory': os.path.isdir(file)
                }
                if not file_info['is_directory']:
                    file_info['size'] = os.path.getsize(file)
                result.append(file_info)
            
            return {
                'success': True,
                'files': result,
                'directory': directory,
                'pattern': pattern
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'directory': directory
            }
    
    def search_text(self, text: str, search_query: str) -> Dict[str, Any]:
        """
        在文本中搜索内容
        
        Args:
            text: 要搜索的文本
            search_query: 搜索查询
            
        Returns:
            Dict: 搜索结果
        """
        try:
            # 执行搜索
            matches = []
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if re.search(search_query, line, re.IGNORECASE):
                    matches.append({
                        'line_number': i + 1,
                        'line': line
                    })
            
            return {
                'success': True,
                'matches': matches,
                'match_count': len(matches),
                'search_query': search_query
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'search_query': search_query
            }
    
    def get_current_time(self, format: str = '%Y-%m-%d %H:%M:%S') -> Dict[str, Any]:
        """
        获取当前时间
        
        Args:
            format: 时间格式
            
        Returns:
            Dict: 当前时间
        """
        try:
            current_time = datetime.datetime.now().strftime(format)
            return {
                'success': True,
                'current_time': current_time,
                'format': format
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate(self, expression: str) -> Dict[str, Any]:
        """
        计算数学表达式
        
        Args:
            expression: 数学表达式
            
        Returns:
            Dict: 计算结果
        """
        try:
            # 安全计算表达式
            # 注意：这是一个简化的实现，实际使用中应该使用更安全的计算方法
            # 例如使用ast模块解析表达式
            result = eval(expression, {'__builtins__': {}})
            return {
                'success': True,
                'result': result,
                'expression': expression
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'expression': expression
            }
    
    def get_weather(self, location: str) -> Dict[str, Any]:
        """
        获取天气信息
        
        注意：这个方法只是一个示例实现，实际使用中需要接入天气API
        
        Args:
            location: 位置
            
        Returns:
            Dict: 天气信息
        """
        try:
            # 这里只是一个示例实现，实际使用中需要接入天气API
            # 例如：和风天气API、OpenWeatherMap等
            self.logger.warning("Weather API is not implemented. This is a mock response.")
            
            # 返回模拟数据
            return {
                'success': True,
                'location': location,
                'weather': 'Sunny',
                'temperature': 25,
                'humidity': 60,
                'wind_speed': 10,
                'message': 'This is a mock response. Please implement a real weather API.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'location': location
            }