# 测试说明

测试位于 [`spec/minigit_spec.py`](../spec/minigit_spec.py)，使用 pytest 收集以 `it_` 开头的测试函数。

## 运行测试

```bash
python -m pytest
```

项目测试配置位于 `pyproject.toml`：

```toml
[tool.pytest.ini_options]
testpaths = ["spec"]
python_files = ["*_spec.py"]
python_functions = ["it_*"]
```

## 测试结构

每个测试通常分为三段：

1. 数据：创建文件、仓库和配置。
2. 执行：调用 miniGit 或真实 Git。
3. 期望：比较输出、退出码、对象字节和落盘文件。

## 两种测试数据来源

### 纯 miniGit 仓库

使用 miniGit 完成 `init`、`add` 和 `commit`，再用真实 Git 读取生成结果。这类测试验证 miniGit 写出的对象、Tree、Commit 和索引是否可被 Git 读取。

### 真实 Git 仓库

先用真实 Git 创建提交，再把 `.git` 改名为 `.minigit`，让 miniGit 读取 Git 写入的数据。这类测试验证索引、ignore 规则和提交对象的读取能力。

## 确定性数据

测试使用固定字节和固定身份，例如：

```text
hello\n
Test User <test@example.com>
```

Blob、Tree 和空 Tree 的 SHA-1 常量在测试文件中显式保存，用于验证序列化算法。

## `xfail` 的含义

部分测试使用 `pytest.mark.xfail` 记录已知限制，例如：

- 索引 trailer 缺失导致 `git fsck` 失败
- 索引条目排序尚未保证
- 首次提交前 `status` 的边界行为

这些测试是可执行的改进清单；修复实现后应变成 XPASS，并重新评估是否移除 `xfail`。

## 添加新测试

新增命令或修复格式时，建议同时补充：

- 正常路径
- 空仓库和空文件边界
- 不存在的对象或引用
- 工作区、索引和 HEAD 的状态变化
- 与真实 Git 的交叉验证
- Windows 路径分隔符行为
