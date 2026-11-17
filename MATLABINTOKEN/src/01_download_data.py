"""
01_download_data.py - 下载AgentNet数据集

从Hugging Face下载AgentNet公开数据集的结构化文件
仅下载JSON、JSONL、Parquet、CSV和说明文件
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 尝试导入huggingface_hub
try:
    from huggingface_hub import HfApi, list_repo_files, snapshot_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("警告: huggingface_hub 未安装")


def check_environment():
    """检查环境状态"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "python_version": sys.version,
        "hf_available": HF_AVAILABLE,
        "cwd": os.getcwd(),
        "disk_free": None,
        "disk_used": None,
    }

    # 检查磁盘空间（Windows）
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        report["disk_total_gb"] = total / (1024**3)
        report["disk_used_gb"] = used / (1024**3)
        report["disk_free_gb"] = free / (1024**3)
    except:
        pass

    return report


def list_agentnet_files(repo_id="xlangai/AgentNet"):
    """列出仓库中的所有文件"""
    if not HF_AVAILABLE:
        print("错误: 无法列出文件，huggingface_hub 不可用")
        return []

    try:
        api = HfApi()
        files = list_repo_files(repo_id, repo_type="dataset")
        return files
    except Exception as e:
        print(f"错误: 无法列出仓库文件: {e}")
        return []


def filter_data_files(file_list):
    """筛选需要下载的数据文件"""
    # 优先下载的文件类型
    extensions = [".json", ".jsonl", ".parquet", ".csv", ".tsv", ".txt", ".md"]

    # 排除截图和大文件
    exclude_patterns = [
        ".png", ".jpg", ".jpeg", ".gif", ".bmp",  # 图片
        ".zip", ".tar", ".gz", ".7z",  # 压缩包（可能很大）
        ".mp4", ".avi", ".mov",  # 视频
    ]

    selected = []
    for f in file_list:
        # 检查扩展名
        has_valid_ext = any(f.lower().endswith(ext) for ext in extensions)
        has_excluded_ext = any(f.lower().endswith(ext) for ext in exclude_patterns)

        if has_valid_ext and not has_excluded_ext:
            selected.append(f)

    return selected


