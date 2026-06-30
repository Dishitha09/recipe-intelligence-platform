from services.ingestion.audio_adapter import AudioAdapter


def test_audio_adapter_returns_raw_record_for_existing_file(tmp_path):
    audio_path = tmp_path / "sample.mp3"
    audio_path.write_bytes(b"")

    adapter = AudioAdapter(str(audio_path))
    records = adapter.extract()

    assert len(records) == 1
    assert records[0].source_type == "audio"
    assert records[0].metadata["filename"] == "sample.mp3"
    assert records[0].metadata["transcription_status"] == "not_transcribed"


def test_audio_adapter_rejects_missing_file(tmp_path):
    adapter = AudioAdapter(str(tmp_path / "missing.mp3"))

    try:
        adapter.extract()
        raised = False
    except FileNotFoundError:
        raised = True

    assert raised is True
