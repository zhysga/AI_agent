"""
语言模型工具实现
"""
import asyncio
import json
import abc
from typing import Dict, Any, Optional, List, Union, Callable
import logging

from .base_tool import BaseTool, ToolResponse


class LLMTool(BaseTool):
    """
    语言模型工具基类
    
    提供与语言模型交互的基础功能
    """
    
    def _initialize(self):
        """
        初始化语言模型工具
        """
        # 设置工具名称
        self.name = "LLMTool"
        
        # 设置工具描述
        self.description = "与语言模型交互的基础工具"
        
        # 语言模型客户端
        self.llm_client = None
        
        # 模型配置
        self.model_config = {}
    
    @abc.abstractmethod
    async def _execute(self, prompt: str, **kwargs) -> ToolResponse:
        """
        执行语言模型工具的具体实现
        
        Args:
            prompt: 提示词
            **kwargs: 其他参数
            
        Returns:
            ToolResponse: 执行结果
        """
        pass
    
    def set_llm_client(self, llm_client):
        """
        设置语言模型客户端
        
        Args:
            llm_client: 语言模型客户端实例
        """
        self.llm_client = llm_client
        self.logger.info(f"LLM client set: {llm_client.__class__.__name__}")
    
    def set_model_config(self, config: Dict[str, Any]):
        """
        设置模型配置
        
        Args:
            config: 模型配置参数
        """
        self.model_config = config
        self.logger.info(f"Model config updated")
    
    def get_model_config(self) -> Dict[str, Any]:
        """
        获取模型配置
        
        Returns:
            Dict: 模型配置参数
        """
        return self.model_config.copy()


class TextGenerationTool(LLMTool):
    """
    文本生成工具
    
    使用语言模型生成文本内容
    """
    
    def _initialize(self):
        """
        初始化文本生成工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "TextGenerationTool"
        self.description = "使用语言模型生成文本内容"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.7,
            'max_tokens': 1000,
            'top_p': 0.9,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0
        }
    
    async def _execute(self, prompt: str, **kwargs) -> ToolResponse:
        """
        执行文本生成
        
        Args:
            prompt: 提示词
            **kwargs: 生成参数
            
        Returns:
            ToolResponse: 生成的文本结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录生成请求
            self.logger.info(f"Generating text with prompt length: {len(prompt)} chars")
            
            # 调用语言模型客户端生成文本
            # 注意：这里假设llm_client有一个generate_text方法
            # 实际使用中需要根据具体的客户端实现进行调整
            if hasattr(self.llm_client, 'generate_text'):
                result = await self.llm_client.generate_text(prompt, **params)
            elif hasattr(self.llm_client, 'generate_response'):
                result = await self.llm_client.generate_response(prompt, **params)
            elif hasattr(self.llm_client, 'create_completion'):
                result = await self.llm_client.create_completion(prompt, **params)
            else:
                return self.format_response(
                    success=False,
                    error="LLM client does not have required method"
                )
            
            # 处理生成结果
            # 这里假设结果是一个字典，包含'content'字段
            # 实际使用中需要根据具体的客户端返回格式进行调整
            if isinstance(result, dict) and 'content' in result:
                generated_text = result['content']
            elif isinstance(result, str):
                generated_text = result
            else:
                # 尝试将结果转换为字符串
                try:
                    generated_text = str(result)
                except:
                    generated_text = ""
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=generated_text,
                prompt=prompt,
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)


class TextCompletionTool(LLMTool):
    """
    文本补全工具
    
    完成给定文本的续写或补全
    """
    
    def _initialize(self):
        """
        初始化文本补全工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "TextCompletionTool"
        self.description = "完成给定文本的续写或补全"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.5,
            'max_tokens': 500,
            'top_p': 0.8
        }
    
    async def _execute(self, text: str, **kwargs) -> ToolResponse:
        """
        执行文本补全
        
        Args:
            text: 要补全的文本
            **kwargs: 补全参数
            
        Returns:
            ToolResponse: 补全后的文本结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录补全请求
            self.logger.info(f"Completing text with length: {len(text)} chars")
            
            # 调用语言模型客户端进行文本补全
            # 这里使用TextGenerationTool的方法，但可以根据需要自定义
            completion = await TextGenerationTool._execute(self, text, **params)
            
            # 处理结果
            if completion.success:
                # 将原始文本和补全结果合并
                completed_text = text + completion.result
                
                return self.format_response(
                    success=True,
                    result=completed_text,
                    original_text=text,
                    completion=completion.result,
                    params=params
                )
            else:
                return completion
            
        except Exception as e:
            return self.handle_error(e)


class TextSummarizationTool(LLMTool):
    """
    文本摘要工具
    
    生成给定文本的摘要
    """
    
    def _initialize(self):
        """
        初始化文本摘要工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "TextSummarizationTool"
        self.description = "生成给定文本的摘要"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.3,
            'max_tokens': 300,
            'top_p': 0.7
        }
        
        # 默认摘要提示词模板
        self.summary_template = """请为以下文本生成一个简明扼要的摘要：

{text}

