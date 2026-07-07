from services.ingestion.source_adapter import SourceAdapter


def _first_nonempty_line(text):
    for line in str(text or "").splitlines():
        line = line.strip()
        if line:
            return line

    return None


def _read_text(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().strip()


class YouTubeAdapter(SourceAdapter):
    source_type = "youtube"

    def __init__(self, video_id, source_id="youtube.default", config=None):
        self.video_id = video_id
        self.raw_records = []

        super().__init__(source_id=source_id, config=config)

    def validate_config(self):
        super().validate_config()

        if not self.video_id:
            raise ValueError("video_id is required")

    def extract(self):
        transcript_path = self.config.get("transcript_path")
        transcript_text = self.config.get("transcript_text")
        transcript_status = "api"
        segment_count = 0

        if transcript_text:
            raw_text = str(transcript_text).strip()
            transcript_status = "inline_config"
        elif transcript_path:
            raw_text = _read_text(transcript_path)
            transcript_status = "sidecar_file"
        else:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript = YouTubeTranscriptApi.get_transcript(self.video_id)
            raw_text = " ".join(item.get("text", "") for item in transcript).strip()
            segment_count = len(transcript)

        source_url = self.config.get(
            "source_url",
            f"https://www.youtube.com/watch?v={self.video_id}",
        )
        title = self.config.get("title") or _first_nonempty_line(raw_text)

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": title,
                    "raw_text": raw_text,
                    "source_url": source_url,
                },
                metadata={
                    "video_id": self.video_id,
                    "segments": segment_count,
                    "transcript_status": transcript_status,
                    "transcript_path": transcript_path,
                }
            )
        ]

        return self.raw_records
