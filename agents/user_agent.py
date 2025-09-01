"""
用户智能体实现
"""
import asyncio
import json
from typing import Dict, Any, Optional, List, Union, Callable
import logging

from .base_agent import BaseAgent


class UserAgent(BaseAgent):
    """
    用户智能体实现
    
    代表用户与其他智能体进行交互
    """
    
    def _initialize(self):
        """
        初始化用户智能体
        
        设置用户参数、交互模式等
        """
        # 获取用户配置
        self.username = self.agent_config.get('username', 'User')
        self.interaction_mode = self.agent_config.get('interaction_mode', 'auto')  # auto, manual, hybrid
        self.auto_response_timeout = self.agent_config.get('auto_response_timeout', 60)  # 秒
        
        # 初始化回调函数
        self.user_reply_callback = self.agent_config.get('user_reply_callback', None)
        
        # 设置默认的自动回复
        self.auto_responses = self.agent_config.get('auto_responses', {})
        
        # 设置初始状态
        self.set_state({
            'initialized': True,
            'ready': True,
            'username': self.username,
            'interaction_mode': self.interaction_mode
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
            
            # 添加到消息历史
            self.add_message_to_history(message)
            
            # 根据交互模式处理消息
            if self.interaction_mode == 'auto':
                # 自动模式：自动生成回复
                return await self._handle_auto_response(message)
            elif self.interaction_mode == 'manual':
                # 手动模式：等待用户手动回复
                return await self._handle_manual_response(message)
            elif self.interaction_mode == 'hybrid':
                # 混合模式：根据消息内容决定是自动回复还是手动回复
                return await self._handle_hybrid_response(message)
            else:
                # 未知模式，默认使用自动模式
                return await self._handle_auto_response(message)
            
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
                    'user_response': result
                }
            
            return result
            
        except Exception as e:
            return self.handle_error(e)
    
    async def _handle_auto_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理自动回复
        
        Args:
            message: 要处理的消息
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 提取消息内容
            content = message.get('content', '')
            
            # 检查是否有匹配的自动回复
            response = None
            for trigger, auto_reply in self.auto_responses.items():
                if trigger.lower() in content.lower():
                    response = auto_reply
                    break
            
            # 如果没有匹配的自动回复，生成默认回复
            if response is None:
                response = self._generate_default_auto_response(message)
            
            # 构建响应消息
            response_message = {
                'role': 'user',
                'content': response,
                'username': self.username,
                'auto_generated': True
            }
            
            # 添加到历史记录
            self.add_message_to_history(response_message)
            
            # 模拟用户思考时间
            await asyncio.sleep(1)  # 1秒延迟，模拟用户思考
            
            return {
                'success': True,
                'content': response,
                'message': response_message,
                'auto_generated': True
            }
            
        except Exception as e:
            return self.handle_error(e)
    
    async def _handle_manual_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理手动回复
        
        Args:
            message: 要处理的消息
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 如果提供了回调函数，使用回调函数获取用户回复
            if self.user_reply_callback and callable(self.user_reply_callback):
                self.logger.info(f"Waiting for manual user response...")
                
                # 调用回调函数获取用户回复
                # 注意：这里假设回调函数是异步的
                if asyncio.iscoroutinefunction(self.user_reply_callback):
                    response = await self.user_reply_callback(message)
                else:
                    # 如果回调是同步的，在事件循环中运行
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self.user_reply_callback(message)
                    )
            else:
                # 如果没有提供回调函数，使用默认的手动回复机制
                response = await self._get_default_manual_response(message)
            
            # 构建响应消息
            response_message = {
                'role': 'user',
                'content': response,
                'username': self.username,
                'auto_generated': False
            }
            
            # 添加到历史记录
            self.add_message_to_history(response_message)
            
            return {
                'success': True,
                'content': response,
                'message': response_message,
                'auto_generated': False
            }
            
        except Exception as e:
            return self.handle_error(e)
    
    async def _handle_hybrid_response(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理混合模式回复
        
        Args:
            message: 要处理的消息
            
        Returns:
            Dict: 处理结果
        """
        try:
            # 提取消息内容
            content = message.get('content', '')
            
            # 判断是否需要手动回复
            # 这里可以根据实际需求自定义判断逻辑
            # 例如，检查是否包含特定关键词，或者消息是否来自特定智能体
            need_manual_reply = self._need_manual_reply(message)
            
            # 根据判断结果选择回复模式
            if need_manual_reply:
                return await self._handle_manual_response(message)
            else:
                return await self._handle_auto_response(message)
            
        except Exception as e:
            return self.handle_error(e)
    
    def _generate_default_auto_response(self, message: Dict[str, Any]) -> str:
        """
        生成默认的自动回复
        
        Args:
            message: 要回复的消息
            
        Returns:
            str: 默认回复内容
        """
        # 简单的默认回复逻辑
        # 实际使用中可以根据需要自定义更复杂的回复逻辑
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        
        # 根据角色生成不同的默认回复
        if role == 'system':
            return "好的，我已收到系统消息。"
        elif role == 'assistant':
            # 检查消息内容是否包含问题
            if any(keyword in content.lower() for keyword in ['?', '？', '请', '能否', '是否']):
                return "这是一个自动回复。请提供更多详细信息。"
            else:
                return "好的，我了解了。"
        elif role == 'tool':
            return "工具执行结果已收到。"
        else:
            return "收到消息。"
    
    async def _get_default_manual_response(self, message: Dict[str, Any]) -> str:
        """
        获取默认的手动回复
        
        默认情况下，这里会抛出异常，因为在手动模式下需要用户交互
        在实际使用中，这应该被替换为实际的用户交互代码
        
        Args:
            message: 要回复的消息
            
        Returns:
            str: 用户回复内容
        """
        self.logger.warning(
            "No user_reply_callback provided for manual interaction mode. "
            "Falling back to default auto-response."
        )
        
        # 如果没有提供回调函数，使用自动回复作为备选方案
        return self._generate_default_auto_response(message)
    
    def _need_manual_reply(self, message: Dict[str, Any]) -> bool:
        """
        判断是否需要手动回复
        
        Args:
            message: 要判断的消息
            
        Returns:
            bool: 是否需要手动回复
        """
        # 简单的判断逻辑
        # 实际使用中可以根据需要自定义更复杂的判断逻辑
        content = message.get('content', '')
        
        # 如果消息包含特定关键词，需要手动回复
        keywords = ['需要你的确认', '请确认', '是否继续', '需要决策', '请选择', '你觉得呢']
        if any(keyword in content for keyword in keywords):
            return True
        
        # 如果消息长度较短，可能需要手动回复
        if len(content) < 20:
            return True
        
        # 默认不需要手动回复
        return False
    
    def set_interaction_mode(self, mode: str):
        """
        设置交互模式
        
        Args:
            mode: 交互模式，可选值：auto, manual, hybrid
        """
        if mode in ['auto', 'manual', 'hybrid']:
            self.interaction_mode = mode
            self.set_state({
                'interaction_mode': mode
            })
            self.logger.info(f"Interaction mode set to: {mode}")
        else:
            self.logger.warning(f"Invalid interaction mode: {mode}. Using 'auto' instead.")
            self.set_interaction_mode('auto')
    
    def add_auto_response(self, trigger: str, response: str):
        """
        添加自动回复
        
        Args:
            trigger: 触发关键词
            response: 对应的回复内容
        """
        self.auto_responses[trigger] = response
        self.logger.info(f"Auto-response added: '{trigger}' -> '{response}'")
    
    def remove_auto_response(self, trigger: str):
        """
        移除自动回复
        
        Args:
            trigger: 触发关键词
        """
        if trigger in self.auto_responses:
            del self.auto_responses[trigger]
            self.logger.info(f"Auto-response removed: '{trigger}'")
        else:
            self.logger.warning(f"Auto-response not found: '{trigger}'")
    
    def get_auto_responses(self) -> Dict[str, str]:
        """
        获取所有自动回复
        
        Returns:
            Dict: 自动回复字典
        """
        return self.auto_responses.copy()
    
    def set_user_reply_callback(self, callback: Callable):
        """
        设置用户回复回调函数
        
        Args:
            callback: 回调函数
        """
        if callable(callback):
            self.user_reply_callback = callback
            self.logger.info("User reply callback set successfully")
        else:
            self.logger.error("Invalid callback function")
    
    async def send_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送消息
        
        Args:
            message: 要发送的消息
            
        Returns:
            Dict: 发送结果
        """
        try:
            # 确保消息格式正确
            if 'content' not in message:
                return {
                    'success': False,
                    'error': 'Message content is required'
                }
            
            # 添加用户信息
            message['role'] = 'user'
            message['username'] = self.username
            
            # 添加到历史记录
            self.add_message_to_history(message)
            
            # 调用父类的发送消息方法（如果有）
            # 这里可以根据实际需求自定义消息发送逻辑
            
            self.logger.info(f"User message sent: {message.get('content')}")
            
            return {
                'success': True,
                'message': message
            }
            
        except Exception as e:
            return self.handle_error(e)
    
    def display_message(self, message: Dict[str, Any]):
        """
        显示消息
        
        Args:
            message: 要显示的消息
        """
        # 简单的消息显示逻辑
        # 实际使用中可以根据需要自定义更复杂的显示逻辑
        role = message.get('role', 'unknown')
        content = message.get('content', '')
        sender = message.get('username', role)
        
        # 打印消息
        print(f"\n[{sender}]\n{content}\n")
        
        # 记录日志
        self.logger.info(f"Message displayed: role={role}, sender={sender}, content={content[:100]}...")
    
    async def wait_for_reply(self, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        等待回复
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            Dict: 回复消息
        """
        # 简单的等待回复逻辑
        # 实际使用中可以根据需要自定义更复杂的等待逻辑
        # 注意：这个方法需要根据实际的交互机制来实现
        self.logger.warning("wait_for_reply method is not fully implemented.")
        
        # 默认返回一个示例回复
        await asyncio.sleep(2)  # 模拟等待时间
        
        return {
            'success': True,
            'content': "这是一个模拟的回复。实际使用中，应该实现真实的等待回复逻辑。",
            'role': 'user',
            'username': self.username
        }
    
    def export_conversation_history(self, file_path: str = None) -> Dict[str, Any]:
        """
        导出对话历史
        
        Args:
            file_path: 导出文件路径，如果为None则只返回数据不保存
            
        Returns:
            Dict: 对话历史数据
        """
        try:
            # 构建对话历史数据
            conversation_data = {
                'username': self.username,
                'interaction_mode': self.interaction_mode,
                'start_time': self.get_state('start_time'),
                'end_time': datetime.datetime.now().isoformat(),
                'messages': self.get_message_history()
            }
            
            # 如果提供了文件路径，保存到文件
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(conversation_data, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"Conversation history exported to: {file_path}")
            
            return conversation_data
            
        except Exception as e:
            self.logger.error(f"Failed to export conversation history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def import_conversation_history(self, file_path: str) -> Dict[str, Any]:
        """
        导入对话历史
        
        Args:
            file_path: 导入文件路径
            
        Returns:
            Dict: 导入结果
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                conversation_data = json.load(f)
            
            # 恢复对话历史
            if 'messages' in conversation_data:
                self.clear_message_history()
                for message in conversation_data['messages']:
                    self.add_message_to_history(message)
            
            # 恢复其他信息
            if 'username' in conversation_data:
                self.username = conversation_data['username']
                self.set_state({'username': self.username})
            
            if 'interaction_mode' in conversation_data:
                self.set_interaction_mode(conversation_data['interaction_mode'])
            
            self.logger.info(f"Conversation history imported from: {file_path}")
            
            return {
                'success': True,
                'imported_data': conversation_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to import conversation history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }