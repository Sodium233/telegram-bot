from utils import file
from utils import gen_ics
from config import CONFIG

import jwclient
class API:

    def __init__(self, jw):
        self.jw = jw

    async def update_schedule(self):
        schedule_data = await self.jw.get_schedule()
        file.save_json("schedule.json", schedule_data)
        gen_ics.generate_ics_from_json(
            CONFIG['output']['schedule_file'],
            CONFIG['schedule']['first_day'],
            CONFIG['output']['ics_file']
        )
        print(f"课表已保存到 {CONFIG['output']['schedule_file']} 和 {CONFIG['output']['ics_file']}")

    def get_local_schdule(self):
        return file.load_json("schedule.json")

    async def update_score(self):
        pass