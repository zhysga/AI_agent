"""
系统工具实现
"""
import os
import sys
import subprocess
import platform
import time
import datetime
import shutil
import tempfile
import glob
import stat
import json
import yaml
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
import logging
import abc

from .base_tool import BaseTool, ToolResponse


class SystemTool(BaseTool):
    """
    系统工具基类
    
    提供与操作系统交互的基础功能
    """
    
    def _initialize(self):
        """
        初始化系统工具
        """
        # 设置工具名称
        self.name = "SystemTool"
        
        # 设置工具描述
        self.description = "与操作系统交互的基础工具"
        
        # 系统信息
        self.system_info = {
            'os': platform.system(),
            'version': platform.version(),
            'architecture': platform.architecture(),
            'machine': platform.machine(),
            'python_version': platform.python_version()
        }
        
        # 初始化日志
        self.logger.info(f"System info: {self.system_info}")
    
    @abc.abstractmethod
    async def _execute(self, **kwargs) -> ToolResponse:
        """
        执行系统工具的具体实现
        
        Args:
            **kwargs: 工具的输入参数
            
        Returns:
            ToolResponse: 执行结果
        """
        pass
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        获取系统信息
        
        Returns:
            Dict: 系统信息字典
        """
        return self.system_info.copy()
    
    def is_windows(self) -> bool:
        """
        检查当前操作系统是否为Windows
        
        Returns:
            bool: 是否为Windows
        """
        return self.system_info['os'] == 'Windows'
    
    def is_linux(self) -> bool:
        """
        检查当前操作系统是否为Linux
        
        Returns:
            bool: 是否为Linux
        """
        return self.system_info['os'] == 'Linux'
    
    def is_macos(self) -> bool:
        """
        检查当前操作系统是否为macOS
        
        Returns:
            bool: 是否为macOS
        """
        return self.system_info['os'] == 'Darwin'


class CommandExecutionTool(SystemTool):
    """
    命令执行工具
    
    在系统中执行命令行指令
    """
    
    def _initialize(self):
        """
        初始化命令执行工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "CommandExecutionTool"
        self.description = "在系统中执行命令行指令"
        
        # 默认配置
        self.default_params = {
            'shell': False,
            'timeout': 60,
            'cwd': None,
            'env': None,
            'capture_output': True
        }
        
        # 安全命令列表（白名单）
        self.allowed_commands = set()
        
        # 危险命令列表（黑名单）
        self.dangerous_commands = {
            'rm', 'del', 'erase', 'format', 'mkfs',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'su', 'sudo', 'passwd', 'useradd', 'userdel',
            'mount', 'umount', 'dd', 'chmod', 'chown'
        }
    
    async def _execute(self, command: Union[str, List[str]], **kwargs) -> ToolResponse:
        """
        执行命令
        
        Args:
            command: 要执行的命令，可以是字符串或列表
            **kwargs: 执行参数
            
        Returns:
            ToolResponse: 执行结果
        """
        try:
            # 验证命令安全性
            if not self._is_command_safe(command):
                return self.format_response(
                    success=False,
                    error=f"Command is not allowed for security reasons: {command}"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录命令执行请求
            self.logger.info(f"Executing command: {command}")
            
            # 执行命令
            result = await self._run_command(command, params)
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=result,
                command=command,
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    def _is_command_safe(self, command: Union[str, List[str]]) -> bool:
        """
        验证命令是否安全
        
        Args:
            command: 要验证的命令
            
        Returns:
            bool: 命令是否安全
        """
        # 获取命令名称
        if isinstance(command, list):
            cmd_name = command[0].lower()
        else:
            # 对于字符串命令，提取第一个单词作为命令名
            cmd_parts = command.strip().split()
            if not cmd_parts:
                return False
            cmd_name = cmd_parts[0].lower()
        
        # 如果命令在黑名单中，禁止执行
        if cmd_name in self.dangerous_commands:
            self.logger.warning(f"Dangerous command blocked: {cmd_name}")
            return False
        
        # 如果有白名单，只有白名单中的命令可以执行
        if self.allowed_commands and cmd_name not in self.allowed_commands:
            self.logger.warning(f"Command not in allowed list: {cmd_name}")
            return False
        
        return True
    
    async def _run_command(self, command: Union[str, List[str]], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行命令并获取结果
        
        Args:
            command: 要运行的命令
            params: 运行参数
            
        Returns:
            Dict: 命令运行结果
        """
        try:
            # 提取参数
            shell = params.get('shell', False)
            timeout = params.get('timeout', 60)
            cwd = params.get('cwd')
            env = params.get('env')
            capture_output = params.get('capture_output', True)
            
            # 准备命令参数
            command_kwargs = {
                'shell': shell,
                'timeout': timeout,
                'cwd': cwd,
                'env': env
            }
            
            # 是否捕获输出
            if capture_output:
                command_kwargs['stdout'] = subprocess.PIPE
                command_kwargs['stderr'] = subprocess.PIPE
            
            # 在Windows上，如果是列表形式的命令，需要特殊处理
            if self.is_windows() and isinstance(command, list) and not shell:
                # 使用PowerShell执行命令
                cmd = ['powershell.exe', '-Command', ' '.join(command)]
            else:
                cmd = command
            
            # 记录执行的实际命令
            self.logger.debug(f"Running command with params: {cmd}, {command_kwargs}")
            
            # 执行命令（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def run_sync_command():
                return subprocess.run(cmd, **command_kwargs)
            
            process = await loop.run_in_executor(None, run_sync_command)
            
            # 构建结果
            result = {
                'returncode': process.returncode,
                'success': process.returncode == 0
            }
            
            # 如果捕获了输出，解码输出内容
            if capture_output:
                stdout = process.stdout.decode('utf-8', errors='replace') if process.stdout else ''
                stderr = process.stderr.decode('utf-8', errors='replace') if process.stderr else ''
                
                result['stdout'] = stdout
                result['stderr'] = stderr
                
                # 合并输出用于简单查看
                result['output'] = stdout + '\n' + stderr if stdout or stderr else ''
            
            return result
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command execution timed out: {command}")
            raise Exception(f"Command execution timed out after {params.get('timeout', 60)} seconds")
        except Exception as e:
            self.logger.error(f"Error executing command {command}: {str(e)}")
            raise
    
    def add_allowed_command(self, command: str):
        """
        添加允许的命令到白名单
        
        Args:
            command: 要添加的命令名称
        """
        self.allowed_commands.add(command.lower())
        self.logger.info(f"Added command to allowed list: {command}")
    
    def remove_allowed_command(self, command: str):
        """
        从白名单中移除允许的命令
        
        Args:
            command: 要移除的命令名称
        """
        if command.lower() in self.allowed_commands:
            self.allowed_commands.remove(command.lower())
            self.logger.info(f"Removed command from allowed list: {command}")
    
    def set_allowed_commands(self, commands: List[str]):
        """
        设置允许的命令白名单
        
        Args:
            commands: 允许的命令列表
        """
        self.allowed_commands = set(cmd.lower() for cmd in commands)
        self.logger.info(f"Set allowed commands: {self.allowed_commands}")
    
    def clear_allowed_commands(self):
        """
        清空允许的命令白名单
        """
        self.allowed_commands.clear()
        self.logger.info("Cleared allowed commands list")


class FileSystemTool(SystemTool):
    """
    文件系统工具
    
    提供文件和目录操作功能
    """
    
    def _initialize(self):
        """
        初始化文件系统工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "FileSystemTool"
        self.description = "提供文件和目录操作功能"
        
        # 默认配置
        self.default_params = {
            'recursive': False,
            'overwrite': False,
            'preserve_permissions': True
        }
        
        # 安全路径检查（白名单）
        self.allowed_paths = []
        
        # 禁止访问的路径（黑名单）
        self.forbidden_paths = [
            os.path.expanduser('~'),  # 用户主目录
            '/etc', '/var', '/usr', '/boot', '/bin', '/sbin',  # Linux系统目录
            'C:\\Windows', 'C:\\Program Files', 'C:\\Program Files (x86)'  # Windows系统目录
        ]
    
    async def _execute(self, operation: str, path: str, **kwargs) -> ToolResponse:
        """
        执行文件系统操作
        
        Args:
            operation: 操作类型（read, write, list, create, delete, copy, move）
            path: 文件或目录路径
            **kwargs: 操作参数
            
        Returns:
            ToolResponse: 操作结果
        """
        try:
            # 验证路径安全性
            if not self._is_path_safe(path):
                return self.format_response(
                    success=False,
                    error=f"Path is not allowed for security reasons: {path}"
                )
            
            # 规范化路径
            path = os.path.abspath(os.path.normpath(path))
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录操作请求
            self.logger.info(f"Executing file system operation: {operation} on path: {path}")
            
            # 根据操作类型执行相应的操作
            if operation.lower() == 'read':
                result = await self._read_file(path, params)
            elif operation.lower() == 'write':
                result = await self._write_file(path, params)
            elif operation.lower() == 'list':
                result = await self._list_directory(path, params)
            elif operation.lower() == 'create':
                result = await self._create_path(path, params)
            elif operation.lower() == 'delete':
                result = await self._delete_path(path, params)
            elif operation.lower() == 'copy':
                result = await self._copy_path(path, params)
            elif operation.lower() == 'move':
                result = await self._move_path(path, params)
            else:
                return self.format_response(
                    success=False,
                    error=f"Unsupported operation: {operation}"
                )
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=result,
                operation=operation,
                path=path,
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    def _is_path_safe(self, path: str) -> bool:
        """
        验证路径是否安全
        
        Args:
            path: 要验证的路径
            
        Returns:
            bool: 路径是否安全
        """
        # 规范化路径
        normalized_path = os.path.abspath(os.path.normpath(path))
        
        # 如果有允许的路径列表，检查路径是否在允许的路径内
        if self.allowed_paths:
            allowed = False
            for allowed_path in self.allowed_paths:
                allowed_path = os.path.abspath(os.path.normpath(allowed_path))
                if normalized_path.startswith(allowed_path + os.sep) or normalized_path == allowed_path:
                    allowed = True
                    break
            if not allowed:
                self.logger.warning(f"Path not in allowed list: {normalized_path}")
                return False
        
        # 检查路径是否在禁止访问的路径内
        for forbidden_path in self.forbidden_paths:
            # 处理用户主目录的特殊情况
            if forbidden_path == os.path.expanduser('~'):
                forbidden_path = os.path.abspath(forbidden_path)
                
            forbidden_path = os.path.abspath(os.path.normpath(forbidden_path))
            if normalized_path.startswith(forbidden_path + os.sep) or normalized_path == forbidden_path:
                self.logger.warning(f"Path is forbidden: {normalized_path}")
                return False
        
        # 检查是否存在路径遍历攻击
        if '..' in path or (self.is_windows() and any(c in '<>:"|?*' for c in path)):
            self.logger.warning(f"Potential path traversal attack: {path}")
            return False
        
        return True
    
    async def _read_file(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        读取文件内容
        
        Args:
            path: 文件路径
            params: 读取参数
            
        Returns:
            Dict: 读取结果
        """
        try:
            # 检查文件是否存在
            if not os.path.isfile(path):
                raise Exception(f"File not found: {path}")
            
            # 检查文件大小
            max_size = params.get('max_size', 10 * 1024 * 1024)  # 默认最大10MB
            file_size = os.path.getsize(path)
            if file_size > max_size:
                raise Exception(f"File size exceeds maximum limit: {file_size} > {max_size} bytes")
            
            # 异步读取文件（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def read_sync():
                with open(path, 'rb') as f:
                    content = f.read()
                
                # 根据文件类型尝试解码
                encoding = params.get('encoding', 'utf-8')
                try:
                    text_content = content.decode(encoding)
                    is_text = True
                except UnicodeDecodeError:
                    text_content = str(content)
                    is_text = False
                
                # 如果是文本文件，且指定了格式化，可以进行格式化
                if is_text and params.get('format', False):
                    try:
                        # 尝试JSON格式化
                        if path.endswith('.json'):
                            parsed_content = json.loads(text_content)
                            formatted_content = json.dumps(parsed_content, indent=2, ensure_ascii=False)
                        # 尝试YAML格式化
                        elif path.endswith(('.yaml', '.yml')):
                            parsed_content = yaml.safe_load(text_content)
                            formatted_content = yaml.dump(parsed_content, default_flow_style=False, allow_unicode=True)
                        else:
                            formatted_content = text_content
                    except Exception:
                        formatted_content = text_content
                else:
                    formatted_content = text_content
                
                return {
                    'content': content,
                    'text_content': text_content,
                    'formatted_content': formatted_content,
                    'is_text': is_text,
                    'size': file_size,
                    'path': path
                }
            
            return await loop.run_in_executor(None, read_sync)
        except Exception as e:
            self.logger.error(f"Error reading file {path}: {str(e)}")
            raise
    
    async def _write_file(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        写入文件内容
        
        Args:
            path: 文件路径
            params: 写入参数，必须包含content
            
        Returns:
            Dict: 写入结果
        """
        try:
            # 获取内容
            content = params.get('content')
            if content is None:
                raise Exception("Content is required for write operation")
            
            # 检查目录是否存在，如果不存在则创建
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 检查文件是否存在，如果不允许覆盖则抛出异常
            if os.path.exists(path) and not params.get('overwrite', False):
                raise Exception(f"File already exists and overwrite is not allowed: {path}")
            
            # 异步写入文件（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def write_sync():
                # 确定写入模式
                mode = 'wb'
                
                # 处理内容类型
                if isinstance(content, str):
                    content_bytes = content.encode(params.get('encoding', 'utf-8'))
                elif isinstance(content, bytes):
                    content_bytes = content
                else:
                    # 尝试将其他类型转换为字符串
                    content_str = str(content)
                    content_bytes = content_str.encode(params.get('encoding', 'utf-8'))
                
                # 写入文件
                with open(path, mode) as f:
                    f.write(content_bytes)
                
                # 获取文件信息
                file_size = os.path.getsize(path)
                
                return {
                    'path': path,
                    'size': file_size,
                    'written': True
                }
            
            return await loop.run_in_executor(None, write_sync)
        except Exception as e:
            self.logger.error(f"Error writing file {path}: {str(e)}")
            raise
    
    async def _list_directory(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出目录内容
        
        Args:
            path: 目录路径
            params: 列出参数
            
        Returns:
            Dict: 列出结果
        """
        try:
            # 检查目录是否存在
            if not os.path.isdir(path):
                raise Exception(f"Directory not found: {path}")
            
            # 获取递归选项
            recursive = params.get('recursive', False)
            
            # 异步列出目录（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def list_sync():
                files = []
                directories = []
                
                if recursive:
                    # 递归列出所有文件和目录
                    for root, dirs, filenames in os.walk(path):
                        for dir_name in dirs:
                            dir_path = os.path.join(root, dir_name)
                            rel_path = os.path.relpath(dir_path, path)
                            stat_info = os.stat(dir_path)
                            
                            directories.append({
                                'name': dir_name,
                                'path': dir_path,
                                'relative_path': rel_path,
                                'size': 0,  # 目录大小不计算
                                'modified_time': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                'created_time': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                                'type': 'directory'
                            })
                        
                        for filename in filenames:
                            file_path = os.path.join(root, filename)
                            rel_path = os.path.relpath(file_path, path)
                            stat_info = os.stat(file_path)
                            
                            files.append({
                                'name': filename,
                                'path': file_path,
                                'relative_path': rel_path,
                                'size': stat_info.st_size,
                                'modified_time': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                'created_time': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                                'type': 'file',
                                'extension': os.path.splitext(filename)[1].lower() if '.' in filename else ''
                            })
                else:
                    # 只列出当前目录
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        stat_info = os.stat(item_path)
                        
                        if os.path.isdir(item_path):
                            directories.append({
                                'name': item,
                                'path': item_path,
                                'relative_path': item,
                                'size': 0,  # 目录大小不计算
                                'modified_time': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                'created_time': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                                'type': 'directory'
                            })
                        else:
                            files.append({
                                'name': item,
                                'path': item_path,
                                'relative_path': item,
                                'size': stat_info.st_size,
                                'modified_time': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                                'created_time': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                                'type': 'file',
                                'extension': os.path.splitext(item)[1].lower() if '.' in item else ''
                            })
                
                return {
                    'path': path,
                    'directories': directories,
                    'files': files,
                    'total_directories': len(directories),
                    'total_files': len(files),
                    'recursive': recursive
                }
            
            return await loop.run_in_executor(None, list_sync)
        except Exception as e:
            self.logger.error(f"Error listing directory {path}: {str(e)}")
            raise
    
    # 以下方法简化实现，省略异步处理的详细代码
    async def _create_path(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建文件或目录
        
        Args:
            path: 要创建的路径
            params: 创建参数
            
        Returns:
            Dict: 创建结果
        """
        try:
            # 检查路径是否已存在
            if os.path.exists(path):
                if params.get('overwrite', False):
                    # 如果允许覆盖，先删除原路径
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                else:
                    raise Exception(f"Path already exists: {path}")
            
            # 根据参数决定创建文件还是目录
            is_directory = params.get('is_directory', False)
            
            if is_directory:
                os.makedirs(path, exist_ok=True)
            else:
                # 确保父目录存在
                directory = os.path.dirname(path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                # 创建空文件
                with open(path, 'w') as f:
                    pass
            
            return {
                'path': path,
                'created': True,
                'is_directory': is_directory
            }
        except Exception as e:
            self.logger.error(f"Error creating path {path}: {str(e)}")
            raise
    
    async def _delete_path(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        删除文件或目录
        
        Args:
            path: 要删除的路径
            params: 删除参数
            
        Returns:
            Dict: 删除结果
        """
        try:
            # 检查路径是否存在
            if not os.path.exists(path):
                raise Exception(f"Path not found: {path}")
            
            # 根据路径类型进行删除
            if os.path.isdir(path):
                # 递归删除目录
                shutil.rmtree(path)
            else:
                # 删除文件
                os.remove(path)
            
            return {
                'path': path,
                'deleted': True
            }
        except Exception as e:
            self.logger.error(f"Error deleting path {path}: {str(e)}")
            raise
    
    async def _copy_path(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        复制文件或目录
        
        Args:
            path: 源路径
            params: 复制参数，必须包含destination
            
        Returns:
            Dict: 复制结果
        """
        try:
            # 获取目标路径
            destination = params.get('destination')
            if destination is None:
                raise Exception("Destination is required for copy operation")
            
            # 检查源路径是否存在
            if not os.path.exists(path):
                raise Exception(f"Source path not found: {path}")
            
            # 检查目标路径是否存在
            if os.path.exists(destination):
                if not params.get('overwrite', False):
                    raise Exception(f"Destination already exists and overwrite is not allowed: {destination}")
            
            # 根据源路径类型进行复制
            if os.path.isdir(path):
                # 确保目标目录不存在
                if os.path.exists(destination):
                    shutil.rmtree(destination)
                # 复制目录
                shutil.copytree(path, destination, symlinks=params.get('follow_symlinks', False))
            else:
                # 确保目标目录存在
                destination_dir = os.path.dirname(destination)
                if destination_dir and not os.path.exists(destination_dir):
                    os.makedirs(destination_dir, exist_ok=True)
                # 复制文件
                shutil.copy2(path, destination) if params.get('preserve_permissions', True) else shutil.copy(path, destination)
            
            return {
                'source': path,
                'destination': destination,
                'copied': True
            }
        except Exception as e:
            self.logger.error(f"Error copying path from {path} to {destination}: {str(e)}")
            raise
    
    async def _move_path(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        移动文件或目录
        
        Args:
            path: 源路径
            params: 移动参数，必须包含destination
            
        Returns:
            Dict: 移动结果
        """
        try:
            # 获取目标路径
            destination = params.get('destination')
            if destination is None:
                raise Exception("Destination is required for move operation")
            
            # 检查源路径是否存在
            if not os.path.exists(path):
                raise Exception(f"Source path not found: {path}")
            
            # 检查目标路径是否存在
            if os.path.exists(destination):
                if not params.get('overwrite', False):
                    raise Exception(f"Destination already exists and overwrite is not allowed: {destination}")
                # 如果目标路径存在且允许覆盖，先删除目标路径
                if os.path.isdir(destination):
                    shutil.rmtree(destination)
                else:
                    os.remove(destination)
            
            # 确保目标目录存在
            destination_dir = os.path.dirname(destination)
            if destination_dir and not os.path.exists(destination_dir):
                os.makedirs(destination_dir, exist_ok=True)
            
            # 移动路径
            shutil.move(path, destination)
            
            return {
                'source': path,
                'destination': destination,
                'moved': True
            }
        except Exception as e:
            self.logger.error(f"Error moving path from {path} to {destination}: {str(e)}")
            raise
    
    def add_allowed_path(self, path: str):
        """
        添加允许访问的路径到白名单
        
        Args:
            path: 要添加的路径
        """
        normalized_path = os.path.abspath(os.path.normpath(path))
        self.allowed_paths.append(normalized_path)
        self.logger.info(f"Added path to allowed list: {normalized_path}")
    
    def remove_allowed_path(self, path: str):
        """
        从白名单中移除允许访问的路径
        
        Args:
            path: 要移除的路径
        """
        normalized_path = os.path.abspath(os.path.normpath(path))
        if normalized_path in self.allowed_paths:
            self.allowed_paths.remove(normalized_path)
            self.logger.info(f"Removed path from allowed list: {normalized_path}")
    
    def set_allowed_paths(self, paths: List[str]):
        """
        设置允许访问的路径白名单
        
        Args:
            paths: 允许访问的路径列表
        """
        self.allowed_paths = [os.path.abspath(os.path.normpath(path)) for path in paths]
        self.logger.info(f"Set allowed paths: {self.allowed_paths}")


class ProcessTool(SystemTool):
    """
    进程管理工具
    
    提供进程查看和管理功能
    """
    
    def _initialize(self):
        """
        初始化进程管理工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "ProcessTool"
        self.description = "提供进程查看和管理功能"
        
        # 导入psutil库（需要安装）
        try:
            import psutil
            self.psutil_available = True
        except ImportError:
            self.psutil_available = False
            self.logger.warning("psutil library is not available. Process management features will be limited.")
    
    async def _execute(self, operation: str, **kwargs) -> ToolResponse:
        """
        执行进程管理操作
        
        Args:
            operation: 操作类型（list, info, kill）
            **kwargs: 操作参数
            
        Returns:
            ToolResponse: 操作结果
        """
        try:
            # 检查psutil是否可用
            if not self.psutil_available:
                return self.format_response(
                    success=False,
                    error="psutil library is not available. Please install it with 'pip install psutil'")
            
            # 导入psutil
            import psutil
            
            # 记录操作请求
            self.logger.info(f"Executing process operation: {operation}")
            
            # 根据操作类型执行相应的操作
            if operation.lower() == 'list':
                result = await self._list_processes(kwargs)
            elif operation.lower() == 'info':
                result = await self._get_process_info(kwargs)
            elif operation.lower() == 'kill':
                result = await self._kill_process(kwargs)
            else:
                return self.format_response(
                    success=False,
                    error=f"Unsupported operation: {operation}")
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=result,
                operation=operation,
                params=kwargs)
            
        except Exception as e:
            return self.handle_error(e)
    
    async def _list_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        列出进程
        
        Args:
            params: 列出参数
            
        Returns:
            Dict: 列出结果
        """
        try:
            # 导入psutil
            import psutil
            
            # 异步列出进程（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def list_sync():
                processes = []
                count = 0
                
                # 获取限制条件
                max_processes = params.get('max_processes', 100)
                name_pattern = params.get('name_pattern')
                pid_pattern = params.get('pid_pattern')
                
                # 遍历所有进程
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status', 'create_time']):
                    try:
                        # 获取进程信息
                        proc_info = proc.info
                        
                        # 过滤进程
                        if name_pattern and name_pattern not in proc_info['name']:
                            continue
                        if pid_pattern and str(pid_pattern) not in str(proc_info['pid']):
                            continue
                        
                        # 格式化创建时间
                        create_time = datetime.datetime.fromtimestamp(proc_info['create_time']).isoformat()
                        
                        # 添加进程信息
                        processes.append({
                            'pid': proc_info['pid'],
                            'name': proc_info['name'],
                            'username': proc_info.get('username', 'unknown'),
                            'cpu_percent': proc_info.get('cpu_percent', 0),
                            'memory_percent': proc_info.get('memory_percent', 0),
                            'status': proc_info.get('status', 'unknown'),
                            'create_time': create_time
                        })
                        
                        # 检查是否达到最大进程数
                        count += 1
                        if count >= max_processes:
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        # 忽略无法访问的进程
                        pass
                
                return {
                    'processes': processes,
                    'total_processes': len(processes),
                    'max_processes': max_processes
                }
            
            return await loop.run_in_executor(None, list_sync)
        except Exception as e:
            self.logger.error(f"Error listing processes: {str(e)}")
            raise
    
    async def _get_process_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取进程详细信息
        
        Args:
            params: 获取信息参数，必须包含pid
            
        Returns:
            Dict: 进程详细信息
        """
        try:
            # 导入psutil
            import psutil
            
            # 获取进程ID
            pid = params.get('pid')
            if pid is None:
                raise Exception("Process ID (pid) is required")
            
            # 异步获取进程信息（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def get_info_sync():
                try:
                    # 获取进程对象
                    proc = psutil.Process(pid)
                    
                    # 获取进程基本信息
                    proc_info = proc.info
                    
                    # 获取更多详细信息
                    details = {
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'username': proc_info.get('username', 'unknown'),
                        'cpu_percent': proc_info.get('cpu_percent', 0),
                        'memory_percent': proc_info.get('memory_percent', 0),
                        'status': proc_info.get('status', 'unknown'),
                        'create_time': datetime.datetime.fromtimestamp(proc_info['create_time']).isoformat(),
                        'cpu_times': proc.cpu_times()._asdict(),
                        'memory_info': proc.memory_info()._asdict(),
                        'cmdline': proc.cmdline(),
                        'environ': proc.environ(),
                        'num_threads': proc.num_threads(),
                        'open_files': [f.path for f in proc.open_files()],
                        'connections': [conn._asdict() for conn in proc.connections()]
                    }
                    
                    return details
                except psutil.NoSuchProcess:
                    raise Exception(f"Process with PID {pid} does not exist")
                except psutil.AccessDenied:
                    raise Exception(f"Access denied to process with PID {pid}")
                except Exception as e:
                    raise Exception(f"Error getting process info: {str(e)}")
            
            return await loop.run_in_executor(None, get_info_sync)
        except Exception as e:
            self.logger.error(f"Error getting process info: {str(e)}")
            raise
    
    async def _kill_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        终止进程
        
        Args:
            params: 终止参数，必须包含pid
            
        Returns:
            Dict: 终止结果
        """
        try:
            # 导入psutil
            import psutil
            
            # 获取进程ID
            pid = params.get('pid')
            if pid is None:
                raise Exception("Process ID (pid) is required")
            
            # 检查是否是当前进程
            if pid == os.getpid():
                raise Exception("Cannot kill the current process")
            
            # 异步终止进程（使用线程池避免阻塞事件循环）
            import asyncio
            loop = asyncio.get_event_loop()
            
            def kill_sync():
                try:
                    # 获取进程对象
                    proc = psutil.Process(pid)
                    
                    # 获取终止信号类型
                    signal_type = params.get('signal', 'terminate')  # terminate, kill, suspend, resume
                    
                    # 执行相应的操作
                    if signal_type == 'terminate':
                        proc.terminate()
                    elif signal_type == 'kill':
                        proc.kill()
                    elif signal_type == 'suspend':
                        proc.suspend()
                    elif signal_type == 'resume':
                        proc.resume()
                    else:
                        raise Exception(f"Unsupported signal type: {signal_type}")
                    
                    # 如果是终止或杀死操作，等待进程结束
                    if signal_type in ['terminate', 'kill']:
                        # 等待进程结束，最多等待5秒
                        try:
                            proc.wait(timeout=5)
                            terminated = True
                        except psutil.TimeoutExpired:
                            terminated = False
                    else:
                        terminated = True
                    
                    return {
                        'pid': pid,
                        'signal': signal_type,
                        'terminated': terminated,
                        'process_name': proc.name()
                    }
                except psutil.NoSuchProcess:
                    raise Exception(f"Process with PID {pid} does not exist")
                except psutil.AccessDenied:
                    raise Exception(f"Access denied to terminate process with PID {pid}")
                except Exception as e:
                    raise Exception(f"Error terminating process: {str(e)}")
            
            return await loop.run_in_executor(None, kill_sync)
        except Exception as e:
            self.logger.error(f"Error terminating process: {str(e)}")
            raise