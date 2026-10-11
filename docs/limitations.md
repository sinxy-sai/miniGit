# 已知限制

miniGit 是教学实现，以下限制是当前设计的一部分或后续改进方向。

## 功能范围

当前没有实现：

- 远程仓库、fetch、push、pull
- merge 和冲突处理
- rebase
- reset、restore、revert
- cherry-pick
- 完整的分支管理命令
- packfile 和增量对象
- garbage collection
- hooks
- 完整的配置层级
- 完整的 revision range 语法

## 索引格式

- 主要支持 Index v2。
- 写入时没有标准 20 字节 trailer。
- 添加路径后不保证始终按 Git 要求的字典序排列。
- 不支持 extended index entries。

## 工作区和状态

- 首次提交前的 `status` 仍有教程实现遗留的边界问题。
- `add` 当前面向文件路径，不提供完整的目录递归和 pathspec 语义。
- symlink 支持不完整，`checkout` 中仍有待实现的 symlink 处理。
- 工作区扫描和文件元数据受操作系统差异影响。

## ignore 规则

- `.gitignore` 需要进入索引后才会参与当前实现的规则读取。
- 使用 `fnmatch` 的简化匹配，不覆盖 Git 的全部目录和 pathspec 规则。
- 不保证和 Git 对所有复杂模式逐字节一致。

## 提交和标签

- 提交身份依赖用户 Git 配置中的 `user.name` 和 `user.email`。
- 附注标签使用固定的 miniGit tagger 和固定消息格式，不能自定义完整标签元数据。
- 活动分支更新支持当前简单的 HEAD 形式，不提供完整 detached HEAD 工作流。

## 项目定位

这些限制不会削弱 miniGit 作为学习项目的价值，但使用者不应把它当作生产环境的 Git 替代品。
