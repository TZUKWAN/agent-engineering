"""
02_inspect_files.py - 检查已下载的数据文件

读取已下载的数据文件，核验数据结构和字段
"""

import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd


def find_data_files(raw_dir="data/raw"):
    """查找所有数据文件"""
    if not os.path.exists(raw_dir):
        return []

    data_files = []
    for root, dirs, files in os.walk(raw_dir):
        for f in files:
            if f.endswith((".json", ".jsonl", ".parquet", ".csv", ".tsv")):
                data_files.append(os.path.join(root, f))

    return data_files


def inspect_json_file(filepath, max_records=5):
    """检查JSON文件"""
    result = {
        "file": filepath,
        "type": "json",
        "readable": False,
        "records": 0,
        "sample": None,
        "fields": [],
        "error": None,
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        result["readable"] = True

        if isinstance(data, list):
            result["records"] = len(data)
            if data:
                result["sample"] = data[:min(max_records, len(data))]
                result["fields"] = sorted(list(data[0].keys())) if isinstance(data[0], dict) else []
        elif isinstance(data, dict):
            result["records"] = 1
            result["sample"] = data
            result["fields"] = sorted(list(data.keys()))
        else:
            result["records"] = 1
            result["sample"] = str(data)[:500]

    except Exception as e:
        result["error"] = str(e)

    return result


def inspect_jsonl_file(filepath, max_records=5):
    """检查JSONL文件"""
    result = {
        "file": filepath,
        "type": "jsonl",
        "readable": False,
        "records": 0,
        "sample": [],
        "fields": [],
        "error": None,
    }

    try:
        records = []
        with open(filepath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records.append(record)
                    if len(records) >= max_records + 100:  # 多读一些来估计总数
                        break
                except:
                    pass

        result["readable"] = True
        result["sample"] = records[:max_records]
        result["records"] = len(records)  # 这只是抽样，不是总数

        if records and isinstance(records[0], dict):
            result["fields"] = sorted(list(records[0].keys()))

        # 尝试获取准确的行数
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                result["records"] = sum(1 for line in f if line.strip())
        except:
            pass

    except Exception as e:
        result["error"] = str(e)

    return result


def inspect_parquet_file(filepath, max_records=5):
    """检查Parquet文件"""
    result = {
        "file": filepath,
        "type": "parquet",
        "readable": False,
        "records": 0,
        "sample": None,
        "fields": [],
        "error": None,
    }

    try:
        df = pd.read_parquet(filepath)
        result["readable"] = True
        result["records"] = len(df)
        result["fields"] = sorted(list(df.columns))
        result["sample"] = df.head(max_records).to_dict("records")

    except Exception as e:
        result["error"] = str(e)

    return result


def inspect_csv_file(filepath, max_records=5):
    """检查CSV文件"""
    result = {
        "file": filepath,
        "type": "csv",
        "readable": False,
        "records": 0,
        "sample": None,
        "fields": [],
        "error": None,
    }

    try:
        df = pd.read_csv(filepath, nrows=100)
        result["readable"] = True
        result["fields"] = sorted(list(df.columns))
        result["sample"] = df.head(max_records).to_dict("records")

        # 估算总行数
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                result["records"] = sum(1 for line in f) - 1  # 减去表头
        except:
            pass

    except Exception as e:
        result["error"] = str(e)

    return result


def inspect_file(filepath):
    """检查单个文件"""
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        return inspect_json_file(filepath)
    elif ext == ".jsonl":
        return inspect_jsonl_file(filepath)
    elif ext == ".parquet":
        return inspect_parquet_file(filepath)
    elif ext in (".csv", ".tsv"):
        return inspect_csv_file(filepath)
    else:
        return {
            "file": filepath,
            "type": "unknown",
            "readable": False,
            "error": "Unknown file type",
        }


def main():
    """主函数"""
    print("=" * 60)
    print("检查数据文件")
    print("=" * 60)

    raw_dir = "data/raw"

    # 查找数据文件
    data_files = find_data_files(raw_dir)

    if not data_files:
        print(f"\n在 {raw_dir}/ 中未找到数据文件")
        print("请先运行 01_download_data.py 下载数据")
        return 1

    print(f"\n找到 {len(data_files)} 个数据文件\n")

    # 检查每个文件
    inspection_results = []
    for f in data_files:
        print(f"检查: {os.path.basename(f)}")
        result = inspect_file(f)
        inspection_results.append(result)

        if result["readable"]:
            print(f"  - 类型: {result['type']}")
            print(f"  - 记录数: {result['records']}")
            print(f"  - 字段: {', '.join(result['fields'][:10])}")
            if len(result['fields']) > 10:
                print(f"    ... 还有 {len(result['fields']) - 10} 个字段")
        else:
            print(f"  - 错误: {result['error']}")
        print()

    # 保存检查结果
    os.makedirs("data/interim", exist_ok=True)
    output_path = os.path.join("data/interim", "file_inspection.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "files": inspection_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"检查结果已保存: {output_path}")

    # 更新数据字典
    dd_path = "data_dictionary.md"
    if os.path.exists(dd_path):
        with open(dd_path, "r", encoding="utf-8") as f:
            dd_content = f.read()

        # 更新字段信息
        field_info = ""
        for r in inspection_results:
            if r["readable"] and r["fields"]:
                field_info += f"\n### {os.path.basename(r['file'])}\n"
                field_info += f"- 记录数: {r['records']}\n"
                field_info += f"- 字段: {', '.join(r['fields'])}\n"

        if field_info:
            dd_content = dd_content.replace(
                "## 字段映射（待核验）",
                f"## 字段映射\n\n### 已检查文件\n{field_info}"
            )

            with open(dd_path, "w", encoding="utf-8") as f:
                f.write(dd_content)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
