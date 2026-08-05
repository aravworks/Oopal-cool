"""
MindEase — Speech Emotion Recognition (SER)
Two-step pipeline:
  1. Transcribe audio → text via OpenAI Whisper
  2. Analyse transcript + acoustic features via Gemini
     (full acoustic SER would need librosa/pyAudioAnalysis — 
      this version uses Whisper's metadata + Gemini text analysis
      as a practical approximation for the college demo)
"""

import os
import io
import json
from openai import OpenAI

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

import google.generativeai as genai
from gemini_system_prompt import generate_with_fallback


# ── Step 1: Transcribe ────────────────────────────────────────────────────────

def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Send audio bytes to Whisper API.
    Returns: { transcript, language, duration_secs }
    """
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    response = openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",   # includes segments with timestamps
        timestamp_granularities=["segment"],
    )

    # Extract pause data from segment timestamps
    segments = response.segments or []
    pauses = _calculate_pauses(segments)

    return {
        "transcript":    response.text,
        "language":      response.language,
        "duration_secs": response.duration,
        "segments":      [{"text": s.text, "start": s.start, "end": s.end} for s in segments],
        "pauses":        pauses,
    }


def _calculate_pauses(segments: list) -> dict:
    """
    Detect silence gaps between spoken segments.
    Long pauses (>1.5s) are a signal of emotional heaviness or dissociation.
    """
    if len(segments) < 2:
        return {"count": 0, "avg_duration": 0, "max_duration": 0}

    gaps = []
    for i in range(1, len(segments)):
        gap = segments[i].start - segments[i - 1].end
        if gap > 0.5:   # ignore micro-gaps (normal breathing)
            gaps.append(gap)

    if not gaps:
        return {"count": 0, "avg_duration": 0, "max_duration": 0}

    return {
        "count":        len(gaps),
        "avg_duration": round(sum(gaps) / len(gaps), 2),
        "max_duration": round(max(gaps), 2),
    }


# ── Step 2: Emotion Analysis ──────────────────────────────────────────────────

def analyse_emotion(transcript: str, pause_data: dict, duration_secs: float) -> dict:
    """
    Uses Gemini to classify emotional state from transcript content
    combined with acoustic heuristics (pause frequency, speaking pace).

    Returns:
      {
        calm:    float (0–1),
        anxious: float (0–1),
        fatigue: float (0–1),
        sad:     float (0–1),
        primary_emotion: str,
        notes: str,
      }
    """
    words = len(transcript.split())
    words_per_minute = (words / duration_secs * 60) if duration_secs > 0 else 0
    long_pauses = pause_data.get("count", 0)
    avg_pause   = pause_data.get("avg_duration", 0)

    # Acoustic heuristics
    speech_rate_note = (
        "Speech rate is very fast (>180 wpm) — possible anxiety or urgency."
        if words_per_minute > 180 else
        "Speech rate is slow (<100 wpm) — possible fatigue or low mood."
        if words_per_minute < 100 else
        "Speech rate is normal."
    )
    pause_note = (
        f"{long_pauses} notable pauses detected (avg {avg_pause}s). "
        + ("Frequent long pauses suggest emotional heaviness or dissociation."
           if long_pauses > 4 else "")
    )

    prompt = f"""You are an emotion classifier for a mental health app.
Analyse the transcript below alongside the acoustic notes.
Return ONLY a valid JSON object with these exact keys:
  calm, anxious, fatigue, sad  → each a float from 0.0 to 1.0 (they don't need to sum to 1)
  primary_emotion              → one word: calm | anxious | fatigued | sad | mixed
  notes                        → one sentence summary of the emotional state

Acoustic context:
- {speech_rate_note}
- {pause_note}

Transcript:
"{transcript}"

JSON only, no markdown:"""

    try:
        resp = generate_with_fallback(lambda name: genai.GenerativeModel(name).generate_content(prompt))
        raw  = resp.text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        result["words_per_minute"] = round(words_per_minute)
        return result
    except Exception as e:
        # Fallback — return neutral scores
        return {
            "calm":             0.5,
            "anxious":          0.3,
            "fatigue":          0.2,
            "sad":              0.2,
            "primary_emotion":  "mixed",
            "notes":            "Emotion analysis unavailable.",
            "words_per_minute": round(words_per_minute),
            "error":            str(e),
        }


# ── Combined pipeline ─────────────────────────────────────────────────────────

def process_voice_input(audio_bytes: bytes, filename: str = "audio.webm") -> dict:
    """
    Full pipeline: audio bytes → transcript + emotion scores.
    Called by POST /api/v1/voice/transcribe
    """
    transcription = transcribe_audio(audio_bytes, filename)
    emotion = analyse_emotion(
        transcript=transcription["transcript"],
        pause_data=transcription["pauses"],
        duration_secs=transcription["duration_secs"],
    )
    return {
        "transcript": transcription["transcript"],
        "duration_secs": transcription["duration_secs"],
        "language": transcription["language"],
        "emotion": emotion,
        "context_for_gemini": (
            f"[Voice note — {transcription['duration_secs']:.0f}s, "
            f"primary emotion: {emotion['primary_emotion']}, "
            f"calm: {emotion['calm']:.0%}, "
            f"anxious: {emotion['anxious']:.0%}, "
            f"fatigue: {emotion['fatigue']:.0%}]\n\n"
            f"Transcript: {transcription['transcript']}"
        ),
    }
