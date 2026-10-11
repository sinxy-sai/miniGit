# 算法原理

miniGit 的价值不只在于提供一组类似 Git 的命令，更在于它把内容寻址、不可变对象、递归数据结构、符号引用、增量状态比较和图遍历放进了一个可以运行和观察的系统。

## 1. 内容寻址与对象不可变性

miniGit 对对象计算的身份不是随机 ID，而是对象完整序列化结果的 SHA-1：

```text
payload = serialize(object)
header  = type + " " + decimal(len(payload)) + "\\0"
raw     = header + payload
object_id = SHA1(raw)
```

对象路径由对象 ID 直接决定：

```text
.minigit/objects/<sha[0:2]>/<sha[2:]>
```

这带来三个性质：

1. 相同内容得到相同 ID，相同 Blob 可以被多个文件或 Tree 共享。
2. 内容变化产生新对象，提交不会修改旧 Blob、Tree 或 Commit。
3. 对象可以通过 ID 校验，读取后重新计算哈希即可验证内容是否匹配路径。

miniGit 使用 SHA-1 是为了兼容 Git 的教学格式。生产系统还需要考虑 SHA-1 碰撞攻击和哈希算法迁移问题。

## 2. 对象写入算法

`object_write` 的核心算法如下：

```text
object_write(object, repository):
    data = object.serialize()
    raw = object.type + " " + len(data) + NUL + data
    sha = SHA1(raw)

    if repository is not None:
        path = objects/sha[0:2]/sha[2:]
        if path does not exist:
            write(path, zlib.compress(raw))

    return sha
```

写入前检查目标路径是否存在，使对象库天然具有幂等性：重复写入完全相同的对象不会覆盖已有对象。

读取时先解压，再解析类型、长度和 payload；长度检查可以发现对象截断或格式损坏。

## 3. Tree 是递归的目录数据结构

Tree 不是把完整路径平铺保存，而是使用目录树：

```text
root Tree
├── hello.txt -> Blob
└── src       -> Tree
    └── main.py -> Blob
```

每个 Tree 条目保存模式、名称和 20 字节对象 ID。目录条目指向另一个 Tree，普通文件条目指向 Blob。

### 从索引构造 Tree

`tree_from_index` 相当于一次后序遍历：

```text
for each index entry path:
    add entry to its parent directory list
    create every missing ancestor directory list

for directories from deepest to root:
    tree = Tree(entries in this directory)
    sort tree entries by Git tree order
    tree_sha = object_write(tree)
    append (directory_name, tree_sha) to the parent directory

return root_tree_sha
```

从最深目录向根目录处理，是因为父目录必须先知道子 Tree 的 SHA-1。

Tree 排序不是简单的操作系统目录排序。miniGit 使用以下排序键：

```text
regular file: filename
directory:    directory_name + "/"
```

给目录名追加 `/` 可以使 Git 的目录排序语义保持稳定。

## 4. 索引是二进制缓存和暂存快照

索引让用户先选择下一次提交的内容，而不必立即提交整个工作区。当前实现读取和写入 Git DirCache v2 的主要部分：

```text
12-byte header
  ├── "DIRC"
  ├── version = 2
  └── entry count
N entries
  ├── timestamps
  ├── device / inode
  ├── mode / uid / gid / size
  ├── 20-byte Blob SHA-1
  ├── flags
  ├── NUL-terminated path
  └── 8-byte alignment padding
```

固定部分是 62 字节，路径长度不固定，因此每个条目结束后填充到 8 字节边界：

```text
next_offset = ceil(current_offset / 8) * 8
```

`status` 先比较索引保存的 `ctime`、`mtime` 等元数据，只有元数据变化时才重新读取文件并计算 Blob SHA-1：

```text
metadata unchanged  -> assume content unchanged
metadata changed    -> hash file content to confirm
```

因此，单纯改变时间但不改变字节内容不会被报告为文件修改。当前 `index_write` 没有追加标准索引 trailer，也没有保证每次 `add` 后都按完整 Git 规则排序。

## 5. 状态计算是两个差集加一个过滤器

把三类状态抽象成映射：

```text
H = HEAD Tree 中的 path -> Blob SHA-1
I = Index 中的 path -> Blob SHA-1
W = 工作区中实际存在的 path -> 当前 Blob SHA-1
```

已暂存变化是 `H` 与 `I` 的差异：

```text
added    = keys(I) - keys(H)
deleted  = keys(H) - keys(I)
modified = {p | p in H ∩ I and H[p] != I[p]}
```

未暂存变化是 `I` 与 `W` 的差异：

```text
deleted  = keys(I) - keys(W)
modified = {p | p in I ∩ W and I[p] != W[p]}
```

未跟踪文件则是：

```text
untracked = (keys(W) - keys(I)) - ignored_paths
```

因此当前 `status` 不是三路合并算法，而是两个连续的二路比较：先比较 HEAD 与索引，再比较索引与工作区。

## 6. 引用解析是有优先级的名称解析

`object_resolve` 把一个用户输入名称映射为候选对象 ID：

```text
resolve(name):
    if name == "HEAD":
        return resolve_ref("HEAD")
    if name matches hexadecimal prefix:
        search objects/<prefix>/ for matching suffix
    try refs/tags/name
    try refs/heads/name
    try refs/remotes/name
    return candidates
```

如果候选为空，报告未知引用；如果候选多于一个，报告歧义，而不是随意选择一个对象。

`object_find` 可以做类型导向的跟随：要求 Tree 时跟随 Commit 的 `tree` 字段，遇到 Tag 时跟随 Tag 的 `object` 字段。

## 7. 提交历史是有向无环图遍历

Commit 的 `parent` 字段构成从子提交指向父提交的有向图。`log_graphviz` 使用深度优先遍历：

```text
visit(commit):
    if commit in seen:
        return
    add commit to seen
    emit node(commit)
    for parent in commit.parents:
        emit edge(commit, parent)
        visit(parent)
```

`seen` 集合保证共享父提交不会重复展开，也避免异常引用造成无限递归。访问 `V` 个提交和 `E` 条 parent 边的复杂度是 `O(V + E)`。

## 8. ignore 规则是作用域查找加最后匹配胜出

对相对路径，miniGit 先从最具体的父目录开始查找 scoped 规则，再查绝对规则：

```text
sub/deep/file.txt
  ↓
sub/deep/.gitignore 规则
sub/.gitignore 规则
根目录规则
全局 / exclude 规则
```

同一组规则内使用“最后一个匹配胜出”：

```text
*.tmp      -> ignored
!keep.tmp  -> not ignored
```

## 9. 不变量

阅读或修改实现时，下面几个不变量最重要：

1. 对象路径必须由对象完整序列化内容的 SHA-1 决定。
2. Tree 条目中的对象 ID 必须指向对象库中存在的对象。
3. Commit 的 `tree` 必须指向由当前索引构造的根 Tree。
4. 活动分支引用必须指向一个 Commit，或在空仓库中暂时不存在目标文件。
5. 索引路径必须是工作区相对路径，并统一使用 `/`。
6. `status` 的已暂存比较不能直接读取工作区内容。

这些不变量比单个命令的输出更适合作为扩展功能时的正确性标准。
