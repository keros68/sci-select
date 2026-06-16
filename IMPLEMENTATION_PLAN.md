# sci-aiselect 增强实现计划

## 架构设计

### 1. Journal Finder 模块结构
```
scripts/
├── journal_finders/
│   ├── __init__.py
│   ├── base.py              # 基类
│   ├── elsevier.py          # Elsevier Journal Finder
│   ├── wiley.py             # Wiley Journal Finder
│   ├── taylor_francis.py    # Taylor & Francis
│   ├── springer.py          # Springer
│   └── wos.py               # Web of Science
├── select_journals.py       # 主选择器（已修改）
└── ...
```

### 2. 数据流
```
输入：标题 + 摘要 + 关键词
    ↓
并行访问 5 个 Journal Finder
    ↓
收集约 50 个候选期刊
    ↓
去重和标准化
    ↓
原有 AI 匹配流程（LetPub + OpenAlex）
    ↓
输出：最终推荐列表
```

### 3. Journal Finder 接口设计

#### 3.1 基类接口
```python
class BaseJournalFinder:
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def search(self, title: str, abstract: str, keywords: List[str] = None) -> List[Dict]:
        """
        搜索期刊
        
        Returns:
            List[Dict]: 期刊列表，每个包含：
                - journal_name: 期刊名称
                - match_score: 匹配度分数 (0-1)
                - issn: ISSN 号
                - publisher: 出版商
                - url: 期刊 URL
                - source: 来源（如 "elsevier"）
        """
        raise NotImplementedError
    
    def _normalize_results(self, raw_results: List[Dict]) -> List[Dict]:
        """标准化结果格式"""
        # ...
```

#### 3.2 统一结果格式
```python
{
    "journal_name": "Journal of Hydrology",
    "match_score": 0.85,
    "issn": "0022-1694",
    "publisher": "Elsevier",
    "url": "https://www.sciencedirect.com/journal/journal-of-hydrology",
    "source": "elsevier",
    "raw_data": {}  # 原始数据，用于调试
}
```

### 4. 实现策略

#### 4.1 Elsevier Journal Finder
- **API:** 可能是 GraphQL 或 REST API
- **输入:** 标题 + 摘要
- **实现:** 使用 Playwright 模拟浏览器行为，捕获 API 请求

#### 4.2 Wiley Journal Finder
- **API:** 需要研究
- **输入:** 标题 + 摘要
- **实现:** 类似 Elsevier

#### 4.3 Taylor & Francis
- **API:** 需要研究
- **输入:** 标题 + 摘要
- **实现:** 类似

#### 4.4 Springer
- **API:** 需要研究
- **输入:** 标题 + 摘要
- **实现:** 类似

#### 4.5 Web of Science
- **认证:** 需要登录
- **方案:**
  1. **Cookies 方案:** 用户手动登录后导出 cookies
  2. **API Key 方案:** 如果 Clarivate 提供 API
  3. **OAuth2 方案:** 如果支持 OAuth2
- **实现:** 优先尝试 API Key，其次 Cookies

### 5. 主选择器修改

#### 5.1 新增参数
```python
def select_journals(
    text: str,
    title: str = None,
    abstract: str = None,
    keywords: List[str] = None,
    use_journal_finders: bool = True,  # 新增：是否使用 Journal Finder
    journal_finder_config: Dict = None,  # 新增：Journal Finder 配置
    # ... 其他原有参数
) -> Dict:
```

#### 5.2 工作流修改
```python
def select_journals(text, ...):
    # 1. 解析输入
    title, abstract, keywords = parse_input(text, title, abstract, keywords)
    
    # 2. 使用 Journal Finder 初筛（如果启用）
    if use_journal_finders:
        finder_candidates = search_via_journal_finders(
            title, abstract, keywords, journal_finder_config
        )
    else:
        finder_candidates = []
    
    # 3. 原有 AI 匹配流程
    profile = infer_paper_profile(text)
    # ...
    
    # 4. 合并结果
    all_candidates = merge_candidates(finder_candidates, ai_candidates)
    
    # 5. 排序和推荐
    ranked = rank_metric_records(profile, all_candidates)
    
    return {"profile": profile, "results": ranked}
```

### 6. Web of Science 认证方案

#### 6.1 方案 A: Cookies（推荐）
```python
# 用户手动登录后，导出 cookies
# 保存到 ~/.hermes/skills/sci-aiselect/assets/wos_cookies.json

{
    "cookies": [
        {
            "name": "cookie_name",
            "value": "cookie_value",
            "domain": ".clarivate.com",
            "path": "/"
        }
    ],
    "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 6.2 方案 B: API Key
```python
# 如果 Clarivate 提供 API Key
# 保存到 ~/.hermes/skills/sci-aiselect/assets/wos_api_key.txt

WOS_API_KEY=your_api_key_here
```

#### 6.3 方案 C: OAuth2
```python
# 如果支持 OAuth2
# 需要用户授权流程
```

### 7. 错误处理

#### 7.1 网络错误
- 超时重试
- 降级到其他 Journal Finder

#### 7.2 认证错误
- 提示用户更新 cookies/API key
- 跳过需要认证的 Journal Finder

#### 7.3 解析错误
- 记录原始数据
- 返回空结果

### 8. 测试策略

#### 8.1 单元测试
- 每个 Journal Finder 的独立测试
- 模拟网络请求

#### 8.2 集成测试
- 测试完整工作流
- 测试错误处理

#### 8.3 性能测试
- 并发访问测试
- 超时处理测试

### 9. 配置管理

#### 9.1 配置文件
```yaml
# ~/.hermes/skills/sci-aiselect/config.yaml

journal_finders:
  enabled: true
  timeout: 30
  retry_count: 3
  
  elsevier:
    enabled: true
    
  wiley:
    enabled: true
    
  taylor_francis:
    enabled: true
    
  springer:
    enabled: true
    
  wos:
    enabled: true
    auth_type: cookies  # cookies, api_key, oauth2
    cookies_file: assets/wos_cookies.json
    api_key_file: assets/wos_api_key.txt
```

### 10. 下一步行动

1. **实现基类和 Elsevier Journal Finder**
2. **研究其他 Journal Finder 的 API**
3. **实现 Web of Science 认证**
4. **修改主选择器**
5. **测试和优化**
