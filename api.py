from utils import file
from utils.calendar import ScheduleManager
from config import CONFIG

import jwclient

class API:

    def __init__(self, jw):
        self.jw = jw
        self.current_schedule_manager = ScheduleManager()
        self.current_xn = None
        self.current_xq = None
        self.current_first_monday = None

    async def update_calendar(self):
        await self.update_term_information()
        self.current_schedule_manager.set_first_monday(self.current_first_monday)
        schedule_data = await self.jw.get_schedule()
        exam_data = await self.jw.get_exam()
        file.save_json("schedule.json", schedule_data)
        file.save_json("exam.json", exam_data)
        self.current_schedule_manager.load()
        self.current_schedule_manager.generate_ics()
        print(f"日历已保存到{CONFIG['output']['ics_file']}")

    async def update_term_information(self):
        self.current_xn, self.current_xq, self.current_first_monday = await self.jw.get_latest_term_information()

    def get_current_term_information(self):
        return self.current_xn, self.current_xq, self.current_first_monday

    def get_local_schedule(self):
        return file.load_json("schedule.json")

    def get_today_schedule(self):
        return self.current_schedule_manager.load().get_today_schedule()

    async def get_credit_requirenments(self):
        return await self.jw.get_credit_requirements()

    async def get_transferable_credit(self):
        return await self.jw.get_transferable_social_credit(), await self.jw.get_transferable_innovation_credit()

    async def get_gpa(self):
        gpa = await self.jw.get_gpa()
        return gpa
    async def get_scores(self, xn=None, xq=None):
        scores = await self.jw.get_scores(xn,xq)
        return scores