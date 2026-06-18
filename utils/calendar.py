import json
import re
import sys
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, date

from ics import Calendar as IcsCalendar, Event as IcsEvent
from ics.grammar.parse import ContentLine

from config import CONFIG

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

    brackets = re.findall(r"\[(.*?)\]", sksj)
    week_pattern = re.compile(r"\d.*周")
    section_pattern = re.compile(r"\d.*节")
    location_pattern = re.compile(r"^[A-Za-z]\d+")
    teacher_pattern = re.compile(r"^[一-鿿]{2,4}$")

    info_items = []
    for item in brackets:
        if week_pattern.search(item) or section_pattern.search(item):
            continue
        info_items.append(item)

    for item in info_items:
        if location_pattern.match(item):
            location = item
            break

    for item in info_items:
        if item != location and teacher_pattern.match(item):
            teacher = item
            break

    if location == "无地点":
        for item in info_items:
            if item != teacher:
                location = item
                break

    for line in lines:
        if line.startswith("["):
            break
        name_lines.append(line.strip())

    return " - ".join(name_lines), teacher, location


def parse_weekday_and_jc(key):
    parts = key.split("_")
    if len(parts) != 2:
        print(f"无法解析的 KEY: {key}", file=sys.stderr)
        return -1, -1

    weekday = parts[0].replace("xq", "")
    jc = parts[1].replace("jc", "")

    if weekday.isdigit() and jc.isdigit():
        return int(weekday), int(jc)

    print(f"无法解析的 KEY: {key}", file=sys.stderr)
    return -1, -1


def parse_weeks(zc):
    weeks = []
    for i, c in enumerate(zc):
        if c == "1":
            weeks.append(i + 1)
    return weeks


def split_contiguous_ranges(values):
    sorted_values = sorted(set(values))
    ranges = []
    if not sorted_values:
        return ranges

    start = end = sorted_values[0]
    for value in sorted_values[1:]:
        if value == end + 1:
            end = value
        else:
            ranges.append((start, end))
            start = end = value
    ranges.append((start, end))
    return ranges


def merge_courses(data):
    grouped = defaultdict(list)

    for course in data:
        try:
            name, teacher, location = parse_course_info(course["SKSJ"])
        except Exception:
            print(f"跳过无法解析的课程数据: {course}", file=sys.stderr)
            continue

        key = course.get("KEY")
        if not key or key == "bz":
            continue

        weekday, jc = parse_weekday_and_jc(key)
        if weekday == -1 or jc == -1:
            print(f"跳过无法解析的课程数据: {course}", file=sys.stderr)
            continue

        weeks = tuple(parse_weeks(course.get("ZC", "")))
        if not weeks:
            continue

        grouped[(name, teacher, location, weekday, weeks)].append(jc)

    merged = []
    for (name, teacher, location, weekday, weeks), jcs in grouped.items():
        for start_jc, end_jc in split_contiguous_ranges(jcs):
            merged.append({
                "name": name,
                "teacher": teacher,
                "location": location,
                "weekday": weekday,
                "weeks": weeks,
                "start_jc": start_jc,
                "end_jc": end_jc,
            })

    return merged


def parse_exam(exam):
    times = exam.get("KSJTSJ", "").split("-")
    if len(times) != 2:
        raise ValueError(f"无法解析考试时间: {exam.get('KSJTSJ')}")

    start_time, end_time = times
    start = datetime.fromisoformat(f"{exam.get('KSRQ', '')} {start_time}")
    end = datetime.fromisoformat(f"{exam.get('KSRQ', '')} {end_time}")

    return {
        "title": f"【{exam.get('KSSJDMC', '')}考试】{exam.get('KCMC', '')}",
        "start": start,
        "end": end,
        "location": f"{exam.get('JXLMC', '')} {exam.get('JXCDMC', '')}".strip(),
        "description": (
            f"课程代码：{exam.get('KCDM', '')}\n"
            f"考试类型：{exam.get('KSSJDMC', '')}"
        ),
    }


