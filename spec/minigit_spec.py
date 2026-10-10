"""minigit 命令行测试:单文件,行为句用例(it_*),每个用例三段式:数据/执行/期望。

运行: python -m pytest          (收集规则配置在 pyproject.toml: it_* 函数)

每个用例三段式:
    # 数据   —— 显式摆出来的文件/仓库状态
    # 执行   —— 跑哪条 minigit 命令
    # 期望   —— 逐字的期望输出/文件字节

测试数据的两种来路:
  1) 纯 minigit:用 minigit 自己 add/commit,对象/索引/git 都能读——
     就用真实 git 交叉验证(命令 `git --git-dir=.minigit ...`)。
     (索引虽缺 20 字节 trailer,git 运行时命令照样读、`git status` 还会把
      trailer 修好写回;但 `git fsck` 报 fatal——trailer 属已知未修,见文件末尾。)
  2) 真实 git 造夹具:git init/add/commit 后把 .git 改名 .minigit,
     拿 git 自己的答案当期望输出,考察 minigit 能否读 git 写的索引。

确定性哈希常量(sha1("blob <len>\\0"+data) / tree 序列化),
其中 HELLO_SHA、EMPTY_*、EMPTY_TREE_SHA 是 git 社区公认值,
文件开头有自检用例验证算法,其余用同一算法算出后抄成字面量。
"""

import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MINIGIT = ROOT / "src" / "minigit"

# --------------------------------------------------------------------------
# 测试数据(输入)与期望输出(字面量)
# --------------------------------------------------------------------------

HELLO = b"hello\n"
HELLO_V2 = b"hello v2\n"
NESTED = b"nested\n"
BAR = b"bar\n"
SCRATCH = b"scratch\n"
KEEP = b"keep me\n"
NOTES = b"notes\n"
LOGDATA = b"log\n"
OKDATA = b"ok\n"

HELLO_SHA = "ce013625030ba8dba906f756967f9e9ca394464a"
NESTED_SHA = "79c53955ef856f16f2107446bc721c8879a1bd2e"
SCRATCH_SHA = "fb188b9ecf0563e4e036fa3031d43b6a9387504d"
HELLO_V2_SHA = "a9aa67508972702119f06b0de94cbdc45516c8e5"
EMPTY_BLOB_SHA = "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"

SUB_TREE_SHA = "9dfd7d08cef435bccfc5701b5b547c3740a67404"          # 含 sub/nested.txt 的树
SINGLE_HELLO_TREE_SHA = "aaa96ced2d9a1c8e72c56b253a0e2fe78393feb7" # 仅 hello.txt 的树
HELLO_PLUS_SUB_TREE_SHA = "35b1388c8ad6fd52c547077a4e4ffc067d7a852a"
V2_PLUS_SUB_TREE_SHA = "e2a4383fe9cbb5bec15839508917de535beca009"
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

GITIGNORE_ROOT = "*.tmp\n# a comment\n!keep.tmp\n"   # 根规则:忽略 *.tmp,但保留 keep.tmp
GITIGNORE_SUB = "*.log\n"                            # sub/ 目录内规则

AUTHOR = "Test User <test@example.com>"              # 配合 fake HOME 的固定作者


# --------------------------------------------------------------------------
# 跑命令的管道(纯函数,返回普通元组)
# --------------------------------------------------------------------------

def fake_home_env(root):
    """为 root 所在 tmp 目录准备假 HOME(写死 .gitconfig),返回 env 字典。

    目的:minigit 提交时读 ~/.gitconfig,身份固定成 AUTHOR,可逐字断言;
    也确保测试永远碰不到你真实的 git 配置。
    """
    home = Path(root).parent / "home"
    home.mkdir(exist_ok=True)
    cfg = home / ".gitconfig"
    if not cfg.exists():
        cfg.write_text("[user]\n\tname = Test User\n\temail = test@example.com\n",
                       encoding="utf-8")
    (home / "xdg").mkdir(exist_ok=True)  # XDG 空目录 => 没有全局 ignore/exclude
    return {**os.environ, "HOME": str(home), "USERPROFILE": str(home),
            "XDG_CONFIG_HOME": str(home / "xdg")}


def minigit(root, *args):
    """跑 `minigit <args>`(cwd=root),返回 (returncode, stdout文本, stderr文本)。

    注:Windows 管道会把 Python 的 print 换行转成 CRLF,期望值一律按 LF 写,
    所以这里统一归一化回来——测的是 minigit 的逻辑,不是控制台换行。
    """
    p = subprocess.run([sys.executable, str(MINIGIT), *map(str, args)],
                       cwd=str(root), env=fake_home_env(root), capture_output=True)
    def text(b):
        return b.decode("utf-8", errors="replace").replace("\r\n", "\n")
    return (p.returncode, text(p.stdout), text(p.stderr))


def ok(root, *args):
    """同上,但要求成功;失败时把 stdout/stderr 一起抛进断言信息。返回 stdout。"""
    rc, out, err = minigit(root, *args)
    assert rc == 0, f"minigit {' '.join(map(str, args))} 失败 rc={rc}\nout:\n{out}\nerr:\n{err}"
    return out


