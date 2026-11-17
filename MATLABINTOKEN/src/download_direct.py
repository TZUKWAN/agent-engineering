"""
直接下载AgentNet数据文件
"""

import os
from huggingface_hub import hf_hub_download, snapshot_download

def main():
    print("=" * 60)
    print("直接下载AgentNet数据")
    print("=" * 60)

    repo_id = "xlangai/AgentNet"
    output_dir = "data/raw"
    os.makedirs(output_dir, exist_ok=True)

    files_to_download = [
        "README.md",
        "meta_data_merged.jsonl",
        "agentnet_win_mac_18k.jsonl",
        "agentnet_ubuntu_5k.jsonl"
    ]

    downloaded = []
    failed = []

    for filename in files_to_download:
        try:
            print(f"\n正在下载: {filename}")
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                repo_type="dataset",
                local_dir=output_dir,
                local_dir_use_symlinks=False,
                force_download=True
            )
            print(f"  ✓ 已保存: {local_path}")
            downloaded.append(filename)
        except Exception as e:
            print(f"  ✗ 下载失败: {e}")
            failed.append(filename)

    print(f"\n" + "=" * 60)
    print(f"下载完成: {len(downloaded)} 成功, {len(failed)} 失败")
    print("=" * 60)

    if downloaded:
        print("\n已下载的文件:")
        for f in downloaded:
            full_path = os.path.join(output_dir, f)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                print(f"  - {f} ({size:,} bytes)")

    print("\n检查目录内容:")
    for f in os.listdir(output_dir):
        full_path = os.path.join(output_dir, f)
        if os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            print(f"  {f}: {size:,} bytes")

if __name__ == "__main__":
    main()
