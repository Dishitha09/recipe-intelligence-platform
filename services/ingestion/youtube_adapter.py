from services.ingestion.source_adapter import SourceAdapter


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
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript = YouTubeTranscriptApi.get_transcript(self.video_id)
        raw_text = " ".join(item.get("text", "") for item in transcript).strip()
        source_url = f"https://www.youtube.com/watch?v={self.video_id}"

        self.raw_records = [
            self.build_raw_record(
                {
                    "title": None,
                    "raw_text": raw_text,
                    "source_url": source_url,
                },
                metadata={
                    "video_id": self.video_id,
                    "segments": len(transcript),
                }
            )
        ]

        return self.raw_records
