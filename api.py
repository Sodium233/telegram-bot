from utils import file
from utils.calendar import ScheduleManager
from config import CONFIG

import jwclient

class API:

    def __init__(self, jw):
        self.jw = jw
        self.schedule_manager = ScheduleManager()

    async def update_calendar(self):
        schedule_data = await self.jw.get_schedule()
        exam_data = await self.jw.get_exam()
        file.save_json("schedule.json", schedule_data)
        file.save_json("exam.json", exam_data)
        self.schedule_manager.load()
        self.schedule_manager.generate_ics()
        print(f"日历已保存到{CONFIG['output']['ics_file']}")

    def get_local_schedule(self):
        return file.load_json("schedule.json")

    def get_today_schedule(self):
        return self.schedule_manager.load().get_today_schedule()

    async def get_gpa(self):
        gpa = await self.jw.get_gpa()
        return gpa
    async def get_scores(self, xn=None, xq=None):
        scores = await self.jw.get_scores(xn,xq)
        return scores