def git(cwd, *args, check=True):
    """跑真实 git(关闭 autocrlf,固定身份),返回 (returncode, stdout文本)。"""
    p = subprocess.run(["git", "-c", "user.name=Test User", "-c", "user.email=test@example.com",
                        "-c", "core.autocrlf=false", "-c", "core.fileMode=false",
                        "-c", "commit.gpgsign=false", *map(str, args)],
                       cwd=str(cwd), capture_output=True,
                       env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C"})
    out = p.stdout.decode("utf-8", errors="replace")
    if check and p.returncode != 0:
        raise AssertionError(f"git {' '.join(map(str, args))} 失败 rc={p.returncode}\n"
                             f"stdout:\n{out}\nstderr:\n{p.stderr.decode('utf-8','replace')}")
    return p.returncode, out


# --------------------------------------------------------------------------
# 摆数据 / 检查落盘结果
# --------------------------------------------------------------------------

def init_repo(tmp_path):
    """# 数据构造: 一个 minigit init 出来的空仓库,返回仓库根目录 Path。"""
    root = tmp_path / "repo"
    root.mkdir()
    ok(root, "init", str(root))
    return root


def write_file(root, rel, content):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p


def git_written_repo(tmp_path, files, message="v1", untracked=None):
    """# 数据构造: 用真实 git 造好提交,再把 .git 改名 .minigit 交给 minigit。

    files 会全部提交;untracked 在提交后写入(保持未跟踪)。
    """
    root = tmp_path / "gr"
    root.mkdir()
    git(root, "init", "-b", "master", ".")
    for rel, content in files.items():
        write_file(root, rel, content)
    git(root, "add", "-A")
    git(root, "commit", "-m", message)
    for rel, content in (untracked or {}).items():
        write_file(root, rel, content)
    os.rename(str(root / ".git"), str(root / ".minigit"))
    return root


def git_in(root, *args, check=True):
    """真实 git 读 minigit 写的 objects/refs:`git --git-dir=<root>/.minigit ...`。"""
    return git(root, "--git-dir", str(Path(root) / ".minigit"), *args, check=check)


def index_header(root):
    """.minigit/index 头 12 字节 -> (version, entry_count)。魔数不是 DIRC 即失败。"""
    raw = (Path(root) / ".minigit" / "index").read_bytes()
    assert raw[:4] == b"DIRC", f"索引魔数错误: {raw[:4]!r}"
    return int.from_bytes(raw[4:8], "big"), int.from_bytes(raw[8:12], "big")


def index_entries(root):
    """按 DIRC v2 布局手工解包索引字节,返回 [{name,sha,perms,stage,assume,...},...]。"""
    raw = (Path(root) / ".minigit" / "index").read_bytes()
    _, count = index_header(root)
    entries, pos = [], 12
    for _ in range(count):
        ctime_s, ctime_ns, mtime_s, mtime_ns, dev, ino, unused, mode, uid, gid, fsize, sha, flags = \
            struct.unpack_from(">6I2H3I20sH", raw, pos)
        pos += 62
        assert unused == 0 and mode >> 12 in (0b1000, 0b1010, 0b1110)
        name_len = flags & 0xFFF
        if name_len < 0xFFF:
            assert raw[pos + name_len] == 0
            name = raw[pos:pos + name_len]
            pos += name_len + 1
        else:  # 12 位长度溢出:名字至少 0xFFF 字节,靠找 0x00 定尾
            end = raw.index(b"\x00", pos + 0xFFF)
            name = raw[pos:end]
            pos = end + 1
        pos = (pos + 7) // 8 * 8  # 条目按 8 字节对齐
        entries.append({
            "ctime": (ctime_s, ctime_ns), "mtime": (mtime_s, mtime_ns),
            "dev": dev, "ino": ino, "perms": mode & 0xFFF, "mode_type": mode >> 12,
            "uid": uid, "gid": gid, "fsize": fsize,
            "sha": sha.hex(), "assume": bool(flags & 0x8000), "stage": (flags >> 12) & 3,
            "name": name.decode("utf-8"),
        })
    return entries, raw


def object_exists(root, sha):
    return (Path(root) / ".minigit" / "objects" / sha[:2] / sha[2:]).is_file()


def ref_text(root, ref):
    return (Path(root) / ".minigit" / ref).read_text()


def parse_status(text):
    """把 `minigit status` 文本切成 {"branch":…, "staged":[…], "unstaged":[…], "untracked":[…]}。

    条目归一成 "added: hello.txt" 这样的单空格形式。
    """
    import re as _re
    secs = {"branch": None, "staged": [], "unstaged": [], "untracked": []}
    cur = None
    for line in text.splitlines():
        s = _re.sub(r"\s+", " ", line).strip()
        if s.startswith("On branch ") or s.startswith("HEAD detached"):
            secs["branch"] = s
            cur = None
        elif s.startswith("Changes to be committed"):
            cur = "staged"
        elif s.startswith("Changes not staged"):
            cur = "unstaged"
        elif s.startswith("Untracked files"):
            cur = "untracked"
        elif s:
            assert cur, f"status 出现无法归类的行: {s!r}"
            secs[cur].append(s)
    return secs


# ==========================================================================
# 自检:手抄常量的生成算法必须与 git 公认值一致
# ==========================================================================

def it_agrees_with_canonical_git_hashes():
    # 数据: "hello\n"、空内容
    # 期望: 与 git 社区公认常量逐字相等(错了说明整套常量表算错)
    import hashlib
    def blob(data):
        return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()
    assert blob(HELLO) == HELLO_SHA == "ce013625030ba8dba906f756967f9e9ca394464a"
    assert blob(b"") == EMPTY_BLOB_SHA == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
    empty_tree = hashlib.sha1(b"tree 0\x00").hexdigest()
    assert empty_tree == EMPTY_TREE_SHA == "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


# ==========================================================================
# init:建仓库与向上定位
# ==========================================================================

def it_init_creates_the_expected_layout(tmp_path):
    # 数据: 空目录 init
    # 期望: 四个子目录;HEAD 内容逐字节 "ref: refs/heads/master\n";
    #       config 含 repositoryformatversion = 0
    root = init_repo(tmp_path)
    gitdir = root / ".minigit"
    for d in ["branches", "objects", "refs/heads", "refs/tags"]:
        assert (gitdir / d).is_dir(), f"缺目录 {d}"
    assert (gitdir / "HEAD").read_text() == "ref: refs/heads/master\n"
    assert "repositoryformatversion = 0" in (gitdir / "config").read_text()


def it_ls_files_on_fresh_repo_prints_nothing(tmp_path):
    # 边界: 全新仓库(还没有 .minigit/index 文件)
    # 期望: 退出码 0,输出为空串——空索引不是错误
    root = init_repo(tmp_path)
    assert ok(root, "ls-files") == ""


def it_finds_the_repo_from_a_subdirectory(tmp_path):
    # 数据: 仓库根有 hello.txt 已 add;在 repo/sub/ 里执行 ls-files
    # 期望: 照常输出 "hello.txt\n"(repo_find 从 cwd 向上找到仓库根)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    (root / "sub").mkdir()
    rc, out, err = minigit(root / "sub", "ls-files")
    assert rc == 0, err
    assert out == "hello.txt\n"


def it_fails_outside_any_repository(tmp_path):
    # 边界: cwd 往上没有任何 .minigit
    # 期望: 非零退出,stderr 含 "No git directory."
    rc, out, err = minigit(tmp_path, "ls-files")
    assert rc != 0 and "No git directory" in err


def it_refuses_to_reinit_a_nonempty_repository(tmp_path):
    # 边界: .minigit 已存在且非空
    # 期望: 非零退出,报 "is not empty"
    root = init_repo(tmp_path)
    rc, out, err = minigit(root, "init", str(root))
    assert rc != 0 and "not empty" in err


def it_refuses_init_when_target_is_a_file(tmp_path):
    # 边界: 目标路径存在但不是目录
    # 期望: 非零退出,报 "not a directory"
    f = tmp_path / "plain.txt"
    f.write_bytes(b"x")
    rc, out, err = minigit(tmp_path, "init", str(f))
    assert rc != 0 and "not a directory" in err


# ==========================================================================
# hash-object / cat-file:对象库读写
# ==========================================================================

def it_hash_object_prints_sha_without_storing(tmp_path):
    # 数据: hello.txt = "hello\n"
    # 执行: hash-object(不带 -w)
    # 期望: stdout == HELLO_SHA;对象库 ce/ 目录根本没建
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    assert ok(root, "hash-object", "hello.txt") == HELLO_SHA + "\n"
    assert not (root / ".minigit" / "objects" / "ce").exists()


def it_hash_object_w_stores_the_loose_object(tmp_path):
    # 数据: hello.txt = "hello\n"
    # 执行: hash-object -w
    # 期望: 同一 sha;文件 .minigit/objects/ce/0136...464a 出现
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    assert ok(root, "hash-object", "-w", "hello.txt") == HELLO_SHA + "\n"
    assert object_exists(root, HELLO_SHA)


def it_hash_object_on_empty_file(tmp_path):
    # 边界: 0 字节文件
    # 期望: 公认的空 blob 哈希 e69de29b...5391
    root = init_repo(tmp_path)
    write_file(root, "empty.txt", b"")
    assert ok(root, "hash-object", "empty.txt") == EMPTY_BLOB_SHA + "\n"


def it_cat_file_blob_returns_the_exact_bytes(tmp_path):
    # 数据: add hello.txt 后对象已在库里
    # 执行: cat-file blob ce013625...
    # 期望: 输出逐字 "hello\n"(cat-file 走 sys.stdout.buffer,子进程原样捕获)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    assert ok(root, "cat-file", "blob", HELLO_SHA) == "hello\n"


def it_cat_file_fails_on_unknown_object(tmp_path):
    # 边界: 库里不存在的 sha
    # 期望: 非零退出,报 "No such reference"
    root = init_repo(tmp_path)
    rc, out, err = minigit(root, "cat-file", "blob", "0" * 40)
    assert rc != 0 and "No such reference" in err


def it_cat_file_fails_when_type_does_not_match(tmp_path):
    # 边界: sha 是 blob,却要求 cat-file tree
    # 期望: 非零退出(minigit 类型跟随找不到 tree)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    rc, out, err = minigit(root, "cat-file", "tree", HELLO_SHA)
    assert rc != 0


# ==========================================================================
# add / rm / ls-files:索引写与读
# ==========================================================================

def it_add_writes_blob_index_entry_and_lists_the_file(tmp_path):
    # 数据: hello.txt = "hello\n"
    # 期望: ls-files == "hello.txt";索引头 (v2, 1 条);
    #       blob ce01... 落库;解包条目: name/sha/perms 644/mode_type 0b1000/stage 0
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")

    assert ok(root, "ls-files") == "hello.txt\n"
    assert index_header(root) == (2, 1)
    assert object_exists(root, HELLO_SHA)
    entries, _ = index_entries(root)
    assert [(e["name"], e["sha"], e["perms"], e["mode_type"], e["stage"]) for e in entries] \
        == [("hello.txt", HELLO_SHA, 0o644, 0b1000, 0)]


def it_readd_after_modify_replaces_the_entry(tmp_path):
    # 场景: add -> 改内容 -> 再 add(内部先 rm 再 append)
    # 数据: "hello\n" 改成 "hello v2\n"
    # 期望: 索引仍只有 1 条,sha 换成 a9aa6750...;两个 blob 都还在库里
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    write_file(root, "hello.txt", HELLO_V2)
    ok(root, "add", "hello.txt")

    entries, _ = index_entries(root)
    assert len(entries) == 1 and entries[0]["sha"] == HELLO_V2_SHA
    assert object_exists(root, HELLO_SHA) and object_exists(root, HELLO_V2_SHA)


def it_add_stores_nested_paths_with_forward_slash(tmp_path):
    # 场景/边界: Windows 上的子目录文件(回归测试:索引名必须是 "/" 不是 "\")
    # 数据: sub/nested.txt = "nested\n"
    # 期望: ls-files 输出 "sub/nested.txt\n",blob 79c53955... 落库
    root = init_repo(tmp_path)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "sub/nested.txt")
    assert ok(root, "ls-files") == "sub/nested.txt\n"
    assert object_exists(root, NESTED_SHA)


