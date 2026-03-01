#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
启用双渠道模式配置脚本

此脚本用于修改配置文件，激活双渠道筛选模式。
"""

import json
from pathlib import Path

def enable_dual_channel_mode():
    """启用双渠道模式"""
    config_path = Path("config/thresholds.json")

    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 更新配置以启用双渠道模式
    config["category_filter"]["dual_channel_mode"] = True
    config["category_filter"]["tools_channel_count"] = 5
    config["category_filter"]["academic_media_channel_count"] = 5

    # 保存更新后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("双渠道模式已启用！")
    print("- tools_channel_count:", config["category_filter"]["tools_channel_count"])
    print("- academic_media_channel_count:", config["category_filter"]["academic_media_channel_count"])

def disable_dual_channel_mode():
    """禁用双渠道模式，恢复为单渠道模式"""
    config_path = Path("config/thresholds.json")

    # 读取现有配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 更新配置以禁用双渠道模式
    config["category_filter"]["dual_channel_mode"] = False
    config["category_filter"]["tools_channel_count"] = 5
    config["category_filter"]["academic_media_channel_count"] = 5

    # 保存更新后的配置
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("双渠道模式已禁用，恢复为单渠道模式！")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        if action == "enable":
            enable_dual_channel_mode()
        elif action == "disable":
            disable_dual_channel_mode()
        else:
            print("用法: python enable_dual_channel.py [enable|disable]")
            print("  enable: 启用双渠道模式")
            print("  disable: 禁用双渠道模式")
    else:
        print("用法: python enable_dual_channel.py [enable|disable]")
        print("  enable: 启用双渠道模式")
        print("  disable: 禁用双渠道模式")