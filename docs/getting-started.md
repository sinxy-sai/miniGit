# 安装与第一个仓库

## 环境要求

- Python 3.10 或更高版本
- 无第三方运行时依赖
- 如果需要运行测试，需要安装 `pytest`
- 如果需要进行互操作测试，需要系统中有 `git`

## 安装

在项目根目录执行可编辑安装：

```bash
python -m pip install --editable .
```

安装后可以检查命令是否可用：

```bash
minigit --help
```

开发时也可以直接运行源码入口：

```bash
python ./src/minigit init ./demo
```

## 创建第一个仓库

```bash
minigit init ./demo
cd demo
```

初始化后会创建 `.minigit` 目录。它保存对象库、索引、HEAD 和引用。

## 创建第一个提交

```bash
echo hello > hello.txt
minigit add hello.txt
minigit status
minigit commit -m "first commit"
minigit log
```

提交前的 `add` 会把文件内容写成 Blob 对象，并把文件路径和 Blob 的 SHA-1 写入索引。`commit` 再根据索引生成 Tree 和 Commit 对象。

## 查看结果

```bash
minigit ls-files
minigit show-ref
minigit ls-tree HEAD
minigit cat-file commit HEAD
```

`log` 输出 Graphviz DOT 格式的提交图；`ls-tree` 查看提交对应的目录树；`cat-file` 查看对象内容。

## 从子目录运行

miniGit 会从当前目录向上查找 `.minigit`。因此可以在仓库的子目录中执行命令：

```bash
mkdir sub
cd sub
minigit ls-files
```

## 退出仓库

如果当前目录和所有父目录都没有 `.minigit`，需要仓库的命令会失败并报告 `No git directory.`。