def it_add_fails_on_missing_file(tmp_path):
    # 边界: add 一个不存在的文件
    # 期望: 非零退出
    root = init_repo(tmp_path)
    rc, out, err = minigit(root, "add", "ghost.txt")
    assert rc != 0


def it_add_fails_on_directory(tmp_path):
    # 边界: add 目录(不是文件)
    # 期望: 非零退出
    root = init_repo(tmp_path)
    (root / "adir").mkdir()
    rc, out, err = minigit(root, "add", "adir")
    assert rc != 0


def it_add_fails_outside_the_worktree(tmp_path):
    # 边界: add 仓库外的绝对路径文件
    # 期望: 非零退出
    root = init_repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(HELLO)
    rc, out, err = minigit(root, "add", str(outside))
    assert rc != 0


def it_rm_deletes_file_and_index_entry(tmp_path):
    # 场景: add 后 rm(同时删工作区文件和索引条目)
    # 期望: 磁盘上文件消失;ls-files 空;索引头 count 归 0
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "rm", "hello.txt")
    assert not (root / "hello.txt").exists()
    assert ok(root, "ls-files") == ""
    assert index_header(root) == (2, 0)


def it_rm_keeps_other_entries(tmp_path):
    # 场景: 两个条目只删其一
    # 期望: 剩下的一条顺序不变(a 先 add、b 后 add,删 a 剩 b)
    root = init_repo(tmp_path)
    write_file(root, "a.txt", HELLO)
    write_file(root, "b.txt", NESTED)
    ok(root, "add", "a.txt")
    ok(root, "add", "b.txt")
    ok(root, "rm", "a.txt")
    assert ok(root, "ls-files") == "b.txt\n"


