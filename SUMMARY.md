# sci-aiselect 增强版总结

## 项目概述

sci-aiselect 是一个增强版的期刊选择助手，它结合了多个出版社的 Journal Finder 和 AI 匹配功能，提供更全面、更准确的期刊推荐。

## 已完成的工作

### 1. 基础架构
- ✅ 创建了 Journal Finder 模块结构
- ✅ 实现了基类 `BaseJournalFinder`
- ✅ 实现了 Journal Finder 管理器 `JournalFinderManager`
- ✅ 创建了统一的结果格式 `JournalFinderResult`

### 2. Journal Finder 实现
- ✅ **Elsevier** Journal Finder 框架
- ✅ **Wiley** Journal Finder 框架
- ✅ **Taylor & Francis** Journal Suggester 框架
- ✅ **Springer** Journal Finder 框架
- ✅ **Web of Science** Master Journal List 框架（支持多种认证方式）

### 3. 配置管理
- ✅ 创建了配置文件模板 `config.yaml`
- ✅ 支持启用/禁用特定的 Journal Finder
- ✅ 支持并行搜索配置
- ✅ 支持 Web of Science 认证配置

### 4. 测试和文档
- ✅ 创建了测试脚本 `test_journal_finders.py`
- ✅ 创建了使用指南 `USAGE_GUIDE.md`
- ✅ 更新了 SKILL.md 文档

## 技术特点

### 1. 模块化设计
- 每个 Journal Finder 都是独立的模块
- 易于扩展和维护
- 支持并行搜索

### 2. 统一接口
- 所有 Journal Finder 都实现相同的接口
- 结果格式统一，便于后续处理
- 支持自定义配置

### 3. 错误处理
- 支持重试机制
- 支持超时处理
- 支持降级策略

### 4. 认证支持
- Web of Science 支持多种认证方式
- 支持 cookies 和 API key
- 易于扩展其他认证方式

## 下一步工作

### 1. 分析网站 API（优先级：高）
需要实际访问每个 Journal Finder 网站，分析其 API 端点和数据格式：

- **Elsevier**: 使用 Playwright 分析 GraphQL API
- **Wiley**: 分析搜索表单和 API 端点
- **Taylor & Francis**: 分析搜索功能
- **Springer**: 分析期刊搜索 API
- **Web of Science**: 分析 API 文档和认证流程

### 2. 实现实际 API 调用（优先级：高）
基于分析结果，实现每个 Journal Finder 的实际搜索功能：

```python
# 示例：实现 Elsevier API 调用
def _search_via_api(self, search_text):
    # 1. 分析网站的 API 端点
    # 2. 构造请求参数
    # 3. 发送请求并解析响应
    # 4. 返回标准化结果
    pass
```

### 3. 处理反爬虫机制（优先级：中）
某些网站可能有反爬虫机制，需要：
- 使用 Playwright 模拟浏览器行为
- 处理 JavaScript 渲染
- 处理验证码（如果需要）

### 4. 优化结果解析（优先级：中）
- 改进 HTML 解析逻辑
- 提取更准确的匹配分数
- 处理不同格式的结果

### 5. 集成到主选择器（优先级：中）
修改 `select_journals()` 函数，支持使用 Journal Finder 结果：

```python
def select_journals(
    text: str,
    title: str = None,
    abstract: str = None,
    keywords: List[str] = None,
    use_journal_finders: bool = True,
    # ...
):
    # 1. 使用 Journal Finder 初筛
    if use_journal_finders:
        finder_results = search_all_journal_finders(title, abstract, keywords)
    
    # 2. 原有 AI 匹配流程
    # ...
    
    # 3. 合并结果
    # ...
```

### 6. 添加缓存机制（优先级：低）
- 缓存 Journal Finder 结果
- 缓存期刊指标数据
- 设置合理的缓存过期时间

### 7. 添加结果导出功能（优先级：低）
- 支持导出为 CSV/Excel
- 支持导出为 JSON
- 支持生成报告

## 使用示例

### 基本使用

```python
from scripts.journal_finders import search_all_journal_finders
from scripts.select_journals import select_journals, format_selection_report

# 准备论文信息
title = "Groundwater nitrate source identification using stable isotopes"
abstract = "This study investigates..."
keywords = ["groundwater", "nitrate", "stable isotopes"]

# 搜索 Journal Finders
finder_results = search_all_journal_finders(title, abstract, keywords)

# 使用 AI 匹配
paper_text = f"{title}\n{abstract}\n{' '.join(keywords)}"
bundle = select_journals(text=paper_text, max_candidates=10)

# 输出报告
print(format_selection_report(bundle["profile"], bundle["results"]))
```

### 高级使用

```python
from scripts.journal_finders import JournalFinderManager
from scripts.journal_metrics import get_journal_metrics

# 创建管理器
manager = JournalFinderManager()

# 自定义配置
config = {
    'timeout': 60,
    'parallel': True,
    'max_workers': 3,
    'elsevier': {'enabled': True},
    'wiley': {'enabled': True},
    'wos': {'enabled': False},  # 禁用 WOS
}

# 搜索
results = manager.search(
    title="Your title",
    abstract="Your abstract",
    config=config
)

# 获取详细指标
for result in results[:5]:
    metrics = get_journal_metrics(result.journal_name)
    print(f"{result.journal_name}: IF={metrics.get('impact_factor')}")
```

## 测试

### 运行单元测试

```bash
cd ~/.hermes/skills/sci-aiselect
python -m unittest discover -s tests -v
```

### 运行 Journal Finder 测试

```bash
cd ~/.hermes/skills/sci-aiselect
python test_journal_finders.py
```

## 配置示例

### 完整配置

```yaml
journal_finders:
  enabled: true
  timeout: 30
  retry_count: 3
  max_results_per_finder: 10
  parallel: true
  max_workers: 5
  
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
    auth_type: cookies
    cookies_file: assets/wos_cookies.json
    api_key_file: assets/wos_api_key.txt
```

## 注意事项

1. **网络访问**：Journal Finder 需要访问外部网站
2. **API 限制**：某些网站可能有请求频率限制
3. **认证状态**：Web of Science 需要认证
4. **结果数量**：默认每个 Journal Finder 返回最多 10 个结果
5. **并行搜索**：默认启用并行搜索以提高效率

## 贡献指南

欢迎贡献代码和改进建议：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

MIT License
