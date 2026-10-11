# 开发指南

## 添加新命令

一个新命令通常需要四部分：

1. 在 `argsubparsers` 中注册参数。
2. 在 `main` 的 `match` 中分派。
3. 实现 `cmd_<name>`。
4. 在 `spec/minigit_spec.py` 中增加行为测试，并在 `docs/commands.md` 中补充说明。

示意：

```python
argsp = argsubparsers.add_parser("example", help="...")
argsp.add_argument("name")

def cmd_example(args):
    repo = repo_find()
    ...
```

## 扩展对象类型

如果要增加对象类型，需要：

- 增加继承自 `GitObject` 的类。
- 实现 `serialize`、`deserialize` 和 `fmt`。
- 在 `object_read` 和 `object_hash` 中注册类型。
- 增加对象落盘和读取测试。
- 在[对象数据库](object-database.md)中说明格式。

## 修改索引格式

修改索引时应同时关注：

- `index_read`
- `index_write`
- 条目排序
- trailer 校验和
- Git 读取兼容性
- Windows 文件元数据宽度

建议先用固定的小仓库记录索引字节，再用真实 Git 的 `ls-files`、`status` 和 `fsck` 验证。

## 修改提交流程

提交流程的关键不变量是：

```text
索引 → Tree → Commit → 活动引用
```

不要让 Commit 直接从工作区读取文件；否则 `add` 提供的暂存语义会被绕过。

## 文档和图表

架构或流程发生变化时，应该同步更新：

- 对应 Markdown 章节
- 命令参考
- 已知限制
- 相关测试说明

图表直接以内嵌 Mermaid 代码块保存在 Markdown 章节中。渲染图片和本地实验源码不需要提交到公开仓库。

## Mermaid 渲染

项目文档直接嵌入 Mermaid 代码块。需要在本地导出 SVG 时，可以使用 Mermaid CLI：

```bash
npx @mermaid-js/mermaid-cli -i diagram.mmd -o diagram.svg
```

SVG 或 PNG 是可重新生成的本地产物，不提交到公开仓库。

## 提交前检查

- 新命令能通过 `--help` 看到。
- 正常路径和边界路径都有测试。
- 文档中的命令与 argparse 参数一致。
- Mermaid 图表中的节点和关系与当前代码一致。
- 已知限制没有被文档误写成已实现功能。
