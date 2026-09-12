from datetime import date, datetime, time, timedelta
from app.domain import Medication, ScheduleOccurrence


DEFAULT_REMINDER_TIMES = {
    1: [time(9, 0)],
    2: [time(9, 0), time(21, 0)],
    3: [time(9, 0), time(14, 0), time(21, 0)],
    4: [time(8, 0), time(12, 0), time(17, 0), time(21, 0)],
}


def reminder_times(times_per_day: int) -> list[time]:
    if times_per_day in DEFAULT_REMINDER_TIMES:
        return DEFAULT_REMINDER_TIMES[times_per_day]
    start, span = 8 * 60, 13 * 60
    return [time((start + round(i * span / max(times_per_day - 1, 1))) // 60 % 24, (start + round(i * span / max(times_per_day - 1, 1))) % 60) for i in range(times_per_day)]


def generate_schedule(medication: Medication) -> list[ScheduleOccurrence]:
    # Never infer a course length. A missing duration must be clarified in the
    # source prescription before calendar occurrences can be generated.
    if medication.duration_days is None:
        return []
    times = medication.exact_times or reminder_times(medication.times_per_day)
    source = "prescribed_exact_time" if medication.exact_times else "reminder_preference_default"
    result = []
    for day_offset in range(medication.duration_days):
        on_date = medication.start_date + timedelta(days=day_offset)
        for dose_time in times:
            timestamp = datetime.combine(on_date, dose_time)
            result.append(ScheduleOccurrence(
                id=f"{medication.id}:{timestamp.isoformat()}", medication_id=medication.id,
                medication_name=medication.name, dosage=medication.dosage, quantity=medication.quantity,
                instructions=medication.instructions, scheduled_at=timestamp, time_source=source,
            ))
    return result


def all_occurrences(medications: list[Medication], logs: dict[str, dict]) -> list[ScheduleOccurrence]:
    rows = [item for medication in medications for item in generate_schedule(medication)]
    for item in rows:
        if item.id in logs:
            item.status = "taken"
            item.completed_at = datetime.fromisoformat(logs[item.id]["completed_at"])
    return sorted(rows, key=lambda item: item.scheduled_at)
