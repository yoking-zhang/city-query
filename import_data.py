"""
数据导入脚本：从 JSON 数据解析省市县及身份证号前缀、区号、邮编，
导入到 SQLite 数据库。
"""
import json
import sqlite3
import os
import argparse


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regions.db")


def create_tables(conn: sqlite3.Connection):
    """创建数据库表结构"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,          -- 区域名称
            adcode      TEXT    NOT NULL,          -- 行政区划代码 (6位)
            level       TEXT    NOT NULL,          -- province / city / district
            parent_code TEXT,                      -- 上级行政区划代码
            prefix2     TEXT,                      -- 身份证号前2位 (省)
            prefix4     TEXT,                      -- 身份证号前4位 (省市)
            prefix6     TEXT,                      -- 身份证号前6位 (省市县)
            areacode    TEXT,                      -- 电话区号
            postcode    TEXT,                      -- 邮政编码
            car_prefix  TEXT,                      -- 车牌号前缀
            pinyin      TEXT                       -- 拼音首字母
        )
    """)
    # 为常用查询建立索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prefix2 ON regions(prefix2)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prefix4 ON regions(prefix4)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prefix6 ON regions(prefix6)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parent  ON regions(parent_code)")
    conn.commit()


def import_shenfenzheng(conn: sqlite3.Connection, filepath: str):
    """
    从 shenfenzheng.json 解析数据并导入

    数据结构:
    [
      {
        "Province": "北京市",
        "ID": "110000",
        "Short_ID": "11",
        "children": [...]
      },
      ...
    ]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for province in data:
        p_name = province["Province"]
        p_code = province["ID"]
        p_prefix2 = province["Short_ID"]

        rows.append({
            "name": p_name,
            "adcode": p_code,
            "level": "province",
            "parent_code": None,
            "prefix2": p_prefix2,
            "prefix4": None,
            "prefix6": None,
        })

        for city in province.get("children", []):
            c_name = city["City"]
            c_code = city["ID"]
            c_prefix4 = city["Short_ID"]

            rows.append({
                "name": c_name,
                "adcode": c_code,
                "level": "city",
                "parent_code": p_code,
                "prefix2": p_prefix2,
                "prefix4": c_prefix4,
                "prefix6": None,
            })

            for district in city.get("children", []):
                d_name = district["County"]
                d_code = district["ID"]
                d_prefix6 = district["Short_ID"]

                rows.append({
                    "name": d_name,
                    "adcode": d_code,
                    "level": "district",
                    "parent_code": c_code,
                    "prefix2": p_prefix2,
                    "prefix4": c_prefix4,
                    "prefix6": d_prefix6,
                })

    conn.executemany(
        """INSERT INTO regions (name, adcode, level, parent_code, prefix2, prefix4, prefix6)
           VALUES (:name, :adcode, :level, :parent_code, :prefix2, :prefix4, :prefix6)""",
        rows,
    )
    conn.commit()

    stats = {
        "province": sum(1 for r in rows if r["level"] == "province"),
        "city": sum(1 for r in rows if r["level"] == "city"),
        "district": sum(1 for r in rows if r["level"] == "district"),
    }
    return stats


def build_adcode_map(filepath: str, field: str):
    """
    从 areacode.json / postcode.json 构建 adcode → value 映射

    文件结构: [{Province, ID, areacode/postcode, children: [{City, ID, ...}]}]
    遍历到叶子，只要节点的 field 字段有值就记录
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}

    def walk(node, _field):
        if "ID" in node and _field in node and node[_field]:
            mapping[str(node["ID"])] = str(node[_field])
        for child in node.get("children", []):
            walk(child, _field)

    for province in data:
        walk(province, field)

    return mapping


def enrich_car_prefix(conn: sqlite3.Connection, filepath: str):
    """从 car_no_prefix.json 导入车牌前缀，仅存到地级市"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    count = 0
    for city_name, prefixes in data.items():
        # 直辖市（北京/上海/天津/重庆）的 city 级别 name 和 province 同名，
        # 只更新 level='city' 的记录
        joined = ",".join(prefixes)
        cur = conn.execute(
            "UPDATE regions SET car_prefix = ? WHERE name = ? AND level = 'city'",
            (joined, city_name),
        )
        if cur.rowcount > 0:
            count += cur.rowcount
        else:
            print(f"  未匹配: {city_name}")

    conn.commit()
    print(f"已更新 {count} 条车牌前缀数据")


def enrich_from_map(conn: sqlite3.Connection, mapping: dict, column: str, label: str):
    """根据 adcode→值 的映射，批量更新数据库某列"""
    count = 0
    for adcode, value in mapping.items():
        conn.execute(f"UPDATE regions SET {column} = ? WHERE adcode = ?", (value, adcode))
        count += 1
    conn.commit()
    print(f"已更新 {count} 条{label}数据")


def enrich_pinyin(conn: sqlite3.Connection, filepath: str):
    """从 region.json 中提取拼音首字母"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}

    def walk(node):
        if "adcode" in node and "pinyin1" in node:
            mapping[str(node["adcode"])] = node["pinyin1"]
        for child in node.get("children", []):
            walk(child)

    for root in data:
        walk(root)

    for adcode, pinyin in mapping.items():
        conn.execute("UPDATE regions SET pinyin = ? WHERE adcode = ?", (pinyin, adcode))
    conn.commit()
    print(f"已更新 {len(mapping)} 条拼音数据")


def main():
    parser = argparse.ArgumentParser(description="导入省市县数据（身份证前缀/区号/邮编）")
    parser.add_argument("--shenfenzheng",
        default=os.path.join(os.path.dirname(__file__), "data", "shenfenzheng.json"))
    parser.add_argument("--areacode",
        default=os.path.join(os.path.dirname(__file__), "data", "areacode.json"))
    parser.add_argument("--postcode",
        default=os.path.join(os.path.dirname(__file__), "data", "postcode.json"))
    parser.add_argument("--region",
        default=os.path.join(os.path.dirname(__file__), "data", "region.json"))
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    if os.path.exists(args.db):
        os.remove(args.db)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    create_tables(conn)

    # 1. 身份证前缀
    stats = import_shenfenzheng(conn, args.shenfenzheng)
    print(f"导入完成: 省份 {stats['province']} 个, 城市 {stats['city']} 个, 区县 {stats['district']} 个")

    # 2. 电话区号
    if os.path.exists(args.areacode):
        areacode_map = build_adcode_map(args.areacode, "areacode")
        enrich_from_map(conn, areacode_map, "areacode", "区号")
    else:
        print("areacode.json 未找到，跳过区号导入")

    # 3. 邮编
    if os.path.exists(args.postcode):
        postcode_map = build_adcode_map(args.postcode, "postcode")
        enrich_from_map(conn, postcode_map, "postcode", "邮编")
    else:
        print("postcode.json 未找到，跳过邮编导入")

    # 4. 车牌前缀
    car_prefix_path = os.path.join(os.path.dirname(__file__), "data", "car_no_prefix.json")
    if os.path.exists(car_prefix_path):
        enrich_car_prefix(conn, car_prefix_path)
    else:
        print("car_no_prefix.json 未找到，跳过车牌前缀导入")

    # 5. 拼音
    if os.path.exists(args.region):
        enrich_pinyin(conn, args.region)
    else:
        print("region.json 未找到，跳过拼音导入")

    conn.close()
    print("数据库已保存到:", args.db)


if __name__ == "__main__":
    main()
