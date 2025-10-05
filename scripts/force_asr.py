from pathlib import Path
from whisper_to_cards.asr import transcribe_audio, write_transcript

src = Path("examples/lecture.mp3")
out = Path("outputs/transcript.json")
out.parent.mkdir(parents=True, exist_ok=True)

t = transcribe_audio(src, model_size="small", language="en")
write_transcript(t, out)
print("WROTE:", out)
