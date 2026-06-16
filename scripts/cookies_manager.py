"""
Cookies 管理模块

用于管理和加载各出版社网站的 cookies
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path


class CookieManager:
    """Cookies 管理器"""
    
    def __init__(self, cookies_dir: str = None):
        """
        初始化
        
        Args:
            cookies_dir: cookies 存储目录
        """
        if cookies_dir is None:
            cookies_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'cookies')
        
        self.cookies_dir = Path(cookies_dir)
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
    
    def save_cookies(self, source: str, cookies: List[Dict], metadata: Dict = None):
        """
        保存 cookies
        
        Args:
            source: 来源名称（如 'elsevier', 'wiley'）
            cookies: cookies 列表
            metadata: 元数据（如浏览器信息、用户代理等）
        """
        data = {
            'source': source,
            'cookies': cookies,
            'metadata': metadata or {},
            'saved_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
        }
        
        filepath = self.cookies_dir / f'{source}_cookies.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[CookieManager] Cookies 已保存到: {filepath}")
    
    def load_cookies(self, source: str) -> Optional[List[Dict]]:
        """
        加载 cookies
        
        Args:
            source: 来源名称
        
        Returns:
            Optional[List[Dict]]: cookies 列表，如果不存在或已过期则返回 None
        """
        filepath = self.cookies_dir / f'{source}_cookies.json'
        
        if not filepath.exists():
            print(f"[CookieManager] Cookies 文件不存在: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            expires_at = datetime.fromisoformat(data.get('expires_at', '2000-01-01'))
            if datetime.now() > expires_at:
                print(f"[CookieManager] Cookies 已过期: {source}")
                return None
            
            return data.get('cookies', [])
        
        except Exception as e:
            print(f"[CookieManager] 加载 cookies 失败: {e}")
            return None
    
    def list_cookies(self) -> List[Dict]:
        """
        列出所有保存的 cookies
        
        Returns:
            List[Dict]: cookies 信息列表
        """
        result = []
        
        for filepath in self.cookies_dir.glob('*_cookies.json'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                result.append({
                    'source': data.get('source', filepath.stem),
                    'saved_at': data.get('saved_at', ''),
                    'expires_at': data.get('expires_at', ''),
                    'cookie_count': len(data.get('cookies', [])),
                    'filepath': str(filepath),
                })
            
            except Exception as e:
                print(f"[CookieManager] 读取文件失败 {filepath}: {e}")
        
        return result
    
    def delete_cookies(self, source: str) -> bool:
        """
        删除 cookies
        
        Args:
            source: 来源名称
        
        Returns:
            bool: 是否删除成功
        """
        filepath = self.cookies_dir / f'{source}_cookies.json'
        
        if filepath.exists():
            filepath.unlink()
            print(f"[CookieManager] Cookies 已删除: {source}")
            return True
        
        return False
    
    def export_cookies_for_requests(self, source: str) -> Optional[Dict]:
        """
        导出为 requests 库可用的 cookies 字典
        
        Args:
            source: 来源名称
        
        Returns:
            Optional[Dict]: cookies 字典
        """
        cookies_list = self.load_cookies(source)
        
        if not cookies_list:
            return None
        
        # 转换为 requests 可用的格式
        cookies_dict = {}
        for cookie in cookies_list:
            name = cookie.get('name', '')
            value = cookie.get('value', '')
            if name:
                cookies_dict[name] = value
        
        return cookies_dict
    
    def export_cookies_for_playwright(self, source: str) -> Optional[List[Dict]]:
        """
        导出为 Playwright 可用的 cookies 格式
        
        Args:
            source: 来源名称
        
        Returns:
            Optional[List[Dict]]: Playwright cookies 格式
        """
        cookies_list = self.load_cookies(source)
        
        if not cookies_list:
            return None
        
        # 转换为 Playwright 可用的格式
        playwright_cookies = []
        for cookie in cookies_list:
            pw_cookie = {
                'name': cookie.get('name', ''),
                'value': cookie.get('value', ''),
                'domain': cookie.get('domain', ''),
                'path': cookie.get('path', '/'),
            }
            
            # 可选字段
            if 'expires' in cookie:
                pw_cookie['expires'] = cookie['expires']
            if 'httpOnly' in cookie:
                pw_cookie['httpOnly'] = cookie['httpOnly']
            if 'secure' in cookie:
                pw_cookie['secure'] = cookie['secure']
            if 'sameSite' in cookie:
                pw_cookie['sameSite'] = cookie['sameSite']
            
            playwright_cookies.append(pw_cookie)
        
        return playwright_cookies
    
    def import_from_browser_export(self, filepath: str, source: str) -> bool:
        """
        从浏览器导出的 cookies 文件导入
        
        支持格式：
        - EditThisCookie (Chrome 扩展) 导出的 JSON
        - Cookie-Editor (Chrome/Firefox 扩展) 导出的 JSON
        - Netscape 格式的 cookies.txt
        
        Args:
            filepath: 文件路径
            source: 来源名称
        
        Returns:
            bool: 是否导入成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析为 JSON
            try:
                data = json.loads(content)
                
                # 检查是否是数组格式（EditThisCookie/Cookie-Editor）
                if isinstance(data, list):
                    cookies = data
                elif isinstance(data, dict) and 'cookies' in data:
                    cookies = data['cookies']
                else:
                    cookies = [data]
                
                self.save_cookies(source, cookies)
                return True
            
            except json.JSONDecodeError:
                # 尝试解析为 Netscape 格式
                cookies = self._parse_netscape_cookies(content)
                if cookies:
                    self.save_cookies(source, cookies)
                    return True
        
        except Exception as e:
            print(f"[CookieManager] 导入失败: {e}")
        
        return False
    
    def _parse_netscape_cookies(self, content: str) -> List[Dict]:
        """
        解析 Netscape 格式的 cookies
        
        Args:
            content: 文件内容
        
        Returns:
            List[Dict]: cookies 列表
        """
        cookies = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('\t')
            if len(parts) >= 7:
                cookies.append({
                    'domain': parts[0],
                    'httpOnly': parts[1].upper() == 'TRUE',
                    'path': parts[2],
                    'secure': parts[3].upper() == 'TRUE',
                    'expires': int(parts[4]) if parts[4] != '0' else None,
                    'name': parts[5],
                    'value': parts[6],
                })
        
        return cookies


# 全局实例
_cookie_manager = None


def get_cookie_manager() -> CookieManager:
    """获取全局 CookieManager 实例"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = CookieManager()
    return _cookie_manager
