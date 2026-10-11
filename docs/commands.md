# 命令参考

## `init`

初始化仓库。

```bash
minigit init [directory]
```

默认在当前目录创建 `.minigit`。目标目录必须是不存在的目录或空目录。

## `hash-object`

计算对象 SHA-1，可选择写入对象库。

```bash
minigit hash-object [-t type] [-w] path
```

`type` 可为 `blob`、`commit`、`tree` 或 `tag`，默认是 `blob`。

```bash
minigit hash-object hello.txt
minigit hash-object -w hello.txt
```

## `cat-file`

显示对象的序列化内容。

```bash
minigit cat-file {blob|commit|tree|tag} object
```

## `ls-tree`

展示 Tree 对象。

```bash
minigit ls-tree tree-ish
minigit ls-tree -r tree-ish
```

`-r` 会递归展开子目录，并使用 `/` 输出路径。

## `checkout`

把 Commit 或 Tree 导出到空目录。

```bash
minigit checkout commit-or-tree empty-directory
```

目标目录必须为空；如果目标不存在，miniGit 会创建它。

## `rev-parse`

解析引用或对象名称。

```bash
minigit rev-parse name
minigit rev-parse --minigit-type tree name
```

## `show-ref`

列出所有引用。

```bash
minigit show-ref
```

## `tag`

列出或创建标签。

```bash
minigit tag
minigit tag name [object]
minigit tag -a name [object]
```

不带 `-a` 创建轻量标签；带 `-a` 创建附注 Tag 对象。

## `log`

输出从指定提交开始的提交历史，格式是 Graphviz DOT。

```bash
minigit log [commit]
```

可以把结果保存为 `.dot` 文件后交给 Graphviz 渲染。

## `ls-files`

列出索引中的路径。

```bash
minigit ls-files
minigit ls-files --verbose
```

## `check-ignore`

检查路径是否被 ignore 规则匹配。

```bash
minigit check-ignore path [path ...]
```

被忽略的路径会打印出来。

## `status`

显示 HEAD、索引和工作区之间的差异。

```bash
minigit status
```

## `add`

把文件内容写入 Blob，并更新索引。

```bash
minigit add path [path ...]
```

当前实现要求输入路径是工作区内的文件。

## `rm`

从工作区删除文件，并从索引移除对应条目。

```bash
minigit rm path [path ...]
```

## `commit`

根据索引创建 Tree 和 Commit，并更新活动分支。

```bash
minigit commit -m "message"
```

提交身份从用户 Git 配置中的 `user.name` 和 `user.email` 读取。
