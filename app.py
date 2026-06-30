"""
Flask Web 应用：根据身份证号前几位查询省市县
- 输入 2 位数字 → 查询省份
- 输入 4 位数字 → 查询省市
- 输入 6 位数字 → 查询省市县
同时返回区号、邮编、车牌前缀
"""
import os
import re
import sqlite3

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regions.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_by_prefix(prefix: str):
    """根据身份证号前缀查询区域信息，同时返回下一级子节点列表"""
    length = len(prefix)

    if length not in (2, 4, 6):
        return []

    conn = get_db()
    try:
        if length == 2:
            # 查询省份 + 其下所有城市
            rows = conn.execute(
                """SELECT name, adcode, prefix2, areacode, postcode
                    FROM regions
                   WHERE prefix2 = ? AND level = 'province'""",
                (prefix,),
            ).fetchall()

            results = []
            for row in rows:
                cities = conn.execute(
                    """SELECT name, adcode, prefix4, areacode, postcode, car_prefix
                        FROM regions
                       WHERE parent_code = ? AND level = 'city'
                       ORDER BY adcode""",
                    (row["adcode"],),
                ).fetchall()
                results.append({
                    "province": row["name"],
                    "city": None,
                    "district": None,
                    "adcode": row["adcode"],
                    "prefix": prefix,
                    "areacode": None,  # 省份本身没有区号
                    "postcode": row["postcode"],
                    "car_prefix": None,
                    "children": [
                        {"name": c["name"], "prefix": c["prefix4"], "adcode": c["adcode"],
                         "areacode": c["areacode"], "postcode": c["postcode"],
                         "car_prefix": c["car_prefix"]}
                        for c in cities
                    ],
                })
            return results

        elif length == 4:
            # 查询省市 + 其下所有区县
            rows = conn.execute(
                """SELECT c.name AS city_name, c.adcode AS city_code,
                          p.name AS province_name, p.adcode AS province_code,
                          p.prefix2, c.prefix4, c.areacode, c.postcode, c.car_prefix
                     FROM regions c
                     JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                    WHERE c.prefix4 = ? AND c.level = 'city'""",
                (prefix,),
            ).fetchall()

            results = []
            for row in rows:
                districts = conn.execute(
                    """SELECT name, adcode, prefix6, areacode, postcode
                        FROM regions
                       WHERE parent_code = ? AND level = 'district'
                       ORDER BY adcode""",
                    (row["city_code"],),
                ).fetchall()
                results.append({
                    "province": row["province_name"],
                    "city": row["city_name"],
                    "district": None,
                    "adcode": row["city_code"],
                    "prefix": prefix,
                    "prefix2": row["prefix2"],
                    "areacode": row["areacode"],
                    "postcode": row["postcode"],
                    "car_prefix": row["car_prefix"],
                    "children": [
                        {"name": d["name"], "prefix": d["prefix6"], "adcode": d["adcode"],
                         "areacode": d["areacode"], "postcode": d["postcode"],
                         "car_prefix": None}
                        for d in districts
                    ],
                })
            return results

        elif length == 6:
            # 查询省市县（叶子节点，无子级）
            rows = conn.execute(
                """SELECT d.name AS district_name, d.adcode AS district_code,
                          c.name AS city_name, c.adcode AS city_code, c.prefix4, c.car_prefix,
                          p.name AS province_name, p.adcode AS province_code, p.prefix2,
                          d.prefix6, d.areacode, d.postcode
                     FROM regions d
                     JOIN regions c ON d.parent_code = c.adcode AND c.level = 'city'
                     JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                    WHERE d.prefix6 = ? AND d.level = 'district'""",
                (prefix,),
            ).fetchall()
            return [
                {
                    "province": row["province_name"],
                    "city": row["city_name"],
                    "district": row["district_name"],
                    "adcode": row["district_code"],
                    "prefix": prefix,
                    "prefix2": row["prefix2"],
                    "prefix4": row["prefix4"],
                    "areacode": row["areacode"],
                    "postcode": row["postcode"],
                    "car_prefix": row["car_prefix"],
                    "children": [],
                }
                for row in rows
            ]
    finally:
        conn.close()

    return []


@app.route("/")
def index():
    return render_template("index.html")


