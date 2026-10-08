# miniGit

miniGit 是一个用 Python 编写的 Git 学习项目，目标是通过逐步实现 Git 的核心概念与命令，加深对版本控制内部机制的理解。

目前仓库包含命令行入口和 Git 风格命令的分发骨架；各命令仍处于实现阶段，尚不适合作为真实 Git 的替代品。

## 使用方法

### 安装命令

在项目根目录执行可编辑安装：

```bash
python -m pip install --editable .
```

安装完成后可以像 Git 一样直接调用 `minigit`：

```bash
minigit --help
```

### 初始化仓库

在当前目录创建 miniGit 仓库：

```bash
minigit init
```

也可以指定目标目录：

```bash
minigit init ./demo
```

命令会在目标目录中创建 `.minigit` 目录，用于保存 miniGit 的仓库数据。当前已实现的命令是 `init`，其他 Git 命令将随着项目学习进度逐步实现。

开发阶段也可以直接运行源码入口，无需安装：

```bash
python ./src/minigit init ./demo
```

## 参考资料

本项目的学习思路参考了 [write-yourself-a-git（wyag）](https://github.com/thblt/write-yourself-a-git)。仓库中的 `wyag.zip` 是随项目保存的参考资料压缩包。

## 致谢

感谢 [thblt/write-yourself-a-git](https://github.com/thblt/write-yourself-a-git) 项目及其作者提供清晰、实用的 Git 实现学习范例。
