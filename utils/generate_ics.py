import json
import sys
import uuid
import re
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict

# ===== 正确的节次时间（按 jc 计算） =====
JC_TIME = {
    1: ("08:30", "10:15"),
    2: ("10:30", "12:15"),
    3: ("14:00", "15:45"),
    4: ("16:00", "17:45"),
    5: ("18:45", "20:30"),
    6: ("20:45", "22:30"),
}
# ======================================


def parse_course_info(sksj):
    lines = sksj.strip().split("\n")

    name_lines = []
    teacher = ""
    location = "无地点"

    # 先收集所有 [] 里的内容
    brackets = re.findall(r"\[(.*?)\]", sksj)

    # 用正则识别各字段，避免 "周健友" 中的 "周" 被误判为周次信息
    week_pattern = re.compile(r"\d.*周")       # 周次: 含数字 + 周 (如 "1-13周", "10,11-13周")
    section_pattern = re.compile(r"\d.*节")    # 节次: 含数字 + 节 (如 "9-10节", "5-6节")
    location_pattern = re.compile(r"^[A-Za-z]\d+")  # 教室: 字母开头 + 数字 (如 T5505, K526)
    teacher_pattern = re.compile(r"^[一-鿿]{2,4}$")  # 中文姓名: 2-4个汉字

    # 过滤掉周次和节次信息
    info_items = []
    for item in brackets:
        if week_pattern.search(item) or section_pattern.search(item):
            continue
        info_items.append(item)

    # 识别教室 (优先匹配标准教室编号如 T5505, K526)
    for item in info_items:
        if location_pattern.match(item):
            location = item
            break

    # 识别教师 (纯中文姓名, 2-4 个汉字)
    for item in info_items:
        if item != location and teacher_pattern.match(item):
            teacher = item
            break

    # 回退: 如果还没找到教室, 从剩余非教师项中取 (处理 "活动中心3楼" 等中文地点)
    if location == "无地点":
        for item in info_items:
            if item != teacher:
                location = item
                break

    # 课程名 = 所有不以 [ 开头的前几行
    for line in lines:
        if line.startswith("["):
            break
        name_lines.append(line.strip())

    name = " - ".join(name_lines)

    return name, teacher, location


def parse_weekday_and_jc(key):
    """
    格式:
    xq7_jc1
    代表周日（xq7）第1节（jc1）
    """
    parts = key.split("_")
    
    weekday = parts[0].replace("xq", "")
    jc = parts[1].replace("jc", "")

    if weekday.isdigit() and jc.isdigit():
        weekday = int(weekday)
        jc = int(jc)
    else:
        print(f"无法解析的 KEY: {key}", file=sys.stderr)
        weekday = -1
        jc = -1

    return weekday, jc


def parse_weeks(zc):
    weeks = []
    for i, c in enumerate(zc):
        if c == "1":
            weeks.append(i)  # i=1表示第1周（第0周默认跳过）
    return weeks


def merge_courses(data):
    """
    合并同一门课连续 jc
    """
    grouped = defaultdict(list)

    for course in data:
        name, teacher, location = parse_course_info(course["SKSJ"])
        key = course["KEY"]
        # 跳过备注类数据
        if key == "bz":
            continue
        weekday, jc = parse_weekday_and_jc(key)
        if(weekday == -1 or jc == -1):
            print(f"跳过无法解析的课程数据: {course}", file=sys.stderr)
            continue
        weeks = tuple(parse_weeks(course["ZC"]))

        group_key = (name, teacher, location, weekday, weeks)
        grouped[group_key].append(jc)

    merged = []

    for (name, teacher, location, weekday, weeks), jcs in grouped.items():
        jcs = sorted(jcs)

        start_jc = jcs[0]
        end_jc = jcs[-1]

        merged.append({
            "name": name,
            "teacher": teacher,
            "location": location,
            "weekday": weekday,
            "weeks": weeks,
            "start_jc": start_jc,
            "end_jc": end_jc
        })

    return merged


def generate_ics(courses, first_monday):
    build_time = datetime.utcnow().strftime(
        "%Y%m%dT%H%M%SZ"
    )
    ics = []
    ics.append("BEGIN:VCALENDAR")
    ics.append("VERSION:2.0")
    ics.append("PRODID:-//HIT Course Schedule//EN")
    ics.append("CALSCALE:GREGORIAN")

    for course in courses:
        for week in course["weeks"]:

            # week=1 -> 第1周
            event_date = first_monday + timedelta(days=7*(week-1) + (course["weekday"]-1))

            start_time = JC_TIME[course["start_jc"]][0]
            end_time = JC_TIME[course["end_jc"]][1]

            dtstart = datetime.strptime(
                event_date.strftime("%Y-%m-%d") + " " + start_time,
                "%Y-%m-%d %H:%M"
            )
            dtend = datetime.strptime(
                event_date.strftime("%Y-%m-%d") + " " + end_time,
                "%Y-%m-%d %H:%M"
            )
            
            uid_source = "|".join([
                course['name'],
                course["teacher"],
                course["location"],
                dtstart.isoformat()
            ])
            uid = hashlib.md5(
                uid_source.encode("utf-8")
            ).hexdigest()

            ics.append("BEGIN:VEVENT")
            ics.append(f"UID:{uid}@sodium233bot")
            ics.append(f"DTSTAMP:{build_time}")
            ics.append(f"DTSTART:{dtstart.strftime('%Y%m%dT%H%M%S')}")
            ics.append(f"DTEND:{dtend.strftime('%Y%m%dT%H%M%S')}")
            ics.append(f"SUMMARY:{course['name']}")
            ics.append(f"LOCATION:{course['location']}")
            ics.append(f"DESCRIPTION:Teacher: {course['teacher']}")
            ics.append("END:VEVENT")

    ics.append("END:VCALENDAR")
    return "\n".join(ics)


def generate_ics_from_json(json_file, first_monday_str, output_path):

    first_monday = datetime.strptime(first_monday_str, "%Y-%m-%d")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged_courses = merge_courses(data)
    ics_content = generate_ics(merged_courses, first_monday)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ics_content)

    return output_path
