# sci-aiselect 使用指南

## 概述

sci-aiselect 是一个增强版的期刊选择助手，它结合了多个出版社的 Journal Finder 和 AI 匹配功能，提供更全面、更准确的期刊推荐。

## 功能特点

### 1. 多源 Journal Finder 初筛
- **Elsevier** Journal Finder
- **Wiley** Journal Finder
- **Taylor & Francis** Journal Suggester
- **Springer** Journal Finder
- **Web of Science** Master Journal List

### 2. AI 智能匹配
- 基于论文内容的语义分析
- 自动识别研究领域和方法
- 匹配 LetPub 期刊分类

### 3. 综合指标评估
- 影响因子（IF）
- 中科院分区
- SCI/SCIE/ESCI 收录
- 审稿速度
- OA/APC 信息
- h-index

## 快速开始

### 方法 1: 使用便捷函数（推荐）

```python
from scripts.journal_finders import search_all_journal_finders
from scripts.select_journals import select_journals, format_selection_report

# 准备论文信息
title = "Your paper title here"
abstract = "Your paper abstract here..."
keywords = ["keyword1", "keyword2", "keyword3"]

# Step 1: 使用 Journal Finder 初筛
print("正在搜索 Journal Finders...")
finder_results = search_all_journal_finders(title, abstract, keywords)
print(f"找到 {len(finder_results)} 个候选期刊")

# Step 2: 使用 AI 匹配
paper_text = f"{title}\n{abstract}\n{' '.join(keywords)}"
print("\n正在进行 AI 匹配...")
bundle = select_journals(
    text=paper_text,
    # 可选：传入 Journal Finder 结果作为初始候选
    # initial_candidates=finder_results,
    impact_low="3",
    max_candidates=10,
)

# Step 3: 输出推荐报告
print("\n" + format_selection_report(bundle["profile"], bundle["results"]))
```

### 方法 2: 分步使用

```python
from scripts.journal_finders import JournalFinderManager
from scripts.journal_metrics import get_journal_metrics, format_metrics_line

# 创建 Journal Finder 管理器
manager = JournalFinderManager()

# 搜索特定的 Journal Finder
results = manager.search(
    title="Your title",
    abstract="Your abstract",
    keywords=["keyword1", "keyword2"],
    finders=["elsevier", "wiley"],  # 只使用特定的 Journal Finder
    max_results=20
)

# 获取期刊详细指标
for result in results[:5]:
    metrics = get_journal_metrics(result.journal_name)
    print(f"{result.journal_name}: {format_metrics_line(metrics)}")
```

## 配置说明

### Journal Finder 配置

编辑 `config.yaml` 文件：

```yaml
journal_finders:
  enabled: true
  timeout: 30
  retry_count: 3
  max_results_per_finder: 10
  parallel: true
  max_workers: 5
  
  # 启用/禁用特定的 Journal Finder
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
    auth_type: cookies  # 或 api_key
```

### Web of Science 认证配置

Web of Science 需要认证才能访问。有两种方式：

#### 方式 1: Cookies（推荐）

1. 在浏览器中登录 [Web of Science](https://mjl.clarivate.com/)
2. 使用浏览器扩展导出 cookies（如 EditThisCookie）
3. 保存到 `assets/wos_cookies.json`

#### 方式 2: API Key

1. 从 Clarivate 获取 API key
2. 保存到 `assets/wos_api_key.txt`

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

## 注意事项

1. **网络访问**：Journal Finder 需要访问外部网站，请确保网络连接正常
2. **API 限制**：某些出版社可能有请求频率限制，请适当控制请求速度
3. **认证状态**：Web of Science 需要认证，请确保认证信息有效
4. **结果数量**：默认每个 Journal Finder 返回最多 10 个结果，可在配置中调整
5. **并行搜索**：默认启用并行搜索以提高效率，可在配置中禁用

## 常见问题

### Q: 为什么 Journal Finder 返回 0 个结果？
A: 可能的原因：
- 网络连接问题
- API 端点已更改
- 搜索内容不符合要求
- 认证信息无效

### Q: 如何更新 Web of Science 的认证信息？
A: 按照上面的"Web of Science 认证配置"部分操作。

### Q: 可以只使用特定的 Journal Finder 吗？
A: 可以，在 `search` 方法中指定 `finders` 参数：
```python
results = manager.search(
    title="...",
    abstract="...",
    finders=["elsevier", "wiley"]  # 只使用这两个
)
```

### Q: 如何调整搜索结果的数量？
A: 在配置文件中修改 `max_results_per_finder` 参数，或在调用时指定 `max_results` 参数。

## 开发计划

### 已完成
- [x] 基础架构设计
- [x] Journal Finder 基类
- [x] 各出版社 Journal Finder 框架
- [x] 配置管理
- [x] 测试脚本

### 进行中
- [ ] 分析各网站的 API 端点
- [ ] 实现实际的 API 调用
- [ ] 处理反爬虫机制
- [ ] 优化结果解析

### 计划
- [ ] 添加更多的 Journal Finder
- [ ] 实现缓存机制
- [ ] 添加结果导出功能
- [ ] 优化性能

## 技术支持

如有问题或建议，请联系开发者。
