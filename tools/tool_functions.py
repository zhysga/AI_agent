"""
工具函数实现
"""
import os
import sys
import json
import yaml
import datetime
import time
import re
import hashlib
import base64
import random
import math
import statistics
import traceback
from typing import Dict, Any, Optional, List, Union, Tuple, Callable, Generator
import logging
import importlib
import inspect

# 导入工具基础类
from .base_tool import BaseTool, ToolResponse


# 工具函数注册器
class ToolFunctionRegistry:
    """
    工具函数注册器
    
    用于注册和管理工具函数
    """
    
    def __init__(self):
        """
        初始化工具函数注册器
        """
        # 存储注册的工具函数
        self._tool_functions: Dict[str, Callable] = {}
        
        # 存储工具函数的元数据
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("ToolFunctionRegistry initialized")
    
    def register(self, name: str = None, description: str = None, **metadata):
        """
        注册工具函数的装饰器
        
        Args:
            name: 工具函数名称，如果为None则使用函数名
            description: 工具函数描述
            **metadata: 其他元数据
        
        Returns:
            Callable: 装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            # 使用函数名作为工具名称（如果未指定）
            tool_name = name if name is not None else func.__name__
            
            # 生成函数描述（如果未指定）
            tool_description = description
            if tool_description is None:
                # 使用函数文档字符串作为描述
                if func.__doc__:
                    tool_description = func.__doc__.strip().split('\n')[0]  # 只取第一行
                else:
                    tool_description = f"Tool function {tool_name}"
            
            # 获取函数签名信息
            signature = inspect.signature(func)
            params = {}
            
            # 分析函数参数
            for param_name, param in signature.parameters.items():
                param_info = {
                    'name': param_name,
                    'type': 'any',  # 默认类型
                    'required': param.default is inspect.Parameter.empty
                }
                
                # 尝试获取参数类型注释
                if param.annotation is not inspect.Parameter.empty:
                    param_info['type'] = str(param.annotation)
                
                # 如果有默认值，记录默认值
                if param.default is not inspect.Parameter.empty:
                    param_info['default'] = param.default
                
                params[param_name] = param_info
            
            # 构建工具元数据
            tool_metadata = {
                'name': tool_name,
                'description': tool_description,
                'function': func,
                'params': params,
                'return_type': 'any',  # 默认返回类型
                **metadata
            }
            
            # 尝试获取返回值类型注释
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                tool_metadata['return_type'] = str(func.__annotations__['return'])
            
            # 注册工具函数
            self._tool_functions[tool_name] = func
            self._tool_metadata[tool_name] = tool_metadata
            
            self.logger.info(f"Registered tool function: {tool_name}")
            
            # 返回原函数
            return func
        
        return decorator
    
    def unregister(self, name: str) -> bool:
        """
        注销工具函数
        
        Args:
            name: 工具函数名称
            
        Returns:
            bool: 是否成功注销
        """
        if name in self._tool_functions:
            del self._tool_functions[name]
            del self._tool_metadata[name]
            self.logger.info(f"Unregistered tool function: {name}")
            return True
        
        self.logger.warning(f"Tool function not found: {name}")
        return False
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        获取工具函数
        
        Args:
            name: 工具函数名称
            
        Returns:
            Optional[Callable]: 工具函数
        """
        return self._tool_functions.get(name)
    
    def get_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具函数的元数据
        
        Args:
            name: 工具函数名称
            
        Returns:
            Optional[Dict]: 工具函数的元数据
        """
        return self._tool_metadata.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有注册的工具函数
        
        Returns:
            List[Dict]: 工具函数列表
        """
        return list(self._tool_metadata.values())
    
    def find_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        根据查询条件查找工具函数
        
        Args:
            query: 搜索查询
            
        Returns:
            List[Dict]: 匹配的工具函数列表
        """
        query = query.lower()
        results = []
        
        for metadata in self._tool_metadata.values():
            # 在名称、描述和参数中搜索
            if (query in metadata['name'].lower() or 
                query in metadata['description'].lower() or 
                any(query in param['name'].lower() for param in metadata['params'].values())):
                results.append(metadata)
        
        return results
    
    def clear(self):
        """
        清除所有注册的工具函数
        """
        self._tool_functions.clear()
        self._tool_metadata.clear()
        self.logger.info("Cleared all tool functions")


# 全局工具函数注册器实例
tool_registry = ToolFunctionRegistry()

# 导出注册器的方法供外部使用
def register_tool(name: str = None, description: str = None, **metadata):
    """
    注册工具函数的装饰器
    """
    return tool_registry.register(name=name, description=description, **metadata)

def unregister_tool(name: str) -> bool:
    """
    注销工具函数
    """
    return tool_registry.unregister(name)

def get_tool(name: str) -> Optional[Callable]:
    """
    获取工具函数
    """
    return tool_registry.get_tool(name)

def get_tool_metadata(name: str) -> Optional[Dict[str, Any]]:
    """
    获取工具函数的元数据
    """
    return tool_registry.get_metadata(name)

def list_tools() -> List[Dict[str, Any]]:
    """
    列出所有注册的工具函数
    """
    return tool_registry.list_tools()

def find_tools(query: str) -> List[Dict[str, Any]]:
    """
    根据查询条件查找工具函数
    """
    return tool_registry.find_tools(query)

def clear_tools():
    """
    清除所有注册的工具函数
    """
    return tool_registry.clear()


# 文本处理工具函数
@register_tool(description="处理和转换文本")
def text_processor(text: str, operation: str = "clean", **kwargs) -> Dict[str, Any]:
    """
    处理和转换文本
    
    Args:
        text: 要处理的文本
        operation: 处理操作（clean, uppercase, lowercase, title, strip, replace, split, join）
        **kwargs: 操作参数
        
    Returns:
        Dict: 处理结果
    """
    try:
        result = {
            'original_text': text,
            'operation': operation,
            'processed_text': text
        }
        
        # 根据操作类型执行相应的文本处理
        if operation.lower() == "clean":
            # 清理文本：去除多余的空白字符，处理换行符等
            processed_text = re.sub(r'\s+', ' ', text).strip()
            result['processed_text'] = processed_text
        elif operation.lower() == "uppercase":
            # 转换为大写
            result['processed_text'] = text.upper()
        elif operation.lower() == "lowercase":
            # 转换为小写
            result['processed_text'] = text.lower()
        elif operation.lower() == "title":
            # 转换为标题格式（每个单词首字母大写）
            result['processed_text'] = text.title()
        elif operation.lower() == "strip":
            # 去除首尾空白字符
            result['processed_text'] = text.strip()
        elif operation.lower() == "replace":
            # 替换文本中的内容
            old_str = kwargs.get("old", "")
            new_str = kwargs.get("new", "")
            result['processed_text'] = text.replace(old_str, new_str)
            result['old_str'] = old_str
            result['new_str'] = new_str
        elif operation.lower() == "split":
            # 分割文本
            separator = kwargs.get("separator", " ")
            maxsplit = kwargs.get("maxsplit", -1)
            split_result = text.split(separator, maxsplit)
            result['processed_text'] = split_result
            result['separator'] = separator
            result['maxsplit'] = maxsplit
            result['split_count'] = len(split_result)
        elif operation.lower() == "join":
            # 连接文本
            if isinstance(text, list):
                separator = kwargs.get("separator", "")
                result['processed_text'] = separator.join(text)
                result['separator'] = separator
            else:
                raise ValueError("Input must be a list for join operation")
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        # 计算处理前后的文本长度变化
        original_length = len(text) if isinstance(text, str) else len(str(text))
        processed_length = len(result['processed_text']) if isinstance(result['processed_text'], str) else len(str(result['processed_text']))
        
        result['original_length'] = original_length
        result['processed_length'] = processed_length
        result['length_change'] = processed_length - original_length
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'original_text': text,
            'operation': operation
        }


@register_tool(description="提取文本中的关键信息")
def text_extractor(text: str, pattern: str = None, extract_type: str = "regex", **kwargs) -> Dict[str, Any]:
    """
    提取文本中的关键信息
    
    Args:
        text: 要提取信息的文本
        pattern: 提取模式（正则表达式或关键词）
        extract_type: 提取类型（regex, keyword, email, phone, url, number, date）
        **kwargs: 提取参数
        
    Returns:
        Dict: 提取结果
    """
    try:
        result = {
            'original_text': text,
            'pattern': pattern,
            'extract_type': extract_type,
            'extracted_data': []
        }
        
        # 根据提取类型执行相应的提取操作
        if extract_type.lower() == "regex" and pattern:
            # 使用正则表达式提取
            matches = re.findall(pattern, text)
            result['extracted_data'] = matches
            result['match_count'] = len(matches)
        elif extract_type.lower() == "keyword" and pattern:
            # 使用关键词提取
            pattern = pattern.lower()
            text_lower = text.lower()
            count = text_lower.count(pattern)
            positions = [m.start() for m in re.finditer(pattern, text_lower)]
            result['extracted_data'] = {
                'keyword': pattern,
                'count': count,
                'positions': positions
            }
        elif extract_type.lower() == "email":
            # 提取电子邮件地址
            email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
            emails = re.findall(email_pattern, text)
            # 去重
            emails = list(set(emails))
            result['extracted_data'] = emails
            result['match_count'] = len(emails)
        elif extract_type.lower() == "phone":
            # 提取电话号码（支持多种格式）
            phone_pattern = r"(?:\+?\d{1,4}[-.\s]?)?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}"
            phones = re.findall(phone_pattern, text)
            # 清理和去重
            phones = [re.sub(r'\D', '', phone) for phone in phones]  # 只保留数字
            phones = [phone for phone in phones if len(phone) >= 7]  # 至少7位数字
            phones = list(set(phones))
            result['extracted_data'] = phones
            result['match_count'] = len(phones)
        elif extract_type.lower() == "url":
            # 提取URL
            url_pattern = r"https?://[^\s]+"
            urls = re.findall(url_pattern, text)
            # 去重
            urls = list(set(urls))
            result['extracted_data'] = urls
            result['match_count'] = len(urls)
        elif extract_type.lower() == "number":
            # 提取数字
            number_pattern = r"-?\d+(?:\.\d+)?"
            numbers = re.findall(number_pattern, text)
            # 转换为数字类型
            numbers = [float(num) if '.' in num else int(num) for num in numbers]
            result['extracted_data'] = numbers
            result['match_count'] = len(numbers)
            # 计算统计信息
            if numbers:
                result['statistics'] = {
                    'min': min(numbers),
                    'max': max(numbers),
                    'sum': sum(numbers),
                    'average': sum(numbers) / len(numbers)
                }
        elif extract_type.lower() == "date":
            # 提取日期（支持多种格式）
            date_patterns = [
                r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
                r"\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
                r"\d{2}/\d{2}/\d{2}",  # MM/DD/YY
                r"\d{4}/\d{2}/\d{2}",  # YYYY/MM/DD
                r"\d{2}-\d{2}-\d{4}"   # DD-MM-YYYY
            ]
            
            dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                dates.extend(matches)
            
            # 去重
            dates = list(set(dates))
            result['extracted_data'] = dates
            result['match_count'] = len(dates)
        else:
            raise ValueError(f"Unsupported extract type or missing pattern: {extract_type}")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'original_text': text,
            'pattern': pattern,
            'extract_type': extract_type
        }


# 数据转换工具函数
@register_tool(description="在不同数据格式之间转换")
def data_converter(data: Any, from_format: str = "auto", to_format: str = "json", **kwargs) -> Dict[str, Any]:
    """
    在不同数据格式之间转换
    
    Args:
        data: 要转换的数据
        from_format: 源数据格式（auto, json, yaml, csv, xml, string, dict, list）
        to_format: 目标数据格式（json, yaml, csv, xml, string, dict, list）
        **kwargs: 转换参数
        
    Returns:
        Dict: 转换结果
    """
    try:
        result = {
            'from_format': from_format,
            'to_format': to_format,
            'converted_data': None
        }
        
        # 解析源数据
        parsed_data = data
        
        if from_format.lower() == "auto":
            # 尝试自动检测数据格式
            if isinstance(data, dict) or isinstance(data, list):
                from_format = "dict" if isinstance(data, dict) else "list"
            elif isinstance(data, str):
                # 尝试解析为JSON
                try:
                    parsed_data = json.loads(data)
                    from_format = "json"
                except json.JSONDecodeError:
                    # 尝试解析为YAML
                    try:
                        parsed_data = yaml.safe_load(data)
                        from_format = "yaml"
                    except yaml.YAMLError:
                        # 默认视为字符串
                        from_format = "string"
        elif from_format.lower() == "json" and isinstance(data, str):
            # 从JSON字符串解析
            parsed_data = json.loads(data)
        elif from_format.lower() == "yaml" and isinstance(data, str):
            # 从YAML字符串解析
            parsed_data = yaml.safe_load(data)
        elif from_format.lower() == "csv" and isinstance(data, str):
            # 从CSV字符串解析
            import csv
            from io import StringIO
            
            reader = csv.DictReader(StringIO(data))
            parsed_data = list(reader)
        
        # 更新结果中的源格式
        result['from_format'] = from_format
        
        # 转换为目标格式
        if to_format.lower() == "json":
            # 转换为JSON字符串
            result['converted_data'] = json.dumps(parsed_data, indent=kwargs.get('indent', 2), ensure_ascii=False)
        elif to_format.lower() == "yaml" or to_format.lower() == "yml":
            # 转换为YAML字符串
            result['converted_data'] = yaml.dump(parsed_data, default_flow_style=False, allow_unicode=True, **kwargs)
        elif to_format.lower() == "csv" and (isinstance(parsed_data, list) and len(parsed_data) > 0):
            # 转换为CSV字符串
            import csv
            from io import StringIO
            
            if isinstance(parsed_data[0], dict):
                # 获取所有字段名
                fieldnames = set()
                for item in parsed_data:
                    fieldnames.update(item.keys())
                fieldnames = sorted(fieldnames)  # 排序以保持一致性
                
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(parsed_data)
                
                result['converted_data'] = output.getvalue()
            else:
                raise ValueError("Data must be a list of dictionaries to convert to CSV")
        elif to_format.lower() == "xml":
            # 转换为XML字符串
            # 注意：这是一个简化的XML转换实现，可能需要根据具体需求进行扩展
            def dict_to_xml(data, root_tag="root", indent=0):
                """将字典转换为XML字符串"""
                spaces = "  " * indent
                if isinstance(data, dict):
                    xml = [f"{spaces}<{root_tag}>"]
                    for key, value in data.items():
                        xml.append(dict_to_xml(value, key, indent + 1))
                    xml.append(f"{spaces}</{root_tag}>")
                    return "\n".join(xml)
                elif isinstance(data, list):
                    xml = []
                    for i, item in enumerate(data):
                        xml.append(dict_to_xml(item, f"{root_tag}_item" if i > 0 else root_tag, indent))
                    return "\n".join(xml)
                else:
                    # 处理基本类型
                    value = str(data)
                    # 对特殊字符进行转义
                    value = value.replace("&", "&amp;")
                    value = value.replace("<", "&lt;")
                    value = value.replace(">", "&gt;")
                    value = value.replace('"', "&quot;")
                    value = value.replace("'", "&apos;")
                    return f"{spaces}<{root_tag}>{value}</{root_tag}>"
            
            result['converted_data'] = dict_to_xml(parsed_data)
        elif to_format.lower() == "string":
            # 转换为字符串
            result['converted_data'] = str(parsed_data)
        elif to_format.lower() == "dict" and (isinstance(parsed_data, str)):
            # 尝试将字符串解析为字典
            if from_format.lower() in ["json", "yaml", "yml"]:
                # 已经是解析后的数据
                result['converted_data'] = parsed_data if isinstance(parsed_data, dict) else {"data": parsed_data}
            else:
                # 尝试解析为JSON
                try:
                    result['converted_data'] = json.loads(parsed_data)
                except (json.JSONDecodeError, TypeError):
                    # 如果失败，返回包含原字符串的字典
                    result['converted_data'] = {"data": parsed_data}
        elif to_format.lower() == "list" and (isinstance(parsed_data, str)):
            # 尝试将字符串解析为列表
            if from_format.lower() in ["json", "yaml", "yml"]:
                # 已经是解析后的数据
                result['converted_data'] = parsed_data if isinstance(parsed_data, list) else [parsed_data]
            else:
                # 尝试解析为JSON
                try:
                    result['converted_data'] = json.loads(parsed_data)
                except (json.JSONDecodeError, TypeError):
                    # 如果失败，返回包含原字符串的列表
                    result['converted_data'] = [parsed_data]
        else:
            raise ValueError(f"Unsupported conversion: {from_format} to {to_format}")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'from_format': from_format,
            'to_format': to_format
        }


# 数学计算工具函数
@register_tool(description="执行数学计算")
def math_calculator(expression: str = None, operation: str = None, numbers: List[Union[int, float]] = None, **kwargs) -> Dict[str, Any]:
    """
    执行数学计算
    
    Args:
        expression: 数学表达式字符串（如"2 + 3 * 4"）
        operation: 数学运算（add, subtract, multiply, divide, power, sqrt, min, max, sum, average, median, mode）
        numbers: 要运算的数字列表
        **kwargs: 计算参数
        
    Returns:
        Dict: 计算结果
    """
    try:
        result = {
            'expression': expression,
            'operation': operation,
            'numbers': numbers,
            'result': None
        }
        
        # 根据计算类型执行相应的计算
        if expression:
            # 执行数学表达式计算
            # 注意：使用eval有安全风险，这里进行了简单的安全检查
            # 仅允许基本的数学运算和函数
            safe_chars = set("0123456789.+-*/()[]{} ")
            safe_functions = {"abs", "round", "min", "max", "sum", "pow", "sqrt", "sin", "cos", "tan", "log", "exp"}
            
            # 检查表达式是否只包含安全字符和函数
            for char in expression:
                if char not in safe_chars:
                    # 检查是否是安全函数的一部分
                    found = False
                    for func in safe_functions:
                        if func in expression:
                            # 确保函数名是完整的，不是其他单词的一部分
                            # 这是一个简化的检查，可能需要更复杂的词法分析
                            if re.search(rf"\b{func}\b", expression):
                                found = True
                                break
                    if not found:
                        raise ValueError(f"Unsafe character in expression: {char}")
            
            # 准备安全的全局变量（只包含允许的数学函数）
            safe_globals = {}
            for func_name in safe_functions:
                if hasattr(math, func_name):
                    safe_globals[func_name] = getattr(math, func_name)
                elif func_name == "sum":
                    safe_globals[func_name] = sum
            
            # 执行计算
            result['result'] = eval(expression, {"__builtins__": {}}, safe_globals)
        elif operation and numbers:
            # 执行指定的数学运算
            if not isinstance(numbers, list):
                numbers = [numbers]
            
            # 转换所有数字为浮点数
            numbers = [float(num) for num in numbers]
            
            if operation.lower() == "add":
                # 加法
                result['result'] = sum(numbers)
            elif operation.lower() == "subtract":
                # 减法（从第一个数减去后续所有数）
                if len(numbers) < 2:
                    raise ValueError("At least 2 numbers are required for subtraction")
                result['result'] = numbers[0] - sum(numbers[1:])
            elif operation.lower() == "multiply":
                # 乘法
                product = 1
                for num in numbers:
                    product *= num
                result['result'] = product
            elif operation.lower() == "divide":
                # 除法（第一个数除以第二个数）
                if len(numbers) != 2:
                    raise ValueError("Exactly 2 numbers are required for division")
                if numbers[1] == 0:
                    raise ValueError("Division by zero is not allowed")
                result['result'] = numbers[0] / numbers[1]
            elif operation.lower() == "power":
                # 幂运算（第一个数的第二个数次幂）
                if len(numbers) != 2:
                    raise ValueError("Exactly 2 numbers are required for power operation")
                result['result'] = math.pow(numbers[0], numbers[1])
            elif operation.lower() == "sqrt":
                # 平方根
                if len(numbers) != 1:
                    raise ValueError("Exactly 1 number is required for square root")
                if numbers[0] < 0:
                    raise ValueError("Cannot calculate square root of a negative number")
                result['result'] = math.sqrt(numbers[0])
            elif operation.lower() == "min":
                # 最小值
                result['result'] = min(numbers)
            elif operation.lower() == "max":
                # 最大值
                result['result'] = max(numbers)
            elif operation.lower() == "sum":
                # 总和
                result['result'] = sum(numbers)
            elif operation.lower() == "average" or operation.lower() == "mean":
                # 平均值
                result['result'] = sum(numbers) / len(numbers)
            elif operation.lower() == "median":
                # 中位数
                sorted_numbers = sorted(numbers)
                n = len(sorted_numbers)
                if n % 2 == 0:
                    # 偶数个数字，取中间两个数的平均值
                    result['result'] = (sorted_numbers[n//2 - 1] + sorted_numbers[n//2]) / 2
                else:
                    # 奇数个数字，取中间的数
                    result['result'] = sorted_numbers[n//2]
            elif operation.lower() == "mode":
                # 众数
                from collections import Counter
                counter = Counter(numbers)
                max_count = max(counter.values())
                modes = [num for num, count in counter.items() if count == max_count]
                result['result'] = modes[0] if len(modes) == 1 else modes
            else:
                raise ValueError(f"Unsupported operation: {operation}")
        else:
            raise ValueError("Either expression or operation with numbers must be provided")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'expression': expression,
            'operation': operation,
            'numbers': numbers
        }


# 日期和时间工具函数
@register_tool(description="处理日期和时间")
def datetime_tool(operation: str = "now", datetime_str: str = None, format_str: str = "%Y-%m-%d %H:%M:%S", **kwargs) -> Dict[str, Any]:
    """
    处理日期和时间
    
    Args:
        operation: 操作类型（now, parse, format, add, subtract, difference）
        datetime_str: 日期时间字符串
        format_str: 日期时间格式字符串
        **kwargs: 操作参数
        
    Returns:
        Dict: 处理结果
    """
    try:
        result = {
            'operation': operation,
            'datetime_str': datetime_str,
            'format_str': format_str,
            'result': None
        }
        
        # 根据操作类型执行相应的日期时间处理
        if operation.lower() == "now":
            # 获取当前时间
            now = datetime.datetime.now()
            result['result'] = now.strftime(format_str)
            result['timestamp'] = now.timestamp()
        elif operation.lower() == "parse" and datetime_str and format_str:
            # 解析日期时间字符串
            parsed_datetime = datetime.datetime.strptime(datetime_str, format_str)
            result['result'] = parsed_datetime
            result['timestamp'] = parsed_datetime.timestamp()
        elif operation.lower() == "format" and datetime_str and format_str:
            # 格式化日期时间字符串
            # 先解析，再格式化
            # 尝试自动检测输入格式
            input_formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y",
                "%d-%m-%Y %H:%M:%S",
                "%d-%m-%Y %H:%M",
                "%d-%m-%Y",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d"
            ]
            
            parsed_datetime = None
            for fmt in input_formats:
                try:
                    parsed_datetime = datetime.datetime.strptime(datetime_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_datetime is None:
                raise ValueError(f"Cannot parse datetime string: {datetime_str}")
            
            result['result'] = parsed_datetime.strftime(format_str)
            result['timestamp'] = parsed_datetime.timestamp()
        elif operation.lower() == "add" and datetime_str and format_str:
            # 向日期时间添加时间间隔
            # 解析日期时间字符串
            parsed_datetime = datetime.datetime.strptime(datetime_str, format_str)
            
            # 获取时间间隔参数
            days = kwargs.get('days', 0)
            hours = kwargs.get('hours', 0)
            minutes = kwargs.get('minutes', 0)
            seconds = kwargs.get('seconds', 0)
            
            # 添加时间间隔
            new_datetime = parsed_datetime + datetime.timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            )
            
            result['result'] = new_datetime.strftime(format_str)
            result['timestamp'] = new_datetime.timestamp()
            result['added_interval'] = {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds
            }
        elif operation.lower() == "subtract" and datetime_str and format_str:
            # 从日期时间减去时间间隔
            # 解析日期时间字符串
            parsed_datetime = datetime.datetime.strptime(datetime_str, format_str)
            
            # 获取时间间隔参数
            days = kwargs.get('days', 0)
            hours = kwargs.get('hours', 0)
            minutes = kwargs.get('minutes', 0)
            seconds = kwargs.get('seconds', 0)
            
            # 减去时间间隔
            new_datetime = parsed_datetime - datetime.timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            )
            
            result['result'] = new_datetime.strftime(format_str)
            result['timestamp'] = new_datetime.timestamp()
            result['subtracted_interval'] = {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds
            }
        elif operation.lower() == "difference":
            # 计算两个日期时间之间的差异
            # 获取两个日期时间字符串
            datetime_str1 = kwargs.get('datetime_str1')
            datetime_str2 = kwargs.get('datetime_str2')
            format_str1 = kwargs.get('format_str1', format_str)
            format_str2 = kwargs.get('format_str2', format_str)
            
            if not datetime_str1 or not datetime_str2:
                raise ValueError("Both datetime_str1 and datetime_str2 are required for difference operation")
            
            # 解析日期时间字符串
            dt1 = datetime.datetime.strptime(datetime_str1, format_str1)
            dt2 = datetime.datetime.strptime(datetime_str2, format_str2)
            
            # 计算差异
            diff = dt2 - dt1
            
            # 将差异转换为各种时间单位
            total_seconds = diff.total_seconds()
            days = diff.days
            hours = total_seconds // 3600
            minutes = total_seconds // 60 % 60
            seconds = total_seconds % 60
            
            result['result'] = {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'total_seconds': total_seconds,
                'total_minutes': total_seconds / 60,
                'total_hours': total_seconds / 3600,
                'total_days': total_seconds / (3600 * 24)
            }
        else:
            raise ValueError(f"Unsupported operation or missing parameters: {operation}")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'operation': operation,
            'datetime_str': datetime_str,
            'format_str': format_str
        }


# 文件处理工具函数
@register_tool(description="处理文件操作")
def file_tool(operation: str, file_path: str, **kwargs) -> Dict[str, Any]:
    """
    处理文件操作
    
    Args:
        operation: 操作类型（read, write, append, delete, exists, info, list, copy, move, rename）
        file_path: 文件路径
        **kwargs: 操作参数
        
    Returns:
        Dict: 操作结果
    """
    try:
        result = {
            'operation': operation,
            'file_path': file_path
        }
        
        # 规范化文件路径
        file_path = os.path.abspath(os.path.normpath(file_path))
        result['file_path'] = file_path
        
        # 根据操作类型执行相应的文件操作
        if operation.lower() == "read":
            # 读取文件
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")
            
            # 获取读取参数
            mode = kwargs.get('mode', 'r')
            encoding = kwargs.get('encoding', 'utf-8')
            
            # 读取文件内容
            with open(file_path, mode=mode, encoding=encoding if 'b' not in mode else None) as f:
                content = f.read()
            
            result['content'] = content
            result['file_size'] = os.path.getsize(file_path)
        elif operation.lower() == "write":
            # 写入文件
            # 获取写入参数
            content = kwargs.get('content', '')
            mode = kwargs.get('mode', 'w')
            encoding = kwargs.get('encoding', 'utf-8')
            overwrite = kwargs.get('overwrite', True)
            
            # 检查文件是否已存在
            if os.path.exists(file_path) and not overwrite:
                raise FileExistsError(f"File already exists and overwrite is not allowed: {file_path}")
            
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # 写入文件内容
            with open(file_path, mode=mode, encoding=encoding if 'b' not in mode else None) as f:
                f.write(content)
            
            result['written'] = True
            result['file_size'] = os.path.getsize(file_path)
        elif operation.lower() == "append":
            # 追加内容到文件
            # 获取追加参数
            content = kwargs.get('content', '')
            encoding = kwargs.get('encoding', 'utf-8')
            
            # 确保文件存在
            if not os.path.exists(file_path):
                # 确保目录存在
                directory = os.path.dirname(file_path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                
                # 创建空文件
                with open(file_path, 'w', encoding=encoding) as f:
                    pass
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")
            
            # 追加内容
            with open(file_path, 'a', encoding=encoding) as f:
                f.write(content)
            
            result['appended'] = True
            result['file_size'] = os.path.getsize(file_path)
        elif operation.lower() == "delete":
            # 删除文件
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")
            
            # 删除文件
            os.remove(file_path)
            
            result['deleted'] = True
        elif operation.lower() == "exists":
            # 检查文件是否存在
            exists = os.path.exists(file_path)
            is_file = os.path.isfile(file_path) if exists else False
            is_dir = os.path.isdir(file_path) if exists else False
            
            result['exists'] = exists
            result['is_file'] = is_file
            result['is_directory'] = is_dir
            
            if exists:
                # 获取文件信息
                stat_info = os.stat(file_path)
                result['file_size'] = stat_info.st_size
                result['created_time'] = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()
                result['modified_time'] = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        elif operation.lower() == "info":
            # 获取文件信息
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # 获取文件状态信息
            stat_info = os.stat(file_path)
            
            result['is_file'] = os.path.isfile(file_path)
            result['is_directory'] = os.path.isdir(file_path)
            result['file_size'] = stat_info.st_size
            result['created_time'] = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()
            result['modified_time'] = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat()
            result['access_time'] = datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat()
            result['mode'] = stat_info.st_mode
            result['uid'] = stat_info.st_uid
            result['gid'] = stat_info.st_gid
            
            # 如果是文件，获取文件扩展名
            if result['is_file']:
                _, extension = os.path.splitext(file_path)
                result['extension'] = extension.lower()
        elif operation.lower() == "list":
            # 列出目录内容
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Directory not found: {file_path}")
            
            # 检查是否是目录
            if not os.path.isdir(file_path):
                raise NotADirectoryError(f"Path is not a directory: {file_path}")
            
            # 获取列表参数
            recursive = kwargs.get('recursive', False)
            pattern = kwargs.get('pattern', None)
            
            files = []
            directories = []
            
            if recursive:
                # 递归列出所有文件和目录
                for root, dirs, filenames in os.walk(file_path):
                    for dir_name in dirs:
                        dir_full_path = os.path.join(root, dir_name)
                        rel_path = os.path.relpath(dir_full_path, file_path)
                        directories.append({
                            'name': dir_name,
                            'path': dir_full_path,
                            'relative_path': rel_path
                        })
                    
                    for filename in filenames:
                        if pattern and not re.match(pattern, filename):
                            continue
                        
                        file_full_path = os.path.join(root, filename)
                        rel_path = os.path.relpath(file_full_path, file_path)
                        file_size = os.path.getsize(file_full_path)
                        
                        files.append({
                            'name': filename,
                            'path': file_full_path,
                            'relative_path': rel_path,
                            'size': file_size
                        })
            else:
                # 只列出当前目录
                for item in os.listdir(file_path):
                    item_full_path = os.path.join(file_path, item)
                    
                    if os.path.isdir(item_full_path):
                        directories.append({
                            'name': item,
                            'path': item_full_path,
                            'relative_path': item
                        })
                    else:
                        if pattern and not re.match(pattern, item):
                            continue
                        
                        file_size = os.path.getsize(item_full_path)
                        files.append({
                            'name': item,
                            'path': item_full_path,
                            'relative_path': item,
                            'size': file_size
                        })
            
            result['files'] = files
            result['directories'] = directories
            result['total_files'] = len(files)
            result['total_directories'] = len(directories)
            result['recursive'] = recursive
        elif operation.lower() == "copy":
            # 复制文件
            # 获取目标路径
            destination = kwargs.get('destination')
            if not destination:
                raise ValueError("Destination path is required for copy operation")
            
            # 规范化目标路径
            destination = os.path.abspath(os.path.normpath(destination))
            
            # 检查源文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file not found: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Source path is a directory, not a file: {file_path}")
            
            # 确保目标目录存在
            destination_dir = os.path.dirname(destination)
            if destination_dir and not os.path.exists(destination_dir):
                os.makedirs(destination_dir, exist_ok=True)
            
            # 检查目标文件是否已存在
            overwrite = kwargs.get('overwrite', True)
            if os.path.exists(destination) and not overwrite:
                raise FileExistsError(f"Destination file already exists and overwrite is not allowed: {destination}")
            
            # 复制文件
            import shutil
            shutil.copy2(file_path, destination)
            
            result['destination'] = destination
            result['copied'] = True
        elif operation.lower() == "move":
            # 移动文件
            # 获取目标路径
            destination = kwargs.get('destination')
            if not destination:
                raise ValueError("Destination path is required for move operation")
            
            # 规范化目标路径
            destination = os.path.abspath(os.path.normpath(destination))
            
            # 检查源文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file not found: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Source path is a directory, not a file: {file_path}")
            
            # 确保目标目录存在
            destination_dir = os.path.dirname(destination)
            if destination_dir and not os.path.exists(destination_dir):
                os.makedirs(destination_dir, exist_ok=True)
            
            # 检查目标文件是否已存在
            overwrite = kwargs.get('overwrite', True)
            if os.path.exists(destination) and not overwrite:
                raise FileExistsError(f"Destination file already exists and overwrite is not allowed: {destination}")
            
            # 移动文件
            import shutil
            shutil.move(file_path, destination)
            
            result['destination'] = destination
            result['moved'] = True
        elif operation.lower() == "rename":
            # 重命名文件
            # 获取新名称
            new_name = kwargs.get('new_name')
            if not new_name:
                raise ValueError("New name is required for rename operation")
            
            # 构建新路径
            directory = os.path.dirname(file_path)
            new_path = os.path.join(directory, new_name)
            
            # 检查源文件是否存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Source file not found: {file_path}")
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                raise IsADirectoryError(f"Source path is a directory, not a file: {file_path}")
            
            # 检查目标文件是否已存在
            overwrite = kwargs.get('overwrite', True)
            if os.path.exists(new_path) and not overwrite:
                raise FileExistsError(f"File with new name already exists and overwrite is not allowed: {new_path}")
            
            # 重命名文件
            os.rename(file_path, new_path)
            
            result['new_name'] = new_name
            result['new_path'] = new_path
            result['renamed'] = True
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'operation': operation,
            'file_path': file_path
        }


# 网络工具函数
@register_tool(description="执行网络操作")
def network_tool(operation: str, url: str = None, **kwargs) -> Dict[str, Any]:
    """
    执行网络操作
    
    Args:
        operation: 操作类型（get, post, head, ping, resolve）
        url: 目标URL
        **kwargs: 操作参数
        
    Returns:
        Dict: 操作结果
    """
    try:
        result = {
            'operation': operation,
            'url': url
        }
        
        # 根据操作类型执行相应的网络操作
        if operation.lower() in ["get", "post", "head"]:
            # HTTP请求
            if not url:
                raise ValueError("URL is required for HTTP request")
            
            # 导入requests库
            import requests
            
            # 获取请求参数
            headers = kwargs.get('headers', {})
            params = kwargs.get('params', {})
            data = kwargs.get('data')
            json_data = kwargs.get('json')
            timeout = kwargs.get('timeout', 30)
            auth = kwargs.get('auth')
            verify = kwargs.get('verify', True)
            
            # 记录请求信息
            logging.info(f"Making HTTP {operation.upper()} request to {url}")
            
            # 发送请求
            if operation.lower() == "get":
                response = requests.get(url, headers=headers, params=params, timeout=timeout, auth=auth, verify=verify)
            elif operation.lower() == "post":
                response = requests.post(url, headers=headers, params=params, data=data, json=json_data, timeout=timeout, auth=auth, verify=verify)
            elif operation.lower() == "head":
                response = requests.head(url, headers=headers, params=params, timeout=timeout, auth=auth, verify=verify)
            
            # 解析响应
            result['status_code'] = response.status_code
            result['headers'] = dict(response.headers)
            result['url'] = response.url  # 可能与请求URL不同（重定向）
            result['elapsed'] = response.elapsed.total_seconds()
            
            # 根据内容类型处理响应内容
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                try:
                    result['content'] = response.json()
                except ValueError:
                    result['content'] = response.text
            else:
                result['content'] = response.text
            
            # 检查响应状态
            result['success'] = 200 <= response.status_code < 300
        elif operation.lower() == "ping":
            # Ping主机
            host = kwargs.get('host') or url
            if not host:
                raise ValueError("Host is required for ping operation")
            
            # 根据操作系统执行不同的ping命令
            import platform
            
            if platform.system().lower() == "windows":
                # Windows系统
                cmd = ["ping", "-n", "4", host]  # 发送4个ping包
            else:
                # Unix/Linux/Mac系统
                cmd = ["ping", "-c", "4", host]  # 发送4个ping包
            
            # 执行ping命令
            import subprocess
            
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(timeout=30)
                
                result['stdout'] = stdout
                result['stderr'] = stderr
                result['return_code'] = process.returncode
                
                # 解析ping结果
                success = process.returncode == 0
                result['success'] = success
                
                if success:
                    # 尝试提取延迟信息
                    if platform.system().lower() == "windows":
                        # Windows ping输出格式
                        match = re.search(r"Average = (\d+)ms", stdout)
                    else:
                        # Unix/Linux/Mac ping输出格式
                        match = re.search(r"rtt min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms", stdout)
                    
                    if match:
                        if platform.system().lower() == "windows":
                            result['average_latency'] = float(match.group(1))
                        else:
                            result['min_latency'] = float(match.group(1))
                            result['average_latency'] = float(match.group(2))
                            result['max_latency'] = float(match.group(3))
                            result['mdev_latency'] = float(match.group(4))
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                result['error'] = "Ping timeout"
                result['stdout'] = stdout
                result['stderr'] = stderr
                result['success'] = False
        elif operation.lower() == "resolve":
            # 解析域名
            host = kwargs.get('host') or url
            if not host:
                raise ValueError("Host is required for resolve operation")
            
            # 导入socket库
            import socket
            
            try:
                # 获取主机的IP地址
                ip_addresses = socket.gethostbyname_ex(host)[2]
                result['ip_addresses'] = ip_addresses
                result['success'] = True
            except socket.gaierror as e:
                result['error'] = str(e)
                result['success'] = False
        else:
            raise ValueError(f"Unsupported operation: {operation}")
        
        return result
    except Exception as e:
        return {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'operation': operation,
            'url': url
        }


# 工具函数类 - 将工具函数封装为BaseTool子类
class FunctionTool(BaseTool):
    """
    函数工具类
    
    将工具函数封装为BaseTool子类
    """
    
    def __init__(self, func: Callable, **kwargs):
        """
        初始化函数工具
        
        Args:
            func: 要封装的函数
            **kwargs: 其他参数
        """
        # 调用父类初始化
        super().__init__(**kwargs)
        
        # 存储函数引用
        self.func = func
        
        # 设置工具名称和描述
        self.name = kwargs.get('name', func.__name__)
        self.description = kwargs.get('description', func.__doc__ if func.__doc__ else f"Tool function {self.name}")
    
    def _initialize(self):
        """
        初始化函数工具
        """
        # 已经在__init__中初始化了必要的属性
        pass
    
    async def _execute(self, **kwargs) -> ToolResponse:
        """
        执行函数
        
        Args:
            **kwargs: 函数参数
            
        Returns:
            ToolResponse: 执行结果
        """
        try:
            # 记录执行信息
            self.logger.info(f"Executing function: {self.name} with args: {kwargs}")
            
            # 执行函数
            # 如果函数是协程函数，使用await执行；否则，在默认执行器中运行
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                import asyncio
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: self.func(**kwargs))
            
            # 格式化响应
            return self.format_response(
                success=True,
                result=result,
                function_name=self.name,
                params=kwargs
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    @classmethod
    def from_function_registry(cls, name: str, **kwargs) -> 'FunctionTool':
        """
        从函数注册器创建函数工具
        
        Args:
            name: 函数名称
            **kwargs: 其他参数
            
        Returns:
            FunctionTool: 函数工具实例
        """
        # 从注册器获取函数
        func = tool_registry.get_tool(name)
        if not func:
            raise ValueError(f"Tool function not found: {name}")
        
        # 获取函数元数据
        metadata = tool_registry.get_metadata(name)
        if metadata:
            # 合并元数据和用户参数
            kwargs['name'] = kwargs.get('name', metadata.get('name'))
            kwargs['description'] = kwargs.get('description', metadata.get('description'))
        
        # 创建函数工具实例
        return cls(func, **kwargs)


# 工具集合类
class ToolSet:
    """
    工具集合类
    
    用于组织和管理多个工具
    """
    
    def __init__(self, name: str = "default", description: str = ""):
        """
        初始化工具集合
        
        Args:
            name: 工具集合名称
            description: 工具集合描述
        """
        self.name = name
        self.description = description
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"ToolSet '{name}' initialized")
    
    def add_tool(self, tool: BaseTool) -> bool:
        """
        添加工具到集合
        
        Args:
            tool: 要添加的工具
            
        Returns:
            bool: 是否添加成功
        """
        if not isinstance(tool, BaseTool):
            self.logger.error("Tool must be an instance of BaseTool")
            return False
        
        tool_name = tool.name
        self.tools[tool_name] = tool
        self.logger.info(f"Added tool '{tool_name}' to ToolSet '{self.name}'")
        return True
    
    def remove_tool(self, name: str) -> bool:
        """
        从集合中移除工具
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否移除成功
        """
        if name in self.tools:
            del self.tools[name]
            self.logger.info(f"Removed tool '{name}' from ToolSet '{self.name}'")
            return True
        
        self.logger.warning(f"Tool '{name}' not found in ToolSet '{self.name}'")
        return False
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取工具
        
        Args:
            name: 工具名称
            
        Returns:
            Optional[BaseTool]: 工具实例
        """
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有工具
        
        Returns:
            List[Dict]: 工具列表
        """
        result = []
        for name, tool in self.tools.items():
            result.append({
                'name': name,
                'description': tool.description,
                'type': type(tool).__name__
            })
        return result
    
    def execute_tool(self, name: str, **kwargs) -> ToolResponse:
        """
        执行工具
        
        Args:
            name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResponse: 执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolResponse(success=False, error=f"Tool not found: {name}")
        
        # 异步执行工具
        import asyncio
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(tool.execute(**kwargs))
    
    def add_function_tool(self, func: Callable, **kwargs) -> bool:
        """
        添加函数工具
        
        Args:
            func: 要添加的函数
            **kwargs: 函数工具参数
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 创建函数工具
            tool = FunctionTool(func, **kwargs)
            # 添加到工具集合
            return self.add_tool(tool)
        except Exception as e:
            self.logger.error(f"Failed to add function tool: {str(e)}")
            return False
    
    def add_function_from_registry(self, name: str, **kwargs) -> bool:
        """
        从函数注册器添加函数工具
        
        Args:
            name: 函数名称
            **kwargs: 函数工具参数
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 从注册器创建函数工具
            tool = FunctionTool.from_function_registry(name, **kwargs)
            # 添加到工具集合
            return self.add_tool(tool)
        except Exception as e:
            self.logger.error(f"Failed to add function tool from registry: {str(e)}")
            return False
    
    def clear(self):
        """
        清空工具集合
        """
        self.tools.clear()
        self.logger.info(f"Cleared all tools from ToolSet '{self.name}'")


# 创建默认的工具集合
default_tool_set = ToolSet(name="default", description="Default tool set")

# 添加常用工具函数到默认工具集合
for func_name in ["text_processor", "text_extractor", "data_converter", "math_calculator", "datetime_tool", "file_tool", "network_tool"]:
    if func_name in globals():
        func = globals()[func_name]
        default_tool_set.add_function_tool(func)