import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import httpx
from openai import OpenAI

logger = logging.getLogger("AutoRAG")

class FallbackLLMClient(object):
    """
    支持三个API回退机制的LLM客户端
    优先级: grok4 → doubao → deepseek
    """
    
    def __init__(self, project_dir: str, llm: str = "fallback", batch: int = 8, **kwargs):
        self.batch = batch
        self.project_dir = project_dir
        
        # 设置日志目录
        self.log_dir = Path(project_dir) / "logs" / "llm_calls"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建详细日志文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"llm_calls_{timestamp}.jsonl"
        
        # 初始化调用计数器
        self.call_counter = 0
        
        # API配置 - 请替换为您的实际API信息
        self.api_configs = {
            # "grok4": {
            #     "api_key": os.environ.get("GROK_API_KEY", ""),
            #     "base_url": "https://api.x.ai/v1",
            #     "model": "grok-4-0709",
            #     "proxy": os.environ.get("GROK_PROXY", "")
            # },
            "doubao": {
                "api_key": os.environ.get("DOUBAO_API_KEY", ""),
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-seed-1-6-flash-250615", #doubao-seed-1-6-flash-250615
                "proxy": None
            },
            "deepseek": {
                "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-chat",
                "proxy": None
            },
            "qwen": {
                "api_key": os.environ.get("QWEN_API_KEY", ""),
                "base_url": "https://api.qwen.com/v1",
                "model": "qwen-7b",
                "proxy": None
            }
        }
        
        # 初始化客户端
        self.clients = {}
        for name, config in self.api_configs.items():
            http_client = None
            if config.get("proxy"):
                http_client = httpx.Client(proxy=config["proxy"])
            self.clients[name] = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
                timeout=300,
                http_client=http_client
            )
        # 回退顺序，DeepSeek优先，然后是豆包，最后是通义千问
        self.fallback_order = ["deepseek", "doubao", "qwen"]
    
    def _log_llm_call(self, call_data: Dict[str, Any]):
        """记录LLM调用的详细信息"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(call_data, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logger.warning(f"写入LLM调用日志失败: {e}")
    
    def _pure(self, prompts: List[str], **kwargs) -> tuple:
        """
        使用回退机制生成文本
        """
        generated_texts = []
        generated_tokens = []
        generated_log_probs = []
        
        for prompt in prompts:
            result = self._generate_single(prompt, **kwargs)
            generated_texts.append(result[0])
            generated_tokens.append(result[1])
            generated_log_probs.append(result[2])
        
        return generated_texts, generated_tokens, generated_log_probs
    
    def _generate_single(self, prompt: str, **kwargs) -> tuple:
        """
        单个prompt的生成，支持回退机制，并记录详细日志
        """
        self.call_counter += 1
        call_start_time = datetime.now()
        
        # 准备日志数据结构
        log_data = {
            "call_id": self.call_counter,
            "timestamp": call_start_time.isoformat(),
            "prompt": prompt,
            "prompt_length": len(prompt),
            "kwargs": kwargs,
            "attempts": []
        }
        
        for api_name in self.fallback_order:
            attempt_start = datetime.now()
            attempt_data = {
                "api_name": api_name,
                "model": self.api_configs[api_name]["model"],
                "attempt_time": attempt_start.isoformat(),
                "success": False,
                "error": None,
                "response": None,
                "thinking": None,
                "duration_ms": 0
            }
            
            try:
                logger.info(f"[调用#{self.call_counter}] 尝试使用 {api_name} API")
                client = self.clients[api_name]
                config = self.api_configs[api_name]
                
                # 准备请求参数
                request_params = {
                    "model": config["model"],
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": kwargs.get("max_tokens", 2048),
                    "temperature": kwargs.get("temperature", 0.7),
                }
                
                # 添加其他参数
                for k, v in kwargs.items():
                    if k not in ["max_tokens", "temperature"]:
                        request_params[k] = v
                
                # 记录请求参数
                attempt_data["request_params"] = request_params.copy()
                
                # 调用API
                response = client.chat.completions.create(**request_params)
                
                # 计算耗时
                attempt_end = datetime.now()
                attempt_data["duration_ms"] = (attempt_end - attempt_start).total_seconds() * 1000
                
                # 提取响应内容
                message = response.choices[0].message
                text = message.content or ""
                
                # 提取thinking内容（如果存在）
                thinking_content = None
                if hasattr(message, 'reasoning') and message.reasoning:
                    thinking_content = message.reasoning
                elif "thinking" in text.lower() or "思考" in text:
                    thinking_markers = ["<thinking>", "思考过程：", "分析：", "推理："]
                    for marker in thinking_markers:
                        if marker in text:
                            thinking_content = text[text.find(marker):]
                            break
                
                tokens = list(range(len(text.split())))
                log_probs = [0.5] * len(tokens)
                
                attempt_data.update({
                    "success": True,
                    "response": {
                        "content": text,
                        "content_length": len(text),
                        "token_count": len(tokens),
                        "finish_reason": response.choices[0].finish_reason,
                        "usage": response.usage.model_dump() if response.usage else None
                    },
                    "thinking": thinking_content
                })
                
                log_data["attempts"].append(attempt_data)
                log_data["final_result"] = {
                    "success": True,
                    "used_api": api_name,
                    "total_duration_ms": (attempt_end - call_start_time).total_seconds() * 1000
                }
                
                self._log_llm_call(log_data)
                
                logger.info(f"[调用#{self.call_counter}] {api_name} API调用成功，耗时: {attempt_data['duration_ms']:.2f}ms")
                if thinking_content:
                    logger.info(f"[调用#{self.call_counter}] 检测到thinking内容: {thinking_content[:100]}...")
                
                return text, tokens, log_probs
                
            except Exception as e:
                attempt_end = datetime.now()
                attempt_data["duration_ms"] = (attempt_end - attempt_start).total_seconds() * 1000
                attempt_data["error"] = str(e)
                
                log_data["attempts"].append(attempt_data)
                
                logger.warning(f"[调用#{self.call_counter}] {api_name} API调用失败: {e}, 耗时: {attempt_data['duration_ms']:.2f}ms")
                
                if api_name == self.fallback_order[-1]:
                    final_end = datetime.now()
                    log_data["final_result"] = {
                        "success": False,
                        "error": "所有API都失败了",
                        "total_duration_ms": (final_end - call_start_time).total_seconds() * 1000
                    }
                    self._log_llm_call(log_data)
                    logger.error(f"[调用#{self.call_counter}] 所有API都失败了")
                    return "抱歉，当前无法生成回答。", [0], [0.0]
                continue
    
    async def astream(self, prompt: str, **kwargs):
        result = self._generate_single(prompt, **kwargs)
        yield result[0]
    
    def stream(self, prompt: str, **kwargs):
        result = self._generate_single(prompt, **kwargs)
        yield result[0]
    
    def get_call_statistics(self) -> Dict[str, Any]:
        if not self.log_file.exists():
            return {"total_calls": 0, "api_usage": {}}
        
        stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "api_usage": {},
            "average_duration_ms": 0,
            "total_tokens": 0
        }
        
        total_duration = 0
        total_tokens = 0
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        call_data = json.loads(line)
                        stats["total_calls"] += 1
                        
                        if call_data.get("final_result", {}).get("success", False):
                            stats["successful_calls"] += 1
                            used_api = call_data["final_result"]["used_api"]
                            stats["api_usage"][used_api] = stats["api_usage"].get(used_api, 0) + 1
                            response = call_data["final_result"].get("response", {})
                            if "usage" in response and response["usage"]:
                                total_tokens += response["usage"].get("total_tokens", 0)
                        else:
                            stats["failed_calls"] += 1
                        if "total_duration_ms" in call_data.get("final_result", {}):
                            total_duration += call_data["final_result"]["total_duration_ms"]
        
        except Exception as e:
            logger.warning(f"读取调用统计失败: {e}")
        
        if stats["total_calls"] > 0:
            stats["average_duration_ms"] = total_duration / stats["total_calls"]
        stats["total_tokens"] = total_tokens
        
        return stats