def query_by_areacode(q: str):
    """按区号查询，返回匹配的城市列表"""
    conn = get_db()
    try:
        cities = conn.execute(
            """SELECT c.name AS city_name, c.adcode AS city_code,
                      p.name AS province_name, p.adcode AS province_code,
                      p.prefix2, c.prefix4, c.areacode, c.postcode, c.car_prefix
                 FROM regions c
                 JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                WHERE c.areacode = ? AND c.level = 'city'
                ORDER BY c.adcode""",
            (q,),
        ).fetchall()

        results = []
        for row in cities:
            districts = conn.execute(
                """SELECT name, adcode, prefix6, areacode, postcode
                    FROM regions
                   WHERE parent_code = ? AND level = 'district'
                   ORDER BY adcode""",
                (row["city_code"],),
            ).fetchall()
            results.append({
                "province": row["province_name"],
                "city": row["city_name"],
                "district": None,
                "adcode": row["city_code"],
                "prefix": row["prefix4"],
                "prefix2": row["prefix2"],
                "areacode": row["areacode"],
                "postcode": row["postcode"],
                "car_prefix": row["car_prefix"],
                "children": [
                    {"name": d["name"], "prefix": d["prefix6"], "adcode": d["adcode"],
                     "areacode": d["areacode"], "postcode": d["postcode"], "car_prefix": None}
                    for d in districts
                ],
            })
        return results
    finally:
        conn.close()


def query_by_postcode(q: str):
    """按邮编查询，先查城市，再查区县"""
    conn = get_db()
    try:
        # 先查城市级别
        cities = conn.execute(
            """SELECT c.name AS city_name, c.adcode AS city_code,
                      p.name AS province_name, p.adcode AS province_code,
                      p.prefix2, c.prefix4, c.areacode, c.postcode, c.car_prefix
                 FROM regions c
                 JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                WHERE c.postcode = ? AND c.level = 'city'
                ORDER BY c.adcode""",
            (q,),
        ).fetchall()

        results = []
        for row in cities:
            districts = conn.execute(
                """SELECT name, adcode, prefix6, areacode, postcode
                    FROM regions
                   WHERE parent_code = ? AND level = 'district'
                   ORDER BY adcode""",
                (row["city_code"],),
            ).fetchall()
            results.append({
                "province": row["province_name"],
                "city": row["city_name"],
                "district": None,
                "adcode": row["city_code"],
                "prefix": row["prefix4"],
                "prefix2": row["prefix2"],
                "areacode": row["areacode"],
                "postcode": row["postcode"],
                "car_prefix": row["car_prefix"],
                "children": [
                    {"name": d["name"], "prefix": d["prefix6"], "adcode": d["adcode"],
                     "areacode": d["areacode"], "postcode": d["postcode"], "car_prefix": None}
                    for d in districts
                ],
            })

        # 再查区县级别
        districts = conn.execute(
            """SELECT d.name AS district_name, d.adcode AS district_code,
                      d.prefix6, d.areacode, d.postcode,
                      c.name AS city_name, c.adcode AS city_code,
                      c.prefix4, c.car_prefix,
                      p.name AS province_name, p.prefix2
                 FROM regions d
                 JOIN regions c ON d.parent_code = c.adcode AND c.level = 'city'
                 JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                WHERE d.postcode = ? AND d.level = 'district'
                ORDER BY d.adcode""",
            (q,),
        ).fetchall()

        for row in districts:
            results.append({
                "province": row["province_name"],
                "city": row["city_name"],
                "district": row["district_name"],
                "adcode": row["district_code"],
                "prefix": row["prefix6"],
                "prefix2": row["prefix2"],
                "prefix4": row["prefix4"],
                "areacode": row["areacode"],
                "postcode": row["postcode"],
                "car_prefix": row["car_prefix"],
                "children": [],
            })

        return results
    finally:
        conn.close()


def query_by_car_prefix(q: str):
    """按车牌前缀查询，模糊匹配"""
    conn = get_db()
    try:
        cities = conn.execute(
            """SELECT c.name AS city_name, c.adcode AS city_code,
                      p.name AS province_name, p.adcode AS province_code,
                      p.prefix2, c.prefix4, c.areacode, c.postcode, c.car_prefix
                 FROM regions c
                 JOIN regions p ON c.parent_code = p.adcode AND p.level = 'province'
                WHERE c.car_prefix LIKE ? AND c.level = 'city'
                ORDER BY c.adcode""",
            (f"%{q}%",),
        ).fetchall()

        results = []
        for row in cities:
            districts = conn.execute(
                """SELECT name, adcode, prefix6, areacode, postcode
                    FROM regions
                   WHERE parent_code = ? AND level = 'district'
                   ORDER BY adcode""",
                (row["city_code"],),
            ).fetchall()
            results.append({
                "province": row["province_name"],
                "city": row["city_name"],
                "district": None,
                "adcode": row["city_code"],
                "prefix": row["prefix4"],
                "prefix2": row["prefix2"],
                "areacode": row["areacode"],
                "postcode": row["postcode"],
                "car_prefix": row["car_prefix"],
                "children": [
                    {"name": d["name"], "prefix": d["prefix6"], "adcode": d["adcode"],
                     "areacode": d["areacode"], "postcode": d["postcode"], "car_prefix": None}
                    for d in districts
                ],
            })
        return results
    finally:
        conn.close()


