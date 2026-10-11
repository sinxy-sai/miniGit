# 数据格式详解

本页说明 miniGit 使用的关键字节格式，适合需要阅读 `src/libminigit.py` 或与真实 Git 互操作的读者。

## Loose object

对象落盘前的原始字节：

```text
<ASCII type><SPACE><ASCII decimal size><NUL><payload>
```

落盘文件是整个原始字节串经过 zlib 压缩后的结果，不是只压缩 payload。

### Blob

Blob 的 payload 就是文件原始字节，不保存文件名、权限或目录位置。

### Commit

Commit payload 是 KVLM 格式：每一行以 `key value` 开始，空行后是提交消息。多行值使用后续行前置空格的方式继续：

```text
tree <sha>
parent <sha>
author <identity> <timestamp> <timezone>
committer <identity> <timestamp> <timezone>

<message>
```

`kvlm_parse` 将重复键保存为列表，因此可以表达多个 `parent`。

### Tree

每个 Tree 条目是：

```text
<ASCII mode><SPACE><UTF-8 name><NUL><20-byte raw object id>
```

Tree 中保存的是 20 字节二进制对象 ID，不是 40 字节十六进制字符串。

## 引用文件

符号引用使用：

```text
ref: refs/heads/master
```

直接引用使用带换行的十六进制 SHA-1。`ref_resolve` 会递归跟随 `ref:`，直到获得直接对象 ID。

## Index v2

索引头：

```text
offset 0   : 4 bytes  "DIRC"
offset 4   : 4 bytes  version = 2, big-endian
offset 8   : 4 bytes  entry count, big-endian
```

单个条目的固定部分为 62 字节，之后是路径、NUL 和八字节对齐填充：

```text
ctime seconds       4
ctime nanoseconds   4
mtime seconds       4
mtime nanoseconds   4
device              4
inode               4
unused              2
mode                4
uid                 4
gid                 4
file size           4
object id           20
flags               2
path                variable
NUL                 1
padding             variable
```

整数使用大端序。flags 的低 12 位保存路径长度；`0xFFF` 表示路径至少这么长，需要继续寻找 NUL。

标准 Git 索引还会在所有条目之后保存校验 trailer。miniGit 当前写入时省略该 trailer，因此 `git fsck` 可能报告问题。

## 文件权限和 Tree mode

索引将 mode 拆成类型和权限；生成 Tree 时重新编码为六位八进制 ASCII，例如普通文件常见形式是 `100644`，目录是 `040000`。

跨平台实现时，工作区的 `st_dev`、`st_ino` 和时间精度可能超过索引字段宽度；miniGit 在 Windows 上会对设备号和 inode 做截断处理。