def it_rm_fails_on_untracked_file(tmp_path):
    # 边界: rm 不在索引里的文件
    # 期望: 非零退出,报 "not in the index"
    root = init_repo(tmp_path)
    write_file(root, "loose.txt", HELLO)
    rc, out, err = minigit(root, "rm", "loose.txt")
    assert rc != 0 and "not in the index" in err


def it_rm_fails_outside_the_worktree(tmp_path):
    # 边界: rm 仓库外路径
    # 期望: 非零退出,报 "outside of worktree"
    root = init_repo(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_bytes(HELLO)
    rc, out, err = minigit(root, "rm", str(outside))
    assert rc != 0 and "outside of worktree" in err


def it_ls_files_verbose_prints_the_stable_fields(tmp_path):
    # 场景: ls-files --verbose
    # 期望逐行: 头行 "Index file format v2, containing 1 entries."、
    #   "hello.txt"、"  regular file with perms: 644"、
    #   "  on blob: ce013625..."、"  flags: stage=0 assume_valid=False";
    #   (device/inode/时间/用户行随机器变化,只断言存在)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    out = ok(root, "ls-files", "--verbose")
    lines = out.splitlines()
    assert lines[0] == "Index file format v2, containing 1 entries."
    assert lines[1] == "hello.txt"
    assert lines[2] == "  regular file with perms: 644"
    assert lines[3] == f"  on blob: {HELLO_SHA}"
    assert any(line.startswith("  flags: stage=0 assume_valid=False") for line in lines)
    assert any(line.startswith("  device: ") for line in lines)


# ==========================================================================
# 索引字节格式(DIRC v2):手写索引 -> minigit 读;minigit 写 -> 手工核对布局
# ==========================================================================

def it_writes_an_index_that_pads_to_eight_byte_blocks(tmp_path):
    # 场景: add 后按字节核对索引布局
    # 期望: 文件长 == 12 + 对齐和;条目固定部分 62 字节,名字含结束 0x00,补到 8 的倍数
    root = init_repo(tmp_path)
    write_file(root, "a.txt", HELLO)          # 名字 5 字节:62+5+1=68 -> 补 4 = 72
    ok(root, "add", "a.txt")
    raw = (root / ".minigit" / "index").read_bytes()
    assert len(raw) == 12 + 72                       # (时间/设备字段随机器,不比)
    assert raw[12 + 62 : 12 + 62 + 6] == b"a.txt\x00"  # 名字 + 结束符
    assert raw[12 + 68 : 12 + 72] == b"\x00\x00\x00\x00"  # 补齐字节


def it_reads_an_index_with_a_fff_byte_name(tmp_path):
    # 边界: 名字长 4095(0xFFF)字节——git 的 12 位长度字段溢出,靠找 0x00 定尾
    # 数据: 手工打包索引(0xFFF 名 + 一条普通名 a.txt)
    # 期望: ls-files 依次输出两个名字;stdout 有 "Notice: Name is 0xFFF bytes long."
    root = init_repo(tmp_path)
    long_name = "x" * 0xFFF

    def pack_entry(name, sha):
        nb = name.encode("utf-8")
        flags = min(len(nb), 0xFFF)
        block = struct.pack(">6I2H3I20sH",
                            1000, 0, 1000, 0, 5, 9,          # ctime, mtime, dev, ino
                            0, 0o100644,                     # unused, mode
                            1000, 1000, len(nb),             # uid, gid, fsize
                            bytes.fromhex(sha), flags) + nb + b"\x00"
        return block + b"\x00" * ((-len(block)) % 8)

    body = pack_entry(long_name, HELLO_SHA) + pack_entry("a.txt", NESTED_SHA)
    (root / ".minigit" / "index").write_bytes(b"DIRC" + struct.pack(">II", 2, 2) + body)

    out = ok(root, "ls-files")
    # index_read 对超长名先打一行 Notice,再接正常输出
    assert out.splitlines() == ["Notice: Name is 0xFFF bytes long.", long_name, "a.txt"]


def it_keeps_flags_when_writing_and_reading_back(tmp_path):
    # 边界: assume_valid / stage 标志位的序列化回环(手工打包 -> ls-files 读)
    # 数据: 一条 assume_valid=True、一条 stage=2(合并冲突条目的形态)
    # 期望: minigit 能读(不 assert),--verbose 行里 flags 原样:
    #       "stage=0 assume_valid=True" 与 "stage=8192 assume_valid=False"
    root = init_repo(tmp_path)

    def pack_entry(name, sha, flags):
        nb = name.encode("utf-8")
        block = struct.pack(">6I2H3I20sH",
                            1000, 0, 1000, 0, 5, 9,
                            0, 0o100644,
                            1000, 1000, 6,
                            bytes.fromhex(sha), flags) + nb + b"\x00"
        return block + b"\x00" * ((-len(block)) % 8)

    body = (pack_entry("a.txt", HELLO_SHA, 0x8000 | 5) +
            pack_entry("b.txt", NESTED_SHA, (2 << 12) | 5))
    (root / ".minigit" / "index").write_bytes(b"DIRC" + struct.pack(">II", 2, 2) + body)

    out = ok(root, "ls-files", "--verbose")
    assert "  flags: stage=0 assume_valid=True" in out
    assert "  flags: stage=8192 assume_valid=False" in out


# ==========================================================================
# commit:树/提交对象、父子链、引用更新
# ==========================================================================

def it_first_commit_has_no_parent_and_points_at_the_right_tree(tmp_path):
    # 数据: hello.txt + sub/nested.txt,逐个 add,commit -m "first"
    # 期望:
    #   refs/heads/master == <40hex>\n;HEAD 仍是符号引用(内容没被动)
    #   4 个对象全部落库:2 blob + 2 tree(树 sha 是字面常量!)
    #   真实 git 交叉验证(git --git-dir=.minigit):
    #     rev-list --count HEAD == 1;commit 对象第 1 行 "tree 35b1388c...",无 parent 行;
    #     author/committer == "Test User <test@example.com> <时间戳> +时区";消息 "first"
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")

    sha = ref_text(root, "refs/heads/master").strip()
    assert len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)
    assert ref_text(root, "HEAD") == "ref: refs/heads/master\n"

    for expected in [HELLO_SHA, NESTED_SHA, SUB_TREE_SHA, HELLO_PLUS_SUB_TREE_SHA]:
        assert object_exists(root, expected), f"对象缺失 {expected}"

    _, commit_raw = git_in(root, "cat-file", "commit", sha)
    lines = commit_raw.splitlines()
    assert lines[0] == f"tree {HELLO_PLUS_SUB_TREE_SHA}"
    assert not any(l.startswith("parent") for l in lines)
    import re
    assert re.match(rf"^author {re.escape(AUTHOR)} \d+ [+-]\d{{4}}$", lines[1])
    assert lines[2] == lines[1].replace("author", "committer")
    assert lines[3] == ""
    assert lines[4] == "first"
    assert git_in(root, "rev-list", "--count", "HEAD")[1].strip() == "1"


