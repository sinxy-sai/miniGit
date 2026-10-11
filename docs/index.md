# miniGit 文档

miniGit 是一个用 Python 编写的 Git 学习项目。它通过实现对象库、索引、引用、提交和工作区状态等核心机制，帮助读者理解版本控制系统是如何工作的。

miniGit 使用 `.minigit` 保存仓库数据，因此可以和同一目录中的真实 `.git` 目录并存。

## 文档导航

### 快速上手

- [安装与第一个仓库](getting-started.md)
- [常见工作流](workflows.md)
- [命令参考](commands.md)

### 核心原理

- [核心概念](concepts.md)
- [仓库目录结构](repository-layout.md)
- [对象数据库](object-database.md)
- [算法原理](algorithms.md)
- [数据格式详解](data-formats.md)
- [复杂度与性能模型](complexity.md)
- [索引与暂存区](index-and-staging.md)
- [引用与修订表达式](references.md)
- [工作区状态与忽略规则](working-tree.md)

### 源码与边界

- [代码架构](architecture.md)
- [与真实 Git 的互操作性](compatibility.md)
- [已知限制](limitations.md)
- [测试说明](testing.md)
- [开发指南](development.md)

## 推荐阅读顺序

```text
安装与第一个仓库
        ↓
核心概念
        ↓
仓库目录结构
        ↓
对象数据库
        ↓
索引与暂存区
        ↓
引用与修订表达式
        ↓
工作区状态与忽略规则
        ↓
代码架构
```

## 图表源码

文档使用 Mermaid 表达软件结构和流程。图表源码保存在 [`diagrams/`](diagrams/) 中，便于继续修改或在本地重新渲染。

- [系统总览](diagrams/system-overview.mmd)
- [对象模型](diagrams/object-model.mmd)
- [add 到 commit 流程](diagrams/add-commit-flow.mmd)
- [工作区状态模型](diagrams/status-model.mmd)
- [仓库目录结构](diagrams/repository-layout.mmd)
- [修订表达式解析](diagrams/revision-resolution.mmd)
- [对象写入时序（PlantUML）](diagrams/object-write-sequence.puml)
- [提交图遍历（Graphviz DOT）](diagrams/commit-graph.dot)

## 项目定位

miniGit 的目标是教学和源码阅读。它实现了 Git 的一组核心机制，但不追求替代真实 Git，也不提供远程协作、合并冲突处理或完整的对象打包能力。
