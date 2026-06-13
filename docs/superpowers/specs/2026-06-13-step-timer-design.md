# Step Timer Feature Design

Date: 2026-06-13

## Overview

Recipe steps can have an optional countdown timer. In the cooking view, steps with a timer show a timer widget the user can start, pause, and restart. When the timer expires, an alarm plays for up to 10 seconds with a dismiss button.

## Data Model

Add an optional `timer` field to the `Step` model:

```python
timer = models.PositiveSmallIntegerField(
    null=True, blank=True,
    help_text=_("Optional timer duration in minutes")
)
```

- Unit: whole minutes
- `null` / blank means no timer for that step
- One migration required
- The `create_step_formset` fields expand to `("content", "order", "timer")`

## Cooking View UI

Steps without a timer render exactly as before. Steps with a timer show an additional widget below the step text containing:

**Idle state:**
- Clock icon + duration label (e.g. "15 min")
- "Start" button

**Running state:**
- Countdown display (MM:SS format)
- "Cancel" button

**Alarming state (timer hit zero):**
- Visual indicator (e.g. pulsing or highlighted widget)
- "Dismiss" button — stops the alarm immediately, transitions to done state

**Done state:**
- "Restart" button — resets countdown to full duration, returns to idle

Multiple timers run fully independently — starting one has no effect on others. Timer state is not persisted across page reloads.

## Alarm Sound

Implemented using the Web Audio API — no audio assets required, works offline.

- Pattern: square wave oscillator at ~880 Hz, beeping 0.2s on / 0.1s off
- Duration: up to 10 seconds, stops automatically
- Dismiss button stops the alarm early
- AudioContext is created lazily on first user interaction to satisfy browser autoplay policies

## Recipe Edit Form

The step formset includes a `timer` field rendered as a small number input (minutes). The field is optional — leaving it blank means no timer.

## Testing

- Unit test: `Step.timer` field is optional, saves/retrieves correctly
- Unit test: formset accepts and saves `timer` values including blank
- No JS unit tests (vanilla JS, minimal logic)
