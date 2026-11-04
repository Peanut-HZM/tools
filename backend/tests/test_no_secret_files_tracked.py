"""守卫测试：真实密钥文件绝不能进入 Git 版本控制

背景
    本项目在「换机迁移」时曾把以下含真实密钥的文件提交到远程仓库
    （gitea/master 的 ``03018de7``）：

      - ``backend/.env``            —— OSS / MinIO / Dify / OCR / JWT 等真实密钥
      - ``frontend/.env``           —— 前端运行时配置
      - ``mini-program/.env.production``
      - ``backend/backups.db``      —— 本地数据库备份（含业务数据）

    这些文件按《密钥暴露面规则》必须**只存在于本地**，既不能被 Git 跟踪，
    也不能出现在任何提交里 —— 否则推送到 origin / github 时会把真实密钥
    发布到公开远程仓库。

判定口径
    1. 上述敏感文件不得出现在 ``git ls-files`` 的跟踪列表中。
    2. 上述敏感文件必须被 ``.gitignore`` 命中（``git check-ignore`` 判定），
       保证 ``git add .`` 不会把它们带进提交。
    3. 上述敏感文件必须存在于本地工作区 —— 本地可正常启动的前提。
    4. ``master`` 历史不得引入**含真实密钥**的敏感文件 —— 历史一旦污染
       即视为已泄露，需要轮换密钥 + 清理历史，而不是靠 ignore 掩盖。
       占位符内容（如仅含公开 API 域名）不算泄露。
"""
import pathlib
import re
import subprocess

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

# 含真实密钥 / 敏感数据、绝不允许被 Git 跟踪的文件（相对仓库根）
SENSITIVE_FILES = (
    "backend/.env",
    "frontend/.env",
    "mini-program/.env.production",
    "backend/backups.db",
)

# 真实密钥特征（仅用于**存在性判定**，命中时不打印匹配到的值本身，
# 避免把密钥带进终端输出 / 会话记录 —— 遵守《密钥暴露面规则》）
_SECRET_PATTERN = re.compile(
    r"(?im)"
    r"^\s*(?:[A-Z0-9_]*(?:SECRET|PASSWORD|PRIVATE_KEY|ACCESS_KEY|API_KEY|TOKEN)[A-Z0-9_]*)\s*=\s*\S+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\bsk-[A-Za-z0-9]{16,}"
    r"|\bLTAI[A-Za-z0-9]{12,}"
)


def _git(*args: str) -> subprocess.CompletedProcess:
    """在仓库根执行 git 命令，返回结果（不抛异常）。"""
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _tracked_files() -> set[str]:
    """Git 当前跟踪的文件集合。"""
    result = _git("ls-files")
    assert result.returncode == 0, f"git ls-files 失败: {result.stderr}"
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _ignored_by_gitignore(rel_path: str) -> bool:
    """文件是否被 .gitignore（或 .git/info/exclude）命中。"""
    result = _git("check-ignore", "-q", "--", rel_path)
    return result.returncode == 0


def _files_introduced_by_history() -> dict[str, list[str]]:
    """扫描 master 历史，返回 {敏感文件路径: [引入它的 commit 短哈希]}。

    口径说明
        只扫 ``master``（跟踪 origin / github 的分支），不扫 ``--all``。
        ``master`` 是会被推送到 origin / github 的分支，它的历史里出现
        **含真实密钥**的敏感文件 = 密钥已发布到公开远程仓库，必须拦截。

        而 gitea 远程的历史里已存在一个含密钥的迁移备份提交（``03018de7``），
        那是**换机迁移时人为上传的本地快照**，属于既成事实的独立问题
        （需轮换密钥 + 单独清理 gitea 历史），不应让本守卫永久变红。

        历史里若只是**占位符内容**（如仅含公开 API 域名、无任何密钥），
        不算泄露，不计入违规。
    """
    offenders: dict[str, list[str]] = {}
    for rel in SENSITIVE_FILES:
        result = _git(
            "log",
            "master",
            "--format=%H",
            "--diff-filter=A",
            "--",
            rel,
        )
        if result.returncode != 0:
            continue
        commits = [
            line.strip()[:8]
            for line in result.stdout.splitlines()
            if line.strip() and _blob_has_secret(rel, line.strip())
        ]
        if commits:
            offenders[rel] = commits
    return offenders


def _blob_has_secret(rel: str, commit: str) -> bool:
    """该提交引入的文件版本是否含真实密钥特征。"""
    blob = _git("rev-parse", f"{commit}:{rel}")
    if blob.returncode != 0:
        return False
    content = _git("cat-file", "-p", blob.stdout.strip())
    if content.returncode != 0:
        return False
    return bool(_SECRET_PATTERN.search(content.stdout))


class TestSensitiveFilesNotTracked:
    """敏感文件不得处于 Git 跟踪状态"""

    def test_sensitive_files_not_tracked(self):
        """敏感文件不得出现在 git ls-files 中"""
        tracked = _tracked_files()
        offenders = [rel for rel in SENSITIVE_FILES if rel in tracked]
        assert offenders == [], (
            f"这些含真实密钥的文件被 Git 跟踪了，push 时会泄露到远程仓库: {offenders}。"
            "请执行 `git rm --cached <文件>` 并确保 .gitignore 覆盖。"
        )

    def test_sensitive_files_are_ignored(self):
        """敏感文件必须被 .gitignore 命中，保证 git add . 不会带上它们"""
        offenders = [rel for rel in SENSITIVE_FILES if not _ignored_by_gitignore(rel)]
        assert offenders == [], (
            f"这些敏感文件没有被 .gitignore 覆盖，存在被误提交的风险: {offenders}"
        )

    def test_sensitive_files_exist_locally(self):
        """敏感文件应存在于本地工作区（本地可正常启动的前提）"""
        missing = [rel for rel in SENSITIVE_FILES if not (REPO_ROOT / rel).exists()]
        assert missing == [], (
            f"这些本地配置文件缺失，服务将无法正常启动: {missing}。"
            "可从本地备份或远程 gitea/master 恢复到工作区（不要提交进 Git）。"
        )


class TestNoSensitiveFilesInHistory:
    """历史提交不得引入敏感文件"""

    def test_no_commit_introduces_sensitive_files(self):
        """master 历史不得新增敏感文件（历史污染 = 视为已泄露）"""
        offenders = _files_introduced_by_history()
        assert offenders == {}, (
            "以下敏感文件曾被提交进 master 历史，等同于已泄露到 origin / github: "
            f"{offenders}。请提醒用户轮换对应密钥，并清理历史。"
        )
