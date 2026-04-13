---
name: garmin-question-assistant
description: Use this skill when the user asks about Garmin health, recovery, training status, recent activities, or race predictions. Route the question to the correct local Garmin CLI query, read the returned JSON, and answer using the fetched timestamp and structured highlights.
---

# Garmin Question Assistant

Use this skill when the user is asking about Garmin-derived health or training questions and the local Garmin CLI tools are available in the same workspace.

## Workflow

1. Classify the user question into one of these `question_type` values:
   - `sleep_recovery`
   - `training_state`
   - `activity_history`
   - `performance_prediction`
   - `composite_health`
2. Run the matching local CLI command from this repository.
3. Read the JSON result.
4. Answer the question in natural language.
5. Explicitly mention the data time using:
   - `meta.fetched_at`
   - `meta.collected_for_date`

## CLI Commands

### Sleep and recovery

```bash
python3 <GARMIN_PROJECT_ROOT>/scripts/garmin_query.py sleep_recovery --pretty
```

Use for:

- sleep quality
- recovery
- HRV
- Body Battery
- overnight stress

### Training state

```bash
python3 <GARMIN_PROJECT_ROOT>/scripts/garmin_query.py training_state --pretty
```

Use for:

- today's training state
- readiness
- VO2Max
- recovery time

### Activity history

```bash
python3 <GARMIN_PROJECT_ROOT>/scripts/garmin_query.py activity_history --days 7 --pretty
```

Use for:

- what the user trained recently
- weekly activity review
- recent running or cycling history

### Performance prediction

```bash
python3 <GARMIN_PROJECT_ROOT>/scripts/garmin_query.py performance_prediction --pretty
```

Use for:

- 5K / 10K / half marathon / marathon prediction
- race prediction questions

### Composite health

```bash
python3 <GARMIN_PROJECT_ROOT>/scripts/garmin_query.py composite_health --days 7 --pretty
```

Use for:

- overall recent condition
- combined sleep, stress, training, and activity review
- whether the user seems fatigued overall

## Answering Rules

- Always answer from the returned JSON.
- Do not invent Garmin values that are absent.
- Use `guidance.summary` first when it is present.
- Use `guidance.rationale` as the main evidence source.
- Use `highlights` for compact numeric support.
- Use `data` when you need more detail.
- If `missing` is not empty, mention that some Garmin fields were unavailable.
- Always state which data date the answer is based on.
- Do not stop at listing metrics; turn the result into a practical recommendation.

## Coaching-Style Answer Shape

Prefer this structure for most answers:

1. Direct judgment first  
   Example: "今天更适合减量或恢复，不建议安排质量训练。"
2. Evidence bullets with real values  
   Quote 2-4 concrete points from `guidance.rationale` or `highlights`.
3. Concrete action for today or the next few days  
   Example: rest, easy run, short recovery ride, or keep the session easy.
4. Data time note  
   Mention `meta.collected_for_date` and, when useful, `meta.fetched_at`.

Do not give vague conclusions like “状态一般” unless you immediately explain why with values.

## Guidance Heuristics

Use these as soft coaching rules, not as rigid medical claims:

- If `training_readiness_score` is very low or `training_readiness_band` is `very_low`, recommend rest or very light activity.
- If `recovery_time_hours` is very high, explicitly say the body is still carrying fatigue.
- If `sleep_score` is mediocre but not terrible, describe recovery as partial rather than bad.
- If `avg_overnight_hrv` is acceptable and `body_battery_change` is positive, mention that some overnight recovery happened even if training readiness is poor.
- If the latest recent activity was long or hard, connect it to today's fatigue instead of only listing it.
- When VO2Max is good but readiness is poor, explain the difference between long-term fitness and short-term freshness.
- If recent activity records are mostly running/cycling and there is no recorded strength work, you may suggest adding a light strength or core session after recovery improves.
- Do not claim anaerobic-zone imbalance unless the returned data actually contains intensity-zone evidence.
- When you point out a structural weakness, explain the likely training consequence in plain language before giving the fix.

## What Good Answers Look Like

- Useful: "你的长期体能基础不错，但今天短期恢复明显不够，所以更适合轻松活动而不是质量课。"
- Better: "今天不建议做质量训练。训练准备度只有 1，恢复时间还剩约 59.4 小时，虽然 VO2Max 59 说明底子很好，但这更像是短期恢复没跟上，而不是能力不足。"
- Not useful: "VO2Max 59，HRV 69，训练准备度 1，静息心率 45。"

## Question-Type Specific Focus

### `sleep_recovery`

- Emphasize overnight recovery quality.
- Explain whether sleep, HRV, stress, and heart rate point in the same direction.
- End with a suggestion for today's intensity.

### `training_state`

- Separate long-term fitness from current readiness.
- Explain whether the user is ready for quality work today.
- Give a clear recommendation: rest, easy, moderate, or go ahead.

### `activity_history`

- Summarize training pattern, not just list workouts.
- Mention volume, frequency, and obvious load clusters.
- If the structure is mostly endurance and there is no recorded strength work, say so plainly and suggest a small amount of strength/core work.
- When mentioning that gap, explain what it may affect: stability, fatigue resistance, movement quality, or injury risk under fatigue.

### `performance_prediction`

- Give the prediction first.
- Then explain what the prediction says about current fitness.
- If possible, connect it to VO2Max or recent training state.

### `composite_health`

- Synthesize sleep, stress, readiness, and recent activity into one conclusion.
- Explicitly answer whether the user seems fresh, neutral, or fatigued overall.
- Give a practical next-step recommendation.
- If recent training looks one-dimensional, mention what is missing from the recorded structure.
- When you mention what is missing, explain why it matters for the next stage of training.

## Routing Guidance

- Questions about sleep, HRV, overnight recovery, or Body Battery usually map to `sleep_recovery`.
- Questions about whether the user should train today, readiness, VO2Max, or training load usually map to `training_state`.
- Questions about what the user did recently map to `activity_history`.
- Questions about predicted race times map to `performance_prediction`.
- Broad “how am I doing overall” questions map to `composite_health`.