def query_by_name(q: str):
    """按名称右模糊查询，匹配省/市/县，返回完整层级"""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT name, adcode, level, parent_code, prefix2, prefix4, prefix6,
                      areacode, postcode, car_prefix
                 FROM regions
                WHERE name LIKE ?
                ORDER BY CASE level
                    WHEN 'province' THEN 1
                    WHEN 'city' THEN 2
                    WHEN 'district' THEN 3
                END
                LIMIT 30""",
            (f"{q}%",),
        ).fetchall()

        results = []
        for row in rows:
            if row["level"] == "province":
                # 省份：查其下城市
                cities = conn.execute(
                    """SELECT name, adcode, prefix4, areacode, postcode, car_prefix
                        FROM regions WHERE parent_code=? AND level='city' ORDER BY adcode""",
                    (row["adcode"],),
                ).fetchall()
                results.append({
                    "province": row["name"], "city": None, "district": None,
                    "adcode": row["adcode"], "prefix": row["prefix2"],
                    "areacode": None, "postcode": row["postcode"], "car_prefix": None,  # 省份本身没有区号
                    "children": [
                        {"name": c["name"], "prefix": c["prefix4"], "adcode": c["adcode"],
                         "areacode": c["areacode"], "postcode": c["postcode"], "car_prefix": c["car_prefix"]}
                        for c in cities
                    ],
                })
            elif row["level"] == "city":
                # 城市：查上级省 + 下级区县
                province = conn.execute(
                    "SELECT name, prefix2 FROM regions WHERE adcode=? AND level='province'",
                    (row["parent_code"],),
                ).fetchone()
                districts = conn.execute(
                    """SELECT name, adcode, prefix6, areacode, postcode
                        FROM regions WHERE parent_code=? AND level='district' ORDER BY adcode""",
                    (row["adcode"],),
                ).fetchall()
                results.append({
                    "province": province["name"] if province else None,
                    "city": row["name"], "district": None,
                    "adcode": row["adcode"], "prefix": row["prefix4"],
                    "prefix2": province["prefix2"] if province else None,
                    "areacode": row["areacode"], "postcode": row["postcode"],
                    "car_prefix": row["car_prefix"],
                    "children": [
                        {"name": d["name"], "prefix": d["prefix6"], "adcode": d["adcode"],
                         "areacode": d["areacode"], "postcode": d["postcode"], "car_prefix": None}
                        for d in districts
                    ],
                })
            else:  # district
                # 区县：查上级省市
                city = conn.execute(
                    "SELECT name, adcode, prefix4, car_prefix FROM regions WHERE adcode=? AND level='city'",
                    (row["parent_code"],),
                ).fetchone()
                province = None
                if city:
                    province = conn.execute(
                        "SELECT name, prefix2 FROM regions WHERE adcode=? AND level='province'",
                        (city["adcode"][:2] + "0000",),
                    ).fetchone()
                results.append({
                    "province": province["name"] if province else None,
                    "city": city["name"] if city else None,
                    "district": row["name"],
                    "adcode": row["adcode"], "prefix": row["prefix6"],
                    "prefix2": province["prefix2"] if province else None,
                    "prefix4": city["prefix4"] if city else None,
                    "areacode": row["areacode"], "postcode": row["postcode"],
                    "car_prefix": city["car_prefix"] if city else None,
                    "children": [],
                })
        return results
    finally:
        conn.close()


@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify({"error": "请输入查询内容", "results": []}), 400

    results = []

    if q.isdigit():
        # 先尝试身份证前缀；未命中则 fallback 到区号/邮编
        results = query_by_prefix(q)
        if not results:
            results = query_by_areacode(q)
        if not results:
            results = query_by_postcode(q)
    else:
        # 含字母 → 车牌查询；纯中文 → 名称查询
        if re.search(r'[A-Za-z]', q):
            results = query_by_car_prefix(q)
            if not results:
                results = query_by_name(q)
        else:
            results = query_by_name(q)

    if not results:
        return jsonify({
            "error": f"未找到与「{q}」匹配的区域信息",
            "results": [],
        }), 404

    return jsonify({"error": None, "results": results})


@app.route("/api/stats")
def stats():
    """返回数据库统计信息"""
    conn = get_db()
    try:
        row = conn.execute("SELECT level, COUNT(*) AS cnt FROM regions GROUP BY level").fetchall()
        stats = {r["level"]: r["cnt"] for r in row}
        return jsonify(stats)
    finally:
        conn.close()


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
