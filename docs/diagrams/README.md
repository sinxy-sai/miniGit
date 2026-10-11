# 图表目录

本目录按图表的叙事目的选择 DSL，并保留可编辑源码。

| 文件 | DSL | 用途 | 选择原因 |
|---|---|---|---|
| `system-overview.mmd` | Mermaid | 系统模块总览 | 适合直接嵌入 Markdown |
| `object-model.mmd` | Mermaid | 对象关系 | 结构简单，文档平台可直接渲染 |
| `add-commit-flow.mmd` | Mermaid | add 到 commit 时序 | 简单交互流程，适合 Markdown |
| `status-model.mmd` | Mermaid | 状态比较 | 适合流程和数据流 |
| `repository-layout.mmd` | Mermaid | 仓库目录结构 | 适合轻量层次图 |
| `revision-resolution.mmd` | Mermaid | 修订名解析流程 | 适合决策分支 |
| `object-write-sequence.puml` | PlantUML | 对象写入时序 | 参与者、消息和数据库边界更清晰 |
| `commit-graph.dot` | Graphviz DOT | 提交图遍历 | 提交历史本身是图，DOT 适合稳定控制节点和边 |

## 维护约定

1. 图表源码是主产物，SVG 或 PNG 只是可重新生成的渲染结果。
2. 节点 ID 使用稳定的 ASCII 名称，显示文本可以单独修改。
3. 每张图只表达一个叙事目标；跨层级内容应拆成多张图。
4. 箭头表示方向，标签说明关系含义，不能只依赖颜色。
5. 源码发生变化时，同时检查对应 Markdown 章节、测试和已知限制。

## 渲染命令

项目内工具链位于 `tools/diagram-toolchain/`。第一次使用前，在项目根目录执行：

```powershell
npm install --prefix tools/diagram-toolchain
```

PlantUML JAR 位于 `tools/diagram-toolchain/tools/bin/plantuml.jar`。如果该文件不存在，需要从 PlantUML 官方 release 下载对应版本后放入该路径。

### Mermaid

```powershell
npm exec --prefix tools/diagram-toolchain -- mmdc -i docs/diagrams/system-overview.mmd -o docs/diagrams/system-overview.svg
```

### PlantUML

项目有 Java 时，可以把 PlantUML JAR 固定在项目工具目录，再运行：

```powershell
java -jar tools/diagram-toolchain/tools/bin/plantuml.jar -tsvg docs/diagrams/object-write-sequence.puml
```

### Graphviz

安装或提供 Graphviz 后运行：

```powershell
node tools/diagram-toolchain/render-graphviz.mjs
```

如果环境没有系统级 `dot`，可以使用项目固定的 Graphviz WASM 依赖生成 SVG，避免依赖开发机 PATH。