摘要："""
    
    async def _execute(self, text: str, summary_length: str = "medium", **kwargs) -> ToolResponse:
        """
        执行文本摘要
        
        Args:
            text: 要摘要的文本
            summary_length: 摘要长度，可选值：short, medium, long
            **kwargs: 摘要参数
            
        Returns:
            ToolResponse: 生成的摘要结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 根据摘要长度调整参数
            if summary_length == "short":
                params['max_tokens'] = 100
                length_instruction = "请保持摘要简洁，控制在100字以内。"
            elif summary_length == "long":
                params['max_tokens'] = 500
                length_instruction = "请提供详细的摘要，包含主要观点和关键细节。"
            else:
                params['max_tokens'] = 300
                length_instruction = "请提供中等长度的摘要，包含核心内容。"
            
            # 构建摘要提示词
            prompt = self.summary_template.format(text=text)
            prompt += f"\n{length_instruction}"
            
            # 记录摘要请求
            self.logger.info(f"Summarizing text with length: {len(text)} chars, target length: {summary_length}")
            
            # 调用语言模型客户端生成摘要
            result = await TextGenerationTool._execute(self, prompt, **params)
            
            # 处理结果
            if result.success:
                return self.format_response(
                    success=True,
                    result=result.result,
                    text_length=len(text),
                    summary_length=len(result.result),
                    params=params
                )
            else:
                return result
            
        except Exception as e:
            return self.handle_error(e)


class QuestionAnsweringTool(LLMTool):
    """
    问答工具
    
    基于给定的上下文回答问题
    """
    
    def _initialize(self):
        """
        初始化问答工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "QuestionAnsweringTool"
        self.description = "基于给定的上下文回答问题"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.2,
            'max_tokens': 500,
            'top_p': 0.7
        }
        
        # 默认问答提示词模板
        self.qa_template = """请根据以下上下文回答问题：

上下文：
{context}

问题：
{question}

回答："""
    
    async def _execute(self, question: str, context: str = "", **kwargs) -> ToolResponse:
        """
        执行问答
        
        Args:
            question: 问题
            context: 上下文信息
            **kwargs: 问答参数
            
        Returns:
            ToolResponse: 回答结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 构建问答提示词
            prompt = self.qa_template.format(context=context, question=question)
            
            # 记录问答请求
            self.logger.info(f"Answering question: {question[:50]}..., context length: {len(context)} chars")
            
            # 调用语言模型客户端生成回答
            result = await TextGenerationTool._execute(self, prompt, **params)
            
            # 处理结果
            if result.success:
                return self.format_response(
                    success=True,
                    result=result.result,
                    question=question,
                    has_context=bool(context),
                    params=params
                )
            else:
                return result
            
        except Exception as e:
            return self.handle_error(e)


class TranslationTool(LLMTool):
    """
    翻译工具
    
    将文本从一种语言翻译成另一种语言
    """
    
    def _initialize(self):
        """
        初始化翻译工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "TranslationTool"
        self.description = "将文本从一种语言翻译成另一种语言"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.2,
            'max_tokens': 2000,
            'top_p': 0.7
        }
        
        # 默认翻译提示词模板
        self.translation_template = """请将以下{source_language}文本翻译成{target_language}：

{text}

翻译结果："""
    
    async def _execute(self, text: str, source_language: str = "中文", target_language: str = "英文", **kwargs) -> ToolResponse:
        """
        执行翻译
        
        Args:
            text: 要翻译的文本
            source_language: 源语言
            target_language: 目标语言
            **kwargs: 翻译参数
            
        Returns:
            ToolResponse: 翻译结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 构建翻译提示词
            prompt = self.translation_template.format(
                source_language=source_language,
                target_language=target_language,
                text=text
            )
            
            # 记录翻译请求
            self.logger.info(f"Translating from {source_language} to {target_language}, text length: {len(text)} chars")
            
            # 调用语言模型客户端执行翻译
            result = await TextGenerationTool._execute(self, prompt, **params)
            
            # 处理结果
            if result.success:
                return self.format_response(
                    success=True,
                    result=result.result,
                    source_language=source_language,
                    target_language=target_language,
                    params=params
                )
            else:
                return result
            
        except Exception as e:
            return self.handle_error(e)


class TextClassificationTool(LLMTool):
    """
    文本分类工具
    
    对给定文本进行分类
    """
    
    def _initialize(self):
        """
        初始化文本分类工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "TextClassificationTool"
        self.description = "对给定文本进行分类"
        
        # 默认配置
        self.default_params = {
            'temperature': 0.1,
            'max_tokens': 100,
            'top_p': 0.7
        }
        
        # 默认分类提示词模板
        self.classification_template = """请将以下文本分类到给定的类别中：

文本：
{text}

类别列表：
{categories}

请直接返回分类结果，不要添加额外的解释。"""
    
    async def _execute(self, text: str, categories: List[str], **kwargs) -> ToolResponse:
        """
        执行文本分类
        
        Args:
            text: 要分类的文本
            categories: 类别列表
            **kwargs: 分类参数
            
        Returns:
            ToolResponse: 分类结果
        """
        try:
            # 检查语言模型客户端是否设置
            if not self.llm_client:
                return self.format_response(
                    success=False,
                    error="LLM client not set"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 格式化类别列表
            categories_str = "\n".join([f"- {cat}" for cat in categories])
            
            # 构建分类提示词
            prompt = self.classification_template.format(
                text=text,
                categories=categories_str
            )
            
            # 记录分类请求
            self.logger.info(f"Classifying text, {len(categories)} categories available")
            
            # 调用语言模型客户端执行分类
            result = await TextGenerationTool._execute(self, prompt, **params)
            
            # 处理结果
            if result.success:
                # 清理分类结果
                classification_result = result.result.strip()
                
                # 检查分类结果是否在类别列表中
                if classification_result not in categories:
                    # 尝试找到最匹配的类别
                    matched_category = None
                    for cat in categories:
                        if cat.lower() in classification_result.lower():
                            matched_category = cat
                            break
                    
                    if matched_category:
                        classification_result = matched_category
                    
                return self.format_response(
                    success=True,
                    result=classification_result,
                    categories=categories,
                    params=params
                )
            else:
                return result
            
        except Exception as e:
            return self.handle_error(e)