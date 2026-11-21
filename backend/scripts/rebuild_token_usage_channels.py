"""重建 Token Usage 渠道数据（一次性维护脚本）

用途：渠道列上线后，把本地仍保留的历史用量按渠道重采集一遍。
默认只处理当前登录用户不可知，因此必须显式指定 ``--user``。

用法：
    cd backend
    python -m scripts.rebuild_token_usage_channels --user peanut --days 3650

说明：
- 走正常 ``sync_token_usage`` 链路，幂等；
- 同步窗口内的 legacy NULL 行会被带渠道的新行替换，不会双计；
- 窗口外历史若无本地数据则保持「未知渠道（历史）」。
"""

import argparse
import logging
import sys

from app.services.token_usage_channels import reset_channel_cache
from app.services.token_usage_sync_service import sync_token_usage


def main() -> int:
    parser = argparse.ArgumentParser(description="重建 Token Usage 渠道数据")
    parser.add_argument("--user", required=True, help="用户 ID")
    parser.add_argument("--days", type=int, default=3650, help="回溯天数（默认 3650）")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger = logging.getLogger(__name__)

    reset_channel_cache()
    result = sync_token_usage(user_id=args.user, days=max(1, args.days))
    logger.info(
        "重建完成: 用户=%s, 记录数=%s, 来源=%s",
        args.user,
        result.get("total_records"),
        ",".join(result.get("sources_synced") or []),
    )
    if result.get("errors"):
        for error in result["errors"]:
            logger.warning("同步告警: %s", error)
    return 0


if __name__ == "__main__":
    sys.exit(main())