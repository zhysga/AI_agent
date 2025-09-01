"""
Web工具实现
"""
import asyncio
import json
import aiohttp
import requests
from typing import Dict, Any, Optional, List, Union, Callable
import logging
import re
import abc
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup  # 需要安装: pip install beautifulsoup4

from .base_tool import BaseTool, ToolResponse


class WebTool(BaseTool):
    """
    Web工具基类
    
    提供与Web交互的基础功能
    """
    
    def _initialize(self):
        """
        初始化Web工具
        """
        # 设置工具名称
        self.name = "WebTool"
        
        # 设置工具描述
        self.description = "与Web交互的基础工具"
        
        # HTTP会话配置
        self.http_config = {
            'timeout': 30,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'verify_ssl': True
        }
        
        # 异步HTTP客户端会话
        self._session = None
    
    @abc.abstractmethod
    async def _execute(self, **kwargs) -> ToolResponse:
        """
        执行Web工具的具体实现
        
        Args:
            **kwargs: 工具的输入参数
            
        Returns:
            ToolResponse: 执行结果
        """
        pass
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        获取或创建异步HTTP会话
        
        Returns:
            aiohttp.ClientSession: HTTP会话实例
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.http_config['timeout']),
                headers=self.http_config['headers']
            )
        return self._session
    
    async def close_session(self):
        """
        关闭HTTP会话
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def set_http_config(self, config: Dict[str, Any]):
        """
        设置HTTP配置
        
        Args:
            config: HTTP配置参数
        """
        self.http_config.update(config)
        self.logger.info(f"HTTP config updated")
    
    def get_http_config(self) -> Dict[str, Any]:
        """
        获取HTTP配置
        
        Returns:
            Dict: HTTP配置参数
        """
        return self.http_config.copy()


class WebScrapingTool(WebTool):
    """
    Web爬虫工具
    
    从网页中抓取数据
    """
    
    def _initialize(self):
        """
        初始化Web爬虫工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "WebScrapingTool"
        self.description = "从网页中抓取数据"
        
        # 默认配置
        self.default_params = {
            'parse_html': True,
            'extract_text': True,
            'extract_links': False,
            'extract_images': False
        }
    
    async def _execute(self, url: str, **kwargs) -> ToolResponse:
        """
        执行Web爬取
        
        Args:
            url: 要爬取的网页URL
            **kwargs: 爬取参数
            
        Returns:
            ToolResponse: 爬取结果
        """
        try:
            # 验证URL格式
            if not self._is_valid_url(url):
                return self.format_response(
                    success=False,
                    error=f"Invalid URL: {url}"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录爬取请求
            self.logger.info(f"Scraping web page: {url}")
            
            # 获取网页内容
            content = await self._fetch_url(url)
            
            if not content:
                return self.format_response(
                    success=False,
                    error=f"Failed to fetch content from {url}"
                )
            
            # 解析结果
            result = {
                'url': url,
                'raw_content': content
            }
            
            # 如果需要解析HTML
            if params.get('parse_html', True):
                parsed_data = self._parse_html(content, url, params)
                result.update(parsed_data)
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=result,
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)
        finally:
            # 可选：关闭会话，或者在工具生命周期结束时关闭
            # await self.close_session()
            pass
    
    def _is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            bool: URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def _fetch_url(self, url: str) -> Optional[str]:
        """
        获取URL内容
        
        Args:
            url: 要获取的URL
            
        Returns:
            Optional[str]: URL内容，如果获取失败则返回None
        """
        try:
            # 获取会话
            session = await self._get_session()
            
            # 发送请求
            async with session.get(url, ssl=self.http_config['verify_ssl']) as response:
                # 检查响应状态
                if response.status == 200:
                    # 根据内容类型决定如何读取响应
                    content_type = response.headers.get('Content-Type', '')
                    if 'text' in content_type or 'html' in content_type:
                        return await response.text()
                    else:
                        # 如果是二进制内容，返回Base64编码
                        import base64
                        content_bytes = await response.read()
                        return base64.b64encode(content_bytes).decode('utf-8')
                else:
                    self.logger.error(f"Failed to fetch {url}, status code: {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None
    
    def _parse_html(self, html_content: str, base_url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析HTML内容
        
        Args:
            html_content: HTML内容
            base_url: 基础URL，用于解析相对链接
            params: 解析参数
            
        Returns:
            Dict: 解析结果
        """
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            parsed_data = {}
            
            # 提取文本内容
            if params.get('extract_text', True):
                text = soup.get_text(separator='\n', strip=True)
                # 清理多余的空白字符
                text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
                parsed_data['text_content'] = text
            
            # 提取链接
            if params.get('extract_links', False):
                links = []
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    # 处理相对链接
                    absolute_url = urljoin(base_url, href)
                    links.append({
                        'text': a_tag.get_text(strip=True),
                        'href': href,
                        'absolute_url': absolute_url
                    })
                parsed_data['links'] = links
            
            # 提取图片
            if params.get('extract_images', False):
                images = []
                for img_tag in soup.find_all('img', src=True):
                    src = img_tag['src']
                    # 处理相对链接
                    absolute_url = urljoin(base_url, src)
                    images.append({
                        'alt': img_tag.get('alt', ''),
                        'src': src,
                        'absolute_url': absolute_url
                    })
                parsed_data['images'] = images
            
            # 提取标题
            title = soup.title
            if title:
                parsed_data['title'] = title.get_text(strip=True)
            
            # 提取元数据
            meta_data = {}
            for meta_tag in soup.find_all('meta'):
                if meta_tag.get('name'):
                    meta_data[meta_tag['name']] = meta_tag.get('content', '')
                elif meta_tag.get('property'):
                    meta_data[meta_tag['property']] = meta_tag.get('content', '')
            if meta_data:
                parsed_data['meta_data'] = meta_data
            
            return parsed_data
        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            return {}


class APICallTool(WebTool):
    """
    API调用工具
    
    调用REST API并处理响应
    """
    
    def _initialize(self):
        """
        初始化API调用工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "APICallTool"
        self.description = "调用REST API并处理响应"
        
        # 默认配置
        self.default_params = {
            'method': 'GET',
            'headers': {},
            'params': {},
            'data': None,
            'json': None,
            'auth': None,
            'timeout': 30
        }
    
    async def _execute(self, url: str, **kwargs) -> ToolResponse:
        """
        执行API调用
        
        Args:
            url: API端点URL
            **kwargs: API调用参数
            
        Returns:
            ToolResponse: API调用结果
        """
        try:
            # 验证URL格式
            if not self._is_valid_url(url):
                return self.format_response(
                    success=False,
                    error=f"Invalid URL: {url}"
                )
            
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录API调用请求
            self.logger.info(f"Calling API: {url}, method: {params['method']}")
            
            # 执行API调用
            result = await self._call_api(url, params)
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=result,
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    def _is_valid_url(self, url: str) -> bool:
        """
        验证URL是否有效
        
        Args:
            url: 要验证的URL
            
        Returns:
            bool: URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def _call_api(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用API并处理响应
        
        Args:
            url: API端点URL
            params: API调用参数
            
        Returns:
            Dict: API响应结果
        """
        try:
            # 获取会话
            session = await self._get_session()
            
            # 准备请求参数
            request_kwargs = {
                'ssl': self.http_config['verify_ssl'],
                'timeout': params['timeout']
            }
            
            # 添加请求头
            headers = self.http_config['headers'].copy()
            headers.update(params.get('headers', {}))
            request_kwargs['headers'] = headers
            
            # 添加认证信息
            if params.get('auth'):
                request_kwargs['auth'] = params['auth']
            
            # 根据请求方法选择相应的参数
            method = params['method'].upper()
            if method == 'GET':
                request_kwargs['params'] = params.get('params', {})
            elif method in ['POST', 'PUT', 'PATCH']:
                if params.get('json') is not None:
                    request_kwargs['json'] = params['json']
                elif params.get('data') is not None:
                    request_kwargs['data'] = params['data']
            
            # 发送请求
            async with session.request(method, url, **request_kwargs) as response:
                # 记录响应状态
                self.logger.info(f"API response status: {response.status} for {url}")
                
                # 尝试解析JSON响应
                try:
                    response_data = await response.json()
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试获取文本内容
                    response_data = await response.text()
                
                # 构建结果
                result = {
                    'status_code': response.status,
                    'headers': dict(response.headers),
                    'data': response_data,
                    'ok': response.ok
                }
                
                return result
        except Exception as e:
            self.logger.error(f"Error calling API {url}: {str(e)}")
            raise


class SearchEngineTool(WebTool):
    """
    搜索引擎工具
    
    使用搜索引擎搜索信息
    """
    
    def _initialize(self):
        """
        初始化搜索引擎工具
        """
        # 调用父类初始化
        super()._initialize()
        
        # 更新工具名称和描述
        self.name = "SearchEngineTool"
        self.description = "使用搜索引擎搜索信息"
        
        # 默认配置
        self.default_params = {
            'search_engine': 'google',  # google, bing, baidu
            'num_results': 10,
            'lang': 'zh-CN'
        }
        
        # 搜索引擎URL模板
        self.search_url_templates = {
            'google': 'https://www.google.com/search?q={query}&num={num_results}&hl={lang}',
            'bing': 'https://www.bing.com/search?q={query}&count={num_results}&setlang={lang}',
            'baidu': 'https://www.baidu.com/s?wd={query}&rn={num_results}&tn=SE_PclogoS_8whnvm25'
        }
    
    async def _execute(self, query: str, **kwargs) -> ToolResponse:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            **kwargs: 搜索参数
            
        Returns:
            ToolResponse: 搜索结果
        """
        try:
            # 合并默认参数和用户参数
            params = self.default_params.copy()
            params.update(kwargs)
            
            # 记录搜索请求
            self.logger.info(f"Searching with query: {query}, search_engine: {params['search_engine']}")
            
            # 构建搜索URL
            search_url = self._build_search_url(query, params)
            
            # 获取搜索结果页面
            search_results_page = await self._fetch_url(search_url)
            
            if not search_results_page:
                return self.format_response(
                    success=False,
                    error=f"Failed to fetch search results for query: {query}"
                )
            
            # 解析搜索结果
            parsed_results = self._parse_search_results(
                search_results_page, 
                params['search_engine'],
                params['num_results']
            )
            
            # 返回成功响应
            return self.format_response(
                success=True,
                result=parsed_results,
                query=query,
                search_engine=params['search_engine'],
                params=params
            )
            
        except Exception as e:
            return self.handle_error(e)
    
    def _build_search_url(self, query: str, params: Dict[str, Any]) -> str:
        """
        构建搜索URL
        
        Args:
            query: 搜索查询
            params: 搜索参数
            
        Returns:
            str: 构建好的搜索URL
        """
        import urllib.parse
        
        # 获取搜索引擎模板
        search_engine = params['search_engine'].lower()
        template = self.search_url_templates.get(search_engine, self.search_url_templates['google'])
        
        # 替换模板中的参数
        url = template.format(
            query=urllib.parse.quote(query),
            num_results=params['num_results'],
            lang=params['lang']
        )
        
        return url
    
    def _parse_search_results(self, html_content: str, search_engine: str, num_results: int) -> List[Dict[str, Any]]:
        """
        解析搜索结果
        
        Args:
            html_content: 搜索结果页面的HTML内容
            search_engine: 搜索引擎名称
            num_results: 要返回的结果数量
            
        Returns:
            List[Dict]: 解析后的搜索结果列表
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # 根据不同的搜索引擎使用不同的解析策略
            if search_engine == 'google':
                # 解析Google搜索结果
                for result in soup.select('div.g'):
                    # 提取标题和URL
                    title_elem = result.select_one('h3')
                    url_elem = result.select_one('a')
                    snippet_elem = result.select_one('div.VwiC3b')
                    
                    if title_elem and url_elem:
                        title = title_elem.get_text()
                        url = url_elem['href']
                        snippet = snippet_elem.get_text() if snippet_elem else ''
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            elif search_engine == 'bing':
                # 解析Bing搜索结果
                for result in soup.select('li.b_algo'):
                    # 提取标题和URL
                    title_elem = result.select_one('h2 a')
                    snippet_elem = result.select_one('p')
                    
                    if title_elem:
                        title = title_elem.get_text()
                        url = title_elem['href']
                        snippet = snippet_elem.get_text() if snippet_elem else ''
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            elif search_engine == 'baidu':
                # 解析Baidu搜索结果
                for result in soup.select('div.result.c-container.new-pmd'):
                    # 提取标题和URL
                    title_elem = result.select_one('h3.t a')
                    snippet_elem = result.select_one('div.c-abstract')
                    
                    if title_elem:
                        title = title_elem.get_text()
                        url = title_elem['href']
                        snippet = snippet_elem.get_text() if snippet_elem else ''
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            
            # 返回指定数量的结果
            return results[:num_results]
        except Exception as e:
            self.logger.error(f"Error parsing search results: {str(e)}")
            return []