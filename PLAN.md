# sci-aiselect 增强计划：集成 Journal Finder 初筛

## 目标
在原有 AI 匹配功能之前，先通过 5 个出版社的 Journal Finder 进行初筛，获取约 50 个候选期刊，然后进行 AI 筛选。

## Journal Finder 分析

### 1. Elsevier Journal Finder
- **URL:** https://journalfinder.elsevier.com/
- **输入:** 标题 + 摘要
- **API:** 可能是 REST API，需要研究
- **输出:** 期刊列表，包含匹配度分数

### 2. Wiley Journal Finder
- **URL:** https://www.wiley.com/en-ie/journal-finder/abstract/?type=match
- **输入:** 标题 + 摘要
- **API:** 需要研究
- **输出:** 期刊列表

### 3. Taylor & Francis Journal Suggester
- **URL:** https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/
- **输入:** 标题 + 摘要
- **API:** 需要研究
- **输出:** 期刊列表

### 4. Springer Journal Finder
- **URL:** https://link.springer.com/journals
- **输入:** 标题 + 摘要
- **API:** 需要研究
- **输出:** 期刊列表

### 5. Web of Science Master Journal List
- **URL:** https://mjl.clarivate.com/home?mm=
- **输入:** 需要登录（cookies 或 API key）
- **认证方式:** 需要研究
- **输出:** 期刊列表

## 实现策略

### Phase 1: 研究和原型
1. 使用 Playwright 或 requests 研究每个网站的 API
2. 确定输入格式和输出结构
3. 处理 Web of Science 的认证问题

### Phase 2: 实现 Journal Finder 模块
1. 创建 `scripts/journal_finders/` 目录
2. 为每个 Journal Finder 创建独立的客户端
3. 实现统一的数据格式

### Phase 3: 集成到工作流
1. 修改 `select_journals()` 函数
2. 添加初筛逻辑
3. 优化候选期刊去重和排序

### Phase 4: 测试和优化
1. 测试每个 Journal Finder 的访问
2. 验证数据提取的准确性
3. 优化性能和错误处理

## 技术方案

### Web of Science 认证
- **方案 A:** 使用 cookies（用户手动登录后导出）
- **方案 B:** 使用 API key（如果 Clarivate 提供）
- **方案 C:** 使用 OAuth2 授权

### 数据结构
```python
{
    "source": "elsevier",
    "journal_name": "Journal of Hydrology",
    "match_score": 0.85,
    "issn": "0022-1694",
    "publisher": "Elsevier",
    "url": "https://..."
}
```

### 工作流
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

## 风险和挑战

1. **网站反爬虫:** 可能需要模拟浏览器行为
2. **API 限制:** 可能有请求频率限制
3. **认证复杂性:** Web of Science 可能需要复杂的认证流程
4. **数据格式差异:** 每个网站的输出格式不同

## 下一步

1. 使用 Playwright 研究每个网站的 API
2. 确定 Web of Science 的认证方案
3. 开始实现原型