def it_second_commit_links_to_the_first(tmp_path):
    # 场景: 改 hello -> add -> commit "second"
    # 期望: commit#2 的 parent 行 == commit#1 的 sha;
    #       树换成 v2 常量 e2a4383f...;rev-list 数 2;HEAD~1 == #1
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    first = ref_text(root, "refs/heads/master").strip()

    write_file(root, "hello.txt", HELLO_V2)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "second")
    second = ref_text(root, "refs/heads/master").strip()

    lines = git_in(root, "cat-file", "commit", second)[1].splitlines()
    assert lines[0] == f"tree {V2_PLUS_SUB_TREE_SHA}"
    assert lines[1] == f"parent {first}"
    assert second != first
    assert git_in(root, "rev-list", "--count", "HEAD")[1].strip() == "2"
    assert git_in(root, "rev-parse", "HEAD~1")[1].strip() == first


def it_committing_everything_removed_gives_the_empty_tree(tmp_path):
    # 场景: 提交后 rm 掉全部跟踪文件,再 commit
    # 期望: 新 HEAD 的树 == 公认空树 4b825dc6...;ls-tree 无输出
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    ok(root, "rm", "hello.txt")
    ok(root, "commit", "-m", "all-gone")

    assert git_in(root, "rev-parse", "HEAD^{tree}")[1].strip() == EMPTY_TREE_SHA
    assert ok(root, "ls-tree", "HEAD") == ""


# ==========================================================================
# 历史与树:log / ls-tree / checkout
# ==========================================================================

