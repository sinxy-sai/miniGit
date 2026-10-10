# miniGit

miniGit 是一个用 Python 编写的 Git 学习项目：按照 [write-yourself-a-git（wyag）](https://wyag.thb.lt/) 教程，逐步亲手实现 Git 的核心机制（对象库、索引/暂存区、引用、提交等），加深对版本控制内部原理的理解。

这是一个教学项目，实现程度以教程为准，不能替代真实的 Git。

## 环境要求

- Python 3.10 及以上，无第三方运行时依赖
- 命令 `minigit` 的数据保存在仓库目录的 `.minigit` 子目录中（而非真实 Git 的 `.git`），两者互不干扰

## 安装与运行

在项目根目录执行可编辑安装：

```bash
python -m pip install --editable .
```

之后即可像 Git 一样调用：

```bash
minigit --help
```

开发阶段也可以不安装，直接运行源码入口：

```bash
python ./src/minigit init ./demo
```

## 已实现的命令

| 命令 | 作用 |
| --- | --- |
| `init` | 初始化一个 `.minigit` 仓库 |
| `hash-object` | 计算文件/文本的 SHA-1，并写入对象库 |
| `cat-file` | 查看对象的类型与内容 |
| `ls-tree` | 列出树对象内容（支持 `-r` 递归） |
| `checkout` | 把树对象导出到目录 |
| `rev-parse` | 解析引用名与修订表达式（如 `HEAD~1`） |
| `show-ref` | 列出仓库引用 |
| `tag` | 创建引用作为标签 |
| `log` | 输出提交历史（DOT 格式） |
| `ls-files` | 列出索引中的文件 |
| `check-ignore` | 检查路径是否被 ignore 规则忽略 |
| `status` | 显示工作区、索引与仓库之间的差异 |
| `add` | 写入对象库并更新索引（暂存） |
| `rm` | 从索引和工作区删除文件 |
| `commit` | 从索引生成提交对象并更新 HEAD |

最小工作流示例：

```bash
minigit init ./demo
cd ./demo
echo hello > hello.txt
minigit add hello.txt
minigit commit -m 'first commit'
minigit log
```

## 测试

```bash
python -m pytest
```

需要先安装 `pytest`；部分用例以系统 `git` 作为对照基准，需要 `git` 命令可用。

## 参考资料

本项目逐章实现自 [write-yourself-a-git（wyag）](https://github.com/thblt/write-yourself-a-git)，仓库中的 `wyag.zip` 是随项目保存的参考资料压缩包。

## 致谢

感谢 [thblt/write-yourself-a-git](https://github.com/thblt/write-yourself-a-git) 项目及其作者提供清晰、实用的 Git 实现学习范例。