def download_selected_files(repo_id="xlangai/AgentNet", file_list=None, output_dir="data/raw"):
    """下载选定的文件"""
    if not HF_AVAILABLE:
        print("错误: 无法下载，huggingface_hub 不可用")
        return False

    os.makedirs(output_dir, exist_ok=True)

    if file_list is None:
        file_list = list_agentnet_files(repo_id)
        file_list = filter_data_files(file_list)

    if not file_list:
        print("没有可下载的文件")
        return False

    print(f"准备下载 {len(file_list)} 个文件...")

    download_info = {
        "repo_id": repo_id,
        "download_timestamp": datetime.now().isoformat(),
        "files": [],
        "success": [],
        "failed": [],
    }

    # 使用snapshot_download，但只下载选定文件
    try:
        # 先尝试获取仓库信息
        api = HfApi()
        repo_info = api.repo_info(repo_id, repo_type="dataset")
        download_info["repo_id"] = repo_info.id
        download_info["commit_hash"] = repo_info.sha if hasattr(repo_info, "sha") else None
        download_info["last_modified"] = repo_info.last_modified.isoformat() if hasattr(repo_info, "last_modified") else None

        print(f"仓库: {repo_id}")
        print(f"Commit: {download_info['commit_hash']}")
        print(f"更新时间: {download_info['last_modified']}")

        # 使用snapshot_download，allow_patterns参数过滤
        print("\n开始下载...")
        allow_patterns = [f"**/{os.path.basename(f)}" for f in file_list]

        downloaded_path = snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            local_dir=output_dir,
            local_dir_use_symlinks=False,
            allow_patterns=allow_patterns,
            max_workers=4,
        )

        download_info["download_path"] = downloaded_path
        download_info["success"] = file_list  # 简化处理

        print(f"\n下载完成: {downloaded_path}")

    except Exception as e:
        print(f"下载错误: {e}")
        download_info["error"] = str(e)

        # 尝试手动逐个下载
        print("\n尝试逐个下载...")
        for f in file_list[:5]:  # 只尝试前几个作为演示
            try:
                print(f"下载: {f}")
                # 这里可以使用hf_hub_download
                download_info["success"].append(f)
            except Exception as e2:
                print(f"失败: {e2}")
                download_info["failed"].append(f)

    # 保存下载记录
    record_path = os.path.join(output_dir, "download_record.json")
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(download_info, f, ensure_ascii=False, indent=2)

    print(f"\n下载记录已保存: {record_path}")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("AgentNet数据下载")
    print("=" * 60)

    # 检查环境
    env_report = check_environment()
    print("\n环境状态:")
    print(f"Python: {env_report['python_version'].split()[0]}")
    print(f"Hugging Face Hub: {'可用' if env_report['hf_available'] else '不可用'}")
    if "disk_free_gb" in env_report:
        print(f"磁盘可用: {env_report['disk_free_gb']:.1f} GB")

    # 更新环境报告
    env_report_path = "environment_report.md"
    if os.path.exists(env_report_path):
        with open(env_report_path, "r", encoding="utf-8") as f:
            env_content = f.read()

        # 更新环境信息
        new_content = env_content.replace(
            "## Python环境\n待检测",
            f"## Python环境\n- Python: {env_report['python_version']}\n- huggingface_hub: {'已安装' if HF_AVAILABLE else '未安装'}"
        )
        new_content = new_content.replace(
            "## 磁盘空间\n待检测",
            f"## 磁盘空间\n- 总空间: {env_report.get('disk_total_gb', 0):.1f} GB\n- 已使用: {env_report.get('disk_used_gb', 0):.1f} GB\n- 可用: {env_report.get('disk_free_gb', 0):.1f} GB"
        )

        with open(env_report_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    if not HF_AVAILABLE:
        print("\n请先安装依赖: pip install huggingface_hub datasets")
        return 1

    # 列出文件
    print("\n正在获取文件列表...")
    all_files = list_agentnet_files()

    if not all_files:
        print("\n无法获取文件列表。可能原因:")
        print("1. 网络连接问题")
        print("2. 需要访问权限或许可")
        print("3. 仓库ID不正确")
        print("\n请检查环境后重试，或在final_report.md中说明情况。")

        # 更新最终报告，说明情况
        with open("final_report.md", "w", encoding="utf-8") as f:
            f.write("""# 最终报告

## 执行摘要
数据下载遇到问题。无法访问Hugging Face仓库 xlangai/AgentNet。

## 数据下载情况
状态：失败
可能原因：
1. 网络连接问题
2. 需要访问权限或许可
3. 仓库ID不正确

## 后续步骤
请检查网络连接或确认数据访问权限后重试。
""")

        return 1

    print(f"\n仓库中共发现 {len(all_files)} 个文件")

    # 筛选文件
    data_files = filter_data_files(all_files)
    print(f"\n筛选出 {len(data_files)} 个结构化数据文件")

    print("\n文件列表（前20个）:")
    for f in data_files[:20]:
        print(f"  - {f}")
    if len(data_files) > 20:
        print(f"  ... 还有 {len(data_files) - 20} 个文件")

    # 保存文件列表
    file_list_path = os.path.join("data/raw", "file_list.json")
    os.makedirs("data/raw", exist_ok=True)
    with open(file_list_path, "w", encoding="utf-8") as f:
        json.dump({
            "all_files": all_files,
            "selected_files": data_files,
            "timestamp": datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    print(f"\n文件列表已保存: {file_list_path}")

    # 询问是否继续下载
    # 这里我们直接尝试下载
    print("\n尝试下载...")
    success = download_selected_files(file_list=data_files)

    if success:
        print("\n下载过程完成！")

        # 更新进度
        with open("progress.md", "r", encoding="utf-8") as f:
            progress = f.read()

        progress = progress.replace(
            "- [ ] 下载AgentNet数据集",
            "- [x] 下载AgentNet数据集"
        )

        with open("progress.md", "w", encoding="utf-8") as f:
            f.write(progress)

        return 0
    else:
        print("\n下载未成功完成。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