def it_log_prints_the_parent_chain_as_dot(tmp_path):
    # 场景: first <- second 两个提交后跑 log
    # 期望整段输出逐行(第二行之后):
    #   digraph minigitlog{ /   node[shape=rect] /
    #   c_<s2> [label="<s2前7>: second"] / c_<s2> -> c_<s1>; / c_<s1> [label=...] / }
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    first = ref_text(root, "refs/heads/master").strip()
    write_file(root, "hello.txt", HELLO_V2)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "second")
    second = ref_text(root, "refs/heads/master").strip()

    expected = "\n".join([
        "digraph minigitlog{",
        "  node[shape=rect]",
        f'  c_{second} [label="{second[:7]}: second"]',
        f"  c_{second} -> c_{first};",
        f'  c_{first} [label="{first[:7]}: first"]',
        "}",
    ])
    assert ok(root, "log").strip("\n") == expected


def it_ls_tree_top_level_shows_blobs_and_subtrees(tmp_path):
    # 数据: 提交 hello.txt + sub/nested.txt
    # 期望逐字两行(排序 hello.txt < sub/):
    #   "100644 blob ce01...\thello.txt"
    #   "040000 tree 9dfd...\tsub"
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    out = ok(root, "ls-tree", "HEAD")
    assert out == (f"100644 blob {HELLO_SHA}\thello.txt\n"
                   f"040000 tree {SUB_TREE_SHA}\tsub\n")


def it_ls_tree_recursive_flattens_into_blob_lines(tmp_path):
    # 场景: ls-tree -r
    # 期望: 展平后的两个 blob 行,路径用 "/" 分隔(与真实 git 输出规范一致)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    out = ok(root, "ls-tree", "-r", "HEAD")
    assert out == (f"100644 blob {HELLO_SHA}\thello.txt\n"
                   f"100644 blob {NESTED_SHA}\tsub/nested.txt\n")


def it_checkout_recreates_the_whole_tree(tmp_path):
    # 数据: 提交两个文件后 `checkout HEAD out`
    # 期望: out/hello.txt == "hello\n";out/sub/nested.txt == "nested\n"(目录自动建)
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    ok(root, "checkout", "HEAD", "out")
    assert (root / "out" / "hello.txt").read_bytes() == HELLO
    assert (root / "out" / "sub" / "nested.txt").read_bytes() == NESTED


def it_checkout_refuses_a_nonempty_target(tmp_path):
    # 边界: 目标目录已存在且非空
    # 期望: 非零退出,报 "Not empty"
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    write_file(root, "out/pre-existing.txt", HELLO)
    rc, out, err = minigit(root, "checkout", "HEAD", "out")
    assert rc != 0 and "Not empty" in err


# ==========================================================================
# 引用解析:rev-parse / show-ref / tag
# ==========================================================================

def it_rev_parse_resolves_head_tag_and_type_queries(tmp_path):
    # 数据: 单文件提交 + 轻量标签 v1
    # 期望: rev-parse HEAD == rev-parse master == rev-parse v1 == commit sha;
    #       --minigit-type tree HEAD == 单 hello 树常量 aaa96ced...
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    sha = ref_text(root, "refs/heads/master").strip()
    ok(root, "tag", "v1")

    assert ok(root, "rev-parse", "HEAD").strip() == sha
    assert ok(root, "rev-parse", "master").strip() == sha
    assert ok(root, "rev-parse", "v1").strip() == sha
    assert ok(root, "rev-parse", "--minigit-type", "tree", "HEAD").strip() \
        == SINGLE_HELLO_TREE_SHA


def it_rev_parse_fails_on_unknown_name(tmp_path):
    # 边界: 不存在的名字
    # 期望: 非零退出
    root = init_repo(tmp_path)
    rc, out, err = minigit(root, "rev-parse", "nope")
    assert rc != 0


def it_show_ref_lists_hash_then_name(tmp_path):
    # 数据: 一次提交
    # 期望唯一一行: "<sha> refs/heads/master"
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    sha = ref_text(root, "refs/heads/master").strip()
    assert ok(root, "show-ref") == f"{sha} refs/heads/master\n"


def it_lightweight_tag_is_just_a_ref_file(tmp_path):
    # 场景: tag v1(不加 -a)
    # 期望: refs/tags/v1 内容 == commit sha;`tag`(无参)列表输出 "v1"
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    sha = ref_text(root, "refs/heads/master").strip()

    ok(root, "tag", "v1")
    assert ref_text(root, "refs/tags/v1") == f"{sha}\n"
    assert ok(root, "tag") == "v1\n"


def it_annotated_tag_creates_a_peelable_tag_object(tmp_path):
    # 场景: tag -a v2
    # 期望: refs/tags/v2 是 tag 对象的 sha(≠ commit sha);
    #       git 交叉验证: cat-file tag 里 "object <commit sha>"/"type commit"/"tag v2";
    #       rev-parse v2^{} 剥回 commit;minigit 自己也能 cat-file tag
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    ok(root, "commit", "-m", "first")
    sha = ref_text(root, "refs/heads/master").strip()

    ok(root, "tag", "-a", "v2")
    tag_sha = ref_text(root, "refs/tags/v2").strip()
    assert tag_sha != sha

    lines = git_in(root, "cat-file", "tag", tag_sha)[1].splitlines()
    assert lines[0] == f"object {sha}"
    assert lines[1] == "type commit"
    assert lines[2] == "tag v2"
    assert git_in(root, "rev-parse", "v2^{}")[1].strip() == sha
    assert f"object {sha}" in ok(root, "cat-file", "tag", tag_sha)


# ==========================================================================
# status / check-ignore:读 git 写的索引(git 当出题人),再叠加工作区变化
# ==========================================================================

