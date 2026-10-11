# 与真实 Git 的互操作性

miniGit 使用许多 Git 兼容的数据格式，因此可以和真实 Git 做局部互操作。这种兼容性是学习项目的验证手段，不代表 miniGit 已实现完整 Git 行为。

## miniGit 写、Git 读

对象和提交创建后，可以使用真实 Git 查看：

```bash
git --git-dir=.minigit cat-file -p HEAD
git --git-dir=.minigit ls-tree HEAD
git --git-dir=.minigit rev-list --count HEAD
```

索引也可以被真实 Git 的常用命令读取：

```bash
git --git-dir=.minigit ls-files
```

## Git 写、miniGit 读

可以先用真实 Git 创建仓库，再将 `.git` 改名为 `.minigit`：

```bash
git init
git add .
git commit -m "fixture"
```

然后在实验环境中把 `.git` 改名为 `.minigit`，用 miniGit 执行：

```bash
minigit ls-files
minigit status
minigit check-ignore path
```

项目测试已经覆盖了读取 Git 写入的常见索引、对象、ignore 规则和提交结构。

## 已知兼容性边界

### 索引 trailer

当前 `index_write` 写入条目后没有追加标准的 20 字节索引校验 trailer。真实 Git 的普通运行时命令通常可以容忍或修复它，但 `git fsck` 可能报告索引文件损坏。

### 索引排序

当前 `add` 追加条目，不能保证所有操作顺序下都保持 Git 要求的字典序。真实 Git 对部分命令仍能读取，但格式兼容性还可以继续改进。

### Tree mode

教程实现中的目录 mode 序列化与 Git 的严格格式仍有细节差异，可能触发 `zeroPaddedFilemode` 等检查提示。

### ignore 规则

miniGit 的规则解析使用 Python `fnmatch` 和索引中的 `.gitignore` 内容，目录模式、全局规则和已跟踪文件的细节与完整 Git 不完全相同。

## 互操作实验原则

建议将真实 Git 当作验证器：

1. 用固定输入创建仓库。
2. 用 miniGit 和 Git 分别读取同一个对象或索引。
3. 比较对象类型、树内容、引用和文件列表。
4. 对差异记录为当前限制或待修复项。