class ScheduleEvent:
    def __init__(self, title, start, end, location="", description="", uid=None, source="course"):
        self.title = title
        self.start = start
        self.end = end
        self.location = location
        self.description = description
        self.uid = uid
        self.source = source

    def to_ics_event(self):
        event = IcsEvent()
        event.name = self.title
        event.location = self.location
        event.description = self.description
        if self.uid is not None:
            event.uid = self.uid

        event.extra.append(ContentLine("DTSTART", value=self.start.strftime("%Y%m%dT%H%M%S")))
        event.extra.append(ContentLine("DTEND", value=self.end.strftime("%Y%m%dT%H%M%S")))
        return event

    def to_dict(self):
        return {
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "location": self.location,
            "description": self.description,
            "uid": self.uid,
            "source": self.source,
        }


class ScheduleManager:
    def __init__(self, schedule_file=None, exam_file=None, first_monday=None, output_path=None):
        self.schedule_file = schedule_file or CONFIG["output"].get("schedule_file")
        self.exam_file = exam_file or CONFIG["output"].get("exam_file")
        self.first_monday = first_monday or datetime.strptime(CONFIG["schedule"]["first_day"], "%Y-%m-%d")
        self.output_path = output_path or CONFIG["output"].get("ics_file")
        self._raw_schedule = None
        self._raw_exams = None
        self._course_blocks = None
        self._events = None

    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load(self):
        self._raw_schedule = self._load_json(self.schedule_file)
        self._raw_exams = self._load_json(self.exam_file) if self.exam_file else []
        self._course_blocks = merge_courses(self._raw_schedule)
        self._events = None
        return self

    def build_course_events(self):
        if self._course_blocks is None:
            self.load()

        events = []
        for course in self._course_blocks:
            for week in course["weeks"]:
                event_date = self.first_monday + timedelta(days=7 * (week - 1) + (course["weekday"] - 1))
                start_time = JC_TIME.get(course["start_jc"], ("00:00", "00:00"))[0]
                end_time = JC_TIME.get(course["end_jc"], ("00:00", "00:00"))[1]
                start_dt = datetime.strptime(f"{event_date:%Y-%m-%d} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(f"{event_date:%Y-%m-%d} {end_time}", "%Y-%m-%d %H:%M")
                uid_source = "|".join([course["name"], course["teacher"], course["location"], start_dt.isoformat()])
                uid = hashlib.md5(uid_source.encode("utf-8")).hexdigest()
                events.append(ScheduleEvent(
                    title=course["name"],
                    start=start_dt,
                    end=end_dt,
                    location=course["location"],
                    description=f"Teacher: {course['teacher']}",
                    uid=f"{uid}@sodium233bot",
                    source="course",
                ))
        return events

    def build_exam_events(self):
        if self._raw_exams is None:
            self.load()

        events = []
        for exam in self._raw_exams:
            try:
                exam_info = parse_exam(exam)
                uid = hashlib.md5(exam_info["title"].encode("utf-8")).hexdigest()
                events.append(ScheduleEvent(
                    title=exam_info["title"],
                    start=exam_info["start"],
                    end=exam_info["end"],
                    location=exam_info["location"],
                    description=exam_info["description"],
                    uid=f"{uid}@sodium233bot",
                    source="exam",
                ))
            except Exception as exc:
                print(f"跳过无法解析的考试数据: {exam!r}, 原因: {exc}", file=sys.stderr)
        return events

    def build_events(self):
        if self._events is not None:
            return self._events
        self._events = self.build_course_events() + self.build_exam_events()
        return self._events

    def generate_ics(self, output_path=None):
        self.build_events()
        calendar_obj = IcsCalendar()
        for event in self._events:
            calendar_obj.events.add(event.to_ics_event())

        output_path = output_path or self.output_path
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(calendar_obj.serialize())
        return output_path

    def get_events_for_date(self, query_date=None):
        if query_date is None:
            query_date = date.today()
        if isinstance(query_date, datetime):
            query_date = query_date.date()
        self.build_events()
        return [event.to_dict() for event in self._events if event.start.date() == query_date]

    def get_today_schedule(self):
        return self.get_events_for_date(date.today())


def generate_calendar():
    return ScheduleManager().load().generate_ics()


def get_today_schedule():
    return ScheduleManager().load().get_today_schedule()