# 这个夹具的"标准答案"git 亲自给,改名 .minigit 后 minigit 必须给出同样的读法:
#   已跟踪并提交: .gitignore(根规则 *.tmp, !keep.tmp)、sub/.gitignore(*.log)、
#                 foo/bar.txt、hello.txt
#   未跟踪:       scratch.tmp(被 *.tmp 忽略) keep.tmp(被 ! 保留) notes.md
#                 sub/debug.log(被 sub 的 *.log 忽略) sub/ok.txt
STATUS_FILES = {
    ".gitignore": GITIGNORE_ROOT,
    "sub/.gitignore": GITIGNORE_SUB,
    "foo/bar.txt": BAR,
    "hello.txt": HELLO,
}
STATUS_UNTRACKED = {
    "scratch.tmp": SCRATCH,
    "keep.tmp": KEEP,
    "notes.md": NOTES,
    "sub/debug.log": LOGDATA,
    "sub/ok.txt": OKDATA,
}
EXPECTED_IGNORED = {"scratch.tmp", "sub/debug.log"}     # git 与 minigit 的公共交集
EXPECTED_UNTRACKED = {"keep.tmp", "notes.md", "sub/ok.txt"}


def it_reads_a_git_written_index_exactly_like_git(tmp_path):
    # 场景: git 写索引 -> 改名 .minigit;期望直接拿真实 git 的 ls-files 答案
    #       (索引本身是 git 写的合法文件,git 经 --git-dir 照样能读,与目录名无关)
    # 期望: minigit 的输出与 git 逐字节相等,且等于字面量(字典序 4 条)
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    _, expected = git(root, "--git-dir", str(root / ".minigit"),
                      "--work-tree", str(root), "ls-files")
    out = ok(root, "ls-files")
    assert out == expected
    assert expected == ".gitignore\nfoo/bar.txt\nhello.txt\nsub/.gitignore\n"


def it_check_ignore_matches_git_on_the_common_subset(tmp_path):
    # 场景: 对 7 个路径(2 应忽略、3 未跟踪、2 已跟踪)同时问 git 和 minigit
    # 期望: 两个实现都只判 [scratch.tmp, sub/debug.log] 被忽略
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    probe = ["scratch.tmp", "keep.tmp", "notes.md", "sub/debug.log", "sub/ok.txt",
             "foo/bar.txt", "hello.txt"]
    _, git_out = git(root, "--git-dir", str(root / ".minigit"),
                     "--work-tree", str(root), "check-ignore", *probe, check=False)
    _, out, _ = minigit(root, "check-ignore", *probe)
    assert set(git_out.split()) == EXPECTED_IGNORED
    assert set(out.split()) == EXPECTED_IGNORED


def it_status_of_a_clean_git_repo_lists_only_untracked(tmp_path):
    # 数据: git 提交的 4 个文件 + 5 个未跟踪/忽略文件,无工作区改动
    # 期望: "On branch master.";暂存区/未暂存区皆空;
    #       Untracked 恰为 {keep.tmp, notes.md, sub/ok.txt}(scratch/tmp 与 log 被忽略)
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    secs = parse_status(ok(root, "status"))
    assert secs["branch"] == "On branch master."
    assert secs["staged"] == []
    assert secs["unstaged"] == []
    assert sorted(secs["untracked"]) == sorted(EXPECTED_UNTRACKED)


def it_status_detects_modified_and_deleted(tmp_path):
    # 场景: 改 hello.txt 内容;删 foo/bar.txt
    # 期望 "Changes not staged" 恰为:
    #   modified: hello.txt(时间变了且新哈希不同)
    #   deleted:  foo/bar.txt(索引有、磁盘没了)
    #   暂存区仍空(索引没动)
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    write_file(root, "hello.txt", HELLO + HELLO)
    os.remove(str(root / "foo" / "bar.txt"))
    secs = parse_status(ok(root, "status"))
    assert sorted(secs["unstaged"]) == ["deleted: foo/bar.txt", "modified: hello.txt"]
    assert secs["staged"] == []


def it_touching_a_file_to_the_same_content_is_not_modified(tmp_path):
    # 边界: mtime 变了但内容没变(git 语义:不报修改)
    # 数据: hello.txt 重写一遍相同字节
    # 期望: "Changes not staged" 里 no modified
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    t = os.stat(root / "hello.txt").st_mtime
    os.utime(str(root / "hello.txt"), (t + 10, t + 10))  # 只改时间,不动内容
    secs = parse_status(ok(root, "status"))
    assert secs["unstaged"] == []


def it_adding_an_ignored_file_makes_it_tracked(tmp_path):
    # 场景: scratch.tmp 本被 *.tmp 忽略;`minigit add` 后应进暂存区
    # 期望: status 的 staged 恰为 ["added: scratch.tmp"];
    #       check-ignore 仍按规则判它"匹配 *.tmp"(书中实现只看规则不看跟踪状态,
    #       与真实 git 不同——这是有意保留的 book 行为,见 README)
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    ok(root, "add", "scratch.tmp")
    secs = parse_status(ok(root, "status"))
    assert secs["staged"] == ["added: scratch.tmp"]
    assert "scratch.tmp" not in secs["untracked"]
    _, out, _ = minigit(root, "check-ignore", "scratch.tmp")
    assert out == "scratch.tmp\n"


def it_committing_makes_status_clean_again(tmp_path):
    # 场景: 接上一步 add 了 scratch.tmp 后 commit
    # 期望: 三个变更区全空(HEAD==索引==工作区),只剩 3 个未跟踪文件
    root = git_written_repo(tmp_path, STATUS_FILES, untracked=STATUS_UNTRACKED)
    ok(root, "add", "scratch.tmp")
    ok(root, "commit", "-m", "track scratch")
    secs = parse_status(ok(root, "status"))
    assert secs["staged"] == [] and secs["unstaged"] == []
    assert sorted(secs["untracked"]) == sorted(EXPECTED_UNTRACKED)


# ==========================================================================
# check-ignore 的书内简化语义(纯 minigit,不对照 git)
# ==========================================================================

def it_ignore_rules_come_from_the_index_not_the_disk(tmp_path):
    # 边界: .gitignore 写在磁盘但未 add
    # 期望: check-ignore 什么都不输出——gitignore_read 只扫索引里的 .gitignore
    root = init_repo(tmp_path)
    write_file(root, ".gitignore", "*.tmp\n")
    _, out, _ = minigit(root, "check-ignore", "a.tmp")
    assert out == ""

    ok(root, "add", ".gitignore")   # 进索引后立刻生效
    _, out2, _ = minigit(root, "check-ignore", "a.tmp")
    assert out2 == "a.tmp\n"


def it_negation_and_last_match_wins(tmp_path):
    # 数据: 规则依次 "*b\n!bb\n" —— 对路径 "ab": 只有 *b 匹配 => 忽略;
    #       对 "bb": *b 匹配,后面 !bb 也匹配 => 后者胜 => 不忽略;
    #       对 "bc": 都不匹配 => 不忽略
    root = init_repo(tmp_path)
    write_file(root, ".gitignore", "*b\n!bb\n")
    ok(root, "add", ".gitignore")
    _, out, _ = minigit(root, "check-ignore", "ab", "bb", "bc")
    assert out == "ab\n"


def it_book_style_directory_pattern_limitation(tmp_path):
    # 边界: 书中 check-ignore 用 fnmatch 对【整个相对路径】做匹配——
    #   模式 "build/" 匹配不上 "build/x.o"(真实 git 会忽略,这是 book 的简化);
    #   换成 "build/*" 就能匹配。数据/期望按 book 实现来断言。
    root = init_repo(tmp_path)
    write_file(root, ".gitignore", "build/\n")
    ok(root, "add", ".gitignore")
    _, out, _ = minigit(root, "check-ignore", "build/x.o")
    assert out == ""                                   # book 行为:目录模式不生效

    write_file(root, ".gitignore", "build/\nbuild/*\n")
    ok(root, "add", ".gitignore")                      # 重新 add 更新索引里的规则
    _, out, _ = minigit(root, "check-ignore", "build/x.o")
    assert out == "build/x.o\n"


# ==========================================================================
# 与真实 git 互操作 + 已知未修(xfail 是可执行的备忘:修好后变 XPASS,不会红)
# ==========================================================================

@pytest.mark.xfail(reason="index_write 缺 20 字节 trailer:git 运行时命令容忍(甚至会把索引修好写回),"
                          "但 git fsck 仍 fatal: index file corrupt;另外目录树叶的 mode 写成补零的"
                          " 040000,fsck 的 zeroPaddedFilemode 也会抱怨",
                   strict=False)
def it_passes_git_fsck(tmp_path):
    # 数据: 完整走一遍 add+commit 的仓库
    # 期望(修复后): git fsck 退出码 0、无任何 error/fatal
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "hello.txt")
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    rc, out = git_in(root, "fsck", check=False)
    assert rc == 0


def it_git_runtime_can_read_a_minigit_written_index(tmp_path):
    # 场景: minigit add 写了(无 trailer 的)索引,真实 git 经 --git-dir 读它
    # 期望: git ls-files rc==0、输出 "hello.txt"——运行时路径不因缺 trailer 拒绝
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    rc, out = git_in(root, "ls-files")
    assert rc == 0 and out == "hello.txt\n"


def it_git_status_rewrites_the_missing_trailer(tmp_path):
    # 场景: 无 trailer 索引被 git status 读一次后,git 用标准格式回写(自愈)
    # 期望: 回写的 index 末 20 字节 == 前文之 sha1(git 的 trailer 规则);
    #       minigit 自己的手工解包仍能读出 hello.txt
    import hashlib
    root = init_repo(tmp_path)
    write_file(root, "hello.txt", HELLO)
    ok(root, "add", "hello.txt")
    git_in(root, "status")
    raw = (root / ".minigit" / "index").read_bytes()
    assert hashlib.sha1(raw[:-20]).hexdigest() == raw[-20:].hex()
    entries, _ = index_entries(root)
    assert [e["name"] for e in entries] == ["hello.txt"]


@pytest.mark.xfail(reason="add() 直接 append,索引条目不保证字典序(git 要求排序)",
                   strict=False)
def it_index_entries_stay_sorted(tmp_path):
    root = init_repo(tmp_path)
    write_file(root, "z.txt", HELLO)
    write_file(root, "a.txt", NESTED)
    ok(root, "add", "z.txt")
    ok(root, "add", "a.txt")
    assert ok(root, "ls-files").splitlines() == ["a.txt", "z.txt"]


@pytest.mark.xfail(reason="status 需要 HEAD 的树:首次提交之前运行会异常(book 实现如此)",
                   strict=False)
def it_status_works_before_the_first_commit(tmp_path):
    root = init_repo(tmp_path)
    rc, out, err = minigit(root, "status")
    assert rc == 0


def it_ls_tree_recursive_prints_forward_slash_paths(tmp_path):
    # 回归: ls_tree 曾误用 os.path.join(Windows 拼出反斜杠);展示路径必须用 "/"
    root = init_repo(tmp_path)
    write_file(root, "sub/nested.txt", NESTED)
    ok(root, "add", "sub/nested.txt")
    ok(root, "commit", "-m", "first")
    assert ok(root, "ls-tree", "-r", "HEAD") == f"100644 blob {NESTED_SHA}\tsub/nested.txt\n"
